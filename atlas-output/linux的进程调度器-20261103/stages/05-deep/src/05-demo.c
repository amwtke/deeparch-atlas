/*
 * 05-demo.c — Linux 专用观测 demo(未在本机验证:作者机器是 macOS,无法编译运行;
 *             代码只在 macOS 上过了 clang -fsyntax-only,Linux 分支靠 #ifdef __linux__ 隔开)。
 *
 * 做三件事,对应 Deep 三条主线:
 *   ① 主线①:起三个线程 —— nice 19 的纯算 spinner、nice 0 的纯算 spinner、每 10 ms 醒一次算 50 μs 的 sleeper,
 *      全部绑到同一颗核,然后每秒读 /proc/self/task/<tid>/sched,打印 se.vruntime / se.deadline / se.slice /
 *      nr_switches / nr_involuntary_switches —— 对照 05-deep.md §2.4 的模拟表。
 *   ② 主线②:同一组线程不绑核再跑一遍,读 se.nr_migrations,看搬了几次(对照 §3.4)。
 *   ③ 主线③:如果进程在一个带 cpu.max 的 cgroup v2 里(argv[1] 给 cgroup 路径),每秒读 cpu.stat 的
 *      nr_periods / nr_throttled / throttled_usec(对照 §4.4)。
 *
 * 编译(Linux,glibc ≥ 2.28,内核 ≥ 6.6 才有 deadline / slice 字段):
 *   gcc -O2 -pthread -o 05-demo 05-demo.c
 * 运行:
 *   ./05-demo                      # 主线① + ②
 *   sudo mkdir /sys/fs/cgroup/demo && echo "200000 100000" > /sys/fs/cgroup/demo/cpu.max
 *   echo $$ > /sys/fs/cgroup/demo/cgroup.procs && ./05-demo /sys/fs/cgroup/demo   # 加主线③
 * 观察:
 *   watch -n1 'grep -E "vruntime|deadline|slice|nr_switches|nr_migrations" /proc/<pid>/task/<tid>/sched'
 *   perf sched record -- sleep 2 && perf sched latency --sort max     # 唤醒到上台的延迟
 *   perf stat -e sched:sched_migrate_task,sched:sched_switch -p <pid> sleep 5
 *   gdb:  b pick_eevdf / b place_entity / b check_preempt_wakeup_fair / b throttle_cfs_rq(需 vmlinux + kgdb/QEMU)
 */
#ifdef __linux__
#define _GNU_SOURCE
#include <pthread.h>
#include <sched.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/resource.h>
#include <sys/syscall.h>
#include <time.h>
#include <unistd.h>

static volatile int stop_all;

static pid_t gettid_(void) { return (pid_t)syscall(SYS_gettid); }

static void pin_to_cpu(int cpu) {
    cpu_set_t set;
    CPU_ZERO(&set);
    CPU_SET(cpu, &set);
    sched_setaffinity(0, sizeof set, &set);        /* → p->cpus_ptr = {cpu}:select_task_rq_fair 只能选它 */
}

static void *spinner(void *arg) {                  /* 纯算:永远不阻塞,只能被 tick / 唤醒抢占换下 */
    int nice = (int)(long)arg;
    setpriority(PRIO_PROCESS, 0, nice);            /* → set_user_nice → reweight_task:权重查 sched_prio_to_weight[] */
    pin_to_cpu(0);
    volatile unsigned long x = 0;
    while (!stop_all) x++;                         /* 每个 tick:update_curr → vruntime += delta×1024/weight */
    return NULL;
}

