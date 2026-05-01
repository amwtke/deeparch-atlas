# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

`atlas` v3 is a **Claude skill suite** (Markdown only — no code, no build system, no tests). It implements a Socratic-style technical-teaching workflow: a thin dispatcher SKILL plus 11 specialized sub-skills, loaded progressively.

Trigger: `/atlas <topic>` (e.g. `/atlas malloc`, `/atlas io_uring`). Topic must be **technical** — kernel / JVM / database / distributed systems / middleware. Literary or historical topics belong to `/bookguide` or `/deeparch-literature`.

## Repo layout

```
SKILL.md                                       ← entry dispatcher (~162 lines), ALWAYS in context
README.md                                      ← v0→v3 evolution rationale
skills/
  ├── discovery/SKILL.md                       (one-question discovery)
  ├── progress-tracker/SKILL.md                (state machine + interrupt-recovery)
  ├── three-options/SKILL.md                   (pure-function user-pacing widget)
  ├── stage-{what,why,how,origin,deep,comparison,synthesis}/SKILL.md
  └── final-export/SKILL.md                    (fuse stages + MD/HTML export)
```

Install via `cp -r atlas/ ~/.claude/skills/` (or into a project's `.claude/skills/`).

## How the pipeline works (read before editing any sub-skill)

```
Discovery → What → Why → How → Origin → 🌉watershed → Deep → Comparison → Synthesis → Export
```

After every stage, the user picks one of three options (`懂了 / 追问 / 换角度`) before advancing. Each stage writes its output to `stages/0X-stage.md` immediately so the run is interrupt-resumable.

### Three load-time invariants

1. **Entry `SKILL.md` only routes** — never put teaching logic in it.
2. **Sub-skills load on demand**, not at startup. At any moment Claude holds: entry + current stage + `three-options` + `progress-tracker` (~500–600 lines total).
3. **Sub-skills are tightly coupled to the pipeline** by design. They assume `PROGRESS.md` exists, the soul-question is recorded, and the constraint list is queryable. Do **not** redesign them as standalone — that's `/primer` or `/deeparch-md`'s job.

### Question-driven, not stage-driven (UX contract)

The pipeline is **transparent to the user**. They feel a friend asking and answering questions; they should not feel a 7-stage workflow being run on them.

- Claude knows internally which stage it's in, but **must not** say "What 阶段已写入...", "现在进入 Why 阶段", "调用 three-options", "PROGRESS.md 已更新", "加载 stage-Z" in user-facing text. See entry `SKILL.md` 「对话语言纪律」 for the swap table.
- File paths can be shown to the user (they need to find the artifact), but framed as "草稿 / 我刚记下来的", not "stage 产物 / 阶段文件".
- Stage transitions use **natural connective prose**, never a banner. Example: "那顺着这个,下一个我想跟你回到原点问 ——" instead of "现在进入 Why 阶段。"

### User-pacing contract (gatekeeper)

Codified in `skills/three-options/SKILL.md` (file name is historical; the actual semantics is a user-pacing gatekeeper, not a button widget):

- **Claude never advances on its own.** Default behavior is to stay in the current topic.
- **Advancement requires an explicit signal** from a whitelist: "继续 / 走吧 / 下一个 / 这块够了 / 我懂了接着讲". Bare acks ("嗯 / 好 / 明白") do **not** count.
- After teaching a chunk, Claude poses a **probe question** (检验/反问) and waits. If the user only acks 2–3 rounds without new questions, Claude asks "是否可以接着往下走了?" — putting the decision back on the user, not deciding for them.
- During the wait, every user message gets classified: 追问 / 新视角 / 不懂反馈 / 附和 / 明确推进. Each non-advancement reply triggers a **patch to `stages/0X-stage.md`** — surgical edit, not full rewrite — plus a one-line audit entry in `PROGRESS.md`.
- The stage file is a **living artifact**: it accumulates user insight, clarifications, and reframing until the user explicitly says "this is enough."

### Concept introduction discipline

Every term introduced for the first time **must follow the chain**:

```
因为 <constraint / pain point>(reference a Cn from the Why-stage list when available)
   ↓
要解决 <specific sub-problem>
   ↓
所以引入 <the concept / component / number / threshold>
```

Never just drop a term and define it ostensively ("chunk is the minimum bookkeeping unit"). Always derive it from a constraint. The Why-stage `C1~Cn` list is the **constraint library** — every new concept introduction in How / Deep / Comparison / Synthesis should cite at least one `Cn`.

This applies to **numbers and magic constants too**: `M_ARENA_MAX = 8 × cores`, `M_MMAP_THRESHOLD = 128 KB`, `fastbin upper = 64 B` — each must be explained as "因为 X → 要解决 Y → 所以这个数字 ≈ Z" rather than just "this is the default value".

Full spec in entry `SKILL.md` 「概念引入纪律」 (the discipline section, with reverse-example table) + anti-pattern #12 in the same file.

### Artifact snapshot protocol (git)

Every stage advancement is also a **commit point**. The user's confirmed-stable artifact gets sealed to git in the background:

- When `three-options` receives an explicit advancement signal: `git add atlas-output/<short>-<yyyymmdd>/` + commit with message `atlas(<short>): finish <stage> stage` (+ optional one-line summary of what crystallized this round). This happens **before** loading the next stage skill.
- When `final-export` finishes generating the fused MD/HTML: one final commit + `git push origin main` to the configured remote.
- Git operations are **silent** — no chat output unless they fail. The user feels smooth stage transitions; the snapshots happen behind the scenes.
- `atlas-output/` is **not** in `.gitignore` — these are the artifacts being snapshotted. Only `.DS_Store` is ignored.
- Full spec in entry `SKILL.md` 「产物封存协议」 + `skills/three-options/SKILL.md` 「放行前封存」 + `skills/final-export/SKILL.md` 「终末封存 + push」.

### Single source of truth: `PROGRESS.md`

Every sub-skill communicates through `PROGRESS.md`, never by direct calls. Schema is fixed (interrupt recovery parses it):

- soul question (Discovery)
- progress checkboxes (0–10)
- constraint list C1, C2, … (built in Why, **referenced by every later stage** — un-referenced stages "go fuzzy")
- per-stage 追问/换角度 audit log
- selected comparison targets, selected export format

Sub-skills must call `progress-tracker` at stage start AND stage end. Skipping breaks resume.

### `three-options` is a pure function

It does **not** know what the next stage is. The caller (each `stage-X`) tells it. Don't embed a route table in `three-options` — that's an explicit anti-pattern (turns the suite into a spider web).

## Working-directory contract (runtime, per topic)

When `/atlas <topic>` runs, sub-skills create and read a per-topic workspace **relative to the current working directory**:

```
atlas-output/<short>-<yyyymmdd>/
  ├── PROGRESS.md           ← state machine (metadata records original topic + short name)
  ├── stages/0X-stage.md    ← per-stage outputs (immediate write)
  ├── <short>-atlas.md      ← final fused doc (only after Synthesis)
  └── <short>-atlas.html    ← optional, dark-tech style
```

Path conventions:
- `<short>` is the topic slug — **≤20 chars**, derived in entry `SKILL.md`. If the user's topic is already ≤20 chars use it verbatim (`malloc`, `io_uring`, `B+树`, `glibc的malloc函数`); if longer, the entry **asks the user** for a slug rather than guessing.
- `<yyyymmdd>` is the **creation date**. Resume sticks with the original directory; date does not refresh on later runs.
- Resume detection globs `atlas-output/<short>-*` (any date). If multiple matches exist, take the latest.
- Inside the markdown content (titles, transitions, related-topic suggestions), keep the **original** topic name — only filesystem-visible names get the slug.

This is **runtime user data**, not source. Don't commit a topic run back into the repo (and don't put `atlas-output/` under version control if/when this becomes a git repo).

