# 分集起草派工单(主控写,起草分支只读)

系列:cgroup 核心原理,8 集(ep0 目录 + ep1~ep7 七篇),B 站一个稿件 8 个分 P。你负责其中一集。

下文 `D` = `/Users/jin.xiao/workshop/deeparch-atlas/atlas-output/cgroup核心原理-20261112`,`R` = `/Users/jin.xiao/workshop/deeparch-video`。

## 三条硬禁令(违反任何一条 = 本集作废)
1. 不做任何 git 操作(两个仓库都不行)。
2. 不创建、不修改 `D/video-notes/ready-ep*` 标记,不写 `D/` 根目录下的 vmd(那是主控对齐后生成的)。
3. 不渲染:不跑 `./deeparch-video`、`pipeline.py`、`--no-tts` 预览。

允许跑(都在 `R` 下执行):`venv/bin/python scripts/vmd_lint.py <vmd> --theme anthropic`、`venv/bin/python D/video-notes/review_ep.py <vmd>`、`venv/bin/python scripts/summary_card.py <json> -o <png>`,以及只读的 grep / 读文件。

## 先读
1. `R/skills/deeparch-video-script/SKILL.md` 全文(vmd 格式、场景类型、旁白规范)。和本任务书冲突时以本任务书为准。
2. `R/docs/video-script/conceptual-thinking.md`(组织口播与转场)。
3. 上一部系列的同集 vmd 作格式样例(只学格式,不学内容和用词):`/Users/jin.xiao/workshop/deeparch-atlas/atlas-output/linux的进程调度器-20261103/linux-sched-epN-*.vmd`,总结卡 JSON 样例 `.../linux的进程调度器-20261103/pics/ep3-summary-card.json`,覆盖表样例 `.../linux的进程调度器-20261103/video-notes/coverage-ep3.md`。
4. 原文 `D/cgroup核心原理-atlas.md`(只读)。约束速查在第 54~86 行。各篇行号:
   - ep1 What:87~1085
   - ep2 Why:1086~2516
   - ep3 How:2517~4237
   - ep4 Origin:4238~4914
   - ep5 Deep:4915~6057
   - ep6 Comparison:6058~6168
   - ep7 Synthesis:6169~6425(公开博文,可单独读)

## 素材
- 图:原文每张 SVG 都已转成 `D/pics/<同名>.png`(1920 宽,中文正常,日志图等宽对齐)。vmd 里写 `pics/<名>.png`。
- 源码(Linux 7.0 上游副本):`D/stages/05-deep/src/linux-v7.0/`,目录结构同内核源码树(如 `kernel/sched/fair.c`、`mm/memcontrol.c`、`kernel/cgroup/cgroup.c`)。
- 实验日志:原文代码块里的命令和输出都是日志原文。
- 人物没有照片:Paul Menage、Tejun Heo、Paul Turner、Johannes Weiner 都只能用 text / spotlight / layers 介绍,不要用人物场景(渲染器会自动搜图,配错人)。

## 产物(每集三个文件,不多写)
1. `D/video-notes/ascii-src/cgroup-epN-<slug>.vmd`(slug:ep1-what / ep2-why / ep3-how / ep4-origin / ep5-deep / ep6-comparison / ep7-synthesis)。ASCII 场景按「列模型」写:只用半角空格补齐,一个汉字算 2 列;主控会用 `ascii_px_align.py` 换成按像素对齐的版本。
2. `D/pics/epN-summary-card.json` + `D/pics/epN-summary-card.png`(`scripts/summary_card.py` 生成;takeaway 里可以用 `**` 加粗,那是卡片不是旁白)。
3. `D/video-notes/coverage-epN.md`:原文必讲项 → 画面载体 → 场景号 → 处理(保留 / 合并 / 压缩 / 更正);末尾列「相对原文的事实修正」(没有就写「无」)。

## 篇幅
- ep1 约 9~11 分钟;ep2、ep3、ep5 约 12~15 分钟;ep4 约 9~11 分钟;ep6 约 5~7 分钟;ep7 约 9~11 分钟。
- 每分钟约 2.5~3 个场景、300 字口播;`review_ep.py` 会打估时。

