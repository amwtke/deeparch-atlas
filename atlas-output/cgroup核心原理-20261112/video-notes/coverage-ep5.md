# ep5 Deep 覆盖与证据矩阵

输入:`cgroup核心原理-atlas.md` 第 4915~6057 行(Deep 篇 §0~§7 + 待核清单)。vmd:`video-notes/ascii-src/cgroup-ep5-deep.vmd`,41 场景。源码全部取自 `stages/05-deep/src/linux-v7.0/` 副本的连续行,标题写明出处。未改动源 MD、stages、原 SVG。

| 原文必讲项 | 画面载体 | 场景 | 处理 |
|---|---|---|---|
| §0 三件事 + 约束来源 | layers + sidebar(C1/C2/C4/C5) | 2 | 保留;三件事表压成三行 |
| §1 全景图 05-overview | pics/05-overview.png(html_slide) | 3 | 整图保留,按时间线、三个框、底栏逐区讲 |
| §2 worker 一生:实验设计 | text | 4 | 保留 |
| §2 worker 一生:时间线 | pics/05-shot-life.png | 5 | 终端留档图,讲 fork 询问、64 页、限流、OOM 的关键数字;逐行表和算例压缩 |
| §3 报幕 | spotlight | 6 | 保留 |
| §3 原理:公共池 + 每核本核额度 | ascii 双栏 | 7 | 保留;1660/181 来自 §3.5 |
| §3.1 写入口 tg_set_cfs_bandwidth | code_explain core.c 9540-9565 | 8 | 保留;cpu_max_write(core.c:10177)只在旁白点到,不单独上屏 |
| §3.2 两层开关 + 记账 | code_explain fair.c 5719-5744 | 9 | 保留 |
| §3.2 领额度 + 5 ms + 透支 | code_explain fair.c 5686-5703 | 10 | 保留;「5181」来自 t3.log |
| §3 限流全过程 | statemap | 11 | 新增串联场景 |
| §3.3 pick_task_fair + check_cfs_rq_runtime | code_explain fair.c 8955-8970 | 12 | 保留;check_cfs_rq_runtime 在旁白讲,没单独上屏 |
| §3.3 6.18 前后对比表 | ascii 双泳道 | 13 | 保留;400 进程 4000 次来自 t3n |
| §3.3 throttle_cfs_rq_work | code_explain fair.c 5787-5815 | 14 | 保留 |
| §3.4 周期定时器 + distribute_cfs_runtime | code_explain fair.c 6197-6209;定时器并入旁白 | 15 | 合并;do_sched_cfs_period_timer 与 slack 定时器没单独上屏(slack 路没实测) |
| §3.5 数字对照表 | 15、7 旁白 | 7、15 | 压缩:只保留 1660/181、48532 对 50000 |
| §3.6 反事实小试 | 7 的原理段 | 7 | 压缩:只留「每核各一份」「单一全局池」两条的理由 |
| §3.7 演示脚本与探针表 | — | — | 未上屏:为控制时长;数字已在 5、7 中引用 |
| §4 报幕 | spotlight | 16 | 保留 |
| §4.1~§4.2 沿树记账 + 64 页预领 | ascii 三层框图 | 17 | 保留;t2.log 959→1023 等数字上屏 |
| §4.2 page_counter_try_charge | code_explain page_counter.c 142-154 | 18 | 保留 |
| §4.1 consume_stock / refill_stock | 17 旁白 | 17 | 合并:只讲预领 64 页和 25660 对 400,函数没单独上屏 |
| §4.3 try_charge_memcg 回收 / drain / OOM 重试 | code_explain memcontrol.c 2407-2425 | 19 | 合并:重试 16 轮、mem_cgroup_oom 返回 true 的含义进旁白,OOM 调用段不单独上屏 |
| §4.3 oom_badness 打分 | code_explain oom_kill.c 227-237 | 20 | 保留;77763 / 2416 来自 life.log |
| §4.4 报幕 | spotlight | 21 | 保留 |
| §4.4 两条规则各自的理由 | ascii 双栏 | 22 | 保留,先讲为什么合理 |
| §4.4 oom_evaluate_task 防重复检查 | code_explain oom_kill.c 321-331 | 23 | 保留 |
| §4.4 遍历器跳过退出中的进程 | code_explain cgroup.c 5112-5118 | 24 | 保留 |
| §4.4 do_exit 的先后 | code_explain exit.c 918-923 | 25 | 保留 |
| §4.4 空档 | ascii 双泳道 | 26 | 新增:把两条规则放进一条时间线 |
| §4.4 实验设计 | text | 27 | 保留 |
| §4.4 oomrace 日志 | code_explain lang=bash(原文 5580 命令 + 5530~5540 日志) | 28 | 保留,逐行取自原文 |
| §4.4 四轮留档 | pics/05-shot-oomrace.png | 29 | 保留;数字按图(3、3、3、2) |
| §4.4 三遍 12 轮统计与逐轮表 | — | — | 压缩:不上屏逐轮表,只讲界线 |
| §4.5 反事实小试 | — | — | 未上屏:为控制时长 |
| §4.7 三种改法 + 数据库类比 | ascii 三框 + 旁白 | 30 | 保留;数据库类比一处 |
| §5 报幕 | spotlight | 31 | 保留 |
| §5.1 四个结构 | layers + sidebar(C5) | 32 | 保留 |
| §5.1 css_set | code_explain cgroup-defs.h 265-278 | 33 | 保留 |
| §5.1~§5.2 登记表 + 各控制器填格子 | code_explain cgroup-defs.h 773-795 | 34 | 保留;五控制器逐格表没上屏,旁白讲 cpu 一个 fork 格子都没填 |
| §5.2 pids 登记表全文 | — | — | 未上屏:为控制时长 |
| §5.3 fork:can_fork / post_fork | code_explain cgroup.c 6910-6920 | 35 | 保留;pids_try_charge 和 pids.log 数字进旁白,post_fork 没上屏 |
| §5.4 入组 cgroup_migrate_execute | code_explain cgroup.c 2701-2729 | 36 | 保留;find_css_set 哈希共享一句话带过 |
| §5.5 开控制器 subtree_control | — | — | 未上屏:为控制时长 |
| §5.6 退出 + 更正 | code_explain cgroup.c 7061-7083 | 37 | 保留,按更正后的说法 |
| §5.7 grep 证据 | text | 38 | 保留,含「不是零」三类 |
| §5.8 反事实小试 | — | — | 未上屏:为控制时长 |
| §6 约束回扣 | ascii + sidebar | 39 | 压缩成五条约束一行对应 |
| §7 呼应灵魂问题 | 5、29、40 总结旁白 | — | 合并进总结卡 |
| 总结 | pics/ep5-summary-card.png | 40 | 新增 |
| 下集预告 | spotlight | 41 | 新增 |

## 相对原文的事实修正

- §5.6 原文已更正的一处,视频按更正后讲:`cgroup_task_exit` 只按登记表调用 `exit`,摘名单在 `do_cgroup_task_dead`(场景 37)。场景 5 的 life 留档图里仍是旧标签,图内带有更正注记。
- §4.4 原文前后两处界线说法不一致(前面「`exit_mmap` 开始」,后面更正为「进 `do_exit`、`signal->live` 归零」),视频只用后者(场景 25、26、28)。
- 场景 29 的击杀数用留档图(oomrace.log 第三遍:3、3、3、2),原文 §4.4 表格用的是第一遍(3、2、3、3);旁白只引图上的数。
- 原文标为推断或待核的内容(97 ms 间隔、`cpulimit`、OOM reaper 未参与、`cgroup_task_dead` 时点等)没有进入旁白。
