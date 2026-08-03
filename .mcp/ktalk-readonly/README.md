# KTalk MCP

Project-local MCP server for reading Kontur Talk recordings and creating or
updating guarded KTalk calendar meetings through a browser `sessionToken`. It is
intentionally small and dependency-free: only Python standard library is used.

## Security model

- Recording tools are read-only.
- Meeting creation and update are guarded: proposal tools write only a local
  pending JSON file, and write tools perform the external POST only when
  `approval_text` exactly matches the phrase stored in that pending file.
- No delete or download-to-disk actions are exposed.
- No `.env` loading. Secrets come from an ignored local JSON config or process
  environment.
- HTTPS is required.
- HTTP redirects are refused so `sessionToken` is not forwarded to another host.
- `recording_key` is validated and URL-encoded before it is placed in an API path.
- KTalk pending ids and room names are validated before being used in paths or
  meeting links.
- Tool errors do not print the request URL or token.

The `sessionToken` is still a browser session cookie. Treat it as a personal
secret and rotate it when access is no longer needed.

## Local config

Create `.claude/local/ktalk-session.json`:

```json
{
  "base_url": "https://your-domain.ktalk.ru",
  "allowed_hosts": ["your-domain.ktalk.ru"],
  "session_token": "REPLACE_ME",
  "timeout_seconds": 30
}
```

`.claude/local/` is already ignored by git in this repository.

## MCP config

Project `.mcp.json` entry:

```json
{
  "mcpServers": {
    "ktalk": {
      "command": "python",
      "args": [
        ".mcp/ktalk-readonly/server.py",
        "--config",
        ".claude/local/ktalk-session.json"
      ]
    }
  }
}
```

## Tools

Read:

- `ktalk_list_recordings`
- `ktalk_get_recording`
- `ktalk_get_transcript`
- `ktalk_get_summary`
- `ktalk_get_summary_by_type`
- `ktalk_list_calendar_events`

Guarded write:

- `ktalk_propose_meeting`
- `ktalk_preview_meeting`
- `ktalk_create_meeting`
- `ktalk_propose_update_meeting`
- `ktalk_update_meeting`

Use `format: "markdown"` for reading and `format: "raw"` when the original API
JSON is needed.

For the Yandex Calendar workflow, pass the Yandex approval phrase as
`approval_text` to `ktalk_propose_meeting`. Then the single user approval phrase
shown in the combined preview can authorize the KTalk create step and the
Yandex create step for that same preview.

## Calendar API notes

The create path intentionally follows the constraints observed against the
current KTalk API:

- Send `start` and `end` as UTC ISO strings.
- Do not send `timezone` in `POST /api/calendar`; `Europe/Moscow` can fail with
  `CalendarTimeZoneParse`.
- Omit fields whose value is `null`.
- Fetch `/api/context` before create and include the current user only as the
  technical organizer when the API requires `requiredAttendees`.
- Fetch `/api/roomstemplate/default` before create and reuse its anonymous
  expiration/masking settings.
- If a write fails, fix the cause and request a fresh exact approval before
  retrying `ktalk_create_meeting`.

After a KTalk meeting is created, Yandex Calendar readback may show an extra
same-time event whose UID starts with `talk-`. That is the automatic KTalk ICS
event, not a duplicate created by `yandex_calendar_write.py`.
