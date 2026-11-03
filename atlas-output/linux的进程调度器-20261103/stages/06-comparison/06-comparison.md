# 阶段 6:Linux 的进程调度器与 Windows NT 的对照

> 前五份把 Linux 的挑人规则从「账」讲到 6.12 的行号。这一份把它放到另一套从头设计的内核旁边 —— Windows NT 的 dispatcher —— 看四问里哪些答案两边一样(约束逼出的必然),哪些不一样(血统带来的偶然)。上一轮(Linux进程全链路 §4)已经比过一条线:CreateProcess 对 fork、32 级抢占对 EEVDF 的轮廓、时间片 6 / 36 单位、4 秒反饥饿提升、切换存几个寄存器、SQLOS 为什么自己做调度。那些**只引用不重讲**;这一份往 dispatcher 里面走:提升怎么衰减、理想处理器怎么定、Job 对象怎么封顶、IRQL 怎么挡住调度、MMCSS 留 20% 是不是 Linux 的 95% 阀、SQLOS 2016 起的 LDF 是不是 lag。
>
> **依据**:NT 不开源。NT 侧的说法来自微软文档(learn.microsoft.com 的 Win32 / 驱动 / 硬件定制页、SQL Server 文档、Server 2008 R2 的 RDSH 文档)、微软内核组 David Probert 的「Windows Kernel Internals: Thread Scheduling」讲义(微软版权,2010 年前后)、kubelet 的 Windows 源码;Windows Internals 7th(Yosifovich / Ionescu / Russinovich / Solomon)只作二手佐证并标明。拿不准的标「待核」,不编数字。Linux 侧沿用 How(`03-how.md`)与进源码那一份(`05-deep.md`:§2 主线① EEVDF、§3 主线② 多核、§4 主线③ cgroup、§5 附录)。
>
> 贯穿机器与任务不变:8 核两组 L3、HZ 250、mysqld ×16、redis ×1(nice −10)、xz(nice 19)、PG 后端若干、k8s 容器限 2 核;NT 侧同一台机器装 Windows Server,同一组负载。

---

## 约束清单速查(C1 ~ C8)

> 后文所有 `Cn·短名` 都对应下面 8 条,每条在 Why 里从"一核一队列先来先跑"一刀一刀推出过,这里只放"约束 + 不可再分性 + 口诀"。推导见 `stages/02-why/02-why.md`。对照篇里每条都要多回答一句:**这条约束在 NT 那边一样重吗?一样重的话解法一样吗?**

#### C1 — 只在打断点换

内核没有自己的 CPU,只能在流进内核的瞬间(tick / 系统调用 / 中断 / 阻塞)介入;介入时不一定能立刻换人(持锁、中断上下文)。
**不可再分**:要控制一条流必须先拿到它的核;中断上下文不能换栈。
**口诀**:先打标记 → 出口再换

#### C2 — 未来不可知

内核不知道任务下一步算还是等、要多久;猜的启发式可被构造负载骗。
**不可再分**:意图不在二进制里,不可静态判定。
**口诀**:只看账 → 不看人

#### C3 — 份额与延迟两头要

长期按权重分 CPU(份额)和醒来多久上台有界(延迟)是两个独立要求;插队额度须有界。
**不可再分**:一个标量不能同时编码比例和上界。
**口诀**:权重管份额 → slice 管延迟 → lag 管资格

#### C4 — 挑人须便宜

每核每秒万次级决定,每次 < 1 μs 且不随任务数线性增长;记账必须增量。
**不可再分**:规则的常数项直接吃掉它要分的资源。
**口诀**:O(log n) 挑 → O(1) 记

#### C5 — 核各自为政

核有独立 cache / TLB / 时钟,跨核同步贵一到两个数量级,核间有远近。
**不可再分**:多核硬件结构。
**口诀**:每核一本账 → 搬人要算账

#### C6 — 份额按组算

分配单位是用户 / 容器,线程数可被放大;组要嵌套、要能封顶;内核只看见线程。
**不可再分**:内核没有"用户"这个调度对象。
**口诀**:组是一行账 → 封顶按周期扣

#### C7 — 有人要硬保证

一部分任务要绝对时限 / 优先;相对公平推不出绝对保证;凌驾带来饿死与反转。
**不可再分**:公平与保证互不蕴含。
**口诀**:类栈凌驾 → 每个口子配阀

#### C8 — 核不等速且耗电

核的有效算力随 SMT / 频率 / 大小核变,能耗是非线性的独立目标。
**不可再分**:硬件物理。
**口诀**:按算力比 → 不按核数比

---

## §0 从 Deep 走到 Comparison:三件事记住

承上:进源码那一份把三条主线钉到了三个判据 —— eligible 且 deadline 最早、搬人只在有利可图且不热、整组按周期借还。把 NT 放到旁边,四问各得一个判词,压成三件事。

### §0.1 件①:「何时换」两边一样 —— 从 C1·只在打断点换 推出

因为内核没有自己的 CPU(C1·只在打断点换)→ 要解决"决定换人和真换人分开"→ 两边长出同一个形状:Linux 是 `TIF_NEED_RESCHED` 标记 + 两种出口(How §4);NT 是线程先进 **DeferredReady → Standby**,再由目标处理器的 dispatch 中断(DPC 级)真换,调度本身只在 IRQL < 2 发生(Probert 讲义第 5、15 ~ 18 页)。中断处理里不换人、持自旋锁不换人,两边一字不差 —— NT 用 IRQL 抬到 DISPATCH_LEVEL 表达,Linux 用 `preempt_count` 表达。**硬件给的约束,两边只能这么答。**

### §0.2 件②:「换谁」是血统差异 —— 从 C2·未来不可知 的两种信仰推出

因为未来不可知(C2·未来不可知)→ 要解决"换谁的依据从哪来"→ 两边选了相反的信仰。NT 相信**事件类型能说明意图**:I/O 完成了就给 +1 ~ +8,窗口收到输入就 +2,前台进程类抬到不低于后台,然后每跑完一个时间片减一级回基线(微软「Priority Boosts」页)—— 这正是 Linux 2007 年 CFS 删掉、2023 年 EEVDF 删干净的那套"猜"(Origin §4、§7)。Linux 相信**只有账可信**:lag、deadline、权重,规则不看事件只看数。两边都承认 C2·未来不可知,一个用启发式补,一个用守恒量补。**这是血统(VMS → NT,Cutler 1988)带来的偶然,不是约束逼出的必然** —— 证据是 NT 自己也在往"账"走:SQLOS 2016 起的 Large Deficit First(§7)。

### §0.3 件③:「各多少 / 在哪换」两边被同一组约束逼到相似形状 —— 从 C5·核各自为政 + C6·份额按组算 推出

因为跨核贵、核间有远近(C5·核各自为政)→ 两边都是每核一组就绪队列 + "醒来尽量回原核":Linux 的 `rq` + `wake_affine`,NT 的每处理器 `DispatcherReadyListHead[32]` + 理想处理器 / 上次处理器(Probert 第 15、18 页)。因为组要能封顶(C6·份额按组算)→ 两边都是"按时间周期扣、扣光整组停":Linux `cpu.max`,NT Job 对象的 `JOB_OBJECT_CPU_RATE_CONTROL_HARD_CAP`(微软原话:到了本调度周期的额度,"no threads associated with the job will run until the next interval")。差异在参数和粒度(有没有周期性拉均衡、权重是 1 ~ 10000 还是 1 ~ 9),**结构是必然的**。

### §0 结论:三件事对照

| 件 | Linux 6.12 | Windows NT | 判定 |
|---|---|---|---|
| ① 何时换 | 标记 + 出口;`preempt_count` 非零不换 | DeferredReady → Standby + dispatch 中断;IRQL ≥ 2 不换 | 必然(C1·只在打断点换 硬件给的) |
| ② 换谁 | eligible ∧ deadline 最早;账 | 最高优先级 ∧ 同级轮转;事件提升 + 每片衰减 | 偶然(C2·未来不可知 的两种信仰;血统) |
| ③ 各多少 / 在哪 | `cpu.weight` / `cpu.max`;每核 rq + 调度域均衡 | Job 权重 1 ~ 9 / 硬上限;每处理器队列 + 理想处理器,无周期拉均衡 | 结构必然(C5·核各自为政 + C6·份额按组算)、参数偶然 |

