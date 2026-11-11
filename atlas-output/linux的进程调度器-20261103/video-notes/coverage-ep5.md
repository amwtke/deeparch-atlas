# ep5 Deep 覆盖与证据矩阵

主角色：源码路径（Deep）；输入原文 `linux的进程调度器-atlas.md` 第 1639–2565 行（Deep 篇 §0–§7）+ 第 53–100 行约束速查 + 第 3763–3863 行收尾核实（#23~#29 以核实结论为准）。源码全部取自 `video-notes/src/` 下 Linux v6.12 副本（jsDelivr gh/torvalds/linux@v6.12），code_explain 由脚本按行号截取，逐字连续子串；未改动源 MD、stages、原 SVG。

主链：开场 -> 三件事 -> 鸟瞰图 -> 主线一（实验设计 -> update_curr 记账 -> update_deadline 到期 -> 为什么不当场换 -> 出口检查点 -> 三个安全点 -> __pick_next_task 快路/慢路 -> context_switch 三步 -> __switch_to_asm 两条 movq -> 换栈全景图 -> 进程 = 栈 + 寄存器 + 页表根 -> 十个寄存器去哪 -> rax 信使 -> copy_thread 伪造帧 -> 子进程第一次醒来 -> 父子 rsp 判别表 -> 反事实）-> 主线二（两租户算例 -> pick_task_fair 下行 -> 上行记账 -> 带宽池与闸）-> 主线三（链接脚本 -> scx_simple -> balance_one 三道闸 -> 两层看门狗 -> 拆除三步 -> 为什么先 bypass -> 装载时也 bypass -> 反事实）-> 三本账并列 -> 总结卡 -> 预告 Comparison。

