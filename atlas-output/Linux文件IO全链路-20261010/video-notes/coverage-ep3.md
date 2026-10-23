# ep3 覆盖与证据矩阵

主角色：机制路径（How）；输入原文 atlas md 第 924–1958 行（§0–§10）+ 第 45–102 行约束速查 + stages/03-how/src/03-four-ways.c。未读取旧 VMD。

主链：一次冷的 pread(fd, buf, 4096, 8192) 未命中 → 三件货物（file+inode / folio / bio→request）→ ① VFS 派活 → ② page cache 查页、预读、坐标翻译、造 bio → ③ 块层切分合并拿 tag、调度 → ④ nvme 填命令敲门铃 → ⑤ DMA + 中断 → 回程钩子逐层唤醒 → 四条分叉与边界。

| 原文必讲项 | 证据载体 | 场景 | 处理 |
|---|---|---|---|
| §0 三件货物及其约束来源 | 五层货物分层图 | 3 | 保留，C12/C9/C1 配 sidebar |
| §1 极简概览图 | pics/03-overview.png | 4 | 整图保留，按图讲五件事 |
| §2.1 VFS 四对象 + 逼问 1–5 | VFS 对象图 + text 例子 | 6–7 | 保留 file/inode 分离、函数表、C11/C12；dentry/super_block 逼问压缩进图与 sidebar |
| §2.2–2.3 pread 进入 VFS | vfs_read 源码 | 8 | 保留；修正调用链：经 new_sync_read 包 iov_iter 再调 read_iter |
| §2.4 socket 分叉 | 五条路矩阵 | 31 | 一句话保留，等就绪 vs 等完成留给第五集 |
| §3.1 page cache 对象 + 逼问 1–7 | page cache 结构图 + folio 状态位 text | 10–11 | 保留键选页号、XArray、四状态位、a_ops、extent、LRU；folio 历史细节压缩 |
| §3.2 filemap_read 查、等、拷 + 预读 | page_cache_sync_ra 源码 + 窗口 timeline | 12–13 | 保留并修正（见下：冷随机读只读 1 页） |
| §3.3.1 单位换算链 | 五个数换算图 | 14 | 保留，"位移/查表"二分 |
| §3.3.2 10300 算例 + dd/xxd 实证 | 实验设计 text + Linux 命令 | 15–16 | 保留，先讲设计再给命令和 Linux 预期；碎片 extent 变体放进例子一句 |
| §3.3.3–3.3.4 ext4_mpage_readpages 调用链与图 | pics/03-folio-to-bio.png + 源码 | 17–18 | 保留；图注明为顺序读稳态 32 页窗口 |
| §3.3.5 写方向 / §3.3.6 自举细节 | — | — | 文档保留，不进视频 |
| §3.5 O_DIRECT / mmap 拐出 | 双泳道图 | 33 | 保留 |
| §4.1 块层三对象 + 逼问 1–8 | pics/03-block-layer.png + text | 20–21 | 保留 bio/request/tag/plug/limits；request_queue 逼问压缩进图讲解 |
| §4.2–4.3 四条合同 + 10 步 | blk_mq_submit_bio 源码 | 22 | 保留切分→合并→新建 request/拿 tag；flush 旁支放到 32 |
| 逼问 4 单队列一把锁 vs blk-mq | 双泳道图 | 23 | 保留，80 万 IOPS 按原文口径 |
| §4.4.1 电梯算法算例 | pics/03-elevator.png | 24 | 保留 640/236/236(208)/322 四数（已复算） |
| §4.4.1–4.4.2 deadline 双索引 + 四调度器 | text + elevator_get_default 源码 | 25–26 | 保留；kyber/bfq 只点名；默认规则按 6.12 精确化 |
| §4.5 块层伪代码 | — | — | 由真实源码 22/26 代替，伪代码文档保留 |
| §5.1 驱动对象 + 逼问 1–5 | NVMe 队列图 | 28 | 保留 SQ/CQ/门铃/PRP/MSI-X/CID |
| §5.2 nvme_queue_rq | 源码 | 29 | 保留；补充 per-queue sq_lock 与批量敲门铃 |
| §5.3–5.4 硬件与回程 | 回程 timeline | 30 | 保留；回调按 6.12 用 folio_end_read |
| §6.1 主线 12 步 / §6.6 五条路 × 五层 | 矩阵图 | 31 | 保留 |
| §6.2 write + fsync | text + 例子 | 32 | 保留三个完成时刻、PREFLUSH/FUA/Flush |
| §6.3–6.4 O_DIRECT / mmap | 双泳道图 | 33 | 保留 |
| 03-four-ways.c 实验 | 设计 text + fsync 模式源码 | 34–35 | 先讲设计再上代码，给 Linux 预期；摘录避开含 ⑤ 的注释行 |
| §7 朴素 vs 真实 / §9 约束回扣 | 各站 sidebar 约束 + 总结卡 | 3–33、37 | 合并进各场景"没有它会怎样"与总结卡，不单列表 |
| §8 三个常见误解 | text | 36 | 保留 |
| §10 呼应 | 下集预告 | 38 | 指向 Origin |

## 源码摘录（全部逐行取自 Linux v6.12，副本在 video-notes/src/）

