#!/usr/bin/env python3
"""OSINT: seeds + DuckDuckGo HTML search → candidate @usernames (no LLM)."""
from __future__ import annotations

import json
import re
import subprocess
import sys
import urllib.parse
from pathlib import Path

DENY_SUB = (
    "bot",
    "courses",
    "course",
    "curator",
    "channel",
    "subscribe",
    "marie_",
    "tutoronline_courses",
    "tutoronline_math",
    "math_tutoronline",
    "olga_math",
    "_bot",
)
SKIP_FETCH_HOST = (
    "instagram.com",
    "facebook.com",
    "linkedin.com",
    "twitter.com",
    "x.com",
    "youtube.com",
    "tiktok.com",
)
HR_HINTS = (
    "рекрут",
    "recruit",
    " hr",
    "hr ",
    "кадр",
    "talent",
    "hiring",
    "ваканс",
    "job",
    "карьер",
    "career",
    "отклик",
)

USER_RE = r"[A-Za-z][A-Za-z0-9_]{4,31}"


def company_key(name: str) -> str:
    k = re.sub(r"[^a-z0-9]+", "-", name.casefold().strip())
    return k.strip("-") or "unknown"


def load_seeds(root: Path) -> dict:
    path = root / "data" / "company-seeds.json"
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_seed_entry(seeds: dict, company: str) -> tuple[str | None, dict | None]:
    key = company_key(company)
    if key in seeds:
        return key, seeds[key]
    cf = company.casefold()
    for k, entry in seeds.items():
        names = [k.replace("-", " ")] + list(entry.get("aliases") or [])
        for alias in names:
            a = str(alias).casefold()
            if a == cf or a in cf or cf in a:
                return k, entry
    return None, None


def curl_get(url: str, timeout: int = 20) -> str:
    try:
        return subprocess.check_output(
            [
                "curl",
                "-sfL",
                "--max-time",
                str(timeout),
                "-A",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) recruiter-osint/2.0",
                url,
            ],
            stderr=subprocess.DEVNULL,
        ).decode("utf-8", errors="ignore")
    except subprocess.CalledProcessError:
        return ""


def ddg_search(query: str) -> tuple[list[str], str]:
    try:
        html = subprocess.check_output(
            [
                "curl",
                "-sfL",
                "--max-time",
                "25",
                "-A",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) recruiter-osint/2.0",
                "-d",
                f"q={urllib.parse.quote(query)}",
                "https://html.duckduckgo.com/html/",
            ],
            stderr=subprocess.DEVNULL,
        ).decode("utf-8", errors="ignore")
    except subprocess.CalledProcessError:
        return [], ""
    urls = re.findall(r'class="result__a"[^>]*href="([^"]+)"', html)
    return urls, html


def extract_usernames(text: str) -> list[str]:
    found: list[str] = []
    for m in re.finditer(rf"https?://t\.me/({USER_RE})", text, re.I):
        found.append(m.group(1))
    for m in re.finditer(rf"(?<![A-Za-z0-9_])@({USER_RE})", text):
        found.append(m.group(1))
    return found


def deny(username: str) -> bool:
    low = username.casefold()
    return any(d in low for d in DENY_SUB)


def should_skip_url(url: str) -> bool:
    try:
        host = urllib.parse.urlparse(url).netloc.casefold()
    except Exception:
        return True
    if not host:
        return True
    if "t.me" in host or "telegram.me" in host:
        u = url.casefold()
        if "/+" in u or "/joinchat" in u or "/s/" in u:
            return True
        return False
    return any(h in host for h in SKIP_FETCH_HOST)


def company_context(text: str, company: str) -> bool:
    t = text.casefold()
    c = company.casefold()
    if c in t:
        return True
    for part in c.split():
        if len(part) > 3 and part in t:
            return True
    return False


def hr_context(text: str) -> bool:
    t = text.casefold()
    return any(h in t for h in HR_HINTS)


def add_candidate(
    pool: dict[str, dict],
    username: str,
    *,
    score: int,
    source: str,
    reason: str,
) -> None:
    if deny(username):
        return
    u = username
    prev = pool.get(u)
    meta = {
        "username": u,
        "score": score,
        "source": source,
        "reason": reason,
    }
    if prev is None or meta["score"] > prev["score"]:
        pool[u] = meta


def discover(
    root: Path,
    company: str,
    extra_url: str,
    max_page_fetches: int = 12,
) -> list[dict]:
    pool: dict[str, dict] = {}
    seeds = load_seeds(root)
    seed_key, seed_entry = resolve_seed_entry(seeds, company)

    if seed_entry:
        for lead in seed_entry.get("leads") or []:
            user = (lead.get("username") or "").strip().lstrip("@")
            if not user:
                continue
            src = lead.get("source_url") or f"seed:{seed_key}"
            note = lead.get("source_note") or lead.get("label") or "curated seed"
            add_candidate(
                pool,
                user,
                score=100,
                source=src,
                reason=f"seed ({note})",
            )

    if extra_url:
        html = curl_get(extra_url) if extra_url.startswith(("http://", "https://", "file:")) else ""
        if extra_url.startswith("file:"):
            try:
                fp = urllib.parse.urlparse(extra_url).path
                html = Path(fp).read_text(encoding="utf-8", errors="ignore")
            except OSError:
                html = ""
        if html:
            for user in extract_usernames(html):
                sc = 90 if company_context(html, company) else 70
                add_candidate(pool, user, score=sc, source=extra_url, reason="--url page")

    queries = [
        f'"{company}" рекрутер telegram',
        f'"{company}" HR telegram t.me',
        f"{company} вакансия telegram @",
    ]
    fetch_urls: list[str] = []
    seen_url: set[str] = set()

    for q in queries:
        result_urls, ddg_html = ddg_search(q)
        for user in extract_usernames(ddg_html):
            if company_context(ddg_html, company):
                add_candidate(
                    pool,
                    user,
                    score=45,
                    source=f"ddg:{q}",
                    reason="snippet",
                )
        for url in result_urls:
            if url in seen_url:
                continue
            seen_url.add(url)
            if "t.me" in url or "telegram.me" in url:
                for user in extract_usernames(url):
                    add_candidate(
                        pool,
                        user,
                        score=35,
                        source=url,
                        reason="ddg t.me link",
                    )
                continue
            if should_skip_url(url):
                continue
            fetch_urls.append(url)

    for url in fetch_urls[:max_page_fetches]:
        html = curl_get(url)
        if not html:
            continue
        if not company_context(html, company):
            continue
        base = 55 if hr_context(html) else 50
        for user in extract_usernames(html):
            add_candidate(
                pool,
                user,
                score=base + (10 if hr_context(html) else 0),
                source=url,
                reason="fetched page",
            )

    ordered = sorted(pool.values(), key=lambda x: (-x["score"], x["username"].casefold()))
    return ordered


def main() -> None:
    if len(sys.argv) < 3:
        print("Usage: discover.py ROOT COMPANY [EXTRA_URL]", file=sys.stderr)
        sys.exit(2)
    root = Path(sys.argv[1])
    company = sys.argv[2]
    extra = sys.argv[3] if len(sys.argv) > 3 else ""
    out = discover(root, company, extra)
    print(json.dumps({"company": company, "candidates": out}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()