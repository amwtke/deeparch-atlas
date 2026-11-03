# 06-comparison 阶段审计(供合并进 PROGRESS.md「Comparison 阶段」小节)

### Comparison 阶段
- 对齐(自答,2026-11-03):对象 = Windows NT dispatcher(血统不同:VMS → NT,Cutler);范围 =「比到底」但压在四问上(何时换 / 换谁 / 各多少 / 在哪换);维度 = 按约束组合差异讲 + 可查数字;不加第二对象,FreeBSD ULE / Go runtime 各一段顺带一笔放 §7.3;上一轮已比过的(CreateProcess vs fork、切换寄存器数、时间片 6 / 36 单位、4 s 反饥饿、SQLOS 4 ms)只引用不重讲
- 2026-11-03 初稿写入 stages/06-comparison/06-comparison.md + pics/06-overview.svg、06-boost-vs-lag.svg(xmllint 通过);三件事:① 何时换同形(C1 硬件给的)② 换谁是血统(C2 的两种信仰:猜事件 vs 记账)③ 各多少 / 在哪结构同、参数异(C5 + C6)
- 资料:一手 / 准一手 19 条(微软 Win32 文档 8 页:Scheduling Priorities / Priority Boosts / Priority Inversion / Multiple Processors / Processor Groups / CPU Sets / Quality of Service / MMCSS;API 页 JOBOBJECT_CPU_RATE_CONTROL_INFORMATION;Server 2008 R2 RDSH 文档的 DFSS;驱动文档 Managing Hardware Priorities;硬件定制页 PPM / SchedulingPolicy;SQL Server Thread and task architecture guide;Probert「Windows Kernel Internals: Thread Scheduling」讲义 PDF;kubelet kuberuntime_container_windows.go;k8s Windows 资源管理文档;Roberson ULE 2003 论文 PDF;Go 1.14 release notes;上一轮 06-comparison 已核条目);二手 2 条(Windows Internals 7th、Wikipedia Random boosting),均在正文标注
- 新钉的数字:NT 只提升 0 ~ 15、每片 −1、永不低于基线;Job CpuRate ‰ 单位、Weight 1 ~ 9 默认 5、MinRate 之和 ≤ 10000、与 DFSS 互斥;kubelet `cpuMaximum = 10 × limit_m / cpuCount`(2 核 / 64 核 → 312 ‰),CpuCount 优先于 CpuMaximum,不设权重;MMCSS `SystemResponsiveness` 20% 留给普通任务、High 23 ~ 26 / Medium 16 ~ 22 / Low 8 ~ 15 / 用完配额 1 ~ 7、Clock Rate 保证 Win7 移除;QoS 七级与版本(1709 / 22H2 / Win11 / 2004);`SchedulingPolicy` 0 ~ 5;Processor Groups 64 一组、Win11 / Server 2022 默认跨组 + primary group;CPU Sets Core Reservation;IRQL < 2 才调度、DPC 做 quantum end;讲义「Idle processor preferences」(a) ~ (f) 六条;`KiDeferredReadyThread` 没空核时排理想核队列;SQLOS 2016 Large Deficit First
- 场景复现:§3.3 redis 醒来(NT +2 → 10 级抢占拿整片,最坏 2 片 ≈ 374 ms 优先 vs Linux ≤ 2 slice = 6 ms);§4.3 k8s 限 2 核(两边都是"周期 + 整组停",NT 额度写成全机 ‰、无权重);§5.3 taskset 两面(NT 等价物:就绪时选核把别人放进空闲的核 7;Core Reservation 是更顺手的隔离工具)
- 反问(选择式,§10):NT 的 +2 和 Linux 的 (W + w) / W 放大哪个是猜意图 → A(NT);Linux 的放大是守恒修正;共享的"有界"是 C3 的约束;附:关掉提升 NT 退化成同级轮转(最坏 15 片 ≈ 2.8 s),关掉 PLACE_LAG Linux 仍按 deadline 排
- 待核:#100 ~ #109(见文末表);其中 #100(NT 无周期均衡)是"未见"不是"已证无";#109 Deep § 编号按主控给定布局引用,写作时 05-deep.md 尚未生成
- 分水岭 / 推进:自动运行,Comparison 封板后进 Synthesis

