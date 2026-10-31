# ep6 Comparison 覆盖与证据矩阵

主角色：综合 / 评论（横向对照）。输入原文 `Linux进程全链路-atlas.md` 第 3307–3648 行（Comparison 篇）、第 46–103 行约束速查、第 4067–4118 行收尾核实表（Comparison #1–#10）。只写本集文件，未改源 MD、stages、原 SVG 或其他集。

主链：同一个 hello 两种出生（fork+execve 对 CreateProcess）→ 哪些是约束逼的、哪些是血统 → 全景图三行 → Cutler 与 NT 出发点 → 创建：两步一窗对一步一表（七阶段、CreateProcessW 原型、窗口代价、内核藏着的 fork、各自代价）→ 调度：看级对看账（32 级、加分与衰减、为什么看级、vruntime_eligible 真码、SQLOS 现实版）→ 写时拷贝：页归谁（NT 四概念、do_wp_page 真码、一半同一半无、记账预扣对超售）→ 约束回扣同/异 → 判别法 → 总结卡 → 下集预告。

| 原文必讲项 | 证据载体 | 场景 | 处理 |
|---|---|---|---|
| 开篇锚点：hello 在两套内核里的出生 | title + 口播 | 2 | 保留；Redis bgsave 移到场景 12 例子 |
| §1 概览图 06-overview | pics/06-overview.png | 3 | 整图保留；口播更正图中「每核就绪队列 Win7,2009」为核实后的「队列 2003 年就有、2009 年拆全局锁」 |
| §2.1 NT 初衷（Cutler、三子系统、VMS、NT 3.1） | Dave Cutler 人物页 | 4 | 保留；日期按核实 #1（1988-10 加入，1993-07-27 公开发布） |
| §2.1 擅长 / 不擅长 / 典型应用 | text + sidebar | 5 | 保留；典型应用压成 SQL Server 与 Chrome 两例，IIS、WSL1 分散到 11 |
| §0.1 / §3.1 复制再改对一次造好 | spotlight + ASCII 双栏三段 | 6–7 | 保留；C3、C4 点名；不可回头点对照 |
| §3.2 七阶段表 | timeline 七步 | 8 | 保留阶段与执行位置；Linux 对应物在口播点名 |
| §3.2 窗口去哪了：参数表 | CreateProcessW 原型（Microsoft Learn 文档逐字）+ 四段高亮 | 9 | 新增可复查证据：原文只列参数名，未给原型 |
| §3.2 属性列表 / PROC_THREAD_ATTRIBUTE_HANDLE_LIST、posix_spawn 同款 | text | 10 | 保留；HotOS 2019 多线程 fork 半残放入例子（malloc 锁） |
| §3.5 内核藏着 fork、WSL 博客原话、三个来源 | text + 例子 | 11 | 保留；原话按博客意译，三来源合进口播 |
| §3.4 代价行（CreateProcess 慢、fork 随父进程、Cygwin、Redis for Windows） | text + 例子 | 12 | 保留；数字全部按核实口径 |
| §0.2 / §4.1 级对账 | spotlight | 13 | 保留 |
| §4.2 32 级与优先级类表、选人规则原话 | layers | 14 | 保留；规则按 learn.microsoft.com Scheduling Priorities 原文复述 |
| §4.2 动态加分、每片减一、反饥饿 | timeline（编辑器线程实例） | 15 | 保留；加分值按核实 #4，反饥饿按核实 #5（约 4 秒、抬到 15、每秒扫） |
| §4.2 时间片、§4.5 为什么 NT 这么选、优先级反转 | text + sidebar | 16 | 保留桌面优先、VMS 血统、交给开发者；片长按核实 #6；AutoBoost 年份原文自相矛盾，未入片 |
| §4.3 EEVDF eligible = 拿到的少于应得 | vruntime_eligible 真码 + 四段高亮 | 17 | 新增可复查证据：先在 16 推出「必须记账」，再用源码验证 |
| §4.4 / §4.6 五元组差异（守恒量对经验值） | ASCII 双栏 + 共同约束框 | 18 | 保留；C1、C2 点名 |
| §4.7 你的视角：SQLOS 绕开的是抢占 | text + 例子 | 19 | 保留「病根是抢占」、4 ms 配额（核实 #10）、preemptive 模式；三选项分量表文档保留 |
| §0.3 / §5.1 这一页归谁 | spotlight | 20 | 保留 |
| §5.2 section、prototype PTE、working set、commit charge | layers 四行 | 21 | 保留四概念与 Linux 对应物；软硬缺页按 Working Set 文档原文 |
| §5.3 判据③ 独占才复用 | do_wp_page 尾段真码 + 三段高亮 | 22 | 保留：先口播推出「必须问还有别人吗」再看代码 |
| §5.4 / §5.6 一半同一半无、三轮补丁、WSL1 | ASCII 双栏 + 差异根框 | 23 | 保留 |
| §5.4 / §5.5 记账：commit 预扣对超售、Redis overcommit | text + 例子 | 24 | 保留；C6 点名 |
| §6 约束回扣（同 / 异） | text + sidebar C5 C6 C7 | 25 | 保留；同年每核队列为例 |
| §7 呼应你的问题、§3.6 / §4.6 / §5.6 判别法 | spotlight + 总结卡 | 26–27 | 保留判别法；六问逐条映射文档保留 |
| §2.1 本份不展开的三问（APC、对象引用计数、ETW） | — | — | 文档保留；引用计数在 25 带过 |
| §4.2 切换：Windows x64 非易失寄存器 8 + 10 对 SysV 6 | — | — | 文档保留（图 06 中可见），本集不单列 |
| §8 资料来源与待核 | 本文件 | — | 不朗读 |

