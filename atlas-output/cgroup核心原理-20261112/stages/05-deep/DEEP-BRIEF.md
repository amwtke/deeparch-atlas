# 第五节(源码)写作任务书

你负责写第五节 `05-deep.md` 里的一条主线(一个二级标题 §N)。另外两条主线和开头、结尾由别人写,所以**编号、术语、约束名一律照本文件**。本文件由主会话维护,不要改它。

## 1. 背景(必读)

这是一个四节已经写完的中文技术教学系列「cgroup 核心原理」的第五节:读源码。前四节:

- `stages/01-what/01-what.md`(是什么)、`stages/02-why/02-why.md`(为什么)、`stages/03-how/03-how.md`(怎么做:跟着一个 worker 走五个接入点,用 bpftrace 抓现行)、`stages/04-origin/04-origin.md`(怎么来的:四个人,二十年)。
- 读者:数据库背景的工程师,会写程序,没读过内核。前四节已经讲清「是什么、为什么、大致怎么做、怎么来的」。这一节要讲到函数和代码段。
- 三个灵魂问题:① 往 `cpu.max` 写 `50000 100000`,内核怎么让这组进程最多吃半颗核?② 容器 OOM 只杀容器里的进程,边界谁划的、账怎么记?③ cgroup 通过什么架构实现对各种资源的控制?怎么融入内核?设计哲学是什么?

**写之前必须读:**第三节里和你那条主线对应的小节(下面 §4 给了位置)、第四节里对应的人物小节,以及你那条主线的源码。

## 2. 五条约束(引用格式一律「编号·短名」,不许出现裸的 C1)

- `C1·按组限制合计用量`:单位是组;上限是绝对数;组套组,父组管整棵子树的合计
- `C2·记实际用量,超限处理看资源类型`:记物理页、真实 CPU 时间、真实 IO;能等的等,能拒的拒,内存只能回收或杀
- `C3·内核负责执行,配额由外部设定`:归属和上限进程改不了;谁该分多少由管理程序通过文件写进来
- `C4·在内核已有代码路径上记账,开销要小`:记账点挂在内核本来就要走的路上,必须便宜,不用的人几乎零成本
- `C5·所有资源共用同一套分组`:资源种类会增加,新增一种不惊动已有的;一笔开销跨几种资源,分组只能有一套

五句设计哲学:核心不认识资源 / 只搭车,不改道 / 记账即执法,没有巡查 / 内核只给机制,数字由外面写 / 少留自由。

## 3. 源码

- 上游 **v7.0**,本地副本在 `stages/05-deep/src/linux-v7.0/`(只下载了需要的文件;缺文件可以用 `curl -s https://raw.githubusercontent.com/torvalds/linux/v7.0/<路径>` 下到同一目录)。
- **引代码时写明「文件:行号」,行号以这份 v7.0 副本为准**,用 `grep -n` / `sed -n` 现查,不许凭记忆写行号或代码。
- 每段代码摘录 15 ~ 60 行,只摘关键段;可以删掉不相关的行,删的地方用 `/* ... */` 标出。摘录后逐段解释。
- 实验机内核是 Ubuntu 的 7.0.0-38,和上游 v7.0 可能有少量补丁差异;前几节抓到的函数名都在上游 v7.0 里能找到,可以对上。

## 4. 三条主线的分工

### §3 主线一:`cpu.max` 是怎么兑现的(对应灵魂问题 ①)

