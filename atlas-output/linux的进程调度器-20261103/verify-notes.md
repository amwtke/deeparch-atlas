# verify-notes(内部)—— 未能定案的项与跨篇不一致

## 未能定案
- #5 / #6 / #70 / #85:纯量级估计或场景假设;用户 macOS 上无法跑 perf / bpftrace,只能留在"估计"。真机核法:`perf sched record` + `perf sched latency`(#70)、`perf stat -e irq_vectors:local_timer_entry`(#5)。
- #19 / #71:Deep 分项 6.5 ~ 7.5 μs 与 How 的 7 ~ 10 μs 已在 Deep §2.3 对齐("下限成立,上限对应不可抢占段"),Comparison §3.3 仍写 "~7 ~ 10 μs(How §8.2;Deep §2.3 钉到 ns)",口径一致,不必改。
- #101 AutoBoost 版本:微软文档、Wikipedia、NtDoc、社区帖都不给引入版本;只有 Windows Internals 7th 书内(未能联网读)。正文保留"二手"。
- #102 Job 速率控制的调度间隔:文档明确不给数;Windows Internals 7th 可能有(未能读)。
- #100 NT 周期均衡:课件 / 讲义 / 文档均无周期均衡步骤;OSR 论坛说空闲核会拉任务(二手)。仍是"未见",正文措辞已是"未见≠已证无"。
- #47 4.3BSD 文件版本 7.1 ↔ 发布版:只核到发布月份(1986-06)。
- #48 TR-95-22 原发日期:PDF 首页只有报告号和 "Revised January 26, 1996"。
- #50 APC 采访:原页与 archive.org 本机都不可达;只核到 LWN / OSNews 转载的两句。
- Windows Internals 6th 的 O'Reilly 在线章节返回 403,未能用书内原文核 #100 / #103 / #106;改用微软授权课件(HPI 2007,基于第 4 版)作二手。

## 跨篇不一致(已处理或建议)
1. How §0.3 写 `sched_balance_rq` 改名在 6.12,实际 6.10 —— 已改(#12)。Origin 没有写改名版本,无冲突。
2. Origin 待核表 #49 原写 "2007-07-28",Linus 原信是 2007-07-27 22:36 EST(UTC 已是 28 日);§12 第 12 条 "Re: [ck] Re: Linus 2.6.23-rc1 … 2007-07-28" 是另一封,不冲突;已在 #49 结论里写明时区。
3. Deep L789 源码注释 "每次最多看 32 个" 在 `CONFIG_PREEMPT_RT` 下是 8(#78 已注明);How 未提此数,无冲突。
4. Deep #18 / #74 与 How §7:fair_server 默认 50 ms / 1000 ms,两处一致;新增事实 "dl_server 基础设施 6.8、fair_server 6.12" 只写在核实表,正文未加(How §7 说 "6.12 还有一个新东西" 仍成立)。
5. What §硬件 ③ 与 Why 第五刀都写 "L2 miss ~10 ns",口径一致;核实为 L3 命中量级(Skylake 42 周期),成立。
6. Comparison §4.3 "Windows 8 加 Job 速率控制" 与 API 页最低版本 Windows 8 / Server 2012 一致。
7. 06-comparison 写作时 Deep § 编号按主控布局引用,核实后与 05-deep.md 实际标题一致(#109)。

## 未做
- 没有触碰 stages/07-synthesis(并行写作中)与 PROGRESS.md。
- 修订记录各加一行;verify-results.md 为对读者的表,可直接拼进综合长文末尾。
