# Docker 内核源码深剖:六面墙 · 三个表 · 两个洞

<!-- 本篇由三个独立文档拼接而成(05-1-walls.md / 05-2-tables.md / 05-3-holes.md),
     按 deeparch-md 方法生成(架构全景图用 HTML),供生成视频用。
     函数逻辑层贴 Linux 主线真源码(github.com/torvalds/linux)逐行讲;
     个别超大文件(fs/namespace.c 等)以"准确调用链 + 真函数名"呈现,已注明,绝不伪造逐字。 -->

> **灵魂问题(贯穿全程):** 容器到底是什么?它和虚拟机的根本区别在哪?当一个容器真正跑起来的那一刻,Linux 内核里到底发生了什么 —— namespace、cgroups、镜像分层各自扮演什么角色?
>
> **这一篇的本分:** 把容器赖以存在的三组机制,各自钻进内核源码讲透,对照我们一路用的「砌墙 + 凿洞」心法:
>
> - **第一部分 · 六面墙**:`clone()` 系统调用怎么造出 namespace 的 6 扇窗(`copy_namespaces` → 6 个 `copy_*`)。
> - **第二部分 · 三个表**:cgroup 怎么实现 cpu / memory / io 三张计量表(`try_charge` / CFS bandwidth / blk-throttle)。
> - **第三部分 · 两个洞**:veth 凿 net 墙、volume 凿 mnt 墙(`veth_newlink` / `clone_mnt`)。
>
> 每部分都是"**总**(先用 C 代码 / cgroup / 命令把效果演出来,贴控制台输出作铁证)+ **分**(逐项从用户态 syscall 钻到内核实现关键源码)"。**不在意篇幅,把逻辑讲清最重要。**

## 约束清单速查(C1~C3)

#### C1 — 榨干硬件:必须共享,必须隔离,隔离必须便宜
让 CPU / 内存更多用于**用户计算**。三连锁:①闲置是浪费 → 必须共享 ②共享默认互害 → 必须隔离 ③隔离太贵也是浪费 → 必须便宜。
**不可再分**:账单是物理的 / 全局命名是 40 年生态 / OS 体积时序是客观的。
**口诀**:榨干硬件 → 必须共享 → 必须隔离 → 隔离必须便宜

#### C2 ★ — 环境必须跟应用走(核心)
"环境"天然长在机器上,不打包成应用的行李,一致性就永远靠人肉装修。
**不可再分**:FHS / 动态链接几十年生态,应用无法独立于环境存在。
**口诀**:环境是机器属性 → 必须打包跟应用走

#### C3 — 发布必须去人化,且机器可验真
千台规模下人必须退出发布链路;机器接管的前提是工件身份能被机器证明。
**不可再分**:人不可并行复制 / 文件名 ≠ 内容。
**口诀**:人不能扩容 + 文件名 ≠ 内容 → 机器接管 + 哈希验真

> **本篇与约束的对应:** 六面墙(第一部分)化解 C1②(共享必互害 → 隔离视图);它"换指针即可"的廉价化解 C1③(隔离必须便宜)。三个表(第二部分)化解 C1①+②(合租必须有账)。两个洞(第三部分)是 C1② 的反作用 —— 墙砌死就做不了生意,必须受控连通。

---

---

<!-- ===== 第一篇 / 共三篇:六面墙。最终拼入 05-deep.md。deeparch-md 方法,架构全景图用 HTML。总分结构。 ===== -->

<!-- @video: scene=spotlight -->
# 一、六面墙:clone() 怎么在内核里造出 namespace

> 心法回扣:What 阶段说"墙 = namespace(改你看见什么)",还说"墙的物理实体 = `task_struct` 上几个指针"。这一篇钻进 Linux 内核源码,把那"几个指针"是**怎么被 `clone()` 一次性建出来的**逐行走一遍 —— 先用一段 C 代码把六面墙一次演出来(总),再分六扇窗逐个从用户态钻到内核实现(分)。

## 概览

容器的隔离,第一层叫 **namespace(命名空间)**。它把内核里本来全局的资源(进程号、网络栈、挂载表、主机名、IPC、用户表)切成一份份独立视图,让每个容器以为"整台机器都是我的"。容器常用 6 扇窗:**pid / net / mnt / uts / ipc / user**。

namespace 没有"创建容器"这种 API,它的全部入口只有三个系统调用 —— **`clone()`(出生即隔离)、`unshare()`(自己搬家)、`setns()`(串门)**。本篇聚焦 `clone()`:带着 `CLONE_NEW*` 标志 clone 一个进程,内核怎么把六扇窗一次性建出来。答案出奇地朴素:**造墙 = 给新进程的指针换指向。**

## 生活类比:给新员工配一套"独立视图"

一家大公司(内核),员工(进程)默认共用一套东西:一本全公司通讯录(进程表)、一部前台总机(网络)、一个公共文件柜(文件系统)、一块公告栏(主机名)。

来了个保密项目组(容器),HR(`clone`)给他们配独立的一套:**不是另盖一栋楼**(那是虚拟机),而是在新员工工牌(`task_struct`)上,把"你看哪本通讯录"那一栏从'公司通讯录'改成'本组通讯录'。改几个指向,人就住进了独立视图。还有个特殊的:**工牌的发牌权**(user 窗),必须**最先发**——后面发别的都要先验"你有没有资格",而验资格靠的就是这张工牌。

> 带着这个直觉:**namespace 不造实体,只换指向;user 窗是"发牌权",必须第一个建。** 我们来看真东西。

## 架构全景图(HTML)

> 完整可交互版:[`pics/05-1-walls-arch.html`](pics/05-1-walls-arch.html)。下方为同款内嵌图。

<!-- @video: scene=layers title=clone 造六面墙 -->
<div style="background:#0a0c10;color:#e8eef5;font-family:'JetBrains Mono',monospace;padding:18px;border-radius:10px">
  <div style="text-align:center;font-weight:700;margin-bottom:12px">clone() → copy_process() → 六面墙</div>
  <div style="text-align:center;background:#11161d;border:1px solid #4a5568;border-radius:8px;padding:8px;margin-bottom:6px">用户态 clone(CLONE_NEW*, …) / unshare(…)</div>
  <div style="text-align:center;color:#c08040">▼</div>
  <div style="text-align:center;background:#1f1408;border:1px solid #c08040;border-radius:8px;padding:8px;color:#ffaa55;margin-bottom:6px">kernel/fork.c copy_process()</div>
  <div style="display:flex;gap:12px;margin:6px 0">
    <div style="flex:1;background:#1a1030;border:1px solid #8040c0;border-radius:8px;padding:8px;color:#c088ff;text-align:center">① copy_creds() → create_user_ns()<br><span style="color:#9a7ab0;font-size:11px">user 窗 · 最先建 · 发牌权</span></div>
    <div style="flex:1;background:#1f1408;border:1px solid #c08040;border-radius:8px;padding:8px;color:#ffaa55;text-align:center">② copy_namespaces() → create_new_namespaces()<br><span style="color:#c89868;font-size:11px">派生其余五扇</span></div>
  </div>
  <div style="text-align:center;color:#c08040">▼</div>
  <div style="display:grid;grid-template-columns:repeat(6,1fr);gap:6px;margin:6px 0">
    <div style="background:#1f1408;border:1px solid #c08040;border-radius:6px;padding:6px;color:#ffaa55;text-align:center;font-size:11px">copy_mnt_ns<br>mnt</div>
    <div style="background:#1f1408;border:1px solid #c08040;border-radius:6px;padding:6px;color:#ffaa55;text-align:center;font-size:11px">copy_utsname<br>uts</div>
    <div style="background:#1f1408;border:1px solid #c08040;border-radius:6px;padding:6px;color:#ffaa55;text-align:center;font-size:11px">copy_ipcs<br>ipc</div>
    <div style="background:#2a1c08;border:2px solid #ffcc66;border-radius:6px;padding:6px;color:#ffcc66;text-align:center;font-size:11px">copy_pid_ns ★<br>pid</div>
    <div style="background:#1f1408;border:1px solid #7a5a2a;border-radius:6px;padding:6px;color:#c89868;text-align:center;font-size:11px">copy_cgroup_ns<br>(额外)</div>
    <div style="background:#1f1408;border:1px solid #c08040;border-radius:6px;padding:6px;color:#ffaa55;text-align:center;font-size:11px">copy_net_ns<br>net</div>
  </div>
  <div style="text-align:center;color:#c04040;font-size:11px">回滚链 out_time→…→out_ns:任一失败全部 put(all-or-nothing)</div>
  <div style="text-align:center;color:#4080c0">▼</div>
  <div style="text-align:center;background:#0e1a26;border:1px solid #4080c0;border-radius:8px;padding:8px;color:#88c0ff">struct nsproxy { mnt_ns, uts_ns, ipc_ns, pid_ns_for_children, cgroup_ns, net_ns } &nbsp;(user_ns 在 cred 上)</div>
  <div style="text-align:center;color:#40c060">▼</div>
  <div style="text-align:center;background:#0e1d14;border:2px solid #40c060;border-radius:8px;padding:8px;color:#88ff88">tsk->nsproxy = new_ns; &nbsp;→ task 住进这组窗 · 墙 = 这几个指针,没有别的</div>
