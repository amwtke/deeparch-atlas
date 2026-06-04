// =============================================================================
// 05-mini-docker.c —— 80 行 C 代码,一次造出六面墙
//
// 用 clone() 带六个 CLONE_NEW* 标志生一个子进程,把六扇窗一次开齐,
// 让子进程打印"容器内视图",对印宿主视图 —— 六面墙的现场铁证。
//
// 编译运行(在任一台 Linux 上,普通用户即可,因为带了 CLONE_NEWUSER):
//   gcc -O2 -o mini-docker 05-mini-docker.c
//   ./mini-docker
// =============================================================================
#define _GNU_SOURCE
#include <sched.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <string.h>
#include <fcntl.h>
#include <signal.h>
#include <sys/mount.h>
#include <sys/wait.h>
#include <sys/utsname.h>

#define STACK_SIZE (1024 * 1024)
static char child_stack[STACK_SIZE];
static int sync_pipe[2];                       // 父→子 的同步管:等 uid_map 配好

static void write_file(const char *path, const char *content) {
    int fd = open(path, O_WRONLY);
    if (fd < 0) { perror(path); return; }
    if (write(fd, content, strlen(content)) < 0) perror("write");
    close(fd);
}

// 子进程:它一出生就身处六面墙之内
static int container(void *arg) {
    char ch;
    close(sync_pipe[1]);
    read(sync_pipe[0], &ch, 1);                // 阻塞,直到父把 uid/gid 映射写好

    sethostname("mini-container", 14);          // 【uts 窗】改主机名,只影响本窗
    // 【mnt 窗】先把挂载传播设为私有(不污染宿主),再重新挂 /proc
    mount(NULL, "/", NULL, MS_REC | MS_PRIVATE, NULL);
    mount("proc", "/proc", "proc", 0, NULL);    // 让 ps/ls /proc 只看见本 pid 窗

    struct utsname u; uname(&u);
    printf("\n============= 容器内视图(墙内) =============\n");
    printf("[pid 窗 ] getpid()            = %d        ← 我以为我是 1 号\n", getpid());
    printf("[uts 窗 ] hostname            = %s\n", u.nodename);
    printf("[user窗] getuid()/geteuid()  = %d/%d     ← 容器内的 root\n", getuid(), geteuid());
    printf("[net 窗 ] 我能看到的网卡:\n");
    system("ip -o link show 2>/dev/null | awk '{printf \"          %s\\n\",$2}' || echo '          (只有 lo)'");
    printf("[pid 窗 ] /proc 里的进程数    = ");
    fflush(stdout);
    system("ls /proc | grep -E '^[0-9]+$' | wc -l");
    printf("[ipc 窗 ] 共享内存段(本窗)  = ");
    fflush(stdout);
    system("ipcs -m 2>/dev/null | grep -cE '^0x' || echo 0");
    printf("===========================================\n");
    printf("[容器] 进入交互 shell,exit 退出。\n");

    execlp("/bin/sh", "/bin/sh", (char *)NULL);
    perror("execlp");
    return 1;
}

int main(void) {
    struct utsname u; uname(&u);
    printf("============= 宿主视图(墙外) =============\n");
    printf("[宿主] getpid()  = %d\n", getpid());
    printf("[宿主] hostname  = %s\n", u.nodename);
    printf("[宿主] getuid()  = %d\n", getuid());

    if (pipe(sync_pipe) < 0) { perror("pipe"); exit(1); }

    // ★ 一次 clone,带六个 CLONE_NEW* —— 六面墙一次开齐
    int flags = CLONE_NEWUSER | CLONE_NEWPID | CLONE_NEWNET |
                CLONE_NEWNS  | CLONE_NEWUTS | CLONE_NEWIPC | SIGCHLD;
    pid_t pid = clone(container, child_stack + STACK_SIZE, flags, NULL);
    if (pid < 0) { perror("clone"); exit(1); }
    printf("[宿主] 容器进程在【宿主】上的 PID = %d   ← 注意:不是容器内看到的 1\n", pid);

    // 配 user 窗的映射:容器内 uid 0 ←→ 宿主当前 uid(rootless 的关键)
    char path[64], line[64];
    snprintf(path, sizeof path, "/proc/%d/setgroups", pid); write_file(path, "deny");
    snprintf(path, sizeof path, "/proc/%d/uid_map", pid);
    snprintf(line, sizeof line, "0 %d 1", getuid());        write_file(path, line);
    snprintf(path, sizeof path, "/proc/%d/gid_map", pid);
    snprintf(line, sizeof line, "0 %d 1", getgid());        write_file(path, line);

    write(sync_pipe[1], "x", 1);   // 放行子进程
    close(sync_pipe[1]);
    waitpid(pid, NULL, 0);
    return 0;
}