## 选定的对比对象(供 PROGRESS.md「选定的对比对象」小节)
- Windows NT dispatcher(比到底,压在四问);顺带一笔 FreeBSD ULE、Go runtime;SQLOS 作为"取消 C2 后的第三种解"单独一节

## 交接给 Synthesis(五元组「现实对照」列 + 必然 / 偶然判定)

| 设计决策(Linux) | NT 的对应 | 判定 | 出处 § |
|---|---|---|---|
| 决定与执行分开:标记 + 出口 | DeferredReady → Standby + dispatch 中断;IRQL ≥ 2 不换 | 必然(C1) | §6.1 |
| 每核一本账 + 醒来回原核 | 每处理器 32 级队列 + 位图;理想 / 上次处理器 | 必然(C5) | §5 |
| 分层周期性拉均衡 | 无;只在就绪 / 空闲时选核(待核 #100) | 偶然(C5 vs C4 折中点) | §5.5 |
| 挑人只看账(不猜意图) | 事件提升 + 每片衰减(猜) | 偶然(血统);NT 自己的 SQLOS 2016 转向 deficit | §3、§7.2 |
| 插队有界(lag ±2 slice) | 提升 ≤ 15 且每片 −1 回基线 | 必然(C3),形状不同 | §3.6 |
| 份额与延迟拆成权重 / slice | 无(只能抬级) | Linux 的选择 | §3.4 |
| 被抢者保留剩余 slice(RUN_TO_PARITY 护有资格的 curr) | 片作废,抢占者拿整片 | 偶然 | §3.1 |
| 组 = 同形一行,嵌套权重 1 ~ 10000 | Job 权重 1 ~ 9 / DFSS 按会话,互斥 | Linux 的选择 | §4 |
| 组按时间周期封顶、整组停 | Job HARD_CAP / MaxRate,整 Job 停到 next interval | 必然(C6) | §4.3 |
| 类栈凌驾 + 95% 阀 + PI | 16 ~ 31 无阀;MMCSS 留 20%;AutoBoost 地板 | 凌驾 + 阀 + 继承 = 必然;阀的位置偶然 | §6.2 |
| dl 类准入(Σ runtime / period ≤ 95%) | 无 | Linux 的选择 | §6.2 |
| 按算力 / util 估计量选核调频 | efficiency class + QoS 标签 + SchedulingPolicy | 按算力比 = 必然;估计量 vs 标签 = 偶然 | §6.3 |
| 内核抢占式 | SQLOS 用户态协作式(取消 C2) | 取消一条约束后的另一个局部最优 | §7 |

可复用引语:微软「assigns a full time slice to the higher-priority thread」;「The system does not boost the priority of threads with a base priority level between 16 and 31」;「no threads associated with the job will run until the next interval」;「Windows … cannot guarantee a minimum amount of CPU time」(k8s);「20% of CPU resources are reserved for low-priority tasks」(MMCSS);「one worker thread doesn't monopolize a scheduler」(SQL 2016 LDF);Probert「Priority inversions can lead to starvation / balance manager periodically boosts non-running runnable threads」;Roberson「a pull method, where an idle CPU steals a thread from a non-idle CPU … a push method where a periodic task evaluates the current load situation」;Go 1.14「Goroutines are now asynchronously preemptible」

十年赌注候选(给 Synthesis):NT 会不会也走到"账"—— 证据链:DFSS(2009)→ Job 权重(2012)→ AutoBoost(2013)→ QoS 标签(2017 ~)→ SQLOS LDF(2016);标签越加越多,但骨架还是级
