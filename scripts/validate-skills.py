from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"

required_sections = [
    "# ",
    "## When to Use",
    "## Scope",
    "## Inputs",
    "## Outputs",
    "## Read Sources",
    "## Write Targets",
    "## Approval Rules",
    "## Workflow",
    "## Failure Policy",
    "## Examples",
    "## Smoke Tests",
]
errors = []

for skill_dir in sorted(p for p in SKILLS.iterdir() if p.is_dir()):
    skill_file = skill_dir / "SKILL.md"
    if not skill_file.exists():
        errors.append(f"{skill_dir.name}: missing SKILL.md")
        continue
    text = skill_file.read_text(encoding="utf-8")
    text_lower = text.lower()
    for section in required_sections:
        if section not in text:
            errors.append(f"{skill_dir.name}: missing section marker {section!r}")
    if "official notion" in text_lower and "explicit approval" not in text_lower:
        errors.append(f"{skill_dir.name}: mentions official Notion but not explicit approval")
    if "ktalk" in text_lower and "raw transcript" not in text_lower:
        errors.append(f"{skill_dir.name}: mentions KTalk but not raw transcript handling")

if errors:
    print("Skill validation failed:")
    for error in errors:
        print(f"- {error}")
    raise SystemExit(1)

print("Skill validation passed.")
