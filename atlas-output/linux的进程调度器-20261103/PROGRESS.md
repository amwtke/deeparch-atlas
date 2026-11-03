# linux的进程调度器 Atlas Progress

## 元数据
- **主题**: linux的进程调度器
- **短名**: linux的进程调度器
- **工作目录**: atlas-output/linux的进程调度器-20261103/
- **创建时间**: 2026-11-03T02:40:00+08:00
- **上次更新**: 2026-11-03T13:20:00+08:00
- **当前阶段**: 完成(七份草稿 + 导出 + 8 集大电影 + B 站 + 推送 main)

## 运行模式(本轮特殊)
用户 2026-11-03 授权:**全程自动跑完七份草稿 + 导出 + 大电影 + B 站上传 + 推送 main**,唯一约束是「根据前两轮(Linux文件IO全链路 2026-10、Linux进程全链路 2026-10)的对话总结出用户品味,由助手自己决定本轮品味」。因此:
- 灵魂问题由助手代定(下一节),依据是用户在上一轮灵魂问题第 3 问 + 两次卡在 lag 上 + 「后续主题备忘」里的 sched 子系统线
- 各 stage 的开场对齐 / 推进 reconfirm 由助手按「品味画像」自答,记录在各阶段审计小节的「对齐(自答)」条目里
- 每个 stage 末尾仍抛反问,但每个反问都配《从头走一遍》自答(用户前两轮对预测式反问多次「不知道」,所以反问改成选择式 / 确认式,且不留白)
- 「你的视角」小节改为《你上一轮的视角》:把用户在 Linux进程全链路 里跟调度相关的原话继承进来,标明出处
- git:用户授权最终 commit 并推 main;中间阶段不做快照

## 灵魂问题(助手代定,2026-11-03)
> "一个 CPU 面前有 N 个想跑的任务,内核每次到底按什么规则挑下一个?这条规则(权重 → 虚拟时间 → lag + deadline)是被哪些约束逼出来的、为什么 20 年里换了三代(O(1) → CFS → EEVDF)?多核和 cgroup 又把这条「挑人规则」扩展成了什么(谁把任务搬到别的核,容器的 CPU 上限怎么落到每个线程头上)?"

依据:上一轮灵魂问题第 3 问「怎么调度到 CPU 上执行、典型调度算法的原理」只在 Deep §3 用一条主线带过,用户在 lag / eligibility 上连续两次「不知道」后选「调度这块够了」;上一轮「后续主题备忘」第一条就是按 sched 子系统重讲。本轮把它单独挖到底。

## 品味画像(从前两轮 300+ 轮对话提炼,本轮据此自决)

| # | 品味 | 证据(前两轮) | 本轮怎么落 |
|---|---|---|---|
| 1 | 先立一个人类记得住的稳定骨架,所有问题映射上去 | 文件 IO 五层;进程四幕 | 调度器 = **四问**:何时换(触发点)/ 换谁(挑人规则)/ 各多少(份额)/ 在哪换(多核);每份文档都挂在四问上 |
| 2 | Why 痛点驱动、从最裸起点一刀一刀长;一刀一条约束,5 ~ 8 条,不往上压抽象根 | 文件 IO 12 → 5 根被嫌远;进程改七刀七条 | 从「一核一队列先来先跑」起八刀,C1 ~ C8;附「这些不算约束」 |
| 3 | 引用一律 `ID·短名`,短名精确 | 「R5 C5 看着费劲」 | 全文 `C3·份额与延迟两头要` 式 |
| 4 | 先陈述(概念 + 结构图 / 对象表),再逼问「没有它会坏在哪」,节末汇总表 | How §2.1 样板 → 推到全篇 | How 每个组件一段陈述 + 一张图 / 表 + 逼问表 |
| 5 | 每一幕一个点名的落地例子;核心转换给算例逐步出数、对账 | pread 6000@10300 六步;hello 贯穿 | 固定一台机器(8 核 x86-64 3 GHz,HZ = 250)+ 一组点名任务(mysqld 的 16 个工作线程、redis-server 单线程、一个 nice 19 的 `xz` 备份);算例:nice 权重分配、EEVDF 逐 tick 走表、负载均衡 imbalance、cgroup quota throttling |
| 6 | 关键转换画 SVG + 函数链;源码钉 6.12 带行号;demo 伪代码即可(用户 macOS,不跑) | 「从页到 bio 画个图」;6.12 行号 | 每份 ≥ 1 张 overview SVG + 细节图;Deep 贴 fair.c / core.c 关键段带行号;src/ 给伪代码 + 一份只在 Linux 上能跑的 C demo(标明未在本机验证) |
| 7 | 节首先说结论,三四条短句总结进步点 | 「§4.0 先写 epoll 解决了什么 / io_uring 解决了 epoll 的什么」 | 每个专题节开头「X 解决了什么 / Y 又解决了 X 的什么」+ 三四条短句 |
| 8 | 类比到用户熟的域:MySQL / InnoDB、Windows NT、TCP;对照比到底但压在关心的几层 | jbd2 ↔ redo;IOCP;SQLOS;TCP 拥塞控制 | Comparison 选 Windows NT dispatcher(上一轮只带了一条线,本轮比到底:优先级提升 / 理想处理器 / Job 对象 CPU 限额 / SQLOS);Synthesis 泛化演练选 **MySQL 线程池**(Percona / 企业版 thread_pool);同构回扣第一轮的块层 IO 调度器(BFQ / mq-deadline) |
| 9 | 用户的猜想写进文档,认一半纠一半 | 「TLB 才是贵的」「寄存器分两类」「schedule 自己调自己回」 | 本轮无实时猜想 → 《你上一轮的视角》继承三条原话,标出处与本轮的补充 |
| 10 | 反问要有;答不出就不再追问,改写一节从头解析 | 三次「不知道」都在预测式反问上;卡点在 lag | 反问全部改成选择式 / 确认式;每个反问紧跟《从头走一遍》;Deep 主线① 专门把 lag 从零讲起 |
| 11 | 范围宁全勿缺,深度堆在弱项 | 「四条分支都要」「五个都要」;块层按 结构 / 原理 / 机制 / 策略 加厚 | 弱项 = 多核负载均衡、cgroup 带宽、lag / eligibility(三者前两轮零接触或卡过)→ 按 结构 / 原理 / 机制 / 策略 加厚;上一轮讲厚的 context_switch / 三扇门 只引用不重讲 |
| 12 | 事实先标「待核 #n」,导出前统一核实并把核实表写进文档 | 两轮各 19 / 50 条 | 同 |
| 13 | 产物要能逐节切成视频讲稿:每节自带结论 + 例子 + 图;人物有可查照片 | deeparch-video 流水线 | Origin 人物:Ingo Molnar、Con Kolivas、Peter Zijlstra、Paul Turner、Tejun Heo(+ 学术线 Ion Stoica、Carl Waldspurger) |