static void *sleeper(void *arg) {                  /* 每 10 ms 醒一次,算 50 μs:lag 在 ±2 slice 内来回 */
    (void)arg;
    setpriority(PRIO_PROCESS, 0, -10);             /* 需要 CAP_SYS_NICE;失败就用 nice 0 */
    pin_to_cpu(0);
    struct timespec ts = {0, 10 * 1000 * 1000};
    while (!stop_all) {
        nanosleep(&ts, NULL);                      /* → dequeue_entity(DEQUEUE_SLEEP):update_entity_lag 存 vlag */
        struct timespec a, b;                      /* 醒来 → enqueue_entity → place_entity → check_preempt_wakeup_fair */
        clock_gettime(CLOCK_MONOTONIC, &a);
        do { clock_gettime(CLOCK_MONOTONIC, &b); }
        while ((b.tv_sec - a.tv_sec) * 1000000000L + (b.tv_nsec - a.tv_nsec) < 50000);
    }
    return NULL;
}

static void dump_sched(const char *tag, pid_t tid) {
    char path[64], line[256];
    snprintf(path, sizeof path, "/proc/self/task/%d/sched", tid);
    FILE *f = fopen(path, "r");
    if (!f) return;
    printf("[%s tid %d]\n", tag, tid);
    while (fgets(line, sizeof line, f))
        if (strstr(line, "se.vruntime") || strstr(line, "se.deadline") || strstr(line, "se.slice") ||
            strstr(line, "nr_switches") || strstr(line, "nr_involuntary") || strstr(line, "se.nr_migrations") ||
            strstr(line, "se.load.weight"))
            fputs(line, stdout);                    /* 字段名见 kernel/sched/debug.c proc_sched_show_task */
    fclose(f);
}

static void dump_cpu_stat(const char *cg) {
    char path[256], line[128];
    snprintf(path, sizeof path, "%s/cpu.stat", cg);
    FILE *f = fopen(path, "r");
    if (!f) return;
    printf("[cpu.stat %s]\n", cg);
    while (fgets(line, sizeof line, f))
        if (strstr(line, "nr_periods") || strstr(line, "nr_throttled") || strstr(line, "throttled_usec") ||
            strstr(line, "nr_bursts"))
            fputs(line, stdout);                    /* 来自 core.c cpu_cfs_stat_show / cpu_extra_stat_show */
    fclose(f);
}

struct tinfo { pthread_t th; pid_t tid; const char *name; };
static pid_t tids[3];
static void *tid_wrap(void *a) { struct tinfo *ti = a; ti->tid = gettid_(); return NULL; }

int main(int argc, char **argv) {
    const char *cg = argc > 1 ? argv[1] : NULL;
    pthread_t t[3];
    pthread_create(&t[0], NULL, spinner, (void *)19L);   /* xz 的替身:nice 19,权重 15 */
    pthread_create(&t[1], NULL, spinner, (void *)0L);    /* mysqld 的替身:nice 0,权重 1024 */
    pthread_create(&t[2], NULL, sleeper, NULL);          /* redis 的替身:nice -10,权重 9548 */
    sleep(1);
    for (int round = 0; round < 10; round++) {
        /* 线程 tid 通过 /proc/self/task 枚举更稳,这里简单用 pthread 之外的 gettid 约定:
           Linux 上 /proc/self/task/ 下每个目录就是一个 tid */
        FILE *p = popen("ls /proc/self/task", "r");
        if (p) {
            char buf[32];
            int i = 0;
            while (fgets(buf, sizeof buf, p) && i < 3) {
                pid_t tid = (pid_t)atoi(buf);
                if (tid == getpid()) continue;         /* 跳过主线程 */
                tids[i++] = tid;
            }
            pclose(p);
        }
        printf("===== t=%d s =====\n", round + 1);
        for (int i = 0; i < 3; i++) if (tids[i]) dump_sched(i == 0 ? "spinner nice19" : i == 1 ? "spinner nice0" : "sleeper", tids[i]);
        if (cg) dump_cpu_stat(cg);
        sleep(1);
    }
    stop_all = 1;
    for (int i = 0; i < 3; i++) pthread_join(t[i], NULL);
    (void)tid_wrap;
    return 0;
}
#else
#include <stdio.h>
int main(void) {
    puts("05-demo.c 只能在 Linux 上运行:它读 /proc/<pid>/task/<tid>/sched 和 cgroup v2 的 cpu.stat。");
    return 0;
}
#endif