| 原文必讲项 | 证据载体 | 场景 | 处理 |
|---|---|---|---|
| §0 三件事 + 表 | layers + sidebar 约束 | 3 | 保留 |
| §1 鸟瞰图 05-overview | pics/05-overview.png 整图 | 4 | 保留，按三框解说 |
| §2.1 节首结论（三段） | spotlight | 5 | 保留 |
| §2.2 操作层观察点 + 05-switch-demo 三场景 | text（实验设计，不在本机跑） | 6 | 保留；schedstat/perf 计数列为画面 |
| §2.3.1 task_tick_fair / update_curr | v6.12 kernel/sched/fair.c L1216–1257 `update_curr` | 7 | 原文为删节版，换成真源码 |
| §2.3.1 update_deadline + base_slice 0.75 ms | v6.12 fair.c L1007–1028；fair.c:76 | 8 | 保留 |
| §2.3.1 resched_curr 只置标志 | update_curr 高亮 5 + 旁白 | 7 | 合并（core.c:1079 在 HIGHLIGHT 注明） |
| §2.3.1.1 反问：为什么不在中断里当场 schedule（三样冻不得） | ascii 双栏 + sidebar | 9 | 保留三条；BUG scheduling while atomic、irq_stack.h 行号压缩为一句 |
| §2.3.2 exit_to_user_mode_loop | v6.12 kernel/entry/common.c L90–102 | 10 | 原文为删节，换真源码 |
| §2.3.1.1 三个出口检查点 + TIF_NEED_RESCHED 存在理由 | text + sidebar | 11 | 保留 |
| §2.3.2 __schedule（锁、nvcsw/nivcsw、pick、nr_switches） | 旁白 + 场景 12 | 12 | 压缩：__schedule 不单独上屏，计数器差别由场景 6 承担 |
| §2.3.2 __pick_next_task 快路 + scx_enabled + 类链 | v6.12 kernel/sched/core.c L5952–6002 | 12 | 换真源码 |
| §2.3.2 pick_eevdf eligible + deadline、RUN_TO_PARITY | 场景 12 高亮 + 旁白 | 12 | pick_eevdf 只讲判据；RUN_TO_PARITY 未上屏（并入「少换人」C4 叙述） |
| §2.3.3 context_switch 三步 | v6.12 core.c L5272–5332 | 13 | 换真源码 |
| §2.3.3 __switch_to_asm | v6.12 arch/x86/entry/entry_64.S L177–216 | 14 | 原文删了 stack protector / RSB 填充，这里保留真源码全段，旁白只讲 push/movq/pop |
| §2.3.3 __switch_to 收尾（FS/GS、FPU、current） | 场景 14 高亮 5 | 14 | 压缩 |
| §2.4 05-context-switch 图 | pics/05-context-switch.png（scroll auto） | 15 | 保留，按左栏/中栏/右下解说 |
| §2.4 为什么 6 个寄存器 / 页表根单独换 / 每任务一根栈 | spotlight 16 + 场景 17、22 | 16–17, 22 | 保留 |
| §2.4 纳秒账单分段 | 场景 15、22 旁白 | 15, 22 | **只讲总量**：核实 #24 分段数字未核实，旁白用公开实测 1.2~2.2 μs 总量与「间接几十 μs」；图上分段数字保留在原图里不念 |
| §2.5 你的视角：进程 = 栈 + 寄存器（纠为三样） | spotlight | 16 | 保留；task_struct 是账本不是身份 |
| §2.5.1 反问：另外 10 个寄存器 | ascii 表（四层去处） | 17 | 保留 |
| §2.5.2 反问：A 怎么知道是 C 让的（rax 信使） | timeline 五个时刻 | 18 | 保留 |
| §2.6 copy_thread 伪造帧 | v6.12 arch/x86/kernel/process.c L171–234 | 19 | 原文删节（只留用户线程路径），这里截真源码连续段，含 fsgs / shadow stack / 内核线程分支，旁白只讲高亮行 |
| §2.6 子进程第一次被选中五步 | timeline | 20 | 保留（ret_from_fork_asm movq %rax,%rdi 在 entry_64.S:240） |
| §2.6.1 反问：pt_regs 哪来的、rax 为何是 0 | 场景 19 高亮 3/4 + 旁白 | 19 | 合并 |
| §2.6.2 反问：父子 rsp 相同为何不踩 + 判别表 | ascii 表 | 21 | 保留表；copy_page_range / do_wp_page 的 memory.c 源码不上屏（mm 子系统，非本主题约束） |
| §2.7 反事实四候选 | text + sidebar | 22 | 保留 |
| §3.0 零基础垫脚：cgroup 目录树、为什么要它、css_set | ascii 目录树 + 算例 | 23 | 保留目录树与 C7 痛点；css_set「名册」一句未上屏 |
| §3.1 节首结论 / §3.2 cpu.weight cpu.max 算例 | ascii（实验 1、2 预期） | 23 | 保留；目录名改为 A/ B/ |
| §3.3.3 pick_task_fair 下行 | v6.12 fair.c L8848–8873 | 24 | 换真源码 |
| §3.3.1–§3.3.2 for_each_sched_entity 上行 + calc_group_shares | text + sidebar | 25 | calc_group_shares 公式以文字表达，不上屏源码 |
| §3.3.4 入队也要走链 | — | — | 压缩掉（原文细节，视频只保留上行/下行两向） |
| §3.4 带宽：领（5 ms 片）、闸、开 | v6.12 fair.c L5812–5828 `__account_cfs_rq_runtime` + 高亮 4 | 26 | 保留；throttle_cfs_rq / unthrottle / period too short 只讲结论 |
| §3.5 反事实四候选 | — | — | 压缩掉（篇幅）；结论「树的树 = 不加新算法」进场景 24 旁白 |
| §4.0 零基础垫脚：eBPF、sched_ext、DSQ、slice | 场景 27–28 旁白 | 27–28 | 合并；餐厅排号类比未用（本集无生活类比） |
| §4.1 / §4.3.1 链接脚本定序、sched_class_above | v6.12 include/asm-generic/vmlinux.lds.h L129–138 | 27 | 新增可复查源码 |
| §4.3.1 next_active_class 跳过 fair、static key 零成本 | 场景 12 旁白 | 12 | 压缩 |
| §4.2 scx_simple 三回调 | v6.12 tools/sched_ext/scx_simple.bpf.c L60–97 | 28 | 原文为删节合并版，换真源码；stopping 记账未上屏 |
| §4.3.2 balance_one 三道闸 + SCX_CALL_OP + 32 轮 | v6.12 kernel/sched/ext.c L2652–2717 | 29 | 换真源码 |
| §4.3.3 入队侧 do_enqueue_task、runnable_at | 场景 30 高亮 | 30 | 压缩为「runnable_list 上的超时」 |
| §4.4.1 两层看门狗 | v6.12 ext.c L3340–3374 | 30 | 换真源码 |
| §4.4.2 回退三步 | v6.12 ext.c L4469–4538 | 31 | 换真源码 |
| §4.4.3 反问：为什么先 bypass | ascii 双栏 | 32 | 保留锁序与活性；sched_ext_ops_helper 是 SCHED_FIFO 一条未上屏（已按 #29 更正口径不说它「也会被饿」） |
| §4.4.4 反问：装载时为什么也先 bypass | text + sidebar | 33 | 保留 |
| §4.5 反事实四候选 | text + sidebar | 34 | 保留 |
| §5 其余机制只给结论 | — | — | 压缩掉（ep3 How 已讲唤醒选核/均衡） |
| §6 约束回扣 | 各场景 sidebar + 场景 35 | 3, 35 | 合并为「三本账并列」 |
| §7 呼应灵魂问题 | 场景 35–36 | 35–36 | 压缩 |
| 本集总结 | pics/ep5-summary-card.png | 36 | 新增 |
| 预告 Comparison | spotlight | 37 | 保留 |

