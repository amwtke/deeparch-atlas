# 阶段 2:cgroup 为什么必须存在

> 上一节讲了 cgroup 长什么样:一棵目录树,往文件里写数。这一节回到它出现之前:手里只有 nice、taskset、ulimit 这些老工具的时候,那台机器上的问题到底解决不了在哪。
>
> 读法:每一节先给结论,再在虚拟机里真跑一遍,最后记下一条「硬约束」。八条约束凑齐,cgroup 的形状就被逼出来了;最后一刀讲为什么它做了两遍(v1 和 v2)。
>
> 没用过 docker 也能读:这一节几乎不出现 docker,只有进程、命令和数字。

## §0 先说结论

**一句话:旧工具都把账记在单个进程身上,而你要管的是「一摊」进程的合计。cgroup 做的事就是把账户从进程身上搬到一个进程自己改不了的组上。**

四句话带走主干:

- **单位错了。** 调度器、nice、ulimit 认的都是单个进程;业务却是一组会变的进程,多开一个就多拿一份。
- **说不出绝对数。** nice 只能说「抢的时候谁多」,说不出「最多半颗核」;ulimit 限的是地址空间,不是真占住的内存。
- **边界是自己围的。** 绑核、进程组、会话,进程自己一个系统调用就能改;内存吃光时全机挑最胖的杀,不问是谁闯的祸。
- **做了两遍。** v1 让每种资源各建一棵树,结果写一次文件的账要跨两棵树、对不上;v2 只留一棵树。

![八刀八条:旧办法每差一口气,就记下一条硬约束](pics/02-overview.svg)

这张图就是全节的目录:左边是试过的办法,中间是实测,右边是它差的那一口气和由此记下的约束。后文所有约束都用「编号·短名」引用,比如 `C1·业务是一组进程`。

### §0.1 实验是怎么做的(先交代清楚)

场景还是上一节那台 `host01`:一个数据库,一个每晚起 8 个 worker 的报表任务 report。这一节所有数字都是在 Lima 虚拟机(4 核,内核 7.0)里实跑出来的,但有三处和「真机上的真 mysqld」不一样,先说明白:

| 文中说的 | 实验里实际用的 | 为什么 |
|---|---|---|
| mysqld | 替身脚本 `db.py`(进程名 `db-sim`):4 个连接进程不停做「查询」,一次查询是一小段定量的纯计算,独占一颗核时约 5 ms;跑 8 秒,报告做了多少次、每次多久 | 要的是一个能稳定量出「被挤慢了多少」的东西 |
| report | 替身脚本 `report.py`(worker 进程名 `report-w`):`cpu` 模式每个 worker 死循环,`mem` 模式每个 worker 慢慢吃到指定大小的内存 | 同上 |
| 那台机器 | 一个叫 `host01` 的**沙箱组**:内存上限 3G,不限 CPU | 虚拟机上还跑着别的真服务(一个真的 mysqld、一个 clickhouse),不能真把整机内存打爆 |

第三行有点讽刺:为了演示「没有 cgroup 的世界」,我先用 cgroup 圈了一块地。做法是这样的:

![终端留档:圈一个 3G 的沙箱组 host01,把 shell 搬进去](pics/02-shot-env.svg)

- **「没有 cgroup 的世界」= 沙箱里面不再分组。** db-sim 和 report 挤在同一本账里:CPU 由调度器按进程分,内存见底时在全沙箱里挑人杀。这和一台没有分组的整机是同一种分法。
- **「有 cgroup 的世界」= 沙箱里再分 `db` 和 `report` 两个子组。** 留到 §10。
- 内存按比例缩小:把沙箱当成一台 4 核 3G 的小机器,db-sim 占 1500 MiB(相当于上一节那 4G 缓冲池),每个 worker 要 300 MiB。

图是「终端留档图」:实跑的输出原样存成日志(`src/logs/`),再排成图,不是窗口截图;提示符那一行由留档脚本打印,命令和输出是真实执行结果。正文里的代码块是从日志里节选的(省略处用 …… 标出,个别行尾加了 ← 注释,报错行去掉了脚本行号),原样完整的输出以图和日志为准。全部实验脚本在 `src/02-evidence-sessions.sh`,每个实验结束时沙箱里的进程一次杀光、目录删掉。

## §1 现场:什么都不做,数据库只剩三分之一

**结论:调度器很公平,但它是对「进程」公平。report 开 8 个进程就拿 8 份,db 的 4 个进程只剩 4/12。**

先让 db-sim 独占机器跑一遍,再让 report 起 8 个 worker 后跑一遍:

```
# python3 db.py
查询 5518 次(690 次/秒)  平均 5.8 ms  p99 7.7 ms
这段时间的 CPU:db-sim×4 合计 398%

# python3 report.py cpu 8 &
# python3 db.py
查询 1808 次(226 次/秒)  平均 17.7 ms  p99 25.9 ms
这段时间的 CPU:db-sim×4 合计 132%   report-w×8 合计 266%
```

![终端留档:db-sim 独占 690 次/秒,report 起 8 个 worker 后 226 次/秒](pics/02-shot-cpu0.svg)

**算例。** 4 颗核一共 400% 的 CPU。现在有 12 个想跑的进程(db-sim 4 个 + report-w 8 个),调度器对它们一视同仁:

| | 进程数 | 应得 | 实测 |
|---|---|---|---|
| 每个进程 | 1 | 400% ÷ 12 = 33.3% | — |
| db-sim | 4 | 4 × 33.3% = 133% | 132% |
| report-w | 8 | 8 × 33.3% = 267% | 266% |
| db-sim 的吞吐 | — | 690 × 4/12 = 230 次/秒 | 226 次/秒 |
| 单次查询耗时 | — | 5.8 ms × 3 = 17.4 ms | 17.7 ms |

数字对得严丝合缝。问题不在调度器算错了,而在它数的单位:**它眼里没有「db」和「report」,只有 12 个进程。** report 的作者明天把 worker 改成 16 个,db 就只剩 4/20 = 20%。分给谁多少,取决于谁开的进程多。

把上一节的分户电表类比接过来:这栋楼里每个电器都有自己的插座,但**没有分户电表**。谁家电器多,谁用的电就多,物业只看得见一个个电器,看不见「户」。

> **C1·业务是一组进程。** 一个业务从来不是一个进程,而是一组数量会变的进程(开几个由应用自己定);内核原生只认单个进程。要管住一个业务,记账和设限的单位必须是「组」,而且管的是合计。

悬念:那给 report 降优先级不就行了?Linux 早就有 nice。

## §2 第一件工具:nice —— 看起来解决了

**结论:nice 能让 report 在抢的时候少拿,但它给不出「最多多少」;而且它的权重也是按进程发的,进程一多又被稀释回去。**

nice 值从 -20 到 19,数值越大越「谦让」。内核把它换成权重:nice 0 的权重是 1024,nice 19 是 15。两个进程抢同一颗核时,按权重比例分时间。

把 report 降到 nice 19 再跑:

```
# nice -n 19 python3 report.py cpu 8 &
# python3 db.py
查询 5184 次(648 次/秒)  平均 6.2 ms  p99 10.2 ms
这段时间的 CPU:db-sim×4 合计 386%   report-w×8 合计 11%
```

**算例。** 每颗核上平均有 1 个 db-sim(权重 1024)和 2 个 report-w(权重各 15):

- db-sim 占 1024 ÷ (1024 + 2 × 15) = 97.2%,4 颗核合计 389%。实测 386%。
- report-w 合计 4 × 2.8% = 11.4%。实测 11%。

吞吐回到 648 次/秒,是独占时的 94%。**看起来解决了。** 但往下再试两步,就露出两个洞:

```
### db-sim 没活的时候,nice 19 的 report 吃多少
# python3 cpuof.py 3
3 秒内的 CPU:report-w×8 合计 398%

### 还是 nice 19,但 report 这次起 400 个 worker
# nice -n 19 python3 report.py cpu 400 &
# python3 db.py
查询 2147 次(268 次/秒)  平均 14.9 ms  p99 24.4 ms
这段时间的 CPU:db-sim×4 合计 164%   report-w×400 合计 237%
```

![终端留档:nice 19 下 8 个 worker 时 648 次/秒,闲时 report 吃满 398%,400 个 worker 时 268 次/秒](pics/02-shot-nice.svg)

**洞一:没有天花板。** db 没活的时候,最低优先级的 report 照样吃满 4 颗核(398%)。nice 回答的是「两个人同时要的时候谁多」,回答不了「你最多拿多少」。你没法对任何人承诺「report 最多半颗核」。副作用已经看得见:即便只有 8 个 worker,db 的 p99 也从 7.7 ms 涨到了 10.2 ms —— 查询到来的那一刻,核上正跑着 report。

**洞二:人多就稀释。** 权重是发给每个进程的。400 个 worker 时,每颗核上是 1 个 db-sim 对 100 个 report-w:

- db-sim 占 1024 ÷ (1024 + 100 × 15) = 40.6%,合计 162%。实测 164%。
- 吞吐掉到 268 次/秒,只剩 39%。

nice 19 已经是最低一档,没有更低的了。report 只要多开进程,就能把让出去的再拿回来。这其实还是 `C1·业务是一组进程` 的老毛病,只是藏在权重里。

另外,nice 只管 CPU,内存、磁盘它一概不管。

> **C2·上限要是绝对数。** 相对权重只在有人抢的时候起作用,而且会被进程数稀释;要对别人做出承诺(「它最多半颗核」「它最多 512 MiB」),上限必须是一个不随对手多少、不随自己进程数变化的绝对数。

悬念:要绝对的上限,把 report 关进一颗核里不就是了?

## §3 第二件工具:taskset 绑核 —— 栅栏是自己围的

**结论:绑核是旧工具里唯一有「天花板」的,而且子进程会继承。但它最小只能圈一整颗核,更要命的是:被圈的进程自己一个系统调用就能出来。**

`taskset -c 3` 的意思是「这个进程只许在 3 号核上跑」,它 fork 出来的子进程也继承这条限制:

```
# taskset -c 3 python3 report.py cpu 8 &
# python3 db.py
查询 3890 次(486 次/秒)  平均 8.2 ms  p99 17.5 ms
这段时间的 CPU:db-sim×4 合计 298%   report-w×8 合计 100%
```

report 的 8 个 worker 合计正好 100%:不管开多少个,都挤在那一颗核里。这是第一次出现「合计的上限」。db-sim 拿到 298%,吞吐 486 次/秒(独占时的 70%;比 3/4 略低,因为 db-sim 的进程时不时也落到 3 号核上和 8 个 worker 抢)。

两个缺口:

**缺口一:最小单位是一整颗核。** 「半颗核」说不出来;而且圈走的是一颗具体的核,不是一份时间。

**缺口二:栅栏自己能拆。** report 的作者是普通用户 `lima`,他在 worker 里加了一行:

```python
os.sched_setaffinity(0, range(os.cpu_count()))    # 把自己放回所有核
```

```
# runuser -u lima -- taskset -c 3 python3 report.py cpu 8 unpin &
worker 43076:sched_setaffinity 成功,允许的核从 [3] 变成 [0, 1, 2, 3]
# python3 db.py
查询 1719 次(215 次/秒)  平均 18.6 ms  p99 29.6 ms
这段时间的 CPU:db-sim×4 合计 134%   report-w×8 合计 263%
```

![终端留档:绑核时 report 合计 100%;worker 以普通用户身份自己解绑后,db-sim 回到 215 次/秒](pics/02-shot-taskset.svg)

不需要任何特权,一行代码,回到 §1 的原点(215 次/秒)。进程修改自己的 CPU 亲和性本来就是允许的,这个接口是给程序做性能优化用的,不是给管理员做隔离用的。

### §3.1 现成的「组」也不行:进程组和会话

Unix 早就有两种把进程编成一组的办法:进程组(pgid)和会话(sid),`kill -- -<pgid>` 可以一次杀一组。能不能直接拿它们当「一摊」的边界?

```
# setsid bash -c 'sleep 301 & sleep 302 & setsid sleep 303 & wait' &
# ps -o pid,ppid,pgid,sid,args -C sleep | grep -E 'PID|30[123]'
    PID    PPID    PGID     SID COMMAND
  43120   43118   43118   43118 sleep 301
  43121   43118   43118   43118 sleep 302
  43122   43118   43122   43122 sleep 303

# kill -- -43118
# ps -o pid,ppid,pgid,sid,args -C sleep | grep -E 'PID|30[123]'
    PID    PPID    PGID     SID COMMAND
  43122       1   43122   43122 sleep 303
```

![终端留档:三个子进程里有一个调用了 setsid,按进程组杀完后它还活着](pics/02-shot-setsid.svg)

