/*
 * 03-pick.pseudo.c —— 一次 tick → 记账 → 挑人 → (也许)换人 的伪代码骨架
 *
 * 这不是能编译的 C。每行右侧标注它服务的「件」(§0 三件事)和约束 Cn(02-why.md):
 *   件① 每核一本账 rq + 类栈      件② sched_entity 的账 + 增广树      件③ 标记 + 搬人
 *   C1 只在打断点换  C2 未来不可知  C3 份额与延迟两头要  C4 挑人须便宜
 *   C5 核各自为政    C6 份额按组算  C7 有人要硬保证      C8 核不等速且耗电
 * 真实函数名(Linux 6.12 kernel/sched/)写在注释里,行号级走读见 Deep。
 */

/* ---------- 打断点 1:tick(core.c sched_tick → fair.c task_tick_fair → update_curr) ---------- */
void sched_tick(struct rq *rq)
{
    rq->clock_task = read_tsc() - irq_time;                     /* 件① C4:增量记账,扣掉中断时间   */
    struct se *se = &rq->curr->se;
    u64 delta = rq->clock_task - se->exec_start;                 /* 真实 ns                        */
    se->exec_start = rq->clock_task;
    se->vruntime += delta * 1024 / se->weight;                   /* 件② C3:权重折算 (calc_delta_fair) */
    if (se->vruntime >= se->deadline) {                          /* slice 用完了?(update_deadline)  */
        se->deadline = se->vruntime + se->slice * 1024 / se->weight;
        set_need_resched(rq->curr);                              /* 件③ C1:只打标记,不换人       */
    }
    account_cfs_rq_runtime(cfs_rq_of(se), delta);                /* §6 C6:组的带宽小账扣钱,可能 throttle */
    pelt_update(se);                                             /* §5.2 C8:util/runnable/load 衰减平均 */
    update_cfs_group(se->parent);                                /* §3.7 C6:组实体在本核的权重重算  */
    if (time_after(jiffies, rq->next_balance))
        raise_softirq(SCHED_SOFTIRQ);                            /* 件③ C5:到点了去看邻居          */
}

/* ---------- 打断点 2:唤醒(core.c try_to_wake_up → fair.c enqueue_task_fair / place_entity) ---------- */
void wake_up(struct task *p)
{
    int cpu = select_task_rq_fair(p);                            /* 件③ C5:原核空?同 L3 空核?否则目标核 */
    struct cfs_rq *cfs = &cpu_rq(cpu)->cfs;
    u64 V   = avg_vruntime(cfs);                                 /* 件② C4:min_vruntime + avg_vruntime/avg_load */
    s64 lag = p->se.vlag;                                        /* 睡下去时存的,已夹在 ±2·slice     */
    lag = lag * (cfs->avg_load + p->se.weight) / cfs->avg_load;  /* 件② C3:守恒放大 (place_entity)   */
    p->se.vruntime = V - lag;
    p->se.deadline = p->se.vruntime + p->se.slice * 1024 / p->se.weight;
    rb_insert_by_deadline(&cfs->tree, &p->se);                   /* 件② C4:O(log n) 插入           */
    avg_vruntime_add(cfs, &p->se);                               /* 件② C4:累加器 +=               */
    if (pick_eevdf(cfs) == &p->se)                               /* 件③:抢不抢 = 规则会不会挑它 (check_preempt_wakeup_fair) */
        set_need_resched(cpu_rq(cpu)->curr);                     /* 跨核则发 IPI                    */
}

/* ---------- 打断点 3:阻塞(fair.c dequeue_task_fair / update_entity_lag) ---------- */
void block(struct task *p)
{
    struct cfs_rq *cfs = cfs_rq_of(&p->se);
    s64 lag = avg_vruntime(cfs) - p->se.vruntime;                /* 件② C3:欠它多少                */
    s64 lim = max(2 * p->se.slice, TICK_NSEC) * 1024 / p->se.weight;
    p->se.vlag = clamp(lag, -lim, lim);                          /* 件② C3:插队额度有界 (entity_lag) */
    if (p->se.vlag < 0 && DELAY_DEQUEUE) { p->se.sched_delayed = 1; } /* 6.12:超支的先留树上还账   */
    else { rb_erase(&cfs->tree, &p->se); avg_vruntime_sub(cfs, &p->se); }
    schedule();                                                  /* 件③:自己就在打断点上,直接挑   */
}

/* ---------- 挑人(fair.c pick_eevdf) ---------- */
struct se *pick_eevdf(struct cfs_rq *cfs)
{
    struct se *curr = cfs->curr, *best = NULL;
    if (cfs->nr_running == 1) return curr ? curr : leftmost(cfs);/* 件② C4:单任务免判            */
    if (curr && !eligible(cfs, curr)) curr = NULL;               /* 件② C3:超支的 curr 当不存在    */
    if (curr && curr->vlag == curr->deadline) return curr;       /* RUN_TO_PARITY:slice 保护期     */
    for (node = cfs->tree.root; node; ) {                        /* 树按 deadline 排                */
        if (node->left && node->left->min_vruntime <= V(cfs)) { node = node->left; continue; } /* 件② C4:子树剪枝 */
        if (eligible(cfs, node)) { best = node; break; }         /* 第一个有资格者 = deadline 最早的有资格者 */
        node = node->right;
    }
    if (!best || (curr && curr->deadline < best->deadline)) best = curr;
    return best;                                                 /* 件② C2:全程没看任务是谁        */
}

/* ---------- 出口(kernel/entry/common.c exit_to_user_mode_loop;core.c __schedule) ---------- */
void exit_to_user_mode(void)
{
    while (need_resched()) schedule();                           /* 件③ C1:消费标记               */
}
void schedule(void)
{
    struct rq *rq = this_rq();
    struct task *prev = rq->curr, *next;
    if (all_tasks_are_fair(rq) && !class_above_fair(prev))       /* 件① C4:快路径,类栈不扫        */
        next = pick_next_task_fair(rq);                          /* → pick_eevdf,组节点则下钻      */
    else
        for_each_class_from_high(cls) if ((next = cls->pick_task(rq))) break; /* 件① C7:stop>dl>rt>fair>ext>idle */
    if (next != prev) {
        put_prev_entity(&prev->se);                              /* 件②:回树                     */
        set_next_entity(&next->se);                              /* 件②:出树,vlag = deadline 做保护标记 */
        rq->curr = next;
        context_switch(prev, next);                              /* 上一轮 Deep §3.3:2 ~ 3 μs      */
    }
}

/* ---------- 搬人(fair.c sched_balance_rq,softirq 或 newidle 触发) ---------- */
void sched_balance_rq(struct rq *this_rq, struct sched_domain *sd)
{
    struct sched_group *busiest = find_src_group(sd);            /* 件③ C5 C8:按 load/capacity 比  */
    if (!busiest || busiest_load < local_load * sd->imbalance_pct / 100) return; /* 17% 迟滞 */
    long imbalance = calculate_imbalance(sd) >> 1;               /* 只搬一半,防抖                  */
    struct rq *src = find_src_rq(busiest);
    for_each_task_in_tree_from_tail(p, src) {
        if (p == src->curr) continue;                            /* 正在跑的不搬                    */
        if (!cpumask_test_cpu(this_cpu, p->cpus_ptr)) continue;  /* taskset / cpuset 不允许         */
        if (now - p->se.exec_start < 500000) continue;           /* task_hot:0.5 ms 内跑过 = 热    */
        move(p, src, this_rq); imbalance -= load_of(p);          /* 件②:节点换树                   */
        if (imbalance <= 0) break;
    }
}
