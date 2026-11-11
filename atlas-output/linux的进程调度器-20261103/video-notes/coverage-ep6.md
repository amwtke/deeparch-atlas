# ep6 Comparison 覆盖与证据矩阵

主角色：对照（Windows NT）；输入原文 `linux的进程调度器-atlas.md` 第 2566–3026 行（Comparison 篇 §0–§9 + 出处）+ 第 53–100 行约束速查 + 第 3835–3851 行收尾核实 #30–#46（以核实结论为准）。未改动源 MD、stages、原 SVG。

主链：同一个按键两种理由 → 四层鸟瞰 → Cutler 与 NT 出发点 → 三件事（策略分岔 / 机制同构 / 可调位置）→ 谁先上（树对位图、ReactOS 选人示意、动态提升、算例差一档 + 真权重表、不饿死、为什么 Windows 敢用等级）→ 跑多久（update_deadline 真源码、同级三线程算例）→ 放哪个核（理想核对 prev_cpu、无空闲核时分岔）→ 换人（__switch_to_asm 真源码、ReactOS KiSwapContext 示意、五条逐条成立、唯一差异无 fork、为什么同构）→ C7 Job 对 cgroup → C8 SQLOS 对 sched_ext → SQL Server 三条理由 → 死循环思想实验 → 约束回扣 → 总结卡 → ep7 预告。

