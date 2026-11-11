# 阶段 5:Linux 进程调度器 的深度剖析

> 源码一律钉在 **Linux 6.12**(2024-11-17 发布,sched_ext 首次合入的版本)。行号形如 `core.c:6548` 指 `kernel/sched/core.c` 第 6548 行;`fair.c` = `kernel/sched/fair.c`,`ext.c` = `kernel/sched/ext.c`,`entry_64.S` = `arch/x86/entry/entry_64.S`。贴出的原文只挑关键段,逐句注释。
>
> 三条主线(对齐时选定):**一次换人的全路径**(含 fork 分支,配纳秒时间线)、**cgroup 账本跨层 + 带宽**、**sched_ext 挂载 / 回调 / 看门狗回退**。其余机制 §5 只给结论。每条主线配伪代码 + 可运行脚本(`src/`),每个核心机制后做一次反事实(4 候选)。
>
> 叙事主角换回「内核」和「你」:How 里的「你」是写第一个调度器的人,这一节的「你」是拿着 6.12 源码对照着读的人。

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

## §0 从 Origin 走到 Deep:三件事记住

Origin 把每个机制钉到了一个年份和一个人,但留下了三个「具体怎么做到的」:switch_to 到底换了什么、cgroup 的账怎么跨层、sched_ext 的回调怎么插进 pick_next_task 又怎么被踢出去。这一节只做这三件事,每件事都从一次真实事件出发,顺着函数链钉到行号。

**第一件:换人 = 换一根内核栈。** 因为 C1·CPU快IO慢(等的时候要换人)+ C2·程序不让台(到点要强换)→ 要解决「一个正在内核里跑到一半的任务,怎么冻结、以后怎么原样解冻」→ 所以每个任务有自己的内核栈,换人就是 `__switch_to_asm` 里的一条 `movq TASK_threadsp(%rsi), %rsp`;寄存器只存 6 个 callee-saved,其余按 ABI 本来就是死的。C4·调度不免费 规定了这一步必须便宜:直接成本 1~2 μs,其中换栈本身只占约 20 ns。

**第二件:跨层 = 同一段时间在每一层各记一次账。** 因为 C7·同机多租户(公平单位是组)+ C3·凭账不凭嘴(组也只能凭账)→ 要解决「一个任务跑了 Δt,它所在的组、组的组,各自的 vruntime 该怎么动」→ 所以 `for_each_sched_entity(se)` 自下而上走一遍,每层用该层实体的权重把同一个 Δt 折成该层的虚拟时间;选人时 `pick_task_fair` 自上而下在每层各做一次 EEVDF。带宽控制是同一条链上的附加项:每层 `account_cfs_rq_runtime`,池空就整组出队。

**第三件:可换 = 在类链上多挂一节,并且随时能摘。** 因为 C8·一算法不配万场景(策略要能换,错了不伤内核)+ C4(热路径不能慢太多)→ 要解决「BPF 程序怎么接到 pick_next_task,又怎么在它出错时把所有任务安全送回 fair」→ 所以 ext 类被链接脚本钉在 fair 之后、idle 之前;决策通过 `SCX_CALL_OP` 跨一次边界;看门狗按 `runnable_at` 查饥饿,超时就走 `scx_ops_disable_workfn`:先 bypass 保证前进,再逐个改 `p->sched_class`(为什么必须先 bypass,见 §4.4.3)。

| 三件事 | 是什么 | 为什么存在 |
|---|---|---|
| 换栈即换人 | `__switch_to_asm`:6 push、换 rsp、6 pop;`inactive_task_frame` 是冻结格式 | C1 + C2 要求任意点可冻结;C4 要求便宜 |
| 账本跨层 | `for_each_sched_entity` 上行记账 + `pick_task_fair` 下行选人;`cfs_bandwidth` 池 + 5 ms 领取 | C7 要组级公平;C3 要组也凭账 |
| 类链可换 | 链接脚本定序;`balance_scx → SCX_CALL_OP(dispatch)`;看门狗 → bypass → 改类 | C8 要可换且不伤内核;C4 要本地 DSQ 挡掉多数跨界 |

三者嵌套:第三件事里被踢回 fair 的任务,落回第二件事的树里;第二件事选出的任务,最终由第一件事换上核。

---

## §1 一张极简概览图

![Deep 鸟瞰:三条主线从 __schedule 出发](pics/05-overview.svg)

从图上能读出五件事:

1. 三条主线共享一个入口 `__schedule()`(core.c:6548),区别只在 `pick_next_task` 里走哪条路、以及 `context_switch` 之前谁动了账本。
2. 主线一是一条直线:tick → 置标志 → 出口检查点看见标志 → 选人 → 换栈。没有任何一步是「后台线程」做的,全部借用被打断的那个任务的内核栈(How §3.6 悬念 1 的源码版)。
3. 主线二的两个箭头方向相反:记账自下而上(任务 → 组 → 根),选人自上而下(根 → 组 → 任务)。带宽池挂在组上,不挂在任务上。
4. 主线三里,BPF 程序只出现在一个绿框里;它左右两侧的 `balance_one` 和 `pick_task_scx` 都是内核 C 代码,而且本地 DSQ 有人时根本不进绿框。
5. 红框是唯一一条「向后」的路:看门狗发现有任务超时没跑,就把所有任务送回主线二的树里。整个系统没有第二个兜底。

---

## §2 主线一:一次换人的全路径

### §2.1 节首结论