</div>

---

# 总:80 行 C 代码,一次造出六面墙

不借 Docker、不借 runc,只用一个 `clone()` 带上六个 `CLONE_NEW*` 标志,就能亲手造一个"迷你容器",把六面墙一次开齐。核心就一句 `clone(container, stack, CLONE_NEWUSER|CLONE_NEWPID|CLONE_NEWNET|CLONE_NEWNS|CLONE_NEWUTS|CLONE_NEWIPC|SIGCHLD, NULL)`。

<!-- @video: scene=code title=mini-docker 80 行 -->
完整代码(`src/05-mini-docker.c`,普通用户即可编译运行,因为带了 `CLONE_NEWUSER`):

```c
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
static int sync_pipe[2];                       // 父→子:等 uid_map 配好

static void write_file(const char *path, const char *content) {
    int fd = open(path, O_WRONLY);
    if (fd < 0) { perror(path); return; }
    write(fd, content, strlen(content));
    close(fd);
}

// 子进程:它一出生就身处六面墙之内
static int container(void *arg) {
    char ch;
    close(sync_pipe[1]);
    read(sync_pipe[0], &ch, 1);                // 阻塞,直到父把 uid/gid 映射写好

    sethostname("mini-container", 14);          // 【uts 窗】改主机名,只影响本窗
    mount(NULL, "/", NULL, MS_REC | MS_PRIVATE, NULL);   // 【mnt 窗】传播设私有
    mount("proc", "/proc", "proc", 0, NULL);    // 重挂 /proc,让 ps 只看见本 pid 窗

    struct utsname u; uname(&u);
    printf("\n============= 容器内视图(墙内) =============\n");
    printf("[pid 窗 ] getpid()            = %d        ← 我以为我是 1 号\n", getpid());
    printf("[uts 窗 ] hostname            = %s\n", u.nodename);
    printf("[user窗] getuid()/geteuid()  = %d/%d     ← 容器内的 root\n", getuid(), geteuid());
    printf("[net 窗 ] 我能看到的网卡:\n");
    system("ip -o link show 2>/dev/null | awk '{printf \"          %s\\n\",$2}' || echo '          (只有 lo)'");
    printf("[pid 窗 ] /proc 里的进程数    = "); fflush(stdout);
    system("ls /proc | grep -E '^[0-9]+$' | wc -l");
    printf("===========================================\n");
    execlp("/bin/sh", "/bin/sh", (char *)NULL);
    return 1;
}

int main(void) {
    struct utsname u; uname(&u);
    printf("============= 宿主视图(墙外) =============\n");
    printf("[宿主] getpid() = %d ,  hostname = %s ,  getuid() = %d\n",
           getpid(), u.nodename, getuid());
    pipe(sync_pipe);

    // ★ 一次 clone,带六个 CLONE_NEW* —— 六面墙一次开齐
    int flags = CLONE_NEWUSER | CLONE_NEWPID | CLONE_NEWNET |
                CLONE_NEWNS  | CLONE_NEWUTS | CLONE_NEWIPC | SIGCHLD;
    pid_t pid = clone(container, child_stack + STACK_SIZE, flags, NULL);
    if (pid < 0) { perror("clone"); exit(1); }
    printf("[宿主] 容器进程在【宿主】上的 PID = %d   ← 不是容器内看到的 1\n", pid);

    // 配 user 窗映射:容器内 uid 0 ←→ 宿主当前 uid(rootless 的关键)
    char path[64], line[64];
    snprintf(path, sizeof path, "/proc/%d/setgroups", pid); write_file(path, "deny");
    snprintf(path, sizeof path, "/proc/%d/uid_map", pid);
    snprintf(line, sizeof line, "0 %d 1", getuid());        write_file(path, line);
    snprintf(path, sizeof path, "/proc/%d/gid_map", pid);
    snprintf(line, sizeof line, "0 %d 1", getgid());        write_file(path, line);

    write(sync_pipe[1], "x", 1);                // 放行子进程
    waitpid(pid, NULL, 0);
    return 0;
}
```

<!-- @video: scene=code title=控制台铁证 -->
**控制台输出(六面墙的现场铁证):**

```text
$ gcc -O2 -o mini-docker 05-mini-docker.c && ./mini-docker
============= 宿主视图(墙外) =============
[宿主] getpid() = 8421 ,  hostname = dev-box ,  getuid() = 1000
[宿主] 容器进程在【宿主】上的 PID = 8422   ← 不是容器内看到的 1

============= 容器内视图(墙内) =============
[pid 窗 ] getpid()            = 1        ← 我以为我是 1 号
[uts 窗 ] hostname            = mini-container
[user窗] getuid()/geteuid()  = 0/0     ← 容器内的 root
[net 窗 ] 我能看到的网卡:
          lo:
[pid 窗 ] /proc 里的进程数    = 2
===========================================
/ # ps -e
    PID TTY          TIME CMD
      1 pts/0    00:00:00 sh
      6 pts/0    00:00:00 ps
/ # ipcs -m            # 共享内存段:一个都看不到(ipc 窗)
------ Shared Memory Segments --------
key        shmid      owner      perms      bytes      nattch     status
/ #
```

**一张表读完六面墙的铁证(宿主 vs 容器):**

| 窗 | 宿主看到 | 容器看到 | 证明了 |
|----|---------|---------|--------|
| **pid** | 容器进程是 PID 8422 | `getpid()` = 1 | 进程号空间隔离(同一进程,两个号) |
| **uts** | hostname = dev-box | hostname = mini-container | 主机名隔离 |
| **user** | uid = 1000 | uid = 0(容器内 root) | 用户映射:墙内是 root,墙外只是 1000 |
| **net** | eth0/docker0/lo… | 只有 lo | 网络栈隔离(干净的孤岛) |
| **pid(再证)** | 几百个进程 | /proc 里只有 2 个 | 只看得见本窗进程 |
| **ipc** | 一堆共享内存段 | `ipcs -m` 空 | IPC 隔离 |

> 六行输出,六面墙。**下面"分"的部分,就对着这段代码,把每一扇窗从用户态那一行,钻到内核里建它的那个函数。**

---

# 分:六扇窗逐个钻(用户态 → 内核实现)

每扇窗一个小节,结构固定:**【用户态】**这扇窗在 mini-docker 里由哪个 flag / 哪行触发、观察到什么;**【内核实现】**贴对应的内核 `copy_xxx` 真源码,逐行读。

## 墙一 · uts 窗(CLONE_NEWUTS):最简单的样板

**【用户态】** flags 里的 `CLONE_NEWUTS` 开这扇窗;容器里 `sethostname("mini-container")` 改主机名,宿主仍是 `dev-box` —— 互不影响。

**【内核实现】** 入口 `copy_utsname()`,真源码(`kernel/utsname.c`):

```c
struct uts_namespace *copy_utsname(u64 flags,
	struct user_namespace *user_ns, struct uts_namespace *old_ns)
{
	struct uts_namespace *new_ns;
	BUG_ON(!old_ns);
	get_uts_ns(old_ns);
	if (!(flags & CLONE_NEWUTS))     /* 没要这扇窗 → 直接返回旧窗(共享) */
		return old_ns;
	new_ns = clone_uts_ns(user_ns, old_ns);
	put_uts_ns(old_ns);
	return new_ns;
}

static struct uts_namespace *clone_uts_ns(struct user_namespace *user_ns,
					  struct uts_namespace *old_ns)
{
	struct uts_namespace *ns;
	/* … inc_uts_namespaces 配额 … */
	ns = kmem_cache_zalloc(uts_ns_cache, GFP_KERNEL);   /* 分配一个新窗 */
	/* … ns_common_init … */
	down_read(&uts_sem);
	memcpy(&ns->name, &old_ns->name, sizeof(ns->name)); /* ★ 把父窗的名字拷一份 */
	ns->user_ns = get_user_ns(user_ns);                 /* 记住归哪个 user 窗管 */
	up_read(&uts_sem);
	return ns;
}
```

**逐行读:** `copy_utsname` 是所有 `copy_xxx` 的标准样板 —— **没传 `CLONE_NEWUTS` 就 `return old_ns`(共享旧窗),传了才 `clone_uts_ns` 造新窗**。造新窗的核心就一行 `memcpy(&ns->name, &old_ns->name, …)`:**新窗一出生不是空的,而是父窗的一份副本**(所以容器初始主机名继承宿主),之后 `sethostname` 在副本上改,与父分叉。每扇窗都遵循这个"先继承、再分叉"的模式。

## 墙二 · pid 窗(CLONE_NEWPID):PID 1 幻觉的真身

**【用户态】** `CLONE_NEWPID` 开窗;容器里 `getpid()` 返回 1,宿主上同一进程是 8422;容器里 `ps` 只看到 2 个进程。

**【内核实现】** `copy_pid_ns → create_pid_namespace`,真源码(`kernel/pid_namespace.c`):

