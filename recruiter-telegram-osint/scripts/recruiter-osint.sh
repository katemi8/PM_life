#!/usr/bin/env bash
# Поиск живого Telegram рекрутера по компании — одна команда, без LLM.
# Источники: company-seeds.json → веб-поиск (DDG) → опционально hh (RECRUITER_USE_HH=1).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CACHE="$ROOT/data/recruiter-cache.json"
VERIFY="$ROOT/scripts/verify-telegram.sh"
DISCOVER="$ROOT/scripts/discover.py"
COMPANY=""
EXTRA_URL=""
REFRESH=0

usage() {
  cat >&2 <<'EOF'
Usage:
  recruiter-osint.sh "Название компании"
  recruiter-osint.sh "Название" --url 'https://…'
  recruiter-osint.sh "Название" --refresh

По умолчанию hh.ru не дергаем (там редко есть TG). Включить: export RECRUITER_USE_HH=1
Stdout: JSON. Кэш: data/recruiter-cache.json
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --url)
      EXTRA_URL="${2:-}"
      shift 2
      ;;
    --refresh)
      REFRESH=1
      shift
      ;;
    -h | --help)
      usage
      exit 0
      ;;
    *)
      if [[ -z "$COMPANY" ]]; then
        COMPANY="$1"
      else
        echo "Unknown arg: $1" >&2
        usage
        exit 1
      fi
      shift
      ;;
  esac
done

[[ -n "$COMPANY" ]] || {
  usage
  exit 1
}

mkdir -p "$ROOT/data"
[[ -f "$CACHE" ]] || echo '{}' >"$CACHE"

cache_key="$(python3 -c "import re,sys; k=re.sub(r'[^a-z0-9]+','-',sys.argv[1].casefold().strip()); print(k.strip('-') or 'unknown')" "$COMPANY")"

if [[ "$REFRESH" -eq 0 ]]; then
  if python3 - "$CACHE" "$cache_key" <<'PY'
import json, sys
from pathlib import Path
cache = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
hit = cache.get(sys.argv[2])
if hit and hit.get("contacts"):
    print(json.dumps(hit, ensure_ascii=False, indent=2))
    sys.exit(0)
sys.exit(1)
PY
  then
    echo "(from cache, use --refresh)" >&2
    exit 0
  fi
fi

tmpdir="$(mktemp -d)"
trap 'rm -rf "$tmpdir"' EXIT

python3 "$DISCOVER" "$ROOT" "$COMPANY" "$EXTRA_URL" >"$tmpdir/discover.json"

python3 - "$tmpdir/discover.json" >"$tmpdir/candidates.txt" <<'PY'
import json, sys
from pathlib import Path
data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
for c in data.get("candidates") or []:
    print(c["username"])
PY

# Опционально hh.ru (по умолчанию выключено)
HH_UA="${HH_USER_AGENT:-recruiter-osint/2.0 (osint@local)}"
if [[ "${RECRUITER_USE_HH:-0}" == "1" ]]; then
  FETCH_N=0
  fetch() {
    local url="$1"
    FETCH_N=$((FETCH_N + 1))
    curl -sfL --max-time 20 -A "${HH_UA}" "$url" \
      -o "$tmpdir/fetch_${FETCH_N}.html" 2>/dev/null || true
  }
  quoted="$(python3 -c "import urllib.parse,sys; print(urllib.parse.quote(sys.argv[1]))" "$COMPANY")"
  emp_json="$(curl -sfL --max-time 20 -H "User-Agent: ${HH_UA}" \
    "https://api.hh.ru/employers?text=${quoted}&per_page=5" 2>/dev/null || echo '{"items":[]}')"
  echo "$emp_json" >"$tmpdir/employers.json"
  emp_id=""
  if python3 -c "import json;print(len(json.load(open('$tmpdir/employers.json')).get('items',[])))" | grep -qv '^0$'; then
    emp_id="$(python3 - "$tmpdir/employers.json" "$COMPANY" <<'PY'
import json, sys
from pathlib import Path
data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
company = sys.argv[2].casefold()
best, best_score = None, -1
for it in data.get("items") or []:
    name = (it.get("name") or "").casefold()
    score = 100 if name == company else (50 if company in name or name in company else 0)
    if score > best_score:
        best_score, best = score, it
if best and best_score >= 50:
    print(best.get("id"))
PY
)"
  fi
  if [[ -n "$emp_id" ]]; then
    fetch "https://hh.ru/employer/${emp_id}"
    fetch "https://hh.ru/search/vacancy?employer_id=${emp_id}&per_page=20"
    python3 - "$tmpdir" >>"$tmpdir/candidates.txt" <<'PY'