## 结构(必须)
- 顶部:`# 第 N 集 X 阶段 — <中文集标题>`,下一行 `[intro-line] <一句话,复用 H1 里的技术词>`。
- 场景 1:开场 spotlight,画面两行(如「现在我们来看 What 阶段 / cgroup 到底是什么?」),旁白说本集讲什么、和前后集的关系。
- 原文里的手绘图(文件名不含 `-shot-` 的)每张都要用 `[visual: html_slide image="pics/xx.png" title=...]` + `[step: auto]` + `scroll auto` 完整展示,并逐区解说。
- 终端留档图(`-shot-`)挑承载关键数字的展示(至少一半),同样用 html_slide;其余的数字可以在 text / ascii 场景里引用。
- 倒数第二场:本集总结卡 `[visual: html_slide image="pics/epN-summary-card.png" title=...]`。
- 最后一场:「本集就到这里,下集见」+ 下一集预告(spotlight 或 title)。不要自己写「一键三连」,解析器会自动补。ep7 最后一场回到全片开头的问题收束。

## 全系列统一的说法
- 系列的大问题:Linux 内核统一管理资源的问题。三个问题:① 往 `cpu.max` 写 `50000 100000`,内核怎么让这组进程最多只用半颗核;② 容器 OOM 只杀容器里的进程,这个边界是谁划的、用量怎么记;③ cgroup 用什么架构控制各种资源、怎么融入内核、设计原则是什么。
- 五条约束,画面写 `C1·按组限制合计用量` 这种「编号·短名」;旁白读作「C1,按组限制合计用量」。名字不许改:
  - C1·按组限制合计用量
  - C2·记实际用量,超限处理看资源类型
  - C3·内核负责执行,配额由外部设定
  - C4·在内核已有代码路径上记账,开销要小
  - C5·所有资源共用同一套分组
- 八个设计想法(第七篇的说法,名字不许改):分进程组记账 / 将工具统一成框架 / 公共框架加资源插件 / 复用内核已有路径记账 / 记账时同步检查限额 / 按资源特性决定超限处理 / 提供机制,策略由需求定制 / 用统一的方式管理所有资源。第三篇里的「五条设计原则」是其中五条。
- 术语:组籍(进程身上记录它属于哪个组的指针,内核里叫 `css_set`)、控制器、登记表(控制器交给核心的回调函数表,`struct cgroup_subsys`)、接入点(内核本来就要走的路上,cgroup 多执行一步的位置)。第一次出现时用一句白话解释。

