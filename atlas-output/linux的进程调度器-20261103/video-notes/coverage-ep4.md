# ep4 覆盖与证据矩阵（Origin）

主角色：来路 / 演化史。输入原文 `stages/04-origin/04-origin.md`（收尾核实后版本：§12 一手 48 ~ 52，§13 五项升为一手，待核 #40 ~ #49 已结），另读 `stages/03-how/03-how.md` 顶部约束速查（C1 ~ C8）。未改动源 MD、stages、原 SVG。

主链：1995 年写在论文里、2023 年才进内核 → 三次换代各改写一条约束（§0）→ 接力图（§1）→ 序章时间线 V7 / 4.3BSD / 0.01 / 2.4（§2）→ Ingo 与 O(1)：不留活口、每核一把锁、估计器可被骗（§3）→ Con 与 RSDL：不惜一切代价绝对公平 → Ingo 两周写出 CFS → 公平定义差一个词 → 一个人的离开（§4）→ 学术线 Waldspurger 的票、Stoica 的合格时间 → 为什么等 28 年（§5）→ Paul Turner 补组：autogroup、带宽、PELT（§6）→ Peter 翻旧账、删启发式、delayed dequeue（§7）→ Tejun 开口子、Peter 反对、Linus 以治理理由合并（§8）→ 反事实 2008（§9）→ 每一代欠下一代的债（§10）→ 总结卡 → 下集预告。

| 原文必讲项 | 证据载体 | 场景 | 处理 |
|---|---|---|---|
| §0 三件事（2002 / 2007 / 2023 各改写哪条约束） | layers + sidebar C2 C3 C4 C5 | 3 | 保留；旁线一行点名 |
| §1 概览图 04-overview | pics/04-overview.png | 4 | 整图保留，按主线 / 旁线 / 学术线三行讲 |
| §2 序章 V7 setpri / 4.3BSD schedcpu / 0.01 counter / 2.4 goodness + runqueue_lock | timeline 四行 | 5 | 保留四个节点；源码片段不上屏（0.01 / V7 的两行在 timeline 文字里） |
| §3 Ingo 2002 信：两个反问、8 路机器、不留活口、每核锁、140 级位图、1.57 μs | facetime（照片已核）+ text + example | 6、7 | 保留原话；1.57 μs 为控时长删去（文档保留） |
| §3 死胡同：sleep_avg、fiftyp.c 等攻击程序 | spotlight | 8 | 保留"9 ms 算 1 ms 睡"的骗法；程序名只提 fiftyp |
| §4.1 Con 2007-03-04 RSDL 公告与同日回信 | facetime（无照片，占位框） | 9 | 两句原话全保留 |
| §4.2 Ingo 2007-04-13 CFS 公告：彻底重写 / 无启发式 / 调度类 / 功劳记给 Con / 80% 一句话 | text + example + sidebar C2 C7 | 10 | 保留；"缩小 700 行 / +1454 −1133" 为控时长删去 |
| §4.3 公平定义差一个词（算不算睡眠时间）、Con "proportional slowdown" | ascii 双栏 + sidebar C2 C3 | 11 | 保留；kernelnewbies 二手转述不进旁白 |
| §4.4 2.6.23、APC 退出、7-28 澄清、Linus "小的增量改进"、MuQSS 自述基于 EEVDF | spotlight | 12 | 保留；APC 采访只用"宣布退出"事实（原文 §13 部分核实）；Linus "ignoring reality"（一手 49）未用 |
| §5.1 Waldspurger 1994：ad-hoc 优先级、票、币 | facetime（照片已核） | 13 | 保留 |
| §5.2 Stoica 1995：摘要三句、eligible time 独有特征 | facetime（照片已核） | 14 | 保留；准入策略那句（C7）为控时长删去 |
| §5.3 为什么等 28 年：三原因三约束 | layers + sidebar C2 C4 C3 | 15 | 保留；Peter "双树"原话压成一句 |
| §6.1 组调度 2.6.24、autogroup、Linus 2010-11-15 原话 | text example | 16 | 保留"惊讶于这么小 / 杀手级特性"；commit 号不念 |
| §6.2 带宽控制 RFC 2010 "绝对量"、拒绝复用 rt 带宽、v7 补丁标题、3.2 | text + example + sidebar C6 C8 | 16 | 保留 |
| §6.3 PELT 2012 原话、3.8；NUMA 三路线；EAS 5.0 | text 第三行 + 旁白 | 16 | PELT 保留；NUMA 三路线与 EAS 只在接力图场景点名（文档保留） |
| §7 Peter 2023-03-06：latency-nice、dark crypts 13 年、icky heuristics、much better defined | facetime（无照片） | 17 | 四句原话全保留 |
| §7 v2 补丁标题路线图、sched_runtime 接口、核心 commit 说明、delayed dequeue、6.13 lazy preemption | text + example + sidebar C3 C1 | 18 | 保留；6.6 / 6.12 版本在 facetime 要点里 |
| §8 Tejun 2022-11-30 RFC：通用调度器、未部署、安全承诺；Peter "I hate all of this"；Tejun "由 Linus 决定" | facetime（照片：GitHub 头像，已目检） | 19 | 保留 |
| §8 Linus 2024-06-11：no reason to delay、树内一起做、参与门槛；2024-09-21 合并 | spotlight | 20 | 保留；"6 月 11 日"改"6 月"（NUM-RECAP） |
| §9 反事实：2008 年合并会怎样，三样同时到位 | text + example + sidebar C3 C4 C8 | 21 | 保留 |
| §10 回扣表（11 行） | layers 六行 + sidebar | 22 | 压成六行：衰减优先级 / O(1) / CFS / 带宽与 PELT / EEVDF / sched_ext；NUMA、EAS 行并入接力图 |
| §11 呼应三代换代 | 总结卡 | 23 | 化入总结卡 |
| §12 一手资料 52 条 / §13 无一手 | — | — | 文档保留，不朗读；二手项不进旁白 |

