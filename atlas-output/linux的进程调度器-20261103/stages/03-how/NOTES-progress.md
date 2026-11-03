# 03-how 阶段审计(供合并进 PROGRESS.md「How 阶段」小节)

### How 阶段
- 对齐(自答,2026-11-03):机制级全链路,按四问走;弱项加厚 = §3 fair 账(lag 从零讲)、§5 多核(结构 / 原理 / 机制 / 策略四面)、§6 cgroup 带宽;先陈述(概念 + 对象表 / 图)后逼问,每节末汇总表;算例 §3.6 三任务五拍、§5.5 rq3 newidle、§6.3 钩子一;换人动作只引用上一轮 How §6 / Deep §3.3;源码钉 6.12,只写文件 + 函数名
- 三件事:① 每核一本账 `rq` + 类栈 `stop > dl > rt > fair > ext > idle`(C5 + C7,`cpu_capacity` 挂 C8)② `sched_entity` 四个数 + 按 deadline 排的增广红黑树,线程与组同形(C2 + C3 + C4 + C6)③ `TIF_NEED_RESCHED` 标记 + 两种出口 + 三种搬人(C1 + C5)
- 2026-11-03 初稿写入 stages/03-how/03-how.md(810 行)+ pics/03-overview.svg、03-ledger.svg、03-domains.svg、03-cgroup.svg(xmllint 通过)+ src/03-pick.pseudo.c(伪代码)+ src/README.md
- 6.12 函数名已 grep 核对:`sched_balance_rq` / `sched_balance_find_src_group` / `sched_balance_find_src_rq` / `sched_balance_find_dst_cpu` / `sched_balance_newidle` / `sched_balance_domains` / `sched_balance_trigger` / `select_task_rq_fair` / `wake_affine` / `select_idle_sibling` / `select_idle_cpu` / `place_entity` / `update_entity_lag` / `entity_lag` / `entity_eligible` / `vruntime_eligible` / `pick_eevdf` / `avg_vruntime` / `update_deadline` / `update_curr` / `check_preempt_wakeup_fair` / `wakeup_preempt` / `throttle_cfs_rq` / `distribute_cfs_runtime` / `__assign_cfs_rq_runtime` / `sched_cfs_period_timer` / `calc_group_shares` / `update_cfs_group` / `task_hot` / `default_topology` / `sd_init` / `__pick_next_task` 快路径 / `exit_to_user_mode_loop` / `preempt_schedule_irq` / `resched_curr` / `sched_tick` / `do_preempt_short` / `did_preempt_short` / `dequeue_entity` 的 `DELAY_DEQUEUE` 分支
- 数字出处(6.12 源码已见):`sched_prio_to_weight[]` 表;`sysctl_sched_base_slice` 750000 × (1 + ilog2(min(cpus, 8)));`sysctl_sched_migration_cost` 500000;自定义 slice clamp 0.1 ~ 100 ms;`sysctl_sched_cfs_bandwidth_slice` 5000 μs;`default_cfs_period` 100 ms;period 1 ms ~ 1 s;`min_cfs_rq_runtime` 1 ms;`sysctl_sched_rt_runtime` 950000 / `period` 1000000;`RR_TIMESLICE` 100 ms;`imbalance_pct` 117(LLC)/ 110(SMT);`busy_factor` 16;`max_load_balance_interval` HZ/10;`cache_nice_tries` 1 / 2;`sched_weight_from_cgroup` 100 ↔ 1024;类顺序 `stop > dl > rt > fair > ext > idle`(vmlinux.lds.h);`features.h`:PLACE_LAG / PLACE_DEADLINE_INITIAL / RUN_TO_PARITY / PREEMPT_SHORT / DELAY_DEQUEUE / DELAY_ZERO / SIS_UTIL / WA_IDLE / WA_WEIGHT / WA_BIAS / HRTICK(false)
- 反问(选择式,§14):redis lag +4 虚拟 ms 醒来最多连跑多久 —— A 4 ms / B 3 ms / C lag 归零 ~37 ms / D 前提不成立;自答:D 的前提修正(lag 夹在 ±0.643)+ C 的机制(跑到 lag 归零 ~64 ms,因 V 跟着它走);每 4 ms 经历一次标记 → 重挑 → 还是它
- 待核:#12 ~ #26(见 03-how.md 末尾),其中纯机制级待上机验证的是 #19(唤醒到首指令 7 ~ 10 μs 分项)、#26(§3.6 算例数字)

