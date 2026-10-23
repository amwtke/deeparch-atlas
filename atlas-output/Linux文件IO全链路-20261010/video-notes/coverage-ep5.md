# ep5 覆盖与证据矩阵（Deep）

主角色：源码/实现。输入原文 Deep 行 2336–3277，收尾核实表行 4215–4242，约束速查行 1–102；示意代码 stages/05-deep/src/05-demo.pseudo.c 仅作调用链参考，未上屏。

主链：同一次 pread 首读约 94 微秒、再读不到 1 微秒 → 时间账（设备 85%）→ 主线 A：工单与查页、预读、read/mmap 汇合、一次拷贝的必要性 → 主线 B：页号到扇区、bio、tag、NVMe 命令与回程查表、背压与队列深度 → 主线 C：epoll 的就绪模型与 EPERM、io_uring 的先试不睡、页回调与 bio 回调、四条进步与收益边界、晚 25 年的原因 → 约束回扣 → 总结卡。

| 原文必讲项 | 证据载体 | 场景 | 处理 |
|---|---|---|---|
| §0 三件事 | 三主线 layers + 三个报幕 | 4、5、12、20 | 保留，压成三个问题 |
| §1 纳秒时间线 | pics/05-timeline.png | 2、3 | 整图保留；口播注明按稳态 128K 预读窗口算 |
| §2.1 操作层旋钮 | read_ahead_kb、fault-around、O_DIRECT | 8、10、11 | 只保留与读路径因果相关的三项；回写四阈值文档保留（写路径，非本集主链） |
| §2.2.1 kiocb + iov_iter | fs/read_write.c 478–493 | 6 | 保留，断言 -EIOCBQUEUED 与 ep 后段呼应 |
| §2.2.2 filemap_read 拷贝 | 时间账第 11 段 + 场景 11 | 3、11 | 保留结论，不单独上源码 |
| §2.2.3 filemap_get_pages 三级 | mm/filemap.c 2541–2560 | 7 | 保留；NOWAIT/WAITQ 返回 EAGAIN 的两刀 |
| §2.2.4 预读窗口 | mm/readahead.c 363–387 | 8、9 | 保留并修正为 4→8→16→32 |
| §2.2.5 mmap / fault-around | mm/memory.c 5171–5172（16 页）、filemap_fault 3301 | 10 | ASCII 双栏，未上 filemap_fault 源码 |
| §2.3 / §2.4 一次拷贝是局部最优 | 反事实三选项 | 11 | 保留 A/B 两个候选，sendfile 与大 folio 留在侧栏 |
| §3.2.1 ext4 造 bio | fs/ext4/readpage.c 342–366 | 13、14 | 保留，81922→655376→657424 算例 |
| §3.2.2 分区重映射 | block/blk-core.c 555–562 | 13 | 时间轴与口播保留，未上源码 |
| §3.2.3 blk_mq_submit_bio 分支 | block/blk-mq.c 2940–3041 | 13 | 时间轴一行带过（切分、合并、领 tag、plug/直发） |
| §3.2.4 tag 与背压 | block/blk-mq-tag.c 155–179 | 15、16 | 保留；先推导再验证；io_schedule 在第 188 行，口播说明 |
| §3.2.5 派发与完成核选择 | blk-mq.c 1192 | 19 | 例子保留"一核一队列就地完成，不发 IPI" |
| §3.2.6 nvme_queue_rq / 门铃 | drivers/nvme/host/pci.c 876–900 | 17 | 保留 |
| §3.2.6 回程按 CID 查表 | drivers/nvme/host/nvme.h 580–604 | 18 | 保留并修正 CID 结构 |
| §3.3 数字表 | 1024 / 2~4095 / BIO_MAX_VECS 256 | 14、19 | 保留深度与段数；mq-deadline 参数文档保留（第 3 集已讲调度器） |
| §3.4 时间线表 | 05-timeline.png | 3 | 由图承载 |
| §3.5 反事实 1、2、3、4 | 场景 15 例子、场景 19 | 15、19 | 反事实 2（不要 tag）与 3（深度）保留；反事实 1（bio/request 合并）文档保留，第 3 集已讲两者分工 |
| §4.0 epoll 解决什么 + 三个口子 | text + 例子 | 21 | 保留 |
| §4.1 操作层对照 | 05-epoll-vs-io_uring.png | 23 | 由图承载 |
| §4.2.1 epoll 三动作与 EPERM | fs/eventpoll.c 2262–2279；poll.h 75–77 | 22、23 | 保留 EPERM 源码；ep_poll_callback 由图承载 |
| §4.2.2 两个环 | 图 + 口播"同 NVMe 的一对门铃队列" | 23 | 保留同构 |
| §4.2.3 先试不睡 / 页回调 / io-wq 兜底 | io_uring/rw.c 849–873、740–763 | 24、25 | 保留；明确 6.12 上 ext4 未命中不占 io-wq，5.9 才加页回调 |
| §4.2.4 O_DIRECT 回调挂在 bio | fs/iomap/direct-io.c 733–750；include/linux/fs.h 392–394 | 26、27 | 保留；ASCII 双栏对比两条不睡的读路 |
| §4.2.4 两个推论（AIO 只对 O_DIRECT、IOPOLL 只支持 O_DIRECT） | 时间轴 2002 行；侧栏 | 26、29 | 保留为一行 |
| §4.3 必然还是偶然 | text | 30 | 保留"方向必然、年份与字段偶然" |
| §4.3.1 IOCP 对照 + 晚 25 年四因 | timeline 1977–2021 | 29 | 保留四因；IOCP 细节表交第 6 集 |
| §4.4 候选 A–E | 场景 30 例子 | 30 | 保留候选 E（全交 io-wq）；A/B/C/D 文档保留 |
| §5 约束回扣 | text + 侧栏 | 31 | 保留 |
| §6 呼应 | 场景 2 与 32 首尾呼应 | 2、32 | 保留 |

