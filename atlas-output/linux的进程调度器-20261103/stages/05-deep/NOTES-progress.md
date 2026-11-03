# 05-deep 阶段审计(供合并进 PROGRESS.md「Deep 阶段」小节)

### Deep 阶段
- 对齐(自答,2026-11-03):聚焦三条主线 ① EEVDF 挑人全程 ② 多核唤醒选核与周期均衡 ③ cgroup 层级份额与带宽;源码钉 Linux v6.12(scratchpad 副本逐一 `grep -n` 核对行号);demo = 本机可跑的 Python 模拟器 + Linux 专用 C demo(未验证)+ bpftrace;ns 时间线只做主线①;每条主线反事实 4 ~ 6 候选;附录(rt / dl / 抢占模型 / sched_ext / EAS / core scheduling / NUMA / autogroup)只给机制 + 行号;反问改选择式并每个紧跟《从头走一遍》自答
- 三个判据:① eligible ∧ deadline 最早,lag 守恒(`fair.c:907` + `:5266`)② 搬人只在"差距过 117% 迟滞且只搬一半 ∧ 不热(500 μs)"(`:11048` + `:9260`)③ 整组按周期借 5 ms 片、借不到整组下树、定时器补池放回(`:5772` + `:5915` + `:6518`)
- 2026-11-03 初稿写入 stages/05-deep/05-deep.md + pics/05-overview.svg、05-timeline.svg、05-balance.svg、05-bandwidth.svg(xmllint 通过)+ src/05-eevdf-sim.py(本机 `python3 -I` 跑过四个场景)+ src/05-demo.c(`clang -fsyntax-only` 通过;Linux 分支未验证)+ src/05-sched-trace.bt + src/README.md
- 行号核对声明:所有 `file:line` 来自 v6.12 原文 `grep -n`;贴出的源码段为原文节选加中文行内注释;模拟器实现对应 19 个函数(文件头列表)
- **模拟器 vs How 的对账**:How §3.6 五拍表全部复现(V 1203.942 / 1207.885 / 1205.261 / 1209.856,redis 放回 v 1204.761、dl 1205.083,lag 守恒读数 +0.500),差异仅四舍五入;How §14 "redis 连跑约 64 ms" 复现(t = 1 → 65 ms);**How §14 分岔三「mysqld 也有资格」不成立**(两实体 Σ w·lag = 0,mysqld lag −5.995);**How §5.5 两处要改**:MC 层 imbalance = 2 但 `CONFIG_PREEMPTION` 下 newidle 只搬 1(`fair.c:9607`),PKG 层走 `migrate_util` = 1024 而非"~2 个 load 单位";**How §7 `fair_server` "逐步接替 95% 阀"** 无 6.12 依据(两者并存,server 默认 50 ms / 1 s)
- 关掉 How 的待核:#13(PELT 常数 `sched-pelt.h:13 ~ :14`)、#14(NUMA imbalance_pct 117)、#19(7 ~ 10 μs 取下限 6.5 ~ 7.5 μs)、#21(dl 准入与 rt 比值共用)、#26(§3.6 数字)
- 待核:#70 ~ #90(见 05-deep.md 末尾);其中 #72 / #73 / #74 需要回头 patch How §14 / §5.5 / §7;#75 `PREEMPT_LAZY` 版本、#77 `scx_bpf_dsq_insert` 改名版本、#76 k8s weight 公式、#86 sched_ext 用户 需要 web 核
- 反问(选择式)三道各自答:§2.6 两 nice 0 任务 B 睡 20 ms 醒来 lag 记成 +6(夹紧)、立刻抢、连跑 12 ms 后 4 ms 轮换;§3.6 绑核 redis 的 rq7 会被 newidle 拉进 PG(答 B;`avg_idle` 是真实旋钮);§4.6 period 改 10 ms 后 `nr_throttled` 每秒 +100(答 B;看 `throttled_usec / nr_periods`)
- 未做:真机数据(用户 macOS);NUMA / EAS 真实数字;`pick_eevdf` 增广搜索正确性证明

