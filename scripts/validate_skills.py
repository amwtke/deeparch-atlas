#!/usr/bin/env python3
"""Validate Atlas skill metadata and Claude Code/Codex adapters."""

from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
NAME_RE = re.compile(r"^[a-z0-9-]{1,64}$")
FRONTMATTER_RE = re.compile(r"^---\n(?P<body>.*?)\n---(?:\n|$)", re.DOTALL)


def fail(errors: list[str], message: str) -> None:
    errors.append(message)


def parse_frontmatter(path: Path, errors: list[str]) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    match = FRONTMATTER_RE.match(text)
    if not match:
        fail(errors, f"{path.relative_to(ROOT)}: invalid or missing frontmatter")
        return {}

    result: dict[str, str] = {}
    for line in match.group("body").splitlines():
        if not line.strip():
            continue
        if line.startswith((" ", "\t")) or ":" not in line:
            fail(errors, f"{path.relative_to(ROOT)}: frontmatter must use one-line scalar fields")
            continue
        key, value = line.split(":", 1)
        result[key.strip()] = value.strip().strip('"').strip("'")
    return result


def validate_skill(path: Path, internal: bool, errors: list[str]) -> None:
    fields = parse_frontmatter(path, errors)
    if set(fields) != {"name", "description"}:
        fail(
            errors,
            f"{path.relative_to(ROOT)}: frontmatter keys must be exactly name and description",
        )
        return

    name = fields["name"]
    description = fields["description"]
    if not NAME_RE.fullmatch(name):
        fail(errors, f"{path.relative_to(ROOT)}: invalid skill name {name!r}")
    if not description or len(description) > 1024 or "<" in description or ">" in description:
        fail(errors, f"{path.relative_to(ROOT)}: invalid description")
    if internal and ("atlas 入口" not in description or "不应被独立调用" not in description):
        fail(errors, f"{path.relative_to(ROOT)}: missing internal-only trigger boundary")


def validate_link(path: Path, expected: Path, errors: list[str]) -> None:
    if not path.is_symlink():
        fail(errors, f"{path.relative_to(ROOT)}: expected a symlink")
        return
    if path.resolve() != expected.resolve():
        fail(
            errors,
            f"{path.relative_to(ROOT)}: resolves to {path.resolve()}, expected {expected.resolve()}",
        )


def validate_codex_adapter(root_fields: dict[str, str], errors: list[str]) -> None:
    adapter = ROOT / ".agents/skills/atlas/SKILL.md"
    if adapter.is_symlink() or not adapter.is_file():
        fail(errors, f"{adapter.relative_to(ROOT)}: expected a regular delegating SKILL.md")
        return

    adapter_fields = parse_frontmatter(adapter, errors)
    if adapter_fields != root_fields:
        fail(errors, f"{adapter.relative_to(ROOT)}: metadata must match root SKILL.md")

    adapter_text = adapter.read_text(encoding="utf-8")
    if "../../../SKILL.md" not in adapter_text:
        fail(errors, f"{adapter.relative_to(ROOT)}: missing delegation to root SKILL.md")

    nested_skills = ROOT / ".agents/skills/atlas/skills"
    if nested_skills.exists() or nested_skills.is_symlink():
        fail(errors, f"{nested_skills.relative_to(ROOT)}: must not exist; it exposes internal skills")


def main() -> int:
    errors: list[str] = []
    root_skill = ROOT / "SKILL.md"
    validate_skill(root_skill, internal=False, errors=errors)
    root_fields = parse_frontmatter(root_skill, errors)

    internal_skills = sorted((ROOT / "skills").glob("*/SKILL.md"))
    if len(internal_skills) != 11:
        fail(errors, f"skills/: expected 11 internal skills, found {len(internal_skills)}")
    for path in internal_skills:
        validate_skill(path, internal=True, errors=errors)

    validate_link(ROOT / ".claude/skills/atlas/SKILL.md", ROOT / "SKILL.md", errors)
    validate_link(ROOT / ".claude/skills/atlas/skills", ROOT / "skills", errors)
    validate_codex_adapter(root_fields, errors)
    validate_link(ROOT / ".agents/skills/atlas/agents", ROOT / "agents", errors)

    openai_yaml = ROOT / "agents/openai.yaml"
    if not openai_yaml.is_file():
        fail(errors, "agents/openai.yaml: missing Codex UI metadata")

    deprecated_fragments = {
        "ask_user_input_v0": "host-specific choice tool",
        "present_files": "host-specific file presentation tool",
        "](../figures/": "deprecated top-level figures path",
    }
    source_paths = [ROOT / "SKILL.md", *internal_skills]
    for path in source_paths:
        text = path.read_text(encoding="utf-8")
        for fragment, label in deprecated_fragments.items():
            if fragment in text:
                fail(errors, f"{path.relative_to(ROOT)}: contains {label}: {fragment}")

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print(f"OK: root skill, {len(internal_skills)} internal skills, and both adapters are valid")
    return 0


if __name__ == "__main__":
    sys.exit(main())
