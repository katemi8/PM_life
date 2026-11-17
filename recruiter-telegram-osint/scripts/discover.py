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
    "hirehi_official",
    "generalsupport",
    "jun_hi",
    "hirify",
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
HR_VACANCY_CHANNELS = (
    "hrhubvacancy",
    "hrhubvacancy300",
    "hrhubjunior",
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
# Ложные срабатывания из CSS/JSON-LD (@media, @context, …)
FALSE_AT = frozenset(
    {
        "media",
        "context",
        "keyframes",
        "graph",
        "import",
        "charset",
        "supports",
        "layer",
        "container",
        "scope",
        "page",
        "namespace",
        "counter",
        "property",
        "font",
        "document",
        "viewport",
        "hrhub",
        "hrhubvacancy",
        "hrhubvacancy300",
        "hrhubjunior",
        "hrhublibrary",
        "hrhubresume",
    }
)


def company_key(name: str) -> str:
    k = re.sub(r"[^a-z0-9а-яё]+", "-", name.casefold().strip())
    return k.strip("-") or "unknown"


def load_network(root: Path) -> list[dict]:
    path = root / "data" / "network-contacts.json"
    if not path.is_file():
        return []
    return json.loads(path.read_text(encoding="utf-8")).get("contacts") or []


def network_role_score(role: str) -> int:
    r = (role or "").casefold()
    if any(x in r for x in ("hr", "рекрут", "talent", "кадр", "hiring")):
        return 92
    if any(x in r for x in ("cpo", "head of", "директор", "lead", "руковод")):
        return 91
    if any(x in r for x in ("product", "продакт", "проджект", "pm ", " pm")):
        return 90
    return 88


def network_company_match(company: str, contact: dict) -> bool:
    ck = company_key(company)
    if ck in (contact.get("company_keys") or []):
        return True
    cf = company.casefold().strip()
    comp = (contact.get("company") or "").casefold().strip()
    if not comp:
        return False
    if comp == cf or comp in cf or cf in comp:
        return True
    for part in cf.split():
        if len(part) > 2 and part in comp:
            return True
    return False


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


def extract_usernames_near(text: str, company: str, window: int = 400) -> list[str]:
    """@ и t.me только рядом с названием компании (не CSS со всей страницы)."""
    t = text
    low = text.casefold()
    c = company.casefold()
    found: list[str] = []
    for m in re.finditer(rf"(?<![A-Za-z0-9_])@({USER_RE})", t):
        user = m.group(1)
        if user.casefold() in FALSE_AT:
            continue
        start = max(0, m.start() - window)
        end = min(len(t), m.end() + window)
        chunk = low[start:end]
        if c in chunk or any(p in chunk for p in c.split() if len(p) > 2):
            found.append(user)
    for m in re.finditer(rf"https?://t\.me/({USER_RE})", t, re.I):
        user = m.group(1)
        if user.casefold() in FALSE_AT:
            continue
        start = max(0, m.start() - window)
        end = min(len(t), m.end() + window)
        chunk = low[start:end]
        if c in chunk or any(p in chunk for p in c.split() if len(p) > 2):
            found.append(user)
    return found


def deny(username: str) -> bool:
    low = username.casefold()
    if low in FALSE_AT:
        return True
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


def chunk_near_username(text: str, username: str, window: int = 500) -> str:
    t = text
    low = text.casefold()
    u = username.casefold()
    for m in re.finditer(rf"@({USER_RE})", t, re.I):
        if m.group(1).casefold() != u:
            continue
        start = max(0, m.start() - window)
        end = min(len(t), m.end() + window)
        return low[start:end]
    for m in re.finditer(rf"t\.me/{re.escape(username)}", t, re.I):
        start = max(0, m.start() - window)
        end = min(len(t), m.end() + window)
        return low[start:end]
    return ""


def hr_channel_resume_score(chunk: str) -> int:
    if not chunk:
        return 93
    if any(x in chunk for x in ("резюме", "резюм", "в лс", " в лс", "напишите", "пишите")):
        return 98
    return 93


def scan_hr_vacancy_channels(pool: dict[str, dict], company: str) -> None:
    """Посты HR-каналов (как KION в @hrhubvacancy): DDG → t.me/s/… → @ рядом с компанией."""
    for channel in HR_VACANCY_CHANNELS:
        base = f"https://t.me/s/{channel}"
        queries = [
            f"{company} {channel} telegram",
            f"{company} {channel} рекрутер",
            f"{company} {channel} резюме",
        ]
        fetch_urls = [base]
        for q in queries:
            urls, ddg_html = ddg_search(q)
            for user in extract_usernames_near(ddg_html, company, window=600):
                if hr_context(ddg_html):
                    add_candidate(
                        pool,
                        user,
                        score=94,
                        source=f"ddg:{q}",
                        reason="hrhub ddg snippet",
                        role="рекрутер (HR-канал)",
                    )
            for url in urls:
                if "t.me/s/" in url:
                    if channel in url or channel in url.casefold():
                        fetch_urls.append(url.split("&")[0])
        for url in dict.fromkeys(fetch_urls):
            html = curl_get(url)
            if not html or not company_context(html, company):
                continue
            for user in extract_usernames_near(html, company, window=700):
                if deny(user):
                    continue
                chunk = chunk_near_username(html, user)
                if not chunk or not hr_context(chunk):
                    continue
                sc = hr_channel_resume_score(chunk)
                add_candidate(
                    pool,
                    user,
                    score=sc,
                    source=url,
                    reason=f"HR-канал @{channel}",
                    role="рекрутер (HR-канал)",
                )


def add_candidate(
    pool: dict[str, dict],
    username: str,
    *,
    score: int,
    source: str,
    reason: str,
    role: str = "",
    display_name: str = "",
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
        "role": role,
        "display_name": display_name,
    }
    if prev is None or meta["score"] > prev["score"]:
        pool[u] = meta


def discover(
    root: Path,
    company: str,
    extra_url: str,
) -> list[dict]:
    pool: dict[str, dict] = {}
    seeds = load_seeds(root)
    seed_key, seed_entry = resolve_seed_entry(seeds, company)

    for contact in load_network(root):
        if not network_company_match(company, contact):
            continue
        user = (contact.get("username") or "").strip()
        if not user:
            continue
        role = str(contact.get("role") or "—")
        add_candidate(
            pool,
            user,
            score=network_role_score(role),
            source=contact.get("source") or "network-contacts.json",
            reason=contact.get("source_note") or "network",
            role=role,
            display_name=str(contact.get("name") or ""),
        )

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
                role=str(lead.get("label") or ""),
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

    scan_hr_vacancy_channels(pool, company)

    # Только узкие запросы (без обхода случайных сайтов и hh/hirify)
    queries = [
        f'site:hirehi.ru "{company}" telegram',
        f'site:linkedin.com "{company}" ("Tg" OR telegram OR @)',
        f'site:t.me "{company}" (вакансия OR HR OR рекрут)',
    ]
    for q in queries:
        _, ddg_html = ddg_search(q)
        for user in extract_usernames_near(ddg_html, company, window=500):
            if not hr_context(ddg_html):
                continue
            add_candidate(
                pool,
                user,
                score=55,
                source=f"ddg:{q}",
                reason="ddg snippet",
            )

    slug = company_key(company)
    for hire_slug in dict.fromkeys((slug, company.casefold().strip())):
        if not hire_slug or not re.fullmatch(r"[a-z0-9-]+", hire_slug):
            continue
        hirehi = curl_get(f"https://hirehi.ru/companies/{hire_slug}")
        if not hirehi or not company_context(hirehi, company):
            continue
        for user in extract_usernames_near(hirehi, company):
            if not hr_context(hirehi):
                continue
            add_candidate(
                pool,
                user,
                score=75,
                source=f"https://hirehi.ru/companies/{hire_slug}",
                reason="hirehi company page",
            )
    q_html = curl_get(f"https://hirehi.ru/?q={urllib.parse.quote(company)}")
    if q_html:
        for user in extract_usernames_near(q_html, company):
            if not hr_context(q_html):
                continue
            add_candidate(
                pool,
                user,
                score=70,
                source=f"https://hirehi.ru/?q={company}",
                reason="hirehi search",
            )

    ordered = sorted(pool.values(), key=lambda x: (-x["score"], x["username"].casefold()))
    return ordered[:8]


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