---

## §1 一张极简概览图

![四问并排:Linux 的四个答案 vs NT dispatcher 的四个答案,每行一个判词](pics/06-overview.svg)

从图上能读出五件事:

1. **第一行(何时换)两边几乎对称**:左右各一个"标记 / 预备态"小旗子,各一个"出口 / dispatch 中断"。
2. **第二行(换谁)左边是一条数轴(V、lag、deadline),右边是一列 32 级阶梯 + 向上的箭头(提升)和向下的台阶(衰减)**。数轴上没有"你是谁",阶梯上全是"你是谁"。
3. **第三行(各多少)两边都有一条"周期 → 额度 → 停"的时间线**,只是左边额度写的是 ms,右边写的是 ‰(每 10000 周期里的份)。
4. **第四行(在哪)左边 8 本账之间有周期性的虚线(均衡),右边 8 本账之间只有"就绪时放哪"一条实线**。NT 的核之间平时不互相看。
5. **右下角多出两个 NT 独有的小框:MMCSS(留 20%)和 SQLOS(自己做一层)** —— 一个对应 Linux 的 95% 阀,一个对应"把 C2·未来不可知 收回进程内"。

---

## §2 设计动机简表

### §2.1 Windows NT dispatcher

**初衷**。1988 年 Dave Cutler 从 DEC 带着 VMS 的内核模型到微软做 NT(上一轮 §2.1 已核:1988-10 入职,NT 3.1 1993-07 发布)。VMS 的调度就是 32 级优先级 + 事件提升,NT 原样继承并把它写进 Win32 文档:「The system treats all threads with the same priority as equal … assigns time slices in a round-robin fashion to all threads with the highest priority」(微软「Scheduling Priorities」页)。目标不是公平,是**可预期 + 跟手**:桌面上用户在点谁谁就先跑,开发者给线程标好"输入线程 ABOVE_NORMAL、后台线程 BELOW_NORMAL"(同页原话的策略建议)。

**擅长**:
- 桌面交互:前台提升 + 输入提升 + I/O 完成提升,三条启发式直接对准"用户正在等的那个线程"。
- 固定角色的线程集合(游戏引擎、音频栈、驱动 worker):开发者知道谁急,直接标级,不用等账积累。
- 实时类 16 ~ 31 的硬优先:一旦标了,任何普通线程碰不到它。

**不擅长**:
- 多租户 / 大量同级线程的长期份额:同级轮转按线程数分(2008 R2 的 RDSH 文档承认:之前"evenly across all threads at a given priority level … unable to evenly distribute the processor time in the presence of dynamic loads"),所以才在 Server 2008 R2 加 DFSS、在 Windows 8 加 Job CPU 速率控制。
- "低延迟但不多占"这种要求:只能抬级,抬级同时多拿 CPU(C3·份额与延迟两头要 的两个旋钮在 NT 里是一个)。
- 不信任的负载:启发式可被利用(一个每 1 ms 做一次 I/O 的线程永远带着提升;文档自己说 HIGH_PRIORITY_CLASS 用多了"the threads lose their effectiveness")。

**典型应用场景**:Windows 桌面与 Xbox(前台 / 游戏模式)、Windows Server 上的 IIS / Exchange、Azure 的 Windows 宿主与 Windows 容器节点(kubelet 用 Job 对象封顶)、SQL Server(但它在上面自己做了 SQLOS,§7)。

### §2.2 Linux fair 类(对称一行)

**初衷**:2007 年 CFS 为了删掉 O(1) 的交互性启发式(Origin §4),2023 年 EEVDF 为了把份额和延迟拆开(Origin §7)。**擅长**:服务器多租户、容器、任何"不信任负载"的场景;份额与延迟独立可调。**不擅长**:没有"你是谁"的信息,一个从不睡的交互程序(游戏主循环)在账上和 xz 没区别,只能靠自定义 slice 或 `SCHED_BATCH` / `SCHED_IDLE` 显式声明。**典型应用**:所有 Linux 服务器、Android(fair + EAS)、k8s 节点。

---

## §3 对照一:换谁 —— 32 级优先级 + 提升 vs 账 + lag

**先说结论**:两边对 C2·未来不可知 的回答相反 —— NT 用"事件类型 → 临时抬级 → 每片衰减一级"这套启发式表达"谁急",Linux 用 lag(欠多少)和 deadline(请求多短)两个守恒量表达;但两边都把"睡醒插队"限制在**一个时间片量级**内 —— NT 是提升每过一片减一级、永不低于基线,Linux 是 lag 夹在 ±2 slice。功能(插队有界)是必然,形状(级 vs 账)是偶然。三个进步点,各自的:

- NT:不需要账,一次事件就能表达"急",对桌面零延迟生效;开发者可以直接写意图。
- Linux:份额和延迟是两个旋钮;没有可利用的启发式;挑人规则 6 步里没有一个 if 看任务类型。
- 两边共同的:插队有界,所以都不会被"睡醒刷优先级"的负载彻底击穿。

### §3.1 NT 的核心做法

**静态部分**(微软「Scheduling Priorities」页,上一轮 §4.2 已列全表,这里只放用得着的几行):

| 进程优先级类 | 线程 NORMAL 的基础优先级 | 线程可到的范围 |
|---|---|---|
| IDLE | 4 | 1 ~ 6(TIME_CRITICAL 15) |
| NORMAL(默认) | 8 | 1 ~ 10(TIME_CRITICAL 15) |
| ABOVE_NORMAL | 10 | 1 ~ 12(TIME_CRITICAL 15) |
| HIGH | 13 | 1 ~ 15 |
| REALTIME | 24 | 16 ~ 31 |

选人规则原话:最高优先级的所有线程轮转分时间片;「If a higher-priority thread becomes available to run, the system ceases to execute the lower-priority thread (without allowing it to finish using its time slice) and assigns a full time slice to the higher-priority thread.」—— 抢占后**给一整片**,这一点和 Linux 的"被抢的 curr 保留剩余 slice"(`RUN_TO_PARITY` 只护有资格的 curr,How §3.5)不同。

**动态部分**(微软「Priority Boosts」页):

