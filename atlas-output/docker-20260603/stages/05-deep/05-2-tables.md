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