源码版本：Linux v6.12，经 `https://cdn.jsdelivr.net/gh/torvalds/linux@v6.12/<路径>` 取得，存于 video-notes/src。上屏摘录 11 段，均为连续行，已用脚本逐段做子串比对，与原文完全一致：

| 场景 | 文件 | 行号 |
|---|---|---|
| 6 | fs/read_write.c | 478–493 |
| 7 | mm/filemap.c | 2541–2560 |
| 9 | mm/readahead.c | 363–387 |
| 14 | fs/ext4/readpage.c | 342–366 |
| 16 | block/blk-mq-tag.c | 155–179 |
| 17 | drivers/nvme/host/pci.c | 876–900 |
| 18 | drivers/nvme/host/nvme.h | 580–604 |
| 22 | fs/eventpoll.c | 2262–2279 |
| 24 | io_uring/rw.c | 849–873 |
| 25 | io_uring/rw.c | 740–763 |
| 27 | fs/iomap/direct-io.c | 733–750 |

旁证核对（未上屏）：mm/memory.c 5171–5172 fault_around_pages = 65536 >> PAGE_SHIFT；include/linux/bio.h 13 BIO_MAX_VECS 256U；drivers/nvme/host/pci.c 67 / 74 NVME_PCI_MAX_QUEUE_SIZE 4095、io_queue_depth 1024；drivers/nvme/host/core.c 1101 command_id = nvme_cid(req)、985–986 REQ_RAHEAD → NVME_RW_DSM_FREQ_PREFETCH；include/linux/fs.h 369 ki_complete、392–394 is_sync_kiocb；fs/ext4/file.c 946 FOP_BUFFER_RASYNC；mm/readahead.c 573–578 初始窗口、643–646 顺序命中后 get_next_ra_size。原文其余行号与 v6.12 一致。

事实修正：
1. 预读窗口增长。原文 §2.2.4 与 §5 写"4 → 16 → 32"。按 get_next_ra_size，上限 32 页时 max/16 = 2，窗口 4 不小于 2，走翻倍分支，实际为 4 → 8 → 16 → 32。§0 表"初始 4 页翻倍到 32 页"本身正确。
2. NVMe 命令号结构。原文"CID 就是 tag"与"4095 是 16 位 CID 留一位给 AEN"不准确。v6.12 的 nvme_cid 把 4 位代数计数 genctr 放在高位、12 位 tag 放在低位；nvme_find_rq 拆出两者，代数不符即丢弃过期完成。深度上限 4095 来自 12 位 tag 字段（NVME_PCI_MAX_QUEUE_SIZE）。
3. 时间线图按稳态 128K 预读窗口计；首次未命中实际只预读 4 页。口播已注明，图未改。
4. 原文 §3.2.3 引 blk_mq_get_new_requests 为 L3003，实际函数体位于 blk-mq.c 2847 起；未上屏，不影响内容。

人物：本集无人物场景。Davide Libenzi 的照片检索只返回一张 YouTube 视频缩略图，无法确认本人，按规则不做人物场景，只在时间轴 2002 行与旁白提到姓名；Jens Axboe 只在时间轴 2019 行提到。未下载任何照片，未写 portrait-sources-ep5.json。

类比：未使用 story 插件。唯一的同构是 io_uring 两个环与 NVMe 提交/完成队列同形（场景 23），属技术同构。

验收：33 个场景、8 种类型（spotlight 5、title 1、html_slide 3、layers 1、code_explain 11、text 8、ascii 2、timeline 2）；旁白含 [example] 4548 字，按 4548 ÷ 5.4 + 33 × 1.5 + 3 估计约 895 秒，约 14.9 分钟。`venv/bin/python scripts/vmd_lint.py --theme anthropic` 0 错误、12 告警：11 条 CODE-MULTI-HL（多段源码高亮，按要求保留），1 条 NUM-RECAP（末场景标题编号 33）。旁白 atlas 禁词与场景术语检查均无输出。总结卡 pics/ep5-summary-card.png 已目检，无溢出。未改原 md、stages、原 SVG 与其他集文件，未渲染、未提交、未上传。
