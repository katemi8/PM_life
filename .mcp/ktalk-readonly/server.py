#!/usr/bin/env python3
"""Project-local MCP server for Kontur Talk transcripts and guarded meetings.

The server intentionally uses only Python's standard library. It reads a
short-lived browser session token from an ignored local config file. External
write operations are guarded by local pending proposals and exact approval text.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import secrets
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Optional


SERVER_NAME = "trendagent-ktalk"
SERVER_VERSION = "0.2.0"
DEFAULT_CONFIG_PATH = ".claude/local/ktalk-session.json"
DEFAULT_TIMEOUT_SECONDS = 30
DEFAULT_PENDING_DIR = ".claude/local/ktalk-pending"
DEFAULT_TIMEZONE = "Europe/Moscow"
RECORDING_KEY_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,255}$")
PENDING_ID_RE = re.compile(r"^[0-9]{10}$")
ROOM_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]{2,63}$")
VALID_SUMMARY_TYPES = {"shortSummary", "protocol"}
VALID_FORMATS = {"markdown", "raw"}
MSK = timezone(timedelta(hours=3))


class ConfigError(Exception):
    """Configuration is missing or unsafe."""


class ToolError(Exception):
    """Tool call failed in a user-visible way."""


class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Prevent leaking sessionToken through HTTP redirects."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[override]
        return None


def _as_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _as_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "1", "yes", "y"}:
            return True
        if lowered in {"false", "0", "no", "n"}:
            return False
    raise ToolError("boolean value must be true or false")


def _escape_table(value: Any) -> str:
    return _as_text(value, "-").replace("|", "\\|").replace("\n", " ")


def _format_datetime(value: Any) -> str:
    text = _as_text(value)
    if not text:
        return "-"
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return parsed.strftime("%Y-%m-%d %H:%M")
    except ValueError:
        return text


def _format_duration(seconds: Any) -> str:
    try:
        value = int(seconds or 0)
    except (TypeError, ValueError):
        return "-"
    if value < 3600:
        minutes = value // 60
        if value and minutes == 0:
            minutes = 1
        return f"{minutes} min"
    hours = value // 3600
    minutes = (value % 3600) // 60
    return f"{hours} h {minutes} min"


def _format_offset(millis: Any) -> str:
    try:
        total_seconds = int(millis or 0) // 1000
    except (TypeError, ValueError):
        total_seconds = 0
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def _user_name(user: Any) -> str:
    if not isinstance(user, dict):
        return "Unknown"
    if user.get("isAnonymous"):
        return _as_text(user.get("anonymousName"), "Anonymous")
    info = user.get("userInfo") if isinstance(user.get("userInfo"), dict) else user
    surname = _as_text(info.get("surname")) if isinstance(info, dict) else ""
    firstname = _as_text(info.get("firstname")) if isinstance(info, dict) else ""
    login = _as_text(info.get("login")) if isinstance(info, dict) else ""
    if surname and firstname:
        return f"{surname} {firstname}"
    return surname or firstname or login or "Unknown"


def _normalize_format(value: Any) -> str:
    fmt = _as_text(value, "markdown")
    if fmt not in VALID_FORMATS:
        raise ToolError("format must be 'markdown' or 'raw'")
    return fmt


def _require_recording_key(value: Any) -> str:
    key = _as_text(value)
    if not key:
        raise ToolError("recording_key is required")
    if not RECORDING_KEY_RE.match(key):
        raise ToolError("recording_key contains unsafe characters")
    return key


def _require_pending_id(value: Any) -> str:
    pending_id = _as_text(value)
    if not pending_id:
        raise ToolError("pending_id is required")
    if not PENDING_ID_RE.match(pending_id):
        raise ToolError("pending_id contains unsafe characters")
    return pending_id


def _require_title(value: Any) -> str:
    title = _as_text(value).strip()
    if not title:
        raise ToolError("title is required")
    if len(title) > 200:
        raise ToolError("title must be 200 characters or less")
    return title


def _normalize_room_name(value: Any) -> str:
    room_name = _as_text(value).strip().lower()
    if not room_name:
        room_name = "".join(secrets.choice("abcdefghijklmnopqrstuvwxyz0123456789") for _ in range(12))
    if not ROOM_NAME_RE.match(room_name):
        raise ToolError("room_name must contain only lowercase latin letters, digits, or hyphens")
    return room_name


def _timezone_info(name: str) -> timezone:
    if name in ("", DEFAULT_TIMEZONE, "MSK", "UTC+3", "UTC+03:00"):
        return MSK
    if name in ("UTC", "Z"):
        return timezone.utc
    raise ToolError("timezone must be Europe/Moscow or UTC")


def _parse_datetime(value: Any, timezone_name: str, field: str) -> datetime:
    text = _as_text(value).strip()
    if not text:
        raise ToolError(f"{field} is required")
    normalized = text.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        raise ToolError(f"{field} must be ISO 8601, for example 2026-05-19T12:00")
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=_timezone_info(timezone_name))
    return parsed.astimezone(timezone.utc)


def _api_datetime(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _display_datetime(value: datetime, timezone_name: str = DEFAULT_TIMEZONE) -> str:
    return value.astimezone(_timezone_info(timezone_name)).strftime("%Y-%m-%d %H:%M")


def _duration_minutes(value: Any) -> int:
    try:
        minutes = int(value)
    except (TypeError, ValueError):
        raise ToolError("duration_min must be an integer")
    if minutes < 1 or minutes > 24 * 60:
        raise ToolError("duration_min must be between 1 and 1440")
    return minutes


def _json_text(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)


def _chunk_text(text: str, chunk_size: int) -> list[str]:
    if chunk_size < 1000:
        raise ToolError("chunk_size must be at least 1000")
    if len(text) <= chunk_size:
        return [text]

    parts = [part for part in text.split("\n\n") if part.strip()]
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0
    for part in parts:
        added = len(part) + (2 if current else 0)
        if current and current_len + added > chunk_size:
            chunks.append("\n\n".join(current))
            current = [part]
            current_len = len(part)
        else:
            current.append(part)
            current_len += added
    if current:
        chunks.append("\n\n".join(current))
    return chunks


def format_recordings_list(data: dict[str, Any]) -> str:
    records = data.get("recordings") or data.get("entities") or []
    if not isinstance(records, list) or not records:
        return "# KTalk recordings\n\nNo recordings found."

    lines = [
        "# KTalk recordings",
        "",
        "| ID | Title | Date | Author | Duration | Participants |",
        "|----|-------|------|--------|----------|--------------|",
    ]
    for record in records:
        if not isinstance(record, dict):
            continue
        created_by = record.get("createdBy") if isinstance(record.get("createdBy"), dict) else {}
        participants = record.get("participants") if isinstance(record.get("participants"), list) else []
        if participants:
            participant_text = ", ".join(_user_name(item) for item in participants)
        else:
            participant_text = _as_text(record.get("participantsCount"), "-")
        lines.append(
            "| {id} | {title} | {date} | {author} | {duration} | {participants} |".format(
                id=_escape_table(record.get("id") or record.get("key")),
                title=_escape_table(record.get("title") or "Untitled"),
                date=_escape_table(_format_datetime(record.get("createdDate"))),
                author=_escape_table(_user_name(created_by)),
                duration=_escape_table(_format_duration(record.get("duration"))),
                participants=_escape_table(participant_text),
            )
        )

    next_token = data.get("nextPageToken")
    if next_token:
        lines.append("")
        lines.append(f'Next page: pass page_token="{_as_text(next_token)}"')
    return "\n".join(lines)


def format_recording(data: dict[str, Any]) -> str:
    created_by = data.get("createdBy") if isinstance(data.get("createdBy"), dict) else {}
    participants = data.get("participants") if isinstance(data.get("participants"), list) else []
    lines = [
        f"# {_as_text(data.get('title'), 'Untitled')}",
        "",
        f"- ID: {_as_text(data.get('id') or data.get('key'), '-')}",
        f"- Date: {_format_datetime(data.get('createdDate'))}",
        f"- Author: {_user_name(created_by)}",
        f"- Room: {_as_text(data.get('roomName'), '-')}",
        f"- Duration: {_format_duration(data.get('duration'))}",
    ]
    if participants:
        lines.append("- Participants: " + ", ".join(_user_name(item) for item in participants))
    else:
        lines.append(f"- Participants: {_as_text(data.get('participantsCount'), '-')}")
    return "\n".join(lines)


def _meeting_link(base_url: str, event: dict[str, Any]) -> str:
    online_url = _as_text(event.get("onlineMeetingUrl"))
    if online_url:
        return urllib.parse.urljoin(base_url + "/", online_url)
    room = event.get("room") if isinstance(event.get("room"), dict) else {}
    room_name = _as_text(event.get("roomName") or room.get("roomName"))
    if room_name:
        return f"{base_url}/{urllib.parse.quote(room_name, safe='')}"
    return "-"


def format_calendar_events(data: dict[str, Any], base_url: str) -> str:
    events = data.get("items") or data.get("events") or []
    if not isinstance(events, list) or not events:
        return "# KTalk calendar events\n\nNo events found."

    lines = [
        "# KTalk calendar events",
        "",
        "| ID | Title | Start | End | Room | Link | Attendees |",
        "|----|-------|-------|-----|------|------|-----------|",
    ]
    for event in events:
        if not isinstance(event, dict):
            continue
        attendees = event.get("requiredAttendees") if isinstance(event.get("requiredAttendees"), list) else []
        lines.append(
            "| {id} | {title} | {start} | {end} | {room} | {link} | {attendees} |".format(
                id=_escape_table(event.get("id")),
                title=_escape_table(event.get("subject") or event.get("title") or "Untitled"),
                start=_escape_table(_format_datetime(event.get("start"))),
                end=_escape_table(_format_datetime(event.get("end"))),
                room=_escape_table(event.get("roomName")),
                link=_escape_table(_meeting_link(base_url, event)),
                attendees=_escape_table(len(attendees)),
            )
        )
    return "\n".join(lines)


def format_transcript(data: dict[str, Any]) -> str:
    status = _as_text(data.get("status"))
    if status and status not in {"success", "completed"}:
        return f"# Transcript\n\nStatus: {status}"

    tracks = data.get("tracks")
    if not isinstance(tracks, list) or not tracks:
        return "# Transcript\n\nTranscript is empty or not available."

    entries: list[tuple[int, str, str]] = []
    for track in tracks:
        if not isinstance(track, dict):
            continue
        speaker = _user_name(track.get("speaker"))
        chunks = track.get("chunks") if isinstance(track.get("chunks"), list) else []
        for chunk in chunks:
            if not isinstance(chunk, dict):
                continue
            try:
                offset = int(chunk.get("startTimeOffsetInMillis") or 0)
            except (TypeError, ValueError):
                offset = 0
            text = _as_text(chunk.get("text"))
            if text:
                entries.append((offset, speaker, text))

    entries.sort(key=lambda item: item[0])
    if not entries:
        return "# Transcript\n\nTranscript is empty."

    lines = ["# Transcript", ""]
    for offset, speaker, text in entries:
        lines.append(f"**{speaker}** [{_format_offset(offset)}]: {text}")
        lines.append("")
    return "\n".join(lines).rstrip()


def _summary_chunks_to_text(chunks: Any) -> str:
    if not isinstance(chunks, list):
        return ""
    lines: list[str] = []
    for chunk in chunks:
        if not isinstance(chunk, dict):
            continue
        text = _as_text(chunk.get("text"))
        if not text:
            continue
        if chunk.get("type") == "heading":
            lines.append(f"### {text}")
        else:
            lines.append(text)
        lines.append("")
    return "\n".join(lines).rstrip()


def format_summary(data: dict[str, Any]) -> str:
    lines = ["# Summary", "", "## Short summary", ""]
    short = data.get("shortSummaryV2") if isinstance(data.get("shortSummaryV2"), dict) else {}
    protocol = data.get("protocolV2") if isinstance(data.get("protocolV2"), dict) else {}

    if short.get("status") == "success":
        lines.append(_summary_chunks_to_text(short.get("chunks")) or "No content.")
    else:
        lines.append(f"Status: {_as_text(short.get('status'), 'notAvailable')}")

    lines.extend(["", "## Protocol", ""])
    if protocol.get("status") == "success":
        lines.append(_summary_chunks_to_text(protocol.get("chunks")) or "No content.")
    else:
        lines.append(f"Status: {_as_text(protocol.get('status'), 'notAvailable')}")
    return "\n".join(lines).rstrip()


def format_summary_by_type(data: dict[str, Any], summary_type: str) -> str:
    title = "Short summary" if summary_type == "shortSummary" else "Protocol"
    if data.get("status") != "success":
        return f"# {title}\n\nStatus: {_as_text(data.get('status'), 'notAvailable')}"
    return f"# {title}\n\n{_summary_chunks_to_text(data.get('chunks')) or 'No content.'}"


class Config:
    def __init__(
        self,
        base_url: str,
        session_token: str,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
        pending_dir: str = DEFAULT_PENDING_DIR,
    ) -> None:
        self.base_url = base_url
        self.session_token = session_token
        self.timeout_seconds = timeout_seconds
        self.pending_dir = pending_dir


def _read_json_file(path: str) -> dict[str, Any]:
    if not path or not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ConfigError("KTalk config must be a JSON object")
    return data


def _split_hosts(value: Any) -> list[str]:
    if isinstance(value, list):
        return [_as_text(item).strip().lower() for item in value if _as_text(item).strip()]
    if isinstance(value, str):
        return [item.strip().lower() for item in value.split(",") if item.strip()]
    return []


def load_config(path: str) -> Config:
    data = _read_json_file(path)
    base_url = _as_text(data.get("base_url") or os.environ.get("KTALK_BASE_URL"))
    session_token = _as_text(
        data.get("session_token") or os.environ.get("KTALK_SESSION_TOKEN")
    )
    timeout_seconds = data.get("timeout_seconds") or os.environ.get("KTALK_TIMEOUT_SECONDS")
    pending_dir = _as_text(data.get("pending_dir") or os.environ.get("KTALK_PENDING_DIR"), DEFAULT_PENDING_DIR)

    if not base_url:
        raise ConfigError("KTalk base_url is missing")
    if not session_token:
        raise ConfigError("KTalk session_token is missing")

    parsed = urllib.parse.urlparse(base_url)
    if parsed.scheme != "https":
        raise ConfigError("KTalk base_url must use https")
    if not parsed.hostname:
        raise ConfigError("KTalk base_url must include a host")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ConfigError("KTalk base_url must not include credentials, query, or fragment")
    if parsed.path not in ("", "/"):
        raise ConfigError("KTalk base_url must be an origin URL without a path")

    host = parsed.hostname.lower()
    allowed_hosts = _split_hosts(data.get("allowed_hosts") or os.environ.get("KTALK_ALLOWED_HOSTS"))
    if allowed_hosts and host not in allowed_hosts:
        raise ConfigError("KTalk base_url host is not in allowed_hosts")

    try:
        timeout = int(timeout_seconds or DEFAULT_TIMEOUT_SECONDS)
    except (TypeError, ValueError):
        raise ConfigError("timeout_seconds must be an integer")
    if timeout < 1 or timeout > 120:
        raise ConfigError("timeout_seconds must be between 1 and 120")

    origin = f"{parsed.scheme}://{parsed.netloc}"
    if not pending_dir:
        pending_dir = DEFAULT_PENDING_DIR

    return Config(
        base_url=origin.rstrip("/"),
        session_token=session_token,
        timeout_seconds=timeout,
        pending_dir=pending_dir,
    )


class KTalkClient:
    def __init__(self, config: Config) -> None:
        self.config = config
        self.opener = urllib.request.build_opener(NoRedirectHandler)

    def request_json(
        self,
        method: str,
        path: str,
        params: Optional[dict[str, Any]] = None,
        body: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        query = {key: value for key, value in (params or {}).items() if value is not None}
        query["sessionToken"] = self.config.session_token
        url = self.config.base_url + path + "?" + urllib.parse.urlencode(query)
        payload = None
        headers = {"Accept": "application/json"}
        if body is not None:
            payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json; charset=utf-8"
        request = urllib.request.Request(url, data=payload, headers=headers, method=method)
        try:
            with self.opener.open(request, timeout=self.config.timeout_seconds) as response:
                raw = response.read()
        except urllib.error.HTTPError as exc:
            if exc.code in (301, 302, 303, 307, 308):
                raise ToolError("KTalk redirect refused to avoid token leakage")
            if exc.code in (401, 403):
                raise ToolError("KTalk auth failed: session token is invalid or expired")
            if exc.code == 404:
                raise ToolError("KTalk resource not found")
            if exc.code == 429:
                raise ToolError("KTalk rate limit exceeded")
            body_text = ""
            try:
                body_text = exc.read().decode("utf-8", errors="replace").strip()
            except Exception:  # noqa: BLE001 - keep HTTP error handling robust.
                body_text = ""
            if body_text:
                body_text = re.sub(r"sessionToken=[^&\\s]+", "sessionToken=<redacted>", body_text)
                raise ToolError(f"KTalk HTTP error {exc.code}: {body_text[:500]}")
            raise ToolError(f"KTalk HTTP error {exc.code}")
        except urllib.error.URLError:
            raise ToolError("KTalk network error")

        try:
            decoded = raw.decode("utf-8")
        except UnicodeDecodeError:
            raise ToolError("KTalk returned a non-UTF-8 response")
        try:
            data = json.loads(decoded)
        except json.JSONDecodeError:
            raise ToolError("KTalk returned a non-JSON response")
        if not isinstance(data, dict):
            raise ToolError("KTalk returned an unexpected JSON shape")
        return data

    def get_json(self, path: str, params: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        return self.request_json("GET", path, params=params)

    def post_json(self, path: str, body: dict[str, Any], params: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        return self.request_json("POST", path, params=params, body=body)

    def put_json(self, path: str, body: dict[str, Any], params: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        return self.request_json("PUT", path, params=params, body=body)

    def list_recordings(self, args: dict[str, Any]) -> str:
        fmt = _normalize_format(args.get("format"))
        top = int(args.get("top") or 30)
        if top < 1 or top > 100:
            raise ToolError("top must be between 1 and 100")
        data = self.get_json(
            "/api/recordings",
            {
                "query": args.get("query"),
                "startFrom": args.get("start_from"),
                "startTo": args.get("start_to"),
                "top": top,
                "orderMode": args.get("order") or "byTimeNewFirst",
                "pageTokenString": args.get("page_token"),
            },
        )
        return _json_text(data) if fmt == "raw" else format_recordings_list(data)

    def get_recording(self, args: dict[str, Any]) -> str:
        fmt = _normalize_format(args.get("format"))
        key = _require_recording_key(args.get("recording_key"))
        safe_key = urllib.parse.quote(key, safe="")
        data = self.get_json(f"/api/recordings/{safe_key}")
        return _json_text(data) if fmt == "raw" else format_recording(data)

    def get_transcript(self, args: dict[str, Any]) -> str:
        fmt = _normalize_format(args.get("format"))
        key = _require_recording_key(args.get("recording_key"))
        chunk = int(args.get("chunk") or 0)
        chunk_size = int(args.get("chunk_size") or 30000)
        if chunk < 0:
            raise ToolError("chunk must be 0 or a positive integer")
        safe_key = urllib.parse.quote(key, safe="")
        data = self.get_json(f"/api/recordings/{safe_key}/transcript")
        full_text = _json_text(data) if fmt == "raw" else format_transcript(data)
        chunks = _chunk_text(full_text, chunk_size)
        if chunk == 0 and len(chunks) == 1:
            return full_text
        index = 0 if chunk == 0 else chunk - 1
        if index < 0 or index >= len(chunks):
            raise ToolError(f"chunk {chunk} does not exist; total chunks: {len(chunks)}")
        return _json_text(
            {
                "result": chunks[index],
                "chunk": index + 1,
                "total_chunks": len(chunks),
                "has_more": index + 1 < len(chunks),
                "total_characters": len(full_text),
            }
        )

    def get_summary(self, args: dict[str, Any]) -> str:
        fmt = _normalize_format(args.get("format"))
        key = _require_recording_key(args.get("recording_key"))
        safe_key = urllib.parse.quote(key, safe="")
        data = self.get_json(f"/api/recordings/v2/{safe_key}/summary")
        return _json_text(data) if fmt == "raw" else format_summary(data)

    def get_summary_by_type(self, args: dict[str, Any]) -> str:
        fmt = _normalize_format(args.get("format"))
        key = _require_recording_key(args.get("recording_key"))
        summary_type = _as_text(args.get("summary_type"))
        if summary_type not in VALID_SUMMARY_TYPES:
            raise ToolError("summary_type must be shortSummary or protocol")
        safe_key = urllib.parse.quote(key, safe="")
        data = self.get_json(f"/api/recordings/{safe_key}/summary/{summary_type}")
        return _json_text(data) if fmt == "raw" else format_summary_by_type(data, summary_type)

    def list_calendar_events(self, args: dict[str, Any]) -> str:
        fmt = _normalize_format(args.get("format"))
        timezone_name = _as_text(args.get("timezone"), DEFAULT_TIMEZONE)
        start = _parse_datetime(args.get("start"), timezone_name, "start")
        end = _parse_datetime(args.get("end"), timezone_name, "end")
        if end <= start:
            raise ToolError("end must be after start")
        take = int(args.get("take") or 30)
        if take < 1 or take > 100:
            raise ToolError("take must be between 1 and 100")
        data = self.get_json(
            "/api/calendar",
            {
                "start": _api_datetime(start),
                "end": _api_datetime(end),
                "take": take,
                "roomName": args.get("room_name"),
                "ascendingOrder": "true",
            },
        )
        return _json_text(data) if fmt == "raw" else format_calendar_events(data, self.config.base_url)

    def propose_meeting(self, args: dict[str, Any]) -> str:
        title = _require_title(args.get("title"))
        description = _as_text(args.get("description")).strip()
        if len(description) > 5000:
            raise ToolError("description must be 5000 characters or less")
        timezone_name = _as_text(args.get("timezone"), DEFAULT_TIMEZONE)
        start = _parse_datetime(args.get("start"), timezone_name, "start")
        has_end = bool(_as_text(args.get("end")).strip())
        has_duration = args.get("duration_min") is not None
        if has_end == has_duration:
            raise ToolError("pass exactly one of end or duration_min")
        end = (
            _parse_datetime(args.get("end"), timezone_name, "end")
            if has_end
            else start + timedelta(minutes=_duration_minutes(args.get("duration_min")))
        )
        if end <= start:
            raise ToolError("end must be after start")

        pending_id = self._new_pending_id()
        approval_text = _as_text(args.get("approval_text")).strip()
        if approval_text and len(approval_text) > 200:
            raise ToolError("approval_text must be 200 characters or less")
        if not approval_text:
            approval_text = f"АППРУВ СОЗДАТЬ KTALK ВСТРЕЧУ {pending_id}"

        proposal = {
            "id": pending_id,
            "type": "ktalk_calendar_event",
            "created_at": _api_datetime(datetime.now(timezone.utc)),
            "title": title,
            "description": description,
            "start": _api_datetime(start),
            "end": _api_datetime(end),
            "timezone": timezone_name,
            "room_name": _normalize_room_name(args.get("room_name")),
            "allow_anonymous": _as_bool(args.get("allow_anonymous"), True),
            "approval_text": approval_text,
        }
        self._write_pending(proposal)
        return self._format_pending(proposal)

    def preview_meeting(self, args: dict[str, Any]) -> str:
        pending = self._read_pending(_require_pending_id(args.get("pending_id")))
        return self._format_pending(pending)

    def create_meeting(self, args: dict[str, Any]) -> str:
        pending = self._read_pending(_require_pending_id(args.get("pending_id")))
        if pending.get("created_result"):
            raise ToolError("KTalk meeting was already created for this pending proposal")
        approval_text = _as_text(args.get("approval_text"))
        if approval_text != pending.get("approval_text"):
            raise ToolError("approval_text does not match the pending KTalk approval phrase")

        payload = self._calendar_payload(pending)
        data = self.post_json("/api/calendar", payload)
        pending["created_result"] = {
            "created_at": _api_datetime(datetime.now(timezone.utc)),
            "event": data,
        }
        self._write_pending(pending)
        return self._format_created_event(data)

    def propose_update_meeting(self, args: dict[str, Any]) -> str:
        source_pending_id = _require_pending_id(args.get("pending_id"))
        source = self._read_pending(source_pending_id)
        event = source.get("created_result", {}).get("event")
        if not isinstance(event, dict):
            raise ToolError("KTalk meeting was not created for this pending proposal")
        event_id = _as_text(event.get("id"))
        if not event_id:
            raise ToolError("KTalk created event has no id")

        timezone_name = _as_text(args.get("timezone"), DEFAULT_TIMEZONE)
        start = _parse_datetime(args.get("start") or event.get("start"), timezone_name, "start")
        has_end = bool(_as_text(args.get("end")).strip())
        has_duration = args.get("duration_min") is not None
        if has_end and has_duration:
            raise ToolError("pass only one of end or duration_min")
        if has_end:
            end = _parse_datetime(args.get("end"), timezone_name, "end")
        elif has_duration:
            end = start + timedelta(minutes=_duration_minutes(args.get("duration_min")))
        else:
            current_start = _parse_datetime(event.get("start"), DEFAULT_TIMEZONE, "start")
            current_end = _parse_datetime(event.get("end"), DEFAULT_TIMEZONE, "end")
            end = start + (current_end - current_start)
        if end <= start:
            raise ToolError("end must be after start")

        update_id = self._new_pending_id()
        approval_text = _as_text(args.get("approval_text")).strip()
        if approval_text and len(approval_text) > 200:
            raise ToolError("approval_text must be 200 characters or less")
        if not approval_text:
            approval_text = f"АППРУВ ОБНОВИТЬ KTALK ВСТРЕЧУ {update_id}"

        proposal = {
            "id": update_id,
            "type": "ktalk_calendar_event_update",
            "created_at": _api_datetime(datetime.now(timezone.utc)),
            "source_pending_id": source_pending_id,
            "event_id": event_id,
            "title": _as_text(args.get("title") or event.get("subject") or source.get("title")),
            "description": _as_text(args.get("description") if args.get("description") is not None else source.get("description")),
            "start": _api_datetime(start),
            "end": _api_datetime(end),
            "timezone": timezone_name,
            "room_name": _normalize_room_name(args.get("room_name") or event.get("roomName") or source.get("room_name")),
            "allow_anonymous": _as_bool(args.get("allow_anonymous"), bool(source.get("allow_anonymous", True))),
            "approval_text": approval_text,
        }
        self._write_pending(proposal)
        return self._format_update_pending(proposal)

    def update_meeting(self, args: dict[str, Any]) -> str:
        pending = self._read_update_pending(_require_pending_id(args.get("pending_id")))
        if pending.get("updated_result"):
            raise ToolError("KTalk meeting was already updated for this pending proposal")
        approval_text = _as_text(args.get("approval_text"))
        if approval_text != pending.get("approval_text"):
            raise ToolError("approval_text does not match the pending KTalk approval phrase")

        payload = self._calendar_update_payload(pending)
        safe_event_id = urllib.parse.quote(_as_text(pending.get("event_id")), safe="")
        data = self.put_json(f"/api/calendar/{safe_event_id}", payload)
        pending["updated_result"] = {
            "updated_at": _api_datetime(datetime.now(timezone.utc)),
            "event": data,
        }
        self._write_pending(pending)

        source_pending_id = _as_text(pending.get("source_pending_id"))
        if source_pending_id:
            source = self._read_pending(source_pending_id)
            source["title"] = pending.get("title")
            source["description"] = pending.get("description") or ""
            source["start"] = pending.get("start")
            source["end"] = pending.get("end")
            source["room_name"] = pending.get("room_name")
            source["created_result"] = {
                "updated_at": _api_datetime(datetime.now(timezone.utc)),
                "event": data,
            }
            self._write_pending(source)
        return self._format_created_event(data).replace("Created KTalk meeting:", "Updated KTalk meeting:")

    def _calendar_payload(self, pending: dict[str, Any]) -> dict[str, Any]:
        allow_anonymous = bool(pending.get("allow_anonymous"))
        start = _parse_datetime(pending.get("start"), DEFAULT_TIMEZONE, "start")
        payload: dict[str, Any] = {
            "subject": pending.get("title"),
            "description": pending.get("description") or "",
            "start": pending.get("start"),
            "end": pending.get("end"),
            "roomName": pending.get("room_name"),
            "allowAnonymous": allow_anonymous,
            "enableSip": False,
            "enableAutoRecording": False,
            "isRecurring": False,
            "requiredAttendees": self._organizer_attendees(),
        }
        if allow_anonymous:
            template = self.get_json("/api/roomstemplate/default")
            minutes = int(template.get("anonymousAccessTimeMinutes") or 30 * 24 * 60)
            payload["anonymousAccessExpirationDate"] = _api_datetime(start + timedelta(minutes=minutes))
            masking_settings = template.get("maskingSettings")
            if isinstance(masking_settings, dict):
                payload["maskingSettings"] = masking_settings
        return payload

    def _calendar_update_payload(self, pending: dict[str, Any]) -> dict[str, Any]:
        payload = {
            "subject": pending.get("title"),
            "description": pending.get("description") or "",
            "start": pending.get("start"),
            "end": pending.get("end"),
            "roomName": pending.get("room_name"),
            "allowAnonymous": bool(pending.get("allow_anonymous")),
            "enableSip": False,
            "enableAutoRecording": False,
            "isRecurring": False,
            "requiredAttendees": self._organizer_attendees(),
            "optionalAttendees": [],
        }
        return {key: value for key, value in payload.items() if value is not None}

    def _organizer_attendees(self) -> list[dict[str, Any]]:
        context = self.get_json("/api/context")
        user = context.get("user") if isinstance(context.get("user"), dict) else {}
        key = _as_text(user.get("key") or user.get("login"))
        if not key:
            raise ToolError("KTalk context did not return current user key")
        return [{"type": "user", "key": key}]

    def _new_pending_id(self) -> str:
        for _ in range(100):
            pending_id = str(secrets.randbelow(9_000_000_000) + 1_000_000_000)
            if not os.path.exists(self._pending_path(pending_id)):
                return pending_id
        raise ToolError("could not allocate a KTalk pending id")

    def _pending_path(self, pending_id: str) -> str:
        return os.path.join(self.config.pending_dir, f"{pending_id}.json")

    def _write_pending(self, data: dict[str, Any]) -> None:
        os.makedirs(self.config.pending_dir, exist_ok=True)
        path = self._pending_path(_require_pending_id(data.get("id")))
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)

    def _read_pending(self, pending_id: str) -> dict[str, Any]:
        path = self._pending_path(pending_id)
        if not os.path.exists(path):
            raise ToolError("KTalk pending proposal not found")
        data = _read_json_file(path)
        if data.get("type") != "ktalk_calendar_event":
            raise ToolError("KTalk pending proposal has an unexpected type")
        return data

    def _read_update_pending(self, pending_id: str) -> dict[str, Any]:
        path = self._pending_path(pending_id)
        if not os.path.exists(path):
            raise ToolError("KTalk pending update proposal not found")
        data = _read_json_file(path)
        if data.get("type") != "ktalk_calendar_event_update":
            raise ToolError("KTalk pending update proposal has an unexpected type")
        return data

    def _format_pending(self, pending: dict[str, Any]) -> str:
        start = _parse_datetime(pending.get("start"), pending.get("timezone") or DEFAULT_TIMEZONE, "start")
        end = _parse_datetime(pending.get("end"), pending.get("timezone") or DEFAULT_TIMEZONE, "end")
        link = f"{self.config.base_url}/{urllib.parse.quote(_as_text(pending.get('room_name')), safe='')}"
        lines = [
            "Pending KTalk meeting:",
            f"  id: {pending.get('id')}",
            f"  title: {pending.get('title')}",
            "  time: {start}–{end} MSK".format(
                start=_display_datetime(start),
                end=end.astimezone(MSK).strftime("%H:%M"),
            ),
            "  attendees: no team attendees",
            "  KTalk invites: none; organizer is included only as the technical owner",
            f"  room: {pending.get('room_name')}",
            f"  link after create: {link}",
            f"  allow anonymous: {str(bool(pending.get('allow_anonymous'))).lower()}",
        ]
        description = _as_text(pending.get("description")).strip()
        if description:
            lines.append(f"  description: {description}")
        lines.extend(
            [
                "",
                f"Approval phrase: {pending.get('approval_text')}",
                "No KTalk write was performed.",
            ]
        )
        return "\n".join(lines)

    def _format_update_pending(self, pending: dict[str, Any]) -> str:
        start = _parse_datetime(pending.get("start"), pending.get("timezone") or DEFAULT_TIMEZONE, "start")
        end = _parse_datetime(pending.get("end"), pending.get("timezone") or DEFAULT_TIMEZONE, "end")
        link = f"{self.config.base_url}/{urllib.parse.quote(_as_text(pending.get('room_name')), safe='')}"
        lines = [
            "Pending KTalk meeting update:",
            f"  id: {pending.get('id')}",
            f"  source pending id: {pending.get('source_pending_id')}",
            f"  event id: {pending.get('event_id')}",
            f"  title: {pending.get('title')}",
            "  time: {start}–{end} MSK".format(
                start=_display_datetime(start),
                end=end.astimezone(MSK).strftime("%H:%M"),
            ),
            "  attendees: no team attendees",
            f"  room: {pending.get('room_name')}",
            f"  link: {link}",
            f"  allow anonymous: {str(bool(pending.get('allow_anonymous'))).lower()}",
        ]
        description = _as_text(pending.get("description")).strip()
        if description:
            lines.append(f"  description: {description}")
        lines.extend(
            [
                "",
                f"Approval phrase: {pending.get('approval_text')}",
                "No KTalk write was performed.",
            ]
        )
        return "\n".join(lines)

    def _format_created_event(self, data: dict[str, Any]) -> str:
        link = _meeting_link(self.config.base_url, data)
        lines = [
            "Created KTalk meeting:",
            f"  id: {_as_text(data.get('id'), '-')}",
            f"  title: {_as_text(data.get('subject') or data.get('title'), '-')}",
            f"  time: {_format_datetime(data.get('start'))}–{_format_datetime(data.get('end'))}",
            f"  room: {_as_text(data.get('roomName'), '-')}",
            f"  link: {link}",
            "  attendees: no team attendees; organizer is included only as the technical owner",
        ]
        return "\n".join(lines)


def text_schema(description: str) -> dict[str, Any]:
    return {"type": "string", "description": description}


def tool_definitions() -> list[dict[str, Any]]:
    common_format = {
        "type": "string",
        "enum": sorted(VALID_FORMATS),
        "description": "Output format. Use markdown for reading, raw for API JSON.",
        "default": "markdown",
    }
    return [
        {
            "name": "ktalk_list_recordings",
            "description": "List KTalk recordings visible to the configured session.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": text_schema("Search by title, room, or author."),
                    "start_from": text_schema("Start date/time filter, ISO 8601."),
                    "start_to": text_schema("End date/time filter, ISO 8601."),
                    "top": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 100,
                        "default": 30,
                    },
                    "order": {
                        "type": "string",
                        "default": "byTimeNewFirst",
                    },
                    "page_token": text_schema("Pagination token from a previous result."),
                    "format": common_format,
                },
                "additionalProperties": False,
            },
        },
        {
            "name": "ktalk_get_recording",
            "description": "Get metadata for one KTalk recording.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "recording_key": text_schema("Recording id/key."),
                    "format": common_format,
                },
                "required": ["recording_key"],
                "additionalProperties": False,
            },
        },
        {
            "name": "ktalk_get_transcript",
            "description": "Get a KTalk recording transcript with speaker names and timecodes.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "recording_key": text_schema("Recording id/key."),
                    "format": common_format,
                    "chunk": {
                        "type": "integer",
                        "minimum": 0,
                        "default": 0,
                        "description": "0 means auto; 1+ returns a specific chunk.",
                    },
                    "chunk_size": {
                        "type": "integer",
                        "minimum": 1000,
                        "maximum": 100000,
                        "default": 30000,
                    },
                },
                "required": ["recording_key"],
                "additionalProperties": False,
            },
        },
        {
            "name": "ktalk_get_summary",
            "description": "Get KTalk short summary and protocol for one recording.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "recording_key": text_schema("Recording id/key."),
                    "format": common_format,
                },
                "required": ["recording_key"],
                "additionalProperties": False,
            },
        },
        {
            "name": "ktalk_get_summary_by_type",
            "description": "Get one KTalk summary type: shortSummary or protocol.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "recording_key": text_schema("Recording id/key."),
                    "summary_type": {
                        "type": "string",
                        "enum": sorted(VALID_SUMMARY_TYPES),
                    },
                    "format": common_format,
                },
                "required": ["recording_key", "summary_type"],
                "additionalProperties": False,
            },
        },
        {
            "name": "ktalk_list_calendar_events",
            "description": "List KTalk calendar events visible to the configured session.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "start": text_schema("Start date/time, ISO 8601. Naive values are interpreted in MSK."),
                    "end": text_schema("End date/time, ISO 8601. Naive values are interpreted in MSK."),
                    "timezone": {
                        "type": "string",
                        "default": DEFAULT_TIMEZONE,
                        "description": "Timezone for naive start/end values. Supported: Europe/Moscow or UTC.",
                    },
                    "take": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 100,
                        "default": 30,
                    },
                    "room_name": text_schema("Optional KTalk room name filter."),
                    "format": common_format,
                },
                "required": ["start", "end"],
                "additionalProperties": False,
            },
        },
        {
            "name": "ktalk_propose_meeting",
            "description": "Create a local pending KTalk meeting proposal. Does not write to KTalk.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "title": text_schema("Meeting title."),
                    "description": text_schema("Meeting description."),
                    "start": text_schema("Start date/time, ISO 8601. Naive values are interpreted in MSK."),
                    "end": text_schema("End date/time, ISO 8601. Pass exactly one of end or duration_min."),
                    "duration_min": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 1440,
                        "description": "Meeting duration in minutes. Pass exactly one of end or duration_min.",
                    },
                    "timezone": {
                        "type": "string",
                        "default": DEFAULT_TIMEZONE,
                        "description": "Timezone for naive start/end values. Supported: Europe/Moscow or UTC.",
                    },
                    "room_name": text_schema("Optional KTalk room name. Omit to generate a safe random room."),
                    "allow_anonymous": {
                        "type": "boolean",
                        "default": True,
                        "description": "Allow joining by link. Defaults to true, matching the current room template.",
                    },
                    "approval_text": text_schema(
                        "Optional exact approval text to reuse for the create step."
                    ),
                },
                "required": ["title", "start"],
                "additionalProperties": False,
            },
        },
        {
            "name": "ktalk_preview_meeting",
            "description": "Preview a local pending KTalk meeting proposal. Does not write to KTalk.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "pending_id": text_schema("Pending KTalk proposal id."),
                },
                "required": ["pending_id"],
                "additionalProperties": False,
            },
        },
        {
            "name": "ktalk_create_meeting",
            "description": "Create a KTalk meeting from a pending proposal after exact approval.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "pending_id": text_schema("Pending KTalk proposal id."),
                    "approval_text": text_schema(
                        "Exact approval phrase shown by ktalk_propose_meeting."
                    ),
                },
                "required": ["pending_id", "approval_text"],
                "additionalProperties": False,
            },
        },
        {
            "name": "ktalk_propose_update_meeting",
            "description": "Create a local pending KTalk meeting update proposal. Does not write to KTalk.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "pending_id": text_schema("Original pending KTalk proposal id that was created."),
                    "title": text_schema("Updated meeting title. Omit to keep existing."),
                    "description": text_schema("Updated meeting description. Omit to keep existing."),
                    "start": text_schema("Updated start date/time, ISO 8601. Omit to keep existing."),
                    "end": text_schema("Updated end date/time, ISO 8601. Pass at most one of end or duration_min."),
                    "duration_min": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 1440,
                        "description": "Updated duration in minutes. Pass at most one of end or duration_min.",
                    },
                    "timezone": {
                        "type": "string",
                        "default": DEFAULT_TIMEZONE,
                        "description": "Timezone for naive start/end values. Supported: Europe/Moscow or UTC.",
                    },
                    "room_name": text_schema("Optional KTalk room name. Omit to keep existing."),
                    "allow_anonymous": {
                        "type": "boolean",
                        "default": True,
                        "description": "Allow joining by link.",
                    },
                    "approval_text": text_schema("Optional exact approval text to reuse for the update step."),
                },
                "required": ["pending_id"],
                "additionalProperties": False,
            },
        },
        {
            "name": "ktalk_update_meeting",
            "description": "Update a KTalk meeting from a pending update proposal after exact approval.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "pending_id": text_schema("Pending KTalk update proposal id."),
                    "approval_text": text_schema(
                        "Exact approval phrase shown by ktalk_propose_update_meeting."
                    ),
                },
                "required": ["pending_id", "approval_text"],
                "additionalProperties": False,
            },
        },
    ]


class MCPServer:
    def __init__(self, config_path: str) -> None:
        self.config_path = config_path
        self.client: Optional[KTalkClient] = None

    def _client(self) -> KTalkClient:
        if self.client is None:
            self.client = KTalkClient(load_config(self.config_path))
        return self.client

    def handle_request(self, message: dict[str, Any]) -> Optional[dict[str, Any]]:
        request_id = message.get("id")
        method = _as_text(message.get("method"))
        params = message.get("params") if isinstance(message.get("params"), dict) else {}

        if method.startswith("notifications/"):
            return None

        try:
            if method == "initialize":
                result = {
                    "protocolVersion": params.get("protocolVersion") or "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
                }
                return self._response(request_id, result)
            if method == "tools/list":
                return self._response(request_id, {"tools": tool_definitions()})
            if method == "tools/call":
                return self._response(request_id, self._call_tool(params))
            if method == "ping":
                return self._response(request_id, {})
            return self._error(request_id, -32601, f"Method not found: {method}")
        except (ConfigError, ToolError) as exc:
            return self._response(
                request_id,
                {
                    "content": [{"type": "text", "text": str(exc)}],
                    "isError": True,
                },
            )
        except Exception as exc:  # noqa: BLE001 - keep details token-safe.
            return self._response(
                request_id,
                {
                    "content": [
                        {"type": "text", "text": f"Internal error: {type(exc).__name__}"}
                    ],
                    "isError": True,
                },
            )

    def _call_tool(self, params: dict[str, Any]) -> dict[str, Any]:
        name = _as_text(params.get("name"))
        args = params.get("arguments") if isinstance(params.get("arguments"), dict) else {}
        if name not in {
            "ktalk_list_recordings",
            "ktalk_get_recording",
            "ktalk_get_transcript",
            "ktalk_get_summary",
            "ktalk_get_summary_by_type",
            "ktalk_list_calendar_events",
            "ktalk_propose_meeting",
            "ktalk_preview_meeting",
            "ktalk_create_meeting",
            "ktalk_propose_update_meeting",
            "ktalk_update_meeting",
        }:
            raise ToolError(f"Unknown tool: {name}")

        client = self._client()
        handlers: dict[str, Callable[[dict[str, Any]], str]] = {
            "ktalk_list_recordings": client.list_recordings,
            "ktalk_get_recording": client.get_recording,
            "ktalk_get_transcript": client.get_transcript,
            "ktalk_get_summary": client.get_summary,
            "ktalk_get_summary_by_type": client.get_summary_by_type,
            "ktalk_list_calendar_events": client.list_calendar_events,
            "ktalk_propose_meeting": client.propose_meeting,
            "ktalk_preview_meeting": client.preview_meeting,
            "ktalk_create_meeting": client.create_meeting,
            "ktalk_propose_update_meeting": client.propose_update_meeting,
            "ktalk_update_meeting": client.update_meeting,
        }
        return {"content": [{"type": "text", "text": handlers[name](args)}]}

    @staticmethod
    def _response(request_id: Any, result: Any) -> dict[str, Any]:
        return {"jsonrpc": "2.0", "id": request_id, "result": result}

    @staticmethod
    def _error(request_id: Any, code: int, message: str) -> dict[str, Any]:
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": code, "message": message},
        }


def read_message() -> Optional[dict[str, Any]]:
    headers: dict[str, str] = {}
    while True:
        line = sys.stdin.buffer.readline()
        if line == b"":
            return None
        if line in (b"\r\n", b"\n"):
            break
        name, _, value = line.decode("ascii", errors="replace").partition(":")
        headers[name.lower()] = value.strip()

    length_text = headers.get("content-length")
    if not length_text:
        return None
    try:
        length = int(length_text)
    except ValueError:
        return None
    payload = sys.stdin.buffer.read(length)
    if not payload:
        return None
    data = json.loads(payload.decode("utf-8"))
    if not isinstance(data, dict):
        return None
    return data


def write_message(message: dict[str, Any]) -> None:
    payload = json.dumps(message, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    sys.stdout.buffer.write(f"Content-Length: {len(payload)}\r\n\r\n".encode("ascii"))
    sys.stdout.buffer.write(payload)
    sys.stdout.buffer.flush()


def serve(config_path: str) -> None:
    server = MCPServer(config_path=config_path)
    while True:
        message = read_message()
        if message is None:
            return
        response = server.handle_request(message)
        if response is not None:
            write_message(response)


def main() -> None:
    parser = argparse.ArgumentParser(description="Project-local KTalk MCP server")
    parser.add_argument("--config", default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--check-config", action="store_true")
    args = parser.parse_args()

    if args.check_config:
        config = load_config(args.config)
        host = urllib.parse.urlparse(config.base_url).hostname or "-"
        print(f"OK: KTalk config loaded for host {host}")
        return

    serve(args.config)


if __name__ == "__main__":
    main()
