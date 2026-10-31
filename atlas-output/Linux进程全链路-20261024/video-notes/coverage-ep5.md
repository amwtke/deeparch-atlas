# ep5 覆盖与证据矩阵（Deep）

主角色：源码/实现。输入原文 Deep 行 2113–3306，约束速查行 46–103，收尾核实表行 4067–4118（Deep #1–#18 以核实结论为准）。未改动源 MD、stages、原 SVG。

主链：一次回车里的三个决定（能不能回头 / 换谁上台 / 拷还是不拷）→ 三个判据与全景图 → 主线一：先验后换再建（原理 ASCII 双栏在前）、第 996 行分水岭、bss 两段（原理在前）、elf_load、微秒时间账、反事实 → 主线二：EEVDF 两个数（原理在前）、update_curr / update_deadline / lag 与资格 / pick_eevdf、B 醒来的推演（place_entity 放大、醒来即裁决）、lag 一正一负的 ASCII 双栏、纳秒时间线、context_switch、__switch_to_asm → 主线三：copy on write 真实触发链（原理 ASCII 在前）、fork 侧写保护、五岔、第 3724 行判据、引用计数锁下验、wp_page_copy 四步、三轮演进、「谁先动谁 copy」对一半、THP 先拆再拷 → 约束回扣 → 总结卡 → 下集预告。