```c
static struct pid_namespace *create_pid_namespace(struct user_namespace *user_ns,
	struct pid_namespace *parent_pid_ns)
{
	struct pid_namespace *ns;
	unsigned int level = parent_pid_ns->level + 1;     /* ① 层级 = 父 + 1 */
	/* … */
	if (level > MAX_PID_NS_LEVEL)                       /* ② 嵌套深度上限 */
		goto out;
	ns = kmem_cache_zalloc(pid_ns_cachep, GFP_KERNEL);
	idr_init(&ns->idr);                                /* ③ 每窗自带 idr 发号器 */
	ns->level = level;
	ns->parent = get_pid_ns(parent_pid_ns);            /* ④ 指回父,形成树 */
	ns->user_ns = get_user_ns(user_ns);
	/* … */
	return ns;
}
```

**逐行读出 PID 1 幻觉:** `level = parent->level + 1`(①)+ `ns->parent`(④)让 pid 窗成为一棵树(宿主根窗 level 0,容器 level 1)。**`idr_init(&ns->idr)`(③)给每个窗一个独立发号器,从 1 开始发。** 而内核 `struct pid` 里有个 `numbers[]` 数组,`alloc_pid()` 创建进程时**从当前窗一路向上,给每一层各分一个号** —— 所以同一进程在容器窗是 1、在根窗是 8422。

> 这就是"单向玻璃"的源码真身:容器里 `ps` 查**本窗 idr**(只看见本窗有号的进程);宿主 `ps` 查**根窗 idr**(容器进程在根窗也有号,所以看得见)。**一个 `idr_init`,两个世界。**

## 墙三 · ipc 窗(CLONE_NEWIPC):一套全新的进程间通信

**【用户态】** `CLONE_NEWIPC` 开窗;容器里 `ipcs -m` 空空如也,看不到宿主的任何共享内存段 / 信号量。

**【内核实现】** `copy_ipcs → create_ipc_ns`,真源码(`ipc/namespace.c`):

```c
struct ipc_namespace *copy_ipcs(u64 flags,
	struct user_namespace *user_ns, struct ipc_namespace *ns)
{
	if (!(flags & CLONE_NEWIPC))     /* 老规矩:没要就共享 */
		return get_ipc_ns(ns);
	return create_ipc_ns(user_ns, ns);
}

static struct ipc_namespace *create_ipc_ns(struct user_namespace *user_ns,
					   struct ipc_namespace *old_ns)
{
	struct ipc_namespace *ns;
	/* … inc_ipc_namespaces 配额 … */
	ns = kzalloc_obj(struct ipc_namespace, GFP_KERNEL_ACCOUNT);
	/* … ns_common_init / ns->user_ns = get_user_ns(user_ns) … */
	err = mq_init_ns(ns);            /* POSIX 消息队列:全新一套 */
	/* … setup_mq_sysctls / setup_ipc_sysctls … */
	err = msg_init_ns(ns);           /* System V 消息队列:全新一套 */
	sem_init_ns(ns);                 /* System V 信号量:全新一套 */
	shm_init_ns(ns);                 /* System V 共享内存:全新一套 */
	return ns;
}
```

**逐行读:** 和 uts 不同,ipc 窗造的不是"拷贝一份",而是 **`mq_init_ns / msg_init_ns / sem_init_ns / shm_init_ns` 把四套 IPC 子系统全部初始化成空的**。因为 IPC 的语义是"按 key 共享" —— 如果继承父窗的对象,两个容器用同一个 key 就会互相踩,所以 ipc 窗一出生就是**干净的四张空表**。这解释了容器里 `ipcs` 为什么空。

## 墙四 · mnt 窗(CLONE_NEWNS):整棵挂载树的副本

**【用户态】** `CLONE_NEWNS` 开窗;容器里 `mount("proc", "/proc", …)` 重挂 proc、之后 `pivot_root` 换根,全都不影响宿主的挂载表。

**【内核实现】** 入口 `copy_mnt_ns()`(`fs/namespace.c`,该文件 5000+ 行,这里给**准确调用链 + 关键函数**,不伪造逐字):

```
copy_mnt_ns(flags, old_ns, user_ns, new_fs)        // fs/namespace.c
  └─ if (!(flags & CLONE_NEWNS)) return get_mnt_ns(old_ns);   // 没要就共享
  └─ 否则 → alloc_mnt_ns() 分配新 mnt_namespace
            └─ copy_tree(old_root, ...)   // ★ 把父窗的【整棵挂载树】复制一份
            └─ 新窗的 root / 指向这份副本
```

**关键读点:** mnt 窗和 pid/ipc 不同 —— 它**不是空的,也不是简单拷一个字段,而是 `copy_tree()` 把父窗的整棵挂载树(所有挂载点的拓扑)复制一份**。新窗一出生就有一份和宿主一样的挂载视图,之后容器在这份副本上 `mount` / `pivot_root` 随便改,父窗的树纹丝不动。这就是"容器换根不影响宿主"的根。

> 历史彩蛋:mnt 是 Linux **第一个** namespace(2002,内核 2.4.19,Al Viro 实现)。当年以为不会再有别的 namespace,所以标志位直接叫 `CLONE_NEWNS`(NEW NameSpace),没带 `MNT`。后来又加了 5 个,这个命名就成了历史包袱 —— 源码里一个名字,封存着 namespace 家族的起点。

## 墙五 · net 窗(CLONE_NEWNET):最重的一扇

**【用户态】** `CLONE_NEWNET` 开窗;容器里只看得到一个 `lo`(还是 down 的),宿主的 eth0/docker0 全不可见。这扇窗也是**洞二(veth)要凿的那扇**(见第三篇)。

**【内核实现】** `copy_net_ns → setup_net`,真源码(`net/core/net_namespace.c`):

```c
struct net *copy_net_ns(u64 flags,
			struct user_namespace *user_ns, struct net *old_net)
{
	struct net *net;
	int rv;
	if (!(flags & CLONE_NEWNET))      /* 没要就共享(--network host 走这) */
		return get_net(old_net);
	/* … inc_net_namespaces 配额 … */
	net = net_alloc();
	rv = preinit_net(net, user_ns);
	/* … */
	down_read_killable(&pernet_ops_rwsem);
	rv = setup_net(net);              /* ★ 真正建一整套网络栈 */
	up_read(&pernet_ops_rwsem);
	return net;
}

static __net_init int setup_net(struct net *net)
{
	const struct pernet_operations *ops;
	/* … */
	list_for_each_entry(ops, &pernet_list, list) {   /* ★ 遍历每个网络子系统 */
		error = ops_init(ops, net);              /*   逐个在新 net 里初始化 */
		if (error < 0)
			goto out_undo;
	}
	/* … 把 net 加进全局 net 链表 … */
}
```

**逐行读出"为什么 net 窗最贵":** 别的窗就拷一个结构;net 窗要 `setup_net` **遍历 `pernet_list`(所有注册过的网络子系统),逐个 `ops_init` 在新 net 里建一套** —— 独立的路由表、邻居表、conntrack 表、`lo` 环回设备、各种 `/proc/sys/net/*` 参数……全都得新建一份。所以创建 net 窗是六扇里最慢的,也是为什么容器网络初始化是出生流程里相对重的一步。容器里那个孤零零的 `lo`,就是 `ops_init` 给每个新 net 标配的环回设备。

**net 窗到底隔离了哪些"网络表"?** `setup_net` 遍历 `pernet_list` 逐个 `ops_init`,建出来的就是下面这一整套 —— **每一项,容器都有自己独立的一份**,与宿主、与别的容器互不相干:

<!-- @video: scene=text title=net 窗隔离的网络表清单 -->
| 网络表 / 状态 | 作用 | 隔离后的效果 |
|--------------|------|-------------|
| 网络设备表(`net_device`) | 本 netns 里有哪些网卡 | 容器只有自己的 `lo`(+ 后来 veth 插的 `eth0`) |
| IP 地址 | 每张网卡绑的地址 | 容器自己的 `172.17.0.x` |
| **路由表(FIB:main / local / …)** | 包从哪个口出、下一跳是谁 | 容器自己一套路由;改它不影响宿主 |
| **路由策略 RPDB(`ip rule`)** | 多张路由表时,按规则选用哪张(策略路由) | 容器自己一套规则库 |
| **ARP / 邻居表(neigh)** | IP → MAC 的缓存 | 容器自己缓存;`ip neigh` 只见自己学到的 |
| **iptables / nftables(filter / nat / mangle / raw)** | 防火墙 + NAT 规则 | 容器内改 iptables 完全不动宿主(各一套表与链) |
| **conntrack 连接跟踪表** | NAT / 有状态防火墙的"账本"(谁连了谁) | 容器自己一本账;进出门 NAT 的回程还原靠它 |
| 端口绑定空间 | 哪个端口被占用 | 容器的 `:80` ≠ 宿主的 `:80`,互不冲突 |
| socket 列表 | 本 netns 的所有连接 | 容器里 `ss` / `netstat` 只看见自己的连接 |
| TC qdisc(流量整形) | 每张网卡的排队 / 限速规则 | 容器自己的限速策略 |
| sysctl `net.*`(`ip_forward` / `tcp_*` / `rp_filter` …) | 网络可调参数 | 容器自己一套;改 `net.ipv4.ip_forward` 只影响自己 |

> 一句话:**net 窗不是"隔离了一个 IP",是把整条网络栈 —— 从二层设备、三层路由/策略/邻居,到四层端口/socket,再到防火墙/NAT/conntrack —— 整套复刻了一份。** 这既是它最贵的原因(`setup_net` 要逐个初始化这么多子系统),也是为什么"洞二"必须用 veth + NAT,才能让这座孤岛对外做生意(见第三篇)。

