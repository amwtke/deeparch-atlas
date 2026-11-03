# ep3 覆盖与证据矩阵（How）

主角色：实操员。输入 `stages/03-how/03-how.md`（810 行，2026-11-03 收尾核实后版本：§0.3 改名版本 6.10、§4.2 PREEMPT_LAZY 6.13、§7 fair_server 与 95% 阀并存、§14 分岔三「两实体时 mysqld 无资格」、§5.5「newidle 只搬 1 个 / PKG 层 migrate_util 1024」）。约束速查 C1 ~ C8 取自同文件顶部。未改动源 MD、stages、原 SVG。

主链：一秒钟几万次决定 → 三件事（layers）→ 概览图 → 01 每核一本账与类栈（rq、六层、快路径、95% 阀）→ 02 fair 四个数（权重 → 那张表 → vruntime 与 V、slice 与 deadline → lag 一张图 → lag 两条纪律 → 挑人六步 → 五拍算例）→ 03 标记与出口（插旗 vs 出口双栏、抢占模型、唤醒抢占六步）→ 04 三种搬人（调度域图、门槛与算例、taskset 两面闭环）→ 05 封顶（组与带宽图、钩子一周期与改 4 核答案）→ 三个误解 + 硬保证并存 → 反问与从头走一遍 → 总结卡 → 下集预告。

| 原文必讲项 | 证据载体 | 场景 | 处理 |
|---|---|---|---|
| 约束速查 C1 ~ C8 | 各场景 sidebar 按 `C 几 短名` 引用 | 3、9、10、12、13、16、20、21、24、25、26 | 口播一律带短名 |
| §0 三件事 + 对照表 + 嵌套 | layers + sidebar | 3 | 保留三件事与各自约束；嵌套关系在口播 |
| §1 概览图 03-overview + 五件事 | pics/03-overview.png | 4 | 整图保留，五件事逐条口播 |
| §2.1 rq 字段表 | ascii 顶行（curr / nr_running / cpu_capacity）+ 口播 | 6 | 保留四个字段；clock_task、next_balance 文档保留 |
| §2.2 六类表 + 快路径 | ascii 六层 + 快路径一行 | 6 | 保留；ext 标 6.12 新 |
| §2.3 逼问表 | 口播（全局一本账 / 类栈 / 快路径 / cpu_capacity） | 6 | 合并进口播，不单列 |
| §3.1 nice 权重表 + 算例 | text（三任务权重、份额 90:10:0.14、每 ms 涨幅）+ example | 8 | 保留；"nice -10 没用"落在 example |
| §3.1 `sched_prio_to_weight[]` | code_explain，kernel/sched/core.c 10012–10021 | 9 | 单段高亮（generic 门禁下合规），口播讲 1.25 倍与"只是查表" |
| §3.2 vruntime、V 定义、两个累加器、算例 1203.94 | ascii 上半 | 10 | 保留公式与算例 |
| §3.3 slice 3 ms、自定义 0.1 ~ 100 ms、deadline 推一次、三任务 +3.00 / +0.32 / +204.8 | ascii 下半 | 10 | 保留；tick 粒度 4 ms 放到场景 14 |
| §3.4 lag 从零讲 + 03-ledger 图 | pics/03-ledger.png + text（定义、夹紧、守恒放大、DELAY_DEQUEUE）+ example（三任务夹紧值、放大公式、CFS 分水岭） | 11、12 | 保留全部四段；公式口语化为"总权重加它自己再除以总权重" |
| §3.5 pick_eevdf 六步、RUN_TO_PARITY、PREEMPT_SHORT | layers | 13 | 保留六步原序 |
| §3.6 五拍算例 + 四件事 | ascii 表（t 0 / 4 / 8 / 10 / 10.05，v/lag/V/选谁）+ 口播四件事 | 14 | 保留；deadline 列为控宽去掉（在场景 10 已给） |
| §3.7 组是同形一行、calc_group_shares 形状、1024 / 8 = 128 | 场景 23 口播（图左半） | 23 | 保留结论与 128；公式形状文档保留 |
| §3.8 逼问表 | 场景 12、13 口播 | 12、13 | 合并 |
| §4.1 五触发点 + 三种标记来源 + IPI | ascii 双栏左栏 | 16 | 保留 |
| §4.2 两种出口 + 抢占模型表（含 PREEMPT_LAZY 6.13） | ascii 双栏右栏 + 底部两行 | 16 | 保留五种模型名；代价列文档保留 |
| §4.3 tick 两件事 + NO_HZ_IDLE / NO_HZ_FULL | 场景 16 sidebar（NO_HZ_IDLE） | 16 | NO_HZ_FULL 文档保留 |
| §4.4 唤醒抢占六步 | timeline | 17 | 保留；"p99 0.2 ms vs 5 ms"结论在口播 |
| §4.5 逼问表 | 场景 16 口播（持锁不换栈） | 16 | 合并 |
| §5.1 调度域表 + 03-domains 图 | pics/03-domains.png | 19 | 整图保留；MC / PKG、117%、4 ~ 100 ms 在图上 |
| §5.2 PELT 三量 + capacity | 场景 20 visual（32 ms 半衰期、按算力比）+ sidebar | 20 | 三个量名文档保留 |
| §5.3 三种搬人五步 | 场景 19 口播 + 场景 20 visual | 19、20 | 保留 |
| §5.4 策略表（NUMA balancing、misfit、EAS） | 未上屏 | — | 文档保留（Deep 附录会讲） |
| §5.5 rq3 算例（newidle 搬 1 个；PKG 层 144% > 117%） | example | 20 | 按 Deep 修正后的版本 |
| §5.6 taskset 两面表 | ascii 双栏 | 21 | 保留四行里的两行 + isolcpus |
| §5.7 逼问表 | 场景 20 口播 | 20 | 合并 |
| §6.1 cfs_bandwidth 字段 | 场景 24 timeline 标题（200000 100000）+ 口播 | 23、24 | burst / slack_timer 在口播一句 |
| §6.2 借 / 停 / 放 | pics/03-cgroup.png 右半 + timeline | 23、24 | 保留三动作 |
| §6.3 钩子一算例 + 改 4 核三选项 + 并发旋钮 | timeline + 口播 | 24 | 保留答案 C 与"并发才是根治"；period 10 ms / burst / 只用 weight 三行文档保留 |
| §6.4 weight vs max | 场景 25 example 第二条 | 25 | 压缩为一句 |
| §6.5 逼问表 | 未上屏 | — | 文档保留 |
| §7 硬保证三类表 + fair_server 并存 | 场景 6（95% 阀）+ 场景 25 口播（fair_server 并存，5%） | 6、25 | 保留阀与并存结论；dl 准入、PI 文档保留（Deep 附录） |
| §8 两条端到端五步 | 场景 14 第 8 ms / 10 ms 两行 + 场景 17 | 14、17 | 以算例两拍承载；7 ~ 10 μs 分项留 Deep |
| §9 伪代码 + 观测工具表 | 未上屏 | — | 文档保留（Deep 有真源码与观测） |
| §10 朴素 vs 真实 | 各场景 sidebar 的约束对应 | — | 合并 |
| §11 三个误解 | text + example | 25 | 保留三条 |
| §12 约束回扣 | 总结卡 + 各 sidebar | 27 | 合并 |
| §13 呼应 65% | 总结卡口播 + 下集预告 | 27、28 | 指向 Origin |
| §14 反问 + 从头走一遍 | text（题目、四选项、答案）+ example（三个分岔） | 26 | 按修正版：两实体时 mysqld 没资格；64 ms；夹紧 0.643 |