| 原文必讲项 | 证据载体 | 场景 | 处理 |
|---|---|---|---|
| §0 三个判据对照表 | layers + 口播 | 3 | 保留，行号用 v6.12 实物 |
| §1 概览图 05-overview | pics/05-overview.png | 4 | 整图保留，按三列 + 两处交汇解说 |
| §2.1 操作层旋钮表（ASLR / static / PIE / execstack / ulimit） | 场景 7 高亮第三段（PF_RANDOMIZE / setarch -R） | 7 | 只保留 ASLR；其余旋钮文档保留 |
| §2.1 execve 后 fd 保留、handler 重置、线程被杀 | 场景 7 高亮第二、三段 | 7 | 保留 de_thread 与信号重置；fd 继承文档保留 |
| §2.2 调用链 + load_elf_binary 四段 | ASCII 双栏（A 验 B 找 / C 换 D 建）+ fs/binfmt_elf.c 989–1017 | 6、7 | 保留；补 point_of_no_return 与 SIGSEGV 证据（exec.c 1243、1866–1867，未上屏） |
| §2.2 PT_LOAD 循环 | 口播「elf_map 最终调 vm_mmap，MAP_PRIVATE」 | 9 | 循环体文档保留，未上屏 |
| §2.2 elf_load 全文 + hello 对账 | text（原理）+ fs/binfmt_elf.c 400–445 | 8、9 | 保留；对账数字口语化为「五百多字节 / 四千多字节」 |
| §2.2 create_elf_tables 栈布局 / START_THREAD / sysret | timeline 第 5 行 + 场景 7 高亮第四段 | 7、10 | 压缩为一行 |
| §2.3 设计取舍表 + 时间数字 | timeline（§6 hello 时间表） | 10 | 保留；execve 写「一百到三百微秒量级」（Deep #1 未核，有旁证） |
| §2.4 反事实 A–D | text + 侧栏 + 例子 | 11 | 保留 A/B/C；D（posix_spawn）放例子 |
| §3.1 操作层旋钮（nice 权重 / base_slice / sched_runtime / HZ） | text 例子 + 场景 15 高亮 | 13、15 | 保留 nice 5/-5 折算、slice 3 ms、6.12 自定义 slice；autogroup / chrt 文档保留 |
| §3.2 update_curr | kernel/sched/fair.c 1216–1257 | 14 | 保留 |
| §3.2 update_deadline | kernel/sched/fair.c 1007–1029 | 15 | 保留，强调「时间片是请求长度」 |
| §3.2 vruntime_eligible + §3.6 lag 夹紧 | kernel/sched/fair.c 692–740 | 16 | 合并为一屏（entity_lag 夹紧 + 资格不等式） |
| §3.2 pick_eevdf | kernel/sched/fair.c 907–969 | 17 | 保留全函数 |
| §3.2 context_switch | kernel/sched/core.c 5294–5331 | 23 | 保留；finish_task_switch 的 TASK_DEAD 拆栈（core.c 5230–5237）写在高亮第四段 |
| §3.2 __switch_to_asm | arch/x86/entry/entry_64.S 177–216 | 24 | 保留 |
| §3.2 __switch_to | 纳秒时间线 T=1850 行 | 22 | 只列要点（FPU、TLS、current），未上屏 |
| §3.3 纳秒时间线 + 直接/间接代价 | timeline | 22 | 保留；口播直接 2–3 μs，间接改「几十微秒甚至更多」（What #5 核实为几十到上千 μs） |
| §3.3 四个 trade-off（出口换人、加权平均、PCID、FPU 延迟） | 场景 14、23 高亮 + 场景 24 口播 | 14、23、24 | 保留出口换人、PCID；FPU 延迟在时间线一行 |
| §3.4 反事实 机制 A（RR / CFS / 优先级老化 / 用户态 / EDF） | 场景 21 侧栏「短睡眠刷不了优先级」对照 CFS 漏洞 | 21 | 只保留 CFS 漏洞对照；其余文档保留 |
| §3.4 反事实 机制 B（硬件 TSS / 存 16 个 / 不存） | 场景 24 口播「六个就是下限」 | 24 | 压缩为一句；初稿的独立 text 场景为控时长删去 |
| §3.5 tick 到了换不换 | spotlight + place_entity 5341–5370 + check_preempt_wakeup_fair 8824–8846 | 18–20 | 保留；直接用夹紧后的 6 ms 推演（原文按 10 ms 写，正文自注夹成 6） |
| §3.5 RUN_TO_PARITY 三人反例 | 场景 17 高亮第二段 + 场景 21 侧栏 | 17、21 | 结论保留（只动 deadline 不动资格），三人数值反例文档保留 |
| §3.6 超前的 B 醒来 | ASCII 双栏（落后 6 / 超前 6） | 21 | 保留，含 12 ms 还账算式 |
| §4.1 操作层旋钮与观察点 | — | — | 文档保留（MADV_DONTFORK 等不在主链） |
| §4.2 #PF 分支树 + 五岔 | mm/memory.c 5765–5786 | 28 | 保留五岔；fault.c 入口文档保留 |
| §4.2 mm_account_fault | 场景 28 高亮第二段「记主缺页」 | 28 | 压缩；memory.c 5959 已核 |
| §4.2 do_wp_page | mm/memory.c 3703–3745 | 29 | 保留，第 3724 行为本集主判据 |
| §4.2 wp_can_reuse_anon_folio | mm/memory.c 3595–3630 | 30 | 保留，补「为什么不用映射计数」 |
| §4.2 copy_present_ptes（fork 侧） | 原理 ASCII + mm/memory.c 949–970（__copy_present_ptes 写保护） | 26、27 | 改上屏真正做写保护的 __copy_present_ptes；pin 页当场拷的分支（1037–1043）写在高亮与口播 |
| wp_page_copy（原文只给行号 3331） | mm/memory.c 3352–3424 | 31 | 新增上屏：分新页、拷 4KB、pte_same 复核、装新 PTE，满足「按真实触发链讲」 |
| §4.3 缺页耗时表 + Redis 算例 | 场景 31 口播「一到两微秒」+ 场景 33 例子 | 31、33 | 保留 COW 拷贝量级（有 2.3 μs 实测旁证）；Redis fork 写「一百到两百多毫秒」（Deep #14 核实范围） |
| §4.4 反事实 A–F | timeline 三轮演进 | 32 | 保留 C/D/E 三轮（mapcount → page_count → 独占位）；A/B/F 文档保留 |
| §4.5「谁先动谁 copy」对一半 | text + 侧栏 + 例子 | 33 | 保留三情形与「宁可多拷」；MVCC 对照留给第 7 集 |
| §5 附录预留专题表 | — | — | 文档保留（nice / cgroup / rt / deadline / NUMA 只在本集带过名字或不讲） |
| §5.1 THP 与 Redis | mm/huge_memory.c 1821–1850 | 34 | 保留；5.8 改语义、拆 PMD 只拷 4KB、残留毛刺 |
| §6 端到端时间线 | timeline | 10 | 保留 |
| §7 约束回扣 | layers | 35 | 保留三行 + 代价行 |
| §8 呼应你的问题 | 场景 2 开场与场景 36 总结首尾呼应 | 2、36 | 保留 |

源码版本：Linux v6.12，经 `https://cdn.jsdelivr.net/gh/torvalds/linux@v6.12/<路径>` 取得，存于 video-notes/src（文件名为路径以下划线连接）。上屏摘录 16 段，均为连续行，tab 保留；已用脚本逐段比对（整段等于副本对应行切片，且每一行都是副本的子串），16/16 通过：

| 场景 | 文件 | 行号 |
|---|---|---|
| 7 | fs/binfmt_elf.c | 989–1017 |
| 9 | fs/binfmt_elf.c | 400–445 |
| 14 | kernel/sched/fair.c | 1216–1257 |
| 15 | kernel/sched/fair.c | 1007–1029 |
| 16 | kernel/sched/fair.c | 692–740 |
| 17 | kernel/sched/fair.c | 907–969 |
| 19 | kernel/sched/fair.c | 5341–5370 |
| 20 | kernel/sched/fair.c | 8824–8846 |
| 23 | kernel/sched/core.c | 5294–5331 |
| 24 | arch/x86/entry/entry_64.S | 177–216 |
| 27 | mm/memory.c | 949–970 |
| 28 | mm/memory.c | 5765–5786 |
| 29 | mm/memory.c | 3703–3745 |
| 30 | mm/memory.c | 3595–3630 |
| 31 | mm/memory.c | 3352–3424 |
| 34 | mm/huge_memory.c | 1821–1850 |