| 场景 | 文件 | 行号 | 核对 |
|---|---|---|---|
| 8 | fs/read_write.c（vfs_read） | 549–571 | 逐行一致 |
| 12 | mm/readahead.c（page_cache_sync_ra） | 573–596 | 逐行一致 |
| 18 | fs/ext4/readpage.c（ext4_mpage_readpages） | 342–366 | 逐行一致 |
| 22 | block/blk-mq.c（blk_mq_submit_bio） | 2988–3008 | 逐行一致 |
| 26 | block/elevator.c（elevator_get_default） | 558–572 | 逐行一致 |
| 29 | drivers/nvme/host/pci.c（nvme_queue_rq 函数体） | 879–903 | 逐行一致 |
| 35 | stages/03-how/src/03-four-ways.c（run_fsync） | 65–77 | 逐行一致 |
| 16 | 原文 §3.3.2 的对账命令 | — | 取原文命令，删去 stat/debugfs/blockdev 三条，最后一条按 \ 折行 |

旁证核对（未上屏）：mm/readahead.c get_init_ra_size / get_next_ra_size / file_ra_state_init（prev_pos = -1）；include/linux/pagemap.h:1365 VM_READAHEAD_PAGES = 128K；mm/filemap.c:2407–2460 filemap_update_page、1529 folio_end_read；block/mq-deadline.c:30–38（读 HZ/2、写 5*HZ、writes_starved 2、fifo_batch 16）；block/kyber-iosched.c:71–72（2 ms / 10 ms）；drivers/nvme/host/pci.c:74 io_queue_depth = 1024、471–495 门铃与 SQ 拷贝；drivers/nvme/host/nvme.h:575–605 CID = 代数<<12 | tag；mm/page-writeback.c:109 dirty_expire 30 s；block/blk-core.c:555 blk_partition_remap；fs/ext4/file.c:931 只填 read_iter。

## 相对原文的事实修正

1. **预读量**：原文称 pread(fd, buf, 4096, 8192) 未命中会预读页 2..33 共 128 KiB。v6.12 的 page_cache_sync_ra 对新打开文件的这次读：index=2、前一页未缓存，contig_count=0 ≤ 1，走 do_page_cache_ra 只读 1 页。只有文件开头、紧接上次位置或超大请求才开窗，1 页请求初始窗口 4 页，顺序读按 4→8→16→32 页增长，128 KiB 是上限。视频按此讲（场景 2、12、13），folio-to-bio 图解释为顺序读稳态。
2. **ext4 断 bio 的判据**：原文写 bio_end_sector(bio) != pblk<<3；v6.12 实际比较 last_block_in_bio != first_block - 1（块号），并加 fscrypt 可合并检查。
3. **回程回调**：原文写 folio_mark_uptodate + folio_unlock；v6.12 的 __read_end_io 调 folio_end_read，一次原子操作置 uptodate、清 locked 并唤醒。
4. **读者睡在哪**：原文写 filemap_read 里 folio_wait_locked、可中断睡眠；v6.12 是 filemap_get_pages → filemap_update_page 试锁失败 → folio_put_wait_locked(TASK_KILLABLE)，只响应致命信号。
5. **预读调用链**：v6.12 已无 ondemand_readahead；链路为 page_cache_sync_readahead → page_cache_sync_ra → page_cache_ra_order/do_page_cache_ra → page_cache_ra_unbounded → read_pages，plug 包在 read_pages 内。
6. **CID = tag**：v6.12 中 CID 低 12 位是 tag、高 4 位是代数计数器，nvme_find_rq 会校验代数，防止过期完成认错 request。
7. **默认调度器**：除"单队列 → mq-deadline，多队列 → none"外，6.12 还对共享 tag 的多队列设备默认 mq-deadline，且驱动可用 BLK_MQ_F_NO_SCHED_BY_DEFAULT 不要默认调度器。
8. **每核队列免锁**：nvme_queue_rq 拷命令和写门铃持有每队列的 sq_lock；一核一队列时这把锁基本不竞争，但不是无锁。门铃只在 bd->last 或队列回绕时写，一批请求只敲一次。
9. **拿 tag 的时机**：有调度器时分配阶段拿的是调度器 tag，驱动 tag 在派发时再拿；本集主线 NVMe 用 none，分配即拿驱动 tag，视频按主线讲。
10. VFS 入口：vfs_read 先查 f_op->read，ext4 未填，经 new_sync_read 构造 kiocb + iov_iter 再调 read_iter；rw_verify_area 中 security_file_permission / fsnotify_file_area_perm 位于 470 / 474 行，与原文一致。

## 验收

- 场景 38 个，视觉类型 9 种：spotlight 6、title 1、layers 1、html_slide 5（四张 03 图 + 总结卡）、ascii 7、text 8、code_explain 7、code 1、timeline 2。无人物、无类比插件场景。
- 旁白含 [example] 共 4509 字；估时 = 4509÷5.4 + 38×1.5 + 3 ≈ 895 秒（约 14.9 分钟）。
- vmd_lint（anthropic，generic）：0 错误，8 条 CODE-MULTI-HL 告警（多段高亮按要求保留）。
- atlas 禁词与场景术语检查：旁白无命中。ascii 每行显示宽度 ≤ 70、≤ 25 行。
- 总结卡 pics/ep3-summary-card.png 已目检，无溢出。
- 未改动 atlas md、stages、原 SVG 与其他集文件；未渲染、未提交、未上传。
