# ep1 What 覆盖与证据矩阵

输入原文 `cgroup核心原理-atlas.md` 第 87~1085 行（What 篇 §0~§10）+ 第 54~86 行约束速查。未改动原文、stages、原 SVG。
产物：`video-notes/ascii-src/cgroup-ep1-ep1-what.vmd`（29 场景，口播约 3400 字，估时约 11 分钟）、`pics/ep1-summary-card.json/png`。

主链：四次出事 -> 四把旧工具 -> docker 命令 -> 三个问题 -> 一句话定义 -> 两层 -> 合租公寓 -> 一个目录四个文件（实验 + 四种资源各触发一次）-> 数字是谁写的（五个环节 + 换算）-> 半颗核的含义（实验）-> runc 三个动作与先入组再 exec（实验）-> 全景图 -> 系统位置 -> 总结卡 -> 下集预告。

| 原文必讲项 | 画面载体 | 场景 | 处理 |
|---|---|---|---|
| §0.1~0.5 四次出事 + 四把工具四种单位 | text + ascii 表 | 2、3 | 保留；数字是设想场景，画面标题写「设想的场景」 |
| §0.6 docker run 命令、--cpus / -m 两段 | code_explain（标题含「示意」） | 4 | 保留；其余几段（-d、--name、镜像）在高亮里一句带过 |
| §0.6 systemd-run 同样落下两个数 | html_slide 01-shot-systemd.png | 5 | 保留，整图 |
| §0.7 四个问题 + 大问题 | text + sidebar | 6 | 压缩为系列统一的三个问题（四个问题里的第 3、4 个并入问题 2、3） |
| §1 一句话定义 + 三个动词 | text + sidebar | 7 | 保留；三动词对照表并入 sidebar |
| §1 两层（核心 / 控制器）+ C5 | layers + sidebar | 8 | 保留；因为 -> 要解决 -> 所以 的链用旁白讲 |
| §2 合租公寓类比 | ascii 双栏 | 9 | 压缩：9 行对照表缩成 7 行，七条推论只留对应关系；类比到此为止，不回扣 |
| §3 开头「怎么设计接口」的反问 | 旁白 | 10 | 保留，并进实验设计 |
| §3.1 实验设计（组、入组、专用实验机） | text + sidebar | 10 | 保留；先讲设计与预期，再上命令 |
| §3.2 内核认得 9 种资源 | code_explain 实测（原文 289~290 行） | 11 | 保留；其余 5 个控制器只说「共 9 个」，不逐个讲 |
| §3.3 一个目录四个 .max 文件、刚建好是 max、cgroup. 开头文件属于核心 | code_explain 实测（原文 307~315 行） | 11 | 保留；`cd ... ; cd /tmp` 那行去掉行尾的 `; cd /tmp`，其余逐行取自原文 |
| §3.4 四个文件各写一个数 | code_explain 实测（原文 327~330 行，去掉行尾注释） | 12 | 保留；四行逐行高亮 |
| §3.5 四种资源各触发一次 + db 对照 | html_slide 01-shot-quad.png | 13 | 保留，全部数字（999370、137、oom_kill 1、3.00754、0.0092556、325 倍、第 20 次 fork 失败） |
| §3.6 写法一样、超了办法不同（C2） | ascii 双栏 + sidebar | 14 | 保留 |
| §4.1~4.2 五个环节 + 三个动作 | html_slide 01-docker-relay.png | 15 | 保留，整图；OCI、HTTP 请求的细节压缩 |
| §4.3 换算（0.5 -> 50000 100000、512m -> 536870912）+ C3 | ascii 换算 + sidebar | 16 | 保留；表格里的 1.5、2 颗核等例子不上屏；moby 源码（Go）不是 Linux 副本，不上屏 |
| §4.3.1 0.5 颗核不是把核切开 + 01-half-core-timeline | text（实验设计）+ html_slide | 17、18 | 保留，整图；「你的视角」对话体改写成直接陈述 |
| §4.3.2 实验 1（2.05 / 4.20 / 42 个周期） | html_slide 01-shot-half-one.png | 19 | 保留 |
| §4.3.2 实验 2、3 前半（探针 50/50、12.5/87.5） | html_slide 01-shot-probe.png | 20 | 保留；「cpu.max 记的是时间」结论并入旁白 |
| §4.3.2 实验 3 后半（四任务 55.58 s）、实验 4（占空比 5%）、小结表 | 01-shot-four.png、01-shot-duty.png | 未上屏 | 压缩：这两组实验的异常值，原文给的原因是推断、没有证实（待核 #8），按规则不讲；小结表里「保证 / 不保证」的主要几条已在 18、20 的旁白里 |
| §4.3 内存换算、swap 默认翻倍 | ascii 换算后半 | 16 | 内存换算保留；`memory.swap.max` 不展开 |
| §4.4 runc 三个动作 + 先入组后 exec + 62 个文件 | timeline | 21 | 保留；cgroup 驱动对比表（systemd / cgroupfs）压缩掉，只保留 system.slice 下建目录 |
| §4.4.1 事后写主进程、worker 跟不跟 + 组籍规则 | ascii 双栏 + sidebar | 22 | 保留；「组籍」第一次出现时用一句白话解释 |
| §4.4.1 实跑 join-1（400% / demo 账 0） | html_slide 01-shot-join-1.png | 23 | 保留 |
| §4.4.1 实跑 join-2（51.0%、33 个周期、49983 μs） | html_slide 01-shot-join-2.png | 24 | 保留；cgroup.kill 一句话不讲 |
| §4.4 对照表（命令 -> OCI 字段 -> 文件） | 图 15、16 | 15、16 | 合并 |
| §4.5 自己验证（docker inspect、/proc/pid/cgroup） | — | — | 未上屏：原文标为待核 #1，docker 命令没在实验机上跑过 |
| §4.6 手边只有 Mac / Lima / 虚拟化对照 | — | — | 未上屏：属于环境搭建，与「cgroup 是什么」无关，留在文档；01-shot-env.png 一并不用 |
| §5 全景图 01-overview + 六条读法 | html_slide 01-overview.png | 25 | 保留，整图；读法压缩为：树、容器不特殊、一格一上限、system.slice 合计 |
| §5「为什么只有一棵树」的悬念 | — | — | 压缩掉（留给第 2 集 v1 / v2） |
| §6 位置：上面管理程序，下面四条代码路径，接入点 + C4 | ascii + sidebar | 26 | 保留；接入点第一次出现时用一句白话解释 |
| §6.1 worker 一生六个时刻 | — | — | 压缩：只在场景 26 点出 fork、调度器结算、缺页、提交 IO 四条路径；逐一过 worker 一生留给第 3 集 |
| §7 cgroup 不是什么（namespace / ulimit / nice / 虚拟机、不等于容器） | — | — | 未上屏：为控制到 11 分钟取舍；ulimit / nice 的差别已在场景 3 讲过，namespace 与虚拟机的区别留在文档 |
| §8 关键词速查 | — | — | 未上屏：文档保留；核心、控制器、组籍、接入点在出现处各讲一句 |
| §9 留下的悬念 | text | 27 | 压缩为三个问题各还缺什么 |
| §10 呼应灵魂问题 | text + sidebar（五条约束名） | 27 | 保留；约束名按系列统一说法写成「编号·短名」 |
| 本集总结 | html_slide ep1-summary-card.png | 28 | 新增 |
| 下集预告 | spotlight | 29 | 新增 |

终端留档图（-shot-）9 张：上屏 6 张（systemd、quad、half-one、probe、join-1、join-2）；未上屏 3 张（four、duty：见上；env：见上）。手绘图 3 张（docker-relay、half-core-timeline、overview）全部上屏。

## 相对原文的事实修正

无。（原文标为推断或待核的内容：实验 4 的原因（待核 #8）、docker 的 --device-write-bps / --pids-limit（待核 #9）、docker 验证命令输出（待核 #1），都没有进旁白。）
