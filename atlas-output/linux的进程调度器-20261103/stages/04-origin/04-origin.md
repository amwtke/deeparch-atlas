# 阶段 4:Linux 进程调度器 是怎么来的

> 前三节里,「你」是那个要写第一个调度器的人。这一节把「你」换成真名:Linus、Ingo Molnar、Con Kolivas、Peter Zijlstra、Tejun Heo。他们面对的 CPU 和你一样只认下一条指令,但每个人手里的约束组合不一样 —— 这一节讲的就是:同一张约束清单,在 1991、2002、2007、2023、2024 年各长出了什么,以及一个被否决过的问题是怎么在二十年后翻案的。
>
> 资料口径:以 LWN 综述和内核邮件列表存档为主,关键否决 / 决定处引原话并附链接;年份、版本号写作时标「待核 #n」,导出前统一核实。

---

## 约束清单速查(C1 ~ C8)

#### C1 — CPU快IO慢
核比它要等的东西快 10⁴ ~ 10⁷ 倍,等待是常态。
**不可再分**:物理事实。
**口诀**:等的时候换别人上。

#### C2 — 程序不让台
程序不会主动让,内核也猜不到它还要多久。
**不可再分**:程序不可信 + 未来不可知。
**口诀**:时钟来敲门,到点就换人。

#### C3 — 凭账不凭嘴
看不见未来,任务不自报也不可信,只能凭已发生的事。
**不可再分**:信息论事实。
**口诀**:记过去,不猜未来。

#### C4 — 调度不免费
换人直接 1~2 μs + 缓存冷几十 μs;选人代价须与任务数无关。
**不可再分**:CPU 微架构 + 没有专管调度的核。
**口诀**:换得少、选得快。

#### C5 — 核间不通气
核与核无共用桌面:跨核共享一行慢几十倍,打断对方慢上千倍。
**不可再分**:缓存一致性 + IPI 代价。
**口诀**:各管各的队,偶尔对账。

#### C6 — 有人等不起
份额 ≠ 时限:有一类任务要「某时刻前一定拿到」,公平记账只保份额。
**不可再分**:物理世界的期限。
**口诀**:公平之外另开一条道。

#### C7 — 同机多租户
租户在乎的公平单位是「我这一摊」,而租户可随意多开线程。
**不可再分**:应用 / 部署现实。
**口诀**:先分组,组内再分。

#### C8 — 一算法不配万场景
负载对三问的最优答案不同,且变化快于内核发布;策略须可换且错了不伤内核。
**不可再分**:应用多样性 + 社区流程。
**口诀**:策略可换,内核不倒。

---

## §0 从 How 走到 Origin:三件事记住

How 那一节把今天的调度器拆成三件东西:账本与树、三扇门与换人、调度类链。它们看起来像是一次设计出来的,其实不是。每一件都是某一年某个人被某条约束逼到墙角才长出来的,而且长出来之前都走过死胡同。

这一节只要记住三个转折,每个转折对应一条(或一簇)约束第一次「变硬」的时刻:

**第一件:2002 年,数据结构换代 —— 因为 C4·调度不免费 + C5·核间不通气 变硬了**
1991 年的 schedule() 是一个 for 循环扫全部任务,单核几十个进程时谁也不在乎。到 2001 年,Linux 已经跑在几十核的 SMP 机器上、跑着上千线程的 Java 应用,「扫一遍」和「一把大锁」同时成了瓶颈。要解决「选人代价与任务数无关 + 每核各管各的」,所以引入 **O(1) 调度器**:每核一条队列、140 级优先级位图、active / expired 两个数组。这是 How §5「每核一条队列」的出生证明。

**第二件:2007 年,记账哲学换代 —— 因为 C3·凭账不凭嘴 被真正当真了**
O(1) 调度器为了桌面体验堆了一套「交互性启发式」:猜哪个任务是交互式的,猜对了给奖励。猜,就是 C3 的反面。Con Kolivas 用 staircase / RSDL 证明「不猜、只按份额记账」桌面反而更顺;Ingo Molnar 用 62 小时写出 CFS,把记账搬到红黑树上。要解决「不猜未来也能公平」,所以引入 **vruntime 账本 + 时间有序的红黑树** —— 也就是 How §2 的账本与树。同一场争论里,「可插拔调度器」被 Linus 和 Ingo 明确否决。

**第三件:2023 ~ 2024 年,两次翻案 —— 因为 C6·有人等不起 和 C8·一算法不配万场景 各自变硬**
CFS 跑了 16 年,积累的又是一堆启发式(睡眠奖励、唤醒抢占的各种补丁)。Peter Zijlstra 用一篇 1995 年的论文(EEVDF)把「份额」和「时限」统一进一张账本,删掉启发式。一年后,Tejun Heo 的 sched_ext 把 2007 年被否决的「策略可换」重新端上来,这次 Linus 点头了。要解决「份额之外还要时限」和「策略变化快于内核发布」,所以引入 **EEVDF 的 lag / 虚拟期限** 和 **ext 调度类 + eBPF 回调表**。

| 转折 | 是什么 | 为什么存在(哪条约束变硬) |
|---|---|---|
| 2002 O(1) | 每核队列 + 位图,选人 O(1) | C4·调度不免费 + C5·核间不通气:SMP 和千线程让「扫一遍 + 大锁」撑不住 |
| 2007 CFS | vruntime 账本 + 红黑树,不猜交互性 | C3·凭账不凭嘴:启发式猜错的代价已经大过它带来的好处 |
| 2023 EEVDF / 2024 sched_ext | 账本上加期限列;策略交给 eBPF | C6·有人等不起:份额不够用;C8·一算法不配万场景:Meta / Valve 的负载等不起内核发布周期 |

三件事之间的关系:O(1) 留下了「每核队列」这个骨架,CFS 换掉了队列里的排序规则但保留骨架,EEVDF 只改账本的列、不动树,sched_ext 则在调度类链上多挂一节、不动前面任何一件。**每一代都只换约束变硬的那一块**,这是 Linux 调度器 33 年还能认出血缘的原因。

---

## §1 一张极简概览图

![Linux 调度器 33 年:主线两次换算法,可插拔谱系二十年两个答案,三条支线](pics/04-overview.svg)

从图上能读出五件事:

1. 主线(蓝)只有两次真正的算法换代:2007 年换记账哲学,2023 年换账本列。2002 年换的是数据结构,2024 年换的是「谁来写策略」。
2. 可插拔谱系(紫 / 红 / 橙)是同一个问题问了二十年:2004 年提出,2007 年否决,2021 年换成 BPF 钩子再提,2024 年合入。否决和合入的理由都在本节 §5 引原话。
3. 民间线(红)是一个人的故事:Con Kolivas 从 2004 到 2021 维护自己的桌面调度器,从未进主线,但 2007 年主线换代的思想火种是他点的。
4. 实时线(绿)是 C6·有人等不起 的二十年:2004 年 PREEMPT_RT 补丁集诞生,2014 年 SCHED_DEADLINE 进主线,2024 年 PREEMPT_RT 本体才合入,与 sched_ext 同一个版本。
5. 组调度(橙)离 CFS 只差一个版本:CFS 进 2.6.23,组实体进 2.6.24,限额在 3.2。C7·同机多租户 几乎是和公平记账同时变硬的。

---

## §2 序章:1991 ~ 2002,从一个 for 循环到 O(1)

### §2.1 节首结论

- 1991 年的调度器是 30 行 C:扫一遍所有任务,挑 counter 最大的,全为零就重算。它解决了 C1·CPU快IO慢 和 C2·程序不让台,其余约束当时都不存在。
- 2002 年的 O(1) 调度器解决了 C4·调度不免费 和 C5·核间不通气:每核一条队列、位图找最高优先级、两个数组轮换。它留下的「每核队列」骨架活到今天。
- O(1) 为桌面体验加的「交互性启发式」,是下一个转折的病根。

### §2.2 1991:Linus 的 schedule()

