# ep2 覆盖与证据矩阵

主角色：原理 / 机制（约束推导）；输入原文 Why 行 394–923，约束速查行 45–102。未读取或复用其他集文件。

主链：开机 512 字节引导程序（没有任何一层）→ 一刀全切、从硬件往上逐层补回（驱动 → 块层 → 文件系统 → page cache → VFS）→ 每幕浮现的约束 C1~C12 → 收成五根 R1~R5、每层至少两根 → 区分约束与目标 / 策略 / 解法 → 两条 insight（五次坐标变换；异步填 C2、缓存填 C9）→ 预告 How。

| 原文必讲项 | 证据载体 | 场景 | 处理 |
|---|---|---|---|
| 开场：引导程序（实模式、512 字节、int 13h、LILO、GRUB 分级） | 文字 + 例子 | 2–3 | 保留；0x7C00 地址只留在原文 |
| 五幕总路线（一刀全切 → 加一层 → 露新痛点） | 六步节点演化图 | 4 | 保留 |
| 第一幕：三种盘三种语言、异步、特权态 → 驱动；C1 C2 C3 | ASCII 三栏 + Linux 6.12 nvme_mq_ops 源码 | 5–6 | 保留；用真实源码验证「块层定表、驱动填表」 |
| 第一幕例子：NVMe vs MegaRAID 两份 blk_mq_ops | 源码符号核对（scsi_mq_ops、megasas_queue_command） | 6 | 压缩为「SCSI 盘填另一份」；RAID 5 细节文档保留 |
| 第二幕：M×N → M+N、并发、设备上限、介质形状；C4 C5 C6 | ASCII 双栏 | 7 | 保留 |
| 第二幕例子：合并 / 切分 / 多队列 / 调度器按盘选 | 文字 + 三条例子 | 8 | 保留 dd 切分、32 队列、none vs mq-deadline；叠插层（LVM / dm-crypt）文档保留 |
| 第三幕：裸盘数据库重新发明文件系统；映射存盘上、跨块不原子；C7 C8 | 报幕 + 时间线 + ASCII 双栏 | 9–11 | 保留 notes.txt 五步、块 81922 → 扇区 655376 的换算 |
| 「你的视角：文件系统 = 格式化建索引」与「快是第二位」次序 | — | — | 文档保留（时间顺序在 Origin 集展开） |
| R5 展开：日志五步、环形日志区、flush + FUA、校验和 | 状态链 | 12 | 保留 |
| 三种 data 模式、与 InnoDB 对照、doublewrite、两层 WAL、COW / f2fs | 文字 + 例子 | 13 | 保留默认 data=ordered 的保证边界、doublewrite、两层 WAL、另两种形状；三档对照表文档保留 |
| 第四幕：速度断崖数字、局部性、grep 两遍；C9 | 文字 + 例子 | 14 | 保留 |
| 命中 / 未命中 / 预读、O_DIRECT 分叉 | ASCII 双泳道 | 15 | 保留，并按 6.12 校正未命中路径（见下） |
| 写延迟回写、30 秒、fsync；C10 | 文字 + 例子 | 16 | 保留 |
| 第五幕：cat 五样东西、f_op 分派；C11 | ASCII 五泳道 | 17 | 保留 |
| C12：file 与 inode 分离、fork 共享偏移 | 文字 + 例子 | 18 | 保留，shell 例子按事实校正（见下） |
| 「一切皆文件」先理念后 VFS、伪文件系统谱系、ioctl / netlink 旁门 | 时间线 | 19 | 保留；debugfs、tracefs、bpffs 文档保留 |
| 根约束 R1~R5、每层至少两根 | 分层图 | 20 | 保留 |
| 每层主责表、ext4 换 xfs 思考题 | ASCII 表 | 22 | 合并进「坐标变换」场景：一对多是函数指针表，多对一是普通 API |
| 这些不算约束（目标 / 策略 / 解法 / 约定 / 历史选择） | 文字 + 例子 | 21 | 保留目标、策略、解法三类；「4 KiB 页」「单内核」两行文档保留 |
| Insight 1 五次坐标变换 | ASCII | 22 | 保留 |
| Insight 2 两道断崖两种填法 | ASCII 双栏 | 23 | 保留，并为 epoll / io_uring 埋伏笔 |
| 约束 → 化解 → 代价表 | 总结卡 + 各幕旁白 | 5–23、24 | 代价分散到各幕；完整表文档保留 |
| 呼应：page cache 是解法不是约束，数据库 O_DIRECT 的落点 | 例子 | 21 | 保留 |

源码：Linux v6.12，`drivers/nvme/host/pci.c` 第 1710–1720 行（nvme_mq_ops），经 jsDelivr `gh/torvalds/linux@v6.12` 获取，存于 `video-notes/src/drivers__nvme__host__pci.c`；制表符按 8 列展开为空格，其余逐字一致（脚本比对 MATCH）。另核对符号：`drivers/scsi/scsi_lib.c` 第 2025 行 scsi_mq_ops（.queue_rq = scsi_queue_rq）；`drivers/scsi/megaraid/megaraid_sas_base.c` 第 1786 行 megasas_queue_command、第 4088 行 megasas_isr（经 kernel.org cgit 获取）；`include/linux/nvme.h` 第 837 行 nvme_cmd_read = 0x02；`pci.c` 第 876 行 nvme_queue_rq、第 1080 行 nvme_irq。

事实修正：
1. 原文「shell 里 cmd1; cmd2 > log 两条命令顺序追加到同一文件」不成立：这样写只有 cmd2 被重定向。改为用花括号把两条命令包起来一起重定向，两条命令才共享同一个打开文件。
2. 原文第四幕表格写「未命中 → 调 ext4 的 read_folio」。Linux 6.12 的 filemap 读路径在缓存未命中时先走 page_cache_sync_ra 预读，由 ext4 的 readahead 读盘，read_folio 只是兜底。画面与旁白改为「交给预读逻辑分配页，ext4 readahead」；顺序读时窗口放大，默认上限 128 KiB。
3. 伪文件系统时间线只保留 procfs 1992、sysfs 2003、cgroupfs 2008、pidfs 2024 四个节点；bpffs 随 Linux 4.4 于 2016 年 1 月发布，原文「2015」写的是开发年份，未上屏。

人物：本集不放人物场景。类比：本集未使用类比场景。

验收：25 场景，10 种视觉类型（spotlight 3、title 1、text 7、adv_animation 1、ascii 7、code_explain 1、timeline 2、statemap 1、layers 1、html_slide 1）。旁白含 example 共 3528 字，按 5.4 字/秒加每场 1.5 秒缓冲加 3 秒估计约 694 秒，即 11.6 分钟（实际以 TTS 为准）。总结卡 pics/ep2-summary-card.png 为 1920×1080，已目视核对无溢出。`vmd_lint --theme anthropic` 0 错误、1 条 CODE-MULTI-HL 告警（源码场景按要求分 3 段高亮）。旁白与例子无 atlas、无场景类型名、无免责与制作用语、无 markdown 符号。未修改原文 MD、stages、原 SVG 或其他集文件；未渲染、未提交、未上传。
