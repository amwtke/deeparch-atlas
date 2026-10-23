/*
 * 03-four-ways.c —— 同一个文件,四种走法,看它们在五层里各走到哪
 *
 *   buffered : read()            走 ① ② page cache (③④⑤ 只在未命中时)
 *   direct   : read() + O_DIRECT 走 ① ② ③ ④ ⑤,跳过 page cache,buf 直接做 DMA 目标
 *   fsync    : write() + fsync() write 只到 page cache;fsync 把脏页 + 日志 + flush 压到 ⑤
 *   mmap     : mmap() + 读内存   第一次缺页走 ② page cache;之后不进内核
 *
 * 用法(Linux):
 *   gcc -O2 -Wall -o four-ways 03-four-ways.c
 *   dd if=/dev/urandom of=big.bin bs=1M count=256
 *   ./four-ways big.bin buffered      # 跑两遍,第二遍快 10 倍以上 = page cache 命中
 *   ./four-ways big.bin direct        # 每遍都差不多 = 永远下盘
 *   ./four-ways big.bin fsync         # 对比注释掉 fsync() 的版本
 *   ./four-ways big.bin mmap
 *   strace -c ./four-ways big.bin mmap  # 看系统调用次数:mmap 几乎没有 read
 *
 * macOS 没有 O_DIRECT(用 fcntl(F_NOCACHE) 近似),这里只保证能编译。
 */
#define _GNU_SOURCE
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <time.h>
#include <unistd.h>

#ifndef O_DIRECT
#define O_DIRECT 0 /* macOS: 退化成普通读,仅为通过编译 */
#endif

#define CHUNK (64 * 1024)           /* 每次 read 64 KiB */

static double now(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return ts.tv_sec + ts.tv_nsec / 1e9;
}

static void die(const char *what) { perror(what); exit(1); }

/* ① → ② page cache:命中就不下盘;未命中 ② 造 bio → ③ → ④ → ⑤,顺带预读 */
static long run_buffered(const char *path, void *buf) {
    int fd = open(path, O_RDONLY);
    if (fd < 0) die("open");
    long total = 0, n;
    while ((n = read(fd, buf, CHUNK)) > 0) total += n;   /* 每次都要拷贝 page→buf */
    close(fd);
    return total;
}

/* O_DIRECT:② 跳过缓存,把 buf 这几页钉住直接挂到 bio 上;要求 buf / 偏移 / 长度对齐 */
static long run_direct(const char *path, void *buf) {
    int fd = open(path, O_RDONLY | O_DIRECT);
    if (fd < 0) die("open O_DIRECT");
    long total = 0, n;
    while ((n = read(fd, buf, CHUNK)) > 0) total += n;   /* DMA 直接落到 buf,不经过内核拷贝 */
    close(fd);
    return total;
}

/* write 只把页标脏就返回(C10·内存装不下);fsync 才触发回写 + 日志提交 + flush/FUA 穿到 ⑤ */
static long run_fsync(const char *path, void *buf) {
    int fd = open(path, O_WRONLY | O_CREAT | O_TRUNC, 0644);
    if (fd < 0) die("open write");
    memset(buf, 0x5a, CHUNK);
    long total = 0;
    for (int i = 0; i < 64; i++) {           /* 64 × 64 KiB = 4 MiB */
        if (write(fd, buf, CHUNK) != CHUNK) die("write");
        total += CHUNK;
        if (fsync(fd) < 0) die("fsync");     /* 注释掉这一行再跑一遍,感受 R5·活过断电 的价格 */
    }
    close(fd);
    return total;
}

/* mmap:没有 read 系统调用;第一次碰到每一页触发缺页 → filemap_fault → 同一套 page cache */
static long run_mmap(const char *path) {
    int fd = open(path, O_RDONLY);
    if (fd < 0) die("open");
    struct stat st;
    if (fstat(fd, &st) < 0) die("fstat");
    unsigned char *p = mmap(NULL, st.st_size, PROT_READ, MAP_PRIVATE, fd, 0);
    if (p == MAP_FAILED) die("mmap");
    unsigned long sum = 0;
    for (off_t i = 0; i < st.st_size; i += 4096) sum += p[i];   /* 每页摸一下 = 每页一次缺页(或 fault-around) */
    munmap(p, st.st_size);
    close(fd);
    return (long)(sum & 0xff) + st.st_size - (sum & 0xff);
}

int main(int argc, char **argv) {
    if (argc != 3) { fprintf(stderr, "usage: %s <file> buffered|direct|fsync|mmap\n", argv[0]); return 2; }
    void *buf;
    if (posix_memalign(&buf, 4096, CHUNK) != 0) die("posix_memalign");  /* O_DIRECT 要求页对齐 */

    double t0 = now();
    long total;
    if      (!strcmp(argv[2], "buffered")) total = run_buffered(argv[1], buf);
    else if (!strcmp(argv[2], "direct"))   total = run_direct(argv[1], buf);
    else if (!strcmp(argv[2], "fsync"))    total = run_fsync(argv[1], buf);
    else if (!strcmp(argv[2], "mmap"))     total = run_mmap(argv[1]);
    else { fprintf(stderr, "unknown mode\n"); return 2; }
    double dt = now() - t0;

    printf("%-8s %ld bytes in %.3f s  (%.1f MB/s)\n", argv[2], total, dt, total / dt / 1e6);
    free(buf);
    return 0;
}