- 换人分三段:**决定要换**(tick 里的 `update_curr` 发现 deadline 到期,置一个标志位)、**选出换谁**(出口检查点看见标志,进 `__schedule`,红黑树里找 eligible 且 deadline 最早的)、**真的换**(`context_switch`:先换页表根,再换栈,再换 6 个寄存器)。
- 第三段是全部魔法所在:`__switch_to_asm` 一共 14 条指令,**换 rsp 的那一条执行完,`current` 就已经是另一个人**;随后的 pop 弹出的是新任务当年压进去的值,`__switch_to` 的 ret 回到的是新任务当年调用 `context_switch` 的地方。
- 一个被换下的任务,留下的全部痕迹 = 它的内核栈 + 栈顶 `inactive_task_frame` 里 6 个寄存器 + `mm->pgd`。task_struct 是账本,不是身份。
- fork 不走捷径:`copy_thread` 伪造一帧 `inactive_task_frame`,把返回地址写成 `ret_from_fork_asm`,所以新进程第一次被选中时走的是**和老任务完全一样的 pop 路径**,只是弹出来的是伪造值。
- 直接成本 1.5~2 μs(待核 #24),换栈本身约 20 ns;大头在 tick 记账、锁、CR3、段寄存器和 FPU;间接成本(缓存变冷)更大。这是 `sysctl_sched_base_slice = 750000` ns(fair.c:76)不敢再短的理由(C4·调度不免费)。

### §2.2 操作层:从用户态能看到什么

用户态看不到换人,只看得到它的账:

| 观察点 | 含义 | 对应内核计数 |
|---|---|---|
| `getrusage().ru_nvcsw` / `/proc/<pid>/status` 的 `voluntary_ctxt_switches` | 自己睡过去的次数(门 2:读管道、等锁) | `__schedule` 里 `switch_count = &prev->nvcsw`(core.c:6644) |
| `ru_nivcsw` / `nonvoluntary_ctxt_switches` | 被抢的次数(门 1 tick、门 3 唤醒抢占) | `switch_count = &prev->nivcsw`(core.c:6600) |
| `/proc/schedstat` 第 2 列 | 该 CPU 上 `rq->nr_switches` | core.c:6655 `rq->nr_switches++` |
| `perf stat -e context-switches` | 同上,按进程 | tracepoint `sched:sched_switch`(core.c:6700) |

`src/05-switch-demo.c` 用三个场景分别逼出三种账:两个忙循环压同一个核只能靠 tick 抢(nivcsw 涨),两个线程用管道乒乓每拍都睡(nvcsw 涨约 2000),最后 fork 一次看子进程「从没调过 fork 却从 fork 返回 0」。

### §2.3 函数逻辑层:三段各在哪一行

#### §2.3.1 决定要换:tick 里的 20 行

`sched_tick()`(core.c:5584)每 1~4 ms 在**被打断的任务自己的内核栈上**跑一次,关键一行是 `curr->sched_class->task_tick(rq, curr, 0)`,fair 类落到 `task_tick_fair`(fair.c:13049):

```c
/* fair.c:13049 */
static void task_tick_fair(struct rq *rq, struct task_struct *curr, int queued)
{
	struct sched_entity *se = &curr->se;
	for_each_sched_entity(se) {          /* 自下而上:任务 → 它的组 → 组的组 …(§3 再讲) */
		cfs_rq = cfs_rq_of(se);
		entity_tick(cfs_rq, se, queued); /* → update_curr(cfs_rq) */
	}
	...
}

/* fair.c:1216 */
static void update_curr(struct cfs_rq *cfs_rq)
{
	delta_exec = update_curr_se(rq, curr);              /* 这次 tick 距上次记账,实际跑了多少 ns */
	curr->vruntime += calc_delta_fair(delta_exec, curr);/* 折成虚拟时间:Δ × 1024 / weight(fair.c:289) */
	resched = update_deadline(cfs_rq, curr);            /* vruntime 追上 deadline 了吗 */
	update_min_vruntime(cfs_rq);
	...
	account_cfs_rq_runtime(cfs_rq, delta_exec);        /* 带宽记账(§3.4) */
	if (cfs_rq->nr_running == 1) return;                /* 只有一个人,换给谁 */
	if (resched || did_preempt_short(cfs_rq, curr)) {
		resched_curr(rq);                               /* 置标志,不换人 */
		clear_buddies(cfs_rq, curr);
	}
}

/* fair.c:1007 */
static bool update_deadline(struct cfs_rq *cfs_rq, struct sched_entity *se)
{
	if ((s64)(se->vruntime - se->deadline) < 0) return false; /* 还没到期 */
	if (!se->custom_slice) se->slice = sysctl_sched_base_slice;   /* 0.75 ms */
	se->deadline = se->vruntime + calc_delta_fair(se->slice, se); /* EEVDF:vd = ve + r/w */
	return true;                                                   /* 吃完一片,该让了 */
}
```

`resched_curr`(core.c:1079)只做两件事:`set_tsk_need_resched(curr)` 置 `TIF_NEED_RESCHED`,`set_preempt_need_resched()` 把 per-CPU 的 `preempt_count` 最高位清零(让后面 `need_resched()` 一次比较就能判)。**tick 到这里就结束了,没有换人。** 这正是 How §3.2 「门 1 只敲门」的源码依据:中断处理函数里不能当场换人,原因不是「中断要短」,是「此刻不在一个能被冻住的位置」,见下面 §2.3.1.1。

**§2.3.1.1 反问:已经知道该换了,为什么不在中断里当场 schedule**

> 你的答:「中断处理函数要求尽快结束,所以采用标签后处理方式。」

**认一小半,纠大半。** 「中断里的活要短」是内核的通则,没错;但它解释不了这里。看 §2.3.2 就知道:标志置上之后,`schedule()` 就在**同一次中断的返回路上**被调用(`irqentry_exit_to_user_mode → exit_to_user_mode_loop`,common.c:228 → :101),中间只隔几十纳秒,整个换人照样在回用户态之前做完。它不是软中断那种「先返回、以后再说」的延后,而是**挪了个位置**:从处理函数里面,挪到处理函数已经完全退出之后。所以真正的问题是:为什么处理函数里面那个位置不行?

答案接着 §2.5 的结论走:**换人 = 把 prev 此刻的栈原样冻住,不知多久以后再解冻**。那么换人的位置必须满足「此刻栈上的一切都经得起冻」。中断处理函数中间不满足,有三样东西冻不得:

| 冻不得的东西 | 具体是什么 | 当场换会怎样 |
|---|---|---|
| ① 中断自己的半截现场 | `sched_tick` 正持着 `rq_lock(rq)`(core.c:5584 起第 15 行拿、第 31 行放),`task_tick` 就在锁里面跑;硬中断计数还没减(`irq_exit_rcu` 没走),软中断、RCU 的收尾都排在后面 | `__schedule` 第一件事也是拿这把 rq 锁 → 自己等自己。就算先放锁,硬中断计数非零时调度,`schedule_debug` 直接报 `BUG: scheduling while atomic`(core.c:5864 / :5903) |
| ② 可能不在任务自己的栈上 | 中断如果打断的是内核态代码,x86-64 会切到**每 CPU 一根的中断栈**上跑处理函数(irq_stack.h:132~151;打断用户态时不切,因为任务内核栈是空的) | 换人只换 `thread.sp`,冻住的那几帧却躺在 CPU 公用的中断栈上;下一次中断一来就被覆盖,prev 再也回不来。**只有站在任务自己的栈上才能换** |
| ③ 被打断的代码手里可能有锁 | tick 不知道自己打断了谁:可能是用户态代码,也可能是一段正持着自旋锁、关了抢占的内核代码 | 把一个持自旋锁的任务换下去,其他核上等这把锁的人就一直空转到它再被调度 —— 可能永远 |

所以内核把「发现该换」和「真的换」拆成两步,第二步只在**出口检查点**做,这些点的共同性质是「栈上没有冻不得的东西」:

- **回用户态之前**(`exit_to_user_mode_loop`,common.c:101):处理函数已经退完,回到了任务自己的内核栈,栈上只剩一份 `pt_regs`,不可能持有任何内核锁。永远安全。
- **中断返回内核态之前**(`raw_irqentry_exit_cond_resched`,common.c:303):先看 `preempt_count() == 0`(被打断的代码没持锁、没关抢占),是才 `preempt_schedule_irq()`(core.c:7003)。这是可抢占内核才有的检查点。
- **`preempt_enable()` 把计数减到 0 的那一刻**:第 ③ 条里那段持锁代码放完锁,自己检查标志,补上刚才欠的那次换人。

`TIF_NEED_RESCHED` 这个标志位就是为了跨过这段「知道该换但位置不对」的距离存在的:因为 C2·程序不让台(必须能强行换)+ 换人要冻栈(只能在安全点换)→ 要解决「发现的时刻和能换的时刻不是同一个时刻」→ 所以引入一个挂在任务上的标志,由发现者置、由最近的安全点读。

你那句话在另一个地方是对的:中断里做**唤醒**(网卡中断唤醒等数据的进程)时,`try_to_wake_up` 可能发现被唤醒者该抢占当前任务,同样只置标志就走。那里「尽快结束」确实是考虑之一;但根上还是同一条:中断处理函数中间不是能冻的位置。

#### §2.3.2 选出换谁:出口检查点到红黑树

中断返回前,`exit_to_user_mode_loop`(kernel/entry/common.c:90)检查标志:

```c
/* kernel/entry/common.c:101 */
while (ti_work & EXIT_TO_USER_MODE_WORK) {
	local_irq_enable_exit_to_user(ti_work);
	if (ti_work & _TIF_NEED_RESCHED)
		schedule();                      /* 门口。此时在进程上下文,可以换人了 */
	...
}
```

如果中断打断的是内核态(抢占式内核),走的是 `raw_irqentry_exit_cond_resched`(common.c:303)→ `preempt_schedule_irq`。两条路都进 `__schedule()`(core.c:6548):

```c
/* core.c:6548,删去注释 */
static void __sched notrace __schedule(int sched_mode)
{
	cpu = smp_processor_id(); rq = cpu_rq(cpu); prev = rq->curr;
	local_irq_disable();
	rq_lock(rq, &rf);                                   /* 每核一把锁(C5):只锁自己的队 */
	update_rq_clock(rq);
	switch_count = &prev->nivcsw;                       /* 默认按「被抢」记 */
	prev_state = READ_ONCE(prev->__state);
	if (sched_mode == SM_IDLE) { ... }
	else if (!preempt && prev_state) {                  /* prev 自己把状态改成了 SLEEP(门 2) */
		if (signal_pending_state(prev_state, prev)) WRITE_ONCE(prev->__state, TASK_RUNNING);
		else { block_task(rq, prev, flags); block = true; }  /* 出队:睡的人不留在树里 */
		switch_count = &prev->nvcsw;                    /* 改按「自愿」记 */
	}
	next = pick_next_task(rq, prev, &rf);               /* ← 选人 */
picked:
	clear_tsk_need_resched(prev);
	clear_preempt_need_resched();
	if (likely(prev != next)) {
		rq->nr_switches++;
		RCU_INIT_POINTER(rq->curr, next);
		++*switch_count;
		trace_sched_switch(preempt, prev, next, prev_state);   /* bpftrace 钩的就是这里 */
		rq = context_switch(rq, prev, next, &rf);       /* ← 真的换;顺手放锁 */
	} else { ... raw_spin_rq_unlock_irq(rq); }
}
```

`pick_next_task`(core.c:6044)在没开 core scheduling 时就是 `__pick_next_task`(core.c:5952):

```c
/* core.c:5952 */
if (scx_enabled()) goto restart;                         /* 装了 BPF 调度器就不走快路(§4) */
if (likely(!sched_class_above(prev->sched_class, &fair_sched_class) &&
	   rq->nr_running == rq->cfs.h_nr_running)) {        /* 全是 fair 任务:99% 的情况 */
	p = pick_next_task_fair(rq, prev, rf);
	if (unlikely(p == RETRY_TASK)) goto restart;
	if (!p) { p = pick_task_idle(rq); put_prev_set_next_task(rq, prev, p); }
	return p;
}
restart:
	prev_balance(rq, prev, rf);
	for_each_active_class(class) {                       /* 按链接脚本的顺序:stop dl rt fair ext idle */
		if (class->pick_next_task) { p = class->pick_next_task(rq, prev); if (p) return p; }
		else { p = class->pick_task(rq); if (p) { put_prev_set_next_task(rq, prev, p); return p; } }
	}
	BUG();                                               /* idle 类永远有人,走不到 */
```

fair 的选人最终落到 `pick_eevdf`(fair.c:907):先看最左节点是否 eligible(`vruntime ≤ 平均 vruntime`),是就直接要;否则沿树下行,利用每个子树缓存的 `min_vruntime` 剪枝,找 eligible 里 deadline 最早的。How §2.4 讲的「水位」在这里是 `entity_eligible`,`sched_feat(RUN_TO_PARITY)` 则保证选中的人至少把这一片跑完再换(减少换人次数,C4)。

#### §2.3.3 真的换:context_switch 的三步

```c
/* core.c:5272,删注释 */
context_switch(struct rq *rq, struct task_struct *prev, struct task_struct *next, struct rq_flags *rf)
{
	prepare_task_switch(rq, prev, next);
	arch_start_context_switch(prev);
	if (!next->mm) {                               /* 换到内核线程:借用 prev 的地址空间,不换 CR3 */
		enter_lazy_tlb(prev->active_mm, next);
		next->active_mm = prev->active_mm;
		if (prev->mm) mmgrab_lazy_tlb(prev->active_mm); else prev->active_mm = NULL;
	} else {                                       /* 换到用户进程 */
		membarrier_switch_mm(rq, prev->active_mm, next->mm);
		switch_mm_irqs_off(prev->active_mm, next->mm, next);   /* ① 换页表根 CR3 */
		lru_gen_use_mm(next->mm);
		if (!prev->mm) { rq->prev_mm = prev->active_mm; prev->active_mm = NULL; }
	}
	switch_mm_cid(rq, prev, next);
	prepare_lock_switch(rq, next, rf);
	switch_to(prev, next, prev);                   /* ② 换栈 + ③ 换寄存器;这一行「返回」时已是 next 在跑 */
	barrier();
	return finish_task_switch(prev);               /* 在 next 的栈上收尾:放锁、prev->on_cpu = 0 */
}
```

`switch_to` 宏(switch_to.h:49)只是 `last = __switch_to_asm(prev, next)`。汇编全文(entry_64.S:177,删注释与安全缓解):

```asm
SYM_FUNC_START(__switch_to_asm)
	pushq	%rbp              /* 顺序必须和 inactive_task_frame 一致(switch_to.h:23) */
	pushq	%rbx
	pushq	%r12
	pushq	%r13
	pushq	%r14
	pushq	%r15
	movq	%rsp, TASK_threadsp(%rdi)   /* prev->thread.sp = 当前栈顶:prev 被冻结在这里 */
	movq	TASK_threadsp(%rsi), %rsp   /* rsp = next->thread.sp:从此刻起,我们站在 next 的栈上 */
	popq	%r15              /* 弹出的是 next 上次被冻结时压的值 */
	popq	%r14
	popq	%r13
	popq	%r12
	popq	%rbx
	popq	%rbp
	jmp	__switch_to       /* C 收尾:段寄存器、TLS、FPU、pcpu_hot.current_task(process_64.c:609) */
SYM_FUNC_END(__switch_to_asm)
```

`__switch_to`(process_64.c:609)做的是「寄存器里装不下、又必须跟着任务走」的东西:`save_fsgs` / `load_TLS` / `x86_fsgsbase_load`(线程局部存储基址)、`switch_fpu_prepare / finish`(惰性 FPU)、`raw_cpu_write(pcpu_hot.current_task, next_p)`(这一行之后 `current` 宏才指向 next)、`update_task_stack`(内核入口栈指针 sp0)。它的 `ret` 弹出的返回地址是 next 当年调 `__switch_to_asm` 时压的,于是执行流回到 **next 的** `context_switch` 第 5331 行,接着 `finish_task_switch(prev)`。prev 这个指针是怎么跨过换栈传过来的?`__switch_to` 的返回值,在 rax 里。这就是 `switch_to(prev, next, last)` 第三个参数 `last` 的全部意义:切栈之后,寄存器是两个世界之间唯一的信使。

### §2.4 底层原理层:为什么是「栈 + 6 个寄存器 + 页表根」

![switch_to 的魔法:两根栈、一条 movq、一帧伪造](pics/05-context-switch.svg)

**为什么只存 6 个寄存器?** 因为 `__switch_to_asm` 是一个普通函数调用。x86-64 SysV ABI 规定 rbx、rbp、r12~r15 是 callee-saved,其余(rax、rcx、rdx、rsi、rdi、r8~r11)在任何函数调用边界上都视为已毁。prev 调用 `switch_to` 时,编译器已经把它还需要的 caller-saved 值压到 prev 自己的栈帧里了。所以**换栈这个动作借用了 C 函数调用的约定,把「保存现场」的大部分工作免费交给了编译器**。用户态的全部寄存器呢?在中断 / 系统调用进内核时就压成 `pt_regs` 躺在栈底了,返回用户态时统一恢复。

**为什么页表根单独换?** CR3 不是寄存器文件的一部分,它是 MMU 的配置;而且同一进程的多个线程共享一份,换线程时不用换。所以它跟着 `mm` 走(`switch_mm_irqs_off`),不跟着 `thread` 走。现代 x86 有 PCID,换 CR3 不必刷 TLB,这一步从「几 μs」降到了「几百 ns」。

**为什么是每任务一根内核栈,而不是每 CPU 一根?** 因为 Linux 允许内核代码在**任何地方**睡:`pipe_read` 在第 3 层调用深处发现没数据,直接 `schedule()`。要在任意深度冻结并原样解冻,唯一通用办法就是把整根栈留着。每 CPU 一根栈的设计(某些微内核、早期 Mach 的 continuation)要求每个可能睡的点都显式保存状态,内核代码写法完全不同。这是 C1·CPU快IO慢 在内核内部的体现:内核自己也要「等的时候换别人上」。

**纳秒账单**(图左栏;数字是典型现代 x86 服务器量级,待核 #24,可用 `src/05-sched-switch.bt` 的 `@switch_ns` 直方图实测):

| 段 | 做什么 | 量级 |
|---|---|---|
| 中断进入 | 压 pt_regs、swapgs、换到中断栈 | 100~200 ns |
| sched_tick → update_curr → resched_curr | rq 锁、读时钟、乘除折算、置标志 | 300~600 ns |
| exit_to_user_mode_loop → __schedule → pick_eevdf | 再拿 rq 锁、红黑树 O(log n) | 300~500 ns |
| switch_mm_irqs_off | 写 CR3(PCID) | 100~300 ns |
| __switch_to_asm | 6 push、2 movq、6 pop | ≈ 20 ns |
| __switch_to | FS/GS/TLS、FPU、per-CPU current | 100~300 ns |
| finish_task_switch | 放锁、prev->on_cpu = 0 | ≈ 100 ns |
| **直接合计** | | **≈ 1.5~2 μs** |
| 间接 | L1/L2 变冷、分支预测器洗牌 | 之后几十 μs 内变慢 |

每秒一万次换人就是 1.5~2% 的 CPU 直接开销,外加更大的间接开销。`sysctl_sched_base_slice` 默认 0.75 ms、`RUN_TO_PARITY` 保证跑完一片,都是在这张账单上做的取舍(C4·调度不免费)。

### §2.5 你的视角:进程 = 栈 + 寄存器

> 你的话:「switch_to 的魔法,通过切换内核栈来切换不同的进程,其实标志一个进程的所有信息就是栈与寄存器;这里揭示了一个本质。」

**认。** 在 `__switch_to_asm` 那 14 条指令的尺度上,这句话是精确的:换 rsp 之前是 prev,换 rsp 之后是 next,中间没有任何其他状态被触碰。CPU 不认识 task_struct,它只认识 rsp 指向哪里、下一条指令在哪里;而「下一条指令在哪里」本身就存在栈上(ret_addr)。所以**进程对 CPU 而言就是一根栈,寄存器是栈的工作副本**。

**纠一小处,补两点。**

1. 严格说是三样:栈、寄存器、页表根。CR3 决定「栈上那些地址指向哪块物理内存」,没有它,同一个 rsp 在两个进程里指的是两个世界。但它跟着 mm 走而不是跟着线程走,所以线程切换确实只有前两样。
2. task_struct 是账本不是身份:vruntime、deadline、nice、cgroup 归属都在里面,调度器用它决定**换给谁**;但**换这个动作**不读它,只读 `thread.sp`。这也是为什么 sched_ext 换掉整个决策层却完全不碰 `context_switch`(§4):身份和账本是分开的。
3. 这个本质在创建那头也成立,见 §2.6:fork 不是「复制一个进程」,是「伪造一根栈,让它看起来像刚被换下去」。

#### §2.5.1 反问:另外 10 个通用寄存器去哪了

> 问:x86-64 有 16 个通用寄存器,`__switch_to_asm` 只 push 了 rbp、rbx、r12~r15 六个。rax、rcx、rdx、rsi、rdi、r8~r11 这 10 个换人时没存,被换下去的任务换回来后为什么不会算错?
> 你的答:「这些由 CPU 来保存恢复。」

**纠大半,认一小角。** 在 `switch_to` 这条路径上,CPU 一个寄存器都没替内核存;那 10 个是**编译器**存的,而且存在 `__switch_to_asm` 被调用之前。

**为什么是编译器**。`switch_to` 对编译器来说就是一次普通的函数调用:`__schedule → context_switch → switch_to(prev, next, prev) → __switch_to_asm`。System V x86-64 调用约定把 16 个通用寄存器分成两类(entry_64.S:78 的注释原话:"r12-r15, rbp, rbx are callee-preserved in C ABI"):

| 类别 | 寄存器 | 约定 | 换人时谁负责 |
|---|---|---|---|
| callee-saved(被调用方保存) | rbx、rbp、r12~r15 | 被调用的函数如果要用,必须自己存、返回前恢复;调用方默认它们不变 | `__switch_to_asm` 的 6 push / 6 pop。**这是唯一需要汇编手工做的部分** |
| caller-saved(调用方保存) | rax、rcx、rdx、rsi、rdi、r8~r11 | 调用方默认它们会被调用的函数糟蹋掉;如果调用之后还要用,调用前自己压栈 | 编译 `context_switch` / `__schedule` 时,gcc 已经在 `call __switch_to_asm` 之前把还要用的值 spill 到了 prev 的内核栈上,调用返回后再从栈上读回。换人代码对此**一无所知,也不需要知道** |

所以那 10 个寄存器不是没存,是**在 rsp 还指着 prev 的栈时,被 prev 自己的编译结果存进了 prev 的栈**;几毫秒后 prev 被换回来,`__switch_to_asm` 的 `ret` 回到 `context_switch` 里 `call` 的下一条指令,编译器生成的代码从栈上把它们读回。它们跟着栈走了一圈。

这反过来加强了 §2.5 的结论:寄存器里真正「不在栈上」的只有 6 个 callee-saved 加 rsp 本身,其余全部已经是栈的一部分。**进程 ≈ 栈,外加 7 个寄存器的零头**。

**认的那一小角:CPU 确实替内核存过东西,但不在这里**。一个任务从用户态进内核有两条门:

- 中断 / 异常:CPU 硬件自动往内核栈压 5 个字(ss、rsp、rflags、cs、rip),然后由入口汇编 `PUSH_AND_CLEAR_REGS`(entry_64.S:848 / 870)把 15 个通用寄存器压成 `pt_regs`。
- `syscall` 指令:CPU 只把 rip 存进 rcx、rflags 存进 r11,其余全部由软件压(entry_64.S:101~109)。

这些是**用户态的寄存器现场**,在任务进内核的那一刻就已经在内核栈底的 `pt_regs` 里躺好了,比 `switch_to` 早得多,而且 CPU 只负责最多 5 个字,大头仍是软件。换人时它们原封不动留在 prev 的栈底,prev 将来 `sysret` / `iret` 回用户态时再由软件弹回。

**还有一类谁都没提的:浮点 / 向量寄存器**(xmm、ymm、zmm,最多 2 KB 多)。它们既不是 callee-saved 也不在 `pt_regs` 里,由 `__switch_to` 的 `switch_fpu_prepare`(process_64.c:620)用 XSAVES 存到 task_struct 尾部的 `fpu` 区,恢复延迟到下次回用户态(`switch_fpu_finish`,:674,只置 TIF_NEED_FPU_LOAD 标志)。这是 §2.4 时间线里「FPU」那一项的几十到几百纳秒的来源 —— 也是整个换人里**唯一真正按「寄存器」而非「栈」保存的大块状态**,但它是软件 XSAVES,仍然不是 CPU 自动。

**小结**:换人路径上,寄存器分四层去处 —— 6 个 callee-saved 由 `__switch_to_asm` 手工 push;10 个 caller-saved 由编译器提前 spill 进栈;用户态现场早在进内核时就进了 `pt_regs`(CPU 自动压的只有中断那 5 个字);FPU 状态由 `__switch_to` 用 XSAVES 存进 task_struct。「CPU 来保存」这个直觉对应的是 1980 年代 x86 TSS 硬件任务切换的做法(§2.7 候选 A),Linux 2.x 就放弃了它,原因正是 C4·调度不免费:硬件存全部寄存器比软件只存 6 个慢,而且存了一堆编译器早就放进栈里的东西。

#### §2.5.2 反问:A 醒来后怎么知道是 C 把 CPU 让给它的

> 问:A 换给 B 时,A 栈上的局部变量 `prev` 记的是 A 自己。很久以后 C 换回 A。A 的栈原封不动冻着,`prev` 还是 A;可 A 醒来要给「刚才让出 CPU 的人」收尾(`finish_task_switch(prev)`),那个人是 C。A 怎么知道?
> 你的答:「switch_to 会修改这个 prev 的栈上的值到 C。」

**认。结果就是这样:A 的 `prev` 被改写成了 C。** 补的是「谁改的、值怎么过来的」,因为这里有个容易想岔的地方:C 那一侧**没有任何代码伸手去写 A 的栈**。改写发生在换栈之后,是 A 自己的代码写的,值是坐寄存器过来的。

`context_switch` 里那一行有三个参数(core.c:5328),宏只有一句(switch_to.h:49):

```c
switch_to(prev, next, prev);
#define switch_to(prev, next, last)  ((last) = __switch_to_asm((prev), (next)))
```

把 C 换给 A 的那一次,按指令摆开:

| 时刻 | 跑在谁的栈上 | 发生了什么 |
|---|---|---|
| ① | C | C 的 `context_switch` 调 `__switch_to_asm(prev = C, next = A)`:rdi = C,rsi = A |
| ② | C → A | 6 push、换 rsp、6 pop。**此刻栈已经是 A 的,但 rdi / rsi 还是 C 那边放进去的值**(caller-saved,没人动它们) |
| ③ | A | `jmp __switch_to(rdi = C, rsi = A)`,函数末尾 `return prev_p;`(process_64.c:712)—— 返回值 rax = C |
| ④ | A | `ret` 弹出的返回地址是 A 当年压的,回到 **A 的** `context_switch`,执行宏的后半句 `last = rax`,也就是 A 的 `prev = C` |
| ⑤ | A | `finish_task_switch(prev)`(core.c:5331)拿到的是 C:清 `C->on_cpu`、放 rq 锁;如果 C 已经死了(TASK_DEAD),顺手释放它的 task_struct |

所以信使是 **rax**。§2.5.1 说过寄存器里「不在栈上」的只剩一个零头,这里正好用上了这个零头的另一面:**换栈会把栈上的一切都换掉,只有寄存器原样穿过去**。内核想从「上一个世界」带一句话到「下一个世界」,只能放在寄存器里。`switch_to` 的第三个参数 `last` 就是为这一句话存在的。

两处细节:

- 你说的「栈上的值」,实际可能在栈上,也可能被编译器放在某个 callee-saved 寄存器(比如 rbx)里。两种情况一样:那 6 个寄存器在 ② 里被 pop 回了 A 当年的旧值(A 自己),随后同样被 `last = rax` 覆盖。
- 为什么收尾必须由 A 来做、不能让 C 走之前自己做?因为 C 在 ② 换掉 rsp 之后就不再执行任何指令了,而「清 `on_cpu`」「放 rq 锁」必须在**确实已经离开 C 的栈之后**做,否则别的核可能看到 `C->on_cpu == 0` 就把 C 拉过去跑,而 C 的栈这边还有人在用。一个任务没法给自己收尾,只能由接班的人代劳。

fork 分支是同一个信使的另一个用法:新进程没有 `context_switch` 的栈帧,更没有 `prev` 这个局部变量可改,所以 `ret_from_fork_asm` 第一条有效指令就是 `movq %rax, %rdi  /* prev */`(entry_64.S:240),把 rax 直接当参数传给 `schedule_tail(prev)`(§2.6 第 3、4 步)。

### §2.6 fork 分支:一个从没跑过的进程怎么从 switch_to 醒来

`copy_thread`(arch/x86/kernel/process.c:159)为子进程准备的东西:

```c
/* process.c:159,删注释,只留用户线程路径 */
childregs = task_pt_regs(p);                                /* 子进程内核栈顶端预留的 pt_regs 位置 */
fork_frame = container_of(childregs, struct fork_frame, regs);
frame = &fork_frame->frame;                                 /* 紧贴在 pt_regs 下面的 inactive_task_frame */
frame->bp = encode_frame_pointer(childregs);
frame->ret_addr = (unsigned long) ret_from_fork_asm;        /* ★ 伪造的「返回地址」 */
p->thread.sp = (unsigned long) fork_frame;                  /* ★ 下次 __switch_to_asm 会把 rsp 换成这里 */
...
frame->bx = 0;                                              /* 用户线程:bx = 0 表示没有内核函数要跑 */
*childregs = *current_pt_regs();                            /* ★ 整份复制父进程的用户态现场 */
childregs->ax = 0;                                          /* ★ 子进程看到的 fork() 返回值 */
if (sp) childregs->sp = sp;                                 /* clone 指定了用户栈就换 */
```

`struct fork_frame`(switch_to.h:44)就是 `inactive_task_frame` 紧跟一份 `pt_regs`:子进程的栈从一开始就长得**和一个刚被 tick 换下的老任务一模一样**。于是第一次被 `pick_next_task` 选中时:

1. `__switch_to_asm` 把 rsp 换成 `p->thread.sp`,6 条 pop 弹出伪造的 0;
2. `jmp __switch_to`,它的 `ret` 弹出 `ret_addr = ret_from_fork_asm`(entry_64.S:227);
3. `ret_from_fork_asm` 把 rax(prev)、rsp(regs)、rbx(fn)、r12(fn_arg)搬进参数寄存器,`call ret_from_fork`(process.c:140);
4. `ret_from_fork` 先 `schedule_tail(prev)`(core.c:5247)—— 替老任务路径里本该由 `context_switch` 返回后调用的 `finish_task_switch` 补课:放 rq 锁、`prev->on_cpu = 0`;
5. fn 为空,直接 `syscall_exit_to_user_mode(regs)` → `swapgs_restore_regs_and_return_to_usermode`,按 childregs 恢复全部用户态寄存器,rax = 0,sysret。

子进程「从 fork() 返回了 0」,但它从没执行过 fork 系统调用的任何一行。它只是被塞了一帧和父进程一模一样的现场,然后被当作一个普通的、曾经被换下去的任务换了上来。内核线程走同一条路,区别只是 bx = 函数指针、r12 = 参数,`ret_from_fork` 看到 fn 非空就直接调用。

`src/05-switch-demo.c` 第三段、`src/05-sched-switch.bt` 的 `kprobe:schedule_tail` 能看到这一步。

#### §2.6.1 反问:子进程的 pt_regs 是哪来的、rax 为什么是 0

> 问:prev 的用户态现场是进内核那一刻压在栈底 `pt_regs` 里的;fork 出来的子进程从没进过内核,它栈底那份 `pt_regs` 哪来的?rax 为什么是 0?
> 你的答:「在 fork 的时候强行给成了 0。」

**认一半,补一半。** rax 那一半对:`childregs->ax = 0`(process.c:232)就是一行赋值,没有任何「返回」发生,子进程将来 `sysret` 时从这个格子里弹出 0,用户态 C 库再把 rax 当作 `fork()` 的返回值。父进程的 rax 则是 `kernel_clone` 正常返回时写进父进程自己 `pt_regs` 的子 PID。两个进程「从同一个 fork() 返回了不同的值」,其实是两份 `pt_regs` 里 ax 格子被写了不同的数。

补的那一半是「哪来的」:**整份抄父进程的**。`*childregs = *current_pt_regs()`(process.c:231)把父进程进内核时压下的那 21 个字 —— 包括用户态 rip、rsp、rflags、全部通用寄存器 —— 原样复制到子进程栈底。这解释了三件读者通常不问但其实奇怪的事:

| 现象 | 来源 |
|---|---|
| 子进程醒来后执行的第一条用户指令,恰好是父进程 `syscall` 的下一条 | `childregs->ip` 抄的是父进程的 ip |
| 子进程的局部变量、调用栈、所有寄存器和父进程一模一样 | 通用寄存器抄自 `pt_regs`;用户栈内容则靠 mm 复制(COW) |
| `fork()` 不换用户栈,`clone(CLONE_VM)` 建线程才换 | `if (sp) childregs->sp = sp`(:234):只有调用者给了新栈才改,`fork` 传 0 |

所以 fork 的「复制一个进程」在调度器这一层只是三步:抄一份 `pt_regs`、改一个格子(ax)、在它下面伪造一帧 `inactive_task_frame`。剩下的「复制」全是 mm 子系统的事(页表、COW),和换人无关。这也是 §2.5 第 1 点说「页表根跟着 mm 走」的另一面:fork 后父子的 `pt_regs->sp` 数值相同,之所以不互相踩,是因为 CR3 不同,同一个数值落在两个地址空间里。

#### §2.6.2 反问:父子用户态 rsp 数值相同,为什么不互相踩

> 问:fork 后父子的 `pt_regs->sp` 是同一个数,子进程醒来就往那里压栈,父进程也还在用。为什么不踩?
> 你的答:「因为 COW。」

**认大半,往下垫一层。** COW 是让它们分开的那个动作;但它能成立,靠的是更前面的一步:**fork 给了子进程一份自己的页表**。COW 回答的是「这份页表怎么便宜地建」,不是「为什么不踩」。就算没有 COW、fork 时老老实实把内存整份抄一遍,也不会踩,只是慢。

三步,按时间:

1. **fork 时:抄页表,不抄页。** `copy_process` 在 `copy_thread` 之前先 `copy_mm`(fork.c:2374 → :1697)。没带 `CLONE_VM` 就 `dup_mm`(:1724)→ `dup_mmap` → `copy_page_range`(fork.c:746 → memory.c:1356)。走到每个页表项时(`__copy_present_ptes`,memory.c:949):

   ```c
   /* If it's a COW mapping, write protect it both processes. */
   if (is_cow_mapping(src_vma->vm_flags) && pte_write(pte)) {
   	wrprotect_ptes(src_mm, addr, src_pte, nr);   /* 父进程的页表项:去掉写位 */
   	pte = pte_wrprotect(pte);                    /* 要写给子进程的那份:也去掉写位 */
   }
   set_ptes(dst_vma->vm_mm, addr, dst_pte, pte, nr);
   ```

   结果:两份页表(两个 CR3),指向**同一批物理页**,两边都只读。此刻父子确实共用同一块栈内存,但谁都写不了。
2. **子进程第一次写栈:缺页,复制一页。** 子进程被换上来、`sysret` 回用户态,第一个 `push` 就写栈页 → CPU 发现页表项没有写位 → 缺页异常 → `handle_pte_fault` 看到「写操作 + 页表项不可写」→ `do_wp_page`(memory.c:5782 → :3655)→ `wp_page_copy`(:3331):分配一张新页、拷 4 KB、把**子进程自己的**页表项改指新页并恢复写位。从这一刻起,同一个 rsp 数值在父子两边落到两张不同的物理页上。
3. **父进程后来再写同一页:缺页,但不用复制。** 父进程的页表项也被去了写位,它写时同样缺页;但 `do_wp_page` 发现这张页现在只剩自己一个使用者(`wp_can_reuse_anon_folio`,memory.c:3724),直接恢复写位(`wp_page_reuse`,:3731),不复制。

**COW 为什么存在**:因为 fork 之后多半立刻 `exec`(shell 起命令就是这样),整份抄完马上扔掉 → 要解决「复制地址空间太贵且多半白抄」→ 所以把复制推迟到第一次写、按页进行。这是 mm 子系统的约束,不在本主题的 C1~C8 里;跟调度器沾边的只有一点:**子进程第一次上 CPU 做的第一件事,往往就是一次写保护缺页**,这笔钱不在 §2.4 的换人账单里。

**把这一问和 §2.5 合起来,得到一张判别表**。两个执行流要同时跑而不互相踩,「用户栈位置」和「页表」至少得有一样不同:

| 创建方式 | 用户 rsp 数值 | 页表(CR3) | 为什么不踩 | 源码 |
|---|---|---|---|---|
| `fork()` 的父子 | 相同 | **不同**(`dup_mm`) | 同一个数落在两个地址空间;COW 把真正的复制推迟到第一次写 | fork.c:1724 |
| `clone(CLONE_VM)` 建线程 | **不同**(调用者给新栈) | 相同(`mmget` 共享) | 同一个地址空间里各占一段 | fork.c:1720;process.c:234 `childregs->sp = sp` |
| `vfork()` | 相同 | 相同 | **会踩** —— 所以内核干脆不让它们同时跑:父进程睡到子进程 `exec` 或退出为止 | fork.c:2887 `CLONE_VFORK \| CLONE_VM`;:2824 `wait_for_vfork_done` |

第三行是这张表的反证:两样都相同时,唯一的办法是让调度器保证它们不同时运行。这也把 §2.5 的那句话补全了:**线程 = 换栈不换页表;进程 = 栈的数值可以相同,但页表不同**。

### §2.7 反事实:换人为什么是「换内核栈」

| 候选 | 做法 | 违反的约束 / 代价 | 现实里谁这么做 |
|---|---|---|---|
| A 硬件任务切换 | x86 TSS + 远跳转,CPU 自己存取全部寄存器 | C4:几百周期,存了大量用不着的寄存器;不可移植;Linux 早期用过,2.x 改为软件切换(待核 #25) | 几乎无人再用;x86-64 长模式已不支持 |
| B 存全部寄存器 | 不信任 ABI,16 个通用寄存器全压 | C4:多 10 条 push/pop,且毫无必要 —— 调用边界上 caller-saved 已死 | 某些手写汇编的 RTOS |
| C 每 CPU 一根内核栈 + continuation | 睡眠点显式保存状态,换人不换栈 | 违反「内核任意点可睡」的编程模型;驱动、文件系统全部改写法;C1 在内核内部的代价转嫁给所有开发者 | Mach 的 continuations、部分微内核、seL4(内核不可抢占) |
| D 用户态切换(绿色线程) | 进程内 swapcontext,内核看不见 | 一个阻塞系统调用卡死全部协程(C1);一个进程无法用多核(C5) | Go runtime、Java 虚拟线程 —— 但都是在内核线程**之上**叠一层,不是替代 |

**结论**:在「内核代码可以在任意深度阻塞」这个 Linux 的基本编程模型下,每任务一根内核栈 + callee-saved 最小帧是 C1 + C4 联合下的局部最优。候选 D 之所以能和它共存,正是因为它解决的是另一层的问题。

---

## §3 主线二:cgroup 账本跨层 + 带宽控制

### §3.0 零基础垫脚:cgroup 是什么、调度器看到的它长什么样

> 你的反馈:「我对 sched_ext 与 cgroup cset 都不熟悉。」这一小节和 §4.0 是两块垫脚砖,先把「它是什么」立住,再往下看源码。How §6 讲过「三问的主语从任务换成组」,这里只补最底层的用户视角。

**用户看到的 cgroup**:就是 `/sys/fs/cgroup/` 下的一棵目录树。每个目录是一个「组」,把一个进程的 PID 写进该目录的 `cgroup.procs`,这个进程(和它以后 fork 出来的子孙)就属于这个组。目录里的其他文件是旋钮:`cpu.weight`、`cpu.max`、`memory.max`、`io.max`……每种资源一套,叫一个「控制器」。本阶段只碰 CPU 控制器的两个旋钮。

```
/sys/fs/cgroup/                    ← 根组 = 整台机器
├── atlas-A/                       ← 一个组
│   ├── cgroup.procs               ← 写 PID 进来 = 把进程放进组
│   ├── cpu.weight  (= 100)        ← 跟兄弟组比,CPU 该分多少(相对份额)
│   └── cpu.max     (= max 100000) ← 每 period 最多跑多少(硬上限;max = 不限)
└── atlas-B/
    ├── cgroup.procs
    ├── cpu.weight  (= 300)
    └── cpu.max     (= 50000 100000) ← 每 100 ms 最多 50 ms
```

**为什么要有它**(C7·同机多租户):没有组之前,调度器眼里只有一个个任务,谁开的线程多谁拿的 CPU 多。一台机器上跑两个租户,A 开 30 个线程、B 开 1 个,B 几乎拿不到 CPU。要解决「先在租户之间分,再在租户内部分」,所以引入组:**调度器先把组当成一个「假任务」在上一层分 CPU,分到的那份再在组内部的成员之间分**。类比公司预算:先在部门之间按人头权重切总预算,再在部门内部按人切。

**调度器看到的 cgroup**:每个组在每个 CPU 上有自己的一棵小红黑树(`cfs_rq`),组本身在父级那棵树里占一个节点(组实体 `sched_entity`)。树套树。任务永远在叶子那棵树里;选人的时候从根那棵树一层层往下挑,记账的时候从叶子一层层往上记。这就是 §3.3 要讲的「上行记账、下行选人」。

**你提到的 cset**:内核里有个 `css_set` 结构,记的是「某个任务属于哪几个控制器的哪个组」,是 cgroup 子系统内部的会员名册,调度器不直接碰它;调度器只认 `task_group`(`p->sched_task_group`),每个 cgroup 目录对应一个。本阶段用不到 `css_set`,知道它是名册就够。

### §3.1 节首结论

- 组调度**没有新算法**。它把 How §2 的「每核一本账 + 一棵树」在每个 cgroup 里**再复制一份**:每个 task_group 在每个 CPU 上有一个 `cfs_rq`(自己的红黑树)和一个代表自己的 `sched_entity`(挂在父组的树里)。
- 跨层折算 = **同一段 Δt 在每一层各记一次账**:`for_each_sched_entity(se)` 从任务向上走到根,每层调 `update_curr`,用该层实体自己的权重把 Δt 折成该层的 vruntime。任务权重来自 nice,组实体权重来自 `calc_group_shares`(fair.c:4015):`cpu.weight × 本 CPU 上这组的负载 / 这组全部 CPU 的负载`。
- 选人反向:`pick_task_fair`(fair.c:8848)从根开始,每层做一次 `pick_eevdf`,选中组实体就下钻到它的 cfs_rq,直到选到一个真任务。深度 = cgroup 层数,每层 O(log n)。
- 带宽控制挂在同一条链上:`update_curr → account_cfs_rq_runtime`,每核从组的全局池按 5 ms 一片领额度;领不到就 `resched_curr`,随后 `throttle_cfs_rq` 把**整个组实体**从父树摘下;hrtimer 每个 period 补池并 `unthrottle`。
- 代价:tick 和 enqueue 都要走一遍层级链(C4);换来的是 C7·同机多租户 的公平单位可以是「我这一摊」而不是线程数。

### §3.2 操作层:两个文件、一个算例

cgroup v2 的 CPU 控制器只有两个旋钮(How §6.4):

| 文件 | 写入 | 内核入口 | 落到 |
|---|---|---|---|
| `cpu.weight` | 1~10000,默认 100 | core.c:9797 `cpu_weight_write_u64` → `sched_group_set_shares` | `tg->shares`,再由 `calc_group_shares` 分到每个 CPU 的组实体 |
| `cpu.max` | `quota period`(μs),如 `50000 100000` | core.c:9894 `cpu_max_write` → `tg_set_cfs_bandwidth`(:9298) | `cfs_b->quota / period`;period 限 1 ms ~ 1 s(core.c:9291) |

**算例**(`src/05-cgroup-demo.sh` 实验 1):CPU0 上,组 A(weight 100)有 3 个忙循环 t1 t2 t3,组 B(weight 300)有 1 个忙循环 t4。

- 没有 cgroup:`rq->cfs` 树里 4 个任务,nice 0 权重各 1024,每人 25%。B 的租户抱怨:「我只开了一个线程就该被三倍稀释?」(C7 的痛,How §6.2)
- 有 cgroup:`rq->cfs` 树里只有两个**组实体** se_A、se_B。单 CPU 情况下 `calc_group_shares` 的「本 CPU 负载 / 全部负载」= 1,所以 se_A 权重 ∝ 100、se_B ∝ 300:B 拿 75%,A 拿 25%。A 的 cfs_rq 里 t1 t2 t3 再均分那 25%,各 8.3%。
- 实验 2 再给 B 加 `cpu.max = 50000 100000`:B 每 100 ms 只能跑 50 ms。B 掉到 50%,被 throttle 的那 50 ms 里 A 独占,A 的三个各升到 16.7%;`B/cpu.stat` 的 `nr_throttled` 每 100 ms 加 1。

### §3.3 函数逻辑层:上行记账、下行选人

#### §3.3.1 数据:三样东西怎么连

```c
/* fair.c:306,CONFIG_FAIR_GROUP_SCHED */
#define for_each_sched_entity(se) \
		for (; se; se = se->parent)          /* 任务 se → 组实体 → 父组实体 → … → NULL(根) */
```

- `task_struct.se.parent` 指向「我所在组在**我这个 CPU** 上的组实体」;组实体的 `parent` 再往上;根组的实体 parent 为 NULL。
- 每个组实体 `se->my_q`(`group_cfs_rq(se)`)指向该组在该 CPU 上的 cfs_rq,也就是它名下任务的红黑树。
- 所以每个 CPU 上是一棵**树的树**:`rq->cfs` 的红黑树节点有的是任务、有的是组实体;组实体下面还有一棵红黑树。

#### §3.3.2 上行:同一段 Δt 记 N 次

`task_tick_fair`(§2.3.1 已贴)的 `for_each_sched_entity` 循环,每层调 `entity_tick → update_curr(cfs_rq)`。注意 `update_curr` 用的是 `cfs_rq->curr`,也就是**该层当前正在跑的实体**:在任务层是 t1,在根层是 se_A。`update_curr_se` 算出的 Δt 是同一个物理时间段,但:

```
任务层:t1.vruntime += Δt × 1024 / w(t1)     w 来自 nice,1024
根  层:se_A.vruntime += Δt × 1024 / w(se_A)  w 来自 calc_group_shares ≈ 100 × 1024/100 … 按 cpu.weight 比例
```

`calc_group_shares`(fair.c:4015)的核心三行:

```c
load = max(scale_load_down(cfs_rq->load.weight), cfs_rq->avg.load_avg); /* 这组在本 CPU 上的负载 */
tg_weight = atomic_long_read(&tg->load_avg) - cfs_rq->tg_load_avg_contrib + load; /* 这组全部 CPU 的负载 */
shares = tg_shares * load / tg_weight;                                   /* cpu.weight 按本 CPU 占比切一份 */
return clamp_t(long, shares, MIN_SHARES, tg_shares);
```

这就是「跨层折算」的全部:**权重在每层各自定义,Δt 不变,vruntime 的增量随层变**。组实体的权重还会随「这组的任务分布在几个 CPU 上」动态变化,所以 `entity_tick` 每次都调 `update_cfs_group(curr)`(fair.c:4054)重算。

#### §3.3.3 下行:每层一次 EEVDF

```c
/* fair.c:8848 */
static struct task_struct *pick_task_fair(struct rq *rq)
{
again:
	cfs_rq = &rq->cfs;                         /* 从根开始 */
	if (!cfs_rq->nr_running) return NULL;
	do {
		if (cfs_rq->curr && cfs_rq->curr->on_rq) update_curr(cfs_rq);  /* 先把这层的账记到当下 */
		if (unlikely(check_cfs_rq_runtime(cfs_rq))) goto again;        /* 这层带宽用完了?整层 throttle,重来 */
		se = pick_next_entity(rq, cfs_rq);     /* → pick_eevdf(cfs_rq):这层 eligible 里 deadline 最早的 */
		if (!se) goto again;
		cfs_rq = group_cfs_rq(se);             /* 选中的是组实体?下钻到它的树;是任务?NULL,退出 */
	} while (cfs_rq);
	return task_of(se);
}
```

同一个 `pick_eevdf` 在每一层各跑一次;选人成本 = 层数 × O(log n)。这是组调度在 C4 上的账单,也是 cgroup 层级不宜过深的源码原因。

#### §3.3.4 入队也要走链

`enqueue_task_fair`(fair.c:6955)有两个 `for_each_sched_entity` 循环:第一个自下而上把任务和「还没在父树里的」组实体依次 `enqueue_entity`(一个组实体只有当它名下第一个任务醒来时才需要挂进父树,`if (se->on_rq) break` 就是这个判断);第二个继续向上给已在树里的祖先更新负载和 `h_nr_running`。6.12 还在这里把组实体的 slice 设成子树里最小的 slice(`cfs_rq_min_slice`),保证组里有短 slice 任务时组实体自己的 deadline 也早 —— 这是 EEVDF 跨层时对 C6 的一点照顾。

### §3.4 带宽:池、片、闸

**数据**:每个 task_group 一个 `cfs_bandwidth`(全局池:`quota`、`period`、`runtime` 剩余、hrtimer `period_timer`、`throttled_cfs_rq` 链表);每个 CPU 上的 cfs_rq 一个 `runtime_remaining`(本地额度)。

**领**(fair.c:5812):

```c
static void __account_cfs_rq_runtime(struct cfs_rq *cfs_rq, u64 delta_exec)
{
	cfs_rq->runtime_remaining -= delta_exec;        /* 本地额度扣 Δt */
	if (likely(cfs_rq->runtime_remaining > 0)) return;
	if (cfs_rq->throttled) return;
	if (!assign_cfs_rq_runtime(cfs_rq) && likely(cfs_rq->curr))   /* 去全局池领一片(5 ms,fair.c:124) */
		resched_curr(rq_of(cfs_rq));                /* 领不到:置标志,让 pick 路径来处理 */
}
```

为什么每次领 5 ms 而不是精确到纳秒?因为全局池有一把锁(`cfs_b->lock`),所有 CPU 都来抢,C5·核间不通气 要求少去;5 ms 一片是「去得少」和「不浪费额度」之间的折中(`sysctl_sched_cfs_bandwidth_slice`)。

**闸**(fair.c:5915):`check_cfs_rq_runtime` 在 put_prev / pick 路径上发现 `runtime_remaining ≤ 0` 且领不到,调 `throttle_cfs_rq`:把这个 cfs_rq 挂进 `cfs_b->throttled_cfs_rq`,然后 `for_each_sched_entity(se)` 自下而上把**组实体**从父树 `dequeue_entity`,并把 `h_nr_running` 减掉整组的任务数。组里的任务一个都没动 —— 它们还在组的 cfs_rq 里,只是这棵子树整个从父树上摘了下来,`pick_task_fair` 走不到它们。

**开**(fair.c:6518 / 6279 / 6018):hrtimer `sched_cfs_period_timer` 每个 period 到期,`do_sched_cfs_period_timer` 先 `__refill_cfs_bandwidth_runtime` 把池补满(`runtime = quota`),再 `distribute_cfs_runtime` 给 `throttled_cfs_rq` 链表上的每个 cfs_rq 发额度并 `unthrottle_cfs_rq`:自下而上把组实体重新 `enqueue_entity` 回父树。如果 timer 连续 4 次都跑不完(period 太短),内核会把 period 和 quota 同时翻倍并打印 `cfs_period_timer: period too short`(fair.c:6550)。

### §3.5 反事实:组级公平为什么是「树的树」

| 候选 | 做法 | 违反的约束 / 代价 | 现实 |
|---|---|---|---|
| A 扁平化权重 | 不建层级,把组权重除以组内任务数,直接写进每个任务 | 任务睡醒、迁核时 n 变,全组任务要重算权重 O(n);无法表达「组在不同 CPU 上的占比」;C4、C5 都伤 | 早期一些「按用户公平」补丁 |
| B 只有配额、没有权重 | 只做 cpu.max,不做 cpu.weight | 空闲时无法「尽量多用」,有竞争时无法按比例分;C7 只解决一半 | 严格 VM 配额(某些 hypervisor 模式) |
| C 两级时间片 | 外层按组切大时间片,组内再跑一个独立调度器 | 组切换粒度粗,组内延迟敏感任务等整个外层片(C6);两套账本 | Xen credit、早期容器方案 |
| D 彩票 / 步幅调度带组票 | 每组一叠票,按票随机抽 | 随机性带来方差;层级要嵌套抽签;不凭账(C3 弱) | Waldspurger 1994 论文,未进主线 |

**结论**:把同一套 cfs_rq + sched_entity 在每层复制一份,是「不加新算法」前提下满足 C7 + C3 的局部最优;付的是 C4 上的层数倍数。Origin §6.3 说的「组调度之所以顺,是因为账本本身可以套娃」,源码上就是 `for_each_sched_entity` 这一个宏。

---

## §4 主线三:sched_ext 的挂载、回调与看门狗回退

### §4.0 零基础垫脚:sched_ext 是什么、eBPF 在这里扮演什么

> 同样先立「它是什么」,再看源码。How §7 讲过「三问的答题人换成你」,Origin §7.1.1 讲过「跨一次 BPF 边界」。

**原来的情形**:调度器的三个决定(谁先上、跑多久、放哪个核)全部写死在内核的 `fair.c` 里。想换一种排法,只能改内核源码、重新编译、重启机器 —— 还要说服内核维护者收下你的改动(Origin §5)。

**eBPF 是什么**:内核里一台小型的、安全的虚拟机。你用 C 写一个小程序,编译成 BPF 字节码,在运行时装进内核;装进去之前内核的**验证器**逐条检查:不会死循环、不会越界访问内存、只调用内核允许的函数(kfunc)。检查过关后,内核在特定的「钩子」上调用你这段程序。它原本用来做网络包过滤和性能追踪,sched_ext 把它用到了调度器上。

**sched_ext 是什么**(C8·一算法不配万场景):它在内核里加了一个新的调度类 ext,排在 fair 后面。这个类自己不做任何决定,它把三个决定变成三个**回调**(`select_cpu` 放哪核 / `enqueue` 谁先上 / `dispatch` 什么时候上),你用 BPF 程序把它们填上。装载方式是一个普通的用户态程序(比如内核树自带的 `scx_simple`),它把编好的 BPF 程序通过 `bpf()` 系统调用注册进去;从那一刻起,所有普通任务改由你的程序决定顺序。`Ctrl-C` 杀掉那个用户态程序,一切回到 fair。

```
            ┌──────────── 用户态 ──────────────┐        ┌───────────── 内核 ──────────────┐
            │  scx_simple(普通程序)          │        │  调度类链:stop → dl → rt → fair → ext → idle │
            │   ├─ scx_simple.bpf.c 编成 BPF  │ bpf() │                                   │  │
            │   └─ 装载 ───────────────────────┼───────▶│  验证器检查 → 挂到 ext 类的回调上 ─┘  │
            └──────────────────────────────────┘        │  每次要选人:ext 类调你的回调         │
                                                        │  看门狗:有任务 30 s 没上 → 踢掉,回 fair│
                                                        └──────────────────────────────────┘
```

**几个词**:DSQ(dispatch queue)= 候客区,一个 CPU 一个本地 DSQ,另有全局共享的;你的 `enqueue` 把任务放进某个 DSQ,`dispatch` 负责把人从共享 DSQ 搬到某个 CPU 的本地 DSQ,内核从本地 DSQ 取人上 CPU。slice = 这次上去最多跑多久,你派发时给一个数,内核自己扣。

**类比**:餐厅排号。原来叫号规则是餐厅定死的;sched_ext 允许你带一份自己的叫号规则来,餐厅先检查这份规则不会出事(验证器),然后照你的规则叫号;一旦发现有人等了 30 分钟还没被叫到(看门狗),餐厅收回规则,自己叫号(回退到 fair)。

**为什么要它**:Origin §4~§6 的二十年故事。一句话:不同机器、不同负载要不同的排法(C8),但 fair 只能有一个;以前的答案是「别想换」,sched_ext 的答案是「可以换,出错有兜底」。

### §4.1 节首结论

- **挂在哪**:链接脚本 `vmlinux.lds.h:131` 把六个 `sched_class` 结构体按 stop → dl → rt → fair → ext → idle 的顺序排成一段连续内存,`for_each_active_class` 就是指针递增。ext 在 fair 之后:**没切到 ext 的任务(如 root 的系统进程)永远比 BPF 调度器管的任务优先**;`switched_all` 模式下循环直接跳过 fair(sched.h:2535)。
- **怎么接**:`__pick_next_task` 一看 `scx_enabled()` 就放弃 fair 快路径,进类链循环;到 ext 这一节先 `balance_scx → balance_one`(ext.c:2629):本地 DSQ 有人就不叫 BPF;没人才 `SCX_CALL_OP(dispatch)` 跨一次边界;然后 `pick_task_scx` 弹本地 DSQ 队首。入队侧 `enqueue_task_scx → do_enqueue_task → SCX_CALL_OP_TASK(enqueue)`。
- **怎么踢**:每个 scx 任务记 `runnable_at`;看门狗 `scx_watchdog_workfn`(ext.c:3340)每 timeout/2 扫所有 CPU 的 `runnable_list`,有任务 runnable 却超过 timeout(默认 30 s,BPF 可设短)没跑,就 `scx_ops_error_kind(SCX_EXIT_ERROR_STALL)`。tick 里的 `scx_tick` 还反过来盯着看门狗本身有没有按时打卡。
- **怎么退**:`scx_ops_disable_workfn`(ext.c:4445)三步:`scx_ops_bypass(true)` 让所有 scx 任务走内核内置的全局 FIFO、不再调用任何 BPF 回调(保证前进);遍历所有任务 `p->sched_class = __setscheduler_class(policy, prio)` 送回 fair;关掉 `__scx_ops_enabled` 静态分支,调 `ops.exit` 通知用户态。整个过程不重启,`context_switch` 一行没改。
- 代价:每次决策多一次间接调用 + 本地 DSQ 不空才省;`scx_enabled()` 让所有换人都走慢路径(类链循环)而不是 fair 快路径。

### §4.2 操作层:一个最小 BPF 调度器长什么样

`tools/sched_ext/scx_simple.bpf.c`(156 行,内核树自带)实现了一个「全局一条按 vtime 排序的队列」:

```c
/* scx_simple.bpf.c:60 唤醒时选核:交给内核默认算法,选到空闲核就直接派到那个核的本地 DSQ */
s32 BPF_STRUCT_OPS(simple_select_cpu, struct task_struct *p, s32 prev_cpu, u64 wake_flags)
{
	cpu = scx_bpf_select_cpu_dfl(p, prev_cpu, wake_flags, &is_idle);
	if (is_idle) scx_bpf_dispatch(p, SCX_DSQ_LOCAL, SCX_SLICE_DFL, 0);  /* kfunc:放进本地 DSQ */
	return cpu;
}
/* :74 入队:按 vtime 放进共享 DSQ;睡太久的最多只能攒一片的「欠账」 */
void BPF_STRUCT_OPS(simple_enqueue, struct task_struct *p, u64 enq_flags)
{
	u64 vtime = p->scx.dsq_vtime;
	if (vtime_before(vtime, vtime_now - SCX_SLICE_DFL)) vtime = vtime_now - SCX_SLICE_DFL;
	scx_bpf_dispatch_vtime(p, SHARED_DSQ, SCX_SLICE_DFL, vtime, enq_flags);
}
/* :95 派发:某个 CPU 本地没人了,从共享 DSQ 搬一个过来 */
void BPF_STRUCT_OPS(simple_dispatch, s32 cpu, struct task_struct *prev) { scx_bpf_consume(SHARED_DSQ); }
/* :115 停下时记账:跑了多少,按权重倒数折成 vtime —— 这就是 CFS 的 vruntime,30 行写完 */
void BPF_STRUCT_OPS(simple_stopping, struct task_struct *p, bool runnable)
{ p->scx.dsq_vtime += (SCX_SLICE_DFL - p->scx.slice) * 100 / p->scx.weight; }

SCX_OPS_DEFINE(simple_ops, .select_cpu = …, .enqueue = …, .dispatch = …, .running = …,
	       .stopping = …, .enable = …, .init = …, .exit = …, .name = "simple");
```

三问各对应一个回调:谁先上 = `enqueue` 里的 vtime 排序 + `dispatch`;跑多久 = `scx_bpf_dispatch` 时给的 `SCX_SLICE_DFL`(20 ms),之后**内核自己扣**;放哪个核 = `select_cpu`。`SCX_OPS_DEFINE` 生成的就是一张 `struct sched_ext_ops`,通过 `bpf(BPF_LINK_CREATE)` 以 struct_ops 方式注册(ext.c:5618 `bpf_sched_ext_ops`,`.reg = bpf_scx_reg → scx_ops_enable`)。

用户态只看三个文件:`/sys/kernel/sched_ext/state`(enabled / disabled)、`root/ops`(调度器名)、`switch_all`。`src/05-scx-demo.sh` 装载、观察、卸载、再用 `scx_qmap -t` 故意制造饥饿触发看门狗。

### §4.3 函数逻辑层:钩子在哪、边界在哪

#### §4.3.1 挂载点:链接脚本 + 两个 goto

```
/* include/asm-generic/vmlinux.lds.h:129 */
#define SCHED_DATA
	__sched_class_highest = .;
	*(__stop_sched_class)
	*(__dl_sched_class)
	*(__rt_sched_class)
	*(__fair_sched_class)
	*(__ext_sched_class)       ← 6.12 新增的一行;fair 之后、idle 之前
	*(__idle_sched_class)
	__sched_class_lowest = .;
```

`DEFINE_SCHED_CLASS(ext)`(ext.c:3966)把 ext 的 `sched_class` 放进 `__ext_sched_class` 段;`for_class_range` 就是从 `__sched_class_highest` 到 `__sched_class_lowest` 的指针步进。**类的优先级不是运行时数据,是链接时的内存地址**,所以 `sched_class_above(a, b)` 就是 `a < b`(sched.h:2555)。

`__pick_next_task` 里两处改动(§2.3.2 已贴):`if (scx_enabled()) goto restart` 放弃 fair 快路径;`for_each_active_class` 在 `switched_all` 时跳过 fair:

```c
/* sched.h:2531 */
static inline const struct sched_class *next_active_class(const struct sched_class *class)
{
	class++;
	if (scx_switched_all() && class == &fair_sched_class) class++;   /* 全切模式:fair 树是空的,不看 */
	return class;
}
```

`scx_enabled()` 是一个 static key(`__scx_ops_enabled`,ext.c:862):没装调度器时这个 `if` 被编译成 nop,**fair 用户不为 sched_ext 的存在付任何代价**。这是 Gleixner「干净集成」要求在源码上的体现(Origin §5.3)。

#### §4.3.2 热路径:balance_one 的三道闸

```c
/* ext.c:2629,删注释 */
static int balance_one(struct rq *rq, struct task_struct *prev)
{
	if (prev_on_scx) {
		update_curr_scx(rq);                                   /* 扣 prev 的 slice */
		if ((prev->scx.flags & SCX_TASK_QUEUED) && prev->scx.slice && !scx_rq_bypassing(rq)) {
			rq->scx.flags |= SCX_RQ_BAL_KEEP; goto has_tasks; /* 闸 1:prev 还有片,继续跑它,不叫 BPF */
		}
	}
	if (rq->scx.local_dsq.nr) goto has_tasks;                  /* 闸 2:本地 DSQ 有人,不叫 BPF */
	if (consume_global_dsq(rq)) goto has_tasks;                /* 闸 3:内核内置全局 DSQ 有人,不叫 BPF */
	if (!SCX_HAS_OP(dispatch) || scx_rq_bypassing(rq) || !scx_rq_online(rq)) goto no_tasks;
	dspc->rq = rq;
	do {                                                       /* 三道闸都空,才跨边界 */
		dspc->nr_tasks = 0;
		SCX_CALL_OP(SCX_KF_DISPATCH, dispatch, cpu_of(rq), prev_on_scx ? prev : NULL);
		flush_dispatch_buf(rq);                                /* BPF 里 scx_bpf_dispatch 的结果先攒在 per-CPU 缓冲,这里一次落队 */
		if (rq->scx.local_dsq.nr) goto has_tasks;
		if (consume_global_dsq(rq)) goto has_tasks;
		if (unlikely(!--nr_loops)) { scx_bpf_kick_cpu(cpu_of(rq), 0); break; }  /* 最多 32 轮,防 BPF 死循环派不出人 */
	} while (dspc->nr_tasks);
	...
}
```

`SCX_CALL_OP`(ext.c:1084)展开就是 `scx_kf_allow(mask); scx_ops.dispatch(args); scx_kf_disallow(mask);` —— `scx_ops` 是内核持有的那份 `sched_ext_ops` 副本,`.dispatch` 是 struct_ops 注册时填进去的 BPF 蹦床地址。**这就是 Origin §7.1.1 说的「跨一次边界」在源码里的位置**:一个函数指针调用,前后各一次 kfunc 许可位的开关。`SCX_HAS_OP(op)` 也是 static key:BPF 调度器没实现的回调,连这个 `if` 都不花钱。

`pick_task_scx`(ext.c:2947)随后要么按 `SCX_RQ_BAL_KEEP` 继续跑 prev(slice 用完就补一片 `SCX_SLICE_DFL`),要么 `first_local_task(rq)` 弹本地 DSQ 队首。跑多久由 `update_curr_scx`(ext.c:1638)在 tick 里从 `p->scx.slice` 扣,扣到 0 → `task_tick_scx` 置 resched —— **BPF 只在派发时给一个数字,倒计时是内核做的**,所以「跑多久」这一问不跨边界(Origin §7.1.1 表)。

#### §4.3.3 入队侧:直派、本地、全局、还是问 BPF

`do_enqueue_task`(ext.c:1973)是一串 goto:CPU 下线中 → `local`(本地 DSQ,不问);`scx_rq_bypassing` → `global`(内核全局 FIFO,不问);BPF 在 `select_cpu` 里已经 `scx_bpf_dispatch` 过 → `direct`(不再问);没实现 `enqueue` → `global`;否则 `SCX_CALL_OP_TASK(SCX_KF_ENQUEUE, enqueue, p, enq_flags)` 跨边界问一次。任务进 `rq->scx.runnable_list` 时记 `runnable_at = jiffies`(`set_task_runnable`,ext.c:2057)—— 这个时间戳是看门狗的全部依据。

### §4.4 底层原理层:看门狗与回退

#### §4.4.1 两层看门狗

```c
/* ext.c:3313 */
static bool check_rq_for_timeouts(struct rq *rq)
{
	list_for_each_entry(p, &rq->scx.runnable_list, scx.runnable_node) {
		if (unlikely(time_after(jiffies, p->scx.runnable_at + scx_watchdog_timeout))) {
			scx_ops_error_kind(SCX_EXIT_ERROR_STALL, "%s[%d] failed to run for %u.%03us", ...);
			return true;              /* 有一个 runnable 却久等不上的任务,就判 BPF 调度器失职 */
		}
	}
}
/* ext.c:3340:工作队列项,每 timeout/2 跑一次,扫完所有在线 CPU 再把自己排回去 */
static void scx_watchdog_workfn(struct work_struct *work)
{
	WRITE_ONCE(scx_watchdog_timestamp, jiffies);                 /* 打卡 */
	for_each_online_cpu(cpu) if (check_rq_for_timeouts(cpu_rq(cpu))) break;
	queue_delayed_work(system_unbound_wq, to_delayed_work(work), scx_watchdog_timeout / 2);
}
/* ext.c:3356:tick 里反盯看门狗 —— 万一 BPF 调度器把跑看门狗的 kworker 也饿死了呢 */
void scx_tick(struct rq *rq)
{
	if (unlikely(time_after(jiffies, READ_ONCE(scx_watchdog_timestamp) + scx_watchdog_timeout)))
		scx_ops_error_kind(SCX_EXIT_ERROR_STALL, "watchdog failed to check in for %u.%03us", ...);
}
```

第二层很关键:看门狗自己是一个 kworker,也是一个被调度的任务;一个坏的 BPF 调度器完全可能把它也饿死。所以 `sched_tick → scx_tick` 这条**不经过任何调度决策的中断路径**反过来检查看门狗有没有按时打卡。超时默认 `SCX_WATCHDOG_MAX_TIMEOUT = 30 × HZ`(ext.c:14),BPF 调度器可以用 `ops.timeout_ms` 设更短但不能更长(ext.c:5120)。

#### §4.4.2 回退三步

`scx_ops_error_kind` 只是记下退出原因并 `irq_work_queue`;真正的拆除在一个专用 kthread 上跑 `scx_ops_disable_workfn`(ext.c:4445):

```c
scx_ops_bypass(true);              /* ① 所有 CPU:scx 任务改走内核内置全局 FIFO(do_enqueue_task 的 global 分支),
                                    *    balance_one 不再 SCX_CALL_OP。从这一刻起不依赖 BPF 也能前进 */
mutex_lock(&scx_ops_enable_mutex);
static_branch_disable(&__scx_switched_all);
scx_cgroup_exit();
percpu_down_write(&scx_fork_rwsem);                        /* 禁 fork,免得有任务在迁移中间出生 */
scx_task_iter_start(&sti);
while ((p = scx_task_iter_next_locked(&sti))) {            /* ② 逐个任务 */
	new_class = __setscheduler_class(p->policy, p->prio);   /*    按它本来的 policy 算回 fair / rt / dl */
	sched_deq_and_put_task(p, DEQUEUE_SAVE | DEQUEUE_MOVE, &ctx);
	p->sched_class = new_class;                             /*    改类 */
	sched_enq_and_set_task(&ctx);                           /*    重新入队:现在它在 fair 的红黑树里了 */
	scx_ops_exit_task(p);
}
static_branch_disable(&__scx_ops_enabled);                 /* ③ 关总闸:__pick_next_task 回到 fair 快路径 */
for (i = SCX_OPI_BEGIN; i < SCX_OPI_END; i++) static_branch_disable(&scx_has_op[i]);
synchronize_rcu();
pr_err("sched_ext: BPF scheduler \"%s\" disabled (%s)\n", scx_ops.name, ei->reason);
if (scx_ops.exit) SCX_CALL_OP(SCX_KF_UNLOCKED, exit, ei);  /* 最后通知 BPF 一声,带上原因和 dump */
```

第 ① 步是整个设计的要害:**先切到一个不需要 BPF 的最低限度策略,再慢慢拆**。拆的过程要拿锁、要遍历所有任务、可能睡,如果这期间还得靠 BPF 调度器派发,就可能永远拆不完。bypass 模式下的全局 FIFO 很不公平,但它只需要维持几毫秒。

回退之所以能成立,靠的是 §2.5 说的「身份和账本分开」:每个任务的 `se`(fair 的账本)从来没被删,切到 ext 时只是没人读它;`p->sched_class = &fair_sched_class` 之后 `enqueue_task_fair` 直接把它放回树里。Origin §5.7 说的「调度类链让它有退路」,源码上就是 task_struct 里同时躺着 `se` 和 `scx` 两本账。

#### §4.4.3 反问:为什么不直接改类,要先 bypass

> 你的回答:「不清楚,是稳定性的考虑?还是性能的考虑?」

**结论先说**:两个都不是主因。性能完全不是 —— bypass 态的全局 FIFO 比直接改回 fair 更慢更不公平;「稳定性」沾一点边但不准,准确的词是**活性(forward progress)+ 锁序**:改类这件事要拿睡眠锁,而看门狗被触发的那一刻,恰恰没人能保证持锁的任务还在跑。

源码自己把理由写在了 `scx_ops_bypass` 的函数注释里(ext.c:4289~4294):

```c
/*
 * Bypassing guarantees that all runnable tasks make forward progress without
 * trusting the BPF scheduler. We can't grab any mutexes or rwsems as they might
 * be held by tasks that the BPF scheduler is forgetting to run, which
 * unfortunately also excludes toggling the static branches.
 */
```

拆成三条,每条对着 §4.4.2 那段代码看:

| # | 直接改类会撞上什么 | bypass 为什么躲得开 |
|---|---|---|
| ① 锁被「忘记跑」的任务拿着 | 改类前要 `mutex_lock(&scx_ops_enable_mutex)`、`percpu_down_write(&scx_fork_rwsem)`,遍历用的 `scx_task_iter` 也可能睡。看门狗之所以触发,就是因为 BPF 调度器把某些任务晾了 30 s;这些任务里可能正有一个在 fork 中途持着 `scx_fork_rwsem` 读端。拆除线程去拿写端,就等一个永远排不上 CPU 的人放锁 —— 死锁 | bypass 只拿 `raw_spinlock` 和每个 CPU 的 `rq_lock`(ext.c:4323 / 4350),都是不睡的锁;连 `cpus_read_lock()` 都不敢用,改走 `for_each_possible_cpu`(注释 ext.c:4343~4344) |
| ② 连 static key 都翻不了 | 直觉是「先关 `__scx_ops_enabled` 总闸不就行了」。不行:`static_branch_disable` 要改代码段,内部拿 `jump_label_mutex` + `cpus_read_lock`,同样是睡眠锁。所以注释特意加一句 "also excludes toggling the static branches" —— 第 ③ 步只能放在最后 | bypass 不动任何代码,只在每个 `rq->scx.flags` 上置一个 `SCX_RQ_BYPASSING` 位,热路径用 `scx_rq_bypassing(rq)` 读这个位决定「不问 BPF」(§4.3.2 三道闸、§4.3.3 的 `global` 分支里都有这个判断) |
| ③ 拆除线程自己会不会排不上 CPU | 不会,但要看清它是靠什么不会的。`scx_ops_disable_workfn` 跑在专门的内核线程 `sched_ext_ops_helper` 上,这个线程创建时就被设成 `SCHED_FIFO`(ext.c:4948 ~ 4956 `scx_create_rt_helper` 里的 `sched_set_fifo`),属于实时类,在调度类链上排在 ext 之前,坏掉的 BPF 调度器饿不到它。它能上核,却可能卡在第 ① 条上:它要拿的睡眠锁正被一个排不上核的 ext 任务拿着 | bypass 后 `do_enqueue_task` 一律走 `global`、`balance_one` 一律不 `SCX_CALL_OP`,所有 ext 任务由内核内置 FIFO 轮着跑;tick 一到就把当前任务转到队尾(`SCX_RQ_BAL_KEEP` 不再设),slice 也不信了。持锁的那个任务于是能跑到放锁,拆除线程才等得到 |

还有一条量级上的区别:bypass 是 **O(CPU 数)**,每个 CPU 拿一次 rq 锁、把 `runnable_list` 上的任务 deq/enq 一遍(ext.c:4376~4383),几十微秒内全机一致进入「不信 BPF」状态;改类是 **O(任务数)**,逐个做、中间可以睡,第一个和最后一个任务之间必然有一段「一半在 fair、一半还在 ext」的混合态。如果这段混合态里 ext 那一半仍由坏掉的 BPF 派发,那「先改类」等于让坏调度器一直工作到最后一个任务。先 bypass,混合态就无害了。

**所以回到你的两个候选**:

- 性能:否。bypass 态的 FIFO 没有 vruntime、没有 cgroup 权重、每 tick 轮转,是三条主线里最差的策略;它的价值只在「不需要 BPF 也能跑」。
- 稳定性:沾边。少调一次坏掉的 BPF 回调,确实少一分出错机会。但这不是设计它的理由 —— 真正逼出它的是 C8·一算法不配万场景的后半句「错了不伤内核」:要能在调度器已经坏掉、任何任务都可能卡住的前提下,仍然安全地拿锁、遍历、翻代码段。这件事只能靠一个**自身不依赖任何睡眠锁、也不依赖 BPF** 的最低限度策略来兜底。

一个旁证:bypass 不只在拆除时用。装载时(ext.c:5133~5135)先开 bypass,等所有任务都切到 ext 再关;系统休眠/挂起(ext.c:5826~5838)也先开 bypass。三处的共同点是「BPF 调度器此刻不可信」—— 装载时它还没看到全部任务,挂起时用户态调度器可能已被冻结。bypass 是 sched_ext 的「安全模式」,不是拆除流程的专属步骤。

#### §4.4.4 反问:调度器刚装上、还没坏,为什么也要先 bypass

> 你的回答:「不清楚。」

注释点名的那一类是**用户态调度器**(ext.c:5130~5133:"some BPF schedulers (e.g. userspace scheduling) may not function correctly before all tasks are switched")。`scx_userland` / `scx_rustland` 这类调度器,BPF 部分只做转发:`ops.enqueue` 把任务塞进 ring buffer,真正「谁先上」由一个用户态守护进程决定,再写回来派发。

卡在哪,把装载路径(`scx_ops_enable`,ext.c:4991 起)按时间摆开就看见了:

```
用户态守护进程 ──bpf(BPF_LINK_CREATE, struct_ops)──▶ 内核 scx_ops_enable()   ← 守护进程的主线程此刻在内核里
   ①  static_branch_enable(&__scx_ops_enabled)            ext.c:5219      ← 从这一行起,任何任务都可能落到 ext 类
   ②  for 每个任务: p->sched_class = ext ...              ext.c:5228~5242 ← 逐个切,O(任务数),中间会睡
   ③  scx_ops_bypass(false)                               ext.c:5250
   ④  返回用户态,守护进程这才开始跑它的调度循环
```

鸡生蛋的点在 ①→④ 之间:**决策者还没开始工作,被它管的人已经开始排队了**。第 ② 步切过去的第一个任务一入队,`ops.enqueue` 就把它推给用户态;用户态的调度循环要到第 ④ 步才启动,所以这个任务在那之前谁也不会派发它。更要命的是注释前半句「`%current` 随时可能被切到 SCX」:做第 ② 步的线程自己就在任务表里,轮到它时它也被切成 ext 类;它接下来任何一次睡眠再醒来(迭代器里的 `cond_resched`、等 `scx_tasks_lock`)都要有人把它选上 CPU,而能选它的,是它自己还没启动的那个循环。它在等自己 —— 这就是「stall」。

纯 BPF 的 `scx_simple` 不会卡,因为它的 `enqueue` / `dispatch` 在内核里就地算完,不需要任何任务「醒着」才能做决定。用户态调度器把「做决定」这件事本身变成了一个需要被调度的任务,于是装载过程就有了和拆除过程一模一样的结构:**执行切换的人自己也是被切换的对象**。

bypass 怎么解:①~③ 之间所有 ext 任务都走内核内置 FIFO,不问 BPF 也不问用户态;第 ② 步做完、所有任务都切过去了,第 ③ 步关 bypass,第 ④ 步守护进程回到用户态开始接活。此时它面对的是「全部任务已就位」的稳定状态,不会再撞上一半 fair 一半 ext 的混合态。

跟 §4.4.3 合起来看,bypass 的三处用法其实是同一句话:**只要「做决定的人」可能排不上 CPU,就先让内核自己兜底**。拆除时是 BPF 坏了;装载时是决策者还没启动;挂起时是用户态进程被冻结。这是 C8·一算法不配万场景「错了不伤内核」在三个时间点上的同一个答案。

### §4.5 反事实:可插拔为什么长成「fair 之后的一节 + 看门狗」

| 候选 | 做法 | 违反的约束 / 代价 | 现实 |
|---|---|---|---|
| A 编译期替换整个调度器 | plugsched(2004):`CONFIG_SCHED_X` 选一个 | 没有兜底,错了就是内核崩;每个调度器都是内核 C 代码,维护者问题(Origin §5.2) | 被否决 |
| B 决策放用户态 | ghOSt(Google 2021):内核通过共享内存把事件发给用户态 agent,agent 回消息 | 每次决策跨进程边界,延迟 μs 级(C4 更重);agent 挂了要另一套回退;但不受验证器限制 | Google 内部,未进主线 |
| C 只给钩子不给类 | Gushchin 2021:在 fair 的唤醒 / 抢占决策点加 BPF 钩子微调 | 只能微调 fair,不能表达「全局一条队列」「按 cgroup 分层」这类整体策略;C8 只解决一半 | 2021 提案,被 sched_ext 取代 |
| D 把 ext 排在 fair 之前 | 让 BPF 调度器管的任务优先于未切换的 fair 任务 | 一个坏的 BPF 策略能饿死没切过去的系统进程(含看门狗 kworker);违反 C8 的「错了不伤内核」 | 无 |

**结论**:在 C8(策略可换 + 不伤内核)和 C4(热路径不能明显变慢)之下,「一个排在 fair 之后的调度类 + 本地 DSQ 挡掉多数跨界 + 以 runnable_at 为依据的两层看门狗 + bypass 后逐任务改类」是局部最优。候选 B 不是劣解,是另一个点:它用更高的每次决策成本换掉了验证器的表达力限制;Meta 选了 BPF,Google 选了用户态,对应的是两家机器上 C4 和 C8 的相对权重不同。

---

## §5 其余机制:只给结论

| 机制 | 一句话结论 | 源码入口(6.12) | 对应 How |
|---|---|---|---|
| 唤醒选核 | `select_task_rq_fair` 先看 `wake_affine`(跟唤醒者同簇),再 `select_idle_sibling` 在同 LLC 里找空闲核;找不到才算负载 | fair.c `select_task_rq_fair` | §5.2 |
| 周期性负载均衡 | 每个调度域一个周期,`sched_balance_domains` 找最忙组、`detach_tasks` 搬任务;只在 `sched_tick` 末尾 `sched_balance_trigger` 置软中断 | fair.c `sched_balance_domains`;core.c:5634 | §5.3 |
| 唤醒抢占 | `wakeup_preempt → check_preempt_wakeup_fair`:新醒的任务 deadline 比 curr 早且 eligible 就 `resched_curr`;6.12 加了 `PREEMPT_SHORT`:slice 更短的可以抢 | fair.c `check_preempt_wakeup_fair` | §3.4 |
| rt 类 | 100 级位图 + 每级 FIFO,`pick_next_task_rt` 找最低置位;`sched_rt_runtime_us = 950000` 兜底由 `sched_rt_period_timer` 执行 | kernel/sched/rt.c | §4.3 |
| dl 类 | EDF + CBS:`pick_next_task_dl` 取红黑树最左(deadline 最早);`dl_server` 在 6.12 还被用来给 fair 任务兜底 | kernel/sched/deadline.c | §2.6 |
| 延迟出队 | 6.12 新特性 `DELAY_DEQUEUE`:睡的任务 lag 为负时不立刻出队,先留在树里把欠账跑平,避免「睡一下就洗白」 | fair.c `dequeue_entity` / `sched_delayed` | §2.4 补 |

---

## §6 约束回扣

| 机制(源码) | 对应约束 | 精确化解方式 | 付出的代价 |
|---|---|---|---|
| `__switch_to_asm` 换 rsp + 6 个 callee-saved(entry_64.S:177) | C1·CPU快IO慢、C2·程序不让台 | 任意深度冻结 / 解冻;借 ABI 省掉一半保存工作 | 每任务一根 16 KB 内核栈 |
| `update_deadline` + `resched_curr`(fair.c:1007 / core.c:1079) | C2、C4·调度不免费 | tick 只置标志,出口检查点才换人;base_slice 0.75 ms | 最坏 1 个 tick 的响应延迟 |
| `pick_eevdf`(fair.c:907) | C3·凭账不凭嘴、C6·有人等不起 | eligible 保份额,deadline 保时限,一棵树两问 | O(log n) + 子树 min_vruntime 维护 |
| `rq_lock` 每核一把(core.c:6592) | C5·核间不通气 | 选人只锁自己的队 | 需要另一条对账机制(负载均衡) |
| `for_each_sched_entity` 上行 + `pick_task_fair` 下行(fair.c:306 / 8848) | C7·同机多租户、C3 | 同一 Δt 每层各记一次,权重按 cpu.weight 与 CPU 占比折算 | tick / enqueue / pick 成本 × 层数 |
| `cfs_bandwidth` 池 + 5 ms 片 + throttle(fair.c:5812 / 5915) | C7、C5 | 组级硬上限;整组实体出队而非逐任务 | 全局池一把锁;被 throttle 的组内任务延迟最长一个 period |
| 链接脚本定序 + `scx_enabled()` static key(vmlinux.lds.h:131 / ext.c:862) | C8·一算法不配万场景、C4 | 可换一节;没装时零成本 | 装了之后所有换人走类链慢路径 |
| `balance_one` 三道闸 + `SCX_CALL_OP`(ext.c:2629 / 1084) | C8、C4 | 本地 DSQ 有人不跨界;一次函数指针调用 | 跨界时几十到几百 ns(待核 #23) |
| 两层看门狗 + `scx_ops_disable_workfn`(ext.c:3313 / 3356 / 4445) | C8 后半句 | bypass 保前进 → 逐任务改回 fair → 关 static key | 默认 30 s 内可能有任务饿着;bypass 期间不公平 |

两个观察:

1. **三条主线各自只碰一张表**:主线一只读 `thread.sp`,主线二只读 `se`,主线三只读 `scx`。task_struct 里三本账并列,这是回退能成立的结构性原因。
2. **C4 出现在每一行的「代价」列里**。调度器的每一处设计都在和自己的开销讨价还价;6.12 里最新的两样东西(EEVDF 的 `RUN_TO_PARITY`、sched_ext 的本地 DSQ)都是为了少换人、少跨界。

---

## §7 呼应灵魂问题

灵魂问题的前半截「调度器替系统做什么、怎么做」,What 立了三问,How 给了机制,Origin 给了来路,这一节把「怎么做」钉到了行号:换人是 `__switch_to_asm` 的一条 movq,到点是 `update_deadline` 的一次比较,选人是 `pick_eevdf` 的一次树下行。**前半截闭环到 95%**,剩下的 5% 是负载均衡的细节(§5 只给了入口),留给有兴趣的读者。

后半截「cgroup 和 sched_ext 增强了什么、为什么需要」,Origin 留下的 15% 在这一节全部钉死:

| Origin 留下的 | 本节答案 |
|---|---|
| sched_ext 的回调怎么挂进 pick_next_task | 不是挂进去,是**排在后面**:链接脚本把 ext 放在 fair 之后;`__pick_next_task` 因 `scx_enabled()` 放弃快路径走类链;到 ext 那一节 `balance_one` 三道闸都空了才 `SCX_CALL_OP(dispatch)`(§4.3) |
| 看门狗怎么踢人回 fair | `runnable_at` 超时 → `SCX_EXIT_ERROR_STALL` → `scx_ops_disable_workfn`:bypass → 逐任务 `p->sched_class = fair` 并重新入队 → 关 static key;tick 反盯看门狗本身(§4.4) |
| cgroup 子树的 vruntime 怎么跨层折算 | 不折算 vruntime,折算 **Δt**:`for_each_sched_entity` 每层调 `update_curr`,用该层实体的权重(任务用 nice,组用 `calc_group_shares`)把同一段 Δt 折成该层的 vruntime 增量(§3.3.2) |

**后半截在源码层面钉到了 100%,但在「读者消化」层面只到垫脚**:2026-11-11 你明确表示对 cgroup 和 sched_ext 两块都不熟,决定这两条线在本次只保留 §3.0 / §4.0 的零基础垫脚 + 源码结论,不再往下追问,**以后各自单独开一轮 atlas**(cgroup CPU 控制器一轮,sched_ext 一轮)。本次剩余的对话精力回到换人主线(§2)。

还有一件事没做:横向对照。Windows NT 的调度器是另一套血统(多级反馈队列 + 优先级提升),FreeBSD 的 ULE 是第三套;它们怎么回答三问、有没有 cgroup 和 sched_ext 的等价物,是下一步可以选的方向。

---

## 待核清单(导出前统一核实)

(2026-11-12 导出前已统一核实,逐条结果见综合长文末尾《收尾核实》。)

- #24 §2.4 纳秒时间线各段量级(现代 x86 服务器,PCID 开启):建议用 `src/05-sched-switch.bt` 实测一组数据替换
- #25 Linux 从 x86 硬件任务切换(TSS)改为软件切换的版本(2.2 还是 2.4)
- #26 `scx_qmap` 制造饥饿的命令行选项拼写(`-t COUNT` 每第 N 个用户任务 stall)及其 `timeout_ms` 默认值(5000?)
- #27 `SCX_SLICE_DFL` 默认值 20 ms —— 已核:include/linux/sched/ext.h:20 `SCX_SLICE_DFL = 20 * 1000000`
- #28 全部行号按 raw.githubusercontent.com tag v6.12 下载文件数出,导出前再对一次(本稿写完后已自查 9 处并修正)
- #29 §4.4.3「拆除线程自己也归 BPF 管」:`scx_ops_helper` kthread 在 `switch_all` 下是否也被切到 ext 类,待查 6.12 `scx_ops_enable` 对 kthread 的处理

(#1 ~ #23 见 Origin 文档。)

## 修订记录

| 时间 | 修订摘要 | 触发原因 |
|---|---|---|
| 2026-11-10 | 初稿:三条主线(换人全路径 + fork 分支 + 纳秒时间线 / cgroup 跨层 + 带宽 / sched_ext 挂载 + 看门狗回退),每条三层剖析 + 源码追踪 + 4 候选反事实;§2.5 用户视角「进程 = 栈 + 寄存器」;src/ 四个可运行 demo;两张 SVG;待核 #24~#28 | 对齐 Q1~Q3 + 追加 1(switch_to 本质)+ fork 接入 + reconfirm 后用户「没有了」 |
| 2026-11-10 | 新增 §4.4.3:反问「为什么先 bypass 不直接改类」→ 不是性能、稳定性沾边,主因是活性 + 锁序(睡眠锁可能被被晾任务持有 / static key 也要睡眠锁 / 拆除线程自己要被调度);O(CPU) vs O(任务) 的混合态论证;bypass 三处用法(装载 / 拆除 / 挂起)= 安全模式;§0 第三件加交叉引用;待核 #29 | 用户答「不清楚,是稳定性还是性能」(不懂反馈) |
| 2026-11-10 | 新增 §4.4.4:反问「装载时为什么也先 bypass」→ 用户态调度器(scx_userland / rustland):决策者是一个用户任务,装载第 ②~④ 步之间它还没开始跑,被切过去的任务无人派发;做切换的 current 自己也被切到 ext 后「等自己」;与拆除同构 = 执行切换的人自己也是被切换对象;三处 bypass 归一为「决策者可能排不上就让内核兜底」 | 用户答「不清楚」(不懂反馈) |
| 2026-11-11 | 新增 §3.0 / §4.0 两块零基础垫脚:cgroup = /sys/fs/cgroup 目录树 + 两个旋钮 + 调度器眼里的「树套树」,css_set 是会员名册本阶段不碰;sched_ext = fair 之后的一个调度类 + 三个回调由 BPF 程序填 + 用户态程序装载 + 看门狗兜底,eBPF = 带验证器的内核小虚拟机,DSQ / slice 词义,餐厅叫号类比 | 用户反馈「我对 sched_ext 与 cgroup cset 都不熟悉」(不懂反馈,背景缺口) |
| 2026-11-11 | §7 记录用户决定:cgroup / sched_ext 两条线本次止于垫脚 + 源码结论,以后各自单独开 atlas;对话回到换人主线 | 用户选 3「回到换人主线」并说「cgroup sched_ext 以后单独开 atlas」 |
| 2026-11-11 | 新增 §2.5.1:反问「另外 10 个通用寄存器去哪了」→ 用户答「CPU 来保存恢复」;纠大半(System V ABI caller-saved 由编译器在 call 之前 spill 进 prev 栈,callee-saved 6 个才需汇编手工存)、认一小角(中断入口 CPU 自动压 5 个字;syscall 只存 rcx/r11;pt_regs 大头软件压);补 FPU XSAVES 一层;寄存器四层去处小结;加强「进程 ≈ 栈 + 7 个寄存器零头」 | 用户答「这些由 cpu 来保存恢复」(反问回答) |
| 2026-11-11 | 新增 §2.6.1:反问「子进程 pt_regs 哪来的、rax 为什么 0」→ 用户答「fork 时强行给成 0」;认一半(ax 一行赋值,父子两份 pt_regs 写不同数)补一半(整份抄 current_pt_regs:ip 相同 → 醒在 syscall 下一条;sp 只在 clone 给栈时才换;父子 sp 数值相同靠 CR3 不踩)| 用户答「编译器存的。在 fork 的时候强行给成了 0」(反问回答) |
| 2026-11-11 | 新增 §2.6.2:反问「父子用户 rsp 相同为什么不踩」→ 用户答「因为 COW」;认大半垫一层(根因是 dup_mm 给了独立页表,COW 是便宜建法:fork 时父子 PTE 都去写位 → 子首次写 do_wp_page 复制 → 父再写 reuse 不复制);fork / 线程 / vfork 判别表(栈位置与页表至少一样不同,vfork 两样都同所以父进程睡);补全「线程 = 换栈不换页表」 | 用户答「因为 COW」(反问回答) |
| 2026-11-11 | 新增 §2.5.2:反问「A 醒来怎么知道是 C」→ 用户答「switch_to 会把栈上的 prev 改成 C」;认(结果正确),补「谁改的、值怎么来」:C 侧不碰 A 的栈,__switch_to 返回 prev_p 在 rax,换栈后 A 自己执行 last = rax;五步时刻表;寄存器是跨栈唯一信使;为什么收尾只能由接班者做(on_cpu / rq 锁必须在离开 prev 栈之后);fork 分支 movq %rax,%rdi 同一信使 | 用户答「switch_to 会修改这个 prev 的栈上的值到 C」(反问回答) |
| 2026-11-11 | 新增 §2.3.1.1:反问「为什么不在中断里当场 schedule」→ 用户答「中断要尽快结束,标签后处理」;认一小半纠大半:schedule 就在同一次中断返回路上,不是延后而是挪位置;换人 = 冻栈 → 三样冻不得(rq 锁与硬中断计数 / 每 CPU 中断栈 / 被打断代码持锁);三个出口检查点;TIF_NEED_RESCHED 按「因为→要解决→所以」重引;原 §2.3.1 末句「要拿 rq 锁、要能睡」改写 | 用户答「中断处理函数要求尽快结束,所以采用标签后处理方式」(反问回答) |
| 2026-11-12 | 导出前核实,更正 §4.4.3 第 ③ 条:拆除线程 `sched_ext_ops_helper` 是 `SCHED_FIFO` 的实时类内核线程(ext.c:4948 ~ 4956),不归 BPF 管;原稿「`switch_all` 时它自己也归 BPF 管」有误。它需要 bypass 的原因并入第 ① 条(等的锁被排不上核的 ext 任务拿着)。待核 #26(`scx_qmap -t COUNT`、`timeout_ms = 5000`)已核,#29 已核并更正 | 导出前统一核实 |
| 2026-11-12 | 图 `pics/05-context-switch.svg` 左栏标题里的「待核 #24」改为「量级,未实测」,与收尾核实的结论一致 | 导出 HTML 时发现 |