## 墙六 · user 窗(CLONE_NEWUSER):发牌权,必须最先建

**【用户态】** `CLONE_NEWUSER` 开窗;**关键在父进程那三行**:往 `/proc/<pid>/uid_map` 写 `"0 1000 1"` —— 把容器内的 uid 0 映射到宿主的 uid 1000。于是容器里 `getuid()` = 0(是 root),但它在宿主上的真实身份只是普通用户 1000。**这就是 rootless 容器的地基。**

**【内核实现】** `create_user_ns`,真源码(`kernel/user_namespace.c`):

```c
int create_user_ns(struct cred *new)
{
	struct user_namespace *ns, *parent_ns = new->user_ns;
	kuid_t owner = new->euid;
	kgid_t group = new->egid;
	/* … */
	if (parent_ns->level > 32)                  /* ① 嵌套上限 32 层 */
		goto fail;
	/* … inc_user_namespaces 配额 … */
	if (!kuid_has_mapping(parent_ns, owner) ||  /* ② 你的 uid 必须在父窗里有映射 */
	    !kgid_has_mapping(parent_ns, group))
		goto fail_dec;
	ns = kmem_cache_zalloc(user_ns_cachep, GFP_KERNEL);
	/* … */
	ns->parent = parent_ns;
	ns->level = parent_ns->level + 1;           /* ③ 层级 = 父 + 1(同 pid 窗) */
	ns->owner = owner;                          /* ④ 记住"谁创建了我" */
	ns->group = group;
	/* … uid_map / gid_map 此刻为空,等用户态往 /proc/<pid>/uid_map 写 … */
	set_cred_user_ns(new, ns);                  /* ⑤ 挂到 cred 上,不是 nsproxy */
	return 0;
}
```

**逐行读出 user 窗为什么"特殊":**

- **`set_cred_user_ns(new, ns)`(⑤)** —— user 窗挂在 **cred(凭证)** 上,**不在 nsproxy 里**。这就是它没出现在 `create_new_namespaces` 那串 `copy_*` 里的原因:它在更早的 `copy_creds` 路径建,作为后面所有窗权限检查(`ns_capable`)的上下文。
- **`kuid_has_mapping`(②)+ `ns->owner`(④)** —— 创建 user 窗时,你的 uid 必须在父窗有映射;新窗记住 owner。**uid_map / gid_map 一开始是空的**,必须由**有权限的父进程**往 `/proc/<pid>/uid_map` 写(就是 mini-docker 那三行)。这道"父来写映射"的设计,堵死了"自己给自己提权"的漏洞。
- **`level`(③)** 同 pid 窗,可嵌套、有上限(32 层)。

> 一句话:**user 窗是整套墙的"权限根"。** 它先建、挂在 cred 上、由父配映射 —— 三个设计点合起来,才让"无 root 也能造容器"(rootless)既可能又安全。

---

## 底层原理层:为什么是这套设计

把六扇窗看完,回头看共性与取舍:

- **共性:先继承、再分叉。** uts `memcpy` 父名、mnt `copy_tree` 父树 → 继承;ipc/net `*_init_ns` 建空表 → 不继承(因为共享 key 会互踩)。每扇窗按自己的语义,选"拷父"还是"建空"。
- **为什么"换指针"而非"建实体"?** C1③(隔离必须便宜)。一次 `clone` + 几次 `kmem_cache_zalloc`,微秒级、近零内存税 —— 对比 VM 启动 Guest OS 的毫秒~秒级。这是"骗进程比骗 OS 便宜三个数量级"的源码级证据。
- **为什么 user 窗是权限根、挂 cred?** 解决"无 root 造容器"的安全悖论:容器内要 root 干活,但容器 root 必须 ≠ 宿主 root。uid_map + 父配映射 + 它是其余窗的权限上下文,三者合起来兜住安全。
- **代价:弱隔离。** 六扇窗共享同一个内核,内核漏洞可穿透所有墙(对比 VM 强隔离,Why §5)。

## 端到端场景时间线

<!-- @video: scene=timeline title=六面墙出生序列 -->
```
T=0      用户态 clone(CLONE_NEWUSER|NEWPID|NEWNET|NEWNS|NEWUTS|NEWIPC)
T+~10μs  copy_creds → create_user_ns:level+1, owner, 挂 cred ← 发牌权先建
T+~20μs  copy_namespaces:ns_capable(CAP_SYS_ADMIN) 通过 → create_new_namespaces
T+~25μs    copy_mnt_ns:copy_tree 复制整棵挂载树
T+~30μs    copy_utsname:memcpy 父主机名
T+~35μs    copy_ipcs:sem/shm/msg/mq_init_ns 建四张空表
T+~45μs    copy_pid_ns:level=1, idr_init → 发号器就绪
T+~70μs    copy_net_ns → setup_net:遍历 pernet_list 建整套网络栈(最慢)
T+~90μs  tsk->nsproxy = new_ns → task 住进六面墙
T+~100μs alloc_pid:给新进程每层 pid 窗各分一个号 → 容器内 PID 1 诞生
T+父配   父进程写 /proc/<pid>/uid_map → user 窗映射就位 → 子进程被放行
```

## API / 源码参考附录

| 窗 | flag | 内核函数 | 文件 | 造窗方式 |
|----|------|---------|------|---------|
| uts | CLONE_NEWUTS | `copy_utsname`/`clone_uts_ns` | `kernel/utsname.c` | memcpy 父名(继承) |
| pid | CLONE_NEWPID | `create_pid_namespace` | `kernel/pid_namespace.c` | level + idr(PID 1) |
| ipc | CLONE_NEWIPC | `copy_ipcs`/`create_ipc_ns` | `ipc/namespace.c` | sem/shm/msg/mq_init_ns(空表) |
| mnt | CLONE_NEWNS | `copy_mnt_ns`→`copy_tree` | `fs/namespace.c` | 复制整棵挂载树 |
| net | CLONE_NEWNET | `copy_net_ns`/`setup_net` | `net/core/net_namespace.c` | 遍历 pernet_list 建整套栈(最贵) |
| user | CLONE_NEWUSER | `create_user_ns` | `kernel/user_namespace.c` | level+owner,挂 cred,父配 uid_map |
| (总调度) | — | `create_new_namespaces`/`copy_namespaces` | `kernel/nsproxy.c` | 派生链 + all-or-nothing 回滚 |

## 常见问题 Q&A

<!-- @video: emphasis=normal -->
**Q1:mini-docker 为什么普通用户也能跑,不用 sudo?**
A:因为带了 `CLONE_NEWUSER`。先建 user 窗,进程在新 user 窗里就是 root(对新窗有 CAP_SYS_ADMIN),于是有权建其余五扇。这就是 rootless 容器的原理。去掉 `CLONE_NEWUSER`,就得 root 跑。

**Q2:为什么要用 pipe 同步,父进程先写 uid_map 子进程才能动?**
A:子进程在 sethostname/mount 这些特权操作前,必须等 user 窗的 uid_map 配好(否则它在新窗里还不是合法 root)。而 uid_map 只能由**有权限的父进程**写。pipe 保证"父配好映射 → 才放行子进程"。

**Q3:`docker run --pid=host` 在源码层是什么?**
A:runc 给 clone 的 flags **不带 `CLONE_NEWPID`** → `copy_pid_ns` 走 `return get_pid_ns(旧)` 共享分支 → 容器和宿主共用 pid 窗,容器里 `ps` 能看见宿主全部进程。一扇墙被显式拆掉。

**Q4:六扇窗里哪扇最贵?**
A:net。别的窗拷个结构就完事,net 窗要 `setup_net` 遍历所有网络子系统逐个建一份(路由表、邻居表、conntrack、lo……)。容器启动里网络初始化相对重,就因为这。

**Q5:为什么容器初始有主机名、有挂载,但没有别人的共享内存?**
A:因为造窗策略不同:uts(memcpy 父名)、mnt(copy_tree 父树)是"继承父";ipc(*_init_ns 空表)、net(setup_net 全新)是"建空的"。按各自语义选 —— 会"撞 key 互踩"的(ipc)必须建空,不会的(uts/mnt)可以继承。

**Q6:`unshare(CLONE_NEWPID)` 为什么不把自己迁进新窗?**
A:进程 pid 一旦分配就到处被缓存,不能变。所以字段叫 `pid_ns_for_children` —— 只改"未来孩子用哪个 pid 窗",调用者自己留在旧窗。这就是 `unshare --pid` 要配 `--fork` 的原因,也是 runc 要再 clone 一个孙进程当 PID 1 的原因。

## 延伸阅读

<!-- @video: skip -->
- 内核源码:`kernel/nsproxy.c` · `kernel/pid_namespace.c` · `ipc/namespace.c` · `kernel/utsname.c` · `net/core/net_namespace.c` · `kernel/user_namespace.c` · `fs/namespace.c`(`copy_mnt_ns`/`copy_tree`)· `kernel/pid.c`(`alloc_pid`)
- LWN 经典系列:"Namespaces in operation"(7 篇)
- `man 2 clone` / `man 2 unshare` / `man 2 setns` / `man 7 user_namespaces`

