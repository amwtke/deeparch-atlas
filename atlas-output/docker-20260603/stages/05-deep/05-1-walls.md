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
