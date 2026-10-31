# ep7 Synthesis 覆盖与证据矩阵

主角色：综合 / 决策（方法论收官）；输入原文 `Linux进程全链路-atlas.md` 第 3649–4137 行（Synthesis 篇 + 待核汇总 + 收尾核实），约束速查与灵魂问题第 1–103 行；未改动源 MD、stages、原 SVG。

主链：./hello 走完一辈子（锚点）→ 换一套约束会长成什么样（本质问题）→ 六种证据只剩印象（旧方案）→ 五元组 / 判别法 / 五步法（模型）→ 四行五元组过筛 + 取消约束形状就退 + 必然偶然分账（推导）→ fair.c 时间片系数源码验证第 7 行（源码）→ 十一条洞察 + 三个同构 → MVCC 对两阶段锁离题验证 → 时代局限 + 十年赌注 + 七约束落点（边界与迁移）→ 回到灵魂问题。

| 原文必讲项 | 证据载体 | 场景 | 处理 |
|---|---|---|---|
| §0 三件事：五元组 / 判别法 / 五步法 | text + sidebar | 3–4 | 保留；三者关系“结果 / 读法 / 过程” |
| §1 概览图 | pics/07-overview.png | 5 | 整图保留；讲五步流水线、前六集各占哪步、MVCC 并排 |
| §2.1 五元组 14 行 | 第 4 行 fork+exec（ascii 五元组）、第 5 行 tick 打标记、第 7 行 slice（源码）、第 6 行级 vs 账（双栏） | 7–10 | 每行讲约束 / 代价 / 反事实 / 现实；第 1/2/3/8/9/10/11/12/13/14 行由洞察与落点场景覆盖（15–18、26、29），未单列 |
| §2.2 六次取消约束 | layers 六行（C3 unikernel、C4 NT 不超售/Cygwin、C2 SQLOS/Go 1.14 前、C5 DPDK、C7 Linux 0.01、向后兼容 spawn） | 12 | 保留 |
| §0.2 判别法 + §2.2 结论 | 必然 / 偶然双栏框图 | 13 | 保留“1969 年的形状、唯一同时过筛、只有偶然部分能修且付兼容债” |
| §3.1 一本账 / clone flags 是隔离级别 | text + 命名空间长出容器例子 | 15 | 保留；NT silo 反例文档保留 |
| §3.2 把复制变成异常 | 旁白 | 15 | 保留 |
| §3.3 约束一刀一条，对不到三四个组件是口号 | 五步法第一步旁白 | 21 | 合并进五步法，不单列 |
| §3.4 execve 先验后换再建、996 行 | layers + 旁白（binfmt_elf.c:996 `retval = begin_new_exec(bprm);` 已对 v6.12 核实） | 16 | 保留；padzero 修正与 ld.so 耗时留给 Deep 集 |
| §3.5 tick 只打标记 | text 五元组 + layers | 8、16 | 保留 |
| §3.6 switch_to 只存 6 个，约定者是 ABI | layers + 旁白 | 16 | 保留；NT 存 18 个反例文档保留 |
| §3.7 判据③ 独占才复用 | timeline 旁白 | 17 | 保留（mm/memory.c:3724 已核） |
| §3.8 fork 是 27 行汇编的偶然 | text | 18 | 保留 |
| §3.9 判据三轮补丁 | timeline 6 节点 | 17 | 保留 |
| §3.10 THP 拆 PMD 只拷 4 KiB | example | 18 | 压缩为一句“过期的常识” |
| §3.11 级 vs 账 | 双栏框图 | 10 | 保留 |
| §4 同构系统 JVM / KVM 与容器 / Git | 三行三列框图（收集者 / 推迟拷贝 / 还有谁在用） | 19 | 保留 JVM、Git 与 §4.4 三件零件；KVM 表文档保留，容器只在侧栏一句 |
| §5.1–§5.5 五步法每步实例 | 五状态推进 + 每步一句动作 | 20–21 | 保留 |
| §5.6 MVCC 对两阶段锁 | 约束 D1–D5 映射 C、K1–K5 代价、undo vs 堆内双栏、局部最优三次取消、长事务 = 没退出的子进程 / xmin = 离线 ref_count | 22–25 | 保留 |
| §6 时代局限 | layers 六行 | 26 | 保留 |
| §7 约束回扣 | C1–C7 各自落点 + C3/C4 主轴、C5 内核独有 | 29 | 保留；逐列表文档保留 |
| §8 呼应你的问题 | 收尾三句答案（不装载只映射 / 不复制只写保护 / 只守在门口） | 31 | 保留；六问逐条的必然偶然判定文档保留 |
| §9 十年赌注 | timeline 1993–2025 + spotlight “偶然的设计被挤回必然的角落” | 27–28 | 保留；四行比较表文档保留 |
| 待核汇总 / 收尾核实 / 延伸阅读 / Q&A 钩子 | — | — | 文档保留，不进口播；用到的核实结论见下 |

源码：kernel/sched/fair.c 第 191–220 行（`get_update_sysctl_factor` + `update_sysctl`），Linux v6.12（jsDelivr gh/torvalds/linux@v6.12），本地副本 video-notes/src/kernel/sched/fair.c，逐字一致（tab 保留）；第 70–77 行注释与 `sysctl_sched_base_slice = 750000ULL` 用于核对 0.75 ms。另核 fs/binfmt_elf.c:996、mm/memory.c:3724（副本同目录）。

事实修正与措辞收紧：
- 原文第 7 行“slice = 0.75 ms × (1 + log2 核数)”补出 6.12 真实条件：核数先与 8 取较小值，系数封顶 4，核再多时间片也封顶 3 ms。
- §3.8“1304 个 Debian 包调用 fork”无法在本集核到原句，口播与画面收紧为“上千个软件包”。
- §5.5 OCC 现实例子“Spanner / CockroachDB”未进视频：Spanner 读写事务用悲观锁（wound-wait），不宜作乐观并发例证；画面只写“冲突极少时最优”。
- Oracle 采用收尾核实结论：多版本读一致性 v4（1984）已有，v6（1988）换成库内回滚段；画面写“先有回滚段，Oracle v6，1988 年”。
- Redis fork 耗时口播用“一两百毫秒”（收尾核实：物理机约 9 ms/GB，20 GB 约 180 ms）。
- 窗口泄漏代价口播具体化为“多线程程序里 fork 只带走调用它的那一个线程”。

验收：31 个场景，9 种视觉类型（spotlight 6、text 6、ascii 6、layers 5、title 2、html_slide 2、timeline 2、code_explain 1、statemap 1）；无人物、无类比场景。旁白含 [example] 共 3872 字，估时 3872÷5.4 + 31×1.5 + 3 ≈ 767 秒，约 12.8 分钟（实际以 TTS 为准）。`vmd_lint --theme anthropic`：0 错误、3 告警（PATCH-NEW-CODE 选题误报；code_explain 三段高亮 CODE-MULTI-HL；“十一条洞察”报幕 NUM-RECAP）。旁白无 atlas、无场景类型术语、无 markdown；画面与侧栏无箭头、带圈数字、≠ 等豆腐字。总结卡 pics/ep7-summary-card.png 1920×1080 已目检无溢出。

分P标题建议：P7 Synthesis：不是最聪明的设计，是七条约束筛剩下的
主控修正：JDK 13 → JDK 12（JDK-8213192，ProcessBuilder 在 Linux 默认 posix_spawn 自 JDK 12 起）
