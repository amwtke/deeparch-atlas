/*
 * 05-switch-demo.c —— 逼出三种换人,并亲眼看 fork 的「伪造栈」
 *
 * 编译:gcc -O0 -g -pthread 05-switch-demo.c -o 05-switch-demo
 * 运行:./05-switch-demo
 * 观察:另开一个终端先跑 sudo bpftrace 05-sched-switch.bt(见同目录)
 *
 * 钉在 Linux 6.12 / x86-64。注释里的 → 链给出每一步落在哪段内核源码。
 */
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <pthread.h>
#include <sched.h>
#include <sys/resource.h>
#include <sys/wait.h>
#include <time.h>

static void show_ctxsw(const char *tag)
{
	struct rusage ru;
	getrusage(RUSAGE_SELF, &ru);
	/* nvcsw = 自愿换人(门 2:睡/读管道);nivcsw = 被迫换人(门 1:tick 抢占) */
	printf("[%s] voluntary=%ld  involuntary=%ld\n", tag, ru.ru_nvcsw, ru.ru_nivcsw);
}

static void pin_cpu0(void)
{
	cpu_set_t set;
	CPU_ZERO(&set);
	CPU_SET(0, &set);
	sched_setaffinity(0, sizeof(set), &set);   /* 把所有线程压到 CPU0,逼出竞争 */
}

/* 场景 1:两个忙循环抢同一个核 → 只能靠 tick 抢人(门 1) */
static void *spin(void *arg)
{
	volatile unsigned long x = 0;
	time_t end = time(NULL) + 2;
	while (time(NULL) < end)
		x++;                 /* 每 1~4 ms 一次时钟中断:sched_tick → task_tick_fair → update_curr
				      *   → update_deadline 发现 vruntime ≥ deadline → resched_curr 置 TIF_NEED_RESCHED
				      *   → 中断返回路径 exit_to_user_mode_loop 看见标志 → schedule() → __schedule()
				      *   → pick_next_task → context_switch → switch_to(本线程被换下) */
	return NULL;
}

/* 场景 2:两个线程用管道乒乓 → 每一拍都是「主动睡 + 被唤醒」(门 2 + 门 3) */
static int pfd[2][2];
static void *pingpong(void *arg)
{
	int me = (int)(long)arg, other = 1 - me;
	char c = 'x';
	for (int i = 0; i < 1000; i++) {
		if (me == 0)
			write(pfd[other][1], &c, 1);  /* → pipe_write → wake_up → try_to_wake_up → ttwu_queue
						       *   → enqueue_task_fair(对方) → wakeup_preempt 可能置 need_resched */
		read(pfd[me][0], &c, 1);          /* → pipe_read 没数据 → set_current_state(TASK_INTERRUPTIBLE)
						       *   → schedule() → __schedule(): prev_state≠0 → block_task 出队
						       *   → pick_next_task 选对方 → switch_to,本线程的栈冻结在这里 */
		if (me == 1)
			write(pfd[other][1], &c, 1);
	}
	return NULL;
}

int main(void)
{
	pin_cpu0();
	show_ctxsw("start");

	pthread_t a, b;
	pthread_create(&a, NULL, spin, NULL);
	pthread_create(&b, NULL, spin, NULL);
	pthread_join(a, NULL);
	pthread_join(b, NULL);
	show_ctxsw("after spin   (involuntary 应明显增加)");

	pipe(pfd[0]);
	pipe(pfd[1]);
	pthread_create(&a, NULL, pingpong, (void *)0L);
	pthread_create(&b, NULL, pingpong, (void *)1L);
	pthread_join(a, NULL);
	pthread_join(b, NULL);
	show_ctxsw("after pingpong (voluntary 应增加约 2000)");

	/* 场景 3:fork —— 子进程第一次上核不是从 switch_to 的调用点「返回」,
	 * 而是从 copy_thread 伪造的那帧醒来:
	 *   copy_thread(): frame->ret_addr = ret_from_fork_asm; childregs = *current_pt_regs(); childregs->ax = 0
	 *   第一次被 pick 到 → __switch_to_asm 换栈 → popq ×6(弹出伪造的 0)→ jmp __switch_to → ret
	 *   → 弹出 ret_addr = ret_from_fork_asm → call ret_from_fork → schedule_tail → syscall_exit_to_user_mode
	 *   → sysret,rax = 0 → 子进程「从 fork() 返回」,返回值 0 */
	pid_t pid = fork();
	if (pid == 0) {
		printf("[child] fork() returned %d —— 这个 0 是 copy_thread 写进伪造 pt_regs 的 ax\n", 0);
		_exit(0);
	}
	waitpid(pid, NULL, 0);
	printf("[parent] fork() returned %d —— 父进程走的是正常的 syscall 返回路径\n", pid);
	return 0;
}