## 讲解规则(用户定下的,必须遵守)
- 白话。用户原话:「以后都要说白话」。旁白和画面文字都直接说机制做了什么:主语 + 动作 + 对象。不用口号、四字格、对仗句,不用拟人(「下场」「叫人」「监工」),不用比喻(「零钱」「挂牌」「闸门」「搭车」「骨架」「账本」「加税」「撞线」「隐身」)。原文日志里保留了「零钱」「挂牌」「闸门」「公共池」等旧叫法:日志画面可以照原样出现,旁白要换成白话(本核预领的额度 / 限流标记 / 防重复检查 / 组的总额度)。`review_ep.py` 会查这些词。
- 类比少用:合租公寓分户水电表是 ep1 的主类比,ep1 可以用一处,后面最多回扣一句;用户是数据库背景,拿数据库比可以,但要明说「拿数据库比」,一集最多一处。
- 两条及以上链路/路径对比,画 ASCII 双栏或双泳道框图(┌─┐ + ▼),不用 `(a) --x--> (b)` 文字箭头串。
- 原理段先讲「为什么这样设计可行、为什么在工程上划算」,再进代码;只讲事实不讲为什么不合格。
- 代码场景用 `code_explain`,讲清函数作用、调用参数、意图;右侧 HIGHLIGHT 可画小 ASCII 结构图。源码必须是 `D/stages/05-deep/src/linux-v7.0/` 下副本的逐字连续子串(tab 缩进原样保留,可截连续片段),标题写明出处,如「(Linux 7.0 kernel/sched/fair.c)」。原文伪代码上屏时标题必须含「伪代码」或「示意」。
- 实验场景:先讲实验设计和预期,再讲命令和结果。命令和输出上屏用 `code_explain lang=bash`,标题含「实测」,内容必须逐行取自原文代码块(`review_ep.py` 会对原文查)。数字一律以原文为准。
- 缩写读英文原文:cgroup、OOM、CPU、IO、PSI、bpftrace、fork 等不要逐字母念成中文怪音。
- 第二人称「你」开场,具体数字;句长约 30 字,单段旁白不超过 150 字。
- 旁白零免责:不出现「待核 / 未核实 / 推断 / 验收」之类;原文标为推断或待核的数字,旁白不说具体值或只说量级,结论用「看起来是 / 原因可能是」这种平常说法也不行,直接不讲那条。
- 旁白禁词(`review_ep.py` 会查):atlas、facetime、html_slide、code、spotlight、adv_animation、statemap、recap、analogy、layers、timeline、ascii、场景类型、visual: ;旁白不写 markdown(`**`、反引号、#)。
- 画面(非代码场景)不用 `→`、`①~⑨` 等会变方块的字符,用 `->` 和阿拉伯数字;ASCII 每行不超过 70 列、每图不超过 25 行。
- 不用 diff / data / news_title 场景(anthropic 主题 lint strict 会拦);对比一律 ASCII 双栏。
- 场景类型尽量丰富:spotlight、text、ascii、layers、timeline、statemap、code_explain、html_slide、title;sidebar 可用。

## 各集重点
- ep1 What:§0 四种资源先后出事的现场;一句话定义;合租公寓类比;一个目录四个文件;从 `docker run` 倒推数字是谁写进去的(Docker → containerd → runc → 内核);从进程查组;一棵树 + 一排控制器的全景;它在系统里的位置。
- ep2 Why:不用 cgroup 的现场(690 → 226);nice / taskset / setsid / ulimit / 全机 OOM 各自管不住在哪;磁盘与进程数;「你的第一版」;框架放在哪;核心想法(组籍、用量记录、限额、树);v1 的四个问题和 v2 的改法;四种资源放进组里重演;几个旋钮;五条约束怎么得出。
- ep3 How:三件事(组籍、账、接入点);核心建树、控制器依次接入;五个接入点(fork、调度结算、缺页、提交 IO、退出)各自的调用栈与实测;CPU 额度用完怎么停、内存超限先回收再杀、进程数拒绝和磁盘排队三种超限处理;把用量记到树上;worker 的一生回放;最小伪代码;五条设计原则。
- ep4 Origin:2006 年 Paul Menage 动手时桌上有什么;把分组抽出来;为什么先有多棵树;Paul Turner 给 CPU 加绝对上限;Johannes Weiner 的内存控制器两个阶段;Tejun Heo 把多棵树收回来;推演和历史对上的、没对上的。原话只用原文里的引文,不自己编。
- ep5 Deep:v7.0 源码三条主线:`cpu.max` 写入 → 记账(两层开关、每核领 5 ms)→ 限流 → 周期补额度;内存记账(64 页一批、沿父组逐层比)→ 回收 → 组内 OOM 打分 → 多杀一个的原因(遍历时看不到正在退出的进程,但它的内存还没还)与三种改法;公共框架(`css_set`、`cgroup_subsys`、按表逐个调用)。先讲 §2 一个 worker 一生的时间线。
- ep6 Comparison:Windows Job Object 对照;内存超限一个杀进程、一个拒绝分配;为什么 Windows 不需要「公共框架加资源插件」。
- ep7 Synthesis:按博文的顺序:问题 → 五条约束 → 八个想法 → 拿八个想法设计数据库资源组 → 设计决策总表 → 这套做法的边界。最后一场回到第一集开头那台机器和三个问题。

## 自检(返回前做完,并在汇报里贴结果)
1. `venv/bin/python scripts/vmd_lint.py <你的 vmd> --theme anthropic` 无 error。
2. `venv/bin/python D/video-notes/review_ep.py <你的 vmd>` 输出 `ISSUES 0`。
3. 用 Read 看一眼自己的 summary-card.png,没有文字溢出、没有方块字。
4. 汇报控制在 40 行内:场景数、口播字数、估时、类型分布、用到的原文图、源码出处列表、相对原文的事实修正、没覆盖的原文必讲项及理由。
