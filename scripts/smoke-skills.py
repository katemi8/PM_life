import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"
MANIFEST = ROOT / "manifest.json"


def read(path):
    return path.read_text(encoding="utf-8")


def require_contains(errors, name, text, needles):
    lowered = text.lower()
    for needle in needles:
        if needle.lower() not in lowered:
            errors.append(f"{name}: missing expected behavior marker: {needle}")


def require_any(errors, name, text, needles, label):
    lowered = text.lower()
    if not any(needle.lower() in lowered for needle in needles):
        errors.append(f"{name}: missing any marker for {label}: {', '.join(needles)}")


def main():
    errors = []
    manifest = json.loads(read(MANIFEST))
    manifest_skills = {item["name"]: item for item in manifest.get("skills", [])}

    expected = {
        "agent-system-install": {
            "must": [
                "codex mcp add notion --url https://mcp.notion.com/mcp",
                "codex mcp login notion",
                "KTalk MCP server `ktalk`",
                "ktalk_list_recordings",
                "ready, partial or blocked",
                "Do not ask PM to paste `sessionToken`",
            ],
            "any": [],
        },
        "metrics-markup": {
            "must": [
                "Use the official hosted Notion MCP as the supported read path",
                "notion_query_database_view",
                "batch preview",
                "diff plus explicit approval",
                "readback matches",
            ],
            "any": [],
        },
        "product-context-search": {
            "must": [
                "Use the official hosted Notion MCP",
                "Do not use another Notion connector as a substitute",
                "Search is read-only",
                "Use KTalk as a raw source only when meeting context is relevant",
                "highlights it instead of choosing silently",
                "raw transcript text must not be copied",
            ],
            "any": [],
        },
        "meeting-context-review": {
            "must": [
                "Current v0 is read-only",
                "KTalk MCP server `ktalk`",
                "does not write results to Notion",
                "raw transcript text must not be copied",
                "conflict and does not resolve silently",
                "official hosted Notion MCP",
            ],
            "any": [],
        },
    }

    for name, spec in expected.items():
        if name not in manifest_skills:
            errors.append(f"{name}: missing from manifest.json")
            continue

        skill_path = ROOT / manifest_skills[name]["path"] / "SKILL.md"
        if not skill_path.is_file():
            errors.append(f"{name}: missing SKILL.md")
            continue

        text = read(skill_path)
        require_contains(errors, name, text, spec["must"])
        for group in spec["any"]:
            require_any(errors, name, text, group["needles"], group["label"])

        if "## Smoke Tests" not in text:
            errors.append(f"{name}: missing Smoke Tests section")
        smoke_text = text.split("## Smoke Tests", 1)[-1]
        smoke_count = sum(1 for line in smoke_text.splitlines() if line.strip().startswith("- "))
        if smoke_count < 2:
            errors.append(f"{name}: expected at least 2 smoke tests, found {smoke_count}")

    skill_dirs = {path.name for path in SKILLS.iterdir() if path.is_dir()}
    missing_expected = skill_dirs - set(expected)
    if missing_expected:
        errors.append("smoke expectations missing for skills: " + ", ".join(sorted(missing_expected)))

    if errors:
        print("Skill smoke tests failed:")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)

    print("Skill smoke tests passed.")


if __name__ == "__main__":
    main()