各 stage 的推荐默认(house-style 第二部分)全部采纳,差异只在主题换算,见下文「总纲」。

## 进度状态机
- [x] 0. Discovery(灵魂问题由助手代定)
- [x] 1. What(2026-11-03,274 行 + 01-overview.svg)
- [x] 2. Why(含约束清单建立;2026-11-03,C1 ~ C8 定稿 + 02-cuts.svg)
- [x] 3. How(2026-11-03,810 行 + 4 图 + 伪代码)
- [x] 4. Origin(2026-11-03,424 行 + 04-overview.svg;一手资料 30 条 + 二手 17 条)
- [x] 5. 分水岭决定(2026-11-03 自答:继续往下挖)
- [x] 6. Deep(2026-11-03,1626 行 + 4 图 + 模拟器 / C demo / bpftrace)
- [x] 7. Comparison(2026-11-03,492 行 + 2 图;Windows NT dispatcher)
- [x] 8. Synthesis(2026-11-03,492 行 + 07-overview.svg;五元组 14 行 / 必保 11 / MySQL 线程池演练 / 十年赌注)
- [x] 9. 导出格式询问(2026-11-03 自答:综合 MD + 暗色科技风 HTML)
- [x] 10. 融合输出(2026-11-03:linux的进程调度器-atlas.md 4474 行 / 14 图 / 收尾核实 78 条 + .html 暗色科技风;随后进入大电影)

## 约束清单(Why 阶段建立,后续阶段引用)
一刀一条,共 8 条(建立于 2026-11-03,编号永久固定;引用一律 `ID·短名`):

| # | 短名 | 约束 | 来源 | 不可再分性 | 逼出的东西 |
|---|------|------|------|-----------|-----|
| C1 | 只在打断点换 | 内核没有自己的 CPU,只能在流进内核的瞬间介入;介入时不一定能立刻换人 | 隔离模型 + 中断 / 锁结构 | 要控制一条流必须先拿到它的核;中断上下文不能换栈 | tick、need_resched 标记 + 出口换人、抢占模型、唤醒抢占只打标记 |
| C2 | 未来不可知 | 内核不知道任务下一步算还是等、要多久;猜的启发式可被构造负载骗 | 意图不在二进制里 | 不可静态判定 | 按过去记账(虚拟时间),规则只看账 |
| C3 | 份额与延迟两头要 | 长期按权重分(份额)与醒来多久上台有界(延迟)是两个独立要求;插队额度须有界 | 用户需求形状(吞吐 vs 尾延迟) | 一个标量不能同时编码比例和上界 | 权重 / 虚拟时间、slice / deadline、lag / eligibility |
| C4 | 挑人须便宜 | 每核每秒万次级决定,每次 < 1 μs 且不随任务数线性增长;记账须增量 | 换人代价 2 ~ 3 μs 给出的预算 | 规则的常数项直接吃掉它要分的资源 | 红黑树 + 增广、avg_vruntime 累加器、TSC 增量记账 |
| C5 | 核各自为政 | 核有独立 cache / TLB / 时钟,跨核同步贵一到两个数量级,核间有远近 | 多核硬件 | 物理 | 每核 rq、调度域层级、唤醒选核、周期均衡、迁移门槛 0.5 ms、亲和 |
| C6 | 份额按组算 | 分配单位是用户 / 容器,线程数可被放大;组要嵌套、要能封顶;内核只看见线程 | 多租户 + 计费 + 桌面会话 | 内核没有"用户"这个调度对象 | task_group 组实体、cpu.weight、cpu.max 带宽与 throttling、autogroup |
| C7 | 有人要硬保证 | 一部分任务要绝对时限 / 优先;相对公平推不出绝对保证;凌驾带来饿死与反转 | 实时负载 | 公平与保证互不蕴含 | 类栈 stop > dl > rt > fair > ext > idle、EDF + 准入、95% 阀、优先级继承 |
| C8 | 核不等速且耗电 | 核的有效算力随 SMT / 频率 / 大小核变,能耗是非线性独立目标 | 硬件物理 + 电源 | 物理 | capacity 归一、PELT、SMT 均衡优先、EAS、schedutil |

