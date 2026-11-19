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
SKIP_USERS=()

usage() {
  cat >&2 <<'EOF'
Usage:
  recruiter-osint.sh "Название компании"
  recruiter-osint.sh "Название" --url 'https://…'
  recruiter-osint.sh "Название" --refresh
  recruiter-osint.sh "Название" --json   # полный JSON
  recruiter-osint.sh "Название" --skip @ник   # следующий кандидат (уже писали первому)

По умолчанию: список контактов (★ — рекомендуемый), тип и источник; полный JSON: --json
Кэш: data/recruiter-cache.json
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --url)
      EXTRA_URL="${2:-}"
      shift 2
      ;;
    --skip)
      nick="${2:-}"
      nick="${nick#@}"
      [[ -n "$nick" ]] && SKIP_USERS+=("$nick")
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

cache_key="$(python3 -c "import sys; sys.path.insert(0, sys.argv[2]); from discover import company_key; print(company_key(sys.argv[1]))" "$COMPANY" "$ROOT/scripts")"

if [[ "$REFRESH" -eq 0 && ${#SKIP_USERS[@]} -eq 0 ]]; then
  cache_hit_file="$(mktemp)"
  if python3 - "$CACHE" "$cache_key" "$cache_hit_file" <<'PY'
import json, sys
from pathlib import Path

cache = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
hit = cache.get(sys.argv[2])
if hit and (hit.get("best_contact") or hit.get("contacts")):
    Path(sys.argv[3]).write_text(json.dumps(hit, ensure_ascii=False), encoding="utf-8")
    sys.exit(0)
sys.exit(1)
PY
  then
    if [[ "$JSON_OUT" -eq 1 ]]; then
      python3 -m json.tool <"$cache_hit_file"
    else
      python3 "$ROOT/scripts/emit_contacts.py" "$cache_hit_file"
    fi
    rm -f "$cache_hit_file"
    echo "(из кэша; --refresh чтобы обновить)" >&2
    exit 0
  fi
  rm -f "$cache_hit_file"
fi

tmpdir="$(mktemp -d)"
trap 'rm -rf "$tmpdir"' EXIT

echo "discover…" >&2
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
  echo "Контакт не найден. Откройте вакансию на HireHi или добавьте seed / --url" >&2
  [[ "$JSON_OUT" -eq 1 ]] && empty_result
  exit 1
fi

echo "verify ${#candidates[@]} @…" >&2
"$VERIFY" "${candidates[@]}" >"$tmpdir/verified.json"

SKIP_CSV=""
if ((${#SKIP_USERS[@]} > 0)); then
  SKIP_CSV=$(printf '%s,' "${SKIP_USERS[@]}")
  SKIP_CSV="${SKIP_CSV%,}"
fi
echo "ранжирование (био)…" >&2
python3 "$ROOT/scripts/rank_contacts.py" \
  "$COMPANY" "$EXTRA_URL" "$tmpdir/discover.json" "$tmpdir/verified.json" "$SKIP_CSV" \
  >"$tmpdir/result.json"

if [[ "$(python3 -c "import json;print(len(json.load(open('$tmpdir/result.json')).get('contacts',[])))")" -eq 0 ]]; then
  echo "Контакт не найден. HireHi / сохраните пост с @ → bash scripts/recruiter-osint.sh \"Компания\" --url 'file://…'" >&2
  [[ "$JSON_OUT" -eq 1 ]] && python3 -m json.tool <"$tmpdir/result.json"
  exit 1
fi

if [[ "$JSON_OUT" -eq 1 ]]; then
  python3 -m json.tool <"$tmpdir/result.json"
else
  python3 "$ROOT/scripts/emit_contacts.py" "$tmpdir/result.json"
fi

python3 - "$CACHE" "$cache_key" "$tmpdir/result.json" <<'PY'
import json, sys
from pathlib import Path
cache_path, key, result_path = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
cache = json.loads(cache_path.read_text(encoding="utf-8"))
cache[key] = json.loads(result_path.read_text(encoding="utf-8"))
cache_path.write_text(json.dumps(cache, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
PY