## 相对原文的事实修正

1. 原文写 `pick_next_task(core.c:6044)` 在没开 core scheduling 时就是 `__pick_next_task`。v6.12 副本里 core.c:6044 是 **CONFIG_SCHED_CORE 版**的 `pick_next_task`；不开 core scheduling 时的版本在 **core.c:6491**。视频只引 `__pick_next_task`（core.c:5952），未引 6044。
2. 原文 §4.3.1 贴的 `next_active_class` 只有「switched_all 跳过 fair」一句；v6.12 sched.h:2531 还有一句 `if (!scx_enabled() && class == &ext_sched_class) class++;`（没装 BPF 调度器时连 ext 也跳过）。视频未上屏该函数，不影响叙述。
3. `__switch_to_asm` 原文删去了 stack protector 和 `FILL_RETURN_BUFFER`；视频按 v6.12 原样展示（L177–216），pop 在 L208–213、`jmp __switch_to` 在 L215。
4. 纳秒账单分段（#24 未核实）：视频不念分段数字，只用总量 1.2~2.2 μs（公开实测旁证，Why-4）；原文「换栈本身约 20 ns」「每秒一万次 = 1.5~2%」未进旁白。
5. 「中断返回路上只隔几十纳秒」为原文估计，未进旁白，改成定性说法。
6. 其余行号（fair.c 1216/1007/306/4015/5812/8848/76/124，core.c 1079/5272/5328/5331/5952/6548，entry_64.S 177/190/191/227/240，process.c 159/175/176/231/232，ext.c 14/1084/2629/3313/3340/3356/4445，vmlinux.lds.h 129–138，scx_simple.bpf.c 60/74/95，ext.h:20 SCX_SLICE_DFL = 20 ms）已在副本中 grep 核对一致。

- （主控复审追加）原文 §2.5.1 写「rax、rcx、rdx、rsi、rdi、r8~r11 这 10 个」，实际列出的是 9 个 caller-saved 寄存器（16 个通用寄存器 = 6 个 callee-saved + 9 个 caller-saved + rsp）；视频第 17 场改为 9 个，并说明栈指针是被换的那一个。