事实处理：
- 所有年份、日期、引语均取自 04-origin.md 正文与 §12 一手条目；Ingo O(1) 首帖按待核 #41 写 2002 年 1 月 3 日（美东）。
- Con 的退出只说"2007 年 7 月宣布退出"，不引 APC 原文（§13 部分核实）。
- "autogroup 进 2.6.38"、"PELT 进 3.8"、"EAS 5.0"、"NUMA 三路线"未进旁白（控时长），接力图场景一句带过。
- 无 Cn 的 facetime / spotlight 场景旁白不提约束编号；提到编号的 text / layers / ascii 场景均配 sidebar 列出约束短名。
- 画面与侧栏无 → 与带圈数字（用 -> 与阿拉伯数字）；ASCII 双栏按渲染器字宽（ASCII 13 px / CJK 22 px）用半角与全角空格补齐，预览出帧目检框线对齐；facetime 要点每行压到 ≤ 22 个中文宽度，出帧无截断。

人物：facetime 6 位 —— 有照片 4（Ingo Molnár / Carl Waldspurger / Ion Stoica / Tejun Heo，来源见 pics/portrait-sources.json），无照片占位框 2（Con Kolivas / Peter Zijlstra）；Paul Turner、Mike Galbraith 在 text 场景与旁白中出现；Linus Torvalds 只在旁白与 spotlight 引语中出现（本集不做人物场景，避免与上一轮重复）。

验收：24 场景，8 种视觉类型（spotlight 5、title 1、layers 3、html_slide 2、facetime 6、text 5、ascii 1、timeline 1）；口播 4296 字（含 example），按 5.4 字/秒加场间 1.5 秒估约 13.9 分钟（上一轮同口径估 11.1 实际 9.4，预计实际 11.5 ~ 12 分钟）。`vmd_lint --theme anthropic --profile generic`：0 错误、1 告警（PATCH-NEW-CODE：本集无源码场景，属历史叙事集）。`review_ep.py`：ISSUES 0。总结卡 pics/ep4-summary-card.png 1920×1080 已目检。未新建 story 插件。

分P标题建议：P4 Origin：O(1)、CFS、EEVDF、sched_ext，五个转折点和他们的人