import re, sys
from pathlib import Path
deny = ("bot", "courses", "curator", "channel", "subscribe")
for path in Path(sys.argv[1]).glob("*.html"):
    text = path.read_text(encoding="utf-8", errors="ignore")
    found = set()
    for m in re.finditer(r"https?://t\.me/([A-Za-z][A-Za-z0-9_]{4,31})", text, re.I):
        found.add(m.group(1))
    for m in re.finditer(r"(?<![A-Za-z0-9_])@([A-Za-z][A-Za-z0-9_]{4,31})", text):
        found.add(m.group(1))
    for u in found:
        low = u.casefold()
        if any(d in low for d in deny):
            continue
        print(u)
PY
  fi
fi

python3 - "$tmpdir/discover.json" "$tmpdir/candidates.txt" >"$tmpdir/ordered.txt" <<'PY'
import json, sys
from pathlib import Path
disc = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
raw = Path(sys.argv[2]).read_text(encoding="utf-8").splitlines()
prio = {c["username"].casefold(): i for i, c in enumerate(disc.get("candidates") or [])}
spell = {c["username"].casefold(): c["username"] for c in disc.get("candidates") or []}
n = len(prio)
for line in raw:
    u = line.strip()
    if not u:
        continue
    k = u.casefold()
    if k not in prio:
        prio[k] = n
        spell[k] = u
        n += 1
for k in sorted(prio.keys(), key=lambda x: prio[x]):
    print(spell[k])
PY

candidates=()
while IFS= read -r line || [[ -n "$line" ]]; do
  [[ -n "$line" ]] && candidates+=("$line")
done <"$tmpdir/ordered.txt"

empty_result() {
  python3 - "$COMPANY" <<'PY'
import json, datetime, sys
print(json.dumps({
  "company": sys.argv[1],
  "queried_at": datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat(),
  "hh_employer_id": None,
  "contacts": [],
  "hint": "Добавьте компанию в data/company-seeds.json (username + ссылка-источник) или найдите пост с @ником.",
}, ensure_ascii=False, indent=2))
PY
}

if [[ ${#candidates[@]} -eq 0 ]]; then
  echo "Нет кандидатов. Можно дописать data/company-seeds.json или --url 'file://…'" >&2
  empty_result
  exit 1
fi

"$VERIFY" "${candidates[@]}" >"$tmpdir/verified.json"

python3 - "$COMPANY" "$EXTRA_URL" "$tmpdir/discover.json" "$tmpdir/verified.json" >"$tmpdir/result.json" <<'PY'
import json, datetime, sys
from pathlib import Path

company, extra, disc_path, vpath = sys.argv[1:5]
disc = json.loads(Path(disc_path).read_text(encoding="utf-8"))
meta = {c["username"].casefold(): c for c in disc.get("candidates") or []}
verified = json.loads(Path(vpath).read_text(encoding="utf-8"))
alive = [v for v in verified if v.get("alive")]
for v in alive:
    m = meta.get(v["username"].casefold(), {})
    v["source_url"] = m.get("source")
    v["match_reason"] = m.get("reason")
    v["score"] = m.get("score", 0)
alive.sort(key=lambda x: (-(x.get("score") or 0), x.get("username", "").casefold()))
top = alive[0].get("score") or 0 if alive else 0
# не сыпем лишние TG: при уверенном seed (90+) — только один ник
if top >= 90:
    alive = alive[:1]
else:
    alive = [v for v in alive if (v.get("score") or 0) >= top - 10][:2]
out = {
  "company": company,
  "queried_at": datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat(),
  "hh_employer_id": None,
  "extra_url": extra or None,
  "best_contact": alive[0] if alive else None,
  "contacts": alive,
  "rejected_usernames": [v for v in verified if not v.get("alive")],
}
print(json.dumps(out, ensure_ascii=False))
PY

if [[ "$(python3 -c "import json;print(len(json.load(open('$tmpdir/result.json')).get('contacts',[])))")" -eq 0 ]]; then
  echo "Кандидаты были, но t.me не подтвердил — проверьте отклонённые ники в rejected_usernames" >&2
  python3 -m json.tool <"$tmpdir/result.json"
  exit 1
fi

python3 -m json.tool <"$tmpdir/result.json"

python3 - "$CACHE" "$cache_key" "$tmpdir/result.json" <<'PY'
import json, sys
from pathlib import Path
cache_path, key, result_path = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
cache = json.loads(cache_path.read_text(encoding="utf-8"))
cache[key] = json.loads(result_path.read_text(encoding="utf-8"))
cache_path.write_text(json.dumps(cache, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
PY