第三个子进程调用了 `setsid`,给自己换了一个新的会话和进程组(43122)。按组杀完,它还活着,父进程变成了 1 号进程。进程组和会话是为终端的作业控制设计的,**成员身份由进程自己申报**,想走随时能走。

三件东西(CPU 亲和性、进程组、会话)是同一个毛病:

> **C3·被管者不可信。** 被限制的程序不是你写的,也未必配合。凡是进程自己能改的边界(亲和性、进程组、会话),都等于没有边界。「谁属于哪一摊」和「这一摊的上限是多少」,必须由内核强制、由管理员掌握,进程自己改不了。

上一节 §3.4.1 的结论在这里找到了出处:为什么子进程「生下来就在父进程的组里」、为什么 runc 要「先入组、后变身」—— 因为组籍必须在被管的程序开始执行**之前**就定下来,而且之后它自己甩不掉。

悬念:CPU 先放一放。内存这边有 ulimit,它限的可是硬邦邦的数字。

## §4 内存线:ulimit —— 每人不超,合计撑爆

**结论:ulimit 的数字是绝对的,但它一按人头算、二量错了东西:限的是地址空间,不是真占住的物理内存。**

`ulimit -v 524288` 给之后启动的每个进程设一个上限:地址空间最多 512 MiB(单位是 KiB)。单个进程想要 600 MiB,立刻被拒:

```
# bash -c 'ulimit -v 524288; python3 -c "x = b\"x\" * (600 << 20)"'
MemoryError
```

同样的限制下,让 report 起 8 个 worker,每个要 300 MiB:

```
# bash -c 'ulimit -v 524288; python3 report.py mem 8 300' &
# ps -o pid,vsz,rss,comm -C report-w
    PID    VSZ   RSS COMMAND
  46031 325712 315132 report-w
  ……(8 行,每行都一样)
8 个 worker 合计占住 2461 MiB
```

**算例。** 每个 worker 的地址空间(VSZ)是 325 712 KiB ≈ 318 MiB,小于 512 MiB,**没有一个违规**。真占住的物理内存(RSS)每个 308 MiB,8 个合计 2461 MiB —— 是那个「512」的 4.8 倍,这台 3G 的小机器已经被吃掉八成。限额写的是 512,实际效果是 512 × 进程数。又是 `C1·业务是一组进程`。

第二个毛病更隐蔽:它量的东西不对。

```python
# vm.py
m = mmap.mmap(-1, 1 << 30)          # 向内核要 1 GiB 匿名内存,但一页都不去碰
```

```
# python3 vm.py
映射 1 GiB 成功;此刻真正占住的物理内存 VmRSS = 10 MiB
# bash -c 'ulimit -v 524288; python3 vm.py' 2>&1 | tail -1
OSError: [Errno 12] Cannot allocate memory
```

![终端留档:ulimit -v 512M 下单进程 600M 被拒,8 个 worker 合计占住 2461 MiB;1 GiB 没碰过的映射只占 10 MiB 物理内存却被拒](pics/02-shot-ulimit.svg)

这个程序只「预订」了 1 GiB 地址空间,一页都没碰,真占住的物理内存只有 10 MiB,却被 ulimit 拦下了。地址空间不是稀缺资源(64 位进程有的是),物理内存才是。很多运行时(JVM、Go)启动时会预订一大片地址空间,`ulimit -v` 设小了它们起不来,设大了又什么都限不住。

那有没有按物理内存限的 ulimit?有一个 `RLIMIT_RSS`,但手册写得很直白:

