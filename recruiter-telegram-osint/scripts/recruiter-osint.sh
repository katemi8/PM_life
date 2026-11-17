#!/usr/bin/env bash
# Поиск живого Telegram рекрутера по компании (после ручного выбора вакансии). Без LLM.
# Источники: seeds → --url → DDG (hirehi/linkedin/t.me) → hirehi company page.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CACHE="$ROOT/data/recruiter-cache.json"
VERIFY="$ROOT/scripts/verify-telegram.sh"
DISCOVER="$ROOT/scripts/discover.py"
COMPANY=""
EXTRA_URL=""
REFRESH=0
JSON_OUT=0

usage() {
  cat >&2 <<'EOF'
Usage:
  recruiter-osint.sh "Название компании"
  recruiter-osint.sh "Название" --url 'https://…'
  recruiter-osint.sh "Название" --refresh
  recruiter-osint.sh "Название" --json   # полный JSON

По умолчанию: 3 строки — @ник, имя, должность, ссылка t.me
Кэш: data/recruiter-cache.json
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --url)
      EXTRA_URL="${2:-}"
      shift 2
      ;;
    --json)
      JSON_OUT=1
      shift
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
  if python3 - "$CACHE" "$cache_key" "$JSON_OUT" <<'PY'
import json, sys
from pathlib import Path

def emit_short(hit):
    b = hit.get("best_contact") or (hit.get("contacts") or [None])[0]
    if not b:
        return False
    name = (b.get("title") or "").strip() or "—"
    role = (b.get("role") or "").strip() or "—"
    u = b["username"]
    print(f"@{u}")
    print(f"{name}, {role}")
    print(f"https://t.me/{u}")
    return True

cache = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
hit = cache.get(sys.argv[2])
json_out = sys.argv[3] == "1"
if hit and hit.get("contacts"):
    if json_out:
        print(json.dumps(hit, ensure_ascii=False, indent=2))
    else:
        emit_short(hit)
    sys.exit(0)
sys.exit(1)
PY
  then
    echo "(из кэша; --refresh чтобы обновить)" >&2
    exit 0
  fi
fi

tmpdir="$(mktemp -d)"
trap 'rm -rf "$tmpdir"' EXIT

python3 "$DISCOVER" "$ROOT" "$COMPANY" "$EXTRA_URL" >"$tmpdir/discover.json"

candidates=()
while IFS= read -r line || [[ -n "$line" ]]; do
  [[ -n "$line" ]] && candidates+=("$line")
done < <(python3 - "$tmpdir/discover.json" <<'PY'
import json, sys
from pathlib import Path
data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
for c in data.get("candidates") or []:
    print(c["username"])
PY
)

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
    v["role"] = m.get("role") or ""
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
  echo "Живой Telegram не найден (добавьте seed или --url)" >&2
  [[ "$JSON_OUT" -eq 1 ]] && python3 -m json.tool <"$tmpdir/result.json"
  exit 1
fi

if [[ "$JSON_OUT" -eq 1 ]]; then
  python3 -m json.tool <"$tmpdir/result.json"
else
  python3 - "$tmpdir/result.json" <<'PY'
import json, sys
from pathlib import Path
hit = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
b = hit.get("best_contact")
name = (b.get("title") or "").strip() or "—"
role = (b.get("role") or "").strip() or "—"
u = b["username"]
print(f"@{u}")
print(f"{name}, {role}")
print(f"https://t.me/{u}")
PY
fi

python3 - "$CACHE" "$cache_key" "$tmpdir/result.json" <<'PY'
import json, sys
from pathlib import Path
cache_path, key, result_path = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
cache = json.loads(cache_path.read_text(encoding="utf-8"))
cache[key] = json.loads(result_path.read_text(encoding="utf-8"))
cache_path.write_text(json.dumps(cache, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
PY