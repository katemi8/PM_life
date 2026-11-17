#!/usr/bin/env bash
# Проверка, что Telegram username живой (по публичной странице t.me).
# Вывод: JSON-массив.
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo 'Usage: verify-telegram.sh user1 [user2 ...]' >&2
  exit 1
fi

python3 - "$@" <<'PY'
import json, re, subprocess, sys

def normalize(raw: str) -> str:
    s = raw.strip()
    s = re.sub(r"^https?://t\.me/", "", s, flags=re.I)
    s = s.lstrip("@")
    s = s.split("/")[0].split("?")[0]
    return s

def check(username: str) -> dict:
    title = ""
    description = ""
    alive = False
    try:
        html = subprocess.check_output(
            ["curl", "-sfL", "--max-time", "15", f"https://t.me/{username}"],
            stderr=subprocess.DEVNULL,
        ).decode("utf-8", errors="ignore")
    except subprocess.CalledProcessError:
        return {"username": username, "alive": False, "title": "", "description": ""}

    if "If you have Telegram" in html:
        return {"username": username, "alive": False, "title": "", "description": ""}

    m = re.search(
        r'<div class="tgme_page_title"[^>]*><span dir="auto">([^<]*)</span>', html
    )
    if m:
        title = m.group(1)
    m = re.search(r'<meta property="og:description" content="([^"]*)"', html)
    if m:
        description = m.group(1)
    has_photo = "tgme_page_photo_image" in html
    alive = bool(title or has_photo)
    if description and not description.startswith("You can contact @"):
        alive = True
    return {
        "username": username,
        "alive": alive,
        "title": title,
        "description": description,
    }

users = [normalize(a) for a in sys.argv[1:]]
out = [check(u) for u in users if u]
print(json.dumps(out, ensure_ascii=False))
PY