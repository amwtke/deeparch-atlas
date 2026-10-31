# ep3 How 覆盖与证据矩阵

主角色：机制路径（How）；输入原文 `Linux进程全链路-atlas.md` 第 801–1687 行（How 篇 §0–§15）+ 第 46–103 行约束速查 + 第 4067–4118 行收尾核实（以核实结论为准）。未改动源 MD、stages、原 SVG。

主链：敲下 ./hello → 三本账（mm+页表 / task+内核栈 / 每核 rq+出口检查点）→ 页表与 VMA 两本账 → 出生幕：fork 复制账本不复制页 → execve 七步只建地图、start_thread 改 ip/sp → ld.so 到 main → 活着幕：三扇门一扇出口 → 出口检查点源码 → 三处标记一处换人 → 调度类与 EEVDF → tick 到换人时间线 → __switch_to_asm 换栈即换流 → 两段现场与 ABI → 线程/进程切换与多核 IPI → 缺页四路与主次 → copy on write 触发链 → signal 记账与出口投递 → D 态 kill -9 → 死亡幕：do_exit 两段、僵尸与 wait → 旁观工具读账本 → 示意伪代码 → 三个误解 → 总结卡 → Origin 预告。

| 原文必讲项 | 证据载体 | 场景 | 处理 |
|---|---|---|---|
| 贯穿例子 hello.c | code（原文程序，注释精简） | 2 | 保留三个变量三种来源 |
| §0 三件事及约束来源 | layers + sidebar 约束 | 3 | 保留；两段现场挪到 26 讲 |
| §1 极简概览图 | pics/03-overview.png | 4 | 整图保留，按四幕三层讲 |
| §2.1 四级页表 + main 0x401136 算例 | ASCII 地址切分 + 四级链路框图 | 5 | 保留下标 0/0/2/1 + 偏移 0x136 |
| §2.2 五个 PTE 标志 / §2.3 CR3 与 TLB / §2.4 内核半区 | text + example（读内核地址被拒） | 6 | 合并；KPTI 两张 PGD 文档保留，不进视频 |
| §3.1 布局 + 03-layout 图 | pics/03-layout.png | 7 | 整图保留，自下而上解说 |
| §3.2–§3.3 VMA 字段、mm_struct 字段 | 图右栏 + 8 的 sidebar | 7–8 | 字段表压缩进图讲解 |
| §3.4 为什么两本账 | text + example | 8 | 保留四条逼问中的三条 |
| §4.1 fork 复制账本 | ASCII 双栏（父/子 + 共享物理页） | 9–10 | 先讲原理：只复制 VMA 与页表项、清写位、fd 表复制而 file 引用计数共享、子进程 rax=0；Redis 约 10 ms/GB |
| §4.1 fork/vfork/pthread/posix_spawn 旗标 | layers | 11 | 保留 |
| §4.2 ELF 一本两用 + 03-execve 图 | pics/03-execve.png | 12 | 段表五样、节表留给 ld.so 合并进图讲解；readelf 输出文档保留 |
| §4.3 execve 七步 | timeline | 13 | 保留；第 4 步按 6.12 改写（见修正 2） |
| §4.3 第⑦步 start_thread | Linux 6.12 arch/x86/kernel/process_64.c L529–552 `start_thread_common` | 14 | 新增可复查源码 |
| §4.3.1 不可回头点（三处拧紧） | text + example（ld.so 被删返回 ENOENT） | 15 | 保留结论：能验的提前验、建 VMA 只认当前 mm、de_thread 本就不可逆 |
| §4.4 段表到 VMA 对账表 | — | — | 文档保留（地址为示意值，原文待核 #1 未核）；VMA 约 20 条进 17 |
| §4.5 ld.so 到 main 七步 | timeline | 16 | 保留；GOT 首次写触发 copy on write |
| §4.6 再逼问 | 各场景旁白 | 12–16 | 合并 |
| 实测（time -v / strace -T / maps） | 实验设计 text，先推理后命令，Linux 预期 | 17 | 不在本机跑，给 Linux 预期与推理 |
| §5 三扇门 + 03-gates 图 | spotlight + pics/03-gates.png | 18–19 | 整图保留 |
| §5.1–§5.2 系统调用 vs 时钟中断 | ASCII 双泳道框图 | 20 | 保留；门③缺页并入 28 |
| §5.4 出口检查点 | Linux 6.12 kernel/entry/common.c L90–134 `exit_to_user_mode_loop` | 21 | 原文为伪代码，换成真源码；先讲预测再验证 |
| §5.5 内核抢占 preempt_count | 22 的 sidebar | 22 | 一句话保留 |
| §6.1 三处标记一处换人 + §6.1.1 schedule 回到调用者 | text + example（read 等盘） | 22 | 保留「中断上下文」→「中断返回路径」的纠正、「唯一拒绝不了的门」 |
| §6.2 rq、五个调度类、EEVDF 骨架 | layers | 23 | 保留；公式留给 Deep 集 |
| §6.4 tick 到换人时间线 | timeline | 24 | 保留；HZ=250 算例，间接代价按核实改为几十到上千 μs |
| §6.3 context_switch 四步 | Linux 6.12 arch/x86/entry/entry_64.S L177–216 `__switch_to_asm` | 25 | 新增真源码；四步表压进 27 的双栏 |
| §6.3.1 只存六个寄存器（ABI） | text + example | 26 | 保留两处纠正：约定方是 ABI、保存者是代码 |
| §6.5 线程 vs 进程切换 / §6.6 多核 | ASCII 双栏 + 跨核 IPI 框图 | 27 | 保留；PCID 4.14 |
| §7.1 缺页四路 + 主次 | ASCII 判定框图 | 28 | 保留六种情形（swap 一行文档保留） |
| §7.2 copy on write | statemap | 29 | 按真实触发链：谁先写谁在自己的缺页里分新页改映射；计数为 1 直接复用 |
| §7.3–§7.4 signal + ctrl-C 全程 | timeline | 30 | 保留 handler 不能调 printf 的原因；SIGKILL/SIGSTOP 不可拦进 31 sidebar |
| §7.5 D 态 kill -9 | ASCII 双栏（S/KILLABLE vs 纯 D） | 31 | 保留分岔点在 try_to_wake_up |
| §8.1 do_exit 六步 | spotlight + timeline | 32–33 | 保留「在别人的栈上拆我的栈」 |
| §8.2–§8.3 僵尸、wait4、托孤、多线程退出 | text + example | 34 | 保留 tini；线程组退出细节文档保留 |
| §9 旁观工具 | layers | 35 | 保留 7 行；perf / vmstat 文档保留 |
| §10 hello 一辈子 + 分支 | 分散在 10–34 | — | 主线已由全集覆盖，分支表文档保留 |
| §11 60 行伪代码 | code_explain，标题与旁白明说「示意伪代码，不是 Linux 源码」 | 36 | 摘取件③、fork、缺页三段（行文逐字取自原文，去掉类定义与注释） |
| §12 朴素 vs 真实 / §14 约束回扣 | 各场景 sidebar + 总结卡 | 3–35、38 | 合并，不单列表 |
| §13 三个常见误解 | text | 37 | 保留 |
| §15 呼应 | 总结卡 + 下集预告 | 38–39 | 指向 Origin |

