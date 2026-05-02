/*
 * atlas Deep stage demo — three malloc paths in glibc 2.34+
 *
 * 三个场景对应 ptmalloc2 的三条主路径:
 *   场景 1: malloc(24)    → tcache 路径  (thread-local 无锁,完全不进内核)
 *   场景 2: malloc(8KB)   → brk 路径    (走 arena,sysmalloc → sbrk 扩 heap)
 *   场景 3: malloc(200KB) → mmap 路径   (绕过 arena,直接 mmap syscall)
 *
 * 编译:
 *   gcc -O0 -g -o 05-demo 05-demo.c
 *
 * 运行 + 追踪 syscall:
 *   strace -e trace=brk,mmap,munmap ./05-demo
 *
 * 预期输出(关键 syscall 节选):
 *   brk(NULL)             = 0x55...           # libc 启动 + main_arena 初始化
 *   brk(0x55...22000)     = 0x55...22000      # 第一次扩 heap
 *   ... [malloc(24) 完全无 syscall, 走 tcache] ...
 *   brk(0x55...24000)     = 0x55...24000      # 场景 2: 8KB 触发 sbrk
 *   mmap(NULL, 204800, PROT_READ|PROT_WRITE, ...) = 0x7f...    # 场景 3
 *   munmap(0x7f..., 204800) = 0                                # 场景 3 free
 *
 * gdb 追踪关键断点:
 *   gdb ./05-demo
 *     b __libc_malloc
 *     b _int_malloc
 *     b sysmalloc
 *     b _int_free
 *     run
 *     bt        # 看 call stack
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

static void print_separator(const char *title) {
    printf("\n========== %s ==========\n", title);
}

int main(void) {
    /* 让 strace 输出可定位 — 用 write 直接调 syscall 打 marker */
    char marker_msg[] = "\n[MARKER] === scenarios start ===\n";
    write(STDOUT_FILENO, marker_msg, sizeof(marker_msg) - 1);

    /* ========================================================
     * 场景 1: malloc(24) → tcache 路径
     *   - chunk size = 24 + 16(header) = 32B,对齐已满足 16B
     *   - tc_idx = (32 - 16) / 16 = 1  → 命中 tcache->entries[1]
     *   - 但首次 alloc tcache 是空的,会先走 _int_malloc 填充 tcache
     *   - free(p1) 把 chunk 放回 tcache(无锁 push)
     *   - 第二次 malloc(24) 才真正命中 tcache(纯 thread-local,无 syscall)
     * ======================================================== */
    print_separator("Scene 1: malloc(24) - tcache path");

    /* 第 1 次:tcache 空,走 _int_malloc 填 tcache */
    void *p1a = malloc(24);                  /* → __libc_malloc → _int_malloc → tcache_init + fill */
    printf("p1a (1st 24B) = %p\n", p1a);

    /* free 把 chunk 推回 tcache(无锁) */
    free(p1a);                               /* → __libc_free → tcache_put(完全无锁) */

    /* 第 2 次:tcache 命中(thread-local 无锁,~15 ns) */
    void *p1b = malloc(24);                  /* → __libc_malloc → tcache_get → 返回 */
    printf("p1b (2nd 24B, tcache hit) = %p\n", p1b);
    free(p1b);

    /* ========================================================
     * 场景 2: malloc(8KB) → brk 路径
     *   - chunk size = 8192 + 16 = 8208B
     *   - tc_idx = csize2tidx(8208) > TCACHE_MAX_BINS(64)→ tcache miss
     *   - size > MAX_FAST_SIZE(64) → fastbin miss
     *   - 进 _int_malloc 大块路径:unsorted scan → smallbin / largebin / use_top
     *   - 假设 top_chunk 不够 → sysmalloc → sbrk 扩 heap
     *   - free(p2) 把 chunk 标 free,合并相邻,挂回 unsorted bin(默认不还内核)
     * ======================================================== */
    print_separator("Scene 2: malloc(8KB) - brk path");

    void *p2 = malloc(8 * 1024);             /* 8192B → _int_malloc → sysmalloc → sbrk */
    printf("p2 (8KB) = %p\n", p2);

    /* 写入,触发实际物理页分配(让 RSS 真正增长) */
    memset(p2, 0xAB, 8 * 1024);

    free(p2);                                /* → _int_free → coalesce → unsorted bin push(默认不还) */

    /* ========================================================
     * 场景 3: malloc(200KB) → mmap 路径
     *   - chunk size = 204800 + 16 = 204816B
     *   - size >= M_MMAP_THRESHOLD (默认 128KB)→ 不走 arena,直接 sysmalloc_mmap
     *   - mmap syscall 拿独立 VMA,chunk header 标 IS_MMAPED
     *   - free(p3) 看到 IS_MMAPED → 直接 munmap syscall(立即还内核)
     * ======================================================== */
    print_separator("Scene 3: malloc(200KB) - mmap path");

    void *p3 = malloc(200 * 1024);           /* 204800B → sysmalloc_mmap → mmap syscall */
    printf("p3 (200KB) = %p\n", p3);

    memset(p3, 0xCD, 200 * 1024);            /* 触发实际页分配 */

    free(p3);                                /* → _int_free → IS_MMAPED → munmap syscall */

    char marker_msg2[] = "\n[MARKER] === scenarios end ===\n";
    write(STDOUT_FILENO, marker_msg2, sizeof(marker_msg2) - 1);

    return 0;
}