旁证核对（未上屏）：fs/exec.c 1243 `bprm->point_of_no_return = true`、1866–1867 过点后出错 `force_fatal_sig(SIGSEGV)`；kernel/sched/fair.c 76 `sysctl_sched_base_slice = 750000ULL`、191–217 `get_update_sysctl_factor`（cpus 取 min(在线核数, 8)，对数缩放 1 + ilog2）、5578 `se->vlag = se->deadline`、1166–1196 `did_preempt_short` / `do_preempt_short`；kernel/sched/core.c 10012 `sched_prio_to_weight`（nice 5 = 335、nice -5 = 3121）、5230–5237 TASK_DEAD 拆栈、5584 `sched_tick`；arch/x86/kernel/process_64.c 582 `start_thread`、610 `__switch_to`；mm/memory.c 1037–1043 pin 页 fork 时当场拷、5959–5964 主次缺页记账。原文其余引用行号与 v6.12 一致。

事实修正（行号以 v6.12 实物为准）：
1. `update_deadline` 原文 §0 与 §3.2 写 `fair.c:1000`，实际函数在 1007 起（1000 是上方注释区；§3.5 写的 1007 正确）。
2. `pick_eevdf` 里「curr 不 eligible 就置 NULL」原文 §3.5 写第 926 行，实际在 921–922；RUN_TO_PARITY 第 928 行正确。
3. `check_preempt_wakeup_fair`：`update_curr` 原文 :8826 → 实际 8825；`pick_eevdf(cfs_rq) == pse` 原文 :8840 → 实际 8839；`resched_curr` 8845、撕保护 8834 正确。
4. `wp_can_reuse_anon_folio` 里 `lru_add_drain` 原文 §4.5 写第 3608 行，实际 3612（3607 是 `if (!folio_test_lru)`）。
5. `do_huge_pmd_wp_page`：独占早检原文 :1792 → 1793；引用检查 :1814 → 1821；锁下验 1 :1819 → 1826；`__split_huge_pmd` :1842 → 1849。
6. `__switch_to` 原文 `process_64.c:609` 是返回类型行，函数名在 610；`context_switch` 5271 同理（函数名在 5272），均不影响内容。
7. 原文 `__switch_to_asm` 摘录里的 Spectre 注释是作者改写；上屏版本为 v6.12 原注释（198–204 行）。
8. 纳秒时间线与 execve 耗时属量级估计（Deep #1、#4–#8 未核、有旁证），画面标题标「量级」，口播只给区间；间接代价按 What #5 核实结果写「几十微秒甚至更多」，未沿用原文「10~100 μs」上限。
9. padzero 触发缺页（Deep #3 未核）：口播按代码语义表述（往私有文件映射写、PTE 为空时走私有写缺页从文件页拷出一份），未当成实测。

人物：本集无人物场景。Linus、Arcangeli、Hildenbrand 只在三轮演进时间线与旁白中提名；Cutler 只在下集预告提名。未下载照片，未写 portrait-sources-ep5.json。

类比：未使用 story 插件，无生活类比。唯一对照是 MVCC，按原文留给第 7 集。

验收：37 个场景、8 种类型（code_explain 16、spotlight 6、text 4、ascii 3、timeline 3、layers 2、html_slide 2、title 1）；旁白 4429 字 + 朗读例子 344 字 = 4773 字，按 4773 ÷ 5.4 + 37 × 1.5 + 3 估计约 942 秒，约 15.7 分钟（以 TTS 实测为准）。`venv/bin/python scripts/vmd_lint.py --theme anthropic` 0 错误、18 告警：16 条 CODE-MULTI-HL（多段源码高亮，按要求保留）、2 条 NUM-RECAP（场景 18 标题序号、场景 37 旁白年份 1988 的误报）。旁白与朗读例子的 atlas 禁词、场景术语、markdown 标记检查均无输出；画面与侧栏无黑名单豆腐字符（箭头、带圈数字、不等号已替换）。ASCII 图三张按全角双宽对齐，最宽 67 列。总结卡 pics/ep5-summary-card.png 1920×1080 已目检无溢出。未改原 md、stages、原 SVG 与其他集文件，未渲染、未提交、未上传。

分P标题建议：P5 Deep：996、907、3724，三行源码定下进程的三个生死决定