Linux 0.01(1991 年 9 月,待核 #1)的 kernel/sched.c 里,调度器长这样(节选自源码镜像,[mariuz/linux-0.01 kernel/sched.c](https://github.com/mariuz/linux-0.01/blob/master/kernel/sched.c)):

```c
/* this is the scheduler proper: */
	while (1) {
		c = -1;
		next = 0;
		i = NR_TASKS;
		p = &task[NR_TASKS];
		while (--i) {
			if (!*--p)
				continue;
			if ((*p)->state == TASK_RUNNING && (*p)->counter > c)
				c = (*p)->counter, next = i;
		}
		if (c) break;
		for(p = &LAST_TASK ; p > &FIRST_TASK ; --p)
			if (*p)
				(*p)->counter = ((*p)->counter >> 1) +
						(*p)->priority;
	}
	switch_to(next);
```

而时钟中断处理函数 do_timer 里只有一行和调度有关:`if ((--current->counter)>0) return;` —— 每个 tick 把当前任务的 counter 减一,减到零就调 schedule()。

把它对回前三节的三问:

| 三问 | 0.01 的答案 | 对应约束 |
|---|---|---|
| 谁先上 | 扫全表,counter 最大的 | C3·凭账不凭嘴 的雏形:counter 就是「还剩多少额度」,不问任务自己 |
| 跑多久 | counter 个 tick;到零换人 | C2·程序不让台:时钟敲门 |
| 放哪个核 | 没有这一问 | 单核,C5·核间不通气 不存在 |

有意思的是那行重算:`counter = counter/2 + priority`。睡着的任务 counter 没被扣,重算时还能继承一半,等于「睡得多的任务醒来优先」—— 这是最早的、无意的「交互性奖励」。它在 0.01 里无害,到 2002 年会被做成一套复杂的启发式,到 2007 年会被整个推翻。

你在 What §0 里替第一个写调度器的人猜的三个问题,Linus 在 1991 年只回答了两个。第三问要等十年,等 C5 变硬。

### §2.3 2002:Ingo 的 O(1),为什么要 O(1)

到 2001 年,Linux 2.4 跑在 8 核、16 核的 SMP 服务器上,跑着成百上千线程的 Java 应用。0.01 那个 for 循环的两个假设同时崩了:

- **扫一遍太贵**(C4·调度不免费 的「选人代价须与任务数无关」):上千个任务,每次换人扫上千次。
- **一把大锁太贵**(C5·核间不通气):2.4 全局一条就绪队列、一把 runqueue_lock,16 个核抢同一把锁。
- **重算一遍更贵**:counter 全为零时要遍历全部任务重算,Ingo 的原话是「你是否受够了重算循环时不时把 L1 缓存吹飞?」

Ingo Molnar 2002 年 1 月 4 日发到 LKML 的 O(1) 调度器设计文档(后来收进内核 Documentation/sched-design.txt,[存档](https://courses.cs.tau.ac.il/os/orish/src/Documentation/sched-design.txt))列的目标是:

> fully O(1) scheduling. Are you tired of the recalculation loop blowing the L1 cache away every now and then?
> 'perfect' SMP scalability. ... no 'big' runqueue_lock anymore - it's all per-CPU runqueues and locks
> there is no recalculation loop. There is no goodness loop either.

要解决上面三个「太贵」,O(1) 引入三样东西:

| 引入 | 解决 | 活到今天了吗 |
|---|---|---|
| 每核一条就绪队列 + 每核一把锁 | C5·核间不通气:核与核不抢锁 | 活着,How §5 的 per-CPU rq 就是它 |
| 140 级优先级数组 + 64 位位图 | C4:找最高优先级 = 找位图最低置位,一条指令 | 死了,2007 年换成红黑树 |
| active / expired 两个数组轮换 | 去掉重算循环:用完时间片的搬去 expired,active 空了两数组交换指针 | 死了,2007 年换成 vruntime 水位 |

O(1) 进了 2.5.2 开发版(2002 年 1 月,待核 #2),随 2.6.0 稳定版(2003 年 12 月)普及。

### §2.4 病根:交互性启发式

O(1) 有一个 Ingo 自己也承认难搞的部分:怎么让桌面顺滑。它的办法是**猜**:记录每个任务的平均睡眠时间,睡得多的判为「交互式」,给它动态优先级加成,时间片用完也不搬去 expired 数组而是重新插回 active。

这是 C3·凭账不凭嘴 的反面:账本里记的不是「用了多少 CPU」,而是「我猜你是不是交互式」。猜错的代价很具体:一个会睡一会儿的 CPU 密集任务(比如编译时等磁盘)会被误判为交互式,反过来抢真正的桌面进程。2002 ~ 2007 年 LKML 上关于「调度器又卡了」的邮件,绝大多数是在修这套猜法的某个角。

**悬念留到下一节**:有没有办法不猜?

---

## §3 2007:公平之争,CFS 怎么赢的

### §3.1 节首结论

- 一个墨尔本的麻醉医生 Con Kolivas 用三年、三个调度器(staircase → RSDL → SD)证明:不猜交互性,纯按份额记账,桌面反而更顺。这是 C3·凭账不凭嘴 第一次被当真。
- Ingo Molnar 看懂了这个结论,用 62 小时写出 CFS:同样不猜,但把记账换到红黑树上,并把调度器核心做成「调度类」可以挂不同策略。CFS 进 2.6.23(2007 年 10 月)。
- Con 退出内核开发。Linus 的解释是:SD 没有一个「愿意处理别人机器上的问题」的维护者。
- 同一场争论里,「可插拔调度器」被 Linus 和 Ingo 明确否决,理由留到 §5。

### §3.2 起:一个麻醉医生的三个调度器

Con Kolivas 白天在墨尔本一家医院做麻醉医生,业余维护一套面向桌面的内核补丁集 -ck([维基百科 Con Kolivas](https://en.wikipedia.org/wiki/Con_Kolivas))。他的烦躁很具体:内核调度器为服务器负载调优,桌面上鼠标会卡、音乐会断。

他的三次尝试:

| 年份 | 调度器 | 思路 | 结局 |
|---|---|---|---|
| 2004 | staircase | 还在启发式框架内,但简化「交互性」判定 | 没进主线 |
| 2007 年 3 月 | RSDL(Rotating Staircase Deadline) | **彻底不猜**:每个优先级一个固定配额,用完往下掉一级,任何人都饿不死 | Ingo 回复「cool!我比两年前的 staircase 更喜欢它,放进 -mm 看看什么会坏」([LKML 2007-03-08](https://lkml.indiana.edu/0703.1/0053.html)),Andrew Morton 收进 -mm |
| 2007 年 4 月 | SD(Staircase Deadline,RSDL 改名) | 同上 | 被 CFS 盖过,Con 撤回 |

RSDL 发布时 LWN 的判断是「大概率会在 2.6.22 进主线」([LWN 2007-03](https://lwn.net/Articles/230247/))。所有人都以为公平之争已经分出胜负。

### §3.3 承:死胡同 —— 两条被放弃的路

**死胡同一:继续修启发式。** 2002 ~ 2007 年主线的做法。每修一个场景,另一个场景出问题。Ingo 后来在解释 CFS 起源时说,CFS 本来是为了清理 Mike Galbraith 寄给他的「又一个桌面调度补丁」的副作用才动手的([Ingo,LKML 2007-07-29](https://lists.openwall.net/linux-kernel/2007/07/29/293))。连作者自己都已经在清理启发式的副作用,这条路走到头了。

**死胡同二:可插拔调度器(plugsched)。** 既然桌面和服务器要的不一样,为什么不让用户选?2004 年前后,Con Kolivas 基于 William Lee Irwin III 的代码做了 plugsched 补丁集,让多个调度器可以编译进内核、启动时选。Ingo 当时就拒绝,2007 年 4 月再次重申理由(Matt Mackall 在反驳邮件里引述 Ingo 的原话,[LKML 2007-04-15](https://lists.openwall.net/linux-kernel/2007/04/15/135)):

> i didnt want to see the Linux scheduler landscape balkanized and i saw no technological reasons for the complication that external modularization brings.

Linus 的态度更直接。2007 年 3 月 RSDL 讨论串里,William Lee Irwin III 转述 Linus 的话([LKML 2007-03-09](https://lkml.iu.edu/hypermail/linux/kernel/0703.1/0982.html)):

> And hey, you can try to prove me wrong. Code talks. So far, nobody has really ever come close. So go and code it up, and show the end result. So far, nobody who actually *does* CPU schedulers have really wanted to do it, because they all want to muck around with their own private versions of the data structures.

这条路的完整来龙去脉在 §5 单独讲。这里只记一点:**2007 年的内核选择了「一个调度器做到最好」,而不是「几个调度器让用户挑」**。

### §3.4 转:62 小时的顿悟

Ingo 的顿悟不是「公平」—— 那是 Con 证明的。他自己说得很清楚,在 CFS 发布邮件里([LKML 2007-04-13](https://lwn.net/Articles/230501/)):

> he has proven via RSDL/SD that 'fair scheduling' is possible and that it results in better desktop scheduling.

Ingo 的顿悟是**数据结构**。他在三个月后的复盘里说([LKML 2007-07-29](https://lists.openwall.net/linux-kernel/2007/07/29/293)):

> During that cleanup work did i realize how a policy-modularized scheduler would allow the bridging of the seemingly unreconcilable friction between the O(1) data structures that things like RT scheduling needs and the binary tree that "fair share scheduling" concepts dictate. (most of the complexity in kernel code like the scheduler derives from complexity in data structures, so you start writing code by thinking about your data structures.)

翻成前三节的话:实时任务(C6·有人等不起)需要 O(1) 的优先级数组,公平任务(C3·凭账不凭嘴)需要按时间排序的二叉树,两者在一个数据结构里打架。解法是**调度类**:核心不假设数据结构,每个类自带自己的队列。这就是 How §4 调度类链的出生证明。

CFS 的三样东西,每一样都对应 How 里的一个机制:

| CFS 引入 | 解决的约束 | How 里的位置 |
|---|---|---|
| 不用优先级数组,用时间有序的红黑树,最左节点最该跑 | C3·凭账不凭嘴 + C4·调度不免费(选人 O(log n),插入 O(log n)) | §2 账本与树 |
| 不猜交互性,只记每个任务「欠多少」 | C3·凭账不凭嘴 | §2.2 vruntime |
| 调度类:extensible hierarchy of scheduler modules,rt 类排在 fair 前 | C6·有人等不起 | §4 调度类链 |

Ingo 的原话里有两句值得记:「CFS does not use runqueues, it uses a time-ordered rbtree to build a 'timeline' of future task execution」,以及只有一个可调参数 sched_granularity_ns,从「桌面(低延迟)」到「服务器(好批处理)」一个旋钮拧到底。

从「这个 fair-share 的东西表现不错」到发到 LKML,Ingo 说「是几小时而不是几天的量级」;整个 CFS 从动手到发布约 62 小时。CFS 进了 2.6.23,2007 年 10 月 9 日发布([kernelnewbies 2.6.23](https://kernelnewbies.org/Linux_2_6_23))。

### §3.5 合:成型与遗憾

**成型**:CFS 的三样东西到今天一样没少。2023 年换 EEVDF 时,红黑树和调度类原封不动,只改了账本的列。

**遗憾一:Con 走了。** 2007 年 7 月,Con 宣布退出内核开发。APC 杂志的访谈标题是「我为什么退出」([APC Magazine 2007-07-24,存档](https://web.archive.org/web/20110707151924/http://apcmag.com/why_i_quit_kernel_developer_con_kolivas.htm)),文章导语是:「Linux 背着一身企业级的包袱,让它在桌面上跑得很差。」Con 自己后来在评论区补了一句:「我从来没说 Linux 在桌面上失败了,我说的是 Linux 内核及其开发过程怎么对待桌面。」维基百科对访谈的概括是:主线开发不够重视桌面交互性,而且这项业余工作已经拖累他的健康、本职工作和家庭。

Linus 对「为什么选 CFS 不选 SD」的解释,是这段历史里最值得读的一封信([LKML 2007-07-27](https://lists.openwall.net/linux-kernel/2007/07/28/29)):

> People who think SD was "perfect" were simply ignoring reality. Sadly, that seemed to include Con too, which was one of the main reasons that I never ended entertaining the notion of merging SD for very long at all: Con ended up arguing against people who reported problems, rather than trying to work with them.
> ...
> That was where the SD patches fell down. They didn't have a maintainer that I could trust to actually care about any other issues than his own.
> ...
> As a long-term maintainer, trust me, I know what matters. And a person who can actually be bothered to follow up on problem reports is a *hell* of a lot more important than one who just argues with reporters.

Linus 还提到有一个大学团队对旧调度器、SD、CFS 做过双盲测试,结论是 SD 和 CFS 都比旧的好,两者之间没有显著差异(待核 #3,Linus 转述)。也就是说,**CFS 赢的不是算法,是维护者**。这是 Origin 这一节最重要的一句话:内核选的不是最好的代码,是「错了之后谁来修」。

**遗憾二:CFS 自己也开始堆启发式。** 没有了交互性猜测,CFS 还是得处理「刚醒来的任务该放在树的哪里」「谁可以抢占谁」。16 年里这些地方长出了一堆特性开关(GENTLE_FAIR_SLEEPERS、WAKEUP_PREEMPTION 之类),Peter Zijlstra 2023 年称之为「icky heuristics」。这是 §4 的起点。

**遗憾三:plugsched 被否的那句话,17 年后被 Linus 自己收回。** 留到 §5。

---

## §4 2023:EEVDF 换掉 CFS,CFS 哪里不够

### §4.1 节首结论

- CFS 只保份额不保时限(C6·有人等不起 的「软」版本:不是实时任务,但希望「快点轮到我」)。nice 值调的是份额,不是延迟;实时类又太特权。
- Peter Zijlstra 用 1995 年 Stoica 与 Abdel-Wahab 的 EEVDF 算法替换 CFS 的排序规则:账本上加「lag」和「虚拟期限」两列,eligible 的任务里期限最早的先跑。短 slice = 早期限 = 更快轮到,不需要启发式。
- 2023 年 3 月发出第一版,8 月底合入 6.6(2023 年 10 月发布),Linus 没有异议。红黑树和调度类不变。

### §4.2 烦躁:latency-nice 的死胡同

2020 年前后,有一批补丁想给 CFS 加一个 latency-nice 参数:让任务声明「我在乎延迟」。LWN 的概括是([LWN 2023-03-09](https://lwn.net/Articles/925371/)):CFS 自 2007 年起把 CPU 分配做得很好,但「它没有办法让进程表达延迟需求。nice 值调整的是一个进程拿多少 CPU 时间,不是它多快拿到」。实时类能服务延迟敏感任务,但它们是特权类,会扰乱系统其余部分。

latency-nice 的问题是:它又是一个启发式旋钮,挂在 CFS 已经很复杂的唤醒抢占逻辑上。Peter Zijlstra 看完这批补丁后的反应([LKML 2023-03-06](https://lkml.indiana.edu/2303.0/05235.html)):

> I've wondered if EEVDF would not make more sense ... if we can pull this off we can delete a whole much of icky heuristics code.

### §4.3 顿悟:一篇 1995 年的论文

EEVDF(Earliest Eligible Virtual Deadline First)来自 Ion Stoica 和 Hussein Abdel-Wahab 1995 年的技术报告(Old Dominion University TR-95-22,待核 #4)。它的三个概念,How §2.4 已经讲过机制,这里只说它们为什么把 C3 和 C6 统一了:

| 概念 | 定义 | 解决什么 |
|---|---|---|
| lag | 应得时间 − 实得时间 | C3·凭账不凭嘴:还是只记过去,lag 就是「欠你多少」 |
| eligible | lag ≥ 0 才有资格被选 | 防止「刚才多吃的人」继续吃 |
| 虚拟期限 | eligible 时刻 + 本任务的 slice | C6·有人等不起 的软版本:slice 短的任务期限早,自然先轮到,不用猜它是不是交互式 |

关键是最后一行:**「想快点轮到」不再是一种需要猜的身份,而是账本上一个可以算出来的期限。** 延迟敏感 = 短 slice = 早期限。CFS 用启发式猜的东西,EEVDF 用一列数字算出来。

Peter 的第一版基准结果是「一堆赢一堆输,但没有任何迹象是彻底失败」;5 月的版本「延迟更好、方差更小」。2023 年 8 月 28 日 Linus 合入 6.6,没有异议(待核 #5,Phoronix 报道)。

### §4.4 遗憾

EEVDF 合入后,唤醒时「把新醒来的任务放在哪」(placement)又成了争论点,Peter 在 2023 年 10 月的邮件里把一个候选方案称为「complete write-off」,另一个 PLACE_SLEEPER 是「目前最理智但也不漂亮的选项」。也就是说:**换算法能删掉大部分启发式,但「睡醒的人该排哪」这个问题本身删不掉**。How §2.4 讲的 lag 置位规则,就是这场争论的现状。

### §4.5 你的视角:BFS 2009 年就用了虚拟期限,主线为什么等了 14 年

> 反问:BFS 2009 年就用了虚拟期限,主线 2023 年才用,这 14 年是没看见,还是看见了但有东西拦着?
> 你的回答:看见了,有东西拦着不让用。

**认大半。** 主线确实看见了:BFS 发布一周后,Ingo 就在自己的 8 核机器上跑了一整套对比基准发到 LKML(2009-09-06,待核 #20),结论是 CFS 在多数负载上更好;Con 的回应是 BFS 本来就只面向 16 核以下的桌面,这台机器测错了对象。但「拦着」的不是一堵墙,是三样东西叠在一起,少一样都可能提前:

| 拦着的东西 | 它怎么拦 | 对应约束 |
|---|---|---|
| **捆绑** | BFS 的虚拟期限和「单条全局队列 + O(n) 扫描」是一个包裹。主线评审的是包裹,包裹在 C5 上不及格,期限这个想法跟着一起被退回。没有人把它拆出来单独评 | C5·核间不通气 |
| **没痛** | CFS 对「跑多久」的回答是 sched_latency / min_granularity + 一套唤醒抢占启发式,在 C6 还软的年代够用。直到 2019 ~ 2022 年 Android / ChromeOS 一批人反复提 latency-nice 还提不进去,才证明旋钮已经打满、启发式补不动了。没有痛,没人肯重写核心账本 | C6·有人等不起 |
| **没人** | Con 从一开始就声明 BFS 不进主线;树内没有人认领「期限」这个想法。2023 年 Peter 动手时引的是 1995 年的论文,不是 BFS —— 想法是同一个,但他走的是自己的路 | (非技术,和 §3.5 同一个病) |

**纠一点。** 「有东西拦着不让用」容易听成「有人反对」。事实上没有人反对过虚拟期限本身,2023 年 EEVDF 合入时没有异议。拦住它的是**缺少理由 + 缺少人**:一个想法进主线需要有人证明它能单独成立(拆开 C5 的捆绑)、有一个 CFS 补不了的痛(C6 变硬)、有一个愿意扛的人。2009 年三样都没有,2023 年三样齐了。这跟 §5.4 可插拔谱系是同一条规律:**主线不是在选最好的算法,是在等约束变硬到旧答案补不动的那一刻。**

顺便回答一个你可能接着问的:实时线早在 2014 年就把真正的期限调度(SCHED_DEADLINE)合进了主线(§6.2)。为什么那边不用等?因为那边 C6 是硬的,从一开始就有痛;而 fair 类的 C6 是软的,痛来得晚,期限也就来得晚。同一个想法,在两条线上按各自约束变硬的时间先后进门。

---

## §5 可插拔谱系:同一个问题,二十年两个答案

这一节单独成节,因为它闭合 What §7 留的悬念 5:一个算法能覆盖所有场景吗?内核为什么肯交权?

### §5.1 节首结论

- 问题从 2004 年问到 2024 年,内核给了两个相反的答案:2007 年「不行,一个好调度器胜过三个平庸的」;2024 年「行,留在树外才是病」。
- 两次答案都不是技术判断,是**社区判断**:2007 年怕分裂、怕用户手动选调度器;2024 年怕人进不来、怕最好的调度器实验都发生在树外。
- 中间变的是三件事:eBPF 让「策略错了不伤内核」成为可能(C8 的后半句);Meta / Valve / Google 的负载差异大到一个默认调度器确实覆盖不了(C8 的前半句);以及,内核内部早已是一张函数指针表(调度类),「可插拔」从「替换整个调度器」变成了「多挂一个类」。

### §5.2 2004 ~ 2007:为什么不行

**2004 年**,Con Kolivas 基于 William Lee Irwin III 的代码整理出 plugsched,目标是替换整个调度器。Ingo 当时就拒绝(他 2007 年说是「2-3 年前」,Con 的说法也是;待核 #6)。

**2007 年 4 月**,CFS 发布,自带一个「模块化调度器核心」。Con 的第一反应是质问:既然你自己做了模块化,为什么 plugsched 不行?([Con,LKML 2007-04-16](https://lists.openwall.net/linux-kernel/2007/04/16/41))Con 说 plugsched 是「被 Linus 和 Ingo 永久否决的」,而且他自己其实从没想要 plugsched,他要的是「一个能处理所有情况的调度策略」。

Ingo 的区分很清楚:CFS 的模块化是**策略分类**(实时一类、公平一类,按优先级串成链),不是让用户在几个完整调度器里挑。他在 7 月那封长信里把理由说到底([Ingo,LKML 2007-07-31](https://lists.openwall.net/linux-kernel/2007/07/31/376)):

> To recap: we dont have a pluggable TCP/IP core either. Nor do we have a pluggable MM. ... _in a kernel, some things should not be pluggable_
>
> Had we not rejected PlugSched 4 years ago CFS could easily never have happened. We'd have 2-3 mediocre schedulers, instead of one good scheduler and _users_ would resist the removal of any of those schedulers, so no clear winner could ever gain enough momentum and Linux would forever be stuck with a stupid and inferior "you have to tweak the scheduler selection manually to your workload to get the max out of the system" handicap.

Matt Mackall 当时的反驳,放到 2024 年看几乎句句应验([LKML 2007-04-15](https://lists.openwall.net/linux-kernel/2007/04/15/135)):

> But "balkanization" is a good thing. "Monoculture" is a bad thing. Look at what happened with I/O scheduling. ... Look at what's happening right now with TCP congestion algorithms. ... If we'd opened up mainline to a variety of schedulers _3 years ago_, we'd probably have gotten to where we are today much sooner.

2007 年的内核站在 Ingo 这边。而且 Ingo 的赌赢了:CFS 确实成了「一个好调度器」,16 年没人能替换它。

### §5.3 2021 ~ 2024:为什么又行了

**2021 年 10 月**,Roman Gushchin(Facebook)发出第一个「用 BPF 钩子影响调度决策」的提案([LWN 2021](https://lwn.net/Articles/873244/)),范围很小:几个钩子让 BPF 程序调整唤醒和抢占决策。当时就有人(Qais Yousef)提出:加载了外部策略的内核,bug 报告还能信吗?

**2022 年 11 月**,Tejun Heo(Meta)和 David Vernet 发出 sched_ext 第一版:不是钩子,是一整个调度类 SCHED_EXT,策略由 BPF 程序通过 select_cpu / enqueue / dispatch 等回调提供。动机原话([LWN 2023-02-10](https://lwn.net/Articles/922405/)引 cover letter):

> The BPF scheduling class allows that experimentation in a safe manner without even needing to reboot the test machine.

调度器维护者 Peter Zijlstra 对第一版的回复是:

> I hate all of this. Linus NAK'ed loadable schedulers a number of times in the past ...

但 LWN 注意到,他接着逐个 review 了补丁。这是 2007 年没有发生过的事。

**2024 年 6 月 11 日**,Linus 拍板([Linus,LKML 2024-06-11](https://lkml.iu.edu/hypermail/linux/kernel/2406.1/03724.html)):

> I honestly see no reason to delay this any more. This whole patchset was the major (private) discussion at last year's kernel maintainer summit, and I don't find any value in having the same discussion ... one year later, so to make any kind of sane progress, my current plan is to merge this for 6.11.
>
> I've never been a huge believer in trying to make everybody happy with code that is out of tree - we're better off working together on it in-tree.
>
> I'm also not a believer in the argument that has been used (multiple times) that the BPF scheduler would keep people from participating in scheduler development. I personally think the main thing that keeps people from participating is too high barriers to participation.

Thomas Gleixner 6 月 19 日请求缓三个月做「干净的集成」([LKML 2024-06-19](https://lkml.iu.edu/hypermail/linux/kernel/2406.2/05614.html))。他顺手引了一句旧话:「I absolutely *detest* pluggable schedulers. —— 猜猜哪位著名程序员说的。」Linus 第二天的回答([LKML 2024-06-20](https://lkml.iu.edu/hypermail/linux/kernel/2406.2/07255.html)):

> And the "I detest pluggable schedulers" has been long superseded by "I detest people who complain about our one scheduler because they have special loads that only they care about"
>
> This whole "keep things out until they are perfect" is a DISEASE.

6.11 窗口没合入 —— Qais Yousef 在 pull request 下提出 review 不足、schedutil 不该被改、以及「加载外部调度器后 bug 报告不可信,应该 taint 内核」([LKML 2024-07-25](https://lists.openwall.net/linux-kernel/2024/07/25/30));Tejun 回应 taint 不适用,因为 SCX 调度器卸载后不留持久影响([LKML 2024-07-30](https://lists.openwall.net/linux-kernel/2024/07/31/36))。9 月 12 日 Tejun 发出 6.12 的 pull request,改动列表第一条是「Improve integration with sched core」,cgroup 支持单独过 review 后合入([Tejun,LKML 2024-09-12](https://lists.openwall.net/linux-kernel/2024/09/13/45));9 月 21 日 Linus 合入(待核 #7)。6.12 于 2024 年 11 月 17 日发布(待核 #8)。

### §5.4 两个答案之间变了什么

| 维度 | 2007 年否决时 | 2024 年合入时 | 对应约束 |
|---|---|---|---|
| 「错了伤不伤内核」 | plugsched 是编译进内核的 C 代码,错了就是内核 bug | eBPF 验证器 + 看门狗 + 自动回退 fair 类(How §7 兜底表) | C8 后半句:错了不伤内核 |
| 「一个算法够不够」 | 桌面 vs 服务器,Ingo 赌一个好调度器能两头兼顾,赌赢了 | Meta 的 scx_layered 部署在超过一百万台机器(LWN LPC 2024);Valve 的 scx_lavd 面向 Steam Deck 游戏;Google 从 2019 年起在内部做可插拔调度 | C8 前半句:负载对三问的最优答案不同 |
| 「变化快不快」 | 内核发布周期 ≈ 负载变化周期 | 游戏、AI 训练、超大规模部署的负载变化以周计,内核以季度计 | C8:变化快于内核发布 |
| 「可插拔」的粒度 | 替换整个调度器 | 调度类链上多挂一节,排在 fair 之后 idle 之前;前面的类一行不改 | How §4 调度类链本身已经是策略模式 |
| 社区的恐惧 | 分裂、用户手动选调度器 | 人进不来、实验都在树外 | 非技术 |

Ingo 2007 年那句「要是 4 年前没拒绝 PlugSched,CFS 就不会诞生」,和 Linus 2024 年那句「把东西留在树外直到完美是一种病」,**两句都对**。区别在于 2007 年内核需要先选出一个好默认值,2024 年它已经有了好默认值(EEVDF),可以开始允许例外。可插拔的前提是有一个值得作默认的「不可插拔」。

### §5.5 案例:两个真的在用的

**Valve / Steam Deck —— scx_lavd**。Igalia 的 Changwoo Min 为 SteamOS 写的 LAVD(Latency-criticality Aware Virtual Deadline),目标是游戏时的交互性和减少卡顿,主要面向单插槽机器;LWN 在 2024 年 9 月 LPC 报道中说它「正走向在 Steam Deck 上出货」([LWN 2024-09-26](https://lwn.net/Articles/991205/),待核 #9 具体 SteamOS 版本)。它的做法是三问里「谁先上」用自己算的延迟敏感度 + 虚拟期限,而不是 EEVDF 的通用期限。

**Meta —— scx_layered**。按服务把任务分层,每层给不同的 CPU 分配策略;LWN 同一篇报道说 scx_layered 已部署在超过一百万台机器上。2025 年 12 月 Meta 的工程师在 LPC 上讲「怎么让 Steam Deck 的调度器在大型服务器上工作」:scx_lavd 已经跑在 Meta 的一部分生产服务器上,并被当作整个机队默认调度器的候选(待核 #10,Phoronix / Tom's Hardware 对 LPC 2025 演讲的报道;「已是默认」还是「候选」各家说法不一)。一个为掌机游戏写的调度器跑进了数据中心 —— 这正是 C8 的「负载对三问的最优答案不同」的反例:有时候不同负载的答案又是一样的,但你要先能换才知道。

---

### §5.6 你的视角:Linus 这次点的是 eBPF 这项技术,不是人

> 反问:2007 年 Linus 选 CFS 不选 SD,给的理由是维护者不是算法。这个理由放到 2024 年 sched_ext 身上还成立吗?
> 你的回答:点的是 eBPF 这项技术。

**认一半。** 2007 年 Linus 的原话是:SD 没有一个「愿意处理别人机器上问题」的维护者。这句话的要害不是「人」,是「别人机器上的问题最后落在谁头上」。plugsched 时代的答案是:落在内核树头上 —— 可插拔调度器是编译进内核的 C 代码,它崩了就是内核 bug,bug 报告寄给 LKML。eBPF 把这个答案改掉了:验证器保证程序不会越界、死循环;看门狗发现调度器超时就把它踢下去,所有任务回退到 fair 类(How §7 兜底表);调度器卸载后内核里不留痕迹(Tejun 回 Qais 时正是用这一点拒绝 taint)。于是「别人机器上的问题」有了新归宿:谁加载谁负责,Meta 的 scx_layered 崩了是 Meta 的事,内核只保证兜底。**2007 年的维护者难题不是被回答了,是被 eBPF 这项技术搬出了内核树。** 这一点上你是对的:Linus 2024-06-11 那封信里一个字没提 Tejun,提的是「树外没法让所有人满意,进树一起做」。

**纠一半。** Linus 点头之后的三个月,拦住 sched_ext 的恰恰不是技术问题,是维护问题:Gleixner 要的是「与调度核心的干净集成」,Qais 要的是 review 和「别动 schedutil」,6.12 pull request 的第一条就是「Improve integration with sched core」。换句话说,eBPF 解决了「策略错了谁负责」,没解决「钩子本身谁维护」—— 那几百行插进 pick_next_task 和调度类链的 C 代码仍然在树内,仍然需要一个愿意处理别人机器上问题的人。这个人是 Tejun:他已经维护 cgroup 和 workqueue 十几年,Peter Zijlstra「I hate all of this」之后还是逐条 review 了补丁,正是因为对面坐的是一个会把 review 意见全部吃掉的维护者。Con Kolivas 2007 年缺的就是这个位置。

所以更准确的说法是:**eBPF 把需要维护者的那块缩小到了钩子;而钩子的维护者,Linus 事先已经认识。** 2007 年 Linus 要的是一个人扛整个调度器,2024 年他只需要一个人扛一个调度类 —— 技术把「人」的需求缩小了,但没缩到零。这也是 §5.4 表里「可插拔的粒度」那一行的另一面:粒度小到一个调度类,维护者的门槛才低到有人愿意站上去。

### §5.7 你的视角:看门狗能踢人、任务能回退,2004 年缺的是即时编译?

> 反问:看门狗把超时的 BPF 调度器踢下去、任务回退 fair 类,这一招为什么 2004 年的 plugsched 做不到?
> 你的回答:缺了即时编译技术的进步。

**认一小半。** 即时编译确实在链条上:BPF 的 x86 JIT 是 2011 年(3.0)才有的(待核 #16),没有它,每次 pick_next_task 都跑解释器,调度器热路径会慢到没人敢用。LLVM 的 BPF 后端(2015)、BTF(2018)和 CO-RE(2019)则让「用 C 写一个完整调度器、编译成 BPF」从玩具变成工程(待核 #17)。所以 JIT 决定了 sched_ext **快不快**。

**纠大半:** 但「能不能踢、能不能回退」跟快慢无关,2004 年缺的是另外三样东西,而且一样比一样根本。

| 缺的东西 | 何时出现 | 它让哪件事成为可能 |
|---|---|---|
| **验证器** —— 加载前静态证明程序不越界、不死循环、只碰内核允许的内存 | eBPF 2014(3.18,Alexei Starovoitov);有界循环 2019(5.3)(待核 #18) | 「踢下去」的前提是它没把内核搞坏。plugsched 的调度器是原生 C,和内核共用一个地址空间,崩了可能已经踩烂了 runqueue,**踢也来不及** |
| **struct_ops** —— 让一个 BPF 程序实现一张内核 ops 表(先给了 TCP 拥塞控制用) | 2020(5.6,Martin KaFai Lau)(待核 #19) | sched_ext 的 select_cpu / enqueue / dispatch 回调就是一张 struct_ops 表;内核握着表的所有权,**随时可以把表换掉** |
| **调度类链** —— 调度器不是一个整体,是一串按优先级排列的类 | 2007 CFS 同期引入(How §4) | 这是最根本的一条。**plugsched 换的是整个调度器,踢掉它之后没有东西可以回退**;sched_ext 只是链上多挂一节,踢掉它,任务移回 fair 类,fair 类的 sched_entity 一直还在 task_struct 里 |

注意第三条的时间:调度类链是 2007 年 CFS 带进来的,也就是说 **plugsched 被否决和「回退能力」的诞生是同一年**。Ingo 否决 plugsched 时说的「一个好的胜过三个平庸的」,顺手把 fair 类做成了日后所有例外的兜底。这也是为什么 How §7 的兜底表读起来像是为 sched_ext 量身定做的:它确实是,只是早了 17 年。

一句话:即时编译让它快,验证器让它安全,struct_ops 让它可换,调度类链让它有退路。2004 年四样一样没有;你说的那一样,恰好是四样里最不关键的。

## §6 主线旁的三条支线(压短)

### §6.1 民间线:一个人的调度器,2004 ~ 2021(以及 2026)

Con 退出主线后两年,2009 年 8 月 31 日发布 BFS(Brain Fuck Scheduler),明确不打算进主线:单条全局队列、不做任何交互性估计、优先级只看 nice,「我不相信一刀切的调度器」([LWN 2017-04-20](https://lwn.net/Articles/720227/))。值得一记的是:**BFS 用的就是 EEVDF 的虚拟期限思路**(每个任务进队列拿一个 slice 和一个 deadline,期限早的先跑),比主线早了 14 年(为什么隔了 14 年,见 §4.5)。2016 年 10 月 BFS 升级为 MuQSS(每核一条跳表队列,解决多核扩展性)。2021 年 8 月 Con 停止更新 -ck 和 MuQSS,最后一版对应 5.12(待核 #11);2026 年 8 月又有报道称他恢复了 -ck 发布,仍不打算进主线(待核 #12)。

民间线对主线的贡献是两次「证明可行」:2007 年证明不猜也能顺,2009 年证明期限排序能用。主线两次都是别人拿去重写。

### §6.2 实时线:C6·有人等不起 的二十年

- 2004 年,Ingo Molnar 和 Thomas Gleixner 开始维护 PREEMPT_RT 补丁集,让内核几乎处处可抢占(待核 #13)。
- 2014 年,SCHED_DEADLINE 进 3.14:How §2.6 讲的 dl 类,任务声明 runtime / deadline / period,内核做准入控制([LKML 3.14 pull](https://lkml.indiana.edu/1401.2/01843.html))。
- 2024 年 9 月,PREEMPT_RT 本体合入 6.12,与 sched_ext 同一个版本(待核 #14)。

实时线的二十年说明:C6 从来不是靠「公平调度器调一调」解决的,它需要另一条调度类(2007 年 Ingo 做调度类的直接动机之一)加上整个内核的可抢占化。

### §6.3 组调度:C7·同机多租户 几乎与 CFS 同时

CFS 进 2.6.23 的同一个月,Srivatsa Vaddagiri(IBM)的「group-aware CFS」已经在 -mm 里:把 CFS 的红黑树和纳秒记账「重复一层」,用户级 / 容器级实体各自一棵树([Vaddagiri,LKML 2007-06-23](https://lwn.net/Articles/239619/))。它没赶上 2.6.23 是因为 cgroup 本身没准备好,2.6.24 一起合入(待核 #15)。2011 年 Paul Turner(Google)的 CFS bandwidth control 加上 cpu.cfs_quota_us / cpu.cfs_period_us,进 3.2 —— 就是 How §6 的 cpu.max([LWN 2011-02](https://lwn.net/Articles/428230/))。

组调度是三条支线里最「顺」的一条:因为它不换算法,只是把同一个算法再套一层。这呼应 §0 的结论:每一代只换约束变硬的那一块。

---

## §7 约束回扣:当年的约束组合 ≠ 今天的

| 年份 / 人 | 当时已变硬的约束 | 当时不存在或还软的 | 留下的「历史债」 |
|---|---|---|---|
| 1991 Linus | C1·CPU快IO慢、C2·程序不让台 | C4 ~ C8 全部不存在(单核、个位数进程) | counter/2 + priority 的「睡得多优先」,无意间开了交互性启发式的头 |
| 2002 Ingo | C4·调度不免费、C5·核间不通气 | C3 没被当真(用猜的);C6 只有粗糙的 rt 类 | 每核队列骨架是资产;交互性启发式是负债 |
| 2007 Con / Ingo / Linus | C3·凭账不凭嘴 | C8 被明确否决;C7 同年立刻变硬(2.6.24 组调度) | 红黑树 + 调度类是资产;「睡醒的人排哪」的启发式是新负债 |
| 2014 | C6·有人等不起(硬版本) | | dl 类单独一条,不与 fair 共享账本 |
| 2023 Peter | C6·有人等不起(软版本:份额外要时限) | | placement 争论未完 |
| 2024 Tejun / Linus | C8·一算法不配万场景 | | taint / bug 报告可信度问题被搁置;cgroup 与 sched_ext 的交互仍在演进 |

两个观察:

1. **约束变硬的顺序和 Why 那一节六刀的顺序几乎一致**:先是等待(C1)和不让台(C2),再是代价(C4)和多核(C5),然后才是记账哲学(C3)和期限(C6)。Why 是按逻辑切的,历史是按年代长的,两者吻合说明那六刀切在了真实的关节上。
2. **每次换代都是「约束变硬 + 有人证明可行 + 有人愿意维护」三者同时满足**。2007 年 Con 满足前两条不满足第三条,所以赢的是 Ingo;2021 年 Gushchin 的提案满足第一条不满足第二条,所以要等 Tejun 用一整个调度类 + Meta 的百万台机器来证明。

### §7.1 你的视角:每一代都有代价 —— 七种调度器的优缺点总表

> 你的话:「所以 O(1) 其实是用空间换时间,还是有代价的。要把每种调度器的优缺点说清楚。」

**认一半。** O(1) 确实是空间换时间:每核两个数组 × 140 个链表头 + 两张 140 位的位图,换来「选人 = 找位图最低置位」一条指令。但空间本身很便宜(每核几 KB,2002 年的服务器不在乎),**O(1) 真正付出的是精度**:它把「每个任务应得多少」这个连续量压进 140 个格子,格子之间只能靠时间片长短和启发式去凑 —— §2.4 的病根不是附带的,是空间换时间这笔交易的真实账单。

**纠一半。** CFS 不是空间换时间,它走的是反方向:把数组和位图全扔了,换成一棵红黑树,选人靠缓存的最左节点仍是 O(1),但插入 / 删除退到 O(log n),每个 tick 还要更新 vruntime 和 min_vruntime。它付的是**时间换精度**:纳秒级账本,不再猜。Ingo 当年的辩护是 n 通常很小、log n 可以忽略,真正的代价在缓存 —— 树节点散在内存里,不如数组连续。所以 O(1) 和 CFS 是两笔方向相反的交易,不能合在一起说。

下面把每一代摊开,**优点 / 代价 / 交易的本质 / 哪条约束逼的**四列对齐。「代价」一列是这一代被换掉或被绕开的原因,也是下一代的起点。

| 调度器 | 优点 | 代价(缺点) | 交易的本质 | 逼它出现的约束 |
|---|---|---|---|---|
| **1991 for 循环**(0.01) | 30 行,零数据结构;counter 累积让睡得多的任务自动优先,桌面顺手 | 每次换人扫全表 O(n);全局一把锁;counter 全零时重算一遍把 L1 吹飞 | 时间换简单 | C1·CPU快IO慢、C2·程序不让台(单核个位数进程够用) |
| **2002 O(1)** | 选人一条指令;每核队列不抢锁;没有重算循环 | 140 格精度;交互性靠猜睡眠时间,猜错反噬;搬进 expired 数组的任务要等 active 清空才能再跑,CPU 密集任务延迟没上限 | 空间 + 精度换时间 | C4·调度不免费、C5·核间不通气 |
| **2007 CFS** | 不猜,纳秒账本;份额精确到 nice 权重;调度类链让 rt / fair / idle 分层;组调度可以嵌套 | 插入 / 删除 O(log n);每 tick 记账;红黑树缓存不友好;「睡醒的人排哪」仍是启发式;延迟需求没法表达(nice 只管多少,不管多快) | 时间换精度 | C3·凭账不凭嘴 |
| **2023 EEVDF** | 份额和时限进一张账本;slice 短 = 期限早,延迟可表达;删掉大部分唤醒启发式 | 结构代价与 CFS 相同;placement 争论没完;Peter 自述基准「一堆赢一堆输」,吞吐型负载有回退报告(待核 #21) | 同 CFS,多付一个期限维度的记账 | C6·有人等不起(软版本) |
| **2009 BFS / 2016 MuQSS**(树外) | 简单;桌面延迟低;2009 年就用了虚拟期限 | 单条全局队列 O(n),16 核以上不扩展(MuQSS 改每核跳表才缓解);没有 cgroup;树外无人维护 | 扩展性换简单与低延迟 | 只认 C3 + C6,放弃 C5、C7 |
| **2014 SCHED_DEADLINE** | 真正的硬期限;准入控制保证总量不超;任务可以精确声明 runtime / period / deadline | 必须自己声明三个参数;特权类,一旦占满 fair 类没得跑;与 fair 不共享账本,两套逻辑 | 易用性换确定性 | C6·有人等不起(硬版本) |
| **2024 sched_ext** | 策略可换,不重启;错了看门狗回退 fair;负载各写各的 | 每次决策跨一次 BPF 边界(验证器 + JIT 之后仍有调用开销);验证器限制表达力(有界循环、无递归);加载后 bug 报告可信度存疑;与 cgroup 的交互仍在演进 | 开销 + 复杂度换灵活性 | C8·一算法不配万场景 |

从表里读三件事:

1. **没有一代是免费的,每一代的「代价」列正好是下一代的「逼它出现的约束」**。O(1) 付精度 → CFS 来还;CFS 付延迟表达 → EEVDF 来还;EEVDF 仍是一个算法 → sched_ext 来还。换代不是进化,是换一笔交易。
2. **树外线和主线的区别在于肯不肯付 C5 和 C7**。BFS 把扩展性和 cgroup 两笔账直接不付,所以简单;主线必须付,所以复杂。这不是谁对谁错,是面向的机器不同。
3. **sched_ext 没有废掉任何一笔旧交易**。EEVDF 的账本还在(兜底),dl 类还在(硬期限),它只是允许在这些之上再加一笔。所以它的代价是叠加的,不是替换的 —— 这也是 Gleixner 要「干净集成」的原因:新交易不能把旧账本弄脏。

#### §7.1.1 「每次决策跨一次 BPF 边界」是什么意思

> 你问:这句话是什么意思?

先看 fair 类怎么做决策。核心代码要选下一个任务时,调用 pick_next_task_fair(),这是内核里一个普通的 C 函数:同一份代码、同一块内存,它直接伸手进红黑树取最左节点,编译器能内联,CPU 的分支预测认得它。**决策和执行决策的人在同一个房间里。**

sched_ext 把决策搬到了房间外。调度策略是一段 BPF 程序,它和内核之间隔着一条线:

| 线的这边(内核 C 代码) | 线的那边(BPF 程序) |
|---|---|
| 持有 runqueue、task_struct、所有真实状态 | 只能看到内核通过参数递过来的东西 |
| 想要一个决策时,通过 struct_ops 表里的函数指针调过去:select_cpu(p, prev_cpu, flags) / enqueue(p, flags) / dispatch(cpu, prev) | 算完以后,不能直接改内核的队列,只能调用内核预先批准的几个 kfunc(如 scx_bpf_dsq_insert)把任务放进一条**内核拥有**的派发队列 DSQ |
| 每次调过去之前要检查:调度器还活着吗?记一下时间戳给看门狗 | 每条指令都经过验证器,只能用有界循环,不能递归 |

「跨一次边界」就是一次这样的往返:内核 → 函数指针 → BPF 蹦床 → JIT 出来的机器码 → kfunc 回内核 → 返回。跟一次直接的 C 函数调用比,多出来的是:

1. **间接调用**:函数指针调用不能内联,在开了 Spectre 缓解的 x86 上还要走 retpoline / IBT(待核 #23 具体开销);
2. **数据不在手边**:BPF 程序看不到红黑树,只能操作自己的 map 和内核递过来的 DSQ,一个任务从入队到被选中至少走 enqueue 和 dispatch 两次回调,中间还要经过一条内核拥有的队列,而 fair 类只是一次 rb_insert;
3. **每次都要验明正身**:看门狗时间戳、「调度器是否已被踢」的检查,这是 §5.6 讲的「错了不伤内核」的运行时账单。

所以这句话的意思是:**sched_ext 用「每个决策都要出一次房间」换「房间外的人随时可以换」。** 出一次门的开销是几十到几百纳秒量级(待核 #23),fair 类的 pick 本身也在这个量级,也就是说热路径的成本大约翻倍。

Tejun 的缓解办法正好回答了前面那个反问(开销落在三问的哪一问上最贵):

| 三问 | 多久跨一次边界 | sched_ext 的省法 |
|---|---|---|
| 谁先上 | 每次换人 —— 最热 | 每个 CPU 有一条本地 DSQ,本地 DSQ 不空时内核直接弹出,**不叫 BPF**;dispatch 回调一次可以批量派发多个任务 |
| 跑多久 | 每个 tick | slice 由 BPF 在入队时设一次,之后内核自己递减,**不叫 BPF**;tick 回调可以不实现 |
| 放哪个核 | 每次唤醒 | select_cpu 可以不实现,退回内核默认的 idle 核选择 |

答案:**最贵的是「谁先上」,因为它每次换人都要问;sched_ext 的整个数据结构设计(本地 DSQ + 批量派发)就是为了让这一问尽量不出门。** How §7 的 DSQ 机制,从这个角度看就是一道减少跨界次数的缓存。

### §7.2 你的视角:推动换代的是工业,不只是内核里的人

> 你的话:「调度器的迭代应该也是计算机工业发展的要求:多核多进程、CPU 的不断加强、IT 行业的发展、大规模并发任务的互联网应用的爆炸式增长,推动了技术的革新。」

**认。** 这一节前面一直在讲「约束变硬」,但约束不会自己变硬 —— 把它拧硬的是机器和负载。把每次换代背后的工业推力摊开,三列:硬件变了什么、负载变了什么、机器归谁管。

| 换代 | 硬件 | 负载 | 机器归谁管 | 被拧硬的约束 |
|---|---|---|---|---|
| 1991 for 循环 | 一颗 386,单核 | 一个人的几个终端和编译 | 爱好者自己 | C1·CPU快IO慢、C2·程序不让台 |
| 2002 O(1) | 8 ~ 16 核 SMP 服务器 | 互联网第一波:Java 应用服务器、成百上千线程 | 企业机房(IBM 等厂商 2000 年前后押注 Linux) | C4·调度不免费、C5·核间不通气 |
| 2007 CFS + 组调度 | 单核频率停涨,桌面也开始双核(2006 Core 2 Duo) | 桌面 Linux 普及(Ubuntu 2004 起)带来音频 / 视频用户,Con 代表的就是他们;同时 Google 把「容器」概念送进内核(cgroup 前身 process containers,待核 #22) | 桌面个人 + 第一批超大规模数据中心 | C3·凭账不凭嘴、C7·同机多租户 |
| 2014 SCHED_DEADLINE | 嵌入式与工控多核化 | 汽车、工业控制、音频工作站 | 设备厂商 | C6·有人等不起(硬) |
| 2023 EEVDF | 手机 big.LITTLE 异构核普及 | Android / ChromeOS 的触控延迟、游戏帧时间 | 手机与浏览器厂商 | C6·有人等不起(软) |
| 2024 sched_ext | 单机上百核、NUMA、异构 | 超大规模部署(Meta 一百万台以上同构机器)、游戏主机(Steam Deck)、AI 训练;负载以周为单位换 | 少数几家拥有百万台机器的公司 | C8·一算法不配万场景 |

**一处精修。** 「CPU 的不断加强」要拆开看:2005 年前后单核频率停止增长,CPU 的「加强」从此几乎全部变成「加核」和「加异构」。这件事对调度器的意义比任何一次算力提升都大 —— 它把 C5 从「服务器才有的问题」变成「每台机器都有的问题」,又在十年后把「放哪个核」从对称选择变成异构选择。换句话说,推动调度器的不是 CPU 变快,是 CPU 变宽。

**一处补充。** 工业推力是必要条件,不是充分条件。§4.5 讲的 14 年空档、§3.5 讲的维护者问题都说明:负载早就把约束拧硬了,主线仍然要等到「有人证明 + 有人维护」。所以本节的公式应该是:**工业把约束拧硬 → 有人证明新答案可行 → 有人愿意扛 → 换代**。前一个是你说的推力,后两个是人的变量,缺一个都会拖年。

---

## §8 呼应灵魂问题

灵魂问题的前半截(调度器替系统做什么、怎么做)在 How 已经闭环到约 70%;这一节补上「它为什么长成这样」:每一个机制都有一个被约束逼到墙角的年份和一个人。

后半截(cgroup / sched_ext 增强了什么、为什么需要)在这一节闭环到约 85%:

- cgroup 的「为什么」:2007 年公平记账一落地,「以组为单位公平」的需求就跟着来了(C7·同机多租户),解法是把同一套账本再套一层,所以它顺。
- sched_ext 的「为什么」:2007 年被否决的问题在 2024 年翻案,不是因为谁说服了谁,而是 eBPF 让「错了不伤内核」成立、超大规模部署让「一个算法不够」成立、调度类链让「可插拔」只需多挂一节(C8·一算法不配万场景 的三个条件同时满足)。
- 还剩 15% 留给 Deep:sched_ext 的回调在 6.12 源码里具体怎么挂进 pick_next_task,看门狗怎么踢人回 fair 类,以及 cgroup 子树的 vruntime 怎么跨层折算。

What §7 的五个悬念,到这一节的状态:

| 悬念 | 状态 |
|---|---|
| 1 调度器在谁的时间里跑 | How §3.6 已揭 |
| 2 轮流为何不够公平 | How §2 揭机制,本节 §3 揭历史(2007 年公平之争) |
| 3 视频为何卡 | How §4 揭机制,本节 §4 揭历史(份额 ≠ 时限,EEVDF) |
| 4 为何要分组 | How §6 揭机制,本节 §6.3 揭历史 |
| 5 一个算法能覆盖所有场景吗 / 内核为何肯交权 | 本节 §5 闭合:两个答案,二十年,三个条件 |

---

## 一手资料引用列表

| 年份 | 来源 | 链接 |
|---|---|---|
| 1991 | Linux 0.01 kernel/sched.c(源码镜像) | https://github.com/mariuz/linux-0.01/blob/master/kernel/sched.c |
| 2002-01 | Ingo Molnar,O(1) scheduler 设计文档(sched-design.txt 存档) | https://courses.cs.tau.ac.il/os/orish/src/Documentation/sched-design.txt |
| 2007-03-08 | Ingo Molnar 回复 RSDL 发布 | https://lkml.indiana.edu/0703.1/0053.html |
| 2007-03-09 | William Lee Irwin III 转述 Linus 对可插拔调度器的回应 | https://lkml.iu.edu/hypermail/linux/kernel/0703.1/0982.html |
| 2007-03 | LWN,RSDL 报道 | https://lwn.net/Articles/230247/ |
| 2007-04-13 | Ingo Molnar,CFS 发布邮件(LWN 转载) | https://lwn.net/Articles/230501/ |
| 2007-04-15 | Matt Mackall 反驳 Ingo(内引 Ingo 否决 plugsched 原话) | https://lists.openwall.net/linux-kernel/2007/04/15/135 |
| 2007-04-16 | Con Kolivas 回复 CFS 发布 | https://lists.openwall.net/linux-kernel/2007/04/16/41 |
| 2007-04-17 | LWN,Schedulers: the plot thickens | https://lwn.net/Articles/230574/ |
| 2007-06-23 | Srivatsa Vaddagiri,Add group awareness to CFS v2 | https://lwn.net/Articles/239619/ |
| 2007-07-24 | APC Magazine,Why I quit: kernel developer Con Kolivas(存档) | https://web.archive.org/web/20110707151924/http://apcmag.com/why_i_quit_kernel_developer_con_kolivas.htm |
| 2007-07-27 | Linus Torvalds,为什么不合 SD | https://lists.openwall.net/linux-kernel/2007/07/28/29 |
| 2007-07-29 | Ingo Molnar,CFS 起源与 62 小时 | https://lists.openwall.net/linux-kernel/2007/07/29/293 |
| 2007-07-31 | Ingo Molnar,为什么内核不该有可插拔调度器 | https://lists.openwall.net/linux-kernel/2007/07/31/376 |
| 2007-10-09 | kernelnewbies,Linux 2.6.23 | https://kernelnewbies.org/Linux_2_6_23 |
| 2011-02 | LWN,CFS bandwidth control | https://lwn.net/Articles/428230/ |
| 2014-01 | LKML,scheduler changes for v3.14(含 SCHED_DEADLINE) | https://lkml.indiana.edu/1401.2/01843.html |
| 2017-04-20 | LWN,The MuQSS CPU scheduler(含 BFS 设计) | https://lwn.net/Articles/720227/ |
| 2021-10 | LWN,Roman Gushchin 的 BPF 调度钩子提案 | https://lwn.net/Articles/873244/ |
| 2023-02-10 | LWN,The extensible scheduler class | https://lwn.net/Articles/922405/ |
| 2023-03-06 | Peter Zijlstra,EEVDF using latency-nice(cover letter) | https://lkml.indiana.edu/2303.0/05235.html |
| 2023-03-09 | LWN,An EEVDF CPU scheduler for Linux | https://lwn.net/Articles/925371/ |
| 2024-06-11 | Linus Torvalds,决定合入 sched_ext | https://lkml.iu.edu/hypermail/linux/kernel/2406.1/03724.html |
| 2024-06-19 | Thomas Gleixner,请求缓三个月 | https://lkml.iu.edu/hypermail/linux/kernel/2406.2/05614.html |
| 2024-06-20 | Linus Torvalds,「detest」已被取代 | https://lkml.iu.edu/hypermail/linux/kernel/2406.2/07255.html |
| 2024-07-25 | Qais Yousef,对 6.11 pull request 的反对 | https://lists.openwall.net/linux-kernel/2024/07/25/30 |
| 2024-07-30 | Tejun Heo 回复 taint 问题 | https://lists.openwall.net/linux-kernel/2024/07/31/36 |
| 2024-09-12 | Tejun Heo,sched_ext 6.12 pull request | https://lists.openwall.net/linux-kernel/2024/09/13/45 |
| 2024-09-26 | LWN,Sched_ext at LPC 2024 | https://lwn.net/Articles/991205/ |
| — | 维基百科 Con Kolivas(传记与访谈概括) | https://en.wikipedia.org/wiki/Con_Kolivas |

## 无一手资料或仅有二手转述的部分

- Con Kolivas 2007 年访谈正文:存档页只保留了导语和评论区,正文未取到;本节引用的是导语、Con 本人在评论区的补充、以及维基百科对访谈的概括。
- Linus 2007 年 3 月关于可插拔调度器的原话,取自 William Lee Irwin III 的转引,未取到 Linus 原帖。
- 「大学团队双盲测试 SD vs CFS」只有 Linus 的转述,未找到测试本身。
- Meta 2025 年改用 scx_lavd 的说法来自科技媒体对 LPC 2025 演讲的报道,未取到演讲材料。
- plugsched 首次被拒的年份:Ingo 2007 年 7 月说「4 年前」,同年 4 月的说法是「2-3 年前」,本节写 2004 年前后。

## 待核清单(导出前统一核实)

(2026-11-12 导出前已统一核实,逐条结果见综合长文末尾《收尾核实》。)

#1 Linux 0.01 发布日期 1991-09-17;#2 O(1) 进 2.5.2 的具体版本与日期;#3 双盲测试的出处;#4 EEVDF 论文编号 TR-95-22;#5 EEVDF 合入 6.6 的 commit 与日期;#6 plugsched 首次被拒年份;#7 sched_ext 6.12 合入 commit 与日期(2024-09-21);#8 6.12 发布日期(2024-11-17);#9 SteamOS 启用 scx_lavd 的版本;#10 Meta 改用 scx_lavd 的材料;#11 -ck 最后一版 5.12 与 2021-08 停更;#12 2026-08 -ck 恢复的报道;#13 PREEMPT_RT 补丁集起始年份;#14 PREEMPT_RT 合入 6.12 的日期;#15 组调度合入 2.6.24 的日期(2008-01)。

---
- #16 BPF x86 JIT 首次合入 3.0(2011,Eric Dumazet)
- #17 LLVM BPF 后端 2015 / BTF + CO-RE 2019 年份
- #18 eBPF 验证器随 3.18(2014)合入;有界循环 5.3(2019)
- #19 struct_ops 合入 5.6(2020),首个用户是 TCP 拥塞控制
- #20 Ingo 2009-09-06 LKML「BFS vs. mainline scheduler benchmarks and measurements」出处与 Con 的回应
- #21 EEVDF 合入 6.6 后吞吐型负载回退报告的出处(Phoronix / LKML)
- #22 cgroup 前身 process containers 由 Google(Paul Menage / Rohit Seth)提出的年份与合入版本 2.6.24
- #23 BPF struct_ops 间接调用 + 蹦床一次往返的开销量级(retpoline / IBT 环境下)

## 修订记录

| 时间 | 修订摘要 | 触发原因 |
|---|---|---|
| 2026-11-08 | 初稿:序章(0.01 / O(1))、2007 公平之争、2023 EEVDF、可插拔谱系单独成节、三条支线、约束回扣、一手资料 29 条 | 对齐 Q1~Q3 + reconfirm 后用户「动手吧」 |
| 2026-11-08 | §5.6 新增《你的视角》:用户答「点的是 eBPF 这项技术」;认一半(eBPF 把「别人机器上的问题」搬出内核树)、纠一半(钩子仍在树内,6.11→6.12 拦住它的正是集成与 review,Tejun 的维护者身份仍是前提) | 用户视角(反问 1) |
| 2026-11-08 | §5.7 新增《你的视角》:用户答「缺了即时编译技术的进步」;认一小半(JIT 决定快慢)、纠大半(验证器 / struct_ops / 调度类链才决定能踢能退);待核 #16~#19 | 用户视角(反问 2) |
| 2026-11-08 | §4.5 新增《你的视角》:用户答「看见了,有东西拦着」;认大半(捆绑 C5 / 没痛 C6 / 没人)、纠一点(拦的不是反对,是缺理由与缺人);§6.1 加交叉引用;待核 #20 | 用户视角(反问 3) |
| 2026-11-08 | §7.1 新增《你的视角》:用户指出 O(1) 是空间换时间、要把每种调度器优缺点说清楚;认一半(O(1) 付的其实是精度)纠一半(CFS 是时间换精度,方向相反);加七种调度器「优点 / 代价 / 交易本质 / 逼它的约束」总表;待核 #21 | 用户新视角(读稿后) |
| 2026-11-08 | §7.1.1 新增:解释「每次决策跨一次 BPF 边界」(fair 类同屋直取 vs BPF 隔线调用:函数指针 / struct_ops / DSQ / kfunc / 看门狗),并按三问给出跨界频率与省法,回答反问 4「最贵在谁先上」;待核 #23 | 用户不懂反馈 |
| 2026-11-08 | §7.2 新增《你的视角》:用户提出换代由工业发展推动(多核、互联网并发爆炸);认 + 加「硬件 / 负载 / 机器归谁管 / 被拧硬的约束」表;精修「CPU 加强」为「CPU 变宽」;补充工业推力是必要不充分;待核 #22 | 用户新视角(读稿后) |
| 2026-11-12 | 导出前核实:§5.5 Meta 使用 scx_lavd 的表述改为「跑在一部分生产服务器上、全机队默认调度器的候选」并注明各家报道说法不一;§5.7 BTF 年份更正为 2018(CO-RE 仍为 2019) | 导出前统一核实 |
