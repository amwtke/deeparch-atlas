# ep4 覆盖与证据矩阵

主角色：来路 / 演化史；输入原文 Origin 行 1959–2335，另读约束速查行 1–102 与收尾核实表行 4215–4242（#1–#7、#16 涉及本篇）。

主链：你今天的一次 read 穿过五层 → 每层都有出生年份 → 1974~1992 原件定型（形状）→ 1998~2008 日志、统一缓存、extent（换内脏）→ 2002~2021 硬件逼块层两次重做、调度器反转、folio → 每层出生时缺的约束就是今天的历史债 → 五个转折点都是“约束代价第一次忍不了”。

| 原文必讲项 | 证据载体 | 场景 | 处理 |
|---|---|---|---|
| §0 三件事 | 三行分层表 | 3 | 保留，年代与“形状 / 内脏 / 推翻”三分法 |
| §1 时间线图 | pics/04-timeline.png | 4 | 整图保留，按泳道讲五个读法 |
| §2.1 1974 Unix 三样原件 | CACM 1974 论文引文 | 5 | 人物 Dennis Ritchie（照片已核），提及 Ken Thompson |
| §2.2 1984 FFS“快是后加的” | FFS 论文 2% 带宽 | 6 | 压成旁白一句 |
| §2.3 1986 Kleiman vnode / vfs | Kleiman 1986 论文；6.12 file_operations 原文 | 6–7 | 保留；源码证明“那张表”的直系后代 |
| §3 1992 Linux VFS、ext、ext2 | ext2 论文（Card / Ts'o / Tweedie 1994） | 8–10 | 保留 Minix 16 位 / 64 MB / 14 字符、0.96c、ext 死胡同、file 与 inode 分开 |
| §4.1–4.4 Tweedie 日志 | 1998 论文引文、四条路表 | 11–14 | 保留烦躁 / 四条路 / 三个决定 / 盘上格式冻结 |
| §4.4.1 反事实 | 论文对 WAFL 的评价，ZFS / btrfs 旁证 | 14 | 压成一条例子 |
| §4.4 入主线 | ChangeLog-2.4.15（核实表 #3） | 15 | 保留 2001-11 Morton 合入 |
| §4.5 extent 来自 Lustre | OLS 2007 论文；Tomas LKML 2005-02、2006-08 | 15–16 | 保留 16 TB、128 MB、4 条、2.6.28 稳定 |
| §5 2001 块设备进 page cache | Riel 2001；LWN 2001-05；Linus 2001-09-08 / 09-17（核实表 #5 #7） | 17–19 | 保留两套缓存、元数据损坏、九天改主意、Morton 评价、O_DIRECT 诞生 |
| §6.1 bio | Axboe 2001-12 说明、biodoc | 20–21 | 保留 2.4 块层毛病清单与 bio 形状 |
| §6.2 blk-mq | kernelnewbies 3.13（核实表 #2）、5.0 说明 | 21 | 保留 80 万为旧单锁上限、2019 年 5.0 删光 |
| §7 调度器谱系 | LWN 2000~2017、提交 f382fb0bcef4（核实表 #4） | 22–23 | 六段压成一条状态线 + 一段 C6 反转说明 |
| §8.1 Wilcox NVMe 驱动 | Wilcox 2011-03-03 帖、3.3 合入（核实表 #6） | 24 | 保留每 CPU 一队列、撞上单锁墙；bio-based 绕路写进约束回扣表 |
| §8.2 folio | Wilcox 2020-12 RFC、5.16 合并 | 24 | 保留“保证不是尾页”与 compound_head 例子 |
| §9 约束回扣表 | 六行对照 | 25 | 保留核心六行，其余留在文档 |
| §10 呼应 | — | 26–27 | 化成“没有一个是灵光一现”与总结卡 |
| §11 / §12 资料列表与待核 | — | — | 文档保留，不朗读 |

一手出处：见原文 §11；源码 include/linux/fs.h（Linux v6.12，经 jsDelivr gh/torvalds/linux@v6.12 取得，存 video-notes/src/include__linux__fs.h），场景 7 摘第 2062–2080 行，逐字核对一致。

事实处理：
- 按核实表 #2，“80 万 IOPS”只作旧单锁设计上限讲，不说成 blk-mq 指标。
- 按核实表 #6，NVMe 驱动 2012~2015 是 bio-based、绕过 request_fn / 电梯路径，不说成绕过 request_queue 对象。
- 按核实表 #16，page cache 早于 2001 已存在；本集只讲 2.2 两套缓存并存与 2001 年块设备并入，不声称 2001 年才有 page cache。
- 时间线图写 “2014 blk-mq 入 3.13”（发布日期），旁白 2013 指 blk-mq 写成与论文年份，两者一致。
- Kleiman、Alex Tomas、Andrea Arcangeli、Matthew Wilcox 没有可核实的本人照片（同名演员 / DJ / 错图），改由文字场景介绍，不做人像。

人物：facetime 4 位（Ritchie、Torvalds、Tweedie、Axboe），文字介绍 4 位（Kleiman、Tomas、Arcangeli、Wilcox），来源记录 pics/portrait-sources-ep4.json。

验收：28 场景，10 种视觉类型（spotlight 5、title 2、layers 1、html_slide 2、facetime 4、text 7、code_explain 1、ascii 3、timeline 2、statemap 1）；旁白含 example 3386 字，按 5.4 字/秒加场间 1.5 秒估计约 11.2 分钟。Anthropic VMD lint 0 错误，1 条 CODE-MULTI-HL 告警（源码分三段高亮，旁白按段顺序讲）。三个 ASCII 框按渲染器 13 px / 22 px 字宽逐行补齐，边线误差 ≤2 px。总结卡 pics/ep4-summary-card.png 1920×1080 已目检无溢出。
