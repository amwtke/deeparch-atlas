# Atlas v3 — Claude Code / Codex 深度技术探索套件

Atlas 用苏格拉底式对话陪用户把一个复杂技术主题从“它是什么”一路推到“为什么这样设计”，并把每轮形成的理解持续写成可恢复、可修订、可导出的技术文档。

它不是一次性长文生成器。用户决定什么时候推进；追问、新视角和不懂反馈会继续 patch 当前文档，直到用户确认这一块已经足够稳定。

## 双平台支持

| 宿主 | 项目级发现入口 | 显式调用 |
|------|----------------|----------|
| Codex | `.agents/skills/atlas/` | `$atlas malloc` |
| Claude Code | `.claude/skills/atlas/` | `/atlas malloc` |

Claude Code 入口直接链接到根 `SKILL.md` 和 `skills/`。Codex 入口是一个很薄的真实 `SKILL.md`，只注册 `$atlas` 并转发到根指令；这样不会把 11 个内部资源误暴露成顶层 Codex skills。两边的工作流逻辑仍只有根目录这一份。自然语言请求也可以触发，例如“用第一性原理带我搞懂 io_uring”。

## 目录结构

```text
deeparch-atlas/
├── SKILL.md                         # 共享入口：触发、路由、通用纪律
├── skills/                          # 11 个按需加载的内部子 skill
├── agents/openai.yaml               # Codex UI 元数据
├── .agents/skills/atlas/            # Codex 项目级薄适配入口
├── .claude/skills/atlas/            # Claude Code 项目级适配入口（symlink）
├── AGENTS.md                        # Codex 维护说明
├── CLAUDE.md                        # Claude Code 维护说明
├── scripts/validate_skills.py       # 双平台结构校验
└── atlas-output/                    # 技术探索运行产物
```

## 11 个子 skill 分别做什么

| 子 skill | 作用 | 关键产物 / 决策 |
|----------|------|-----------------|
| `discovery` | 只问一个“最想搞清楚的问题”，把模糊主题收敛成灵魂问题 | 初始化探索目标 |
| `progress-tracker` | 管理状态机、约束编号、追问审计和中断恢复 | `PROGRESS.md` |
| `three-options` | 用户节奏 gatekeeper；区分追问、换视角、没懂、附和和明确推进 | 当前文档持续 patch |
| `stage-what` | 建立一句话定义、跨领域类比、全景图、术语与技术栈位置 | `01-what.md` |
| `stage-why` | 从“没有它会怎样”推出不可再分约束 | `02-why.md` + 稳定的 `C1~Cn` |
| `stage-how` | 从约束推出核心组件和端到端工作骨架，不深入源码 | `03-how.md` + 概览图 |
| `stage-origin` | 用一手资料还原技术的历史问题、死路、取舍与遗憾 | `04-origin.md` + 来源链接 |
| `stage-deep` | 做操作层、函数逻辑层、底层原理层剖析，并加入可运行 demo 和反事实小试 | `05-deep.md` + `src/` |
| `stage-comparison` | 让用户选择对比对象，把主题放回完整设计空间 | 可选 `06-comparison.md` |
| `stage-synthesis` | 把约束、决策、代价、反事实和现实对照收束成可迁移方法论 | `07-synthesis.md` |
| `final-export` | 融合各阶段，修正资源路径，生成综合 MD，可选 HTML / 视频脚本提示 | `<短名>-atlas.md` / `.html` |

这些子 skill 是 Atlas 内部资源，不作为 11 个独立顶层技能安装。入口只在需要时读取“当前阶段 + `progress-tracker` + `three-options`”，避免一次把全部说明塞进上下文。

## 工作流

```text
Discovery
   ↓
What → Why → How → Origin
                       ↓
                 深度分水岭
                  ↙       ↘
            Synthesis     Deep → Comparison（可跳过）
                  ↘       ↙
                    Export
```

每块内容写完后不会自动前进：

1. 助手用一个反问检查理解。
2. 用户追问、提出新视角或指出没懂的地方。
3. 助手回答并局部更新当前文档与 `PROGRESS.md`。
4. 只有用户明确要求推进，并再次确认已读当前草稿，才进入下一块。

## 使用

在本仓库中启动 Codex 或 Claude Code 时，项目级适配入口已经存在，无需额外安装。

Codex：

```text
$atlas malloc
$atlas io_uring
继续 atlas B+树
```

Claude Code：

```text
/atlas malloc
/atlas io_uring
继续 atlas B+树
```

如果技能列表没有立即刷新，重启对应客户端或新开一个会话。

### 在其他仓库或用户级安装

推荐让两边都指向同一个 Atlas 源目录，但 Codex 要链接到专用适配目录：

```bash
ATLAS_SRC=/absolute/path/to/deeparch-atlas
mkdir -p ~/.agents/skills ~/.claude/skills
ln -s "$ATLAS_SRC/.agents/skills/atlas" ~/.agents/skills/atlas
ln -s "$ATLAS_SRC" ~/.claude/skills/atlas
```

也可以只安装其中一个宿主的链接。Codex 不要直接链接仓库根目录，否则递归发现会把 `skills/*` 当成独立技能。不要分别复制两份工作流后独立修改。

## 运行产物

```text
atlas-output/<短名>-<yyyymmdd>/
├── PROGRESS.md
├── stages/
│   ├── 01-what/
│   │   ├── 01-what.md
│   │   └── pics/
│   ├── 02-why/02-why.md
│   ├── 03-how/
│   │   ├── 03-how.md
│   │   └── pics/03-overview.svg
│   ├── 04-origin/04-origin.md
│   ├── 05-deep/
│   │   ├── 05-deep.md
│   │   └── src/
│   ├── 06-comparison/06-comparison.md
│   └── 07-synthesis/07-synthesis.md
├── <短名>-atlas.md
└── <短名>-atlas.html               # 可选
```

每个阶段目录自包含 Markdown、图片和代码；综合文档导出时会重写这些相对路径。

## 关键设计约束

- 第一次引入任何概念时都从“因为某约束 → 要解决某问题 → 所以引入该概念”推出。
- Why 建立的 `C1~Cn` 是后续 How / Origin / Deep / Comparison / Synthesis 的共同脊梁。
- 复杂关系优先画带暗色背景的 SVG，放在当前 stage 的 `pics/` 内。
- Origin 必须联网查一手资料，不能只凭模型记忆编写历史故事。
- 结构化选择控件是可选增强；宿主没有对应能力时，退回简短文本选项。
- 文件呈现使用宿主原生能力；Codex 返回可点击路径，Claude Code 使用其可用的文件呈现能力或路径。
- Git 快照与远程 push 默认关闭，只有用户在当前对话明确授权时才执行；永不夹带无关改动，永不 force-push。

## 开发与校验

修改入口、子 skill 或任一适配目录后运行：

```bash
python3 scripts/validate_skills.py
git diff --check
git status --short
```

校验会检查：

- 根 skill 与 11 个内部 skill 的 frontmatter；
- 内部 skill 的“不得独立触发”边界；
- Claude Code 符号链接和 Codex 薄适配入口是否仍指向同一共享工作流；
- Codex `agents/openai.yaml` 是否存在；
- 是否重新引入了已废弃的宿主专用工具名或旧 `figures/` 路径。

## 适用与不适用

适合内核、JVM、数据库、编译器、分布式系统、中间件等需要理解设计约束与取舍的技术主题。

不适合文学、历史、艺术主题，也不适合只查一个语法、参数或 API 的短问题。
