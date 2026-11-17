#!/usr/bin/env python3
"""Импорт контактов из xlsx (Нетворк + ProductCamp) → data/network-contacts.json."""
from __future__ import annotations

import json
import re
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
USER_RE = re.compile(r"(?:t\.me/|telegram\.me/|@)([A-Za-z][A-Za-z0-9_]{4,31})", re.I)
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "network-contacts.json"
DEFAULT_NET = ROOT / "data" / "sources" / "network-career.xlsx"
DEFAULT_PC = ROOT / "data" / "sources" / "productcamp-spring-2024.xlsx"


def company_key(name: str) -> str:
    k = re.sub(r"[^a-z0-9а-яё]+", "-", (name or "").casefold().strip())
    return k.strip("-") or "unknown"


def read_xlsx(path: Path) -> list[list[str]]:
    with zipfile.ZipFile(path) as z:
        ss: list[str] = []
        if "xl/sharedStrings.xml" in z.namelist():
            root = ET.fromstring(z.read("xl/sharedStrings.xml"))
            for si in root.findall(".//m:si", NS):
                ss.append("".join((t.text or "") for t in si.findall(".//m:t", NS)))
        root = ET.fromstring(z.read("xl/worksheets/sheet1.xml"))
        rows: list[list[str]] = []
        for row in root.findall(".//m:sheetData/m:row", NS):
            vals: list[str] = []
            for c in row.findall("m:c", NS):
                v = c.find("m:v", NS)
                if v is None or v.text is None:
                    vals.append("")
                elif c.get("t") == "s":
                    vals.append(ss[int(v.text)])
                else:
                    vals.append(v.text)
            rows.append(vals)
        return rows


def tg_user(cell: str) -> str | None:
    if not cell or not str(cell).strip():
        return None
    m = USER_RE.search(str(cell).strip())
    return m.group(1) if m else None


def parse_network(path: Path) -> list[dict]:
    rows = read_xlsx(path)
    hdr_idx = next(
        i for i, r in enumerate(rows) if any("Текущая компания" in (c or "") for c in r)
    )
    hdr = rows[hdr_idx]
    col = {h.strip(): i for i, h in enumerate(hdr) if h}
    out: list[dict] = []
    prev_col = "Предыдущие компании, куда могут зареферить "
    for r in rows[hdr_idx + 1 :]:
        if not any(str(x).strip() for x in r):
            continue

        def cell(key: str) -> str:
            if key not in col or col[key] >= len(r):
                return ""
            return str(r[col[key]]).strip()

        name = cell("Фамилия и имя")
        company = cell("Текущая компания")
        role = cell("Должность")
        prev = cell(prev_col)
        user = tg_user(cell("Телеграм"))
        if not user or not company:
            continue
        keys = [company_key(company)]
        for chunk in re.split(r"[,;\n]+", prev):
            c = chunk.strip()
            if c:
                keys.append(company_key(c))
        out.append(
            {
                "name": name,
                "company": company,
                "company_keys": list(dict.fromkeys(keys)),
                "role": role or "—",
                "username": user,
                "source": "network-career-chat",
                "source_note": "Нетворк, чат карьерного сопровождения",
            }
        )
    return out


def parse_productcamp(path: Path) -> list[dict]:
    rows = read_xlsx(path)
    hdr_idx = next(i for i, r in enumerate(rows) if r and r[0] == "ID")
    col = {h: i for i, h in enumerate(rows[hdr_idx]) if h}
    out: list[dict] = []
    for r in rows[hdr_idx + 1 :]:
        if not r or not str(r[0]).strip().isdigit():
            continue

        def cell(key: str) -> str:
            if key not in col or col[key] >= len(r):
                return ""
            return str(r[col[key]]).strip()

        name = f"{cell('Имя')} {cell('Фамилия')}".strip()
        company = cell("Продукт/компания")
        role = cell("Должность/роль")
        user = tg_user(cell("Профиль в social media"))
        if not user or not company:
            continue
        out.append(
            {
                "name": name,
                "company": company,
                "company_keys": [company_key(company)],
                "role": role or "—",
                "username": user,
                "source": "productcamp-spring-2024",
                "source_note": "ProductCamp Spring 2024",
            }
        )
    return out


def main() -> None:
    net = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_NET
    pc = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_PC
    items = []
    if net.is_file():
        items.extend(parse_network(net))
    else:
        print(f"skip (нет файла): {net}", file=sys.stderr)
    if pc.is_file():
        items.extend(parse_productcamp(pc))
    else:
        print(f"skip (нет файла): {pc}", file=sys.stderr)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        json.dumps({"contacts": items}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(items)} contacts → {OUT}", file=sys.stderr)


if __name__ == "__main__":
    main()