# ep2 覆盖与证据矩阵

主角色：原理 / 机制（约束推导）；输入原文 Why 行 426–800，约束速查行 46–103，收尾核实行 4067–4118（Why #1~#3 及 What #1/#2、Deep #14 的核实口径）。未改动源 MD、stages、原 SVG 或其他集文件。

主链：裸机上一个程序独占一切（进程无意义）→ 七刀路线 → 第一刀 CPU 等盘 → 多道 + 可存取现场（C1，源码验证现场只有 7 个 8 字节）→ 第二刀霸台 → 闹钟 + 靠历史猜的排班（C2）→ 第三刀三种伤害 → 三道闸（C3）、闸的代价、clone 标志位即隔离级别、与事务隔离对照 → 第四刀文件变地址空间 → ELF / 只建地图 / copy on write（C4）+ Redis bgsave 触发链 → 第五刀三扇门一扇出口（C5，源码验证出口循环）→ signal 延迟投递 → 第六刀 exit 两段式（C6，源码验证僵尸可被 autoreap 绕开）→ 第七刀每核队列 + IPI（C7）→ 七条对四幕 + 压缩记录 → 这些不算约束 → 三个洞察 → 总结卡 → 预告 How。

| 原文必讲项 | 证据载体 | 场景 | 处理 |
|---|---|---|---|
| 开场：裸机独占 CPU / 内存 / 设备 / 无账本；「进程」无意义 | 标题 + 文字 + 例子 | 2–3 | 保留；Arduino、GRUB 例子；0x7C00 / UEFI 细节与纸带例子文档保留 |
| 七刀七条总路线 | 分层图 | 4 | 新增路线图，便于观众对号 |
| 第一刀：速度差 10^4~10^7、报表作业 20%、IBM 7090 / 711 读卡机 | 文字 + 例子 | 5 | 按收尾核实 Why #1：290 万美元、250 张/分 |
| 多道程序 + 现场可存 + 中断雏形；C1 | ASCII 双栏（单道 vs 多道） | 6 | 保留 |
| 现场是一组有限寄存器（task_struct 现场字段） | Linux 6.12 arch/x86/include/asm/switch_to.h L23–47 真源码 | 7 | 原文无源码，新增可复查证据：inactive_task_frame 七个 8 字节 + fork_frame 里的 pt_regs |
| 第二刀：协作式（Win 3.x / Mac OS 9）、100 ms、CTSS 1961 | 文字 + 例子 | 8 | 保留；「100 ms 是目标」提前在侧栏点出 |
| 闹钟 + 排班；调度只能用历史猜未来（MLFQ→CFS→EEVDF）；C2 | 金句卡 | 9 | 保留 |
| 第三刀三种伤害（读 / 写 / 拖死） | 文字 + 例子 | 10 | 保留学生读成绩、DOS 野指针、cli |
| 三道闸表（伤害 / 资源 / 闸 / 硬件开关）+「不是禁止而是经内核之手」+ 0x1000 翻到不同物理页；C3 | ASCII 表 | 11 | 保留；「闸后还能怎么用」一列并入旁白 |
| 闸的代价表（页表 40 MB、CR3 + TLB、syscall 80/200 ns、tick） | 文字 + 例子 | 12 | 按 Why #2 核实值；vDSO / io_uring / NO_HZ 留在侧栏 |
| clone flags 就是隔离级别 | Linux 6.12 include/uapi/linux/sched.h L11–19 真源码 | 13 | 原文只列宏名，新增源码；fork 不带 / pthread_create 带 VM FS FILES SIGHAND THREAD |
| 与数据库事务隔离对照 + 两处本质不同（语义 vs 地址、无 commit）；PG 进程 vs MySQL 线程 | ASCII 双栏 | 14 | 保留；锁超时 ↔ 抢占、DBA ↔ ring 0 两行文档保留 |
| 「这道闸不是唯一形状」（JVM / Wasm / eBPF、微内核） | — | — | 文档保留（Comparison / Synthesis 集展开） |
| 第四刀三个问题（格式约定、装不下、复制要便宜） | 文字 + 例子 | 15 | 保留 |
| C4 三个面各逼出一样东西（ELF / 只建地图 / COW）；C4 | ASCII 三栏 | 16 | 保留 |
| COW 真实触发链 + 缺页成为最常用工具 | 时间线（Redis bgsave） | 17 | 按讲解规则写谁先写谁缺页、缺页里分新页改映射；数字按 Deep #14（20 GB 100~260 ms）与 What #2（4 KB COW 约 2.3 μs） |
| 第五刀：内核没有自己的 CPU；三扇门表；出口；C5 | ASCII 竖链 | 18 | 保留 |
| 一切挂在出口上（调度、signal） | Linux 6.12 kernel/entry/common.c L90–134 真源码 | 19 | 原文无源码，新增：NEED_RESCHED→schedule、SIGPENDING→arch_do_signal_or_restart、关中断重读 |
| signal 延迟投递、handler 不插在两条指令间、抢占靠闹钟 | 金句卡 | 20 | 保留 |
| 第六刀：pid 32768 / 4194304、无 GC、fork 炸弹、栈与账本自己拆不了、退出码 | 文字 + 例子 | 21 | 保留 |
| exit 两段式、僵尸、wait、init 收养；C6 | 状态图 | 22 | 保留 |
| 「必须有僵尸」是解法（SIGCHLD 设 SIG_IGN 不留僵尸） | Linux 6.12 kernel/exit.c L737–777 exit_notify 真源码；kernel/signal.c L2049 do_notify_parent、L2120–2136 SIG_IGN / SA_NOCLDWAIT 置 autoreap | 23 | 新增源码证据，把原文「这些不算约束」中的一行做成可验证场景 |
| 第七刀：共享排班表锁、cache 亲和、IPI；同插槽约 60 ns / 跨插槽约 150 ns；C7 | ASCII 双栏 | 24 | 按 Why #3 核实值 |
| 七条 ↔ 四幕；旁观是派生 | 分层图 | 25 | 保留 |
| 压缩记录 16→11→7（放弃 4 条根） | 旁白 | 25 | 压缩为一句；三张合并表文档保留 |
| 这些不算约束（历史选择 / 目标 / 策略 / 约定 / 解法 / 派生） | 文字 + 例子 | 26 | 保留 fork+execve、100 ms、公平、ELF、僵尸、抢占；4 KiB 页 / pid 数字、单内核两行文档保留 |
| 三个 insight + 互相依赖 | 文字 + 例子 | 27 | 保留；KVM / 容器两条推论文档保留 |
| insight 解决约束 + 代价表 | 侧栏 + 总结卡 | 27–28 | 代价进侧栏，完整表文档保留 |
| 呼应六问 | 预告旁白 | 29 | 只保留「约束只说必须解决什么」的过渡，逐问对照表文档保留 |