引用约定:一律 `ID·短名`(如 `C2·未来不可知`),不写裸编号。

## 用户疑问/追问审计

### What 阶段
- 对齐(自答,2026-11-03):轮廓 + 边界都要;总纲 = 四问(何时换 / 换谁 / 各多少 / 在哪换);硬件入门四样(时钟与 HZ / TSC / cache 与 TLB 引上一轮 / SMT·LLC·NUMA·频率);钩子两个(容器限 2 核 p99 抖;PG 100 后端 + Redis 的 nice 与 taskset);性能专题(rt / dl / 抢占模型 / sched_ext / EAS)留 Deep 附录
- 2026-11-03 初稿写入 stages/01-what/01-what.md + pics/01-overview.svg(xmllint 通过);定义 29 字;《你上一轮的视角》继承三条原话(TLB 才是贵的 / 寄存器分两类 / schedule 自己调自己回)并记上一轮两次 lag「不知道」
- 待核:#1 sysctl_sched_migration_cost 默认 500000 ns(6.12 fair.c:79 已见,待核改为已核);#2 SMT 两线程同忙吞吐 60 ~ 70%;#3 跨 NUMA 访存慢 1.5 ~ 2 倍;#4 L2 miss ~10 ns;#5 一次 tick 处理 ~1 μs
- 反问(选择式,自答在 Deep §4):limits.cpu 2 → 4,p99 减半 / 消失 / 变成另一种抖

### Why 阶段
- 对齐(自答,2026-11-03):痛点驱动;起点「一核一 FIFO 不抢占」;八刀一刀一条;场景 + 数字;附「这些不算约束」;C3 加厚并对照数据库线程池 / Resource Governor
- 2026-11-03 初稿写入 stages/02-why/02-why.md + pics/02-cuts.svg;C1 ~ C8 定稿并写入本文件约束表;四条 insight(记账不猜 / 三个数 / N × H 本账 / 凌驾配阀);呼应:三代换代各改写哪条约束(2002 C4 + C5;2007 C2;2023 C3)
- 待核:#6 2.4 goodness 扫描 3000 线程 ~30 μs;#7 O(1) sleep_avg 奖励上限 +5 级;#8 火星探路者 1997 优先级反转;#9 sched_rt_runtime_us 默认 950000;#10 PELT 半衰期 32 ms;#11 turbo 3.8 vs 全核 3.0 GHz 为示例值
- 本轮不与上一轮约束混用:上一轮 C2·霸台不可预知 → 本轮 C1 + C2 + C3;上一轮 C7·核各自为政 → 本轮 C5 + C8

### How 阶段
- 对齐(自答,2026-11-03):机制级全链路,按四问走;弱项加厚 = §3 fair 账(lag 从零讲)、§5 多核(结构 / 原理 / 机制 / 策略四面)、§6 cgroup 带宽;先陈述(概念 + 对象表 / 图)后逼问,每节末汇总表;算例 §3.6 三任务五拍、§5.5 rq3 newidle、§6.3 钩子一;换人动作只引用上一轮 How §6 / Deep §3.3;源码钉 6.12,只写文件 + 函数名
- 三件事:① 每核一本账 `rq` + 类栈 `stop > dl > rt > fair > ext > idle`(C5 + C7,`cpu_capacity` 挂 C8)② `sched_entity` 四个数 + 按 deadline 排的增广红黑树,线程与组同形(C2 + C3 + C4 + C6)③ `TIF_NEED_RESCHED` 标记 + 两种出口 + 三种搬人(C1 + C5)
- 2026-11-03 初稿写入 stages/03-how/03-how.md(810 行)+ pics/03-overview.svg、03-ledger.svg、03-domains.svg、03-cgroup.svg(xmllint 通过)+ src/03-pick.pseudo.c(伪代码)+ src/README.md
- 6.12 函数名已 grep 核对:`sched_balance_rq` / `sched_balance_find_src_group` / `sched_balance_find_src_rq` / `sched_balance_find_dst_cpu` / `sched_balance_newidle` / `sched_balance_domains` / `sched_balance_trigger` / `select_task_rq_fair` / `wake_affine` / `select_idle_sibling` / `select_idle_cpu` / `place_entity` / `update_entity_lag` / `entity_lag` / `entity_eligible` / `vruntime_eligible` / `pick_eevdf` / `avg_vruntime` / `update_deadline` / `update_curr` / `check_preempt_wakeup_fair` / `wakeup_preempt` / `throttle_cfs_rq` / `distribute_cfs_runtime` / `__assign_cfs_rq_runtime` / `sched_cfs_period_timer` / `calc_group_shares` / `update_cfs_group` / `task_hot` / `default_topology` / `sd_init` / `__pick_next_task` 快路径 / `exit_to_user_mode_loop` / `preempt_schedule_irq` / `resched_curr` / `sched_tick` / `do_preempt_short` / `did_preempt_short` / `dequeue_entity` 的 `DELAY_DEQUEUE` 分支
- 数字出处(6.12 源码已见):`sched_prio_to_weight[]` 表;`sysctl_sched_base_slice` 750000 × (1 + ilog2(min(cpus, 8)));`sysctl_sched_migration_cost` 500000;自定义 slice clamp 0.1 ~ 100 ms;`sysctl_sched_cfs_bandwidth_slice` 5000 μs;`default_cfs_period` 100 ms;period 1 ms ~ 1 s;`min_cfs_rq_runtime` 1 ms;`sysctl_sched_rt_runtime` 950000 / `period` 1000000;`RR_TIMESLICE` 100 ms;`imbalance_pct` 117(LLC)/ 110(SMT);`busy_factor` 16;`max_load_balance_interval` HZ/10;`cache_nice_tries` 1 / 2;`sched_weight_from_cgroup` 100 ↔ 1024;类顺序 `stop > dl > rt > fair > ext > idle`(vmlinux.lds.h);`features.h`:PLACE_LAG / PLACE_DEADLINE_INITIAL / RUN_TO_PARITY / PREEMPT_SHORT / DELAY_DEQUEUE / DELAY_ZERO / SIS_UTIL / WA_IDLE / WA_WEIGHT / WA_BIAS / HRTICK(false)
- 反问(选择式,§14):redis lag +4 虚拟 ms 醒来最多连跑多久 —— A 4 ms / B 3 ms / C lag 归零 ~37 ms / D 前提不成立;自答:D 的前提修正(lag 夹在 ±0.643)+ C 的机制(跑到 lag 归零 ~64 ms,因 V 跟着它走);每 4 ms 经历一次标记 → 重挑 → 还是它
- 待核:#12 ~ #26(见 03-how.md 末尾),其中纯机制级待上机验证的是 #19(唤醒到首指令 7 ~ 10 μs 分项)、#26(§3.6 算例数字)
- 2026-11-03 How 封板(自动运行);Deep handoff 清单见 stages/03-how/NOTES-progress.md

