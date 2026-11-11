# 分集起草派工单（主控写，起草分支只读）

## 三条硬禁令（违反任何一条 = 本集作废）
1. **不做任何 git 操作**（add/commit/push/stash/checkout/reset 都不行，两个仓库都不行）。
2. **不创建 / 不修改 `video-notes/ready-ep*` 标记**，就绪标记只由主控打。
3. **不渲染**：不跑 `./deeparch-video`、`pipeline.py`、`--no-tts` 预览（8 集共用同一目录的 tmp，会互相踩）。

允许跑：`venv/bin/python scripts/vmd_lint.py <vmd> --theme anthropic`、`venv/bin/python video-notes/review_ep.py <vmd>`、`venv/bin/python scripts/summary_card.py <json> -o <png>`，以及只读的 grep/读文件。所有命令在 `/Users/jin.xiao/workshop/deeparch-video` 下执行。

## 输入
- 原文：`linux的进程调度器-atlas.md`（**只读，不得修改**；stages/ 也只读）
- 约束速查 C1~C8：第 53–100 行；收尾核实 81 条：第 3763–3863 行（数字、年份以核实结论为准，「更正」的按更正讲，「未核实」的不讲具体数字或改成量级）
- 架构图 PNG：`pics/*.png`（原文 11 张 SVG 已转好，中文正常）
- 人物照片：`pics/person-linus-torvalds.jpg`、`pics/person-ingo-molnar.jpg`、`pics/person-dave-cutler.jpg`（已目检）。Con Kolivas / Peter Zijlstra / Tejun Heo / David Vernet **没有照片，只能用 text 或 spotlight 场景介绍，不要用人物场景**（否则渲染器会自动搜图配错人）
- 源码副本（Linux v6.12，jsDelivr gh/torvalds/linux@v6.12）：`video-notes/src/`，文件名把 `/` 换成 `_`，如 `kernel_sched_fair.c`；另有 `linux-0.01_kernel_sched.c`

## 产物（每集三个文件，不多写）
1. `linux-sched-epN-<slug>.vmd`
2. `pics/epN-summary-card.json` + `pics/epN-summary-card.png`（`scripts/summary_card.py` 生成，格式照上一部 `/Users/jin.xiao/workshop/deeparch-atlas/atlas-output/Linux进程全链路-20261024/pics/ep7-summary-card.json`；takeaway 里可用 `**` 加粗，那是卡片不是旁白）
3. `video-notes/coverage-epN.md`：原文必讲项 → 证据载体 → 场景号 → 处理（保留/合并/压缩/更正），格式照上一部 `video-notes/coverage-ep3.md`；末尾列「相对原文的事实修正」

## 篇幅
每集 9~14 分钟：约 22~38 个场景、口播 2800~4200 字（review_ep.py 会打估时）。ep3 How、ep5 Deep 可到上限，ep1 What 偏下限。

## 结构（必须）
- 顶部：`# 第 N 集 X 阶段 — <带钩子的中文集标题>`，下一行 `[intro-line] <一句话，必须复用 H1 里的技术词>`
- 场景 1：开场过场 spotlight，模板见 skill（「现在我们来看 What 阶段 / Linux 调度器到底是什么？」等），旁白介绍本集讲什么、和前后集的关系
- 本篇引用的每张原文图都要用 `[visual: html_slide image="pics/xx.png" title=...]` + `[step: auto]` / `scroll auto` 完整展示并逐区解说（格式照上一部 ep5 第 4 场景）
- 倒数第二场：本集总结卡 `[visual: html_slide image="pics/epN-summary-card.png" title=...]`
- 最后一场：「本集就到这里，下集见」+ 下一集预告的 spotlight 或 title。**不要自己写「一键三连」**，解析器会自动补。ep7 最后一场回到全片第一个问题收束

## 讲解规则（用户审片定下的，必须遵守）
- 两条及以上链路/路径对比，画 ASCII 双栏/双泳道框图（┌─┐ + ▼），不用 `(a) --x--> (b)` 文字箭头串
- 原理类段落先讲「为什么这样设计是可行的、为什么是工程上最佳」，再进代码；只讲事实不讲为什么不合格
- 代码场景用 `code_explain`，讲清函数作用、调用参数、意图，可以慢；右侧 HIGHLIGHT 说明可画小 ASCII 结构图。**源码必须是 video-notes/src 下副本的逐字连续子串**（tab 缩进原样保留，可截取连续片段），标题写明「（Linux 6.12 kernel/sched/fair.c）」这类出处；原文里的伪代码若要上屏，标题必须含「伪代码」或「示意」
- 生活类比少用：只在必要且能讲清时用，一集最多 1~2 处（厨房类比是 What 篇的主类比，ep1 用，后面最多回扣一句）
- 实测/实验：先讲实验设计和预期，再讲命令；以 Linux 为准给出预期结果和推理，不在本机跑
- 缩写读英文原文：EEVDF、CFS、cgroup、BPF、IPI、TLB、vruntime 等别逐字母念成中文怪音；「copy on write」写英文
- 第二人称「你」开场钩子，具体数字（以核实表为准），句长约 30 字，单段旁白 ≤150 字
- **旁白零免责、零合同语言**：不出现「本机未复现 / 我们预测 / 验收 / 边界仍 / 待核 / 未核实 / 已核」之类；不确定的数字直接不说或说量级
- 旁白禁词（review_ep.py 会查）：atlas、facetime、html_slide、code、spotlight、adv_animation、statemap、recap、analogy、layers、timeline、ascii、场景类型、visual: ；不写 markdown（`**`、反引号、#）
- 画面（非代码场景）不用 `→`、`①~⑨` 等会变豆腐的字符，用 `->` 和阿拉伯数字；ASCII 每行 ≤70 字符、每图 ≤25 行；全角空格补齐对齐可以用
- 约束引用写成「C3 凭账不凭嘴」这种编号+短名，旁白里可读作「C3，凭账不凭嘴」
- 不用 diff / data / news_title 场景（anthropic 主题 lint strict 会拦）；对比一律 ascii 双栏
- 场景类型尽量丰富：spotlight、text、ascii、layers、timeline、statemap、code_explain、html_slide、title，人物场景只给有照片的三位；sidebar 可用

## 自检（返回前必须做完并在汇报里贴结果）
1. `venv/bin/python scripts/vmd_lint.py <vmd> --theme anthropic` 无 error
2. `venv/bin/python <D>/video-notes/review_ep.py <vmd>` 输出 `ISSUES 0`
3. 用 Read 看一眼自己的 summary-card.png 没有溢出/豆腐
4. 汇报：场景数、口播字数、估时、类型分布、用到的原文图、源码出处列表、相对原文的事实修正、任何没覆盖的原文必讲项及理由。汇报控制在 40 行内
