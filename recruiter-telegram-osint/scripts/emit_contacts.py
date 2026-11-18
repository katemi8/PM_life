#!/usr/bin/env python3
"""Краткий stdout: список контактов с типом и источником."""
from __future__ import annotations

import json
import sys
from pathlib import Path


def iter_contacts(hit: dict):
    """best_contact, затем alternates; из contacts, если старый кэш."""
    best = hit.get("best_contact")
    alts = list(hit.get("alternates") or [])
    if not best and hit.get("contacts"):
        all_c = hit["contacts"]
        best = all_c[0]
        alts = all_c[1:]
    seen: set[str] = set()
    if best:
        seen.add(best["username"].casefold())
        yield best, True
    for a in alts:
        u = a.get("username")
        if not u:
            continue
        k = u.casefold()
        if k in seen:
            continue
        seen.add(k)
        yield a, False


def format_source(c: dict) -> str:
    reason = (c.get("match_reason") or "—").strip()
    url = (c.get("source_url") or "").strip()
    if not url:
        return reason
    if url in reason:
        return reason
    return f"{reason} | {url}"


def emit_contacts(hit: dict) -> bool:
    company = (hit.get("company") or "").strip()
    if company:
        print(f"Компания: {company}")
        print()

    items = list(iter_contacts(hit))
    if not items:
        return False

    for i, (c, is_best) in enumerate(items, 1):
        u = c["username"]
        name = (c.get("display_name") or c.get("title") or "").strip() or "—"
        role = (c.get("role") or "").strip() or "—"
        kind = (c.get("contact_type") or "контакт").strip()
        star = " ★" if is_best else ""
        print(f"{i}. @{u}{star}")
        print(f"   {name}, {role}")
        print(f"   тип: {kind}")
        print(f"   источник: {format_source(c)}")
        print(f"   https://t.me/{u}")
        if i < len(items):
            print()
    return True


def main() -> int:
    path = Path(sys.argv[1])
    hit = json.loads(path.read_text(encoding="utf-8"))
    return 0 if emit_contacts(hit) else 1


if __name__ == "__main__":
    raise SystemExit(main())