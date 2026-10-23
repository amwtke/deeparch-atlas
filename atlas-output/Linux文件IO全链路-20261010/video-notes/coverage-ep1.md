# ep1 What 覆盖与证据矩阵

主角色：全景 / 心智模型。输入原文 `Linux文件IO全链路-atlas.md` 第 103–393 行（What 篇）与第 45–102 行约束速查；未改动源 MD、stages、原 SVG。

主链：同一行 read 两种命运（命中/未命中）→ 一句话定义（往下翻译、往上送回）→ 图书馆类比（角色映射 + 失效边界）→ 五层全景图 → 货物交接 → 文件概念止于 bio → 五层点名 + 接口表源码 → 硬件入门（HDD/SSD、AHCI/NVMe）→ 四对边界 → 思考题一（M×N→M+N、机制与策略 + 默认调度器源码）→ 思考题二（缓存坐标）→ 两个窄腰 → 分叉点与 epoll/io_uring 位置 → 总结卡。

| 原文必讲项 | 证据载体 | 场景 | 处理 |
|---|---|---|---|
| 一句话定义（往下翻译 / 往上送回） | text + 具体例子 | 3 | 保留 |
| 图书馆调书类比 + 三条性质 | analogy（复用 vfs-library-route，mode: warehouse）+ text | 4–5 | 保留；补类比失效边界（DMA 直送、服务台不出人） |
| 全景图 01-overview | pics/01-overview.png | 6 | 整图保留，自上而下解说 |
| 交接货物表（7 个交接点） | timeline | 7 | 保留 |
| 「文件」概念只活到第 ② 层 | spotlight | 8 | 保留，表述为「到 bio 就消失」 |
| 五层各是谁 + page cache 旁路 | layers | 9 | 保留 |
| VFS 定接口 / ext4 给实现 | Linux 6.12 fs/ext4/file.c L929–948 真源码；对照 net/socket.c L154–157 | 10 | 原文无源码，新增可复查证据 |
| 硬件入门 HDD vs SSD | text + 例子 | 11 | 保留 5~10 ms / 几十 μs / 约 100 倍 |
| AHCI vs NVMe | ASCII 双栏 | 12 | 保留 1×32、约 6.5 万队列 × 约 6.5 万命令、PCIe、门铃 |
| DMA 与中断（回程） | 3 的例子、6 的图、7 的第 7 步 | 3、6、7 | 合并讲，不单列场景 |
| 关键词速查表 | — | — | 文档保留（术语已在 7、9 中出现） |
| 边界几对（含块设备词义、socket 平行链路） | text + 例子 | 13 | 保留 |
| 思考题一：去掉块层 | spotlight + ASCII 双栏（M×N vs M+N） | 14–15 | 保留；NVMe none 反例、IP 层窄腰 |
| 机制与策略分离 + 派生好处 | text + Linux sysfs 观测例子；Linux 6.12 block/elevator.c L562–572 真源码 | 16–17 | 保留；叠插层（LVM/md/dm-crypt/cgroup）文档保留 |
| 思考题二：缓存为何按（文件，页号） | spotlight + ASCII 双栏 | 18–19 | 保留：服务无盘文件系统、翻译费与循环依赖、空洞、换块、mmap；buffer cache 2.4 统一留给 Origin 集 |
| 两个窄腰对照 + 共享内存页 | layers | 20 | 保留，引出 mmap 零拷贝 / O_DIRECT |
| 分叉点 + epoll / io_uring 位置 | ASCII 竖链 + 侧标 | 21 | 只标位置；epoll_ctl 对普通文件 EPERM |
| 呼应灵魂问题 | 总结卡旁白 | 22–23 | 保留，下集预告 Why |

源码版本：Linux v6.12（jsDelivr gh/torvalds/linux@v6.12），本地副本在 video-notes/src/：
- fs/ext4/file.c L929–948 `ext4_file_operations`（逐字摘录，tab 保留）
- block/elevator.c L562–572 `elevator_get_default`（逐字摘录）；L746–772 `elv_iosched_show` 用于核实 sysfs 输出格式（方括号标当前调度器）
- net/socket.c L154–157 `socket_file_ops.read_iter = sock_read_iter`（只在高亮与旁白中引用）
- include/linux/fs.h L2107–2114 FOP_* 能力位注释；io_uring/rw.c L753 检查 `FOP_BUFFER_RASYNC`

事实修正与收紧：
- 原文「NVMe 默认把调度器关成 none」收紧为 6.12 的真实条件：硬件队列多于 1 条且不共享 tag 的设备默认不挂调度器；单硬件队列设备（典型 SATA 盘）默认 mq-deadline；驱动可用 BLK_MQ_F_NO_SCHED_BY_DEFAULT 主动声明不要。
- 原文 page cache 的位置在两处写法不一（全景「挂在 ② 旁」、窄腰表「① ② 之间」）；视频统一说成「挂在文件系统旁、查缓存发生在 ext4 算块号之前」，不给编号区间。
- 类比补出失效边界：真实回程是 DMA 直写内存加中断通知，图书馆里没有对应人手。

验收：23 场景、9 种视觉类型（spotlight 5、text 5、ascii 4、layers 2、html_slide 2、code_explain 2、title 1、timeline 1、analogy 1）。口播（含 example）2653 字，估时 2653÷5.4 + 23×1.5 + 3 ≈ 529 秒，约 8.8 分钟（实际以 TTS 为准）。`vmd_lint --theme anthropic`：0 错误、4 告警（两段源码 3 段高亮的 CODE-MULTI-HL；两个 spotlight 标题序号 14、23 触发的 NUM-RECAP 误报）。旁白与朗读例子无 atlas、无场景类型术语、无免责/制作用语；正文与侧栏无黑名单豆腐字符（箭头、带圈数字已替换）。总结卡 pics/ep1-summary-card.png 1920×1080 已目检无溢出。本集无人物场景。
