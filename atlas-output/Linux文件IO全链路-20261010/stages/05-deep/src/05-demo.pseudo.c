/*
 * 05-demo.pseudo.c —— 伪代码(按用户要求不保证可编译),每行注释给出 Linux 6.12 的真实调用链。
 * 三个场景对应正文三条主线。以后要在 Linux 上跑,把 PSEUDO 块换成真实系统调用即可。
 *
 * 观察手段(真机):
 *   strace -c ./demo                 系统调用次数:场景 1 vs 场景 3 差一个数量级
 *   bpftrace -e 'kprobe:submit_bio { @[comm] = count(); }'     看谁在往块层发 bio
 *   bpftrace -e 'kprobe:blk_mq_get_tag { @ = hist(nsecs); }'   tag 等待分布(背压)
 *   cat /sys/kernel/debug/tracing/events/block/block_rq_issue   request 下发时间点
 *   perf trace -s ./demo             每个系统调用的耗时直方图
 */

/* ---------- 场景 1:主线 A,缓冲读命中 vs 未命中,以及 mmap 缺页 ---------- */
void scenario_upper(void) {
    int fd = open("/mnt/nvme/notes.txt", O_RDONLY);     // → do_sys_openat2 → path_openat → dcache / ext4 lookup
    char *buf = aligned_alloc(4096, 65536);

    pread(fd, buf, 4096, 8192);                          // 第一次:未命中
    // → ksys_pread64 → vfs_read(L549) → new_sync_read(L478):kiocb + iov_iter
    // → ext4_file_read_iter(fs/ext4/file.c L130) → generic_file_read_iter → filemap_read(mm/filemap.c L2610)
    //   → filemap_get_pages(L2523):批量查 XArray 空 → page_cache_sync_readahead → page_cache_sync_ra(mm/readahead.c L538)
    //     窗口 = get_init_ra_size(1, 32) = 4 页;按 2 的幂涨到 32 页(128 KiB)
    //   → page_cache_ra_unbounded(L205):filemap_add_folio × N(置 locked)→ read_pages → ext4_readahead → 进场景 2
    //   → folio_wait_locked:睡;回程 folio_end_read 唤醒 → copy_folio_to_iter(folio 2, 0, 4096)

    pread(fd, buf, 4096, 8192);                          // 第二次:命中
    // → 同上到 filemap_get_pages → filemap_get_read_batch 直接拿到 uptodate 的 folio → 拷贝 → 返回;③④⑤ 不动

    char *p = mmap(NULL, 1 << 20, PROT_READ, MAP_PRIVATE, fd, 0);   // 不读任何数据,只建 VMA(vm_ops = ext4_file_vm_ops)
    volatile char c = p[8192];                                      // 缺页异常(不是系统调用)
    // → handle_mm_fault → do_fault(mm/memory.c L5401) → do_read_fault(L5277)
    //   → 先试 fault-around:filemap_map_pages(mm/filemap.c L3630),把周围已在缓存的 16 页一起填 PTE(fault_around_pages = 65536 >> 12,memory.c L5171)
    //   → 没命中才 vm_ops->fault = filemap_fault(L3301):filemap_get_folio → do_sync_mmap_readahead → 同一套 XArray / 预读
    //   → 把 folio 的物理地址填进页表;异常返回,重执行那条读指令;以后读这页不再进内核
    c = p[8192 + 4096 * 3];                                          // 在 fault-around 覆盖范围内:无异常
}

