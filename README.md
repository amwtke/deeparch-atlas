# /atlas v3 — 苏格拉底式技术教学 skill 套件

**陪你一个阶段一个阶段把一个技术从头到尾搞透。**

v3 把 atlas 重构成 **Superpowers 风格的 skill 套件**——轻量入口 + 11 个专精子 skill。
入口只做调度,子 skill 按需加载,渐进式上下文管理。

## v0 → v1 → v2 → v3 演化

| 维度 | v0 | v1 | v2 | **v3** |
|------|-----|-----|-----|--------|
| 主题范围 | 技术 + 文学 | 专精技术 | 专精技术 | 专精技术 |
| 工作流形态 | OUTLINE → 写 | Discovery 三问 → 写 | 七阶段 monolithic | **七阶段 + skill 套件** |
| 文件结构 | 单文件 | 单文件 | 单文件(584 行) | **入口 162 行 + 11 个子 skill** |
| 上下文加载 | 全量加载 | 全量加载 | 全量加载(584 行) | **渐进加载(只加载相关阶段)** |
| Discovery | (无) | 3 题 | 1 题 | 1 题 |
| 中断恢复 | ❌ | ❌ | ✅ | ✅ |
| 风格 | Spec-driven 生成 | Spec-driven 生成 | 苏格拉底教学(monolithic) | **苏格拉底教学(套件化)** |
| 维护性 | 改任何一处都要改主文件 | 同左 | 同左 | **每个阶段独立维护** |

## 套件结构

```
atlas/
├── SKILL.md                          ← 入口,162 行,只做调度
├── README.md                         ← 本文件
└── skills/
    ├── discovery/SKILL.md            ← Discovery 一问(87 行)
    ├── progress-tracker/SKILL.md     ← 状态机管理 + 中断恢复(146 行)
    ├── three-options/SKILL.md        ← 三选项交互模式,纯函数(107 行)
    ├── stage-what/SKILL.md           ← What 阶段(145 行)
    ├── stage-why/SKILL.md            ← Why 阶段 + 约束清单(120 行)
    ├── stage-how/SKILL.md            ← How 阶段(109 行)
    ├── stage-origin/SKILL.md         ← Origin 阶段(含 web search,169 行)
    ├── stage-deep/SKILL.md           ← Deep 阶段 + 反事实小试(144 行)
    ├── stage-comparison/SKILL.md     ← Comparison Hook + 候选生成(163 行)
    ├── stage-synthesis/SKILL.md      ← 五元组方法论(189 行)
    └── final-export/SKILL.md         ← 融合 + MD/HTML 导出(210 行)
```

**总计**:1751 行(11 个子 skill + 1 个入口),但 Claude 在任意时刻**只需加载** 入口 + 当前阶段子 skill + three-options + progress-tracker(约 500~600 行),远低于 v2 monolithic 的 584 行全量加载。

## 设计决定回顾

| 决定 | 选择 | 理由 |
|------|------|------|
| 子 skill 命名 | **不加 atlas- 前缀** | atlas 单独项目,不会污染其他 skill 体系 |
| 子 skill 独立性 | **强耦合,只服务 pipeline** | atlas 灵魂是七阶段,独立调用没意义,简化设计 |
| three-options 路由 | **纯函数,不知道下一步** | 路由由调用方决定,three-options 职责单一 |

## 安装

```bash
cp -r atlas/ ~/.claude/skills/
# 或
cp -r atlas/ <project>/.claude/skills/
```

## 用法

```
/atlas malloc       # 启动 Discovery → 进入 What 阶段
/atlas io_uring
/atlas B+树

# 中断后恢复
/atlas malloc       # 自动检测 PROGRESS.md,询问"上次走到 X 阶段,继续吗?"
继续 atlas malloc   # 同上,自然语言也认
```

## 工作流可视化

```
[Discovery]   一问:你最想搞清楚的具体问题?
   ↓
[1. What]     它是什么 → stages/01-what.md
   ↓ three-options
[2. Why]      为什么需要 + 建立约束清单 → stages/02-why.md
   ↓ three-options
[3. How]      大致怎么工作 → stages/03-how.md
   ↓ three-options
[4. Origin]   它怎么来的(web search) → stages/04-origin.md
   ↓ 🌉 分水岭三选项: 满足导出 / 继续 Deep / 追问
[5. Deep]     源码与设计 + 反事实小试 → stages/05-deep.md
   ↓ three-options
[6. Comparison] Hook(用户选 1~3 个对比对象) → stages/06-comparison.md
   ↓ three-options
[7. Synthesis] 五元组方法论 → stages/07-synthesis.md
   ↓
[Export]      询问 MD / MD+视频 / MD+HTML
              融合 stages/*.md → <短名>-atlas.md
              (可选)生成 HTML
```

## 与 Superpowers 的设计对应

| Superpowers | /atlas v3 |
|-------------|-----------|
| 入口 SKILL.md 只做调度 | ✅ 入口 162 行,只路由 |
| skills/ 子目录多个专精 skill | ✅ skills/ 子目录 11 个 |
| 渐进式上下文加载 | ✅ 按需加载子 skill |
| 中断恢复(plan 文件) | ✅ PROGRESS.md 状态机 |
| 子 skill 职责单一 | ✅ 每个 80~210 行 |
| TDD 不让 AI 一把梭 | ✅ 每阶段三选项让用户主导 |
| 工程方法论(TDD) | 思考方法论(第一性原理 + 反事实) |

## 关键创新:two-tier 加载架构

Claude 在任意时刻只需加载:

1. **常驻**:入口 SKILL.md(162 行)
2. **共享**:progress-tracker(146 行)+ three-options(107 行)
3. **当前阶段**:对应的 stage-X 子 skill(80~210 行)

总计 ~500~600 行,**远低于 v2 monolithic 的 584 行全量**。这意味着:

- 上下文压力小 → Claude 处理质量高
- 阶段切换时,前一阶段子 skill 可以从上下文移除 → 始终保持小上下文
- 改一个阶段不影响其他阶段
- 可以独立测试每个子 skill

## 文件

- `SKILL.md` — v3 入口(162 行)
- `skills/` — 11 个子 skill(共 1589 行,但按需加载)
- `SKILL.v2-monolithic.md` — v2 备份(单文件版,584 行)
- `SKILL.v1.md` — v1 备份(Discovery 三问 + 篇级 checkpoint)
- `SKILL.v0.md` — v0 备份(无 Discovery,带文学模式)
- `README.md` — 本文件

## 适用场景

- ✅ 完全不懂某技术,想从头搞透
- ✅ 已经懂但想搞清楚某个具体问题(灵魂问题驱动)
- ✅ 想做 B 站长视频素材
- ✅ 中途打断,几天后想继续(PROGRESS.md 自动恢复)
- ✅ 想精确控制 atlas 的某个阶段(改单个子 skill 即可)

## 不适用

- ❌ 文学/历史/艺术主题(用 /bookguide 或 /deeparch-literature)
- ❌ 单纯查个语法/API(用直接对话或 /primer)
- ❌ 想要"AI 替我一把梭写完"(那是 v0/v1 的形态)

## 后续可能的演化

- **v3.1**:为每个子 skill 编写 eval 测试集(skill-creator 风格)
- **v3.2**:跨阶段追问——用户在 Deep 阶段想回头改 Why 的约束清单
- **v3.3**:多用户协同——团队成员可以接力跑 atlas(基于 PROGRESS.md)
- **v4**:多主题对照——`/atlas malloc vs jemalloc` 同时教两个相关技术