## Conventions when editing sub-skills

- **Sub-skills don't call each other directly** — all routing flows back through entry `SKILL.md`'s dispatch table. Cross-calls are an anti-pattern.
- **Each sub-skill's `description:` frontmatter must say "仅由 atlas 入口调度时使用,不应被独立调用"** to prevent accidental triggering as a top-level skill.
- **Keep sub-skills small** (target ~80–210 lines). The whole point of v3 is progressive context loading; bloating one file undoes that.
- **Don't ask about export format in Discovery** — the user only knows what they want after they've gone through the stages. Discovery asks exactly one question (the soul question) — the v1 three-question form is dead.
- **Constraint references**: `stage-{how,origin,deep,comparison,synthesis}` must reference constraints by ID (e.g. "this addresses C3 + C5"). Adding a stage without constraint cross-refs is the documented "things go fuzzy" failure mode.

## HTML export style (user preference, hard-coded)

Dark tech aesthetic — `#0a0c10` background, JetBrains Mono + Noto Sans SC, left-side timeline + right-side color-tagged cards. Reference: the user's `process-address-space.html`. Don't redesign without asking.

## Anti-patterns (explicitly listed in entry `SKILL.md`)

1. Putting teaching logic in entry `SKILL.md`
2. Skipping `progress-tracker` between stages (kills resume)
3. **Advancing without an explicit user signal** (treating "嗯/好/明白" as advancement) — violates gatekeeper contract
4. **Leaking pipeline language into the user-facing dialogue** ("X 阶段 / 加载 stage-Y / 调用 three-options / PROGRESS.md 已更新") — the user should feel a friend, not a workflow
5. **Treating stage files as write-once artifacts** — they should be patched on every meaningful user input (追问 / 新视角 / 不懂反馈), not only when "换角度" is selected
6. **Answering questions in chat without patching the stage file** — the file becomes stale and stops reflecting the user's current understanding
7. Sub-skills calling each other directly (route through entry instead)
8. Designing sub-skills as standalone-callable (over-engineering — they're pipeline-only)
9. Later stages not cross-referencing constraint IDs
10. Handling literary/historical topics (out of scope)
11. Asking about export format in Discovery