## Deep handoff(Deep 应引用的 How 小节)
- §3.2 V 的两个累加器 → Deep 主线① 贴 `avg_vruntime_add/sub/update` + `avg_vruntime()` 的左偏处理
- §3.3 `update_deadline` 只推一次 → Deep 主线① 贴 `update_curr` 全文 + `update_deadline`;HRTICK 关导致 4 ms 粒度的证据
- §3.4 lag 夹紧(`entity_lag`:±max(2·slice, TICK_NSEC))与守恒放大(`place_entity` 的 vl_i = (W + w)·vl'_i / W)→ Deep 主线① 逐行;`DELAY_DEQUEUE` / `DELAY_ZERO` 的 `dequeue_entity` 分支与 `requeue_delayed_entity`
- §3.5 `pick_eevdf` 六步 + `RUN_TO_PARITY`(`set_next_entity` 的 vlag = deadline 标记)+ `PREEMPT_SHORT`(`do_preempt_short` / `did_preempt_short`)→ Deep 主线① 贴源码 + 反事实 A1 ~ A6(RR / CFS / 彩票 / stride / BVT / sched_ext 自定义)
- §3.6 五拍算例 → Deep 主线① 的 ns 时间线以第 8 ms(tick 换人)和第 10 ms(唤醒抢占)两行为骨架,逐项钉 ns
- §3.7 `calc_group_shares` 的公式 (3)(5)(6)→ Deep 主线③ 贴注释里的推导 + `reweight_entity`
- §4.1 三种标记来源 / §4.2 两种出口与抢占模型 → Deep 主线① 时间线中 `exit_to_user_mode_loop` 与 `preempt_schedule_irq` 的位置;附录讲 `PREEMPT_DYNAMIC` 的 static call 与 `PREEMPT_LAZY`(6.13,待核 #16)
- §4.4 唤醒抢占六步 → Deep 主线① 贴 `check_preempt_wakeup_fair` 全文
- §5.1 调度域两层 / `imbalance_pct` / `balance_interval` → Deep 主线② 贴 `sd_init` + `default_topology[]`,给真机 `/sys/kernel/debug/sched/domains/` 的样子
- §5.2 PELT 三个量 → Deep 主线② 贴 `pelt.c` 的 `___update_load_sum` / `decay_load`,`y^32 = 0.5`,段 1024 μs(待核 #13)
- §5.3 三种搬人 → Deep 主线② 贴 `select_task_rq_fair` → `wake_affine_idle/weight` → `select_idle_sibling` → `select_idle_cpu`(SIS_UTIL 上限,待核 #25);`sched_balance_rq` → `sched_balance_find_src_group`(`group_type` 分类表)→ `calculate_imbalance`(四种 `migration_type`)→ `detach_tasks`(`task_hot`);`sched_balance_newidle` 的 `avg_idle` 判定
- §5.5 算例 → Deep 主线② 用 `sg_lb_stats` 字段把 rq3 newidle 这一例算到数(load_avg / util_avg / idle_cpus)
- §5.6 taskset 两面 → Deep 主线② 反事实 B(全局队列 / 无 task_hot / 每次醒来放最闲 / push 模型 / 不分层)
- §6.2 借 / 停 / 放 → Deep 主线③ 贴 `__assign_cfs_rq_runtime` / `throttle_cfs_rq` / `distribute_cfs_runtime` / `sched_cfs_period_timer`(含 period 自动翻倍的 warn)/ `return_cfs_rq_runtime` + slack timer
- §6.3 钩子一与"改 4 核"三选项 → Deep 主线③ 把 `cpu.stat` 的 `nr_throttled / throttled_usec` 对到时间线;反事实 C(按核数限 / 无周期 / 只停超额线程 / 无 burst)
- §7 `fair_server`(6.12 `dl_server_update`)→ Deep 附录;待核 #18
- §8.2 7 ~ 10 μs 唤醒链 → Deep 主线① 唯一的 ns 时间线(待核 #19)
- §11 三误解 → Synthesis 洞察清单候选