> This limit has effect only in Linux 2.4.x, x < 30. —— [getrlimit(2)](https://man7.org/linux/man-pages/man2/getrlimit.2.html)

也就是说,在今天的 Linux 上,**根本没有「限制一个进程占多少物理内存」的 rlimit**。

还有一大类物理内存压根不在任何进程的账上:页缓存(读写文件时内核替你缓存的数据)。§6 会实测到:一个进程写了 1 GiB 文件就退出了,机器的缓存涨了 1 GiB,而这 1 GiB 不算在任何进程的 RSS 里。

> **C4·账要记在物理消耗上。** 稀缺的是物理内存页、真实跑掉的 CPU 时间、真实的磁盘带宽,不是地址空间这类「预订量」。而且有相当一部分物理消耗(页缓存、内核替进程占的内存)不挂在任何进程名下。要管得住,账必须在物理资源真正被占用的那一刻记,并且记到「一摊」的头上。

悬念:限不住就限不住吧,内存真吃光了,内核总有办法。它的办法是什么?

## §5 内存吃光的那一刻:闯祸的是报表,死的是数据库

**结论:内存和 CPU 不一样,不够了等不来,到头只能杀进程。没有边界的时候,内核在全场挑最胖的那个杀 —— 最胖的往往正是数据库。**

db-sim 先占住 1500 MiB(扮演 mysqld 的缓冲池),然后 report 起 8 个 worker,每个慢慢吃到 300 MiB:

```
# python3 hold.py db-sim 1500 &
db-sim(pid 46097)已占住 1500 MiB
# python3 report.py mem 8 300 &

# journalctl -k --since 18:41:24 -o cat --no-pager | grep -E 'invoked oom-killer|oom-kill:|Killed process'
report-w invoked oom-killer: gfp_mask=0xcc0(GFP_KERNEL), order=0, oom_score_adj=0
Memory cgroup out of memory: Killed process 46097 (db-sim) total-vm:1555400kB, anon-rss:1540552kB, ……

# ps -o pid,rss,comm -C db-sim,report-w
(只剩 7 个 report-w,db-sim 不在了)
# wait 46097; echo …
db-sim 的退出状态 = 137(137 = 128 + 9,被 SIGKILL 杀死)
```

![终端留档:report-w 触发 OOM,被杀的是 db-sim;db-sim 退出状态 137](pics/02-shot-oom.svg)

日志的头两行把事情说完了:**`report-w invoked oom-killer`(report 的 worker 触发的),`Killed process 46097 (db-sim)`(被杀的是数据库)。**

**算例。** 机器 3072 MiB,db-sim 占 1500 MiB,8 个 worker 各吃到 w:

- 1500 + 8 × w = 3072,解得 w ≈ 196 MiB 时见底。日志里 worker 被杀时的 `anon-rss` 是 208 900 KiB ≈ 204 MiB,对得上。
- 此刻全场最胖的是 db-sim(1504 MiB),是任何一个 worker(约 200 MiB)的 7 倍多。内核挑的是「杀掉它能腾出最多内存」的那个,于是 db-sim 第一个死。

**为什么只能杀。** CPU 是可以排队的资源:不够了让人等一等,慢,但不死;下一个时间片又有新的 CPU 时间。内存不是:已经发出去的页,主人不还,内核收不回来。内核能做的只有两件事 —— 先回收(扔掉可以重读的页缓存;有 swap 的话把匿名页换出去),回收不动就杀。这台机器没有 swap,匿名内存无处可去,第二件事来得很快。

**能不能给 mysqld 贴一张免死金牌?** 可以,`oom_score_adj` 设成 -1000 就不会被选中。但这只改变「杀谁」的排序,不改变「report 能吃多少」:机器照样被吃光,只是换一个倒霉蛋(下一个最胖的)。而且它又是一个贴在单个进程身上的设置。

两点如实交代:

1. **这是沙箱里的 OOM。** 日志写的是 `Memory cgroup out of memory`,约束类型是 `CONSTRAINT_MEMCG`、范围是 `oom_memcg=/host01`,因为我把沙箱当成了整台机器。真机上内存见底时,日志是 `Out of memory: Killed process …`。两种情况挑人的规则是同一套(都是在范围内找最胖的),这一点的源码确认留到后面(待核 #2)。
2. **还多杀了一个。** 图里能看到,db-sim 之后紧接着又有一个 report-w(pid 46111,约 204 MiB)被杀。按算例,db-sim 腾出 1.5G 之后内存是够的,不该再杀。我跑了三遍,db-sim 每次都是第一个死,之后又分别搭上 1 个、3 个、1 个 worker(前两遍 worker 吃得更快,每 50 ms 吃 10 MiB,其中第二遍的日志留在 `src/logs/oom-fast.log`;正文和图用的是第三遍,每 200 ms 吃 10 MiB)。为什么会多杀,我还没查清,不替它编理由,留到讲内存这条线的源码时回答(待核 #1)。

> **C5·内存不可压缩。** CPU 不够可以让人等,内存不够等不来:占了不还,回收不动就只能杀进程。既然到头总要有人死,「在哪个范围里挑人」就必须有边界:谁那一摊超了,就在谁那一摊里回收、在谁那一摊里杀。

这就是你带来的第二个问题的另一半:容器 OOM 为什么只杀容器里的进程。不是内核变仁慈了,而是挑人的范围从「全机」换成了「超限的那一组」。§10 会把同一出戏放进组里再演一遍。

## §6 同一种病:磁盘 IO 与进程数

**结论:换成磁盘和进程数,毛病一模一样 —— 账记在错的人头上,或者干脆没人认账。** 这两种资源只各举一个例子。

### §6.1 磁盘 IO:写盘的不是花钱的人

让 report 写一个 1 GiB 的临时文件,并且用 `ionice -c 3` 给它最低的 IO 优先级:

```
# grep ^Cached: /proc/meminfo
Cached:          2605832 kB
# ionice -c 3 dd if=/dev/zero of=/var/tmp/report.tmp bs=1M count=1024 2>&1 | tail -1
1073741824 bytes (1.1 GB, 1.0 GiB) copied, 0.100223 s, 11 GB/s
# grep ^Cached: /proc/meminfo
Cached:          3654444 kB

### 同样的写,但要求 dd 等数据真正落到盘上再返回
# ionice -c 3 dd if=/dev/zero of=/var/tmp/report.tmp bs=1M count=1024 conv=fsync 2>&1 | tail -1
1073741824 bytes (1.1 GB, 1.0 GiB) copied, 0.608359 s, 1.8 GB/s
```

**算例。**

- 第一次:0.10 秒写完 1 GiB,速度 11 GB/s,比这块盘快得多(第二次量出来是 1.8 GB/s)。因为这 0.10 秒里 dd 只是把数据拷进了内核的页缓存,然后就退出了。
- 缓存涨了 3 654 444 − 2 605 832 = 1 048 612 KiB ≈ 1024 MiB,正好是那个文件。**这 1 GiB 物理内存不在任何进程的 RSS 里**(dd 已经不在了),这是 `C4·账要记在物理消耗上` 说的那一类。
- 真正落盘要 0.61 秒。少掉的那 0.5 秒的活,是内核的回写线程在 dd 退出之后替它干的。

所以给 dd 设 IO 优先级意义不大,手册说得很明白:

> I/O priorities are not supported for asynchronous writes because they are issued outside the context of the program dirtying the memory. —— [ioprio_set(2)](https://man7.org/linux/man-pages/man2/ioprio_set.2.html)

弄脏内存的是 report,发出磁盘 IO 的是内核线程。**花钱的人和付账的人不是同一个。** 这件事先记着,它是 §9 里 v1 栽跟头的地方。

### §6.2 进程数:数的是「这个用户」,而且 root 不算

怕 report 无限 fork,可以用 `ulimit -u` 限进程数。限成 30 试试:

```
# ps -L -u lima --no-headers | wc -l
3
# runuser -u lima -- bash -c 'ulimit -u 30; python3 forkn.py 100'
第 26 次 fork 失败:[Errno 11] Resource temporarily unavailable
想要 100 个子进程,成功 fork 出 25 个

### 同样的限制,换成 root(容器里的进程常常就是 root)
# bash -c 'ulimit -u 30; python3 forkn.py 100'
想要 100 个子进程,成功 fork 出 100 个
```

![终端留档:dd 0.10 秒写完 1 GiB(只进了页缓存),落盘要 0.61 秒;ulimit -u 30 对普通用户按用户总数算,对 root 不生效](pics/02-shot-same.svg)

- 普通用户:限 30,只 fork 出 25 个。因为它数的是 **`lima` 这个用户名下的全部进程**(原有的几个也算在内),不是「report 这个作业」。同一个用户跑两个业务,它们共用这一个数。
- root:100 个全部成功。手册原话是该限制对有 `CAP_SYS_ADMIN` / `CAP_SYS_RESOURCE` 能力或真实用户为 0 的进程不生效([getrlimit(2)](https://man7.org/linux/man-pages/man2/getrlimit.2.html))。而服务和容器里的进程,常常就是 root。

这两个例子没有带来新的约束,是前面几条在别的资源上重演:单位不对(`C1·业务是一组进程`)、被管者能绕过(`C3·被管者不可信`)、账记不到真正的消耗上(`C4·账要记在物理消耗上`)。

## §7 退一步:每个业务一台虚拟机

**结论:虚拟机隔得住,但它是用「一人一套房」解决「合租」问题:每台各带一套内核、各占一份预留内存,闲着的互相借不到。要省,就得在同一个内核里隔。**

既然进程级的工具都不行,干脆从硬件上切:db 一台虚拟机,report 一台。虚拟机确实能隔住 —— report 在自己的虚拟机里怎么 fork、怎么吃内存,都只能祸害自己那台。

代价用 host01 算一下(4 核 8G):

| | 切成两台虚拟机 | 同一个内核里分组 |
|---|---|---|
| 内存怎么分 | db 虚拟机 5G + report 虚拟机 3G,各自预留 | 只写上限;没用到的谁都能用 |
| report 一天只跑 1 小时 | 其余 23 小时它那 3G 闲着,db 借不到 | 其余 23 小时 8G 都可以给 db 当缓存 |
| 固定开销 | 每台各一套内核和系统服务;同一个库文件、同一份数据在两台里各缓存一份 | 一套内核,一份缓存 |
| 起一个业务 | 开机:我们这台 Lima 虚拟机实测 7.8 秒(内核 0.13 + initrd 1.27 + 用户态 6.43,`src/logs/00-vm-boot.log`) | 起一个进程:毫秒级 |
| 调上限 | 多半要停机改配置 | 往文件里写一个数,立即生效 |

而且虚拟机里面还是同一个问题:db 那台虚拟机里又跑了备份任务,备份把 mysqld 挤慢了怎么办?再套一层虚拟机?

所以方向只能是:**在同一个内核里,让内核自己认得「组」。** 这个选择带来一个不小的后果。回头看 §6.1 的 dd:0.10 秒里它往页缓存写了 1 GiB,也就是 262 144 个 4K 的页。如果每占一页都要问一句「这一页记在哪个组头上、这个组超了没有」,那就是 0.1 秒里问 26 万次;CPU 那边,每次调度切换也都要问一遍。**账记在内核最热的路径上,记账本身必须便宜到几乎不要钱。** 上一节的悬念 3(「每跑一微秒就加一次吗?那得多慢」)就是从这里来的,答案在讲架构时给。

> **C6·共用一个内核。** 一个业务一台虚拟机,等于每份都预留、每份都带一套内核,闲置的资源互相借不到。要便宜就得让所有业务共用一个内核,由内核在内部区分「这是谁的」。由此的推论:记账发生在调度和内存分配这些最热的路径上,必须极便宜。

## §8 核心想法,以及第一版答案(v1)

**结论:把账户从进程身上搬到「组」上。进程只带一个组籍,生下来就继承父进程的;每次真正消耗资源时顺手记到组的账上;账满了就在组内处置。组还要能套组,因为额度是一层层往下分的。**

### §8.1 一个想法

![核心想法:把账户从进程身上,搬到一个进程自己改不了的组上](pics/02-ledger-move.svg)

可以写成一句「用 X 换 Y」:

> **用「每个进程多带一个组籍 + 每次消耗资源时多记一笔」,换「对任意一组进程的合计设限」。**

拆开看是三样东西,正好一样对一簇约束:

| 要有什么 | 它是什么 | 被哪条约束逼出来 |
|---|---|---|
| **组籍** | 每个进程身上一个「我属于哪个组」的标记;fork 时子进程继承父进程的;进程自己改不了 | `C1·业务是一组进程`、`C3·被管者不可信` |
| **组的账** | 挂在组上的计数器,记的是物理量:跑掉的 CPU 时间、占住的物理页 | `C4·账要记在物理消耗上`、`C6·共用一个内核` |
| **组的限** | 写在组上的绝对数;账到了这个数,就地处置(CPU 让它等,内存先回收再杀) | `C2·上限要是绝对数`、`C5·内存不可压缩` |

回到分户电表:以前只有每个电器上的保险丝(ulimit),现在给每户装了**电表和总闸**。电器随便添,表只有一块;闸在楼道里,住户自己拧不了。

如果你熟悉数据库,这像是从「只能给每条连接设上限」(单条 SQL 最多用多少内存)走到「给整个租户设资源组」:前者拦不住一个租户开 400 条连接,后者才是合计。

### §8.2 第一版答案:v1 把组做成了目录树

这个想法 2.6.24 版内核第一次做出来(版本出处:[cgroups(7)](https://man7.org/linux/man-pages/man7/cgroups.7.html);它是谁做的、为什么叫这个名字,讲来路时再说)。外形就是上一节看到的:一个特殊的文件系统,建目录 = 建组,把 pid 写进文件 = 入组,往文件里写数 = 设限。

它一开始就是**树**,组里可以再建组。为什么不是平铺的一层?因为额度在现实里是一层层往下分的。还是 host01,这次它归一个容器平台管:

```
机器 4 核
└─ 平台拿走 3 核(留 1 核给系统自己)
   ├─ 租户 A:2 核
   │   ├─ report:0.5 核
   │   └─ api:1.5 核
   └─ 租户 B:1 核
```

平台只需要保证「租户 A 合计不超过 2 核」,A 内部怎么分给 report 和 api,是 A 自己的事,平台不想管也管不过来。反过来,A 无论怎么分,report + api 的合计都越不过 2 核。这要求两件事:组能套组;父组的上限对整棵子树的合计生效。

> **C7·限额要能层层转包。** 资源的归属是分层的(机器 → 平台 → 租户 → 容器 → 容器里的服务)。上级只管给下级一个合计的额度,下级怎么再分上级不管;但下级之和不能超过上级。所以组必须能套组,组织成一棵树,上限沿着树向下约束。

到这里,v1 把 `C1·业务是一组进程` 到 `C7·限额要能层层转包` 都接住了。它栽在下一条上。

### §8.3 这个想法不挑资源:所以它被做成了一个框架

**结论:§8.1 的核心想法里没有出现「CPU」或「内存」这两个词。「进程带组籍、消耗时记一笔、账上有上限」对任何一种资源都成立。所以 cgroup 从第一版起就不是「限 CPU 的工具」加「限内存的工具」,而是一个公共的骨架加一排可以插拔的控制器。**

(这一小节是你读完前三节后指出的缺口:前面把 CPU 和内存讲透了,却没有点明 cgroup 管的是「各种资源」,它是一个架构。)

回头看八条约束,可以分成两堆:

| 和资源种类无关(只需要做一遍) | 每种资源各不相同(每种各做一份) |
|---|---|
| `C1·业务是一组进程`:谁和谁算一组 | `C4·账要记在物理消耗上`:这种资源在哪条路上被消耗、记什么 |
| `C3·被管者不可信`:归属和上限进程自己改不了 | `C5·内存不可压缩`:这种资源超了以后能不能等、能不能拒绝 |
| `C7·限额要能层层转包`:组套组 | `C2·上限要是绝对数`:上限用什么单位写(微秒、字节、个数) |

左边一堆是「分组」的事,右边一堆是「记账和处置」的事。旧工具的毛病恰好是把两堆搅在一起、每种资源各搞一套:CPU 有 nice 和绑核,内存有 ulimit 和全机 OOM,磁盘有 ionice,进程数有 `ulimit -u`。它们各有各的「单位」(进程、用户、会话),互相对不上,§1 到 §6 就是这么一刀刀切下来的。

cgroup 的做法是把左边一堆抽出来做成公共的一层,只做一遍;右边一堆交给各种资源自己的**控制器**(v1 里叫子系统)。新增一种要管的资源,只需要新写一个控制器,分组那一套原样复用。这台内核上现在有 9 个控制器:

```
# cat /sys/fs/cgroup/cgroup.controllers
cpuset cpu io memory hugetlb pids rdma misc dmem
```

§6 里旧工具管不住的磁盘 IO 和进程数,在 §10.8 里换成对应的控制器各演一遍。框架内部怎么搭的(核心提供什么、控制器填什么),放在下一节 §9。

`C8·一笔开销跨多种资源` 可以换一个说法:它是这个框架自己踩出来的约束。把资源做成一个个独立的插件之后才会遇到「插件之间要对账」的问题,v1 没有处理好,v2 才补上。

## §9 最后一刀:v1 自己的四个痛,和 v2 的改法

**结论:v1 最大的设计失误是「每种资源可以各挂一棵树」。看起来灵活,实际让各种资源对「谁是一组」各有各的答案,一笔跨资源的开销就记不到同一个人头上。v2 只留一棵树,顺带立了三条规矩。**

先看总表,再逐条展开:

| v1 的痛 | host01 上的例子 | v2 的改法 |
|---|---|---|
| ① 多棵树,账对不上 | report 写文件:内存记在 memory 树的一个组,磁盘 IO 该记在 blkio 树的谁头上? | 只有一棵树,所有资源共用同一套分组 |
| ② 一个进程的线程可以拆到不同组 | mysqld 的两个线程分在两个内存组:它们共用同一份内存,一页算谁的? | 入组的单位是进程,不是线程 |
| ③ 父组自己的进程和子组抢 | report 主进程待在 report 组里,又建了子组 workers:主进程和整个子组怎么分? | 有进程的组,不能再给子组分内存这类资源 |
| ④ 接口各说各话 | 限 CPU 要写两个文件、限内存是另一种命名;组空了要靠内核拉起一个外部程序来通知 | 统一命名和格式;组的事件写在文件里,可以监听 |

内核文档有专门一章讲这些,下面的英文引文都出自 [cgroup-v2 文档的「Issues with v1 and Rationales for v2」](https://docs.kernel.org/admin-guide/cgroup-v2.html#issues-with-v1-and-rationales-for-v2)。

### §9.1 v1 长什么样(实跑)

这台 7.0 内核的虚拟机默认是 v2,但 v1 的挂法还能演示。v1 里每种资源由一个「控制器」负责,可以各挂一棵树。这里挂两棵还能用的(`freezer` 和 `net_cls`):

```
# mount -t cgroup -o freezer none /tmp/v1/freezer
# mount -t cgroup -o net_cls none /tmp/v1/net_cls
# mkdir /tmp/v1/freezer/A /tmp/v1/net_cls/X
# echo $$ > /tmp/v1/freezer/A/cgroup.procs; echo $$ > /tmp/v1/net_cls/X/cgroup.procs
# cat /proc/$$/cgroup
4:net_cls:/X
3:freezer:/A
0::/user.slice/user-502.slice/session-6.scope
```

![终端留档:v1 的两棵树,同一个 shell 在两棵树上各占一个位置;一个进程的两个线程被拆到两个组;这台内核已不带 v1 的内存控制器](pics/02-shot-v1.svg)

同一个 shell,现在有**三处组籍**:在 freezer 树的 `/A`,在 net_cls 树的 `/X`,在 v2 那棵树的 `session-6.scope`。v1 的年代,一台机器上常见十来棵树,`/proc/<pid>/cgroup` 就有十来行。

图里最后一步还有一个时代的注脚:这台内核的配置里 `CONFIG_MEMCG_V1` 和 `CONFIG_CPUSETS_V1` 都是 `is not set`,v1 的内存控制器已经没有编进来了。

### §9.2 痛一:多棵树,账对不上

![v1 多棵树 vs v2 一棵树:同一个 worker 写一个文件,账记到哪](pics/02-v1-vs-v2.svg)

接着 §6.1 的发现:写文件这一个动作,先占内存(页缓存),稍后由内核线程写盘。在 v1 里:

1. 占掉的内存,记在 memory 树上 report 所在的那个组(图里的 `jobs`)。
2. 稍后回写线程要把这些页写到盘上。这笔 IO 应该算在 blkio 树的哪个组头上?发 IO 的是内核线程,不是 report;而 memory 树和 blkio 树是两棵互不相干的树,形状可以完全不同,从「memory 树的 jobs」推不出「blkio 树的 slow」。

文档的说法:

> each controller had to assume that all other controllers were attached to completely orthogonal hierarchies. This made it impossible, or at least very cumbersome, for controllers to cooperate with each other.

多棵树还有两个附带的麻烦:实际使用中大家几乎都是一个控制器一棵树(文档:"most configurations resorted to putting each controller on its own hierarchy"),管理程序同一件事要在每棵树上各做一遍;一个进程的组籍长度不固定,树越多越长。

**v2 的改法:只有一棵树。** 一个进程只在一个组里,这个组同时是它的 CPU 组、内存组、IO 组。于是内存和 IO 两边可以合作:

> The io controller, in conjunction with the memory controller, implements control of page cache writeback IOs.

> **C8·一笔开销跨多种资源。** 写一次文件既是内存的开销又是磁盘的开销,而且真正发出磁盘 IO 的是内核线程。要让这笔账记到同一个人头上,所有资源必须对「谁是一组」给出同一个答案:分组只能有一套,树只能有一棵。

### §9.3 痛二:线程可以拆到不同的组

v1 入组的最小单位是线程(`tasks` 文件),可以把一个进程的两个线程放进两个组。实跑:

```
# python3 two_threads.py &
进程 pid = 45856(主线程的 tid 也是它)
副线程 tid = 45858
# mkdir /tmp/v1/freezer/B; echo 45858 > /tmp/v1/freezer/B/tasks
# grep -H freezer /proc/45856/task/*/cgroup
/proc/45856/task/45856/cgroup:3:freezer:/A
/proc/45856/task/45858/cgroup:3:freezer:/B
```

同一个进程,主线程在 `/A`,副线程在 `/B`。对 CPU 这也许说得通,对内存就没法说了:同一个进程的线程共用一个地址空间,mysqld 的两个线程分在两个内存组,缓冲池里的一页算谁的?文档:"This didn't make sense for some controllers"。

**v2 的改法:只认进程。** 把副线程的 tid 写进 `cgroup.procs`,搬走的是整个进程:

```
# echo 45929 > /sys/fs/cgroup/host01/report/cgroup.procs      ← 45929 是副线程
# grep -H . /proc/45927/task/*/cgroup
/proc/45927/task/45927/cgroup:0::/host01/report
/proc/45927/task/45929/cgroup:0::/host01/report
```

(v2 后来给 CPU 这类「按线程分也说得通」的资源单独留了一个口子,叫 threaded 模式,讲架构时再说。)

### §9.4 痛三:父组自己的进程,和子组抢

v1 允许一个组里既有进程、又有子组。那么父组自己的进程和子组之间怎么分?比如 report 主进程待在 `report` 组里,下面又建了子组 `workers`:主进程是和「整个 workers 子组」平起平坐,还是和 workers 里的每个进程平起平坐?v1 里每个控制器各有各的答案,文档逐个点了名:cpu 把进程和子组当成平级的竞争者,于是比例随进程数变来变去;io 偷偷造了一个隐藏的叶子节点;memory 干脆没有定义。

**v2 的改法:一条硬规矩,有进程的组不能再给子组分这类资源**(文档叫 No Internal Process Constraint)。进程只待在叶子上,父组只管分。实跑:

```
# echo $$ > /sys/fs/cgroup/host01/db/cgroup.procs             ← 组里有进程了
# echo +memory > /sys/fs/cgroup/host01/db/cgroup.subtree_control
bash: echo: write error: Device or resource busy               ← 想给子组分内存:不许

# echo $$ > /sys/fs/cgroup/host01/db/sub/cgroup.procs         ← 把进程挪到叶子上
# echo +memory > /sys/fs/cgroup/host01/db/cgroup.subtree_control && echo 成功
成功

# echo $$ > /sys/fs/cgroup/host01/db/cgroup.procs             ← 反过来:已经在分资源的组,不再收进程
bash: echo: write error: Device or resource busy
```

![终端留档:v2 里写副线程的 tid 会搬走整个进程;有进程的组打开子组的内存控制被拒,把进程挪到叶子后成功](pics/02-shot-v2rule.svg)

顺带交代一个我踩到的细节:我第一次用的是 `+cpu`,结果没有报错。这条规矩管的是内存这一类资源,cpu 走的是上面说的 threaded 那个口子,行为不一样。所以总表里写的是「内存这类资源」,区别留到讲架构时展开。

这条规矩其实是 `C7·限额要能层层转包` 的补丁:转包的时候,发包的人自己不能同时下场干活,否则「合计不超过」里的那个「合计」说不清。

### §9.5 痛四:接口各说各话

v1 的控制器是不同的人在不同年代各自加进来的,文档的评价是 "grew without oversight"。几个看得见的地方:

| 事情 | v1 | v2 |
|---|---|---|
| 限 CPU | 两个文件:`cpu.cfs_quota_us` 和 `cpu.cfs_period_us` | 一个文件:`cpu.max`,内容 `配额 周期` |
| 限内存 | `memory.limit_in_bytes` | `memory.max` |
| 内存快超了 | 只有一条硬线,到了就可能杀 | 多一条 `memory.high`:先逼它回收、让它慢下来,不杀 |
| 组空了怎么通知 | 内核每次拉起一个外部程序(上面 v1 那张图的 `ls` 里能看到 `release_agent`、`notify_on_release`) | 写在组自己的 `cgroup.events` 文件里,可以监听 |

`memory.high` 值得多说一句。它是对 `C5·内存不可压缩` 的一个缓冲:内存虽然等不来,但可以在杀之前先让申请的人慢下来、自己去回收。v1 只有一条硬线,文档说大家因此不敢设紧,宁可多留余量,浪费内存。怎么个慢法,是后面讲内存这条线时的内容。

### §9.6 两个版本的时间线

出处是 [cgroups(7)](https://man7.org/linux/man-pages/man7/cgroups.7.html):

- 2.6.24:第一版(后来叫 v1)。
- 3.10:开始做 v2,最初藏在一个实验性的挂载选项后面。
- 4.5:v2 转正,当时带 io、memory、pids 三个控制器。
- 4.15:cpu 控制器才进 v2。也就是说,v2 转正之后有相当长一段时间限不了 CPU,这是 v1 又被多用了很多年的直接原因。
- 今天:这台 7.0 内核里,v1 的内存控制器已经不编进来了(§9.1)。

这一期之后的架构和源码,只讲 v2。

## §10 换成 cgroup 再演一遍:它解决了什么

**结论:同样的 report、同样的 400 个 worker、同样的内存吃法,放进组里之后:report 合计恰好半颗核,db 不受进程数影响;内存超了只在 report 组里杀,db-sim 毫发无伤;setsid 和普通用户权限都出不了组。**

现在把沙箱 host01 当成机器,在里面分两个子组 `db` 和 `report`。入组用一个两行的小脚本 `ingroup`(上一节的「先入组、后变身」):

```sh
echo $$ > /sys/fs/cgroup/host01/$1/cgroup.procs    # 先把自己写进组
shift; exec "$@"                                    # 再变身成要跑的程序
```

### §10.1 CPU:半颗核就是半颗核,开多少进程都一样

```
# echo '50000 100000' > /sys/fs/cgroup/host01/report/cpu.max

# ./ingroup report python3 report.py cpu 8 &
# ./ingroup db python3 db.py
查询 5063 次(633 次/秒)  平均 6.3 ms  p99 13.7 ms
这段时间的 CPU:db-sim×4 合计 348%   report-w×8 合计 50%

# ./ingroup report python3 report.py cpu 400 &
# pgrep -c -x report-w
400
# ./ingroup db python3 db.py
查询 5120 次(640 次/秒)  平均 6.3 ms  p99 21.0 ms
这段时间的 CPU:db-sim×4 合计 348%   report-w×400 合计 52%

# grep -E 'usage_usec|nr_periods|nr_throttled' /sys/fs/cgroup/host01/report/cpu.stat
usage_usec 64859376
nr_periods 1298
nr_throttled 1296
```

![终端留档:report 组限 0.5 核,8 个 worker 和 400 个 worker 时 db-sim 都是 348% 的 CPU、约 635 次/秒](pics/02-shot-cgcpu.svg)

**算例。**

- report 没用 nice,没绑核。8 个 worker 合计 50%,400 个 worker 合计 52%:**开多少进程都是这半颗核。**
- db-sim 应得 400% − 50% = 350%,实测两遍都是 348%。对比 §2:nice 19 下 400 个 worker 时 db 只有 164%。
- 对账:64 859 376 μs ÷ 1298 个周期 = 49 969 μs/周期,就是那个 50 000;1298 个周期里有 1296 个被限流,report 几乎每个周期都撞到了上限。
- 吞吐 633 和 640 次/秒,是独占时(690)的 92%~93%,比按 CPU 算的 87.5% 高一点。原因是这两遍里每次查询花的 CPU 略少(348% ÷ 633 ≈ 5.5 ms,独占那一遍是 398% ÷ 690 ≈ 5.8 ms),属于虚拟机上不同遍之间的速度波动。以 CPU 占比为准:db 少掉的,不多不少就是 report 那半颗核。

一个小插曲:第二步里从启动 report 到 400 个 worker 起齐,要等上好一阵。因为 fork 这 400 次本身也在那半颗核里排队,先生出来的 worker 立刻开始和主进程抢。限额管的是组里的一切,包括「生孩子」这个动作。

### §10.2 内存:超了只在自己组里杀

```
# echo 512M > /sys/fs/cgroup/host01/report/memory.max
# ./ingroup db python3 hold.py db-sim 1500 &
db-sim(pid 46164)已占住 1500 MiB
# ./ingroup report python3 report.py mem 8 300 &

# journalctl -k --since 18:41:36 -o cat --no-pager | grep 'Killed process' | cut -c1-64
Memory cgroup out of memory: Killed process 46172 (report-w) tot
……(共 7 行,全是 report-w)
# journalctl -k … | grep 'oom-kill:' | head -1
oom-kill:constraint=CONSTRAINT_MEMCG,…,oom_memcg=/host01/report,task_memcg=/host01/report,task=report-w,pid=46172,uid=0

# grep oom_kill /sys/fs/cgroup/host01/report/memory.events /sys/fs/cgroup/host01/db/memory.events
/sys/fs/cgroup/host01/report/memory.events:oom_kill 7
/sys/fs/cgroup/host01/db/memory.events:oom_kill 0

# ps -o pid,rss,comm -C db-sim,report-w
    PID   RSS COMMAND
  46164 1546984 db-sim
  46176 314828 report-w
```

![终端留档:report 组限 512 MiB,8 个 worker 被杀 7 个,db-sim 的 1500 MiB 原封不动](pics/02-shot-cgmem.svg)

**算例。**

- 512 MiB 的额度,8 个 worker 一起涨:每个涨到 64 MiB 时第一次撞线(8 × 64 = 512),杀一个;剩下的继续涨,再撞线,再杀。
- 最后能留下几个?一个 worker 要 300 MiB,两个就是 600 > 512,所以只能留 1 个,**要杀 7 个**。实测 `oom_kill 7`,活下来 1 个 report-w(RSS 314 828 KiB ≈ 307 MiB),组的账 `memory.current` 是 319 913 984 字节 ≈ 305 MiB。
- db 组:`oom_kill 0`,db-sim 的 1500 MiB 原封不动。

日志里那行 `oom_memcg=/host01/report` 就是你第二个问题里的「边界」:这次 OOM 的范围是 report 这个组,挑人只在这个组里挑。对比 §5 那一行,范围是 `oom_memcg=/host01`(当时的「整台机器」),所以 db-sim 被挑中了。**同一个内核、同一套挑人规则,只是范围从全场换成了超限的那一组。**

### §10.3 边界:换得了会话,换不了组

```
# ./ingroup report setsid bash -c 'sleep 301 & sleep 302 & setsid sleep 303 & wait' &
# ps -o pid,pgid,sid,cgroup,args -C sleep | grep -E 'PID|30[123]'
    PID    PGID     SID CGROUP                      COMMAND
  45371   45369   45369 0::/host01/report           sleep 301
  45372   45369   45369 0::/host01/report           sleep 302
  45373   45373   45373 0::/host01/report           sleep 303

# ./ingroup report runuser -u lima -- bash -c 'echo $$ > /sys/fs/cgroup/host01/db/cgroup.procs'
bash: line 1: /sys/fs/cgroup/host01/db/cgroup.procs: Permission denied
# ./ingroup report runuser -u lima -- bash -c 'echo max > /sys/fs/cgroup/host01/report/cpu.max'
bash: line 1: /sys/fs/cgroup/host01/report/cpu.max: Permission denied

# echo 1 > /sys/fs/cgroup/host01/report/cgroup.kill
# ps -o pid,args -C sleep | grep -c '30[123]'
0
```

![终端留档:setsid 之后进程换了会话和进程组,cgroup 一栏仍是 /host01/report;普通用户改组籍和改上限都被拒;cgroup.kill 一个不漏](pics/02-shot-cgescape.svg)

- §3.1 里靠 `setsid` 逃掉的那个 `sleep 303`,这次会话和进程组照样换了(45373),但 `CGROUP` 一栏还是 `/host01/report`。组籍不归它自己管。
- 普通用户想把自己挪到 db 组、想把自己组的上限改成 `max`,都是 `Permission denied`:组籍和限额就是两个文件,文件的主人是 root。
- `cgroup.kill` 按组杀,一个不漏。

### §10.4 前后对照

| 场景 | 旧办法(实测) | 放进组里(实测) | 对应约束 |
|---|---|---|---|
| report 8 个 worker 时 db 的吞吐 | 不管 226;nice 648;绑核 486 | 633 | `C1·业务是一组进程` |
| report 400 个 worker 时 db 的吞吐 | nice 19:268 | 640 | `C1·业务是一组进程` |
| report 最多能吃多少 CPU | nice:闲时 398% | 任何时候约 50% | `C2·上限要是绝对数` |
| 被管的进程能不能自己出去 | 解绑成功;setsid 成功 | 组籍不变;改文件被拒 | `C3·被管者不可信` |
| 「512M」实际限住多少 | ulimit:合计 2461 MiB | 合计不超过 512 MiB | `C4·账要记在物理消耗上` |
| 内存见底谁死 | db-sim | 7 个 report-w;db-sim 活着 | `C5·内存不可压缩` |
| 代价 | — | 同一个内核,没有多开一台虚拟机 | `C6·共用一个内核` |

也有它没解决、或者说它带来的新问题,如实列出来:

- report 在半颗核里跑得慢得多,延迟也会有毛刺(上一节 §3.3.2 量过:跑一阵、停一阵)。这是限额的本意,但对延迟敏感的业务是个坑。
- OOM 还是杀,只是杀对了地方。活下来的那 1 个 worker 对 report 来说多半也没用了 —— 一个任务死了 7/8,剩下的该不该一起死?
- 上限是上限,不是保证。db 组没写任何数,它「拿到 348%」只是因为 report 被摁住了,并没有人承诺给它留着。

这三件事分别通向后面的内容:限流的机制、组内 OOM 的策略、保底那一组旋钮。

### §10.5 只分组、不封顶:400 个 worker 还稀释得了 db 吗

**结论:稀释不了。只要分了组,哪怕一个上限都不写,调度器也是先在组和组之间分,再在组里面分;400 个 worker 合起来只算「report 这一组」。两个组默认各一半,db 理论上拿 200%,实测 152%,差的那一截查到了原因:4 个 db-sim 没有铺满 4 颗核。但这种「按比例分」和 nice 一样没有天花板,db 一闲 report 就吃满,所以它替代不了 `cpu.max`。**

这一小节来自看完初稿后的一个问题:把 report 组的 `cpu.max` 去掉,只保留「db 一组、report 一组」的分组,report 400 个 worker 对 db-sim 4 个进程,db 能拿到多少 CPU?你当时的回答是「不知道」。这个问题确实没法靠前面的内容直接推出来,所以先把两种可能的算法摆出来,再跑。

- **如果还是按进程分**(§1、§2 的老规矩):404 个进程平分 4 颗核,db-sim 占 4 ÷ 404 ≈ 1%,合计约 4%。数据库基本停摆。(这一行是算出来的,没有实跑。)
- **如果按组分**:两个组平分,db 组 200%,它的 4 个进程每个半颗核;report 组 200%,400 个 worker 每个 0.5%。

先交代一个新文件。因为 nice 的权重是发给进程的,进程一多就被稀释(`C1·业务是一组进程`),要让「抢的时候谁多谁少」也按组来算,所以 v2 给每个组一个权重文件 `cpu.weight`:取值 1 ~ 10000,默认 100,同一个父组下面的几个子组按权重的比例分 CPU([cgroup-v2 文档 Weights 一节](https://docs.kernel.org/admin-guide/cgroup-v2.html#weights))。它可以看成「发给组的 nice」。

```
# cat /sys/fs/cgroup/host01/report/cpu.max
max 100000                                   ← 不封顶
# cat /sys/fs/cgroup/host01/db/cpu.weight /sys/fs/cgroup/host01/report/cpu.weight
100
100                                          ← 两个组权重相同

# ./ingroup report python3 report.py cpu 400 &
# ./ingroup db python3 db.py &
# ps -o psr= -C db-sim | sort -n | xargs echo 第 2 秒,4 个 db-sim 所在的核:
第 2 秒,4 个 db-sim 所在的核: 1 1 2 3
# ps -o psr= -C db-sim | sort -n | xargs echo 第 5 秒,4 个 db-sim 所在的核:
第 5 秒,4 个 db-sim 所在的核: 1 1 2 3
查询 1982 次(248 次/秒)  平均 16.2 ms  p99 39.5 ms
这段时间的 CPU:db-sim×4 合计 152%   report-w×400 合计 234%

### 权重不变(100 比 100),这次手工把 4 个 db-sim 一个核放一个
# ./ingroup db python3 db.py &
# i=0; for p in $(pgrep -x db-sim); do taskset -cp $i $p > /dev/null; i=$((i+1)); done
4 个 db-sim 所在的核: 0 1 2 3
查询 2565 次(321 次/秒)  平均 12.5 ms  p99 60.0 ms
这段时间的 CPU:db-sim×4 合计 192%   report-w×400 合计 180%

### 不钉核,把 db 组的权重调到 900(report 还是 100)
# echo 900 > /sys/fs/cgroup/host01/db/cpu.weight
# ./ingroup db python3 db.py &
4 个 db-sim 所在的核: 0 1 2 3
查询 4413 次(552 次/秒)  平均 7.2 ms  p99 19.9 ms
这段时间的 CPU:db-sim×4 合计 345%   report-w×400 合计 36%

### db-sim 没活的时候,权重只有 100 的 report 吃多少
# python3 cpuof.py 3
3 秒内的 CPU:report-w×400 合计 385%
```

![终端留档:只分组不封顶,400 个 worker 时 db-sim 拿到 152%;一个核放一个时 192%;权重调到 900 时 345%;db 闲时 report 吃到 385%](pics/02-shot-cgweight.svg)

**第一件事:是按组分的。** db 拿到 152%,不是 4%。400 个 worker 合计 234%,平均每个 0.6%;4 个 db-sim 平均每个 38%。同样是「普通优先级的进程」,一个 db-sim 拿到的是一个 report-w 的 65 倍,唯一的区别是它们的组不同。对比 §2:同样 400 个 worker,nice 19 已经降到底了,db 也只有 164%;这里 report 一点没降,db 就有 152%。分组这一个动作,顶得上把对方降到最低优先级。

**第二件事:没到 200%,原因是进程没铺开。** 按组平分应该是 200%,实测 152%,差了四分之一。这个差距不是偶然,这一幕前后跑了五遍,db 分别是 174% / 133% / 155% / 141% / 152%,没有一遍到 200%。

留档里那两行 `ps` 是追查的线索:4 个 db-sim 落在 1、1、2、3 号核上,0 号核上一个 db-sim 都没有。于是 0 号核整颗归了 report,db 组在那颗核上有份额也没人去领;1 号核上两个 db-sim 挤在一起,合用 db 组在这颗核上的那一份。

验证办法很直接:权重一个字不改,手工把 4 个 db-sim 一个核钉一个(第三段)。db 立刻到了 192%,report 180%,基本就是对半。所以**差的那一截不在「权重怎么算」,而在「进程摆在哪」:组的份额是在每颗核上各自兑现的,组里的进程不在那颗核上,那颗核上的份额就兑现不了。**

这里有两点我还没有查清,先记进待核清单,不编解释:一是内核为什么没有把 db-sim 自动铺到 4 颗核上(§2 里不分组时,实测 164% 和「一核一个」算出来的 162% 吻合,说明那时是铺开的);二是「组的权重怎么摊到每颗核上」的具体算法。

**第三件事:权重可以调,比例基本兑现。** db 组调到 900,report 还是 100,比例 9 比 1:

- db 应得 400% × 900 ÷ (900 + 100) = 360%。实测 345%,这一遍 4 个 db-sim 正好铺在 0、1、2、3 号核上。
- report 实测 36%。400 个 worker 合计只有三分之一颗核。
- 吞吐 552 次/秒,是独占时(690)的 80%。
- 这一步五遍分别是 352% / 329% / 288% / 257% / 345%。偏低的那两遍(288%、257%)当时没有采样进程所在的核,我推测同样是没铺满,但没有证据,记入待核。

**第四件事:它没有天花板。** db-sim 一停,权重只有 100 的 report 立刻吃到 385%。这和 §2 的洞一是同一个洞:权重只回答「同时要的时候谁多」,回答不了「你最多拿多少」。文档里管这叫 work-conserving:只有此刻用得上资源的组才参与分配,没人要的就给要的人。

把四种管法放在一起(都是 report 400 个 worker 的场景):

| 管法 | 管的单位 | 会不会被进程数稀释 | db 闲的时候 report 吃多少 | db 实测拿到 | 理论值 |
|---|---|---|---|---|---|
| nice 19(§2) | 进程 | 会 | 398%,没有天花板 | 164% | 162% |
| `cpu.weight` 100 比 100 | 组 | 不会 | 385%,没有天花板 | 152%(五遍 133% ~ 174%) | 200% |
| `cpu.weight` 900 比 100 | 组 | 不会 | 同上 | 345%(五遍 257% ~ 352%) | 360% |
| `cpu.max` 半颗核(§10.1) | 组 | 不会 | 约 50%,有天花板 | 348%(两遍都是) | 350% |

从这张表能读出三件事:

1. **`cpu.weight` 治好了 §2 的洞二(稀释),没治洞一(天花板)。** 洞二的病根是 `C1·业务是一组进程`,把权重从进程搬到组上就好了;洞一的病根是 `C2·上限要是绝对数`,比例再怎么调也变不成绝对数。所以 CPU 这一种资源,cgroup 给了两个旋钮:`cpu.weight` 管「抢的时候谁多」,`cpu.max` 管「最多多少」。两个可以同时用。
2. **两个旋钮的脾气不一样。** `cpu.max` 是一本硬账,对到了微秒(§10.1 的 49 969 μs),两遍都是 348%;`cpu.weight` 是按比例尽力而为,结果跟进程摆在哪颗核上有关,五遍能差出几十个百分点。要对别人做承诺,只能用前者。
3. **`cpu.weight` 是 §10.4 末尾说的「保底那一组旋钮」里的第一个。** 它不保证 db 任何时候都有 360%,但保证了「db 和 report 同时要的时候,db 大约拿九成」;db 不用的时候这九成不浪费,report 可以拿去用。`cpu.max` 正相反:report 那半颗核以外的部分,db 不用也是空着。

拿你熟悉的东西比:`cpu.weight` 像数据库资源管理里给各个资源组设的「份额」,只在争用时按比例切;`cpu.max` 像给租户设的硬配额,闲着也不许超。这个类比只在「比例对绝对数」这一点上成立,具体实现不相干。

### §10.6 两个旋钮同时用:各算各的,取更紧的那个

**结论:`cpu.weight` 和 `cpu.max` 互不替代,也互不干扰。一个组最后拿到的 CPU = 按权重分到的那一份,再被自己的上限截一刀。db 忙的时候是权重说了算(report 约 40%,够不着 50% 的上限);db 闲的时候是上限说了算(report 停在 50%,多出来的 350% 空着)。**

接着 §10.5 问的:report 的 `cpu.max` 写半颗核,同时 db 权重 900、report 权重 100。db 闲的时候 report 吃多少?db 忙的时候呢?

你的回答:「还是按照组来分,1:9。」

这句话对了一半。db 忙的时候,确实是按组 1 比 9 分:report 应得 400% × 100 ÷ 1000 = 40%,比它的上限 50% 还低,上限用不上。但 db 闲的时候,1 比 9 这个比例就不起作用了:只有一方要,没有什么可按比例分的,§10.5 里这种时候 report 吃到了 385%;这一次它头上多了一个 `cpu.max`,所以停在 50%。

```
# echo '50000 100000' > /sys/fs/cgroup/host01/report/cpu.max
# echo 900 > /sys/fs/cgroup/host01/db/cpu.weight
# ./ingroup report python3 report.py cpu 400 &

### db 忙的时候
# grep -E 'usage_usec|nr_periods|nr_throttled' /sys/fs/cgroup/host01/report/cpu.stat | xargs
usage_usec 10753033 nr_periods 214 nr_throttled 214
# ./ingroup db python3 db.py &
4 个 db-sim 所在的核: 0 1 2 3
查询 4701 次(588 次/秒)  平均 6.8 ms  p99 15.6 ms
这段时间的 CPU:db-sim×4 合计 341%   report-w×400 合计 34%
# grep -E 'usage_usec|nr_periods|nr_throttled' /sys/fs/cgroup/host01/report/cpu.stat | xargs
usage_usec 13990945 nr_periods 296 nr_throttled 240

### db 闲的时候
# python3 cpuof.py 3
3 秒内的 CPU:report-w×400 合计 57%
# grep -E 'usage_usec|nr_periods|nr_throttled' /sys/fs/cgroup/host01/report/cpu.stat | xargs
usage_usec 15523717 nr_periods 327 nr_throttled 271
```

![终端留档:cpu.max 半颗核与权重 900 比 100 同时生效;db 忙时 report 每周期约 39 ms,db 闲时每周期约 49 ms 且每个周期都被限流](pics/02-shot-cgboth.svg)

**算例(用 report 组自己的账来对,三行 `cpu.stat` 两两相减)。**

| 时段 | 周期数 | report 组用掉的 CPU | 每周期 | 其中被限流的周期 | 谁在起作用 |
|---|---|---|---|---|---|
| db 忙 | 296 − 214 = 82 | 13 990 945 − 10 753 033 = 3 237 912 μs | 39 487 μs(39.5%) | 240 − 214 = 26 | 权重:应得 40%,实得 39.5% |
| db 闲 | 327 − 296 = 31 | 15 523 717 − 13 990 945 = 1 532 772 μs | 49 444 μs(49.4%) | 271 − 240 = 31,每个周期都撞线 | 上限:50% |

- db 忙的时候,db-sim 实测 341%(理论 360%),report 39.5%(理论 40%)。你说的 1 比 9,对上了。
- db 闲的时候,report 每周期用 49 444 μs,31 个周期个个被限流。机器上明明空着三颗半核,它也拿不到。这就是 §10.5 那张表最后一列的区别:权重不浪费,上限会浪费。
- 写成一句话:**report 拿到的 = min(按权重分到的,`cpu.max`)**。忙时 min(40%,50%)= 40%;闲时 min(没人抢,想要多少有多少,50%)= 50%。

三处如实交代:

1. 这一幕跑了三遍。db 忙时 report 每周期用量,后两遍是 36 859 μs 和 39 487 μs(第一遍没有打印 `usage_usec`);被限流的周期数,前两遍都是 82 个里 3 个,最后一遍是 26 个。也就是说「按权重分到 40%」是个平均数,有的周期多一点就会碰到 50 ms 的线。权重是尽力而为,上限是硬账,这里又见了一次。
2. 「db 闲的时候」`cpuof.py` 报的数三遍分别是 42% / 53% / 57%,和组的账(49.4% ~ 49.8%)对不上。我的判断是 `cpuof.py` 这把尺子在这里太粗:它读的是每个进程的 CPU 时间,单位是 10 ms 一格(`getconf CLK_TCK` = 100),而 400 个 worker 在 3 秒里每个只跑了不到 4 ms,不够一格;再加上 report 是「跑 50 ms、停 50 ms」,3 秒的窗口两头各切到半个周期。这个判断没有逐项验证,以组自己的账为准。这也顺带说明了一件事:**想知道一组进程合计用了多少,把 400 个进程的数加起来是不准的,组上那本账才准**,这正是 `C1·业务是一组进程` 要的东西。
3. 第二遍的吞吐不对劲:db-sim 的 CPU 是 362%,吞吐却只有 348 次/秒(第一遍 363% 对 641 次/秒)。这和 §10.5 第三遍是同一种怪现象,这次追了一下,有了线索,见待核 #10。

### §10.7 内存为什么没有「1 比 9」

**结论:内存没有按比例分的旋钮。CPU 时间每个瞬间都是新的,下一片给谁都不用收回什么;内存页一旦分出去就一直被占着,要给别人只能先从占着的人手里收回来。所以内存这边,「抢的时候谁多」变成了「抢的时候先收回谁的」,旋钮叫 `memory.low`(保护)。它管得住回收,管不住杀。**

§10.6 之后的问题:CPU 有按比例的 `cpu.weight`,也有绝对上限 `cpu.max`;内存只见过 `memory.max`。内存能不能也像 CPU 那样按 1 比 9 分?不能的话难在哪?

你的回答:「不太行,因为内存是虚拟映射到物理内存的,而且是根据实际使用来划分的,不是一开始就能决定的。」

「不太行」是对的,下面第一步就能看到内存确实没有 weight 文件。两条理由要分开说:

- 「按实际使用来划分」本身不是障碍。CPU 的权重也是按实际使用分的,§10.5 里 db 一闲,report 就拿到 385%,这就是「谁在用才分给谁」。
- 「虚拟映射」也不是。cgroup 记的是物理页(`C4·账要记在物理消耗上`),§4 里 ulimit 按虚拟地址空间限,正是失败的那一刀。
- 真正的区别在 `C5·内存不可压缩`。CPU 时间用掉就没了,下一个 1 ms 是新的,想改比例,下一片给别人就行,什么都不用收回。内存页分出去以后一直被占着,想改比例,只能先从占着的人手里拿回来。拿回来有代价,而且不一定拿得回来。

内核文档说得很直接:按权重分这种模型「因为是动态的,通常用于无状态的资源」([cgroup-v2 文档 Weights 一节](https://docs.kernel.org/admin-guide/cgroup-v2.html#weights))。CPU 是无状态的,内存是有状态的:每一页里装着某个进程的数据。

所以内存给的是另一种旋钮:保护(Protections)。`memory.low` 写一个数,意思是「这个组用量在这个数以内时,抢的时候先别回收它」;`memory.min` 是它的硬版本([同一文档 memory.low / memory.min](https://docs.kernel.org/admin-guide/cgroup-v2.html#memory-interface-files))。

下面这组实验换到了专用实验机 cg-lab 上(见文末说明),沙箱 host01 只给 1G,让 db 和 report 抢这 1G。先用页缓存(读文件时内核替你缓存的文件页,能扔,扔了以后再读就从盘上重读),再用程序自己申请的内存(匿名页,这台机器没有 swap,拿不回来)。

```
# cat /sys/fs/cgroup/host01/memory.max
1073741824                                    ← 两个组合用 1G

### 1. 内存有没有 weight 这个旋钮
# ls /sys/fs/cgroup/host01/db/ | grep -E '^(cpu|memory)\.(weight|max|high|low|min)$'
cpu.max
cpu.weight
memory.high
memory.low
memory.max
memory.min                                    ← 没有 memory.weight

### 2. 不设保护:db 先把自己的 700M 数据文件读进页缓存,然后 report 也读 700M
# ./ingroup db cat /var/tmp/db.dat > /dev/null
db      合计   700 MiB   文件页   700 MiB   匿名页     0 MiB   memory.low 0
# ./ingroup report cat /var/tmp/rep.dat > /dev/null
db      合计   454 MiB   文件页   454 MiB   匿名页     0 MiB   memory.low 0
report  合计   566 MiB   文件页   566 MiB   匿名页     0 MiB   memory.low 0
# grep -H pgsteal /sys/fs/cgroup/host01/db/memory.stat | head -1
/sys/fs/cgroup/host01/db/memory.stat:pgsteal 62976

### 3. 清掉页缓存,给 db 组 memory.low = 700M,同样的顺序再来一遍
# echo 700M > /sys/fs/cgroup/host01/db/memory.low
# ./ingroup db cat /var/tmp/db.dat > /dev/null
# ./ingroup report cat /var/tmp/rep.dat > /dev/null
db      合计   700 MiB   文件页   700 MiB   匿名页     0 MiB   memory.low 734003200
report  合计   320 MiB   文件页   320 MiB   匿名页     0 MiB   memory.low 0

### 4. 换成匿名页(没有 swap):db 占 700M(memory.low 还是 700M),report 要 600M
# ./ingroup db python3 hold.py db-sim 700 &
# ./ingroup report python3 hold.py report-w 600 &
bash: line 20:  2682 Killed                     ./ingroup db python3 hold.py db-sim 700
db      合计     0 MiB   文件页     0 MiB   匿名页     0 MiB   memory.low 734003200
report  合计   604 MiB   文件页     0 MiB   匿名页   603 MiB   memory.low 0
# journalctl -k … | grep -E 'oom-kill:|Killed process'
oom-kill:constraint=CONSTRAINT_MEMCG,…,oom_memcg=/host01,task_memcg=/host01/db,task=db-sim,pid=2682,uid=0
Memory cgroup out of memory: Killed process 2682 (db-sim) total-vm:737056kB, anon-rss:722240kB, …
```

(`memof` 是一个小脚本,读两个组的 `memory.current` 和 `memory.stat` 里的 file / anon 两项,换算成 MiB;完整命令和输出见下图。)

![终端留档:内存没有 weight;不设保护时 db 的页缓存被收走 246 MiB;设了 memory.low 700M 后 db 一页没少、report 被挤在 320 MiB;换成匿名页后,受保护的 db-sim 反而被 OOM 杀掉](pics/02-shot-cglow.svg)

**算例。**

- 第 2 步,不设保护:1G 不够两个 700M,内核就回收。db 被收走 700 − 454 = 246 MiB,`pgsteal 62976` 页 × 4 KiB = 246 MiB,对得上。谁先被收,看的是这一页多久没被碰过,和它属于哪个组无关。db 先读的,它的页更旧,所以先被收。
- 第 3 步,db 设了 `memory.low` 700M:db 一页没少(700 MiB),report 只能在剩下的里面转,停在 320 MiB(1024 − 700,再减去两组的一点零头)。report 读后面的数据时,回收的是它自己前面读进来的页。`memory.events` 里 `low 0`,表示 db 的保护一次都没被突破。
- 第 4 步,同样的保护,换成匿名页:db-sim 占着 720 MiB 的匿名页,没有 swap,这些页回收不了;report 还要 600M,1G 装不下,只能杀。日志里范围是 `oom_memcg=/host01`(两个组的父组),挑中的是 db 组里的 db-sim,也就是受保护的那个。report-w 拿到了它的 600M。

第 4 步是这一节最要紧的一点:**`memory.low` 保的是「先别回收我」,不是「别杀我」。** 页缓存可以回收,所以保护有用;匿名页又没有 swap 时,根本没有东西可回收,保护无从谈起,最后是 OOM 在父组范围里挑人,挑的还是最大的那个。要让 db 在这种情况下活下来,得在 report 头上加 `memory.max`(§10.2 的做法),把它挡在自己的组里。

两遍实跑(日志 `cglow-run1.log` 与 `cglow.log`)数字完全一样:454 / 566、700 / 320,两遍都是 db-sim 被杀。

把 CPU 和内存的旋钮放在一起:

| 想表达的意思 | CPU | 内存 | 为什么两边不一样 |
|---|---|---|---|
| 最多多少 | `cpu.max`(到了就停到下个周期) | `memory.max`(到了先回收,回收不动就在组内杀) | 都是绝对数(`C2·上限要是绝对数`);超了以后 CPU 等一等就行,内存等不来(`C5·内存不可压缩`) |
| 抢的时候谁多 | `cpu.weight`(按比例) | 没有按比例;`memory.low` / `memory.min`(先别回收谁) | CPU 每个瞬间都能重新分,内存要先收回才能重分 |
| 超了先减速、不杀 | `cpu.max` 本身就是减速 | `memory.high`(超了就强制回收、让进程变慢,从不触发 OOM) | 这一个本节没实跑 |

这张表也回答了 §10.4 末尾那句「保底那一组旋钮」:CPU 这边是 `cpu.weight`,内存这边是 `memory.low` / `memory.min`,二者都只在抢的时候起作用;内存那边还要加一句「只保护可回收的那部分」。

#### §10.7.1 给 report 加上 memory.max:边界划在哪,就在哪里杀

接着上面第 4 步问:同样是 db 700M、report 要 600M 的匿名页,再给 report 组加 `memory.max` 300M,谁会被杀?日志里 OOM 的范围会从 `/host01` 变成什么?

你的回答:「report 被杀。」对。范围那一半没答,实跑给出来了:

```
# echo 700M > /sys/fs/cgroup/host01/db/memory.low
# echo 300M > /sys/fs/cgroup/host01/report/memory.max
# ./ingroup db python3 hold.py db-sim 700 &
db-sim(pid 4053)已占住 700 MiB
# ./ingroup report python3 hold.py report-w 600 &
bash: line 20:  4058 Killed                     ./ingroup report python3 hold.py report-w 600

# journalctl -k … | grep -E 'oom-kill:|Killed process'
oom-kill:constraint=CONSTRAINT_MEMCG,…,oom_memcg=/host01/report,task_memcg=/host01/report,task=report-w,…
Memory cgroup out of memory: Killed process 4058 (report-w) total-vm:327220kB, anon-rss:306504kB, …

# grep -H oom_kill …/host01/memory.events …/host01/db/memory.events …/host01/report/memory.events
/sys/fs/cgroup/host01/memory.events:oom_kill 1
/sys/fs/cgroup/host01/db/memory.events:oom_kill 0
/sys/fs/cgroup/host01/report/memory.events:oom_kill 1
# grep -H -E '^(oom_kill|max) ' …/host01/report/memory.events.local …/host01/memory.events.local
/sys/fs/cgroup/host01/report/memory.events.local:max 53
/sys/fs/cgroup/host01/report/memory.events.local:oom_kill 1
/sys/fs/cgroup/host01/memory.events.local:max 0
/sys/fs/cgroup/host01/memory.events.local:oom_kill 0

# ps -o pid,rss,comm -C db-sim,report-w
    PID   RSS COMMAND
   4053 727836 db-sim
```

![终端留档:report 组加了 memory.max 300M 后,OOM 范围变成 /host01/report,被杀的是涨到约 299 MiB 的 report-w,db-sim 活着](pics/02-shot-cgmax.svg)

- 范围从 `oom_memcg=/host01` 变成了 `oom_memcg=/host01/report`。哪个组的上限先撞到,OOM 就在哪个组里发生、只在那个组里挑人。report-w 涨到 anon-rss 306 504 kB ≈ 299 MiB 时撞线(`max 53`:撞了 53 次线,每次先试着回收,收不动),最后被杀。db-sim 的 728 MiB 原封不动。
- 和上面第 4 步对比:两次 db 都有同样的 `memory.low`,结果一死一活。决定谁死的不是保护,是上限划在哪。这正是你灵魂问题②里「边界谁划的」的答案:**边界就是管理员写进某个组 `memory.max` 的那个数,它决定了 OOM 发生在哪一层、在哪些进程里挑人。**
- 一个顺带的细节:父组 host01 的 `memory.events` 也显示 `oom_kill 1`,但 `memory.events.local` 是 0。前者把整棵子树的事件都算上,后者只算自己这一层。这次 OOM 发生在 report,往上汇总到了 host01。这是 `C7·限额要能层层转包` 在账上的样子:父组能看到子树里发生的一切,但事情是在子组那一层处理的。
- 两遍实跑(`cgmax-run1.log` 与 `cgmax.log`)结果一致。

### §10.8 进程数和磁盘 IO:换个控制器,同样的办法

**结论:§6 里旧工具管不住的两样东西,放进组里一样管住了。进程数:组里最多 20 个,root 也不例外。磁盘 IO:每秒最多写 10 MiB,带缓冲的写也算。用的还是「分组、记账、设限」,只是换了一个控制器。**

(这一小节是后补的,原因见 §8.3:前面重演时只演了 CPU 和内存。实验在专用实验机 cg-lab 上跑。)

**进程数。** §6.2 的两个洞:`ulimit -u` 数的是「这个用户」的进程,而且对 root 不生效。同一个测试程序 `forkn.py`,这次用组来管:

```
# echo 20 > /sys/fs/cgroup/host01/report/pids.max
# ./ingroup report python3 forkn.py 100
第 20 次 fork 失败:[Errno 11] Resource temporarily unavailable
想要 100 个子进程,成功 fork 出 19 个

# grep -H . …/report/pids.max …/report/pids.peak …/report/pids.events
/sys/fs/cgroup/host01/report/pids.max:20
/sys/fs/cgroup/host01/report/pids.peak:20
/sys/fs/cgroup/host01/report/pids.events:max 1

# ./ingroup db python3 forkn.py 100
想要 100 个子进程,成功 fork 出 100 个
```

![终端留档:report 组 pids.max 为 20 时,root 身份的第 20 次 fork 失败;db 组不受影响](pics/02-shot-cgpids.svg)

- 上限 20,主进程自己算 1 个,所以成功 19 个,第 20 次 fork 失败。这次是以 root 身份跑的,§6.2 里 root 的 100 次 fork 全部成功。
- 数的是这个组,不是这个用户:同一个 root 在 db 组里 fork 100 个,一个不少。
- 超了的处置是「拒绝」:fork 返回错误,没有谁被杀。

**磁盘 IO。** §6.1 的洞:带缓冲的写是先进页缓存、稍后由内核线程写盘,`ionice` 管不到。这次给 report 组在这块盘(`253:0` 是 vda 的设备号)上设每秒最多写 10 MiB:

```
### 不设限,绕过页缓存直接写 50 MiB
# ./ingroup report dd if=/dev/zero of=/var/tmp/r1.tmp bs=1M count=50 oflag=direct 2>&1 | tail -1
52428800 bytes (52 MB, 50 MiB) copied, 0.00679885 s, 8.7 GB/s

# echo '253:0 wbps=10485760' > /sys/fs/cgroup/host01/report/io.max
# ./ingroup report dd if=/dev/zero of=/var/tmp/r2.tmp bs=1M count=50 oflag=direct 2>&1 | tail -1
52428800 bytes (52 MB, 50 MiB) copied, 4.99987 s, 10 MB/s

### 同样的限制,换成带缓冲的写,等落盘再返回
# ./ingroup report dd if=/dev/zero of=/var/tmp/r3.tmp bs=1M count=50 conv=fsync 2>&1 | tail -1
52428800 bytes (52 MB, 50 MiB) copied, 4.97412 s, 11 MB/s
# cat /sys/fs/cgroup/host01/report/io.stat
253:0 rbytes=16384 wbytes=157286400 rios=4 wios=213 dbytes=0 dios=0

### 对照:db 组没有设限,同样带缓冲地写 50 MiB
# ./ingroup db dd if=/dev/zero of=/var/tmp/d1.tmp bs=1M count=50 conv=fsync 2>&1 | tail -1
52428800 bytes (52 MB, 50 MiB) copied, 0.0261246 s, 2.0 GB/s
```

![终端留档:report 组限每秒写 10 MiB 后,直接写和带缓冲的写 50 MiB 都是 5 秒;db 组同样的写 0.026 秒](pics/02-shot-cgio.svg)

**算例。**

- 50 MiB ÷ 10 MiB/s = 5 秒。直接写 4.99987 秒,带缓冲的写 4.97412 秒。不设限时是 0.0068 秒。
- **带缓冲的写也限住了**,这是 §6.1 里 `ionice` 做不到的,也是 §9.2 里 v1 做不好的。这笔 IO 是内核线程发的,它之所以记到 report 头上,是因为内存和 IO 在同一棵树上,脏页是谁的,IO 就算谁的(`C8·一笔开销跨多种资源`)。
- 账在 `io.stat` 里:三次各写 50 MiB,`wbytes` 最后是 157 286 400 字节 = 150 MiB,一个字节不差。
- db 组不受影响:0.026 秒。

四种资源放在一起:

| 资源 | 旧工具(§1 ~ §6) | 旧工具的洞 | 控制器 | 限 | 实测 | 超了怎么处置 |
|---|---|---|---|---|---|---|
| CPU | nice、taskset | 按进程发、没有上限、能自己解绑 | cpu | `cpu.max` | 8 个或 400 个 worker 都是约 50% | 等到下个周期 |
| 内存 | ulimit -v、全机 OOM | 按进程、限的是虚拟地址、杀错人 | memory | `memory.max` | 杀 7 个 report-w,db-sim 活着 | 组内回收,收不动组内杀 |
| 磁盘 IO | ionice | 管不到带缓冲的写 | io | `io.max` | 50 MiB 写 5 秒,带缓冲的也是 | 请求排队等 |
| 进程数 | ulimit -u | 按用户数、root 不算 | pids | `pids.max` | 第 20 次 fork 失败 | 这次 fork 失败 |

四行的做法是同一个:进到组里,消耗时记到组的账上,账上有个上限。不同的只有最后一列,而最后一列是资源的性质决定的:CPU 时间和 IO 带宽下一刻还会有,可以等;fork 有返回值,可以拒绝;内存既等不来也没法拒绝,只能回收或杀(`C5·内存不可压缩`)。

一处照实交代:磁盘 IO 第一遍跑的时候(日志 `cgio-run1.log`),四次 dd 写的是同一个文件名,结果有两处对不上:`io.stat` 的 `wbytes` 比写入量多出 50 MiB;没有设限的 db 组那一次也被拖到了 5 秒。改成每次写不同的文件之后(正文这一遍)两处都正常。我猜测和「一个文件的回写同一时间只归一个组」有关,没有验证,记入待核。

## §11 约束清单(C1 ~ C8)

| # | 约束 | 来源 | 不可再分性 | 哪一刀逼出来的 |
|---|---|---|---|---|
| C1 | **业务是一组进程**:管的单位必须是「组」,管的是合计 | 进程模型(fork)+ 应用自己决定开几个进程 | 开几个进程是应用的自由,内核无法预知,也不能禁止 | §1 现场(690 → 226) |
| C2 | **上限要是绝对数**:不随对手多少、不随自己进程数变化 | 多个业务同机时相互的承诺 | 相对权重只能回答「谁多」,任何权重表都回答不了「最多多少」 | §2 nice(闲时 398%;400 个时 268) |
| C3 | **被管者不可信**:组籍和上限由内核强制、管理员掌握 | 被限制的程序不是管理员写的 | 只要边界能被进程自己改,就不存在边界 | §3 taskset、setsid |
| C4 | **账要记在物理消耗上**:物理页、真实 CPU 时间、真实 IO | 硬件:稀缺的是物理资源 | 地址空间等「预订量」不稀缺;页缓存等消耗不挂在任何进程名下 | §4 ulimit(合计 2461 MiB;10 MiB 被拒) |
| C5 | **内存不可压缩**:超了只能回收或杀,所以杀的范围必须有边界 | 资源的物理性质 | CPU 时间每个周期都有新的,物理页占了不还就没有 | §5 OOM(db-sim 被杀) |
| C6 | **共用一个内核**:隔离不能靠每人一套内核;记账在最热的路径上,必须便宜 | 成本 | 预留出去的资源无法互借;要互借就必须同处一个内核 | §7 虚拟机 |
| C7 | **限额要能层层转包**:组套组,父组的上限约束整棵子树 | 资源归属的层级(机器 → 平台 → 租户 → 容器) | 上级管不了也不该管下级内部怎么分,但必须管住合计 | §8.2 v1 的树 |
| C8 | **一笔开销跨多种资源**:所有资源必须共用同一套分组 | 内核实现的事实:写文件先占内存、后由内核线程写盘 | 只要「占内存的人」和「发 IO 的人」不是同一个执行者,两边就必须能互相查到对方的组 | §9.2 v1 多棵树 |

八条里,前六条回答「为什么要有 cgroup」,`C7·限额要能层层转包` 回答「为什么是树」,`C8·一笔开销跨多种资源` 回答「为什么只能有一棵树」(也就是为什么有 v2)。

## §12 核心想法怎么接住这些约束

| 设计 | 接住了 | 代价 / 留下的问题 |
|---|---|---|
| 进程带组籍,fork 继承,自己改不了 | `C1·业务是一组进程`、`C3·被管者不可信` | 每个进程多一份数据;fork 和退出都要多做一点事 |
| 账挂在组上,消耗发生时记账 | `C4·账要记在物理消耗上` | 记账落在调度和内存分配的热路径上,必须想办法做便宜(`C6·共用一个内核` 的推论) |
| 限是绝对数,满了就地处置 | `C2·上限要是绝对数`、`C5·内存不可压缩` | CPU 的「处置」是让整组停到下个周期,带来延迟毛刺;内存的「处置」到头还是杀 |
| 组是一棵树 | `C7·限额要能层层转包` | 每次记账都要顺着树往上记到每一层祖先?(这个问题留给架构) |
| 只有一棵树(v2) | `C8·一笔开销跨多种资源` | 放弃了「不同资源按不同方式分组」的自由 |

最后一行是个真实的取舍:v1 的多棵树不是没有用处,有人确实想让 CPU 按部门分、内存按服务分。v2 的判断是这种自由用处不大,而代价(对不上账)太大,于是砍掉了,换来的折中是「同一棵树上,不同资源可以分到不同的深度」。

## §13 这些看着像约束,其实不算

| 常听到的说法 | 为什么不算 |
|---|---|
| 「为了隔离,让进程互相看不见」 | 那是 namespace 的事。cgroup 不管看得见什么,只管用得了多少(上一节 §5) |
| 「为了容器」 | 顺序反了。cgroup 在 2.6.24 就有了,比 docker 早好几年;systemd 给每个服务建组,也和容器无关。是容器用了它,不是它为容器而生 |
| 「为了高性能」 | 这是要求,不是约束。真正的约束是 `C6·共用一个内核` 推出来的那一句:记账在热路径上,所以必须便宜 |
| 「为了公平」 | 调度器本来就公平,§1 的数字分毫不差。缺的不是公平,是公平的单位(`C1·业务是一组进程`) |
| 「为了保证每个业务拿得到资源」 | `cpu.max` 和 `memory.max` 是上限,不是保底。保底是另一组旋钮,属于「怎么分」,不属于「为什么要有」 |
| 「为了安全」 | cgroup 管用量,不管权限。它让 report 吃不垮机器,但拦不住 report 去读别人的文件 |

## §14 呼应灵魂问题

| 你的问题 | 这一节拿到的 | 还缺的 |
|---|---|---|
| 往 `cpu.max` 写 `50000 100000`,内核怎么让这组进程最多吃半颗核? | 为什么必须是「组 + 绝对数」而不是 nice 或绑核(`C1·业务是一组进程`、`C2·上限要是绝对数`);实测它确实做到了:8 个或 400 个 worker 都是约 50%,每周期 49 969 μs;为什么进程自己逃不掉(`C3·被管者不可信`) | 机制本身:账记在哪个结构上、谁在加、数满那一刻 400 个进程是怎么同时被摁住的、下个周期谁放它们出来 |
| 容器 OOM 只杀容器里的进程,边界谁划的、账怎么记? | 为什么内存超了只能杀(`C5·内存不可压缩`);没有边界时杀的是全场最胖的(db-sim);有了组,范围变成 `oom_memcg=/host01/report`,7 个 report-w 死、db-sim 活;账必须记物理页,包括页缓存(`C4·账要记在物理消耗上`) | 一页内存记到组头上的那一刻发生了什么;到上限后先回收什么、何时才杀;组里挑谁;为什么 §5 多杀了一个 |

粗略估计:两个问题各闭环到三成左右。上一节知道了问题里每个词指什么;这一节知道了为什么非这样设计不可,并且亲眼看到它生效。还不知道的是内核里的每一步是怎么做的。

## §15 留下的悬念

这一节每个结论背后都压着一个「那它是怎么做到的」:

1. **组籍存在哪?** 每个进程「多带一个组籍」,带在什么东西上?fork 的那一刻内核做了什么,让子进程生在父进程的组里?
2. **每秒几百万次,怎么记得起?** §7 算过,0.1 秒里要给 26 万个页记账,每次调度切换也要记。每一次都去改组上的同一个计数器吗?4 颗核同时改呢?(`C6·共用一个内核`)
3. **50 ms 用完的那一刻发生了什么?** 400 个 worker 散在 4 颗核上,是谁、用什么办法把它们同时摁住的?为什么连 fork 都要排队?
4. **树怎么约束?** 子组记一笔账,父组、祖父组的账怎么跟着动?每次都要爬一遍树吗?(`C7·限额要能层层转包`)
5. **组内 OOM 的细节。** 先回收什么?挑谁?为什么 §5 里 db-sim 死了之后还要多杀一个 worker?
6. **组的份额怎么落到每颗核上?** §10.5 里两个组权重相同,db 却只拿到 152% 而不是 200%,因为 4 个 db-sim 只占了 3 颗核。一个组的权重是怎么摊到 4 颗核上的?内核为什么没把它们铺开?

还有上一节挂着的那个问题:9 个一模一样的死循环都在同一个 0.5 核的组里,为什么有一个拿到 12%、其余只有 4%~6%?

这些都是「它是怎么解决的」那一段的内容。

## 待核清单

| # | 内容 | 状态 |
|---|---|---|
| 1 | §5:db-sim 被杀之后为什么还多杀 worker(三遍实跑分别多杀 1 / 3 / 1 个)。原因未查清,留到讲内存 OOM 路径的源码时回答 | 待核 |
| 2 | §5 / §10.2:全机 OOM 和组内 OOM 用的是同一套挑人规则(范围内找最胖的,再按 `oom_score_adj` 调整)。目前只有实测与两处日志对照,源码层面未确认 | 待核 |
| 3 | §2:nice 0 的权重 1024、nice 19 的权重 15。实测比例(97.2% / 40.6%)与之吻合;源码位置与行号进源码时补 | 实测吻合,源码待核 |
| 4 | §9.2:v1 时代带缓冲的写入在 blkio 那边到底限不限得住,需要一条一手出处(目前只引了 v2 文档对「控制器无法合作」的总体说法) | 待核 |
| 5 | §10.1:吞吐是独占时的 92%~93% 而 CPU 占比是 87%,差的那几个百分点归因于「不同遍之间单次查询的 CPU 开销波动」,未进一步验证(可能与上一节待核 #8 的虚拟机效应有关) | 待核 |
| 6 | §6.1:这台机器上 dd 结束后 `Dirty` 计数几乎不涨、回写启动得很快,和预想的「脏页攒一阵再写」不一样。结论(写盘的是内核线程、页缓存不在进程名下)不受影响,但回写的时序没有深究 | 待核 |
| 7 | §13:「cgroup 比 docker 早好几年」里 docker 的首发年份;§8.2 第一版的作者与合入经过。讲来路时配一手出处(与上一节待核 #3 合并处理) | 待核 |
| 8 | §10.5:两组权重相同时 db 只有 133% ~ 174%(理论 200%)。已证实的部分:4 个 db-sim 每遍都只落在 2 ~ 3 颗核上,手工一核钉一个之后是 192%。未查清的部分:内核为什么不把它们铺开(§2 不分组时是铺开的);组的权重摊到每颗核上的算法。留到讲 CPU 控制器的机制与源码时回答 | 现象已证实,机制待核 |
| 9 | §10.5:权重 900 比 100 的五遍里有两遍偏低(288%、257%,理论 360%),当时没有采样进程所在的核,「同样是没铺满」只是推测 | 待核 |
| 10 | 同样的 CPU 占比,吞吐有时只有一半:§10.5 第三遍(`cgweight-run3.log`,155% 对 142 次/秒)和 §10.6 第二遍(`cgboth-run2.log`,362% 对 348 次/秒),相当于每次查询花的 CPU 时间从 5.8 ms 变成了 10 ms 左右。追查到的线索(`src/logs/hostspeed-diag.log`):虚拟机空闲时单独跑同一段计算,「算一阵、睡半秒」的跑法每次要 9.1 ~ 10.6 ms,连续跑则是 4.6 ms,4 个进程一起连续跑是 5.3 ~ 6.5 ms。也就是说同一段计算在这台虚拟机里花的 CPU 时间能差一倍多,而且虚拟机内部看不出被抢(墙上时间等于 CPU 时间)。宿主机有两档核(5 + 10),我怀疑是虚拟机的 CPU 有时被排到了慢的那一档核上,或者频率没升上去;宿主机一侧没有验证。影响:**不同遍之间的「次/秒」不能直接比,CPU 占比和组的账可以**;正文的结论都落在 CPU 占比上。#5 和上一节待核 #8 很可能是同一个原因 | 有线索,宿主机一侧待核 |
| 11 | §10.7 第 4 步:受 `memory.low` 保护的 db-sim 被父组 OOM 挑中。实测两遍都是如此,和「OOM 挑人时不看 memory.low,只看谁大」一致;源码层面未确认。memory.min 在同样情况下会不会不同,也没有实跑 | 实测两遍一致,源码待核 |
| 12 | §10.7 第 2 步:「谁先被收,看这一页多久没被碰过,和组无关」是按 db 先读、先被收的现象推的,没有单独实验(比如反过来让 report 先读)验证 | 待核 |
| 13 | §10.8:磁盘 IO 第一遍(`cgio-run1.log`,四次 dd 覆盖写同一个文件)里,`io.stat` 的 `wbytes` 是 200 MiB 而不是 150 MiB,且没有设限的 db 组写这个文件也是 5 秒。换成不同文件后正常。猜测与文件回写的归属有关,未验证 | 待核 |

已核实(出处都在正文链接里):`RLIMIT_AS` 限的是地址空间、`RLIMIT_RSS` 只在 2.4.30 之前有效、`RLIMIT_NPROC` 按真实用户计数且对 root 与两种能力不生效([getrlimit(2)](https://man7.org/linux/man-pages/man2/getrlimit.2.html));异步写不受 IO 优先级影响([ioprio_set(2)](https://man7.org/linux/man-pages/man2/ioprio_set.2.html));2.6.24 / 3.10 / 4.5 / 4.15 四个版本节点([cgroups(7)](https://man7.org/linux/man-pages/man7/cgroups.7.html));v1 的四类问题与 No Internal Process Constraint、Writeback 三处引文([cgroup-v2 文档](https://docs.kernel.org/admin-guide/cgroup-v2.html))。

§10.8 的留档说明:进程数与磁盘 IO 两段在 cg-lab 上跑,日志 `src/logs/cgpids.log`、`cgio.log`(磁盘 IO 的第一遍另存为 `cgio-run1.log`)。

§10.7 的留档说明:这一节起实验换到专用实验机 cg-lab(和 cg 同一个系统镜像,同样是内核 7.0.0-38;4 核 4G,只跑本文的实验,用完删除),因为 cg 上跑着别的服务,之前吃满 CPU 的实验已经干扰到它们。§10.7 跑了两遍,数字一致,正文与图用后一遍(`src/logs/cglow.log`),前一遍是 `cglow-run1.log`;§10.7.1 同样两遍一致(`cgmax.log`、`cgmax-run1.log`)。之前各节的数字都来自 cg,没有重跑。

§10.6 的留档说明:跑了三遍,正文与图用最后一遍(`src/logs/cgboth.log`),前两遍原样保留为 `cgboth-run1.log`、`cgboth-run2.log`。

§10.5 的留档说明:这一幕前后跑了五遍。正文与图用的是最后一遍(`src/logs/cgweight.log`);第二到第四遍的日志原样保留为 `cgweight-run2.log` ~ `cgweight-run4.log`;第一遍(174% / 352%)当时还没加采样核号的命令,日志被后一遍覆盖了,只剩这两个数。另有一遍只用于排查的运行(每半秒采样一次核号,db 138%),没有留日志。

实验环境的一处变化,如实记录:做这一节实验时发现虚拟机里多了 mysqld、clickhouse、redis 三个真服务(当天 17:36 之后装的,不是这一节的实验装的)。因此所有实验都关进了沙箱组,没有做真正的全机 OOM;实验前后这三个服务的进程和内存占用没有变化。

## 修订记录

| 时间 | 修订摘要 | 触发原因 |
|---|---|---|
| 2026-11-13 | 初稿:host01 上逐件试旧工具(不管 / nice / taskset / ulimit / OOM / 虚拟机),IO 与进程数各一例;八刀八条约束;核心想法;v1 的四个痛与 v2 的改法;换成 cgroup 重演一遍并前后对照。13 张终端留档图 + 3 张示意图,全部数字取自同一批留档日志 | 开场对齐后用户「没有了」 |
| 2026-11-13 | 新增 §10.5「只分组、不封顶」:实跑 `cpu.weight`(100 比 100 时 db 152%,一核钉一个时 192%,900 比 100 时 345%,db 闲时 report 385%),四种管法对照表,点明 `cpu.weight` 与 `cpu.max` 各管一个洞;§15 加第 6 条悬念;待核清单加 #8 ~ #10;新增留档图 `02-shot-cgweight.svg` | 用户对反问「去掉 cpu.max 只分组,db 能拿多少」回答「不知道」 |
| 2026-11-13 | 新增 §10.6「两个旋钮同时用」:记录用户的回答「还是按照组来分,1:9」(忙时对,闲时由上限决定);实跑三遍,用组的 `cpu.stat` 对账(忙时每周期 39 487 μs,闲时 49 444 μs 且 31/31 周期被限流);归纳为 min(按权重分到的,`cpu.max`)。待核 #10 补上虚拟机速度浮动的排查线索。新增留档图 `02-shot-cgboth.svg` | 用户回答第 2 个反问 |
| 2026-11-13 | 新增 §10.7「内存为什么没有 1 比 9」:记录用户回答(「不太行」对;「虚拟映射」「按实际使用」不是原因,真正原因是 `C5·内存不可压缩`);在专用实验机 cg-lab 实跑两遍:内存没有 weight,不设保护时 db 页缓存被收 246 MiB,`memory.low` 700M 时 db 不少一页、report 停在 320 MiB,匿名页情况下受保护的 db-sim 反被 OOM 杀;CPU / 内存旋钮对照表;待核 #11、#12;新增图 `02-shot-cglow.svg` | 用户回答第 3 个反问 |
| 2026-11-14 | 新增 §10.7.1「给 report 加上 memory.max」:记录用户回答「report 被杀」(对,范围那一半由实跑补上);cg-lab 实跑两遍:`oom_memcg=/host01/report`,report-w 在约 299 MiB 被杀,db-sim 存活;父组 `memory.events` 与 `memory.events.local` 的区别;新增图 `02-shot-cgmax.svg` | 用户回答第 4 个反问 |
| 2026-11-14 | 补「cgroup 是管各种资源的框架」这条线:新增 §8.3(八条约束分成「与资源无关」和「每种资源各不相同」两堆,所以做成公共骨架 + 控制器;实测 9 个控制器)与 §10.8(进程数:`pids.max` 20,root 的第 20 次 fork 失败;磁盘 IO:`io.max` 每秒 10 MiB,直接写与带缓冲的写 50 MiB 都是 5 秒,db 组 0.026 秒;四种资源对照表);待核 #13;新图 `02-shot-cgpids.svg`、`02-shot-cgio.svg` | 用户新视角:「cgroup 不止能管理 CPU,还能管理内存、IO……是个架构」 |