## 源码摘录（全部逐行取自 Linux v6.12，副本在 video-notes/src/）

| 场景 | 文件 | 行号 | 核对 |
|---|---|---|---|
| 14 | arch/x86/kernel/process_64.c（start_thread_common） | 529–552 | 子串逐字一致（tab 保留） |
| 21 | kernel/entry/common.c（exit_to_user_mode_loop） | 90–134 | 子串逐字一致 |
| 25 | arch/x86/entry/entry_64.S（__switch_to_asm） | 177–216 | 子串逐字一致 |

旁证核对（未上屏）：fs/binfmt_elf.c L996 begin_new_exec、L1014 setup_arg_pages、L1167 elf_load、L1232 start_brk 赋值、L1235 load_elf_interp、L1276 create_elf_tables、L1304 arch_randomize_brk、L1336 ELF_PLAT_INIT、L1340 START_THREAD；arch/x86/include/asm/elf.h L156–170 elf_common_init 清零通用寄存器；kernel/sched/core.c L5274 context_switch（`!next->mm` 借 active_mm、switch_mm_irqs_off、switch_to）。

## 相对原文的事实修正

1. **execve 第④步**：原文写 `set_brk`；v6.12 已无该函数，elf_load 循环后在 fs/binfmt_elf.c L1232 直接 `mm->start_brk = mm->brk = ELF_PAGEALIGN(elf_brk)`，随机化在 L1304 `arch_randomize_brk`（create_elf_tables 之后）。视频写成「定堆的起点，加随机偏移」，不点函数名。
2. **通用寄存器清零**：原文把「其余通用寄存器清零」归给 start_thread；v6.12 中清零由 START_THREAD 之前的 `ELF_PLAT_INIT` → `elf_common_init` 完成，start_thread_common 只改 ip/sp/cs/ss/flags 与段寄存器。高亮按此写。
3. **切换间接代价**：按收尾核实 What #5，「几十 μs」改为「几十到上千 μs」。
4. **入口跳板栈**：按核实 How #2 为 4.15 起（视频未展开，只在 20 写「硬件换栈」）。
5. **fork 代价**：按核实 What #1 / Deep #14 说「每 GB 约十毫秒量级」，不用「9~13 ms/GB」精确区间。
6. **出口检查点**：原文 §5.4 是去掉旁支的伪代码；视频换成 6.12 真源码，额外可见 uprobe / livepatch 两个旁支，旁白只讲 NEED_RESCHED、SIGPENDING 与循环重读。

## 验收

- 场景 39 个，视觉类型 9 种：spotlight 5、code 1、layers 4、html_slide 5（四张 03 图 + 总结卡）、ascii 6、text 8、timeline 5、code_explain 4、statemap 1。无人物、无类比插件场景（遵守少用生活类比）。
- 口播（含 example）约 4750 字；估时 = 字数÷5.4 + 39×1.5 + 3 ≈ 940 秒（约 15.7 分钟，实际以 TTS 为准）。
- vmd_lint（anthropic，generic）：0 错误，5 条告警（4 条 CODE-MULTI-HL 多段高亮按要求保留；1 条 NUM-RECAP 为场景序号 18 的误报）。
- 禁词与场景术语检查：旁白无 atlas、无场景类型名；旁白无 markdown；画面无 → 与带圈数字。ascii 每行显示宽度 ≤ 63、≤ 21 行，框线逐行对齐已校验。
- 总结卡 pics/ep3-summary-card.png 已目检，无溢出。
- 未改动 atlas md、stages、原 SVG 与其他集文件；未渲染、未提交、未上传。

分P标题建议：P3 How：敲下 ./hello 之后，内核只动了三本账
