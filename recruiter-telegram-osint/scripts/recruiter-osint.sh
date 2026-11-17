#!/usr/bin/env bash
# Поиск публичных @username по названию компании — без LLM.
# Кэш: data/recruiter-cache.json
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CACHE="$ROOT/data/recruiter-cache.json"
VERIFY="$ROOT/scripts/verify-telegram.sh"
COMPANY=""
EXTRA_URL=""
REFRESH=0
FETCH_N=0

usage() {
  cat >&2 <<'EOF'
Usage:
  recruiter-osint.sh "Название компании"
  recruiter-osint.sh "Название" --url 'https://…'
  recruiter-osint.sh "Название" --refresh

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
if hit is not None:
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

fetch() {
  local url="$1"
  FETCH_N=$((FETCH_N + 1))
  curl -sfL --max-time 20 -A "${HH_UA:-recruiter-osint/1.0}" "$url" \
    -o "$tmpdir/fetch_${FETCH_N}.html" 2>/dev/null || true
}

HH_UA="${HH_USER_AGENT:-recruiter-osint/1.0 (hh-radar; osint@local)}"
quoted="$(python3 -c "import urllib.parse,sys; print(urllib.parse.quote(sys.argv[1]))" "$COMPANY")"
emp_json="$(curl -sfL --max-time 20 -H "User-Agent: ${HH_UA}" \
  "https://api.hh.ru/employers?text=${quoted}&per_page=5" 2>/dev/null || echo '{"items":[]}')"
if ! python3 -c "import json,sys; json.loads(sys.argv[1]); exit(0)" "$emp_json" 2>/dev/null; then
  emp_json='{"items":[]}'
fi
echo "$emp_json" >"$tmpdir/employers.json"

# fallback: HTML-поиск работодателя (если API 403 с датацентра)
if [[ "$(python3 -c "import json;print(len(json.load(open('$tmpdir/employers.json')).get('items',[])))")" -eq 0 ]]; then
  fetch "https://hh.ru/search/employer?text=${quoted}"
  python3 - "$tmpdir" >"$tmpdir/employer_pick.json" <<'PY'
import json, re, sys
from pathlib import Path
root = Path(sys.argv[1])
ids = []
for path in root.glob("*.html"):
    text = path.read_text(encoding="utf-8", errors="ignore")
    ids.extend(re.findall(r"/employer/(\d+)", text))
ids = list(dict.fromkeys(ids))
if ids:
    print(json.dumps({"id": ids[0], "name": None}, ensure_ascii=False))
else:
    print("null")
PY
fi

if [[ "$(python3 -c "import json;print(len(json.load(open('$tmpdir/employers.json')).get('items',[])))")" -gt 0 ]]; then
  python3 - "$tmpdir/employers.json" "$COMPANY" >"$tmpdir/employer_pick.json" <<'PY'
import json, sys
from pathlib import Path
data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
company = sys.argv[2].casefold()
items = data.get("items") or []
best, best_score = None, -1
for it in items:
    name = (it.get("name") or "").casefold()
    score = 0
    if name == company:
        score = 100
    elif company in name or name in company:
        score = 50
    elif any(w in name for w in company.split() if len(w) > 2):
        score = 20
    if score > best_score:
        best_score, best = score, it
if best and best_score >= 20:
    print(json.dumps({"id": best.get("id"), "name": best.get("name")}, ensure_ascii=False))
else:
    print("null")
PY
fi
[[ -f "$tmpdir/employer_pick.json" ]] || echo null >"$tmpdir/employer_pick.json"

emp_id="$(python3 -c "
import json
from pathlib import Path
d=json.loads(Path('$tmpdir/employer_pick.json').read_text())
print('' if not d else str(d.get('id') or ''))
")"

if [[ -n "$emp_id" ]]; then
  fetch "https://hh.ru/employer/${emp_id}"
  fetch "https://hh.ru/search/vacancy?employer_id=${emp_id}&per_page=20"
fi
[[ -n "$EXTRA_URL" ]] && fetch "$EXTRA_URL"

python3 - "$tmpdir" >"$tmpdir/candidates.txt" <<'PY'
import re, sys
from pathlib import Path
deny = ("bot", "courses", "curator", "channel", "subscribe", "marie_")
found = []
for path in Path(sys.argv[1]).glob("*.html"):
    text = path.read_text(encoding="utf-8", errors="ignore")
    for m in re.finditer(r"https?://t\.me/([A-Za-z][A-Za-z0-9_]{4,31})", text, re.I):
        found.append(m.group(1))
    for m in re.finditer(r"(?<![A-Za-z0-9_])@([A-Za-z][A-Za-z0-9_]{4,31})", text):
        found.append(m.group(1))
seen, out = set(), []
for u in found:
    low = u.casefold()
    if low in seen or any(d in low for d in deny):
        continue
    seen.add(low)
    out.append(u)
print("\n".join(out))
PY

mapfile -t candidates <"$tmpdir/candidates.txt" || true

empty_result() {
  python3 - "$COMPANY" "$emp_id" <<'PY'
import json, datetime, sys
print(json.dumps({
  "company": sys.argv[1],
  "queried_at": datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat(),
  "hh_employer_id": sys.argv[2] or None,
  "contacts": [],
  "hint": "Найдите пост/вакансию с @ником и запустите с --url 'https://…'",
}, ensure_ascii=False, indent=2))
PY
}

if [[ ${#candidates[@]} -eq 0 ]]; then
  echo "Подсказка: найдите страницу с @ником (LinkedIn, careers) и добавьте --url" >&2
  empty_result
  exit 1
fi

"$VERIFY" "${candidates[@]}" >"$tmpdir/verified.json"

python3 - "$COMPANY" "$emp_id" "$EXTRA_URL" "$tmpdir/verified.json" >"$tmpdir/result.json" <<'PY'
import json, datetime, sys
from pathlib import Path
company, emp_id, extra, vpath = sys.argv[1:5]
verified = json.loads(Path(vpath).read_text(encoding="utf-8"))
contacts = [v for v in verified if v.get("alive")]
out = {
  "company": company,
  "queried_at": datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat(),
  "hh_employer_id": emp_id or None,
  "extra_url": extra or None,
  "contacts": contacts,
  "rejected_usernames": [v for v in verified if not v.get("alive")],
}
print(json.dumps(out, ensure_ascii=False))
PY

python3 -m json.tool <"$tmpdir/result.json"

python3 - "$CACHE" "$cache_key" "$tmpdir/result.json" <<'PY'
import json, sys
from pathlib import Path
cache_path, key, result_path = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
cache = json.loads(cache_path.read_text(encoding="utf-8"))
cache[key] = json.loads(result_path.read_text(encoding="utf-8"))
cache_path.write_text(json.dumps(cache, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
PY