## 需要 How patch 的三处(请主控执行)
1. 03-how.md §14 从头走一遍·分岔三:删除"mysqld 也有资格(它落后 V)",改为"两实体时 Σ w·lag = 0,mysqld 的 lag = −9.3 × redis 的 lag,没资格;redis 是唯一候选";结论 64 ms 不变(模拟器 t = 1 → 65 ms)
2. 03-how.md §5.5 第 1 步:"搬 2 个" → "imbalance 算出 2,但可抢占内核下 newidle 搬 1 个就 break(fair.c:9607),剩下的留给下一次";第 2 步:"算出要搬 ~2 个 load_avg 单位" → "PKG 层无 SD_SHARE_LLC,走 migrate_util,imbalance = 本组算力余量 1024"
3. 03-how.md §7 末段:"它正在逐步接替上面那个 95% 的阀(待核 #18)" → "它和 95% 的阀在 6.12 里并存:阀限 rt 最多 95%,server 保 fair 至少 5%(默认 50 ms / 1000 ms,deadline.c:1637)";待核 #18 改为"已核(并存)"

## Comparison handoff(对照应镜像的三条主线)
- 主线① 挑人:Linux = eligible ∧ 最早 deadline(`fair.c:907`),权重管份额、slice 管延迟、lag 管资格、夹紧 ±2 slice;对照 NT 的 32 级优先级 + 提升(boost)+ 量子(quantum)—— NT 用"优先级临时加分"做延迟,Linux 用"lag 有界"做延迟;NT 的 quantum ↔ slice,NT 的 decay ↔ update_deadline
- 主线② 搬人:Linux = 每核 rq + wake_affine 偏 prev + 分层 pull + 500 μs 热门槛 + 可抢占内核 newidle 只搬 1;对照 NT 的 ideal processor / 每核就绪队列(Win7+)/ 空闲处理器搜索 / 无周期均衡(NT 靠唤醒时选核,几乎不做周期 pull)
- 主线③ 组:Linux = task_group 同形一行 + cfs_bandwidth 周期池 + 整组停;对照 NT 的 Job Object CPU rate control(整 job 限,也是周期制)+ DFSS(按会话分份额)+ SQLOS 协作式(C1 的另一种答案)
- 可直接引用的数字:3 ms slice / 4 ms tick / ±6 ms lag 上限 / 117% 迟滞 / 500 μs 热门槛 / 5 ms 借片 / 100 ms 周期 / 87.5 ms 停 / 6.5 ~ 7.5 μs 唤醒链 / 95% rt 阀 / 5% fair_server

## Synthesis handoff(五元组候选决策,带 § 引用)
| 决策 | 本篇 § | 反事实候选(已写) | 现实对照线索 |
|---|---|---|---|
| 只按账挑人,不猜类型 | §2.2.4 / §2.5 | A2 CFS 启发式、A5 BVT warp | NT 的 boost 就是"猜" |
| 份额 / 延迟 / 资格三个数 | §2.2.1 ~ §2.2.3 | A3 彩票、A4 stride | — |
| lag 夹紧 ±2 slice + 守恒放大 | §2.2.3 / §2.6 | "+4 不夹紧 120 ms 不换人"的模拟 | — |
| 树按 deadline 排 + min_vruntime 增广 | §2.2.4 | 扫一遍(C4) | — |
| tick 只标记、出口换 | §2.3 | — | — |
| DELAY_DEQUEUE 睡眠不能逃债 | §2.2.6 | 6.11 以前存负 lag | — |
| 每核一本账 + 唤醒偏 prev | §3.2.1 / §3.5 | B1 全局树、B3 每次放最闲 | NT ideal processor |
| 分层 pull、差距一半、500 μs 热 | §3.2.2 / §3.3 | B2 无 task_hot、B4 push、B5 不分层 | NT 几乎不做周期 pull |
| 同 LLC 按个数、跨 LLC 按算力 | §3.4 | — | — |
| PELT 32 ms 半衰期 | §3.2.3 | — | — |
| 组是同形一行、权重按本核负载分摊 | §4.2.1 / §4.2.2 | C3 只停超额线程 | NT job / DFSS |
| 带宽 = 池 + 每核借片 + 整组停 + 周期补 | §4.2.3 / §4.5 | C1 按核数、C2 无封顶、C4 无 burst、C5 用 dl | NT Job CPU rate control |
| 类栈凌驾 + 95% 阀 + 5% server + PI | §5.1 / §5.2 | — | NT 31 级 realtime 无阀 |
| 挑人规则可替换(sched_ext) | §5.4 / A6 | — | 十年赌注候选 |