/* ---------- 场景 2:主线 B,一个 bio 走到 NVMe 再回来(由场景 1 的未命中触发) ---------- */
void scenario_block(void) {
    // ext4_mpage_readpages(fs/ext4/readpage.c L211),对预读的 32 个 folio:
    //   lblk = index;ext4_map_blocks(fs/ext4/inode.c L595):先查 extent status 缓存 → {0, 256, 81920}
    //   连续性检查(L341-342):last_block_in_bio != first_block - 1 → submit_bio 断开
    //   bio_alloc(bdev, bio_max_segs(32), REQ_OP_READ)(L353);bi_sector = 81922 << 3(L358);bi_end_io = mpage_end_io(L359)
    //   bio_add_folio(L365) × 32;最后 submit_bio(L389)
    PSEUDO submit_bio(bio);
    // → submit_bio(block/blk-core.c L886):计 PGPGIN → submit_bio_noacct(L751)
    //   → blk_partition_remap(L555):bi_sector += bd_start_sect(2048)→ 657424
    //   → __submit_bio(L604):blk_start_plug;bdev 无 submit_bio 钩子 → blk_mq_submit_bio(block/blk-mq.c L2940)
    //     → __bio_split_to_limits(L2988):按 limits.max_sectors / max_segments 切(本例 128 KiB 不用切)
    //     → blk_mq_attempt_bio_merge:plug 里 / 调度器里有相邻 request 吗?无
    //     → blk_mq_get_new_requests(L2847) → __blk_mq_alloc_requests(L435) → blk_mq_get_tag(block/blk-mq-tag.c L134)
    //        位图取 tag;没有就 io_schedule()(L188)睡 —— 背压
    //     → blk_mq_bio_to_request(L2536):rq->__sector / __data_len / bio 链
    //     → plug 非空 → blk_add_rq_to_plug(L1281);blk_finish_plug 时倒出
    //   → blk_mq_dispatch_rq_list(L1992) → q->mq_ops->queue_rq(hctx, &bd)(L2030)
    // → nvme_queue_rq(drivers/nvme/host/pci.c L876)
    //   → nvme_prep_rq(L838) → nvme_setup_cmd(core.c L1052) → nvme_setup_rw(L973):
    //        opcode = nvme_cmd_read;slba = nvme_sect_to_lba(657424)= 657424 >> (lba_shift − 9)(nvme.h L669);
    //        length = (131072 >> lba_shift) − 1;REQ_RAHEAD → DSM FREQ_PREFETCH 提示
    //     → nvme_map_data:32 页 → scatterlist → DMA 映射 → PRP 列表
    //   → spin_lock(sq_lock);nvme_sq_copy_cmd(L488):memcpy 64 B 进 SQ,tail++;
    //   → nvme_write_sq_db(L471, bd->last):只有批尾才 writel 门铃 —— 一批命令一次 MMIO
    PSEUDO device_does_io();        // 取命令 → 闪存 → DMA 写 32 页 → CQ 条目(CID = tag)→ MSI-X
    // → nvme_irq(L1080) → nvme_poll_cq(L1059):循环取 CQ 条目 → nvme_handle_cqe(L1013)
    //   → nvme_find_rq(tagset, command_id)(L1032):tag → request
    //   → nvme_pci_complete_rq(L978) → blk_mq_complete_request(block/blk-mq.c L1226)
    //      → blk_mq_complete_request_remote(L1192):提交核 ≠ 当前核 → IPI 送回提交核(缓存局部性)
    //      → blk_mq_end_request(L1049) → 释放 tag → bio_endio(block/bio.c L1665) → bi_end_io = mpage_end_io
    //        → 对每个 folio:folio_end_read(uptodate + unlock)→ 唤醒睡在 folio 2 上的进程
}

