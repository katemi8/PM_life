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
    name = (b.get("display_name") or b.get("title") or "").strip() or "—"
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
  echo "Контакт не найден. Откройте вакансию на HireHi или добавьте seed / --url" >&2
  [[ "$JSON_OUT" -eq 1 ]] && empty_result
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
RECR_MARK = ("recruiter", "рекрут", " hr", "hr ", "talent", "кадр", "подбор", "hiring")
CORP_MARK = ("идеи, тренды", "календарь", "корпоративн", "marketplace", "подписчик")
INFO_CHAN = ("информационн", "официальн", "канал для", "обратной связи", "клиент&#33;", "kion client")

def rank_contact(v, company_cf):
    if (v.get("match_reason") or "").startswith("seed"):
        v["score"] = int(v.get("score") or 0)
        return v["score"]
    s = int(v.get("score") or 0)
    text = f"{v.get('title', '')} {v.get('description', '')}".casefold()
    un = v["username"].casefold()
    reason = (v.get("match_reason") or "").casefold()
    company_hit = company_cf in text or company_cf in un or any(
        p in text for p in company_cf.split() if len(p) > 3
    )
    if "hr-канал" in reason:
        s += 10
    title = (v.get("title") or "").strip()
    if title and " " in title and len(title) > 5:
        s += 12
    if company_hit and any(m in text for m in RECR_MARK):
        s += 25
    if company_hit:
        s += 8
    if any(m in text for m in CORP_MARK) and not any(m in text for m in RECR_MARK):
        s -= 45
    if any(m in text for m in INFO_CHAN) and not any(m in text for m in RECR_MARK):
        s -= 55
    if un.endswith(("_corp", "_work", "_tg", "client")) or "client" in un or "corp" in un.split("_")[-1]:
        s -= 40
    v["score"] = s
    return s

company_cf = company.casefold()
for v in alive:
    m = meta.get(v["username"].casefold(), {})
    v["source_url"] = m.get("source")
    v["match_reason"] = m.get("reason")
    v["score"] = m.get("score", 0)
    v["role"] = m.get("role") or ""
    v["display_name"] = m.get("display_name") or ""
    rank_contact(v, company_cf)
    if not (v.get("role") or "").strip():
        td = f"{v.get('title','')} {v.get('description','')}".strip()
        if "recruiter" in td.casefold() or "рекрут" in td.casefold():
            v["role"] = td[:80]
alive = [v for v in alive if v.get("score", 0) >= 70]
alive.sort(
    key=lambda x: (
        0 if (x.get("match_reason") or "").startswith("seed") else 1,
        -(x.get("score") or 0),
        x.get("username", "").casefold(),
    )
)
alive = alive[:1]
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
  echo "Контакт не найден. HireHi / сохраните пост с @ → bash scripts/recruiter-osint.sh \"Компания\" --url 'file://…'" >&2
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
name = (b.get("display_name") or b.get("title") or "").strip() or "—"
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