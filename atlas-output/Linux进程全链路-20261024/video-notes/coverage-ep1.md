# ep1 What 覆盖与证据矩阵

主角色：地图 / 心智模型。输入原文 `Linux进程全链路-atlas.md` 第 105–425 行（What 篇）与第 46–103 行约束速查；事实以第 4067–4118 行收尾核实表为准（What #1 ~ #5）。未改动源 MD、stages、原 SVG。

主链：一个 hello 的一眨眼（具体锚点）→ 一句话定义（地址空间 + 执行流，两本账）→ 剧场类比（角色映射 + 失效边界：内核没有自己的舞台，伏笔 C5）→ 四条性质 → 全景图 01-overview → 内核里只有 task → 预测「共享 = 引用计数，隔离 = 复制地图不搬内容」→ copy_mm 源码验证 → 进程/线程/内核线程/协程/容器边界 → hello 四幕时间线 → ELF 一本两用 → execve 只画地图 → 三状态 → 三扇门一扇出口 → 缺页/COW/signal → exit/僵尸/wait → 旁观工具读账本 → CPU 五个开关 → 进程切换 vs 线程切换（四步 + TLB 账单）→ 两个钩子（PG vs MySQL、Redis bgsave）→ 同一个问题：地址空间 → 总结卡 → 下集 Why 预告。

| 原文必讲项 | 证据载体 | 场景 | 处理 |
|---|---|---|---|
| 一句话定义 + 两本账（mm_struct / task_struct） | text + example | 3 | 保留 |
| 剧场类比表 | ascii 双栏映射（剧场 / 内核） | 4 | 保留核心 7 行；补失效边界（内核无自己的舞台，只能借门进来） |
| 类比推出的 4 条性质 | text + example | 5 | 保留（ELF 代码页共享、PG 隔离、换场纯开销、递条子 = 系统调用） |
| 全景图 01-overview + 读图 5 件事 | pics/01-overview.png | 6 | 整图保留，横四幕竖三层解说 |
| 关键观察：内核里没有进程，只有 task（tgid） | spotlight + text | 7–8 | 保留 |
| 线程 = 同一地址空间的第二条执行流 | Linux 6.12 kernel/fork.c L1697–1733 `copy_mm` 真源码 | 9 | 原文无源码，新增可复查证据：CLONE_VM → mmget 共享；否则 dup_mm；current->mm 为空 = 内核线程；min_flt/maj_flt/nvcsw/nivcsw 清零与第四幕工具呼应 |
| 边界表：进程/线程/内核线程/协程/容器 | text + example | 10 | 保留；clone flags、active_mm 借页表、协程阻塞拖整条宿主线程、容器 = namespace + cgroup |
| 四幕各是谁 | timeline（hello 的一辈子 8 步） | 11 | 保留 |
| ELF 段表 / 节表 | ascii 双栏 | 12 | 保留 |
| fork + execve 两步；execve 不搬内容、重定位在 ld.so | text + example | 13 | 保留；补「execve 耗时与程序大小基本无关」（出自 03-execve 图注） |
| 三状态 + CFS → EEVDF（6.6） | statemap | 14 | 保留 |
| 三扇门一扇出口表 | ascii 竖图 | 15 | 保留 |
| 主/次缺页、COW 一句话、signal 一句话 | text + example | 16 | 保留；COW 按真实触发链讲（谁先写谁缺页，缺页处理里复制并改回可写） |
| 第三幕 exit → 僵尸 → wait、孤儿收养 | text + example | 17 | 保留 |
| 第四幕旁观工具表 | layers | 18 | 保留 6 行 |
| CPU 五个开关 + 速查表 | layers | 19 | 保留；旁白只展开 CR3 与时钟中断两个，其余在画面；ARM64 对应物文档保留 |
| 关键词速查表 | — | — | 文档保留（术语已在各场景出现） |
| 进程切换 vs 线程切换（四步表） | spotlight + ascii 双栏 | 20–21 | 保留；内核线程借 active_mm 进侧栏 |
| TLB 才是账单、PCID、数字量级 | text + example | 22 | 保留；KPTI 旁注删去（Why 集会讲系统调用代价） |
| 开场钩子一 PG vs MySQL | ascii 双栏 | 23 | 保留 |
| 开场钩子二 Redis bgsave 算例 | text + example | 24 | 保留 |
| 「你的视角」：两个钩子问同一件事 | spotlight | 25 | 保留；「没有进程的世界」第一反应留给 Why 集开场 |
| 最后的预留（nice/cgroup/vfork/大页） | — | — | 文档保留，本集不展开 |
| 呼应六问 | 总结卡旁白 | 26 | 保留「为什么非得这样一个都没回答」作 Why 钩子 |

源码版本：Linux v6.12（https://cdn.jsdelivr.net/gh/torvalds/linux@v6.12/kernel/fork.c），本地副本 `video-notes/src/kernel_fork.c`：
- kernel/fork.c L1697–1733 `copy_mm`（逐字摘录，tab 保留；已脚本比对与副本第 1697–1733 行完全一致）

事实修正与收紧（依收尾核实表）：
- What #1：Redis fork 耗时不写「10 多 ms/GB」，改为官方 `latest_fork_usec` 实测表：物理机约 9 ms/GB，老式 Xen 239 ~ 424 ms/GB（旁白说「慢二十多到四十多倍」）；20 GB 物理机 ≈ 180 ms。页表账 20 GB / 4 KB × 8 B ≈ 40 MB（524 万页）。
- What #2：COW 一次缺页 + 4 KB 拷贝写成「最坏约 2.3 微秒」（EuroSys'21 On-demand-fork 表 1）。
- What #3：fork 0.24 ~ 0.33 ms、建线程几十微秒（LKML 2004）；PG 新连接毫秒级成本的大头是 backend 初始化，不是 fork（侧栏「PG 大头：初始化」）。
- What #4：PCID 由 Linux 4.14 启用。
- What #5：切换直接开销写 Haswell 实测绑核 1.2 ~ 1.5 μs、不绑约 2.2 μs；间接代价「从几微秒到超过一千微秒」（原「几十 μs」已按核实改）。
- 剧场类比原本用 stage-actor-swap 动画插件，但该插件在 anthropic 主题触发 E-STORY-COLOR 错误（高反差色块 4.1%），改为 ascii 双栏映射表，未新建插件。

验收：27 场景、9 种视觉类型（text 9、spotlight 5、ascii 5、html_slide 2、layers 2、title 1、code_explain 1、timeline 1、statemap 1）。口播（含 example）3334 字，估时 3334÷5.4 + 27×1.5 + 3 ≈ 661 秒，约 11 分钟（实际以 TTS 为准）。`vmd_lint --theme anthropic`：0 错误、2 告警（code 场景 4 段高亮的 CODE-MULTI-HL；场景 25 标题序号触发的 NUM-RECAP 误报）。旁白与朗读例子无 atlas、无场景类型术语、无免责/制作用语；画面与侧栏无 → / 带圈数字。总结卡 pics/ep1-summary-card.png 1920×1080 已目检无溢出。本集无人物场景。

分P标题建议：P1 What：敲下 hello，一个进程的一辈子要走几站