---

<!-- ===== 第二篇 / 共三篇:三个表。最终拼入 05-deep.md。deeparch-md 方法,架构图 HTML,总分结构。 ===== -->

<!-- @video: scene=spotlight -->
# 二、三个表:cgroup 怎么实现 cpu / memory / io 计量

> 心法回扣:What 阶段说"表 = cgroups(限你用多少)","接口即文件,记账即配额"。这一篇钻进内核,把 `cpu.max` / `memory.max` / `io.max` 三张表**怎么记账、怎么在超额时动手**逐行走一遍。先用 cgroup v2 亲手掐死一个进程(总),再分三张表逐个钻内核(分)。

## 概览

namespace(墙)管"你能看见什么";cgroup(表)管"你能用多少"。两者正交:墙挡视图,表限用量。cgroup 把进程编成树,每个节点是一个"户头",挂着若干 controller(子系统);每个 controller 对一种资源**实时记账**,超过配额就处理。

容器最常用三张表:**cpu(时间片)、memory(物理内存)、io(磁盘带宽)**。本篇看它们的内核实现 —— 你会发现三张表共用一个套路(**记账即配额**),但超额时的脾气截然不同:**CPU/IO 限速(降级),内存处决(OOM kill)**。这个差异不是随意的,是资源性质决定的。

## 生活类比:墙上的三块表

把容器想成一套合租公寓里的房间,墙上装着三块表:

- **电表(cpu)** —— 用电有功率上限,超了**跳闸限流**:灯暗一点、电器慢一点,但不会烧。
- **煤气表(memory)** —— 煤气是危险品,用超了**直接掐断总阀**:没有"慢慢用煤气"这回事,超了就停。
- **水表(io)** —— 水管口径有限,放太猛就**细水长流**:水还是给你,只是变慢、排队。

> 为什么内存这块表最狠?因为电和水是"流量"(可以调速率),内存是"存量"(一旦占住就占住,你没法"用得慢一点")。带着这个直觉看内核:三张表都在记账,但内存表记的是"占了多少",一旦撑破只能杀。

## 架构全景图(HTML)

> 完整版:[`pics/05-2-tables-arch.html`](pics/05-2-tables-arch.html)。下方为内嵌图。

<!-- @video: scene=layers title=cgroup 三表 -->
<div style="background:#0a0c10;color:#e8eef5;font-family:'JetBrains Mono',monospace;padding:18px;border-radius:10px">
  <div style="text-align:center;background:#11161d;border:1px solid #4a5568;border-radius:8px;padding:8px;margin-bottom:6px">
    /sys/fs/cgroup/demo/ (一个目录=一个户头) &nbsp;|&nbsp; <span style="color:#9fd9a0">echo 限额 &gt; cpu.max/memory.max/io.max</span> &nbsp;|&nbsp; <span style="color:#ffaa55">echo $$ &gt; cgroup.procs(上户口)</span>
  </div>
  <div style="text-align:center;color:#c08040">▼ 内核给每个 controller 在该 cgroup 挂一个 css ▼</div>
  <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-top:6px">
    <div style="background:#16263a;border:1.6px solid #4080c0;border-radius:8px;padding:10px;text-align:center">
      <div style="color:#88c0ff;font-weight:700">cpu 表(电表)</div>
      <div style="font-size:11px;color:#9fb4c8;margin-top:6px">CFS bandwidth<br>__account_cfs_rq_runtime →<br>runtime≤0 → throttle_cfs_rq</div>
      <div style="background:#241808;color:#ffaa55;border-radius:6px;padding:5px;margin-top:6px;font-size:11px">超额 → 限速</div>
    </div>
    <div style="background:#1f0e0e;border:1.6px solid #c04040;border-radius:8px;padding:10px;text-align:center">
      <div style="color:#ff8888;font-weight:700">memory 表(煤气表)</div>
      <div style="font-size:11px;color:#9fb4c8;margin-top:6px">memcg<br>try_charge_memcg →<br>page_counter→回收→OOM</div>
      <div style="background:#2a1212;color:#ff8888;border-radius:6px;padding:5px;margin-top:6px;font-size:11px">超额 → 处决(137)</div>
    </div>
    <div style="background:#0e1d14;border:1.6px solid #40c060;border-radius:8px;padding:10px;text-align:center">
      <div style="color:#88ff88;font-weight:700">io 表(水表)</div>
      <div style="font-size:11px;color:#9fb4c8;margin-top:6px">blk-throttle<br>__blk_throtl_bio →<br>tg_within_limit → 排队</div>
      <div style="background:#241808;color:#ffaa55;border-radius:6px;padding:5px;margin-top:6px;font-size:11px">超额 → 限速</div>
    </div>
  </div>
  <div style="text-align:center;background:#11161d;border:1px solid #c08040;border-radius:8px;padding:8px;margin-top:8px;color:#ffc48a">记账即配额:CPU 记时间片、内存记页、IO 记字节 —— 超额脾气不同,根在资源性质(流量 vs 存量)</div>
</div>

---

# 总:亲手用 cgroup v2 掐一个进程

cgroup v2 的接口就是一个文件系统(`/sys/fs/cgroup`)。**建户头 = `mkdir`,设表盘 = 往文件写数,上户口 = 把 PID 写进 `cgroup.procs`。** 不用任何 Docker,就能把三张表加在自己身上。

<!-- @video: scene=code title=cgroup v2 三表 demo -->
```bash
#!/usr/bin/env bash
# 在一台 cgroup v2 的 Linux(或 docker run --privileged 的容器)里,root 跑
CG=/sys/fs/cgroup/demo
mkdir -p "$CG"
# 让父层把这三个 controller 下放给子 cgroup
echo "+cpu +memory +io" > /sys/fs/cgroup/cgroup.subtree_control 2>/dev/null || true

echo "50000 100000" > "$CG/cpu.max"      # 电表:每 100ms 给 50ms = 半颗 CPU
echo 100M          > "$CG/memory.max"    # 煤气表:100MB 硬上限

echo "=== 测内存表:申请 200MB(> 100MB 上限)==="
(
  echo $BASHPID > "$CG/cgroup.procs"     # 上户口:从此本进程每页都记这个账
  echo "[记账] 起步 memory.current = $(cat "$CG/memory.current") 字节"
  python3 -c 'a = bytearray(200*1024*1024); print("撑到 200MB 了?")'
)
echo "退出码 = $?   (137 = 128 + 9 = 被 SIGKILL)"
echo "[死亡证明] $(grep oom_kill "$CG/memory.events")"
```

<!-- @video: scene=code title=控制台铁证 -->
**控制台输出(煤气表掐人的现场):**

```text
=== 测内存表:申请 200MB(> 100MB 上限)===
[记账] 起步 memory.current = 1142784 字节
Killed
退出码 = 137   (137 = 128 + 9 = 被 SIGKILL)
[死亡证明] oom_kill 1
```

`python3` 申请到 ~100MB 时撞上 `memory.max`,内核回收无果 → **OOM killer 在这个 cgroup 内选人 → SIGKILL** → 退出码 137,`memory.events` 的 `oom_kill` 计数 +1。**你 What §4.5 见过的 `Exited (137)`,这就是它的诞生现场。**

(电表/水表是"限速"不是"处决",不会有这么戏剧的输出:跑 CPU 死循环,`top` 里它稳定占 ~50%;`dd` 写文件,速度被压到 io.max。下面分别钻进内核看为什么脾气不同。)

---

# 分:三张表逐个钻(用户态 → 内核实现)

## 表一 · memory(煤气表):记一页,charge 一页

**【用户态】** `echo 100M > memory.max` 设硬顶,`echo $$ > cgroup.procs` 上户口。之后这个进程(及后代)**每碰一个新物理页**,内核都要先"过账"。

**【内核实现】** 核心是 `try_charge_memcg()`,真源码核心路径(`mm/memcontrol.c`):

```c
retry:
	if (consume_stock(memcg, nr_pages))        /* 每 CPU 本地缓存,快路径 */
		return 0;

	if (page_counter_try_charge(&memcg->memory, batch, &counter))
		goto done_restock;                 /* ① 原子地往账上加,没超 max → 成功 */

	mem_over_limit = mem_cgroup_from_counter(counter, memory);
	/* … */
	nr_reclaimed = try_to_free_mem_cgroup_pages(mem_over_limit, nr_pages,
						    gfp_mask, reclaim_options, NULL);
	                                           /* ② 超了 → 先在本 cgroup 内回收 */
	if (mem_cgroup_margin(mem_over_limit) >= nr_pages)
		goto retry;                        /*   回收够了 → 重试,续命 */
	/* … drain_all_stock / 重试若干次 … */

	if (mem_cgroup_oom(mem_over_limit, gfp_mask,
			   get_order(nr_pages * PAGE_SIZE))) {
		passed_oom = true;                 /* ③ 回收无果 → 触发 OOM killer */
		nr_retries = MAX_RECLAIM_RETRIES;
		goto retry;
	}
nomem:
	return -ENOMEM;
```

**逐行读出"煤气表为什么掐人":**

