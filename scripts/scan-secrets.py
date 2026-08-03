from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
TEXT_SUFFIXES = {".md", ".json", ".py", ".txt", ".yml", ".yaml", ".toml"}
TEXT_FILENAMES = {".env"}
SECRET_KEY_RE = r"[A-Za-z0-9_-]*(?:sessionToken|session[_-]?token|api[_-]?key|secret|password|token)[A-Za-z0-9_-]*"
PLACEHOLDER_VALUE_RE = r"""
    (?:
        <[^>]+>
        |\$\{?[A-Za-z0-9_]+\}?
        |%[A-Za-z0-9_]+%
        |\*{3,}
        |x{3,}
        |\.\.\.
        |TODO
        |TBD
        |REPLACE(?:_ME)?
        |YOUR[_-]?[A-Za-z0-9_-]*
        |EXAMPLE
        |SAMPLE
        |DUMMY
        |FAKE
        |TEST
        |REDACTED
        |NONE
        |NULL
        |CHANGEME
        |PLACEHOLDER
    )
"""
PATTERNS = [
    (
        "quoted secret assignment",
        re.compile(
            rf"""
            (?<![A-Za-z0-9_])
            ["']?
            {SECRET_KEY_RE}
            ["']?
            \s*[:=]\s*
            ["']
            (?!\s*(?:{PLACEHOLDER_VALUE_RE})\s*["']?\s*(?:[#,\n]|$))
            [A-Za-z0-9._~+/=-]{{8,}}
            ["']
            """,
            re.IGNORECASE | re.VERBOSE,
        ),
    ),
    (
        "env secret assignment",
        re.compile(
            rf"""
            ^\s*
            {SECRET_KEY_RE}
            \s*=\s*
            (?!\s*(?:{PLACEHOLDER_VALUE_RE})\s*(?:[#\n]|$))
            [A-Za-z0-9._~+/=-]{{8,}}
            \s*(?:\#.*)?$
            """,
            re.IGNORECASE | re.VERBOSE,
        ),
    ),
    ("bearer token", re.compile(r"bearer\s+[A-Za-z0-9._~+/=-]{20,}", re.IGNORECASE)),
    ("private key", re.compile(r"-----BEGIN (RSA |OPENSSH |EC )?PRIVATE KEY-----")),
]
SKIP_DIRS = {".git", "__pycache__"}


def is_env_file(path):
    name = path.name.lower()
    return name == ".env" or name.startswith(".env.")


def is_scannable_text_file(path):
    return (
        path.suffix.lower() in TEXT_SUFFIXES
        or path.name.lower() in TEXT_FILENAMES
        or is_env_file(path)
    )


def iter_scan_files(root):
    for path in root.rglob("*"):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path == Path(__file__).resolve():
            continue
        if not path.is_file():
            continue
        if not is_scannable_text_file(path):
            continue
        yield path


def scan(root=ROOT):
    errors = []
    for path in iter_scan_files(root):
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        for lineno, line in enumerate(lines, start=1):
            for name, pattern in PATTERNS:
                if pattern.search(line):
                    errors.append(f"{path.relative_to(root)}:{lineno} matched {name}")
    return errors


def main():
    errors = scan()
    if errors:
        print("Potential secrets found:")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)

    print("No obvious secrets found.")


if __name__ == "__main__":
    main()
