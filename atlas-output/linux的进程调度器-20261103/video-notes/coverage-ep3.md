# ep3 How 覆盖与证据矩阵

主角色：机制路径（How）；输入原文 `linux的进程调度器-atlas.md` 第 549–1071 行（How 篇 §0–§12）+ 第 53–100 行约束速查 + 第 3763–3863 行收尾核实（How-1 ~ How-15，以核实结论为准）。未改动源 MD、stages、原 SVG。

主链：三问 → 三件事（数据/控制/策略）→ 全景图 → vruntime 与权重 → calc_delta_fair 源码 → 一秒的账 → 水位放置 → 红黑树 → EEVDF 资格与期限 → update_deadline 源码 → 三扇门 → 门 1/门 3 双路径 → __schedule 五步 → 悬念 1：借栈换人（图 + __switch_to_asm 源码 + 为什么最省 + fork 伪造帧）→ 3 μs 抢占时间线 → 调度类链 + rt 950 ms → __pick_next_task 源码（编译期策略模式）→ 选核 → 对账 → 调度域 → C7 + cgroup 树 + 两个旋钮 → C8 + sched_ext 回调表 + scx_simple 源码 + 兜底 → 朴素 vs 真实 → 三个误解 → 总结卡 → Origin 预告。

| 原文必讲项 | 证据载体 | 场景 | 处理 |
|---|---|---|---|
| §0 三件事 + 约束来源 | layers + sidebar 约束 | 2 | 保留；§0.4 对照表并入 sidebar |
| §1 概览图 03-overview | pics/03-overview.png | 3 | 整图保留，按门/标记/出口/链/树/别的核逐区讲 |
| §2.1–§2.2 vruntime 与权重 | text（公式 + nice 0/-5/+5） | 5 | 保留 How-1 数字 |
| 折算实现 | Linux 6.12 kernel/sched/fair.c L289–295 `calc_delta_fair` | 6 | 新增可复查源码 |
| §2.3 cc1/chrome 一秒算例 | timeline | 7 | 保留；数字为原文算例（How-2 为演示性质，旁白只讲机制结论） |
| §2.4 水位 min_vruntime + lag | ascii 双栏（不修正 vs 水位放置） | 8 | 保留 |
| §2.5 为什么红黑树 | ascii 四结构表 | 9 | 保留 |
| §2.1 末条「期限一栏」(EEVDF) | ascii 三任务算例 + Linux 6.12 fair.c L1007–1029 `update_deadline` | 10–11 | 按派工要求展开：lag = V − v、资格、期限 = 片起点 v + slice×1024/w；片长 0.75 ms×(1+log2 min(核数,8))（How-5） |
| §2.6 rt/dl 的账本 | 调度类链 layers | 22 | 合并 |
| §3.1–§3.4 三扇门 | ascii 三门汇出口 + ascii 门 1/门 3 双泳道 | 12–14 | 保留；双路径按用户规则画框图 |
| §3.5 schedule() 五步 | timeline | 15 | 保留 |
| §3.6 悬念 1 + 03-switch 图 | spotlight + pics/03-switch.png | 16–17 | 整图保留 |
| §3.6 __switch_to_asm 寄存器集 | Linux 6.12 arch/x86/entry/entry_64.S L182–215 | 18 | 新增可复查源码（How-6） |
| 「为什么借栈最省」 | ascii 双栏（独立调度进程 vs 借栈） | 19 | 新增原理段，按「先讲为什么最优」规则 |
| §3.6.1 fork 新任务伪造帧 | statemap | 20 | 保留（How-15 函数名 ret_from_fork_asm） |
| §3.7 3 μs 时间线 | timeline | 21 | 保留，旁白说「量级」 |
| §4.1–§4.3 调度类链 + 950 ms | layers + sidebar | 22 | 保留；RR 100 ms（How-8）上屏 |
| §4.4 策略模式（编译期） | Linux 6.12 kernel/sched/core.c L5984–6001 `__pick_next_task` 循环段 | 23 | 新增可复查源码；原 spotlight 合并进本场景旁白 |
| §5.1–§5.2 每核队列 + 唤醒选核 | spotlight + ascii 决策链 | 24–25 | 保留 |
| §5.3–§5.4 周期对账算例 | ascii 前后双栏 + sidebar | 26 | 保留；水位差落位（How-11）进旁白 |
| §5.5 调度域 | layers | 27 | 保留 |
| §6.2 线程多的赢 + C7 | spotlight + sidebar | 28 | C7 定义压进 sidebar 与旁白 |
| §6.3 cgroup 树 + 03-cgroup-tree 图 | pics/03-cgroup-tree.png | 29 | 整图保留 |
| §6.4 两个旋钮 / §6.5 没改什么 | ascii 双栏 + sidebar | 30 | 保留（How-12 数字） |
| §7.2 C8 | text + sidebar | 31 | 保留 |
| §7.3 回调表 + DSQ | layers | 32 | 保留 |
| sched_ext 最小实现 | Linux 6.12 tools/sched_ext/scx_simple.bpf.c L74–98 | 33 | 新增可复查源码；点出 vtime 夹到一片与水位同构 |
| §7.4 兜底表 | ascii 表 | 34 | 保留（How-13 看门狗 30 s） |
| §7.5 悬念 5 机制面 | 31、34 旁白 | 31–34 | 合并；历史面留 ep4 |
| §8 伪代码 demo | — | — | 未上屏：本集已有 5 段真源码，加上伪代码会超 15 分钟；其三件事汇合的内容已由 13–15、23 覆盖 |
| §9 朴素 vs 真实 | ascii 双栏 8 行 | 35 | 保留 |
| §10 三个误解 | text + sidebar | 36 | 保留（How-14 PREEMPT_RT 6.12 合入） |
| §11 约束回扣 | 各场景 sidebar 约束标注 + 35 右列 | 多处 | 分散保留 |
| §12 呼应灵魂问题 | 总结卡 + 预告 | 37–38 | 保留；「闭环 70%」类自评不进视频 |

## 相对原文的事实修正 / 口径
1. 原文 §2.1 只说「期限一栏钻源码时再展开」；本集按派工要求用一个三任务示例 + `update_deadline` 真源码讲清资格（lag ≥ 0）和期限。期限按「本片开始时的 v + slice 折算」表述，与 fair.c L1023 一致。
2. 片长：原文「基准约 3 ms」，按 How-5 精确为 0.75 ms × (1 + log2(min(核数, 8)))，8 核以上 3 ms、4 核 2.25 ms。
3. 时钟中断：按 Why-2 口径说「内核默认配置每 4 ms」，不说「主流发行版」。
4. 函数名：tick 处理用 6.12 的 `sched_tick()`（How-4），负载均衡用 `sched_balance_rq`（How-10）。
5. 原文 §3.6 写「把 prev 的被调用者保存寄存器压到 prev 的内核栈」并紧接 `ret`；6.12 源码实际以 `jmp __switch_to` 结尾（How-6），本集按源码讲。