## 源码摘录（逐行取自 Linux v6.12，副本在 video-notes/src/linux-6.12/）

| 场景 | 文件 | 行号 | 核对 |
|---|---|---|---|
| 9 | kernel/sched/core.c（sched_prio_to_weight[]） | 10012–10021 | review_ep.py 子串逐字一致 |

## 相对原文的事实修正

1. 收尾核实改写项已按主控通知同步：`sched_balance_*` 改名版本 6.10（本集口播未点版本号，只说"周期与空闲均衡"）；`PREEMPT_LAZY` 6.13（场景 16 画面）；`fair_server` 与 95% 阀并存（场景 25 口播）。
2. §3.6 第 4 ms 行 V 1203.94 在表里写作 1203.9（控宽四舍五入），口播不读该数。
3. §5.5 按 Deep 修正：newidle 搬 1 个、PKG 层按 migrate_util（口播说"跨 L3 拉一个"，不点 1024）。

## 验收

- 场景 28 个，视觉类型 8 种：spotlight 2、title 6（其中 5 张编号小节卡 01 ~ 05）、layers 2、html_slide 5（四张 03 图 + 总结卡）、ascii 5、text 5、code_explain 1、timeline 2。无人物场景（本集无人物）、无生活类比插件。
- 口播（含 example）约 4925 字；估时 = 字数 ÷ 5.4 + 28 × 1.5 s ≈ 15.9 分钟（超出简报 13 分钟目标，取"讲透优先"；实际以 TTS 为准）。
- vmd_lint（anthropic，generic）：0 错误，1 条告警（NUM-RECAP 为场景序号 28 的误报）。book profile 下的 BOOK-CHAPTERS 也满足（01 ~ 05 连续）。
- review_ep.py：ISSUES 0（旁白无 atlas、无场景类型名、无 markdown；画面无箭头 / 带圈数字 / 勾叉；源码逐字比对通过）。
- ascii 五幕最大显示宽度 ≤ 70 列、≤ 13 行。
- 总结卡 pics/ep3-summary-card.png 已目检。
- 未改动 atlas md、stages、原 SVG 与其他集文件；未渲染、未提交、未上传。

分P标题建议：P3 How：账、标记、搬人，内核用什么把八条约束化解掉
