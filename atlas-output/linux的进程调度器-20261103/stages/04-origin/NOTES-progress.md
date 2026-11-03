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