必须覆盖:
1. 写文件那一刻:`kernel/sched/core.c` 的 `cpu_max_write` → `tg_set_cfs_bandwidth`,两个数存进哪(`struct cfs_bandwidth`,`kernel/sched/sched.h:447` 起)。
2. 记账:`update_curr`(fair.c:1286)→ `account_cfs_rq_runtime`(fair.c:5738,**注意第 5740 行的两层开关:全局 static key `cfs_bandwidth_used()` + 每个 cfs_rq 的 `runtime_enabled`;这回答了第三节待核 #15**)→ `__account_cfs_rq_runtime`(5719)→ `assign_cfs_rq_runtime` / `__assign_cfs_rq_runtime`(5707 / 5679,一份 = `sched_cfs_bandwidth_slice()`,默认 5000 us,fair.c:125)。
3. 池空了:`throttle_cfs_rq`(6001)、`tg_throttle_down`(5978);**6.18 起的按任务限流**:`task_throttle_setup_work`、`throttle_cfs_rq_work`(5773)、`throttled_limbo_list`(sched.h:769)。讲清旧做法(整组 dequeue)与新做法的区别,引第四节 §5.4 的动机。
4. 周期定时器:`sched_cfs_period_timer`(6501)→ `do_sched_cfs_period_timer`(6253)→ `__refill_cfs_bandwidth_runtime`(5655)→ `distribute_cfs_runtime`(6165)→ `unthrottle_cfs_rq`(6042)。
5. 第三节实测对照:`03-how/src/logs/t1.log`(2 秒 1660 笔账、181 笔动公共池)、`t3.log`(时间线,7 个 worker 12.3 / 6.0 / 4.0%)、`t3n.log`(挂牌每秒 40 次与进程数无关)、`cost.log`(不设限 0 次)。用源码解释这些数字。
6. 反事实小试(5 ~ 6 个候选):例如每核独立额度互相借(Bharata 的 RT 式,第四节 §5.2)、只有一个全局池、整组 dequeue(6.18 之前)、给每个进程发信号停下、用 `nice`/权重代替上限、更大或更小的 slice。每个候选写:违反哪条约束、代价、现实里有没有人这么做(有就写出处)。结论一句话。
7. 一段可运行演示:指向 `03-how/src/prog/t3-throttle.bt` 和 `03-how/src/03-evidence-sessions.sh` 的 `t3` 会话,写出运行命令、预期输出(从日志摘)、以及演示里每个探针对应源码的哪一行。

### §4 主线二:内存的账与组内 OOM(对应灵魂问题 ②)

必须覆盖:
1. 记账入口:`__mem_cgroup_charge`(memcontrol.c:4755)→ `charge_memcg`(4739)→ `try_charge_memcg`(2355)。`MEMCG_CHARGE_BATCH`(去 `include/linux/memcontrol.h` 查定义,应为 64)、`consume_stock`(1841)/ `refill_stock`(1939)/ `struct memcg_stock_pcp`(1795)。第四节 §6.2 讲过 32 → 64 的历史。
2. 沿树往上记:`page_counter_try_charge`(mm/page_counter.c:118)逐层加、逐层比;失败时返回撞线的那一层(`fail` 参数)→ `mem_over_limit`。对照 `03-how/src/logs/t2.log`(三层同加 64)。
3. 撞线之后:`try_charge_memcg` 里的重试循环(2370 起的 `retry:`,`MAX_RECLAIM_RETRIES`、`try_to_free_mem_cgroup_pages`、`drain_all_stock`)→ `mem_cgroup_oom`(1706)→ `mem_cgroup_out_of_memory`(1673)→ `out_of_memory`(oom_kill.c:1119)→ `select_bad_process`(365)→ `mem_cgroup_scan_tasks`(memcontrol.c:1170)→ `oom_evaluate_task`(oom_kill.c:309)→ `oom_badness`(202,**写出打分公式,回答第三节待核 #6**)→ `oom_kill_process`(1024)。对照 `03-how/src/logs/t4.log`。
4. **重点:为什么有时多杀一个**(前几节的待核,第二节 #1、第三节 #5)。主会话已查清并实测,你负责写成一小节:
   - `oom_evaluate_task`(oom_kill.c:327-331):遇到「已经被选中、还没拆完」的受害者(`tsk_is_oom_victim` 且没有 `MMF_OOM_SKIP`),就 **abort**,这一轮不再杀人,等它死。这是防止多杀的那道闸。
   - 但 `mem_cgroup_scan_tasks`(memcontrol.c:1170)用 `CSS_TASK_ITER_PROCS` 遍历组里的进程;`css_task_iter_advance`(kernel/cgroup/cgroup.c:5113-5118)会**跳过「PF_EXITING 且 signal->live 已归零」的任务**(注释:"Hide tasks that are exiting but not yet removed")。
   - `do_exit`(kernel/exit.c:917 起):`exit_signals` 设 PF_EXITING,第 923 行 `signal->live` 减到 0,**之后**第 964 行 `exit_mm()` 才去拆内存;拆内存(`exit_mmap`)要几毫秒。
   - 于是有一个窗口:受害者已经开始退出(对遍历不可见,闸门看不到它),它的内存却还没还回去(账还是满的)。触发者这时再撞线、再进 OOM,就看不到受害者,挑了下一个。
   - 实测证据:`05-deep/src/logs/oomrace.log`(4 轮,每轮都印了每次进入 OOM 时的账、打分、选中、受害者开始拆 / 拆完的时刻)。例:第 1 轮 337 us 受害者 165274 开始 exit_mmap,472 us 第二次进 OOM 时只给 165275 和 165277 打分(165274 已不在遍历里),654 us 杀 165275;受害者 165274 要到 9079 us 才拆完映射。第 2 轮的反例:第 3 ~ 6 次进 OOM 都没有打分、没有杀人,因为第二个受害者 165303 还没进 do_exit(1743 us 才开始拆),闸门挡住了。
   - 留档图:`05-deep/pics/05-shot-oomrace.svg`。
   - 写明:这是按源码与实测得出的解释;上游有没有人讨论过、有没有修,没有查(记待核)。
5. 反事实小试(5 ~ 6 个):例如不批量、每页都改计数器;只记本组不沿树记(父组单独统计);超限直接拒绝分配返回错误;超限立刻 OOM 不先回收;全机统一 OOM 不分组;OOM 时整组一起杀(`memory.oom.group`,第四节 §6.3);受害者开始退出后仍对遍历可见(多杀问题的一种修法,标明是假设)。
6. 一段可运行演示:`05-deep/src/prog/oomrun.sh` + `t12-oomrace.bt`(会话 `oomrace`),写出运行命令、预期输出、探针与源码行的对应。

### §5 主线三:骨架,组籍与登记表(对应灵魂问题 ③,第二条主线)

必须覆盖:
1. 结构:`struct css_set`(cgroup-defs.h:272)、`struct cgroup_subsys_state`(179)、`struct cgroup`(472)、`struct cgroup_subsys`(772,**这就是「登记表」:列出它的回调成员,并对照 `03-how/src/logs/table.log`**)。三个控制器各自填的表:`cpu_cgrp_subsys`(core.c:10244)、`memory_cgrp_subsys`(memcontrol.c:4698)、`pids_cgrp_subsys`(pids.c:449)。用一张对照表写出每个控制器填了哪些格子(回答第三节待核 #14)。
2. fork:`cgroup_can_fork`(cgroup.c:6905,`do_each_subsys_mask(... have_canfork_callback)`)→ `pids_can_fork`(pids.c:273)→ `pids_try_charge`(166);`cgroup_post_fork`(6965,挂到父进程的 css_set,再按 `have_fork_callback` 叫人)。对照 `03-how/src/logs/t0.log`、`hooks.log`、`pids.log`。
3. 入组:写 `cgroup.procs` → `cgroup_attach_task`(3020)→ `cgroup_migrate_execute`(2693,`can_attach` / `attach` 回调)→ `find_css_set`(1220)、`css_set_move_task`(919)。对照 `03-how/src/logs/fw.log`(组籍地址换了三次)。
4. 开控制器:写 `cgroup.subtree_control` → `cgroup_apply_control_enable`(3375)→ `css_create`(5792)→ 控制器的 `css_alloc`。对照 `fw.log` 的「建账」四行。
5. 退出:`cgroup_task_exit`(7061)、`cgroup_task_release`(7155);对照 `03-how/src/logs/exit.log`(pids 在收尸时才减一)。
6. 「核心不认识资源」的源码证据:核心代码里只通过 `ss->xxx` 回调和 `do_each_subsys_mask` 碰控制器,不直接调用任何控制器的函数(用 grep 举证,例如在 cgroup.c 里搜 `mem_cgroup` / `cfs_` 的出现次数)。「少留自由」的证据:v2 下 `/proc/<pid>/cgroup` 只有一行;`css_set` 里 `subsys[]` 每个控制器一格、`dfl_cgrp` 一个默认层级指针。
7. 反事实小试(5 ~ 6 个):例如进程直接指向 cgroup(没有 css_set)、每个控制器在 task_struct 里各放一个指针、控制器自己维护进程名单、核心直接调用各控制器的函数(不用回调表)、多棵树(v1)、在 fork 时不继承而由管理程序逐个指派。
8. 一段可运行演示:`03-how/src/prog/t0-fork.bt`、`t5-framework.bt`(会话 `t0`、`fw`),写出运行命令、预期输出、探针与源码行的对应。

## 5. 写法要求

- 节首先说结论(一段加粗的话)。每个小节先说「内核原本在做什么 / 这段代码要解决什么」,再贴代码,再逐段解释,再对照实测数字。
- 新概念首次出现用「因为 <约束> → 要解决 <问题> → 所以引入 <东西>」。约束引用一律「编号·短名」。
- 函数名、结构名第一次出现时用一句白话说它是什么。读者没读过内核。
- 实测数字必须从日志复制,写明出自哪个日志;不许编数字。
- 照实交代:没读到、没验证、推断的地方都要写明,并在你那部分末尾列一个「本小节新增待核」清单(编号用 D1、D2……,主会话合稿时统一编号)。
- 不用「值得注意的是」「本质上」这类套话;少用破折号;中文标点;代码、命令、函数名用反引号。
- 每个关键机制后面一张「没有它会坏在哪 / 它解决了」的小表。
- **篇幅:你那条主线 180 ~ 260 行(含代码)。** 整份文档要控制在 900 行左右。
- 可以引用前几节的章节号(第三节 §7.2 这种写法);可以嵌 `05-deep/pics/` 下的图(写成 `pics/05-shot-xxx.svg`),**不要嵌别的节的图**,要提就用文字引用。

## 6. 交付

- 写到 `stages/05-deep/_build/` 下:主线一写 `part-3.md`,主线二写 `part-4.md`,主线三写 `part-5.md`。从 `## §3 ……`(或 §4、§5)二级标题开始。
- 不要跑任何实验,不要用 `limactl`,不要改别的文件,不要做 git 操作。
- 交回简短报告(15 行以内):小节标题清单;引用了哪些源码位置;用到了哪些日志数字;新增待核;没把握的地方。