| 原文必讲项 | 证据载体 | 场景 | 处理 |
|---|---|---|---|
| 篇首出处口径（文档 / WI / ReactOS） | 9、23 标题「示意，非微软源码」+ 9 旁白一句 | 9、23 | 压缩：只在用到 ReactOS 时说明 |
| §0 三件事 + 表 | layers | 6 | 保留；「越靠近硬件越像」作为全集线索在 3、26、32 回收 |
| §1 概览图五件事 | pics/06-overview.png | 3 | 整图保留，按四层讲 |
| §2 设计动机（初衷 / 擅长 / 不擅长 / 场景） | facetime Dave Cutler + text + sidebar | 4–5 | 保留；典型场景并入 28–29（SQL Server），容器用 Job 未核实 #38 不讲 |
| §3.1–§3.2 数据结构表 | ascii 双栏 | 8 | 保留：树对 32 链表 + 位图、选人复杂度、不饿死方式 |
| §3.2 ReactOS 选人代码 | code_explain（标题「示意，非微软源码」） | 9 | 原文片段原样（去掉行尾注释）；回扣 2002 O(1) |
| §3.3 动态提升来源表 + 三条硬规则 | ascii | 10 | 保留；「前台再加最多 2」按 #33 部分已核改述为「再加一点」 |
| §3.3 06-priority-boost 图 + 算例 1 | pics/06-priority-boost.png | 11 | 整图保留，按算例 1 讲 |
| §3.3 算例 2 差一档 | ascii 双栏 + sidebar（rt 类） | 12 | 保留；Windows 侧「千分之几」为推算 #41，改述为「几乎拿不到」 |
| nice 权重 1277 / 1024 | Linux 6.12 kernel/sched/core.c `sched_prio_to_weight`（L10012–10021） | 13 | 新增可复查源码（#43 已核） |
| §3.4 防饥饿扫描 | ascii 双栏 | 14 | 保留 300 滴答 / 约 4 秒 / 16 / 10（#32 已核）；ReactOS balmgr 代码片段不上屏 |
| §3.5 为什么 Windows 不记账 | ascii 双栏 + sidebar | 15 | 保留；O(1) 加减分幅度（±5，#44 未核实）不讲数字 |
| §4.1–§4.2 片长逐项 | Linux 6.12 kernel/sched/fair.c `update_deadline`（L1003–1019 段） | 16–17 | 新增可复查源码；0.75 ms × (1+log2 min(核数,8)) 进 HIGHLIGHT |
| §4.2 Windows 量子 / Vista 按周期计 | 18 的 ascii 注脚 + sidebar | 18 | 保留（#30、#31 已核）；ReactOS `CLOCK_QUANTUM_DECREMENT 3` 细节文档保留不进视频 |
| §4 算例（3 / 9 / 330 对 31 / 94 / 32 对 187 / 560 / 5） | ascii 表 | 18 | 保留；结论「跑多久被谁先上决定」 |
| §5.1 每核队列骨架 + Server 2003 | spotlight | 19 | 保留前半（#34 前半已核）；「Windows 8 起几核共享」未核不讲 |
| §5.2 选核逐项 + 算例 | ascii 双栏 | 20 | 保留理想核 / prev_cpu / 有空闲核结论一致 / 无空闲核分岔；「Windows 无周期均衡」#36 未核，改述为「决定集中在就绪那一刻」；大小核 #40 不讲 |
| §6.2 Linux __switch_to_asm | Linux 6.12 arch/x86/entry/entry_64.S L183–193 逐字 | 22 | 用真源码替换原文的单行合并写法 |
| §6.2 Windows KiSwapContext | code_explain（ReactOS amd64 示意） | 23 | 原文片段，删注释与省略行 |
| §6.3 逐条对照表 + IRQL 概念 | ascii 表 + sidebar | 24 | 保留五条；CR3 先后顺序、ATTEMPTED_SWITCH_FROM_DPC（#42 未核）文档保留不进视频 |
| §6.4 唯一不同：没有 fork | text + sidebar | 25 | 保留 |
| §6.5 为什么同构 | spotlight | 26 | 保留三样：栈指针、ABI、接班者 |
| §7 C7 Job 对象 | ascii 双栏 + sidebar | 27 | 保留权重 1~9 默认 5、硬上限、最小最大保证；「自 Windows 8」与「容器用它」#38 未核不讲 |
| §7 C8 旋钮 + 用户态自调度 | ascii 双栏 + sidebar | 28 | 保留；UMS Win11 下线（文档已核） |
| §7.1 SQL Server 三条理由 + 算例 | ascii 双栏 + sidebar | 29 | 保留等级 7、4 ms、协作式（#39 已核）；37 万倍算例口播压成「被换下就是几百毫秒」；fiber 模式弃用、PREEMPTIVE 模式文档保留不进视频 |
| §7.1 反问 2 死循环 + 反问 3 监视线程 | timeline | 30 | 合并为一个思想实验；「每调度器只让一个线程可运行」#45 未核，表述为「其他线程在等自己的事件、不在就绪队列」；「调度器不让出」错误不讲；Go / ScyllaDB #46 不讲 |
| §8 约束回扣表 | ascii 表 + sidebar | 31 | 保留 2 同构 / 1 差参数 / 5 分岔 |
| §9 呼应灵魂问题 | 31 旁白 + 33 | 31、33 | 保留「cgroup / sched_ext 增强的正是 Windows 结构上给不了的两样」 |
| 出处列表 | — | — | 文档保留，不进视频 |
| 本集总结 | pics/ep6-summary-card.png | 32 | 新增 |

## 相对原文的事实修正 / 口径收紧

1. 「前台进程再加最多 2」（ReactOS `PsPrioritySeparation`，#33 部分已核）→ 画面写「再加一点」，不给具体数字。
2. 算例 2 Windows 侧「千分之几」（#41 推算）→ 改为「几乎拿不到 CPU」。
3. 「Windows 没有周期性负载均衡、空闲核扫别核队列」（#36 未核部分）→ 不作断言，只讲「选核决定集中在线程就绪那一刻」。
4. VMS 32 级划分（#35 中未核部分）→ 人物卡只写「带来了 VMS 的调度思路」，32 级 / 低 16 分时 / 高 16 实时 作为 NT 自身事实（微软文档已核）呈现。
5. SQLOS「每调度器任一时刻只让一个工作线程可运行」与「调度器不让出」错误（#45 未核）→ 不作为 SQL Server 的实现事实陈述；思想实验只用「其他线程在等自己的事件、不在就绪队列」这一协作式调度的定义性前提。
6. 原文 §6.2 把 Linux 六条 push 合成一行，视频换成 v6.12 entry_64.S 的逐字原文。