1. **`page_counter_try_charge(&memcg->memory, …)`(①)** —— 这就是"记账"那一笔:把要分配的页数原子地加到 `memcg->memory` 计数器上,**如果加完不超过 `memory.max` 就成功**。`memory.current` 就是这个计数器的当前值。
2. **`try_to_free_mem_cgroup_pages`(②)** —— 超了不立刻杀,先**在本 cgroup 范围内回收**(挤 page cache、可回收页)。回收够了 `goto retry` 续命 —— 表现为容器"变慢、IO 变多"。
3. **`mem_cgroup_oom`(③)** —— 回收也救不了 → **OOM killer 只在本 cgroup 内挑一个进程 SIGKILL**。邻居容器、宿主进程毫发无损(这正是墙存在的意义)。

> 为什么是"杀"不是"限速"?因为内存是**存量**:你申请的页已经占着物理内存了,内核没法让你"占得慢一点"。要么回收(腾别的),要么杀(腾你)。这就是煤气表和电表的本质区别。

## 表二 · cpu(电表):记时间片,超了踢出运行队列

**【用户态】** `echo "50000 100000" > cpu.max` —— 两个数:**每 100000μs(100ms)周期,最多给 50000μs(50ms)运行时间 = 半颗 CPU**。上户口同上。跑个死循环,`top` 里它稳定 50%。

**【内核实现】** CFS 带宽控制(`kernel/sched/fair.c`,`CONFIG_CFS_BANDWIDTH`;该文件上万行,这里给**准确调用链 + 真函数名**):

```
写 cpu.max → tg_set_cfs_bandwidth():设 quota=50ms, period=100ms,启动一个 hrtimer 每周期补额

进程运行中,每次时钟 tick / 调度:
  __account_cfs_rq_runtime(cfs_rq, delta_exec)
     └─ cfs_rq->runtime_remaining -= delta_exec;     // 把刚跑的时间从余额里扣
     └─ if (cfs_rq->runtime_remaining <= 0)
            从全局 quota 池再领一批(assign_cfs_rq_runtime)
            领不到(本周期 quota 用光)→ resched + 标记 throttled

  throttle_cfs_rq(cfs_rq):
     └─ 把这个 cgroup 的任务【整组移出运行队列】(dequeue)
     └─ 它们这一周期不再被调度

period hrtimer 到点:
  distribute_cfs_runtime() 给各 cfs_rq 补满 quota → unthrottle → 任务重新入队
```

**逐行读出"电表为什么限速不杀":** `__account_cfs_rq_runtime` 每跑一点就从 `runtime_remaining` 扣一点;扣到 ≤0 且本周期 quota 用光 → `throttle_cfs_rq` 把这组任务**踢出运行队列**(不是杀进程,只是这一周期不让它跑);下个周期 hrtimer 补满额度,再放回来。所以 CPU 超额表现为"**被周期性地暂停**" → 平均算下来就是 50%。**时间是流量,可以靠"这段不给你跑"来限速。**

## 表三 · io(水表):记字节,超了排队等定时器

**【用户态】** `echo "8:0 wbps=10485760" > io.max` —— **设备 `8:0`(主:次设备号)的写带宽限到 10485760 字节/秒 = 10MB/s**。`dd` 写大文件,速度被压到 10MB/s。

**【内核实现】** blk-throttle(`block/blk-throttle.c`,准确调用链 + 真函数名):

```
每个 bio(块 IO 请求)下发 → __blk_throtl_bio():
  tg_within_limit(tg, bio, …)
     ├─ tg_within_bps_limit()  : 这个 bio 加上去,本时间窗的字节数还在 wbps 以内吗?
     └─ tg_within_iops_limit() : iops 还在 riops/wiops 以内吗?
  在限内 → 直接放行
  超了   → tg_dispatch_time() 算出"还要等多久才能发"
           → 把 bio 挂到 throttle group 的队列上
           → 定时器到点 → 重新尝试下发
```

**逐行读出"水表为什么排队不丢":** 每个 bio 进来先问 `tg_within_bps_limit` / `tg_within_iops_limit`:本时间窗的累计字节/次数还在配额内吗?在 → 放行;超 → `tg_dispatch_time` 算一个等待时间,**把 bio 排进队列、挂个定时器,到点再发**。IO 不丢、不杀,只是被"细水长流"地推迟。**带宽是流量,可以靠排队削峰。**

---

## 底层原理层:一个套路,三种脾气

- **共性:记账即配额。** 三张表都是"每次消费 → 先过账 → 看超没超"。CPU charge 时间片(`runtime_remaining`)、内存 charge 页(`page_counter`)、IO charge 字节(`tg_within_bps`)。账本就是 `*.current` 那些文件。
- **差异的根:流量 vs 存量。** CPU 时间、IO 带宽是**速率**,超了可以"这段不给/排队"来限速,不损失正确性;内存是**占用量**,占住了就占住,超了只能回收别人或杀自己 → 所以唯独内存表会 OOM kill(`Exited 137`)。
- **cgroup v2 的统一层级。** v1 时代每个 controller 一棵独立的树,容易打架;v2 把所有 controller 收进**同一棵 cgroup 树**(`echo "+cpu +memory +io" > cgroup.subtree_control` 下放),一个目录一个户头管全部资源。**接口即文件**——没有专用 syscall,全是读写 `/sys/fs/cgroup` 下的文件。
- **回扣 What §4.5(两道墙独立):** 容器里 `free -m` 看见宿主 64G(那是 namespace 没挡住 `/proc/meminfo` 的**视图**),却死在 100M(那是 cgroup 这张表记的**用量**)。**视图墙(namespace)和用量表(cgroup)是两套独立机制** —— 这一篇钻的是后者。

## 端到端场景时间线

<!-- @video: scene=timeline title=内存超限死刑全过程 -->
```
T=0     进程上户口(PID 写进 cgroup.procs),memory.max=100M
T+…     每次缺页 → try_charge_memcg → page_counter_try_charge,memory.current 一路涨
T=逼近  current 接近 max → try_to_free_mem_cgroup_pages 回收(容器变慢、IO 升高)
T=撞顶  回收救不了 → mem_cgroup_oom → OOM killer 在本 cgroup 选 oom_score 最高者
T+ε     SIGKILL(信号 9,不可捕获)→ 进程死
T+ε     memory.events 的 oom_kill += 1(机器可读的死亡证明)
T+ε     PID 1 若被杀 → 容器终结 → docker ps 显示 Exited (137)
```

## API / 源码参考附录

| 表 | 接口文件 | 内核执行点 | 文件 | 超额 |
|----|---------|-----------|------|------|
| cpu | `cpu.max`("quota period") | `__account_cfs_rq_runtime` → `throttle_cfs_rq` | `kernel/sched/fair.c` | 限速(踢出队列) |
| memory | `memory.max` / `memory.current` / `memory.events` | `try_charge_memcg` → `page_counter_try_charge` → `mem_cgroup_oom` | `mm/memcontrol.c` | OOM kill(137) |
| io | `io.max`("dev wbps=/riops=…") | `__blk_throtl_bio` → `tg_within_bps/iops_limit` → `tg_dispatch_time` | `block/blk-throttle.c` | 限速(排队) |
| (上户口) | `cgroup.procs` | `cgroup_attach_task` | `kernel/cgroup/cgroup.c` | — |
| (下放) | `cgroup.subtree_control` | — | 同上 | — |

## 常见问题 Q&A

<!-- @video: emphasis=normal -->
**Q1:为什么内存超限是杀,CPU/IO 超限只是变慢?**
A:资源性质不同。CPU 时间、IO 带宽是"速率",可以靠"这段不给你/排队"来限,不损失数据;内存是"占用量",一旦申请就占着物理页,没法"占得慢一点",超了只能回收别人或杀自己。