### Origin 阶段
# Origin 阶段 —— 给 PROGRESS.md 的审计条目 + 给后续阶段的交接(由 Origin 分支写,主控合并)

## 审计条目(复制到 PROGRESS.md「### Origin 阶段」)

- 对齐(自答,2026-11-03):技术接力打底 + 转折点讲人物;远古史(V7 / 4.3BSD / 0.01 / 2.4)压成 §2 一节 ≤ 50 行;转折点全要(O(1) / RSDL·SD → CFS / 带宽·PELT / EEVDF / sched_ext);学术线(Waldspurger 1994、Stoica 1995)单独成 §5;每个转折点按 烦躁 → 初试 → 死胡同 → 顿悟 → 成型与遗憾;资料严格一手附链接,二手标注
- 2026-11-03 初稿写入 stages/04-origin/04-origin.md + pics/04-overview.svg(xmllint 通过)+ pics/portrait-candidates.md;§12 引用 47 条:一手 30(V7 slp.c、4.3BSD kern_synch.c、0.01 sched.c、2.4.31 goodness、Ingo 2002 设计文档与 -D0 帖、Ingo 2007-04-13 CFS 公告、CFS 内核文档、Con 2007-03-04 RSDL 公告与两封回复、Linus / Con 2007-07-28、MuQSS 设计文档、Stoica 1995 TR、Waldspurger OSDI'94、Paul Turner 2010 RFC / 2011 v7 / 2012 PELT cover、Linus 2010-11-15、autogroup commit、Peter 2023-03-06 / 05-31 cover、EEVDF commit 147f3efaa241、EEVDF 内核文档、Tejun 2022-11-30 RFC、Peter 与 Tejun 2022-12-12、Linus 2024-06-11、sched-ext / sched-energy 内核文档),二手 17(kernelnewbies 7、LWN 9、OSNews / Phoronix)
- 无一手资料 11 项列在 §13(APC 采访原文、Linus "ignoring reality" 原帖、Peter 2008 EEVDF RFC 正文、Waldspurger stride TR、Thompson 1978 BSTJ 文本层、staircase 2004 原帖、sched_ext 合并提交、2.6.24 组调度作者、burst 5.14、PREEMPT_LAZY 6.13)
- 待核:#40 ~ #49(见文末表)
- 反事实(§9):如果 2008 年 Peter 的 fair-group EEVDF RFC 进了树 → 按八条约束逐条看 2008 年权重 → 结论:会是"更贵、多一个没人用的维度"的 CFS;2023 年落地需要三样同时到位(真实延迟需求 C3 / C4 预算宽裕 / 抽屉里的补丁)
- web 调用约 60 次(超出预算 30 ~ 45;原因:lore.kernel.org / lkml.org / git.kernel.org 对本机 403,逐一换镜像)
- 分水岭:按总纲默认「继续往下挖」

## 交接给 Deep

- Deep 主线① 讲 lag 时可直接引 §5.2 论文原话:"eligible time 是我们算法独有的特征";lag 有界 = "差被一个时间量子 q 限制"(论文 abstract);以及 §7 的"睡眠时 lag 怎么办是整个 EEVDF 最新、最不稳定的一块"(delayed dequeue 6.12)—— 这是用户上一轮卡点的历史定位
- Deep 主线① 的反事实候选 "CFS(2007 ~ 2023)" 可引 §4.3:CFS 与 SD 只差"算不算睡眠时间"一个词;Peter 删掉的东西 = v2 补丁标题(START_DEBIT、睡醒补偿、唤醒粒度)
- Deep 主线③ 带宽控制:v7 补丁标题 "throttle entities exceeding their allowed bandwidth" / "return unused runtime on voluntary sleep" 对应 throttle_cfs_rq / __return_cfs_rq_runtime;Paul Turner 拒绝复用 RT 带宽代码的理由("随核数或小预留扩展性差")可作反事实候选
- Deep 主线② 可引 Ingo 2002 文档里 8 路机器"时间片挤压"的描述作为"为什么每核一本账"的历史证据;NUMA 三条路线(Zijlstra / Arcangeli / Gorman)作反事实候选
- Deep 附录 sched_ext:引 §8 的安全承诺原话与 watchdog;EAS 引 sched-energy.rst

## 交接给 Comparison

- Windows NT 对照时,§2 序章的"衰减优先级 + 睡醒提升"世界观正是 NT 保留至今的(优先级 boost),可写成"Windows 停在了 Linux 2007 年换掉的那个世界观上"—— 但需 Comparison 自行核 NT 资料
- Con 对"公平"的定义(随负载按比例变慢是特性)可对照 NT 的"前台窗口提升"

## 交接给 Synthesis

- 五元组"现实对照"列可用:BFS / MuQSS(单队列 vs 每核队列,Con 自述 16 逻辑核上限)、sched_ext(规则可换)、SD vs CFS(睡眠时间算不算)
- 时代局限一节的骨架 = §10 回扣表(每代为当时的约束欠下一代的债)
- 十年赌注候选:sched_ext 让"内核一个规则"变成"每负载一个规则"(Linus 2024-06-11 的治理理由:参与门槛)
- 引语可复用:Peter "icky heuristics" / "much better defined policy";Ingo "takes no prisoners";Con "absolute fairness ... at all costs";Linus "real improvement" / "killer feature";Linus 2024 "work on those concerns when it's in-tree"
- 2026-11-03 Origin 封板(自动运行);handoff 见 stages/04-origin/NOTES-progress.md

### 分水岭
- 2026-11-03(自答,按品味 #11「继续往下挖:进源码和数字」):路由 Deep;预留专题(rt / dl / 抢占模型 / sched_ext / EAS / core scheduling)在 Deep 附录只给机制 + 数字

### Deep 阶段
- 对齐(自答,2026-11-03):聚焦三条主线 ① EEVDF 挑人全程 ② 多核唤醒选核与周期均衡 ③ cgroup 层级份额与带宽;源码钉 Linux v6.12(scratchpad 副本逐一 `grep -n` 核对行号);demo = 本机可跑的 Python 模拟器 + Linux 专用 C demo(未验证)+ bpftrace;ns 时间线只做主线①;每条主线反事实 4 ~ 6 候选;附录(rt / dl / 抢占模型 / sched_ext / EAS / core scheduling / NUMA / autogroup)只给机制 + 行号;反问改选择式并每个紧跟《从头走一遍》自答
- 三个判据:① eligible ∧ deadline 最早,lag 守恒(`fair.c:907` + `:5266`)② 搬人只在"差距过 117% 迟滞且只搬一半 ∧ 不热(500 μs)"(`:11048` + `:9260`)③ 整组按周期借 5 ms 片、借不到整组下树、定时器补池放回(`:5772` + `:5915` + `:6518`)
- 2026-11-03 初稿写入 stages/05-deep/05-deep.md + pics/05-overview.svg、05-timeline.svg、05-balance.svg、05-bandwidth.svg(xmllint 通过)+ src/05-eevdf-sim.py(本机 `python3 -I` 跑过四个场景)+ src/05-demo.c(`clang -fsyntax-only` 通过;Linux 分支未验证)+ src/05-sched-trace.bt + src/README.md
- 行号核对声明:所有 `file:line` 来自 v6.12 原文 `grep -n`;贴出的源码段为原文节选加中文行内注释;模拟器实现对应 19 个函数(文件头列表)
- **模拟器 vs How 的对账**:How §3.6 五拍表全部复现(V 1203.942 / 1207.885 / 1205.261 / 1209.856,redis 放回 v 1204.761、dl 1205.083,lag 守恒读数 +0.500),差异仅四舍五入;How §14 "redis 连跑约 64 ms" 复现(t = 1 → 65 ms);**How §14 分岔三「mysqld 也有资格」不成立**(两实体 Σ w·lag = 0,mysqld lag −5.995);**How §5.5 两处要改**:MC 层 imbalance = 2 但 `CONFIG_PREEMPTION` 下 newidle 只搬 1(`fair.c:9607`),PKG 层走 `migrate_util` = 1024 而非"~2 个 load 单位";**How §7 `fair_server` "逐步接替 95% 阀"** 无 6.12 依据(两者并存,server 默认 50 ms / 1 s)
- 关掉 How 的待核:#13(PELT 常数 `sched-pelt.h:13 ~ :14`)、#14(NUMA imbalance_pct 117)、#19(7 ~ 10 μs 取下限 6.5 ~ 7.5 μs)、#21(dl 准入与 rt 比值共用)、#26(§3.6 数字)
- 待核:#70 ~ #90(见 05-deep.md 末尾);其中 #72 / #73 / #74 需要回头 patch How §14 / §5.5 / §7;#75 `PREEMPT_LAZY` 版本、#77 `scx_bpf_dsq_insert` 改名版本、#76 k8s weight 公式、#86 sched_ext 用户 需要 web 核
- 反问(选择式)三道各自答:§2.6 两 nice 0 任务 B 睡 20 ms 醒来 lag 记成 +6(夹紧)、立刻抢、连跑 12 ms 后 4 ms 轮换;§3.6 绑核 redis 的 rq7 会被 newidle 拉进 PG(答 B;`avg_idle` 是真实旋钮);§4.6 period 改 10 ms 后 `nr_throttled` 每秒 +100(答 B;看 `throttled_usec / nr_periods`)
- 未做:真机数据(用户 macOS);NUMA / EAS 真实数字;`pick_eevdf` 增广搜索正确性证明
- 2026-11-03 Deep 封板(自动运行);How 三处按模拟器结果回改(§14 分岔三 / §5.5 / §7,见 Deep NOTES);handoff 见 stages/05-deep/NOTES-progress.md

### Comparison 阶段
- 对齐(自答,2026-11-03):对象 = Windows NT dispatcher(血统不同:VMS → NT,Cutler);范围 =「比到底」但压在四问上(何时换 / 换谁 / 各多少 / 在哪换);维度 = 按约束组合差异讲 + 可查数字;不加第二对象,FreeBSD ULE / Go runtime 各一段顺带一笔放 §7.3;上一轮已比过的(CreateProcess vs fork、切换寄存器数、时间片 6 / 36 单位、4 s 反饥饿、SQLOS 4 ms)只引用不重讲
- 2026-11-03 初稿写入 stages/06-comparison/06-comparison.md + pics/06-overview.svg、06-boost-vs-lag.svg(xmllint 通过);三件事:① 何时换同形(C1 硬件给的)② 换谁是血统(C2 的两种信仰:猜事件 vs 记账)③ 各多少 / 在哪结构同、参数异(C5 + C6)
- 资料:一手 / 准一手 19 条(微软 Win32 文档 8 页:Scheduling Priorities / Priority Boosts / Priority Inversion / Multiple Processors / Processor Groups / CPU Sets / Quality of Service / MMCSS;API 页 JOBOBJECT_CPU_RATE_CONTROL_INFORMATION;Server 2008 R2 RDSH 文档的 DFSS;驱动文档 Managing Hardware Priorities;硬件定制页 PPM / SchedulingPolicy;SQL Server Thread and task architecture guide;Probert「Windows Kernel Internals: Thread Scheduling」讲义 PDF;kubelet kuberuntime_container_windows.go;k8s Windows 资源管理文档;Roberson ULE 2003 论文 PDF;Go 1.14 release notes;上一轮 06-comparison 已核条目);二手 2 条(Windows Internals 7th、Wikipedia Random boosting),均在正文标注
- 新钉的数字:NT 只提升 0 ~ 15、每片 −1、永不低于基线;Job CpuRate ‰ 单位、Weight 1 ~ 9 默认 5、MinRate 之和 ≤ 10000、与 DFSS 互斥;kubelet `cpuMaximum = 10 × limit_m / cpuCount`(2 核 / 64 核 → 312 ‰),CpuCount 优先于 CpuMaximum,不设权重;MMCSS `SystemResponsiveness` 20% 留给普通任务、High 23 ~ 26 / Medium 16 ~ 22 / Low 8 ~ 15 / 用完配额 1 ~ 7、Clock Rate 保证 Win7 移除;QoS 七级与版本(1709 / 22H2 / Win11 / 2004);`SchedulingPolicy` 0 ~ 5;Processor Groups 64 一组、Win11 / Server 2022 默认跨组 + primary group;CPU Sets Core Reservation;IRQL < 2 才调度、DPC 做 quantum end;讲义「Idle processor preferences」(a) ~ (f) 六条;`KiDeferredReadyThread` 没空核时排理想核队列;SQLOS 2016 Large Deficit First
- 场景复现:§3.3 redis 醒来(NT +2 → 10 级抢占拿整片,最坏 2 片 ≈ 374 ms 优先 vs Linux ≤ 2 slice = 6 ms);§4.3 k8s 限 2 核(两边都是"周期 + 整组停",NT 额度写成全机 ‰、无权重);§5.3 taskset 两面(NT 等价物:就绪时选核把别人放进空闲的核 7;Core Reservation 是更顺手的隔离工具)
- 反问(选择式,§10):NT 的 +2 和 Linux 的 (W + w) / W 放大哪个是猜意图 → A(NT);Linux 的放大是守恒修正;共享的"有界"是 C3 的约束;附:关掉提升 NT 退化成同级轮转(最坏 15 片 ≈ 2.8 s),关掉 PLACE_LAG Linux 仍按 deadline 排
- 待核:#100 ~ #109(见文末表);其中 #100(NT 无周期均衡)是"未见"不是"已证无";#109 Deep § 编号按主控给定布局引用,写作时 05-deep.md 尚未生成
- 分水岭 / 推进:自动运行,Comparison 封板后进 Synthesis
- 2026-11-03 Comparison 封板(自动运行);Synthesis handoff 见 stages/06-comparison/NOTES-progress.md

### Synthesis 阶段
- 对齐(自答,2026-11-03):硬核模式(Deep + Comparison 都走完);读者 = 教学分享但起点是读过内核书的人(只要方法与结论,前置背景最短);先列全部洞察(24 条,带 § 出处)再由助手代挑必保 11 条并各给一句理由;同构三个 = 块层 IO 调度器(回扣用户第一轮 How §4.4)/ Go runtime GMP / TCP 公平队列 fq_codel·DRR;泛化演练 = MySQL 线程池(Enterprise + Percona,参数默认值查官方文档);详尽版;十年赌注一节;反问选择式 + 从头走一遍
- 三件事:① 五元组(决策 / 约束 / 代价 / 反事实 / 现实对照 + 判定)② 必然 vs 偶然判别法(同约束下另一血统是否同形;取消约束才不同形 = 该约束的证据)③ 五步法(前六份的生成顺序)
- 2026-11-03 初稿写入 stages/07-synthesis/07-synthesis.md(492 行)+ pics/07-overview.svg(xmllint 通过);§2 五元组 14 行(判定:必然 7 / Linux 的选择 5 / 偶然 2)+ §2.2 八次取消约束各一个现实样本;§3 洞察 24 条、必保 11 条各一节(①记账不猜 ②三个数 lag 缝合 ③欠账有界守恒 ④标记与真换分开 ⑤N × H 本账 ⑥配额是时间不是核 ⑦有利可图且不热 ⑧凌驾配阀 ⑨猜意图 vs 记账是血统、有界是约束 ⑩换代 = 权重变化 ⑪规则可替换);§4 三同构各一张对照表 + 保留 / 取消了哪条约束;§5 局部最优(八道筛各砍谁 + 权重移动);§6 七代各欠的债 + 今天权重的三处差 + 四笔未还;§7 五步法每步实例 + 常见错误;§7.6 MySQL 线程池 T1 ~ T6 / K1 ~ K7 / 代价 / 纵横表 / 五次取消,结论「用户态的 fair 类减去账,绕不开内核再调一次」;§8 十年赌注选 A(第 13 行,附证伪条件);§9 回扣 8 行;§10 呼应 100%
- 必保挑法:按「离开调度器还能用」挑,第一轮用户的习惯是按编号挑约 11 条;本轮代挑并把未保的 13 条标明并入哪条
- 十年赌注:A(挑人规则被 sched_ext 按负载替换);B 判为同候选改参数;C 判为 Deep §4.5 已否的候选;D 与硬件趋势相反;证伪条件两条(2035 年 scx 仍是实验;fair 长出 per-cgroup 策略 → 第 14 行换)
- 资料:MySQL 8.4 Reference Manual「Server System Variables」「Thread Pool Operation」「Thread Pool Tuning」(2026-11-03 取,一手);Percona Server 8.0「Thread pool」(一手,stall limit 两处不一致);Go 1.14 发布说明(Comparison 已引);其余同构数字凭记忆标待核
- 待核:#120 ~ #129(见文末表);#120 / #123 已核;#121 部分核(Percona stall limit 500 ms vs 示例 100 vs 另一构建 6);#122 oversubscribe 语义;#124 mq-deadline 默认值(第一轮已用,本轮未重 grep);#125 Go sysmon 10 ms / runq 256 / 偷一半;#126 Go 1.25 cgroup 感知 GOMAXPROCS 版本;#127 fq_codel 默认值;#128 继承 Comparison #100;#129 继承 Deep #86
- 反问(选择式,§8):四选一,自答 A,从头走一遍按「改参数 vs 换候选」「证据在反方」「证据链三条」三个分岔
- 推进:自动运行,Synthesis 封板后进导出格式(按品味默认:综合 MD + 暗色科技风 HTML)
- 2026-11-03 Synthesis 封板(自动运行;中途撞 5 小时额度上限,08:00 恢复后续写完成)

## 选定的对比对象(Comparison Hook 后填入)
- Windows NT dispatcher(助手代选,血统不同;比到底,压在四问;§7 顺带 SQLOS / FreeBSD ULE / Go runtime 各一段)

## 选定的导出格式(导出阶段填入)
- 综合 MD + 暗色科技风 HTML(2026-11-03,按品味默认自答);随后 deeparch-video-gen --atlas 大电影(8 集)+ 时尚风封面与目录集 + B 站上传 + 推送 main(用户 2026-11-03 一次性授权)
- 2026-11-03 收尾核实(01 ~ 06 篇):68 条待核 —— 已核 46(含 1 条并存)/ 改写 1(How §0.3 sched_balance_* 改名版本 6.12 → 6.10)/ 部分核实 14 / 无法核实 2 / 无法上机核实 3 / 示例值与场景假设 2;其余改动为补出处与公式(Origin §12 新增一手 48 ~ 52;Deep §4.1 k8s 换算公式;Deep §2.5 A6 现实用户改 Meta / Steam Deck;PREEMPT_LAZY 6.13;DELAY_DEQUEUE 等五项 6.12 新增;cpu.max.burst 5.14;fair_server 6.12 / dl_server 6.8);结果表 verify-results.md,内部笔记 verify-notes.md;Synthesis #120 ~ #129 另行核实
- 2026-11-03 中途撞 5 小时额度上限(04:30 ~ 08:00),Synthesis 与收尾核实两个分支恢复后续完

## 总纲(助手按品味画像自决,2026-11-03)
- 骨架:调度器 = 四问 —— ① 何时换(触发点:tick / 唤醒 / 阻塞 / 让出 / 出口检查)② 换谁(调度类优先级栈 → 类内挑人规则:权重 → vruntime → lag + deadline)③ 各多少(nice 权重、cgroup 层级份额、带宽上限)④ 在哪换(每核就绪队列、唤醒选核、周期均衡、亲和与 NUMA)
- 灵魂问题映射:「按什么规则挑」→ ②;「被哪些约束逼出来、为何三代」→ Why + Origin;「多核」→ ④;「cgroup」→ ③
- 贯穿机器:8 核 x86-64(2 个 LLC 各 4 核,无 SMT 以简化),3 GHz,`CONFIG_HZ = 250`,Linux 6.12;贯穿任务:`mysqld` 16 个工作线程、`redis-server` 1 个线程、`xz`(nice 19)1 个线程、一个 `k8s` 容器 cgroup 限 2 核
- 开场钩子两个(DB 口味):① 容器限 2 核但机器 64 核,MySQL p99 突然抖 —— cgroup 带宽 throttling;② 同机跑 PostgreSQL 100 个后端进程 + Redis,为什么给 Redis `nice -10` 几乎没用、`taskset` 绑核有时有用有时更糟
- What:轮廓 + 边界;四问总纲;硬件四样(时钟中断与 HZ / TSC 与 hrtimer / cache 与 TLB(引上一轮)/ SMT、NUMA、频率);边界(不是切换本身、不是 cpufreq、不是用户态调度、不是 IO 调度器);《你上一轮的视角》
- Why:从「一核一队列先来先跑」起八刀;场景 + 数字;附「这些不算约束」;C3·份额与延迟 单独加厚并类比数据库(资源组 / 线程池公平)
- How:全链路按四问讲;弱项加厚(多核 / cgroup);先陈述后逼问;算例 + 图;经典算法(EEVDF 挑人、负载均衡 imbalance)讲透配图;上一轮 context_switch 只引用
- Origin:技术接力打底,转折点讲人物:O(1)(Ingo 2002)→ staircase / RSDL / CFS(Con 与 Ingo,2007)→ 带宽与 PELT(Paul Turner,2011 ~ 2012)→ EEVDF(Peter Zijlstra,2023)→ sched_ext(Tejun Heo,2024);学术线 Waldspurger 1994 / Stoica 1995 单独成节;严格一手资料附链接
- 分水岭:继续往下挖
- Deep:三条主线 ① EEVDF 挑人全程(lag 从零讲起,逐 tick 算例,唯一的 ns 时间线)② 多核:唤醒选核 + 周期均衡 + PELT ③ cgroup 层级份额 + 带宽 throttling;每条反事实 4 ~ 6 候选;附录 rt / dl / PI / 抢占模型 / sched_ext / EAS / core scheduling 只给机制 + 数字;源码钉 6.12 带行号;src/ 伪代码 + Linux 专用 C demo
- Comparison:Windows NT dispatcher,比到底,压在四问
- Synthesis:读者 = 教学分享但起点是读过内核书的人;五元组 12 ~ 15 行;同构三个(块层 IO 调度器 / Go runtime GMP / TCP 公平队列);五步法;泛化演练 MySQL 线程池;十年赌注;详尽版
- 导出:综合 MD + 暗色科技风 HTML → deeparch-video-gen --atlas → 时尚风封面与目录集 → B 站 → 推 main

## 大电影(deeparch-video-gen --atlas,2026-11-03)
- 分集脚本:ep0 主控自写(四张时尚风目录卡 pics/ep0-card-*.png);ep1 ~ ep7 七个分支各写一集,门禁 = vmd_lint(generic)0 错误 + review_ep.py ISSUES 0(旁白禁词 / 画面豆腐字 / 源码逐字比对 video-notes/src/linux-6.12)
- 渲染:串行队列 video-notes/render-queue.sh,08:12 ~ 08:44 全部 PASS;ep1 / ep5 / ep2 因图或 ASCII 对齐修正各重渲一次(01-overview.svg 标签重叠、05-timeline.svg 文字溢出框、ep2 三栏表竖线错位)
- 时长:ep0 4:56 / ep1 11:58 / ep2 13:45 / ep3 15:27 / ep4 12:50 / ep5 15:02 / ep6 10:56 / ep7 13:20,合计 98.2 分钟(超 90 分钟目标约 8 分钟,未为时长删内容)
- 封面:video-notes/cover-atlas.html → cover-atlas.png(紫 → 品红 → 琥珀渐变 + 玻璃账本卡 + 七集 chip,"时尚风");目录集同风格四张卡
- 人物照片:Molnár(Wikimedia)/ Stoica(Wikimedia)/ Waldspurger(个人站)/ Heo(GitHub 头像,裁到面部)/ Torvalds、Cutler、Thompson(上一轮复用);Zijlstra / Turner / Kolivas / Galbraith 无可验证照片 → 文字出场;来源 pics/portrait-sources.json
- 第二次撞 5 小时额度上限(约 09:20 ~ 13:00),两个修图 / 修表分支恢复后续完
- B 站:2026-11-03 13:14 上传成功,BV17U4M6dEwn https://www.bilibili.com/video/BV17U4M6dEwn(1 稿件 8 分 P,封面 cover-atlas.png,简介 linux-sched-ep0-toc.desc.txt 开头为 C1 ~ C8 速查);回执 upload-receipt.json
- git:随后 commit 本目录并推送 origin main(用户授权)

## 后续主题备忘
- 按 CPU 视角重讲(上一轮备忘第二条)
- 内存子系统 mm 单独一轮(上一轮备忘第一条的另一半)