源码：Linux v6.12，经 jsDelivr `gh/torvalds/linux@v6.12` 获取，副本在 `video-notes/src/`：
- `arch__x86__include__asm__switch_to.h` L23–47（inactive_task_frame、fork_frame）
- `include__uapi__linux__sched.h` L11–19（CLONE_VM ~ CLONE_THREAD）
- `kernel__entry__common.c` L90–134（exit_to_user_mode_loop）
- `kernel__exit.c` L737–777（exit_notify 主体）
- `kernel__signal.c` L2049、L2120–2136（do_notify_parent 的 autoreap 分支，只在高亮与旁白中引用）
四段 code_explain 均为逐字摘录（tab 保留），脚本子串比对全部 MATCH。

事实修正与收紧：
1. IBM 7090 售价与读卡机速度按收尾核实：290 万美元，IBM 711 每分钟 250 张（原「300」）。
2. Redis fork 20 GB 耗时按核实结论写成 100~260 ms（按机器 5~13 ms/GB），不用原文单一区间。
3. 原文「2.4 内核的全局 runqueue」保留为事实陈述；O(1) 调度器每核队列的年份留给 Origin / Deep 集。
4. 「切换存几十个寄存器」收紧为源码事实：被换下时内核栈上只压 r12~r15、bx、bp 与返回地址七个 8 字节；用户态寄存器在进内核时已存进 pt_regs（浮点/向量寄存器另存，未上屏）。
5. pthread_create 只带共享类标志（VM、FS、FILES、SIGHAND、THREAD 等），不说成「全部位都带」。

人物：本集不放人物场景。类比：本集未用 analogy 场景，只保留原文的数据库事务隔离对照（经典软件模型一档）。

验收：29 场景，9 种视觉类型（text 9、ascii 6、spotlight 4、code_explain 4、layers 2、title 1、timeline 1、statemap 1、html_slide 1）。口播含 example 共 3832 字，按 5.4 字/秒加每场 1.5 秒缓冲加 3 秒估约 756 秒，即 12.6 分钟（实际以 TTS 为准）。`vmd_lint --theme anthropic` 0 错误、4 条 CODE-MULTI-HL 告警（四段源码各分 2~3 段高亮）。旁白与例子无 atlas、无场景类型名、无免责与制作用语、无 markdown 符号；画面无箭头与带圈数字等豆腐字（≠ 已改写为「不等于」）。总结卡 pics/ep2-summary-card.png 1920×1080 已目检无溢出。未渲染、未提交、未上传，未创建 ready 标记。

分P标题建议：P2 Why：从一台裸机砍七刀，进程为什么非得长成这样