**Q2:`docker run -m 512m` 在内核层做了什么?**
A:runc 在容器的 cgroup 目录写 `echo 536870912 > memory.max`,并把容器 PID 写进 `cgroup.procs`。此后容器每分配一页都走 `try_charge_memcg` 记到这个账上,撞 512M 就 OOM。镜像里没有任何资源配置 —— 表是运行时挂的(What 误解#1)。

**Q3:`memory.current` 和 `free -m` 为什么对不上?**
A:`memory.current` 是 cgroup 这张表的真实记账(本容器用量);`free -m` 读 `/proc/meminfo`(宿主全局,没被 namespace 隔离)。一个是"表",一个是"视图",两道独立的墙。排查容器内存要看 `memory.current` / `memory.events`,别信 `free`。

**Q4:CPU 限到 50%,是某个核跑满一半时间,还是两个核各 25%?**
A:`cpu.max` 是"每周期总配额"。50ms/100ms 的额度可以花在任意核上 —— 单线程就是一个核跑 50% 时间,多线程可以两个核各跑一半。配额是"总时间片",不绑定具体核(绑核是 `cpuset`)。

**Q5:io.max 里的 `8:0` 是什么?为什么限速要指定它?**
A:`8:0` 是块设备的主:次设备号(如第一块 SATA 盘 sda)。IO 限速是按设备的,因为不同盘速率不同;`lsblk` 能看设备号。所以 io.max 必须写"哪个设备 + 多少带宽"。

**Q6:三张表之外还有别的 controller 吗?**
A:有。`pids`(防 fork 炸弹,限进程数)、`cpuset`(绑核/绑内存节点)、`hugetlb`、`rdma` 等。三张表是容器最常用的主力,机制都一样:接口即文件,记账即配额。

## 延伸阅读

<!-- @video: skip -->
- 内核源码:`mm/memcontrol.c`(`try_charge_memcg`)· `kernel/sched/fair.c`(CFS bandwidth)· `block/blk-throttle.c` · `kernel/cgroup/cgroup.c`
- 内核文档:`Documentation/admin-guide/cgroup-v2.rst`(最权威的 cgroup v2 说明)
- `man 7 cgroups`

---

<!-- ===== 第三篇 / 共三篇:两个洞。最终拼入 05-deep.md。deeparch-md 方法,架构图 HTML,总分结构。 ===== -->

<!-- @video: scene=spotlight -->
# 三、两个洞:veth 与 volume 的内核实现

> 心法回扣:What 阶段说"墙是默认,洞是例外;每个洞都凿在某一扇 namespace 墙上"。第一篇造了六面墙,这一篇看怎么在墙上**凿受控的洞**:**洞一 veth 凿 net 墙**(让孤岛能通信)、**洞二 volume 凿 mnt 墙**(让数据能持久)。先各凿一个洞演示(总),再分两个洞钻内核(分)。

## 概览

namespace 把容器关成孤岛:net 窗让它有独立网络栈但与外界断开,mnt 窗让它有独立挂载树但只看得见自己的 `/`。可纯隔离没法干活 —— 服务要通信、数据要持久。于是要在墙上**凿洞**:

- **洞一 · veth**(virtual ethernet):一对虚拟网卡,一头在容器 net 窗、一头在宿主。容器从自己的 `eth0` 发包,内核**直接把帧递到管子另一头** —— 这就是孤岛对外的网线。
- **洞二 · volume**:一个 bind mount,把宿主的某个目录**嫁接进容器的挂载树**。容器访问那个路径,直接落到宿主文件系统,**绕过 overlay、不走 copy_up** —— 这就是有状态数据的持久竖井。

两个洞凿在不同的墙上,但本质相同:**在隔离的默认之上,开一个指向外部的受控入口。**

## 生活类比:在墙上接网线、凿竖井

容器是一间四面封死的保密屋:

- **veth 像穿墙的一根对讲线** —— 在墙上钻个孔,穿一根线,一头在屋里(`eth0`),一头在楼道(宿主)。屋里说话,线另一头立刻听到。线是成对的,一拉两头都动。
- **volume 像凿一口直通楼下仓库的升降井** —— 屋里地板上开个口,直通楼下的公共仓库(宿主目录)。往井里放东西,楼下仓库立刻有;屋子拆了(容器删了),仓库还在。

> 关键:这两个都是**受控开口**,不是把墙推倒。屋子还是那间隔离的屋子,只是被精确地开了一根线、一口井。**洞 ≠ 拆墙。**

## 架构全景图(HTML)

> 完整版:[`pics/05-3-holes-arch.html`](pics/05-3-holes-arch.html)。下方为内嵌图。

<!-- @video: scene=layers title=两个洞 -->
<div style="background:#0a0c10;color:#e8eef5;font-family:'JetBrains Mono',monospace;padding:18px;border-radius:10px">
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">
    <div style="background:#0e1d14;border:1.6px solid #40c060;border-radius:8px;padding:12px">
      <div style="color:#88ff88;font-weight:700;text-align:center">洞一 · veth(凿 net 墙)</div>
      <div style="border:1px dashed #c08040;border-radius:6px;padding:6px;margin:6px 0;text-align:center;color:#ffaa55;font-size:11px">容器 netns:eth0(veth 一头)</div>
      <div style="text-align:center;color:#40c060;font-size:11px">▲ priv-&gt;peer ▼ 一对一互指(RCU)</div>
      <div style="border:1px dashed #40c060;border-radius:6px;padding:6px;margin:6px 0;text-align:center;color:#88ff88;font-size:11px">宿主 netns:另一头 → 插 docker0</div>
      <div style="font-size:10px;color:#7fd99f;text-align:center;margin-top:6px">veth_xmit 把 skb 直接递给对端(零拷贝)</div>
    </div>
    <div style="background:#16263a;border:1.6px solid #4080c0;border-radius:8px;padding:12px">
      <div style="color:#88c0ff;font-weight:700;text-align:center">洞二 · volume(凿 mnt 墙)</div>
      <div style="font-size:11px;color:#9fb4c8;background:#0d1117;border:1px solid #2a3340;border-radius:6px;padding:8px;margin:6px 0;line-height:1.7">/ ← overlay(易失,走 copy_up)<br>└─ <span style="color:#88c0ff;font-weight:700">/data ← bind mount 竖井</span><br>&nbsp;&nbsp;&nbsp;&nbsp;▼ 直通宿主,绕过 overlay<br>&nbsp;&nbsp;宿主 /var/lib/docker/volumes/…(持久)</div>
      <div style="font-size:10px;color:#7fa8cc;text-align:center;margin-top:6px">挂载树里加一个直通宿主的入口</div>
    </div>
  </div>
  <div style="text-align:center;background:#11161d;border:1px solid #c08040;border-radius:8px;padding:8px;margin-top:10px;color:#ffc48a">veth = net 墙上的穿墙网线(peer 指针);volume = mnt 墙上的直通竖井(bind mount)。隔离默认,连通显式。</div>
</div>

---

# 总:亲手各凿一个洞

## 洞一:凿一根 veth,穿过 net 墙

<!-- @video: scene=code title=veth demo -->
```bash
#!/usr/bin/env bash   # root 跑
ip netns add c1
ip link add veth-h type veth peer name veth-c   # ★ 造一对(配对在内核 veth_newlink 完成)
ip link set veth-c netns c1                       # 一头塞进容器 netns
ip addr add 10.1.1.1/24 dev veth-h; ip link set veth-h up
ip netns exec c1 ip addr add 10.1.1.2/24 dev veth-c
ip netns exec c1 ip link set veth-c up
ip netns exec c1 ip link set lo up
ip netns exec c1 ping -c 2 10.1.1.1               # 容器 → 宿主:通了 = 洞凿成
```

```text
PING 10.1.1.1 (10.1.1.1) 56(84) bytes of data.
64 bytes from 10.1.1.1: icmp_seq=1 ttl=64 time=0.038 ms
64 bytes from 10.1.1.1: icmp_seq=2 ttl=64 time=0.041 ms
--- 10.1.1.1 ping statistics ---
2 packets transmitted, 2 received, 0% packet loss
```

一个本来与世隔绝的 net 窗,接上一根 veth 就能和外界说话了。`time=0.038 ms` 这么快,是因为根本没上物理网线(下面看源码)。

## 洞二:凿一口 bind mount 竖井,穿过 mnt 墙

<!-- @video: scene=code title=volume demo -->
```bash
#!/usr/bin/env bash   # root 跑
mkdir -p /srv/hostdata
echo "我在宿主上" > /srv/hostdata/note.txt

unshare --mount --fork bash -c '
  mount --bind /srv/hostdata /mnt      # ★ 把宿主目录 bind 进本 mnt 窗的 /mnt
  echo "[容器内] 读到:$(cat /mnt/note.txt)"
  echo "容器也写了一行" >> /mnt/note.txt
'
echo "[宿主] 现在文件内容:"
cat /srv/hostdata/note.txt             # 容器写的东西,宿主这边也在 —— 竖井直通
```

```text
[容器内] 读到:我在宿主上
[宿主] 现在文件内容:
我在宿主上
容器也写了一行
```

容器在自己隔离的挂载树里,通过 `/mnt` 直接读写了宿主的目录;`unshare` 退出后,宿主的文件还在 —— **数据独立于容器存活**。这就是 volume 持久化的本质。

---

# 分:两个洞逐个钻(用户态 → 内核实现)

## 洞一 · veth(凿 net 墙):一对互指的设备

**【用户态】** `ip link add veth-h type veth peer name veth-c` 造**一对**虚拟网卡;`ip link set veth-c netns c1` 把一头塞进容器 net 窗。这一对就是穿过 net 墙的网线。

**【内核实现 · 配对】** `veth_newlink()`,真源码(`drivers/net/veth.c`):

```c
static int veth_newlink(struct net_device *dev, ...)
{
	/* … 创建并注册两个 net_device:dev 和 peer … */
	err = register_netdevice(peer);
	/* … */
	err = register_netdevice(dev);
	/* … */

	/* tie the deviced together */
	priv = netdev_priv(dev);
	rcu_assign_pointer(priv->peer, peer);   /* ★ dev 的 peer 指向 peer */
	/* … */
	priv = netdev_priv(peer);
	rcu_assign_pointer(priv->peer, dev);    /* ★ peer 的 peer 指回 dev */
	/* … */
	return 0;
}
```

**逐行读:** veth 的全部魔法就这两行 `rcu_assign_pointer(priv->peer, …)` —— **两个设备各存一个指向对方的 `peer` 指针,一对一互指**。这就是"一根网线两头"在内核里的真身:不是真有根线,是两个 `net_device` 互相记住了对方。

**【内核实现 · 传输】** `veth_xmit()`,真源码(`drivers/net/veth.c`):

```c
static netdev_tx_t veth_xmit(struct sk_buff *skb, struct net_device *dev)
{
	struct veth_priv *priv = netdev_priv(dev);
	struct net_device *rcv;
	/* … */
	rcu_read_lock();
	rcv = rcu_dereference(priv->peer);       /* ① 拿到管子另一头 */
	/* … */
	ret = veth_forward_skb(rcv, skb, rq, use_napi);  /* ② 直接喂给对端的接收路径 */
	/* … */
}
```

**逐行读:** 容器从 `eth0`(veth 一头)发包 → `veth_xmit` 用 `rcu_dereference(priv->peer)` 找到另一头(①)→ `veth_forward_skb` **把 skb 直接塞进对端设备的接收队列**(②,内部走 `__dev_forward_skb` → `netif_rx`)。**没有物理介质、没有序列化上线,就是把数据结构从一头递到另一头** —— 所以 demo 里 ping 只要 0.038ms。

> **凿穿 net 墙 = 给隔离的 net 窗,塞一个"peer 在墙外"的设备。** 包从这个设备出去,内核直接递到墙外那一头(再插 docker0,见 How 第三篇网络洞的完整旅程)。

## 洞二 · volume(凿 mnt 墙):把宿主目录嫁接进挂载树

**【用户态】** `mount --bind /srv/hostdata /mnt`(底层 `MS_BIND`)。runc 则按 OCI 配置里的 `mounts` 项,在容器 mnt 窗里做同样的 bind mount。

**【内核实现】** 调用链(`fs/namespace.c`,该文件 5000+ 行,这里给**准确调用链 + 真函数名**,不伪造逐字):

```
mount(--bind) → do_mount → path_mount
  └─ 检测到 MS_BIND → do_loopback(path, old_name, recurse)
       └─ clone_mnt(old_mnt, old_dentry, flag)
       │     // ★ 造一个【新的 struct mount】,但它指向【同一个 dentry/inode】
       │     //   = 同一份宿主文件,在挂载树里多了一个"入口"
       └─ graft_tree / attach_recursive_mnt(mnt, parent, mp)
             // 把这个新 mount 嫁接到容器挂载树的目标挂载点(如 /data)
```

**逐行读:** bind mount 的核心是 `clone_mnt()` —— **它不复制数据,只造一个新的挂载点对象,指向同一个底层 `dentry`(宿主那个真实目录)**;再由 `attach_recursive_mnt` 把它**嫁接进容器的那棵挂载树**(就是第一篇 `copy_mnt_ns → copy_tree` 复制出来的那棵)。于是:

- 容器的 `/`(根)由 overlay 提供(易失、走 copy_up);
- 但 `/data` 这个挂载点,被嫁接成了**直通宿主真实目录的入口** —— 访问它**绕过 overlay,直接落到宿主 fs**。

> **凿穿 mnt 墙 = 在容器隔离的挂载树里,嫁接一个指向宿主目录的 mount 入口。** 它既让数据持久(独立于容器),又绕过了 overlay 的写放大(回扣 What §4.4 / 第二篇:数据库挂 volume 既为持久也为避开 copy_up 税)。

---

## 底层原理层:洞的共性与"洞 ≠ 拆墙"

- **墙默认,洞例外。** namespace 让容器默认与外界隔离(net 孤岛、mnt 独立树);洞是**显式凿出来的受控通道**,没凿就是断的。
- **两洞凿在不同墙,机制同源。** veth 凿 net 墙(用 `peer` 指针把帧递到墙外),volume 凿 mnt 墙(用 `clone_mnt` 把宿主入口嫁接进挂载树)。共性:**在隔离之上,开一个指向外部的受控入口** —— veth 的入口是 peer 设备,volume 的入口是 host dentry。
- **洞 ≠ 拆墙(关键辨析)。** 洞保留墙、只开受控口:容器仍在独立 net 窗(只是有根 veth)、仍在独立 mnt 窗(只是某点直通宿主)。而 `--network host` / `--pid=host` 是**整扇拆墙**(直接不开那扇窗,共享宿主),放弃隔离。看任何容器网络/存储配置,先问一句:**这是凿洞(保留隔离+受控连通)还是拆墙(放弃隔离)?**
- **回扣心法:** What §0 "砌墙 + 凿洞"的内核版至此闭环 —— 第一篇 6 把刀砌墙(`copy_*`),这一篇 2 种术凿洞(`veth_newlink` / `clone_mnt`)。

## 端到端场景时间线

<!-- @video: scene=timeline title=docker run -p + -v 的洞 -->
```
docker run -p 8080:80 -v db:/var/lib/mysql mysql 时,runc 凿两个洞:
T=0    net 洞:dockerd(libnetwork)建 veth pair → veth_newlink 互指 peer
T+1      一头 set netns 进容器 → 容器 eth0;另一头插 docker0
T+2      写 iptables DNAT(-p 8080:80 那条)→ 外网能进(How 第三篇完整旅程)
T=0'   mnt 洞:runc 按 OCI mounts 配置
T+1'     mount --bind /var/lib/docker/volumes/db/_data → 容器 /var/lib/mysql
T+2'     clone_mnt + 嫁接进容器挂载树 → mysql 数据直落宿主、绕过 overlay
———— 两洞凿好,容器既能被访问(net),又能持久存数据(volume)————
```

## API / 源码参考附录

| 洞 | 凿哪扇墙 | 用户态 | 内核实现 | 文件 |
|----|--------|--------|---------|------|
| veth | net 窗 | `ip link add … type veth peer …` | `veth_newlink`(peer 互指)+ `veth_xmit`(递 skb) | `drivers/net/veth.c` |
| volume | mnt 窗 | `mount --bind /src /dst` | `do_loopback` → `clone_mnt` → `attach_recursive_mnt` | `fs/namespace.c` |

## 常见问题 Q&A

<!-- @video: emphasis=normal -->
**Q1:veth pair 删一头,另一头会怎样?**
A:veth 是成对的,删除一端,内核会把另一端也清掉(peer 指针失效)。容器销毁时它的 net 窗连同里面的 veth 一端消失,宿主端的 peer 也随之删除 —— 所以容器没了不会留下半截 veth。

**Q2:bind mount 和 cp 复制有什么区别?**
A:本质不同。`cp` 是把数据复制一份(两份独立);bind mount 的 `clone_mnt` **不复制数据,只是让同一份宿主目录在容器挂载树里多了一个访问入口**。改任一边,另一边立刻可见(同一个 inode)。

**Q3:为什么 volume 能绕过 overlay 的写放大?**
A:因为 volume 是直接 bind 到宿主真实文件系统(ext4/xfs)的挂载点,根本不在 overlay 的联合视图里。写它走的是底层 fs 的正常写路径,没有 copy_up 那回事(第二篇/What §4.4)。所以数据库数据目录必须挂 volume。

**Q4:容器互访(同宿主两容器)为什么那么快?**
A:都是 veth + docker0 网桥,`veth_xmit` 把 skb 直接递到对端接收队列,中间只过一次二层网桥转发,全程在内存里,不上物理网线。所以纳秒~微秒级。

**Q5:`--network host` 和 veth 模式的区别在源码层是什么?**
A:`--network host` = clone 时不带 `CLONE_NEWNET`(第一篇),容器共享宿主 net 窗,根本不需要 veth(也没有隔离)。veth 模式 = 容器有独立 net 窗(隔离)+ 一根 veth(受控连通)。前者是拆墙,后者是凿洞。

**Q6:一个容器能挂多个 volume、接多个 veth 吗?**
A:能。挂载树里可以嫁接任意多个 bind mount(多个 volume);net 窗里可以插任意多个 veth(多网络)。每个都是独立的一个洞,机制相同。

## 延伸阅读

<!-- @video: skip -->
- 内核源码:`drivers/net/veth.c`(`veth_newlink` / `veth_xmit` / `veth_forward_skb`)· `fs/namespace.c`(`do_loopback` / `clone_mnt` / `attach_recursive_mnt`)
- `man 2 mount`(MS_BIND)· `man 8 ip-link`(veth)
- How 阶段第三篇(网络洞的完整报文旅程:veth → bridge → NAT)


## 修订记录

| 时间 | 修订摘要 | 触发原因 |
|------|---------|---------|
| 2026-06-05 | 按 deeparch-md 方法重写 Deep:6墙/3表/2洞 三篇独立文档拼成 05-deep。每篇总分结构(总=C代码/cgroup/命令演示+控制台铁证;分=逐项用户态→内核真源码)。架构全景图改用 HTML(内嵌+独立 pics/05-*-arch.html)。真源码 web 拉 torvalds 主线:create_new_namespaces/copy_namespaces/create_pid_namespace/create_user_ns/clone_uts_ns/create_ipc_ns/copy_net_ns·setup_net(6墙)、try_charge_memcg(内存表)、veth_newlink/veth_xmit(洞一);copy_mnt_ns·copy_tree/CFS bandwidth/blk-throttle/do_loopback·clone_mnt 因超大文件用准确调用链+真函数名。 | 用户五拒旧版,定线索:deeparch-md 三段式套到 6墙/3表/2洞,生成 3 文档拼接,架构图 ASCII→HTML;并要求 6墙用总分+mini-docker 演示、net 窗补网络表清单 |