源码与文档（Linux 固定 v6.12，经 jsDelivr gh/torvalds/linux@v6.12 取原文，存 video-notes/src/；三段摘录与原文逐行一致，已做子串比对）：

- kernel/sched/fair.c L709–740：注释（eligible 定义、lag 算式）+ `vruntime_eligible`；口播另点 `pick_eevdf` L907 的「在有资格的里挑 deadline 最早」不入画面。
- mm/memory.c L3723–3745：`do_wp_page` 尾段（匿名页独占 / `wp_can_reuse_anon_folio` 复用、否则 `wp_page_copy`）；高亮引用 `wp_can_reuse_anon_folio` L3585。原文 §0 写判据③ 在 `memory.c:3724`，即本段第 2 行，与 v6.12 一致。
- Windows 侧无源码：CreateProcessW 原型逐字取自 https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-createprocessw（2026-10-31 抓取，存 video-notes/src/msdocs/CreateProcessW.prototype.txt）；选人规则、加分只限 0~15 与每片减一、软硬缺页定义分别与 learn.microsoft.com 的 Scheduling Priorities、Priority Boosts、Working Set 页原文核对（抓取文本存 video-notes/src/msdocs/*.txt）。

人物：Dave Cutler，沿用上一部已目检的维基百科条目首图（Commons File:DavidCutler_WindowsAzure.JPG，CC BY 3.0），复制到 pics/person-dave-cutler.jpg 并再次目检，来源记于 pics/portrait-sources-ep6.json。

事实修正与收紧：

1. 概览图「每核就绪队列(Win7,2009)」按核实 #7 改口播：每核队列 Server 2003 已有，Windows 7 / Server 2008 R2 拆的是全局 dispatcher lock；图本身未改。
2. fork 20 GB 复制页表：原文 §3.4 与图写 100~200 ms，按收尾核实 Deep #14 放宽为 100~260 ms。
3. CreateProcess 代价：原文「毫秒级」未入画面，按核实 #3 写「比 fork 加 exec 慢一个量级以上」；Cygwin 按核实 #2 写「几倍到几十倍」。
4. AutoBoost：原文写「2019 年后的 AutoBoost(Windows 8.1 起)」，年份自相矛盾且未核，VMD 不提 AutoBoost。
5. Redis for Windows：按核实 #9 写「堆放进内存映射文件、全部页 COW 保护、子进程持句柄」；「2016 年停止维护」留在文档。
6. 每核队列同年：Linux 侧以 2003 年底发布的 2.6 为准（O(1) 调度器每核 runqueue）。

验收：28 场景、9 种视觉类型（text 8、spotlight 6、ascii 3、code_explain 3、html_slide 2、layers 2、timeline 2、facetime 1、title 1）。口播（含 example）约 3467 字，按上一部同集实测速率（3375 字 → 641 秒）折算约 658 秒，约 11 分钟（实际以 TTS 为准）。`vmd_lint --theme anthropic`：0 错误、3 告警（三段源码多段高亮的 CODE-MULTI-HL，与上一部一致）。旁白与例子无 atlas、无场景类型术语、无免责/制作用语；画面与侧栏无黑名单豆腐字符（箭头、带圈数字、≠ 已替换）。总结卡 pics/ep6-summary-card.png 1920×1080 已目检无溢出。

分P标题建议：P6 Comparison：Windows 没有 fork，创建、调度、写时拷贝各差在哪
