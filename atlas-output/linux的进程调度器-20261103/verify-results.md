## ✅ 收尾核实(导出前统一核实)

七份草稿累计 78 条待核(What #1 ~ #5、Why #6 ~ #11、How #12 ~ #26、Origin #40 ~ #50、Deep #70 ~ #90、Comparison #100 ~ #109、Synthesis #120 ~ #129),2026-11-03 导出前统一核实:**已核 52 条(含 1 条"已核(并存)")、改写 2 条、部分核实 15 条、随前述结论 2 条、无法核实 / 无法上机核实 5 条、示例值与场景假设 2 条**(已核 52 / 改写 2 / 部分核实 15 / 随前述结论 2 / 无法核实 2 / 无法上机核实 3 / 示例值 1 / 场景假设 1)。
内核事实优先用 Linux v6.12 源码(以及 v2.6.18 / v5.13 / v5.14 / v6.7 ~ v6.11 / v6.13 同路径文件)逐行核对;历史事实用 LKML 镜像与 GitHub 提交页;Windows 事实用微软文档与 Windows Internals 授权课件;纯量级估计(时间线 ns、tick 开销、L2 miss)不能在用户的 macOS 上核实,只核对了公开实测的量级。
改写的正文只有两处事实性错误(How §0.3:`sched_balance_*` 改名在 6.10 不是 6.12;Synthesis #121:Percona `thread_pool_stall_limit` 默认 500 ms,原稿把企业版的 6 × 10 ms 误记为另一构建);其余改动是去掉"待核"标记、补入已核的出处与公式(Origin §12 新增一手 48 ~ 52 条;Deep §4.1 补 k8s 换算公式;Deep §2.5 A6 的现实用户改为 Meta 与 Steam Deck)。

| # | 所在篇 | 原文断言 | 结论 | 核实后事实 | 出处 |
|---|---|---|---|---|---|
| 1 | What | `sysctl_sched_migration_cost` 默认 500000 ns | 已核 | `const_debug unsigned int sysctl_sched_migration_cost = 500000UL` | kernel/sched/fair.c:79(v6.12) |
| 2 | What | SMT 两线程同忙时每线程约 60 ~ 70% 吞吐 | 部分核实 | Intel 自述 HT 最多提升约 30%(即两线程同忙每线程 ≈ 65%),平均 10 ~ 20%;量级成立,具体值随负载变 | The Register 2002-06-18 https://www.theregister.com/2002/06/18/what_the_hell_is_hyperthreading/ ;Beamr 实测 https://blog.beamr.com/?p=530(均二手) |
| 3 | What | 跨 NUMA 访存慢 1.5 ~ 2 倍 | 部分核实 | 实测 NUMA 因子 1.5(Westmere 90 / 140 ns)~ 1.7(Xeon E5-2650 MLC 69 / 118 ns;Ice Lake 91 / 157 ns);原文区间成立,上界 2 偏宽 | CERN openlab 讲义 https://openlab-archive-iv-v.web.cern.ch/… ;Intel 社区 MLC 输出 https://community.intel.com/t5/Mobile-and-Desktop-Processors/Interpreting-Intel-Memory-Latency-Checker-Output/m-p/434769 ;LKML 2014 SLIT 讨论 https://lkml.rescloud.iu.edu/1409.2/00354.html |
| 4 | What | 一次 L2 miss 约 10 ns | 部分核实 | Skylake:L2 12 周期、L3 42 周期(4.0 GHz 下 ≈ 3 / 10.5 ns);"L2 miss" 即 L3 命中量级 ≈ 10 ns,成立 | https://www.7-cpu.com/cpu/Skylake.html |
| 5 | What | 一次 tick 处理约 1 μs | 无法上机核实 | 量级估计,保留;可用 `perf stat -e irq:*` / ftrace 在真机核 | — |
| 6 | Why | 2.4 的 goodness 扫描 3000 线程约 30 μs | 无法上机核实 | 2.4 为 O(n) 扫描 + 全局 `runqueue_lock` 的事实已核(Origin §2 引 2.4.31 `sched.c`);"30 μs" 是按每任务 10 ns 的估算 | Origin §12 第 4 条(2.4.31 sched.c) |
| 7 | Why | O(1) 的 sleep_avg 奖励最多 +5 级 | 已核 | `MAX_BONUS = MAX_USER_PRIO × 25 / 100 = 10`,`bonus = CURRENT_BONUS(p) − MAX_BONUS / 2` ∈ [−5, +5] | kernel/sched.c:96 ~ :97、:717(v2.6.18)https://raw.githubusercontent.com/torvalds/linux/v2.6.18/kernel/sched.c |
| 8 | Why | 1997 年火星探路者因优先级反转重启 | 已核 | Mike Jones 1997-12-07 "What really happened on Mars":1997-07-04 着陆后 vxWorks 总线管理任务等待气象任务持有的互斥量,被中优先级通信任务饿死,看门狗复位;修复为打开互斥量的优先级继承 | http://www.cs.cornell.edu/courses/cs614/1999sp/papers/pathfinder.html |
| 9 | Why | `sched_rt_runtime_us` 默认 950000(周期 1000000) | 已核 | `sysctl_sched_rt_period = 1000000`、`sysctl_sched_rt_runtime = 950000` | kernel/sched/rt.c:15、:21(v6.12) |
| 10 | Why | PELT 半衰期 32 ms | 已核 | `LOAD_AVG_PERIOD 32`、`LOAD_AVG_MAX 47742`;段长 1024 μs | kernel/sched/sched-pelt.h:13 ~ :14(v6.12) |
| 11 | Why | turbo 3.8 GHz vs 全核 3.0 GHz | 示例值 | 正文已注明为示意,不对应具体型号;无需核实 | — |
| 12 | How | `load_balance` 等改名为 `sched_balance_*` 的版本(原稿写 6.12) | 改写 | 改名在 **6.10**:v6.9 `fair.c` 仍是 `load_balance` / `find_busiest_group` / `newidle_balance`,v6.10 已是 `sched_balance_rq` / `sched_balance_find_src_group` / `sched_balance_newidle`;How §0.3 "6.12 把老名字改成了它" 改为 6.10 | https://raw.githubusercontent.com/torvalds/linux/v6.9/kernel/sched/fair.c 与 v6.10 同路径(grep) |
| 13 | How | PELT 常数所在头文件 | 已核 | 同 #10;Deep #83 | kernel/sched/sched-pelt.h:13 ~ :14 |
| 14 | How | NUMA 层 `imbalance_pct` | 已核 | `sd_init` 不单独设 NUMA 层 → 默认 117;Deep #81 | kernel/sched/topology.c `sd_init`(v6.12) |
| 15 | How | 自定义 slice 范围 0.1 ~ 100 ms | 已核 | `clamp_t(u64, attr->sched_runtime, NSEC_PER_MSEC/10, NSEC_PER_MSEC*100)` | kernel/sched/syscalls.c:307(v6.12) |
| 16 | How | `PREEMPT_LAZY` 进入主线版本 6.13 | 已核 | v6.12 `kernel/Kconfig.preempt` 无;v6.13 新增 `config ARCH_HAS_PREEMPT_LAZY`(:14)与 `config PREEMPT_LAZY`(:75) | https://raw.githubusercontent.com/torvalds/linux/v6.13/kernel/Kconfig.preempt |
| 17 | How | `NO_HZ_FULL` 下记账方式 | 已核 | `NO_HZ_FULL` 强制 `select VIRT_CPU_ACCOUNTING_GEN`;记账在用户态 / 内核态边界由 `vtime_user_enter` / `vtime_account_kernel` 补 | kernel/time/Kconfig:123 ~ :135;kernel/sched/cputime.c:705、:717(v6.12) |
| 18 | How | `fair_server` 进入版本与默认值;是否替代 95% 阀 | 已核(并存) | dl_server 基础设施 6.8(v6.8 `deadline.c` 有 `dl_server_start`,v6.7 无);fair 类作 dl 实体(`fair_server`)6.12 新(v6.11 `fair.c` 无);默认 runtime 50 ms / period 1000 ms;与 `sched_rt_runtime_us` 并存(How §7 已改) | kernel/sched/deadline.c:1637(v6.12);v6.7 / v6.8 / v6.11 同路径 grep |
| 19 | How | 网卡中断到被唤醒任务第一条指令 7 ~ 10 μs | 部分核实 | Deep §2.3 分项合计 6.5 ~ 7.5 μs,区间下限成立;仍为估计,未上机 | Deep §2.3;上一轮 Deep §3.3(2 ~ 3 μs 换人) |
| 20 | How | 带宽 slice 5 ms、`min_cfs_rq_runtime` 1 ms、period 1 ms ~ 1 s;`cpu.max.burst` 进 5.14 | 已核 | 前三项 v6.12 源码;v5.13 `sched.h` 无 `burst`,v5.14 `sched.h:369` 新增 `u64 burst;`(struct cfs_bandwidth) | kernel/sched/fair.c:124;https://raw.githubusercontent.com/torvalds/linux/v5.14/kernel/sched/sched.h |
| 21 | How | dl 准入与 rt 比值共用 | 已核 | `__dl_overflow` 用 `dl_b->bw`,来自同一 `sched_rt_runtime / period`;Deep #84 | kernel/sched/deadline.c(v6.12) |
| 22 | How | `/proc/<pid>/sched` 字段名 | 已核 | `nr_switches` / `nr_voluntary_switches` / `nr_involuntary_switches`(= nvcsw / nivcsw)、`se.vruntime`、`se.sum_exec_runtime`、`se.nr_migrations`;debug 文件的 `avg_vruntime` 列 | kernel/sched/debug.c:1179 ~ :1184、:1240 ~ :1242、:839(v6.12) |
| 23 | How | `DELAY_DEQUEUE` / `DELAY_ZERO` 进入 6.12 | 已核 | v6.11 `features.h` 无 `DELAY_DEQUEUE` / `DELAY_ZERO` / `PREEMPT_SHORT` / `PLACE_REL_DEADLINE`,均为 6.12 新 | https://raw.githubusercontent.com/torvalds/linux/v6.11/kernel/sched/features.h |
| 24 | How | `cpu.weight` 100 ↔ 1024;k8s `requests.cpu` → `cpu.weight` 公式 | 已核 | kubelet:shares = milliCPU × 1024 / 1000(最小 2,最大 262144);v2 weight = 1 + (shares − 2) × 9999 / 262142(与 OCI cgroups `ConvertCPUSharesToCgroupV2Value` 同式);requests 2 核 → 2048 shares → weight 79 | kubernetes pkg/kubelet/cm/helpers_linux.go:133 ~ :147;pkg/kubelet/cm/cgroup_manager_linux.go:283 ~ :287;opencontainers/cgroups utils.go:425 |
| 25 | How | `SIS_UTIL` 扫描上限公式;`wake_wide` 的 `sd_llc_size` 因子 | 已核 | `wake_wide`:factor = `sd_llc_size`,`slave < factor || master < slave × factor` 则不 wide;`update_idle_cpu_scan`:nr_scan = llc_weight × (1 − (x′ × pct)² / (10000 × 1024)),x′ = sum_util / llc_weight,利用率到 85%(= 100 / 117)停扫 | kernel/sched/fair.c:7331 ~ :7342、:10903 ~ :10972(v6.12) |
| 26 | How | §3.6 算例数字 | 已核 | Deep 模拟器复现到 0.01 ms(Deep #82) | stages/05-deep/src/05-eevdf-sim.py |
| 40 | Origin | Con Kolivas 的 staircase 首发年份 2004 | 已核 | 首帖 "[PATCH]Staircase scheduler - experimental",2004-03-24,对 2.6.4 / 2.6.5-rc2-mm2;LWN 2004-06-02 报道为后续版本 | https://lkml.iu.edu/hypermail/linux/kernel/0403.3/0205.html ;https://lwn.net/Articles/87729/ |
| 41 | Origin | Ingo 2002 O(1) 首帖日期 | 已核 | "[announce] [patch] ultra-scalable O(1) SMP and UP scheduler",2002-01-03 21:19 EST(欧洲时间 1 月 4 日),对 2.5.2-pre6 并附 2.4.17 版 | https://lkml.iu.edu/hypermail/linux/kernel/0201.0/0810.html |
| 42 | Origin | CFS 进 2.6.23 的合并提交 | 已核 | `bf0f6f24a1ec` "sched: cfs core, kernel/sched_fair.c",作者 Ingo Molnar,2007-07-09;进入 2.6.23-rc1 合并窗口 | https://github.com/torvalds/linux/commit/bf0f6f24a1ece8988b243aefe84ee613099a9245 |
| 43 | Origin | Peter 2008-03 fair-group EEVDF RFC 内容是否与 2023 同源 | 已核 | 正文已读:"s1) we use the EDF result if its eligible to run (has >= 0 lag)",否则回退最小 vruntime;双树(timeline + deadline)、`vperiod`、用 `avg_vruntime()` 判资格;与 2023 同源(资格 + 虚拟截止期),实现不同(2023 改单树增广) | https://lkml.iu.edu/hypermail/linux/kernel/0803.1/0278.html(2008-03-09) |
| 44 | Origin | `cpu.max.burst` 合入 5.14 | 已核 | 同 How #20 | https://raw.githubusercontent.com/torvalds/linux/v5.14/kernel/sched/sched.h |
| 45 | Origin | `PREEMPT_LAZY` 合入 6.13 | 已核 | 同 How #16 | https://raw.githubusercontent.com/torvalds/linux/v6.13/kernel/Kconfig.preempt |
| 46 | Origin | sched_ext 合并提交日期 | 已核 | `88264981f208` "Merge tag 'sched_ext-for-6.12'",Linus Torvalds,2024-09-21 16:44:57 UTC | https://github.com/torvalds/linux/commit/88264981f2082248e892a706b2c5004650faac54(GitHub API) |
| 47 | Origin | 4.3BSD `kern_synch.c` 头 "6/5/86" 对应 4.3BSD 发布 | 部分核实 | 4.3BSD 发布于 1986 年 6 月,与文件头日期吻合;版本号 7.1 的对应关系未独立核 | https://en.wikipedia.org/wiki/Berkeley_Software_Distribution |
| 48 | Origin | EEVDF 技术报告 1995 原发 / 1996-01-26 修订 | 部分核实 | PDF 首页:TR-95-22,作者 Stoica、Abdel-Wahab(ODU),末注 "Revised January 26, 1996";1995 由报告号推定,首页无原发日期 | https://people.eecs.berkeley.edu/~istoica/papers/eevdf-tr-95.pdf |
| 49 | Origin | Linus "ignoring reality" 一句的出处 | 已核 | Linus 本人邮件 "Re: Linus 2.6.23-rc1",2007-07-27 22:36 EST:"People who think SD was 'perfect' were simply ignoring reality. Sadly, that seemed to include Con too…";Kasper Sandberg 2007-07-28 回复(2071.html)亦引用 | https://lkml.iu.edu/hypermail/linux/kernel/0707.3/2012.html |
| 50 | Origin | §13:APC "Why I quit" 采访原文 | 部分核实 | 原页不可达;LWN 2007-07-24 与 OSNews 2007-07-24 转载片段可核:"If there is any one big problem with kernel development and Linux it is the complete disconnection of the development process from normal users"、"There were so many subsystems being repeatedly rewritten that there was never-ending breakage" | https://lwn.net/Articles/242764/ ;https://www.osnews.com/story/18321/ |
| 70 | Deep | §2.3 时间线各行 ns 量级 | 无法上机核实 | 估计;换人段取上一轮实测 2 ~ 3 μs | — |
| 71 | Deep | How #19 的 7 ~ 10 μs | 部分核实 | 同 How #19 | Deep §2.3 |
| 72 | Deep | How §14 分岔三 | 已核 | 两实体时 Σ w·lag = 0,mysqld 无资格;How §14 已改 | 05-eevdf-sim.py 场景 deep26 |
| 73 | Deep | How §5.5 两处 | 已核 | MC 层 newidle 可抢占内核只搬 1(`fair.c:9607`);PKG 层 `migrate_util` = 1024;How §5.5 已改 | kernel/sched/fair.c:9607、:11048(v6.12) |
| 74 | Deep | How §7 `fair_server` 接替 95% 阀 | 已核(并存) | 同 How #18;How §7 已改 | kernel/sched/deadline.c:1637 |
| 75 | Deep | `PREEMPT_LAZY` 版本 | 已核 | 6.13;同 How #16 | v6.13 kernel/Kconfig.preempt:75 |
| 76 | Deep | k8s `requests.cpu` → `cpu.weight` 公式 | 已核 | 同 How #24;Deep §4.1 表已补公式 | kubelet cgroup_manager_linux.go:286 |
| 77 | Deep | `scx_bpf_dispatch` → `scx_bpf_dsq_insert` 改名版本 | 已核 | 6.13:v6.13 `ext.c` 用 `scx_bpf_dsq_insert`(21 处),`scx_bpf_dispatch` 仅作兼容别名出现;6.12 仍是 `scx_bpf_dispatch` | https://raw.githubusercontent.com/torvalds/linux/v6.13/kernel/sched/ext.c |
| 78 | Deep | `sysctl_sched_nr_migrate` 默认 32 | 已核 | `SCHED_NR_MIGRATE_BREAK` = 32(`CONFIG_PREEMPT_RT` 下 8) | kernel/sched/sched.h:2819 ~ :2823;kernel/sched/core.c:152(v6.12) |
| 79 | Deep | `max_lock_depth` 默认 1024 | 已核 | `int max_lock_depth = 1024;` | kernel/locking/rtmutex_api.c:14(v6.12) |
| 80 | Deep | `SIS_UTIL` 的 `nr_idle_scan` 公式 | 已核 | 同 How #25 | kernel/sched/fair.c:10903 ~ :10972 |
| 81 | Deep | NUMA 层 `imbalance_pct` 117 | 已核 | `sd_init` 不单独设 | kernel/sched/topology.c |
| 82 | Deep | §3.6 算例 | 已核 | 模拟器复现 | 05-eevdf-sim.py |
| 83 | Deep | PELT 常数 | 已核 | `sched-pelt.h:13 ~ :14` | kernel/sched/sched-pelt.h |
| 84 | Deep | dl 准入与 rt 比值共用 | 已核 | `__dl_overflow` 用 `dl_b->bw` | kernel/sched/deadline.c |
| 85 | Deep | §2.3 假设 LLC0 四核全忙 | 场景假设 | 非事实断言,保留 | — |
| 86 | Deep | sched_ext 的现实用户 | 部分核实 | Meta:生产部署(sched-ext/scx 仓库 README 自述 "Meta and Google are fully committed … mass production deployment");Valve Steam Deck:Igalia 的 `scx_lavd`(Phoronix 2024;Bazzite 社区称 Steam Deck 默认启用,非 Valve 官方声明);"手机厂"未核,已从正文去掉 | https://github.com/sched-ext/scx ;https://phoronix.com/news/LAVD-Scheduler-Linux-Gaming ;https://lpc.events/event/18/contributions/1713/attachments/1425/3058/scx_lavd-lpc-mc-24.pdf |
| 87 | Deep | `wake_affine_weight` 偏置 108.5 | 已核 | `100 + (imbalance_pct − 100) / 2` | kernel/sched/fair.c:7411 |
| 88 | Deep | `throttled_time` 按 cfs_rq 累加 | 已核 | `unthrottle_cfs_rq`:`cfs_b->throttled_time += rq_clock(rq) − cfs_rq->throttled_clock`,每个被 throttle 的 cfs_rq 各加一次;`cpu.stat` 的 `throttled_usec` = `cfs_b->throttled_time` / 1000 | kernel/sched/fair.c:6033 ~ :6034、:9752 ~ :9764(v6.12) |
| 89 | Deep | `cfs_rq_min_slice` 6.12 新加 | 已核 | v6.11 `fair.c` 无 `cfs_rq_min_slice` | https://raw.githubusercontent.com/torvalds/linux/v6.11/kernel/sched/fair.c |
| 90 | Deep | `PLACE_REL_DEADLINE` 6.12 新加 | 已核 | v6.11 `features.h` 无 | 同 How #23 |
| 100 | Comparison | NT 没有周期性跨处理器负载均衡 | 部分核实 | 微软课件(Windows Internals 第 4 版授权)与 Probert 讲义只描述就绪 / 空闲时选核与 Balance Set Manager 每秒扫一次饥饿线程;OSR 论坛(二手)称空闲核在进出空闲时主动拉任务;未见周期均衡,但"未见"仍不等于"已证无" | https://osm.hpi.de/bs/2007/Slides/Unit04/4.5_AdvancedScheduling.pdf ;https://community.osr.com/t/multicore-ht-multi-cpu-scheduling/31516 |
| 101 | Comparison | AutoBoost 引入版本 Windows 8.1 | 无法核实 | 微软文档与 Wikipedia 只说 AutoBoost 取代了 random boosting,不给版本;正文保留 "Windows Internals,二手" 标注 | https://learn.microsoft.com/en-us/windows/win32/procthread/priority-inversion |
| 102 | Comparison | Job 对象 CPU 速率控制的 "scheduling interval" 长度 | 无法核实 | 文档只写 "during each scheduling interval" / "until the next scheduling interval",不给毫秒数 | https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-jobobject_cpu_rate_control_information |
| 103 | Comparison | 理想处理器按进程轮转播种、SMT 兄弟错开 | 部分核实 | 课件:"System selects ideal processor for first thread in process (round robin across CPUs); Next thread gets next CPU relative to the process seed";SMT 错开未见(仅提 Server 2003 的 `GetLogicalProcessorInformation`) | https://osm.hpi.de/bs/2007/Slides/Unit04/4.5_AdvancedScheduling.pdf(基于 Windows Internals 第 4 版,二手) |
| 104 | Comparison | Resource Governor `CAP_CPU_PERCENT` 自 SQL Server 2012 | 已核 | "CAP_CPU_PERCENT … Applies to: SQL Server 2012 (11.x) and later";硬上限,区别于 MAX_CPU_PERCENT 的软上限 | https://learn.microsoft.com/en-us/sql/t-sql/statements/create-resource-pool-transact-sql |
| 105 | Comparison | CPU Sets 首版 Windows 10 1703;Core Reservation 适用版本 | 部分核实 | `SetThreadSelectedCpuSets` 最低 Windows 10 / Windows Server 2016(具体 build 文档不给,"1703" 未证);Core Reservation 文档只说 "Some versions of Windows support" | https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-setthreadselectedcpusets ;…/procthread/cpu-sets |
| 106 | Comparison | 窗口输入提升 +2 | 部分核实 | 课件:"GUI threads that wake up to process windowing input get a boost of 2 (added to the current, not base priority)";前台进程的等待结束也 +2;微软 Win32 文档只给规则不给数 | https://osm.hpi.de/bs/2007/Slides/Unit04/4.5_AdvancedScheduling.pdf(二手);https://learn.microsoft.com/en-us/windows/win32/procthread/priority-boosts |
| 107 | Comparison | Go sysmon 10 ms 抢占阈值 | 已核 | `const forcePreemptNS = 10 * 1000 * 1000 // 10ms`(正文未用数字) | https://raw.githubusercontent.com/golang/go/master/src/runtime/proc.go(forcePreemptNS) |
| 108 | Comparison | NT 侧 "两片 ≈ 374 ms" | 部分核实 | 推算与服务器长片 12 tick × 15.625 ms ≈ 187.5 ms 一致(2 片 ≈ 375 ms);未上机 | 上一轮已核 #6;Microsoft Priority Boosts 页的 "reduces that priority by one level each time the thread completes a time slice" |
| 109 | Comparison | Deep 的 § 编号 | 已核 | 05-deep.md 实际标题 §2 主线① EEVDF / §3 主线② 多核 / §4 主线③ cgroup / §5 附录,与引用一致 | stages/05-deep/05-deep.md |
| 120 | Synthesis | MySQL Enterprise 线程池默认值:size 16、stall_limit 6(×10 ms)、prio_kickup_timer 1000 ms、query_threads_per_group 1、其余 0 | 已核 | 属性表:size 16(1 ~ 512);stall_limit 6(4 ~ 600,单位 10 ms);prio_kickup_timer 1000 ms;query_threads_per_group 1;max_unused_threads / max_transactions_limit / transaction_delay 0;algorithm 0 | https://dev.mysql.com/doc/refman/8.4/en/server-system-variables.html |
| 121 | Synthesis | Percona 8.0 线程池默认值;stall_limit 500 ms 与"另一构建写 6"不一致 | 改写 | 页内表与正文均为 500 ms,示例 `= 100` 只是示例;"6"是 MySQL Enterprise 的默认,不属 Percona,已删去混淆说法;size = 核数、oversubscribe 3、high_prio_tickets 4294967295、high_prio_mode transactions、max_threads 100000、idle_timeout 60 s、8.0.12-1 引入 | https://docs.percona.com/percona-server/8.0/threadpool.html |
| 122 | Synthesis | `thread_pool_oversubscribe` = 每 group 并发上限 | 部分核实 | MariaDB 文档:一个 group 允许的额外活跃工作线程数上限,超过即让线程歇下,不参与新线程创建;Percona 页只写"队列饱和阈值";§7.6 K2 改为"软上限,不控创建" | https://mariadb.com/kb/en/thread-groups-in-the-unix-implementation-of-the-thread-pool/ |
| 123 | Synthesis | 最坏等待 222 s;每秒最多升 100 条到高优先队列 | 已核 | 原句:"a maximum of 100 statements per second are moved to the high-priority queue"、"it takes 222 seconds before the new statement starts executing"(例子里 kickup 设 10 s) | https://dev.mysql.com/doc/refman/8.4/en/thread-pool-tuning.html |
| 124 | Synthesis | mq-deadline 默认 read 500 ms / write 5 s / writes_starved 2 / fifo_batch 16;bfq 用 B-WF2Q+ | 已核 | `read_expire = HZ / 2`、`write_expire = 5 * HZ`、`writes_starved = 2`、`fifo_batch = 16` | v6.12 block/mq-deadline.c:30 ~ :38;block/bfq-iosched.c:31 ~ :33 |
| 125 | Synthesis | Go sysmon 10 ms、抢占阈值 10 ms、偷一半、runq 256 | 已核 | `sysmon` :6031;睡眠上限 10 ms :6047;`forcePreemptNS = 10 ms` :6187;`retake` :6216;`runqgrab` `n = n - n/2` :6878;`runq [256]guintptr` runtime2.go:671 | go1.23.0 src/runtime/proc.go、runtime2.go |
| 126 | Synthesis | Go 1.25 起 GOMAXPROCS 按 cgroup 限额自动设 | 已核 | 「Container-aware GOMAXPROCS」:Linux 上按 cgroup CPU bandwidth limit 取较小值(只看 limit 不看 requests),所有 OS 上周期性更新;可用 GODEBUG 关闭 | https://go.dev/doc/go1.25 |
| 127 | Synthesis | fq_codel 默认 quantum 1514、target 5 ms、interval 100 ms、1024 流、新流先给一个 quantum | 已核 | `q->quantum = psched_mtu(dev)` = mtu + hard_header_len(1500 + 14);`flows_cnt = 1024`;`limit = 10*1024`;新流 `deficit = quantum`;`interval = MS2TIME(100)`、`target = MS2TIME(5)` | v6.12 net/sched/sch_fq_codel.c:212 / :475 ~ :479;include/net/pkt_sched.h:137;include/net/codel_impl.h:56 ~ :57 |
| 128 | Synthesis | NT 无周期均衡 | 随 #100 | 见 Comparison #100 的结论(未见 ≠ 已证无) | — |
| 129 | Synthesis | Meta / Valve / 手机厂商生产使用 scx | 随 #86 | 见 Deep #86 的结论 | — |

### 正文改动清单

- `stages/03-how/03-how.md` §0.3:"6.12 把老名字 `load_balance` 改成了它" → "6.10 …"(#12);§4.2 抢占模型表 `PREEMPT_LAZY` 行去掉待核标记(#16);待核表第三列改为结论。
- `stages/04-origin/04-origin.md` §4.2:staircase 补首帖日期 2004-03-24 并引 [一手 48](#40);§6 `cpu.max.burst` 去掉待核标记(#44);§12 新增 48 ~ 52 五条一手(Con 2004 首帖、Linus 2007-07-27 "ignoring reality"、Peter 2008 RFC 正文、sched_ext 合并提交、CFS 核心提交);§13 五行由"无一手"改为已找到或已核,APC 采访行改为部分核实;待核表第三列改为结论。
- `stages/05-deep/05-deep.md` §2.5 A6:现实用户改为 "Meta 的生产部署、Valve Steam Deck 上 Igalia 的 `scx_lavd`"(#86);§4.1 `cpu.weight` 行补 k8s `requests.cpu` → shares → weight 公式(#76);§4.5 C4 候选去掉 burst 待核标记(#20);待核表第三列改为结论。
- `stages/06-comparison/06-comparison.md` §3.1 提升表 "+2" 标注课件出处(#106);§3.4 AutoBoost 版本改注"收尾核实未找到一手"(#101);待核表第三列改为结论。
- `stages/01-what/01-what.md`、`stages/02-why/02-why.md`:新增 `## 待核` 小节列出 #1 ~ #5 / #6 ~ #11 的结论;正文未改。
- 六份各追加一行修订记录。