| 规则 | 原话要点 | 数值 |
|---|---|---|
| 只提升 0 ~ 15 | 「The system does not boost the priority of threads with a base priority level between 16 and 31」 | — |
| 前台进程类 | NORMAL 类进程到前台时,优先级类抬到「greater than or equal to the priority class of any background processes」 | 类级提升 |
| 窗口收到输入 | 定时器 / 鼠标 / 键盘消息 → 拥有窗口的线程提升 | +2(Windows Internals 第 4 版授权课件:「GUI threads that wake up to process windowing input get a boost of 2」,二手;#106) |
| 等待结束 | 「when a wait operation associated with disk or keyboard I/O finishes, the thread receives a priority boost」 | 盘 +1 / 网 +2 / 键鼠 +6 / 声卡 +8(WDK `wdm.h` 的 `IO_*_INCREMENT`,上一轮已核 #4) |
| 衰减 | 「reduces that priority by one level each time the thread completes a time slice, until the thread drops back to its base priority. A thread's dynamic priority is never less than its base priority」 | 每片 −1 |
| 反饥饿 | 「balance manager periodically boosts non-running runnable threads」(Probert 第 9 页) | 就绪等满 ~4 s 抬到 15(上一轮已核 #5) |
| 可以关 | `SetProcessPriorityBoost` / `SetThreadPriorityBoost` | — |

**时间片**:上一轮已核 #6 —— 客户端 2 个时钟中断(6 单位)、服务器 12 个(36 单位),x86 多核时钟间隔 15.625 ms → 约 31 ms / 187 ms;客户端前台 ×3;Vista 起按 CPU 周期计。片用完的处理在讲义第 24 ~ 25 页 `KiQuantumEnd`:`thread->Quantum = Process->ThreadQuantum`,`Priority = KiComputeNewPriority(thread)`(衰减一级),然后 `KiSelectReadyThread` 找同级或更高的下一个。

**选人的数据结构**(讲义第 15 页):每处理器一份 `DispatcherReadyListHead[32]` + 一个 32 位 `ReadySummary` 位图,找最高非空级就是找位图最高位 —— 和 Linux rt 类的 100 级数组 + 位图(How §7)同形,和 fair 类的红黑树不同形。

### §3.2 Linux 的对应物

How §3 + Deep §2:权重(nice 40 级 1.25 倍等比)、vruntime、加权平均 V、lag = V − v、slice → 虚拟 deadline、`pick_eevdf` 六步、睡下去夹 ±max(2 × slice, tick)、醒来按 lag 放回且 V 不动。规则里没有事件类型。

### §3.3 同一个场景:redis 醒来

redis 睡着,16 个 mysqld 线程在算,网卡数据到了。两边各走一遍(数字见 How §3.6 第 10 ms 行;NT 侧按文档规则推):

| | Linux 6.12 | Windows NT(Server,36 单位片 ≈ 187 ms) |
|---|---|---|
| redis 的"身份" | nice −10 → 权重 9548;睡前存了 `vlag` +0.50(虚拟 ms) | NORMAL 类 8 级;或者运维设成 ABOVE_NORMAL 10 级 |
| 醒来那一刻 | `place_entity`:lag 放大后放回,V 下移,当前 mysqld 变没资格;`pick_eevdf` 选 redis → 标记 → 出口换人 | 网络 I/O 完成:动态优先级 8 + 2 = **10**(ABOVE_NORMAL 则 12);高于正在跑的 mysqld(8)→ 立刻抢占,**拿一整片** |
| 多久能上台 | ~7 ~ 10 μs(How §8.2;Deep §2.3 钉到 ns) | 同量级:DeferredReady → 目标处理器 dispatch 中断 → 换人(讲义第 19 ~ 21 页 `KiDeferredReadyThread`:`thread->Priority > victim->Priority` 就把 victim 标 `Preempted`、自己进 Standby) |
| 能连跑多久不被 mysqld 抢 | 直到 lag 归零:≤ 2 slice = 6 ms 真实时间(How §14 从头走一遍) | 一整片 187 ms(mysqld 都在 8 级,10 > 8);片完减到 9,仍高于 8,再一片;再减到 8 才回到同级轮转 → 最坏约 **2 片 ≈ 374 ms** 的优先 |
| 它跑完 50 μs 又睡 | 出队,lag ≈ +0.49 存下 | 动态优先级留在 10,下次醒来再 +2 → 仍是 10(不超过 15) |
| 如果 redis 不睡、一直算 | 账飞走,没资格,下一个 tick 被换 | 每片 −1,两片后回 8,同级轮转 |
| 如果 100 个 redis 轮流睡醒 | 每个最多插 2 slice;mysqld 的份额由权重保住 | 每个醒来都是 10 级;mysqld 在 8 级可能长时间排不到 —— 要靠 4 s 反饥饿抬到 15 兜底 |

读法:两边都给了 redis "立刻上台";差别在**上台之后能占多久**(6 ms vs 两片)和**谁来还债**(Linux 是 redis 自己的 lag 归零,NT 是时间片衰减 + 兜底扫描)。

### §3.4 在五元组上的差异

| | Linux EEVDF | NT dispatcher |
|---|---|---|
| 核心抽象 | 服务欠账 lag + 虚拟截止期 | 动态优先级 = 基线 + 提升 − 衰减 |
| 处理 C2·未来不可知 | 不猜;只记过去 | 猜:事件类型 = 意图的证据 |
| 处理 C3·份额与延迟两头要 | 权重 / slice / lag 三个数 | 一个数(级);延迟靠提升,份额靠同级轮转 |
| 插队上限 | ±2 slice(6 ms) | 提升 ≤ 15 且每片 −1(≈ 提升级数 × 片长) |
| 被抢的人 | 保留剩余 slice(有资格时受 `RUN_TO_PARITY` 保护) | 片作废,抢的人拿一整片 |
| 代价 | 真正的交互程序没有"奖励";`RUN_TO_PARITY` / `PREEMPT_SHORT` 两个补丁在补"急" | 启发式可被利用;优先级反转需要 AutoBoost;同级按线程数分 |
| 现实 | 所有 Linux | 所有 Windows;Linux 2002 ~ 2007 的 O(1) 也是这个形状 |

### §3.5 为什么 NT 这么选

1. **VMS 血统**:Cutler 把 VMS 的 32 级 + 提升原样带来,1993 年没有任何压力去换(Origin §2:Unix V7 / 4.3BSD 也是衰减优先级;整个行业在 2007 年之前都这么做)。
2. **桌面优先**:用户不想要"后台编译和前台编辑器各 50%",他想要前台跟手。事件提升是最便宜的"跟手"实现 —— 不需要账,一次 I/O 完成就够。
3. **开发者在场**:Win32 应用是一个厂商写的一个 exe,它知道哪条线程是 UI 线程。Linux 服务器上的负载是一堆互不认识的容器,没有人替它们标级。
4. **代价后来才付**:同级按线程数分 → Server 2008 R2 加 DFSS;没法封顶 → Windows 8 加 Job 速率控制;反转 → Windows 8.1 加 AutoBoost(版本号来自 Windows Internals,二手;收尾核实未找到一手,#101)。每补一样都是在"级"的世界观上打补丁,而不是换成"账"。

![同一个睡醒的线程,NT 的提升-衰减 vs Linux 的 lag-归零,两条车道一条时间轴](pics/06-boost-vs-lag.svg)

### §3.6 这个对比突出了什么

挑人规则不是约束逼出的唯一解:C2·未来不可知 允许"不猜"(账)也允许"用事件猜"(提升),两边都活了三十年。真正被约束钉死的是**插队必须有界**(C3·份额与延迟两头要 的第三句)—— NT 的"每片 −1、永不低于基线"和 Linux 的"±2 slice"是同一条约束的两种写法。**判定:插队有界 = 必然;级 vs 账 = 偶然。**

---

## §4 对照二:各多少 —— Job 对象 CPU 速率控制 / DFSS vs cgroup `cpu.weight` / `cpu.max`

**先说结论**:封顶这件事两边同形 —— 都是"按时间周期给额度、扣光整组停、下个周期放",差别只是额度写成 ms 还是写成每 10000 周期里的份。按组分份额这件事 NT 做得晚、做得粗(Job 权重 1 ~ 9,DFSS 只按会话),Linux 做得早、做得细(cgroup 嵌套权重 1 ~ 10000)。C6·份额按组算 的"封顶"一半是必然,"嵌套权重"一半 NT 至今没有完整对应。

### §4.1 NT 的核心做法

**Job 对象 CPU 速率控制**(Windows 8 / Server 2012 起,微软 `JOBOBJECT_CPU_RATE_CONTROL_INFORMATION` 页):

| 模式 | 字段 | 原话要点 |
|---|---|---|
| 硬上限 `HARD_CAP` | `CpuRate`:每 10000 周期里的份,"percentage times 100";20% 写 2000 | 「After the job reaches its CPU cycle limit for the current scheduling interval, no threads associated with the job will run until the next interval」 |
| 权重 `WEIGHT_BASED` | `Weight` 1 ~ 9,默认 5 | 「the share of processor time given to the job relative to other workloads on the processor」 |
| 最小 / 最大 `MIN_MAX_RATE` | `MinRate` / `MaxRate`,同样 ‰ 单位;所有 Job 的 `MinRate` 之和 ≤ 10000 | 到了 `MaxRate` 同样"no threads … can run until the next scheduling interval" |
| 嵌套 | 子 Job 的比例相对于直接父 Job | 「the rates set for the job represent its portion of the CPU rate that is allocated to its parent job」 |
| 限制 | 「cannot be used … if Dynamic Fair Share Scheduling (DFSS) is in effect」 | 两套机制互斥 |
| 调度周期长度 | 文档不给数(待核 #102) | — |

**DFSS**(Server 2008 R2 起,RDSH 文档):「dynamically distributes processor time across sessions based on the number of active sessions and load on those sessions by using the kernel-level scheduling mechanism」;默认开,注册表 `…\SessionManager\DFSS\EnableDFSS = 0` 关。它的"组"是**会话**,不是任意层级。文档同页承认之前的问题:「distributing the processor time evenly across all threads at a given priority level … was unable to evenly distribute the processor time in the presence of dynamic loads」—— 这句就是 Why 第六刀的痛点一(线程数放大份额),微软 2009 年才补。

**QoS / EcoQoS**(Windows 10 1709 起分级,Windows 11 加 Eco / Utility;微软「Quality of Service」页):High / Medium / Low / Utility / Eco / Media / Deadline 七级,按窗口可见性、是否出声、API 标记、MMCSS 标记分类;「scheduling priority remains the main metric … QoS can influence core selection and processor power management」。它不是份额,是"组级的能耗 / 选核倾向"—— 放到 §6 的 C8·核不等速且耗电 里再看。

### §4.2 Linux 的对应物

How §3.7 + §6、Deep §4:`task_group` 在每核一行账,`cpu.weight` 1 ~ 10000 嵌套分摊;`cpu.max = quota period`,每核向池借 5 ms,借不到整组下树,`period_timer` 放回;`cpu.max.burst` 攒额度。

### §4.3 同一个场景:k8s 容器限 2 核

k8s 在 Windows 节点上用 Job 对象隔离容器(k8s 文档:「Windows uses a job object per container」),CPU 上限落到 Job 速率控制。kubelet 源码(`kuberuntime_container_windows.go`)的换算和注释:

```
cpuMaximum := 10 * cpuLimit.MilliValue() / cpuCount     // 范围 1 ~ 10000
// "CPU limits are applied to the job object setting JOB_OBJECT_CPU_RATE_CONTROL_ENABLE,
//  … JOB_OBJECT_CPU_RATE_CONTROL_WEIGHT_BASED or JOB_OBJECT_CPU_RATE_CONTROL_HARD_CAP"
// "At one point CpuWeights were set, but this prevented limits from having any effect"
```

| | Linux(`cpu.max = 200000 100000`) | Windows(`limits.cpu = 2`,64 核节点) |
|---|---|---|
| 额度怎么写 | 每 100 ms 周期 200 ms CPU 时间 | `cpuMaximum = 10 × 2000 / 64 = 312` → 每 10000 周期里 312 份 = 3.12% 的全机周期(≈ 2 核) |
| 额度的单位 | 绝对时间(ms) | 全机百分比;换到 32 核节点 kubelet 重算成 625 |
| 扣的单位 | 每核 `cfs_rq` 向池借 5 ms 片 | 「CPU cycle limit」,按周期计(Vista 起片也按周期) |
| 扣光 | 整组所有核的 `cfs_rq` 下树,停到周期末 | 「no threads associated with the job will run until the next interval」—— 整 Job 停到周期末 |
| 请求(requests)怎么落 | `cpu.weight`(按比例) | **没有**:kubelet 只设 `CpuMaximum` / `CpuCount`,不设权重(注释:设权重会让 limit 失效);k8s 文档:「Windows … cannot guarantee a minimum amount of CPU time」 |
| 钩子一的 p99 抖 | 16 线程 12.5 ms 烧光 200 ms,停 87.5 ms(How §6.3) | 同形:16 线程并发烧光本周期的 3.12%,整 Job 停到下个周期;停多久取决于周期长度(待核 #102) |
| 旋钮 | `period` / `burst` / 并发数 | `MaxRate` 换 `Weight`(放弃封顶);或 `CpuCount`(按核数,等价 cpuset) |

读法:**封顶的形状两边一模一样**(周期 + 整组停),这是 C6·份额按组算 的"要能封顶、可计费"逼出来的;**份额那一半 NT 在容器场景里直接没做**(不设权重),所以 Windows 节点上 `requests.cpu` 只用来算 allocatable,不进调度器。

### §4.4 在五元组上的差异

| | Linux cgroup cpu | NT Job / DFSS |
|---|---|---|
| 核心抽象 | 组 = 账本上同形的一行(`sched_entity`) | 组 = Job 对象上的速率策略(调度器外挂) |
| 处理 C6·份额按组算 的"组是一行" | 嵌套权重,任意深 | Job 权重 1 ~ 9,嵌套按父比例;DFSS 只按会话 |
| 处理 C6·份额按组算 的"封顶" | `cpu.max`,周期 1 ms ~ 1 s | `HARD_CAP` / `MaxRate`,周期不公开 |
| 代价 | 周期末停顿;组权重要按每核负载分摊(`calc_group_shares`) | 同样的停顿;权重粒度粗;与 DFSS 互斥 |
| 现实 | k8s / systemd / Android | k8s Windows 节点、RDS 多会话、Windows 容器 |

### §4.5 这个对比突出了什么

**封顶 = 必然**(两边连"整组停到周期末"的坏脾气都一样,因为"配额是组的、停的单位 = 账的单位"是 C6·份额按组算 的逻辑后果,How §6.5 逼问表第三行)。**嵌套权重 = Linux 的选择**:它来自"组是同形一行"这个 Insight 3(Why),NT 没有这个抽象,只能外挂 Job / DFSS 两套互斥的机制。

---

## §5 对照三:在哪换 —— 理想处理器 + 每处理器就绪队列 vs 调度域 + 均衡

**先说结论**:每核一组队列、醒来优先回原核,两边同形(C5·核各自为政 逼的);NT 没有 Linux 那种按调度域分层、周期性"闲的拉忙的"的均衡 —— 它的跨核决策只发生在**线程就绪那一刻**(选空闲核或理想核,否则排到理想核的队列)和核空闲那一刻。Linux 选了"均衡更准但要花钱看邻居",NT 选了"便宜但可能不均"—— 这是 C5·核各自为政 与 C4·挑人须便宜 之间的折中,两边取的点不同。

### §5.1 NT 的核心做法

| 机制 | 来源与原话要点 |
|---|---|
| 每处理器就绪队列 | 讲义第 15 页:`DispatcherReadyListHeads[F/B][MAXIMUM_PRIORITY]` + `ReadySummary` 每处理器一份;就绪分三个真实状态「DeferredReady – queued on any processor / Standby – will imminently start Running / Ready – queue on target processor by priority」,目的是「granular locking of thread priority queues」(第 13 页);全局 dispatcher lock 到 Windows 7 才拆(上一轮已核 #7) |
| 理想处理器 / 上次处理器 | 微软「Multiple Processors」页:「the scheduler runs the thread on the specified processor when possible … a useful hint」;讲义第 9 页:「tries to keep a thread on its ideal processor/node to avoid perf degradation of cache/NUMA-memory」;理想处理器按进程轮转播种(Windows Internals,二手,待核 #103) |
| 就绪时选核(讲义第 18 页「Idle processor preferences」) | (a) 理想处理器空就用它,否则看硬亲和集里的所有处理器;(b) 有首选亲和集且其中有空核则只看它们;(c) 超线程机器上有整个物理核空闲则只看那些;(d) 上次跑过的核在剩余集合里就选它;(e) 剩余里有没睡的核就缩到那些;(f) 选最左边的 |
| 没空核时(讲义第 20 ~ 21 页 `KiDeferredReadyThread`) | 「target is the ideal processor」;比目标核的 `NextThread` / `CurrentThread`:自己优先级更高 → victim 标 `Preempted`、自己进 Standby、给目标发 dispatch 中断;否则「insert thread on Ready list of target processor」—— **排到理想核的队列,不去找最闲的核** |
| 亲和 | 「Setting thread affinity should generally be avoided, because it can interfere with the scheduler's ability to schedule threads effectively across processors」(「Multiple Processors」页);64 核一组(Processor Groups 页);Windows 11 / Server 2022 起进程默认跨所有组,保留"primary group",理想处理器在主组内 |
| CPU Sets(软亲和) | 「declare application affinity in a 'soft' manner that is compatible with OS power management」;「Some versions of Windows support Core Reservation policies, in which a subset of the system's CPU Sets can be devoted to the exclusive use of individual applications」;硬亲和掩码优先于 CPU Set |
| 周期性均衡 | 讲义和 Win32 文档都没有"闲的核定期去忙的核拉线程"这一步;Windows Internals 的说法是 NT 不做 Linux 意义上的负载均衡,只在就绪 / 空闲时选核(二手,待核 #100) |
| NUMA / 异构 | 「the system attempts to schedule threads on processors that are close to the memory being used」;大小核由 QoS + `SchedulingPolicy`(0 全部 / 1 只大核 / 2 偏大核 / 3 只小核 / 4 偏小核 / 5 自动,微软硬件定制页)决定,§6 |

### §5.2 Linux 的对应物

How §5、Deep §3:调度域两层(MC / PKG)、`imbalance_pct` 117%、`balance_interval` 4 ~ 100 ms、PELT 三个量、`select_task_rq_fair` → `wake_affine` → `select_idle_sibling`、`sched_balance_rq` 五步(只拉差距的一半、跳过 0.5 ms 内跑过的)、`newidle` 均衡。

### §5.3 同一个场景:钩子二的 `taskset`

| 做法 | Linux(How §5.6) | NT 等价物与结果 |
|---|---|---|
| 只绑 redis 到核 7 | 均衡照样把 PG 后端拉进 rq7;更糟 | `SetThreadAffinityMask(redis, 1<<7)`:redis 只能在 7;PG 线程就绪时按 (a)~(f) 选核 —— 核 7 空闲时它们**会被放进来**(规则 (a)(e)(f)),而且其中理想处理器恰好是 7 的那几个 PG 线程不空也会排进 7 的队列;**同样更糟**,但原因不是周期均衡,是就绪时选核 |
| 两边都绑 | PG 绑 0 ~ 6,rq7 只有 redis | PG 进程 `SetProcessAffinityMask(0x7F)`;同样 95% 空转 |
| 隔离核 | `isolcpus=7`,核 7 不在任何域 | CPU Sets 的 Core Reservation(「devoted to the exclusive use」),或把系统默认 CPU Set 排除核 7;NT 这边的工具更顺手,因为它本来就是"软亲和 + 保留"模型 |

结论和 How 一样:位置旋钮必须两边都拧。NT 多给了一样东西 —— 保留核(reservation)是一等公民;Linux 要靠启动参数 `isolcpus` 或 `cpuset` 拼。

### §5.4 在五元组上的差异

| | Linux | NT |
|---|---|---|
| 核心抽象 | 调度域(远近分层)+ 每核账上的负载估计 | 理想处理器 / 上次处理器 + 每处理器队列 |
| 处理 C5·核各自为政 的"每核一本账" | `rq`(2002 O(1) 起) | 每处理器就绪队列(Server 2003 起),全局锁 2009 才拆 |
| 处理 C5·核各自为政 的"远近" | SMT / MC / PKG / NUMA 五层,越远越少看 | 超线程整核优先(规则 c)、NUMA 节点亲近;64 核分组 |
| 处理 C5·核各自为政 的"不均衡" | 周期性拉 + newidle 拉;17% 迟滞;只搬一半 | 就绪时选空核;没空核排理想核;无周期性拉(待核 #100) |
| 处理 C4·挑人须便宜 | 均衡有代价模型(`task_hot`、`avg_idle` 判值不值) | 不做均衡就没有这笔代价 |
| 代价 | 均衡本身的开销与抖动风险 | 队列可能长期不均(一个核排 5 个、另一个空着到有人就绪为止) |

### §5.5 这个对比突出了什么

C5·核各自为政 逼出"每核一本账 + 醒来回原核"是必然(两边 2002 / 2003 同年得出);"周期性均衡"不是必然,是 Linux 在 C5·核各自为政 与 C4·挑人须便宜 之间偏向前者的选择 —— NT 偏向后者,代价是不均。**判定:每核队列 + 亲和 = 必然;分层周期均衡 = 偶然(可用"就绪时选核 + 空闲时找"替代)。**

---

## §6 对照四:何时换 + 硬保证 —— IRQL / DPC vs tick / `need_resched` / `preempt_count`;16 ~ 31 vs rt / dl

**先说结论**:何时换两边同形(C1·只在打断点换 是硬件给的);硬保证两边都有凌驾层,但 Linux 给凌驾配了准入(dl)和 95% 阀(rt),NT 的 16 ~ 31 级既无准入也无阀 —— 它把阀放在另一个地方:MMCSS 给普通任务保留 20%。阀是必然的(两边都长出来了),准入是 Linux 的选择。

### §6.1 何时换

| | Linux | NT |
|---|---|---|
| 决定与执行分开 | 标记 `TIF_NEED_RESCHED`;出口 `exit_to_user_mode_loop` / `preempt_schedule_irq` | DeferredReady → Standby;目标处理器的 dispatch 中断(DPC 级)完成换人;「Thread scheduling occurs at PASSIVE or APC level (IRQL < 2)」(讲义第 5 页) |
| 什么时候不能换 | `preempt_count ≠ 0`(自旋锁、中断、软中断) | IRQL ≥ DISPATCH_LEVEL:「DISPATCH_LEVEL and APC_LEVEL interrupts are masked off」,此时「calling KeWaitForSingleObject … causes a fatal error」(微软驱动文档「Managing Hardware Priorities」)—— 调度器自己就是一个 DISPATCH_LEVEL 的软中断 |
| tick 做什么 | `sched_tick`:记账、看 slice、触发均衡 | 时钟中断减 quantum;「DPCs … also used by scheduler & timers (e.g. at quantum end)」(讲义第 5 页);`KiQuantumEnd` 在 DISPATCH_LEVEL 跑 |
| 抢占模型 | `PREEMPT_NONE` / `VOLUNTARY` / `PREEMPT` / `RT` / `DYNAMIC`(How §4.2) | 只有一种:内核态凡 IRQL < 2 皆可抢,相当于 Linux 的 `PREEMPT`;驱动文档要求「Driver code that runs at IRQL > PASSIVE_LEVEL should execute as quickly as possible」—— 和 Linux "持锁区要短"同一句话 |
| 中断下半部 | softirq / threaded irq | DPC(「higher priority than threads … long DPCs harm perf, by blocking threads」,讲义第 5 页) |

同形到连警告语都一样。**判定:必然。**

### §6.2 硬保证

| | Linux | NT |
|---|---|---|
| 凌驾层 | 类栈 `stop > dl > rt > fair > ext > idle` | 16 ~ 31 实时区,「REALTIME_PRIORITY_CLASS … interrupts system threads that manage mouse input, keyboard input, and background disk flushing」(文档劝「almost never use」) |
| 准入 | dl:`__dl_overflow`,Σ runtime / period ≤ 95% 算力 | 无;有权限就能设 24 ~ 31 |
| 阀(防饿死普通任务) | rt:`sched_rt_runtime_us` 950000 / 1000000,每秒留 5%;6.12 `fair_server` | 实时区:**无**;MMCSS 那条路有:`SystemResponsiveness` 默认 20,「20% of CPU resources are reserved for low-priority tasks」;MMCSS 把音频线程放到 23 ~ 26(High)/ 16 ~ 22(Medium),用完配额的线程降到 1 ~ 7(微软 MMCSS 页) |
| 时限语义 | dl 的 (runtime, period) + EDF | 无 EDF;MMCSS 的「Clock Rate」在 Vista 曾是保证的最大时钟粒度,「Starting with Windows 7 … this guarantee was removed to reduce system power consumption」 |
| 反转 | `rt_mutex` 优先级继承 | AutoBoost:「tracks resource reservations and adjusts thread priorities by applying priority floors … the priority of the owner is raised to the maximum priority of the waiter until it releases the resource」(微软「Priority Inversion」页);之前是 4 s 反饥饿兜底 |

读法:C7·有人要硬保证 的"凌驾 + 阀 + 反转处理"三件,两边都有,只是 NT 的阀装在 MMCSS 而不是实时区本身 —— 所以一个自己把自己设成 REALTIME 的程序在 NT 上真能把机器拖死,在 Linux 上最多拿 95%。**判定:凌驾 + 阀 + 继承 = 必然;准入(dl)= Linux 独有的选择;阀装在哪 = 偶然。**

### §6.3 C8·核不等速且耗电:账 vs 标签,再来一次

| | Linux | NT |
|---|---|---|
| 核的算力 | `cpu_capacity` 归一(≤ 1024),SMT / rt 占用打折 | 「efficiency class」0 / 1,大小核各一套 PPM 参数(微软 PPM 页:`CPMinCores1`、`HeteroIncreaseThreshold`…) |
| 任务的重量 | PELT `util_avg`(估计量) | QoS 标签(High / Medium / Low / Utility / Eco / Media / Deadline),按窗口可见性、出声、API、MMCSS 分类;「Heuristic … thread priority」兜底 |
| 选大核还是小核 | EAS `find_energy_efficient_cpu`(x86 服务器无能耗模型则跳过) | `SchedulingPolicy` 0 ~ 5 + `ShortSchedulingPolicy`,按 QoS 与长短线程分别配 |
| 调频 | `schedutil` 读同一个 `util_avg` | 每个 QoS 级一套 `MaxFrequency` / `PerfEnergyPreference`;Eco「Always selects most efficient CPU frequency and schedules to efficient cores」 |

又是 §3 的那条分歧:Linux 用**估计量**(util),NT 用**分类标签**(QoS)。C8·核不等速且耗电 两边都答了,答法延续各自对 C2·未来不可知 的信仰。**判定:按算力比 = 必然;估计量 vs 标签 = 偶然。**

---

## §7 SQLOS:用户态协作式调度为什么能绕开 C1·只在打断点换 和 C2·未来不可知(以及它 2016 年怎么长出了 lag)

**先说结论**:上一轮你的判断「加分是症状,病根是抢占本身」在本轮的约束表里可以说得更准 —— SQLOS 取消的是 C2·未来不可知(进程内信任自己的 worker),于是 C1·只在打断点换 从"内核只在打断点介入"变成"打断点由 SQLOS 自己定、到处都是";而 C3·份额与延迟两头要 和 C6·份额按组算 它一条也没绕开,只是搬到用户态自己解:2016 年的 LDF 就是 lag,Resource Governor 就是 cgroup。

### §7.1 它做了什么(微软「Thread and task architecture guide」原话)

- 每个 CPU 一个 scheduler:「Each scheduler is mapped to an individual processor (CPU)」。
- 协作式:「The time a worker can remain active in a scheduler is called the OS quantum, with a maximum of 4 ms. After its quantum time expires, a worker yields its time to other workers … This cooperation between workers … is called cooperative scheduling, also known as non-preemptive scheduling」。
- 内核看到的是每核一个线程在跑、其余在等事件;NT 的优先级(默认 7,`priority boost` 到 13 已废弃)对它几乎没意义。

### §7.2 对到本轮的约束

| 约束 | 内核调度器 | SQLOS |
|---|---|---|
| C2·未来不可知 | 不能信任任何流会让台 | **取消**:worker 全是自己写的,每个 yield 点已知;不合作的代码(扩展存储过程、CLR)单独切 preemptive 模式(上一轮已核 #10) |
| C1·只在打断点换 | 只能在 tick / 系统调用 / 中断 / 阻塞介入 | 打断点 = 每次等锁、等 I/O、每 4 ms 配额到期 —— 由 SQLOS 自己埋,密度远高于内核的 tick;代价:一个忘了 yield 的 worker 饿死同 scheduler 的所有人 |
| C3·份额与延迟两头要 | lag / deadline / 权重 | **没绕开**:SQL Server 2014 之前「Worker 1 is allowed to basically monopolize the scheduler by having more overall quantum time」;2016 起 **Large Deficit First**:「quantum usage patterns are monitored and one worker thread doesn't monopolize a scheduler … Worker 2 is allowed to consume repeated quantum's before Worker 1 is allowed more quantum」—— "deficit" = 欠账 = lag,只是没有权重和 deadline |
| C5·核各自为政 | 每核 rq + 均衡 | 每核 scheduler;并行任务「always try to assign schedulers from the same NUMA node … in round-robin fashion」;不做均衡(worker 绑死 scheduler),所以文档劝不要同时在 OS 和 SQL 两边设亲和 |
| C6·份额按组算 | cgroup | Resource Governor 的资源池 `MIN_CPU_PERCENT` / `MAX_CPU_PERCENT` / `CAP_CPU_PERCENT`(2012 起硬上限;二手,待核 #104)—— 同一套"权重 + 封顶" |
| C4·挑人须便宜 | O(log n) | FIFO 可运行队列,O(1);代价是没有"按 deadline 排" |
| C7·有人要硬保证 | 类栈 | 无;checkpoint / log writer 这类系统任务也是普通 worker,靠自己频繁 yield |

**认一半、拧紧一半**(接着上一轮的《你的视角》):"病根是抢占"这句在本轮可以精确成 **"病根是 C2·未来不可知 在进程内不成立,所以内核的 C1·只在打断点换 变成了多余的开销"**;但"绕开"只对 C1·只在打断点换 / C2·未来不可知 成立 —— 份额与延迟的矛盾、按组分配的矛盾,SQLOS 一样要解,而且解法长得和内核一模一样(LDF ≈ lag,Resource Governor ≈ cgroup)。这是本轮最有说服力的一条"必然"证据:**换一个血统、换到用户态,C3·份额与延迟两头要 和 C6·份额按组算 的解还是那个形状。**

### §7.3 顺带一笔:FreeBSD ULE 与 Go runtime

**FreeBSD ULE**(Jeff Roberson,BSDCon 2003 论文):每核一个 `kseq`,current / next 两个队列轮换保公平;**交互性评分**用自愿睡眠时间与运行时间之比(睡 > 跑则落在下半区,反之上半区),过阈值就算交互、进 current 队列;slice 10 ~ 140 ms 随 nice 变;均衡是「a pull method, where an idle CPU steals a thread from a non-idle CPU」+「a push method where a periodic task evaluates the current load situation」;SMT 当作一种 NUMA。读法:ULE 在 C5·核各自为政 上和 Linux 同形(每核队列 + 拉 + 推),在 C2·未来不可知 上和 NT 同阵营(用睡眠比猜意图,正是 Linux 2007 年删掉的 `sleep_avg` 世界观)。它绕不开 C3·份额与延迟两头要:current / next 轮换就是它的"插队有界"。

**Go runtime**:M:N 把 goroutine 调到少量内核线程上,工作窃取;1.14 之前只能在函数调用处抢占 —— 「loops without function calls … potentially deadlock the scheduler」,1.14 起「Goroutines are now asynchronously preemptible」(Go 1.14 发布说明),用信号在任意指令处打断。读法:Go 在用户态重新遇到了 C1·只在打断点换 —— 没有 tick 就没法对付不让台的 goroutine,最后只好自己造一个 tick(信号);它绕开的只有内核的 C4·挑人须便宜(换 goroutine 比换线程便宜)和部分 C2·未来不可知(runtime 知道 goroutine 在等 channel 还是在算)。

---

## §8 约束回扣

| 约束 | Linux 的解 | NT 的解 | 同 / 异 | 判定 |
|---|---|---|---|---|
| C1·只在打断点换 | 标记 + 两种出口;`preempt_count` | DeferredReady / Standby + dispatch 中断;IRQL ≥ 2 不换 | 同 | 必然 |
| C2·未来不可知 | 不猜:账 | 猜:事件提升 + 衰减 | 异 | 偶然(血统);NT 自己的 SQLOS 2016 转向账 |
| C3·份额与延迟两头要 | 权重 / slice / lag 三旋钮;插队 ≤ 2 slice | 一个数;提升每片 −1;抢占者拿整片 | 功能同、形状异 | 插队有界 = 必然;拆成三个数 = Linux 的选择 |
| C4·挑人须便宜 | 红黑树 + 累加器;均衡有代价模型 | 32 位位图 O(1);不做周期均衡 | 异(NT 更偏 C4·挑人须便宜) | 折中点偶然 |
| C5·核各自为政 | 每核 rq + 唤醒亲和 + 分层周期均衡 | 每处理器队列 + 理想 / 上次处理器 + 就绪时选核,无周期均衡 | 前半同、后半异 | 每核队列 + 亲和 = 必然;周期均衡 = 偶然 |
| C6·份额按组算 | 嵌套权重 + `cpu.max` 周期封顶 | Job 权重 1 ~ 9 / DFSS 按会话 + Job 硬上限周期封顶 | 封顶同、权重异 | 封顶 = 必然;嵌套权重 = Linux 的选择 |
| C7·有人要硬保证 | 类栈 + dl 准入 + rt 95% 阀 + PI | 16 ~ 31 无准入无阀;MMCSS 留 20%;AutoBoost 优先级地板 | 凌驾 / 阀 / 继承同,准入与阀的位置异 | 凌驾 + 阀 + 继承 = 必然;准入 = 偶然 |
| C8·核不等速且耗电 | capacity + PELT util + EAS / schedutil | efficiency class + QoS 标签 + `SchedulingPolicy` | 功能同、依据异 | 按算力比 = 必然;估计量 vs 标签 = 偶然 |

一句话:**八条约束里,"何时换、每核队列、封顶、凌驾配阀、插队有界"五样两边长得一样,是必然;"账还是级、要不要周期均衡、要不要嵌套权重和准入"是血统和折中点,是偶然。**

---

## §9 呼应你的问题

你问"内核凭什么挑下一个"。对照之后可以把答案拆成两层:

- **必然的一层**(换一套血统也这么做):只在打断点换;每核一本账,醒来回原核;插队必须有界;组的封顶按周期扣、整组停;凌驾要配阀和继承。这些你在 NT 上能一一找到对应物,连坏脾气(周期末停顿、持锁区要短)都一样。
- **Linux 自己选的一层**(NT 没这么做):把"急"从事件类型里拿掉,全部交给账(C2·未来不可知 的"不猜");把份额和延迟拆成权重与 slice 再用 lag 缝回去(C3·份额与延迟两头要 的三个数);按调度域周期性拉均衡(C5·核各自为政 偏向准而不是省);组是同形一行所以能嵌套(C6·份额按组算);dl 类的准入(C7·有人要硬保证)。

"为什么三代"在对照里多了一条证据:NT 停在了 Linux 2007 年离开的那个世界观(衰减优先级 + 事件提升),三十年只打补丁(DFSS、Job、AutoBoost、QoS)不换骨架;而 NT 之上的 SQLOS 在 2016 年自己长出了 deficit —— **同一道题,不同血统,往同一个方向收敛**。到这里灵魂问题的三段(规则、三代、多核与 cgroup)都从"是什么"走到了"哪些是必然、哪些是选择",闭环约 98%;剩下的 2% 是 Synthesis 要做的事:把"必然 / 偶然"的判别法本身沉淀成方法,再拿到数据库线程池上验一次。

---

## §10 反问(选择式)+ 从头走一遍

**反问**:NT 的"网络 I/O 完成 +2、每片 −1"和 Linux 的"睡醒按 lag 放回、放回前按 (W + w) / W 放大",哪个更像在"猜意图"?

A. NT 的 B. Linux 的 C. 都是 D. 都不是

### 从头走一遍

**问题来源**:两边都在"睡醒的线程该不该插队、插多少"这个点上动了手脚,表面上都是"给睡醒的人一点好处"。要分清哪个是猜,得问一句:**这个好处的大小,取决于什么?**

**分岔一:好处取决于"发生了什么事"还是"账上欠多少"**。NT 的 +2 取决于事件类型(网 +2、盘 +1、键鼠 +6、声卡 +8),和这个线程过去跑了多少无关 —— 一个刚刚连跑了三片的线程,只要做一次网络 I/O 回来,照样 +2。这是在用事件推断意图("做网络 I/O 的线程大概在服务用户")。Linux 的放回位置取决于 lag,lag 取决于它过去拿到的服务和平均线的差 —— 和它为什么睡、睡了做什么无关;一个连跑了三片再睡的线程醒来 lag 是负的,排到后面。所以 A 成立的部分:NT 在猜。

**分岔二:那 Linux 的放大系数 (W + w) / W 是不是也在"给好处"**。不是。它是算术修正:把一个 lag 为 +x 的实体加进加权平均,平均线会被它拉低,它的 lag 立刻变成 x − w·x / (W + w);放大后再放回,加入后的 lag 恰好等于 x(How §3.4 的推导)。它不增加任何人的欠账,只是让"加入队列"这个动作本身不改账 —— lag 守恒。这一步没有意图、没有事件、没有参数(没有"补半个 slice"那种常数,那是 CFS 时代的事)。所以 B 不成立。

**分岔三:两边有没有共同点**。有 —— 都把好处限制在一个时间片量级(NT 每片 −1 衰减回基线;Linux ±2 slice 夹紧),这是 C3·份额与延迟两头要 的"插队有界"逼出来的,不是猜。所以 C 也不对:共同的那部分不是猜,是约束。

**结果**:**A**。NT 的提升是猜(事件 → 意图),Linux 的放大是守恒修正;两边共享的"有界"是约束,不是猜。顺手回答一个更细的问题 —— 如果你把 NT 的提升值全改成 0(`SetThreadPriorityBoost` 关掉),它就退化成纯同级轮转,redis 醒来要排到 16 个 mysqld 后面,最坏 15 片 ≈ 2.8 秒;而 Linux 关掉 `PLACE_LAG`(`features.h`)只是让睡醒的任务从 V 处放回,lag 归零,它仍然"有资格",仍然按 deadline 排,redis 的 0.32 ms 虚拟 deadline 还是比 mysqld 的 3 ms 早 —— 它还是先跑。**账的世界里,"急"是 slice 的函数;级的世界里,"急"是提升的函数。关掉提升,级就失去了表达"急"的手段;关掉 lag,账还有 deadline。**

---

## §11 出处

一手 / 准一手(微软自有文档与源码):

1. Scheduling Priorities(learn.microsoft.com/windows/win32/procthread/scheduling-priorities):优先级表、轮转与抢占原话、REALTIME 警告
2. Priority Boosts(…/procthread/priority-boosts):只提升 0 ~ 15、三种提升、每片 −1、永不低于基线
3. Priority Inversion(…/procthread/priority-inversion):AutoBoost 原话
4. Multiple Processors(…/procthread/multiple-processors):理想处理器、亲和"应避免"、NUMA
5. Processor Groups(…/procthread/processor-groups):64 核一组、按物理局部性分组、Windows 11 / Server 2022 的 primary group
6. CPU Sets(…/procthread/cpu-sets):软亲和、Core Reservation、硬掩码优先
7. Quality of Service(…/procthread/quality-of-service):七级 QoS、分类来源、版本
8. Multimedia Class Scheduler Service(…/procthread/multimedia-class-scheduler-service):`SystemResponsiveness` 20%、23 ~ 26 / 16 ~ 22 / 8 ~ 15 / 1 ~ 7、Clock Rate 保证 Win7 移除
9. JOBOBJECT_CPU_RATE_CONTROL_INFORMATION(…/api/winnt/ns-winnt-jobobject_cpu_rate_control_information):硬上限 / 权重 1 ~ 9 / 最小最大 / 嵌套 / 与 DFSS 互斥
10. Remote Desktop Session Host,Windows Server 2008 R2(learn.microsoft.com/previous-versions/…/dd560667(v=ws.10)):Fair Share CPU Scheduling 原话与注册表项
11. Managing Hardware Priorities(learn.microsoft.com/windows-hardware/drivers/kernel/managing-hardware-priorities):IRQL 表、DISPATCH_LEVEL 不能等待
12. Processor power management options + SchedulingPolicy(learn.microsoft.com/windows-hardware/customize/power-settings/…):efficiency class 1 参数、`SchedulingPolicy` 0 ~ 5
13. Thread and task architecture guide,SQL Server(learn.microsoft.com/sql/relational-databases/thread-and-task-architecture-guide):每 CPU 一个 scheduler、4 ms 配额、协作式、LDF、NUMA 轮转、默认优先级 7
14. David B. Probert(Microsoft),Windows Kernel Internals: Thread Scheduling(www.i.u-tokyo.ac.jp/edu/training/ss/lecture/new-documents/Lectures/03-ThreadScheduling/ThreadScheduling.pdf):第 5 / 9 / 13 / 15 / 18 / 19 ~ 21 / 24 ~ 26 页
15. kubernetes/kubernetes `pkg/kubelet/kuberuntime/kuberuntime_container_windows.go`(raw.githubusercontent.com/kubernetes/kubernetes/master/…):`cpuMaximum` 换算与注释
16. Resource Management for Windows nodes(kubernetes.io/docs/concepts/configuration/windows-resource-management/):Job 对象、不能保证最小 CPU
17. Jeff Roberson,"ULE: A Modern Scheduler for FreeBSD",BSDCon 2003(www.cs.ucdavis.edu/~roper/ecs150/ULE.pdf 副本;原文 usenix.org/events/bsdcon03):§3.1 ~ §3.6
18. Go 1.14 Release Notes(go.dev/doc/go1.14):异步抢占原话
19. 上一轮 `atlas-output/Linux进程全链路-20261024/stages/06-comparison/06-comparison.md` §4、§8:已核的 #4(提升值)、#5(反饥饿)、#6(时间片)、#7(每核队列与 Win7 拆锁)、#10(SQLOS 4 ms 与 preemptive)

二手(标注处已说明):Windows Internals 7th Part 1 Ch.4(AutoBoost 版本、理想处理器播种、"无周期均衡"的表述);Wikipedia「Random boosting」(AutoBoost 取代随机提升)。

## 待核

| # | 条目 | 结论(收尾核实 2026-11-03) |
|---|---|---|
| #100 | NT 是否完全没有周期性的跨处理器负载均衡(只在就绪 / 空闲时选核);Windows Internals 7th 的原话与版本 | **部分核实** —— 微软课件(Windows Internals 第 4 版授权)与 Probert 讲义只描述就绪 / 空闲时选核与 Balance Set Manager 每秒扫一次饥饿线程;OSR 论坛(二手)称空闲核在进出空闲时主动拉任务;未见周期均衡,但"未见"仍不等于"已证无"(出处:https://osm.hpi.de/bs/2007/Slides/Unit04/4.5_AdvancedScheduling.pdf ;https://community.osr.com/t/multicore-ht-multi-cpu-scheduling/31516) |
| #101 | AutoBoost 引入版本(Windows 8.1) | **无法核实** —— 微软文档与 Wikipedia 只说 AutoBoost 取代了 random boosting,不给版本;正文保留 "Windows Internals,二手" 标注(出处:https://learn.microsoft.com/en-us/windows/win32/procthread/priority-inversion) |
| #102 | Job 对象 CPU 速率控制的"scheduling interval"长度 | **无法核实** —— 文档只写 "during each scheduling interval" / "until the next scheduling interval",不给毫秒数(出处:https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-jobobject_cpu_rate_control_information) |
| #103 | 理想处理器按进程轮转播种、SMT 兄弟错开 | **部分核实** —— 课件:"System selects ideal processor for first thread in process (round robin across CPUs); Next thread gets next CPU relative to the process seed";SMT 错开未见(仅提 Server 2003 的 `GetLogicalProcessorInformation`)(出处:https://osm.hpi.de/bs/2007/Slides/Unit04/4.5_AdvancedScheduling.pdf(基于 Windows Internals 第 4 版,二手)) |
| #104 | Resource Governor `CAP_CPU_PERCENT` 自 SQL Server 2012 起 | **已核** —— "CAP_CPU_PERCENT … Applies to: SQL Server 2012 (11.x) and later";硬上限,区别于 MAX_CPU_PERCENT 的软上限(出处:https://learn.microsoft.com/en-us/sql/t-sql/statements/create-resource-pool-transact-sql) |
| #105 | CPU Sets 首次版本(Windows 10 1703)与 Core Reservation 适用版本 | **部分核实** —— `SetThreadSelectedCpuSets` 最低 Windows 10 / Windows Server 2016(具体 build 文档不给,"1703" 未证);Core Reservation 文档只说 "Some versions of Windows support"(出处:https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-setthreadselectedcpusets ;…/procthread/cpu-sets) |
| #106 | 窗口输入提升 +2 的具体值 | **部分核实** —— 课件:"GUI threads that wake up to process windowing input get a boost of 2 (added to the current, not base priority)";前台进程的等待结束也 +2;微软 Win32 文档只给规则不给数(出处:https://osm.hpi.de/bs/2007/Slides/Unit04/4.5_AdvancedScheduling.pdf(二手);https://learn.microsoft.com/en-us/windows/win32/procthread/priority-boosts) |
| #107 | Go runtime sysmon 10 ms 抢占阈值 | **已核** —— `const forcePreemptNS = 10 * 1000 * 1000 // 10ms`(正文未用数字)(出处:https://raw.githubusercontent.com/golang/go/master/src/runtime/proc.go(forcePreemptNS)) |
| #108 | §3.3 NT 侧"两片 ≈ 374 ms 优先"按文档规则推算,未上机 | **部分核实** —— 推算与服务器长片 12 tick × 15.625 ms ≈ 187.5 ms 一致(2 片 ≈ 375 ms);未上机(出处:上一轮已核 #6;Microsoft Priority Boosts 页的 "reduces that priority by one level each time the thread completes a time slice") |
| #109 | Deep 的 § 编号(§2 / §3 / §4 / §5)按主控给定布局引用,写作时 `05-deep.md` 尚未生成 | **已核** —— 05-deep.md 实际标题 §2 主线① EEVDF / §3 主线② 多核 / §4 主线③ cgroup / §5 附录,与引用一致(出处:stages/05-deep/05-deep.md) |

## 修订记录

| 时间 | 修订摘要 | 触发原因 |
|---|---|---|
| 2026-11-03 | 初稿:速查 C1 ~ C8 + §0 三件事(何时换同形 / 换谁血统 / 各多少与在哪结构同参数异)+ §1 概览 + §2 动机简表 + §3 换谁(提升表、redis 场景、五元组、为何、判定)+ §4 各多少(Job / DFSS / QoS、k8s 换算、判定)+ §5 在哪(讲义六条选核规则、taskset 等价物、判定)+ §6 何时换与硬保证(IRQL、MMCSS 20%、AutoBoost、C8·核不等速且耗电)+ §7 SQLOS(LDF = lag,Resource Governor = cgroup;ULE / Go 顺带一笔)+ §8 回扣 + §9 呼应 98% + §10 选择式反问与从头走一遍 + §11 出处 19 条 + 待核 #100 ~ #109 | 自动运行(用户授权),对齐按品味画像自答:对象 Windows NT 比到底、压在四问、按约束差异讲 + 可查数字 |
| 2026-11-03 | 收尾核实:#104 / #107 / #109 已核;#100 / #103 / #105 / #106 / #108 部分核实(课件与微软文档只给规则或最低版本,不给周期与具体 build;§3.1 表的 +2 标注出处);#101 / #102 无法核实,正文保留二手标注 | 导出前统一核实(verify-results.md) |
