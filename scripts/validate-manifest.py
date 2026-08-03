import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "manifest.json"

EXPECTED_REPO = "TrendPM/AI-Skills"
EXPECTED_SOURCE_TYPE = "github-release"
EXPECTED_BRANCH = "main"
EXPECTED_STATUS = "released"
DISALLOWED_OWNER_VALUES = {"", "initial-publisher", "<owner>", "todo", "tbd"}


def fail(errors):
    print("Manifest validation failed:")
    for error in errors:
        print(f"- {error}")
    raise SystemExit(1)


def main():
    errors = []
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))

    target = data.get("targetRepository") or {}
    if target.get("fullName") != EXPECTED_REPO:
        errors.append(f"targetRepository.fullName must be {EXPECTED_REPO}")

    source = data.get("source") or {}
    if source.get("type") != EXPECTED_SOURCE_TYPE:
        errors.append(f"source.type must be {EXPECTED_SOURCE_TYPE}")
    if source.get("branch") != EXPECTED_BRANCH:
        errors.append(f"source.branch must be {EXPECTED_BRANCH}")
    if source.get("publicationStatus") != EXPECTED_STATUS:
        errors.append(f"source.publicationStatus must be {EXPECTED_STATUS}")
    if not source.get("tag"):
        errors.append("source.tag is required for published release manifests")

    governance = data.get("governance") or {}
    ownership = governance.get("ownership") or {}
    initial_owner = str(ownership.get("initialOwner") or "").strip()
    if initial_owner.lower() in DISALLOWED_OWNER_VALUES:
        errors.append("governance.ownership.initialOwner must be a concrete owner")
    if ownership.get("agentCanChangeOwner") is not False:
        errors.append("governance.ownership.agentCanChangeOwner must be false")

    if not (ROOT / ".mcp.example.json").is_file():
        errors.append(".mcp.example.json is required for repo-local MCP setup")

    mcp_servers = data.get("mcpServers")
    if not isinstance(mcp_servers, list) or not mcp_servers:
        errors.append("mcpServers must include project-local MCP servers")
    else:
        seen_mcp = set()
        for server in mcp_servers:
            name = server.get("name")
            path_text = server.get("path")
            entrypoint_text = server.get("entrypoint")
            config_template_text = server.get("configTemplate")
            owner = str(server.get("owner") or "").strip()

            if not name:
                errors.append("mcp server entry is missing name")
            elif name in seen_mcp:
                errors.append(f"duplicate mcp server name: {name}")
            seen_mcp.add(name)

            if not path_text or not (ROOT / path_text).is_dir():
                errors.append(f"{name or '<unknown>'}: MCP server path does not exist: {path_text}")
            if not entrypoint_text or not (ROOT / entrypoint_text).is_file():
                errors.append(f"{name or '<unknown>'}: MCP entrypoint does not exist: {entrypoint_text}")
            if not config_template_text or not (ROOT / config_template_text).is_file():
                errors.append(f"{name or '<unknown>'}: MCP config template does not exist: {config_template_text}")
            if owner.lower() in DISALLOWED_OWNER_VALUES:
                errors.append(f"{name or '<unknown>'}: MCP server owner must be concrete")

    skills = data.get("skills")
    if not isinstance(skills, list) or not skills:
        errors.append("skills must be a non-empty list")
    else:
        seen = set()
        for skill in skills:
            name = skill.get("name")
            path_text = skill.get("path")
            owner = str(skill.get("owner") or "").strip()
            if not name:
                errors.append("skill entry is missing name")
            elif name in seen:
                errors.append(f"duplicate skill name: {name}")
            seen.add(name)
            if not path_text:
                errors.append(f"{name or '<unknown>'}: missing path")
            else:
                skill_path = ROOT / path_text
                if not skill_path.is_dir():
                    errors.append(f"{name}: path does not exist: {path_text}")
                if not (skill_path / "SKILL.md").is_file():
                    errors.append(f"{name}: missing SKILL.md at {path_text}")
            if owner.lower() in DISALLOWED_OWNER_VALUES:
                errors.append(f"{name}: owner must be concrete")

    listed_skill_dirs = {skill.get("path") for skill in skills or [] if skill.get("path")}
    actual_skill_dirs = {str(path.relative_to(ROOT)).replace("/", "\\") for path in (ROOT / "skills").iterdir() if path.is_dir()}
    normalized_listed = {path.replace("/", "\\") for path in listed_skill_dirs}
    missing_from_manifest = actual_skill_dirs - normalized_listed
    if missing_from_manifest:
        errors.append("skills missing from manifest: " + ", ".join(sorted(missing_from_manifest)))

    checks = data.get("checks") or []
    required_checks = {
        "python scripts\\validate-skills.py",
        "python scripts\\smoke-skills.py",
        "python scripts\\validate-manifest.py",
        "python scripts\\scan-secrets.py",
        "python -m json.tool .mcp.example.json",
        "python -m json.tool .mcp\\ktalk-readonly\\ktalk-session.example.json",
        "python -m json.tool manifest.json",
        "python -m json.tool manifest.example.json",
        "git diff --check",
    }
    missing_checks = required_checks - set(checks)
    if missing_checks:
        errors.append("checks missing: " + ", ".join(sorted(missing_checks)))

    if errors:
        fail(errors)

    print("Manifest validation passed.")


if __name__ == "__main__":
    main()