/* ---------- 场景 3:主线 C,epoll 循环 vs io_uring 循环 ---------- */
void scenario_epoll(int listen_fd) {
    int ep = epoll_create1(0);                                        // → ep_alloc:eventpoll{rbr, rdllist, wq}
    epoll_ctl(ep, EPOLL_CTL_ADD, sock_fd, &ev);                       // → do_epoll_ctl(fs/eventpoll.c):file_can_poll? 普通文件 → EPERM(L2273)
    // → ep_insert(L1618):init_poll_funcptr(ep_ptable_queue_proc)(L1693)→ ep_item_poll(L1702)→ vfs_poll → tcp_poll
    //   → ep_ptable_queue_proc(L1413) 把 ep_poll_callback 挂进 socket 的等待队列
    for (;;) {
        int n = epoll_wait(ep, events, 64, -1);                       // → ep_poll(L1966):rdllist 空则睡在 ep->wq
        // 数据到达:sk_data_ready → wake_up → ep_poll_callback(L1308):epitem 挂上 rdllist(L1350),唤醒 ep->wq
        for (int i = 0; i < n; i++)
            read(events[i].data.fd, buf, 4096);                       // 第二次系统调用,才真正读
    }
}

void scenario_io_uring(void) {
    int ring = io_uring_setup(256, &params);                           // → io_uring_setup(io_uring/io_uring.c L3765):分配 io_rings + sqe 数组
    PSEUDO mmap(ring, IORING_OFF_SQ_RING / IORING_OFF_SQES / IORING_OFF_CQ_RING);   // uapi L464-466:三段共享内存
    for (;;) {
        // 填 sqe(uapi L30):opcode = IORING_OP_READ(L226), fd, off = 8192, addr = buf, len = 4096, user_data = 1
        PSEUDO sqes[tail & mask] = sqe; sq.tail = tail + 1;            // 只写共享内存,无系统调用
        io_uring_enter(ring, 1, 1, IORING_ENTER_GETEVENTS);            // → L3279:io_submit_sqes(L2295)→ io_get_sqe(L2261)→ io_submit_sqe
        //   → __io_read(io_uring/rw.c L830):force_nonblock → IOCB_NOWAIT(L853)→ ext4_file_read_iter → filemap_read
        //      命中:当场完成,cqe 写进 CQ;未命中:-EAGAIN → io_queue_async(L1919)
        //      ext4 未命中实际不出 __io_read:io_rw_should_retry(rw.c L733,要 f_op 标 FOP_BUFFER_RASYNC)→ 带 IOCB_WAITQ 再读
        //        → filemap_update_page(mm/filemap.c L2433)→ __folio_lock_async(L1659):回调挂在页上,返回 -EIOCBQUEUED,不发 cqe
        //        → 页到了:folio_end_read → io_async_buf_func(rw.c L702)→ io_req_task_queue:回提交进程重跑 __io_read,命中,发 cqe
        //      socket 未命中:-EAGAIN → io_queue_async(L1919)→ io_arm_poll_handler(L1931)挂 poll 回调,就绪后重试(内置 epoll)
        //      两者都不行(不可 poll 且文件系统没标 FOP_BUFFER_RASYNC):io_queue_iowq(L512)→ io-wq 线程阻塞读,兜底
        //      fd 带 O_DIRECT:ext4_file_read_iter L144 → ext4_dio_read_iter L69 → iomap_dio_rw → bio_iov_iter_get_pages 钉用户 buf
        //        → bi_end_io = iomap_dio_bio_end_io;kiocb 有 ki_complete(io_rw_init_file L824)→ __iomap_dio_rw L737 直接回 -EIOCBQUEUED,不睡
        //        → 盘做完 → bio_endio → iomap_dio_bio_end_io L166 → ki_complete = io_complete_rw L529 → task_work → cqe(回调挂在 bio 上,不是页上)
        //   → IORING_ENTER_GETEVENTS → io_cqring_wait(L2514):CQ 里 ≥ min_complete 条就返回
        PSEUDO cqe = cqes[cq.head & cq_mask]; cq.head++;                // 读共享内存,无系统调用
        // 开 IORING_SETUP_SQPOLL(uapi L151):io_sq_thread(sqpoll.c L267)替你轮询 SQ,连上面那次 io_uring_enter 都省
        // 开 IORING_SETUP_IOPOLL(L150)+ O_DIRECT:io_do_iopoll(rw.c L1138)→ bio_poll → nvme_poll,不等中断
    }
}
