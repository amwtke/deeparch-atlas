# AGENTS.md

This repository is a dual-host Atlas skill suite for Codex and Claude Code. It is Markdown-first: there is no application build, package manager, or runtime service.

## Shared-source contract

- Treat `SKILL.md` and `skills/*/SKILL.md` as the only workflow source of truth.
- Codex discovers a thin delegating adapter through `.agents/skills/atlas/SKILL.md`; that adapter loads the shared root instructions.
- Claude Code discovers the same entry through `.claude/skills/atlas/`.
- Claude Code uses symlinks to the shared source. The Codex adapter is a small real `SKILL.md` because a file-level symlink causes nested internal skills to be discovered as top-level skills.
- Do not add an `.agents/skills/atlas/skills` link. Keep all teaching logic in the root source and keep the Codex adapter limited to discovery metadata plus delegation.
- Keep `agents/openai.yaml` aligned with the root `SKILL.md`; Claude Code safely ignores this Codex metadata.

## Invocation contract

- Codex explicit invocation: `$atlas <technical topic>`.
- Claude Code explicit invocation: `/atlas <technical topic>`.
- Natural-language requests such as “用第一性原理彻底分析 X” may trigger the skill implicitly.
- The suite is for deep technical exploration, not literary/history topics or one-line API lookup.

## Editing the workflow

- Keep the root skill focused on routing, shared invariants, and host compatibility.
- Keep detailed teaching logic in the 11 sub-skills under `skills/`.
- Sub-skills are internal pipeline resources and must retain the description boundary “仅由 atlas 入口…调度时使用,不应被独立调用”.
- Preserve progressive loading: root entry + current stage + `progress-tracker` + `three-options`.
- Preserve `PROGRESS.md` as the single source of truth for resume state and stable constraint IDs.
- Preserve stage-local artifacts: `stages/0X-name/0X-name.md`, with `pics/` and `src/` inside the same stage directory.
- Use host-neutral capability wording. Prefer a structured choice UI when one exists; otherwise ask the same concise question in plain text and wait.
- Present output through the host’s native file UI when available; otherwise return clickable Markdown paths.
- Origin research must use current primary sources and include source links.
- Git snapshots and remote pushes are opt-in. Never force-push, and never include unrelated working-tree changes.

## Verification

Run after changing skill files or adapters:

```bash
python3 scripts/validate_skills.py
```

Also inspect `git diff --check` and `git status --short`. This repository has no separate build or test suite.
