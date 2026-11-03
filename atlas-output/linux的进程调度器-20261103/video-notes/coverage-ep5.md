# ep5 覆盖与证据矩阵（Deep）

主角色：源码 / 实现。输入 `stages/05-deep/05-deep.md`（1626 行，收尾核实后的版本）、约束速查 C1 ~ C8、`pics/05-*.png` 四张图、`video-notes/src/linux-6.12/kernel/sched/fair.c`（9 段 code_explain 全部为逐字连续子串，review_ep.py 核对通过）。未改动源 MD、stages、原 SVG。

主链：一万三千行里只有三处做决定 → 三个判据（layers）→ 三条调用链图 → 主线一：update_deadline / entity_lag / place_entity / pick_eevdf / 唤醒抢占五段源码 → 模拟器五拍表（ascii）→ 纳秒时间线图 → 反问一（text + example 自答）→ 主线二：task_hot / calculate_imbalance → rq3 算例图 → 反问二 → 主线三：__assign_cfs_rq_runtime / throttle_cfs_rq → 钩子一 cpu.stat 图 → 反问三 → 三线同轴 timeline → 附录一屏 → 总结卡 → 下集预告。

| 原文必讲项 | 证据载体 | 场景 | 处理 |
|---|---|---|---|
| §0 三个判据 + 行号 | layers + sidebar C2 / C3 / C5 / C6 | 3 | 保留，行号用 v6.12 实物（907 / 5266 / 11048 / 9260 / 5772 / 5915） |
| §1 概览图 05-overview | pics/05-overview.png | 4 | 整图保留，按三列 + 三个绿框解说 |
| §2.1 操作层旋钮表 | 未上屏 | — | 文档保留（口播在 6 提到 6.12 自定义片 0.1 ~ 100 ms） |
| §2.2.1 update_curr / update_deadline | fair.c 1007 ~ 1029 code_explain | 6 | 保留 update_deadline 全函数；update_curr 只口播 |
| §2.2.2 V 与两个累加器 | 口播（场景 9、11） | 9、11 | 压缩为"平均线"一词；累加器代码未上屏，文档保留 |
| §2.2.3 entity_lag / update_entity_lag / place_entity | fair.c 692 ~ 707、5338 ~ 5370 | 7、8 | 保留；place_entity 取放大段（连续子串），前半段的 avg_vruntime 读取口播带过 |
| §2.2.4 pick_eevdf 全文 + set_next_entity HACK | fair.c 907 ~ 970 | 9 | 保留全函数；HACK 在高亮第 3 段口播 |
| §2.2.5 check_preempt_wakeup_fair | fair.c 8824 ~ 8842 | 10 | 取后半段（记账 / 撤保护 / 再挑一次） |
| §2.2.6 dequeue_entity / DELAY_DEQUEUE | 未上屏 | — | 文档保留（控时长删去） |
| §2.3 三条 trade-off + 纳秒时间线 | pics/05-timeline.png | 12 | 保留时间线；trade-off 表未上屏 |
| §2.4 模拟器五拍表 + 逐列解释 + 300 ms 对账 | ascii 表 | 11 | 保留 6 行 + 对账一行；口播逐列讲 |
| §2.5 反事实 A1 ~ A6 | 未上屏 | — | 文档保留（Synthesis 五元组回收） |
| §2.6 反问 + deep26 模拟 | text + sidebar + example | 13 | 保留，答案 B（+6）、立刻抢、连跑 12 ms |
| §3.1 多核旋钮表 | 口播（场景 15 sysctl −1 / 0） | 15 | 只保留 migration_cost 旋钮 |
| §3.2.1 select_task_rq_fair / wake_affine / select_idle_cpu | 口播（场景 12 时间线 0.5 μs 行） | 12 | 源码未上屏，文档保留 |
| §3.2.2 sched_balance_rq 五步 / sg_lb_stats / group_type | 口播（场景 17） | 17 | 压缩为"最忙组 / 差距 / 从队尾挑" |
| §3.2.2 calculate_imbalance | fair.c 11134 ~ 11165 | 16 | 取 has_spare 后半段（按个数 / 空核数 / 砍半）；migrate_util 分支口播 |
| §3.2.2 can_migrate_task / task_hot | fair.c 9260 ~ 9299 | 15 | 保留 task_hot 全函数 |
| §3.2.2 sched_balance_newidle 三道门 | 场景 18 example | 18 | 口播三道门（ttwu_pending / rd_overloaded / avg_idle） |
| §3.2.3 PELT / §3.2.4 sd_init | 未上屏 | — | 文档保留（口播在 16 提到"按算力比"） |
| §3.4 rq3 算例 MC / PKG | pics/05-balance.png | 17 | 保留；数字 5 − 0 → 2 → 只搬 1；13 / 9 = 144% > 117%；migrate_util 1024 |
| §3.5 反事实 B1 ~ B6 | 未上屏 | — | 文档保留 |
| §3.6 反问绑核 | text + example | 18 | 保留，答案 B |
| §4.1 cgroup v2 四个文件 + k8s 公式 | 口播（场景 22 "限两核就是每周期两百毫秒"） | 22 | 公式未上屏，文档保留 |
| §4.2.1 组实体逐层 / §4.2.2 calc_group_shares | 未上屏 | — | 文档保留（控时长删去） |
| §4.2.3 借 / 停 / 放 / 还 | fair.c 5772 ~ 5797、5915 ~ 5940 | 20、21 | 保留借与停；放（period timer）与还（slack）口播 |
| §4.4 钩子一 cpu.stat + 改 4 核五配置 | pics/05-bandwidth.png | 22 | 保留；答 C；E 根治 = 并发 |
| §4.5 反事实 候选一 ~ 五 | 未上屏 | — | 文档保留 |
| §4.6 反问 period 10 ms | text + example | 23 | 保留，答案 B（100） |
| §5 附录八专题 | text + example | 25 | 一屏带过（rt 95% / dl 准入 + fair_server 5% / 抢占模型 / sched_ext 20 ms / EAS / NUMA） |
| §6 110 ms 同轴时间线 | timeline（8 行） | 24 | 保留主要事件 |
| §7 约束回扣 | 总结卡 + 口播 | 26 | 压入总结六件事 |
| §8 呼应 95% | 下集预告 | 27 | 口播埋 Comparison 钩子 |

## 事实处理
- 全部数字取自 05-deep.md 收尾核实后版本：base_slice 3 ms、夹紧 ±6 ms、放大 (W + w)/W、migration_cost 500 μs、imbalance_pct 117、`>>= 1`、newidle 只搬 1（`fair.c:9607`）、PKG `migrate_util` 1024、bandwidth slice 5 ms、quota 200 ms / period 100 ms、停 87.5 ms、throttled_usec ≈ 14 s/s（按 cfs_rq 累加）、fair_server 50 ms / 1000 ms、sched_ext 默认片 20 ms。
- 收尾核实的改写已反映：sched_ext 现实用户只说"每个负载自己选"未点名厂商；6.12 新增特性（DELAY_DEQUEUE 等）未在口播里标版本以外的说法；PREEMPT_LAZY 未提。
- 时间线各行 ns 为量级估计（Deep 待核 #70），口播用"零点三微秒""六点五到七点五微秒"等量级表述。
- 对原文无事实修正。

## 口播自检
- lint（generic）0 错误 10 警告（CODE-MULTI-HL ×9、NUM-RECAP ×1，均为告警）；review_ep.py ISSUES 0；旁白无 atlas / 场景类型词；code 场景无 sidebar；ascii / layers / text 画面无 `→` 与圈号。
