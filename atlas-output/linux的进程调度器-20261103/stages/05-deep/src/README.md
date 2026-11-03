# 05-deep/src — 三样东西

| 文件 | 是什么 | 在哪里能跑 |
|---|---|---|
| `05-eevdf-sim.py` | 按 6.12 `fair.c` 规则写的单核 EEVDF 模拟器(权重表、`avg_vruntime` 累加器、lag 夹紧与守恒放大、`update_deadline`、`pick_eevdf` + `RUN_TO_PARITY` + `PREEMPT_SHORT`、`DELAY_DEQUEUE`、tick 4 ms、唤醒抢占) | 任何有 Python 3 的机器,**本机已跑**,输出贴在 `05-deep.md` §2.4 / §2.6 |
| `05-demo.c` | Linux 专用:三个线程(nice 19 / nice 0 / 每 10 ms 醒一次的 nice −10)同核,读 `/proc/self/task/<tid>/sched` 与 cgroup `cpu.stat` | **未在本机验证**(macOS 无法编译);只过了 `clang -fsyntax-only` |
| `05-sched-trace.bt` | bpftrace:唤醒到上台延迟直方图、抢占 vs 阻塞计数、迁移是唤醒时还是均衡时 | Linux + bpftrace,未在本机验证 |

## 跑模拟器

```bash
python3 -I 05-eevdf-sim.py how36    # How §3.6 三任务五拍(默认)
python3 -I 05-eevdf-sim.py how14    # How §14:redis 带正 lag 醒来能连跑多久
python3 -I 05-eevdf-sim.py long     # 300 ms:份额与权重对账
python3 -I 05-eevdf-sim.py deep26   # Deep §2.6:B 睡 20 ms 醒来 lag 记成多少、能否抢 A
```

改参数:文件头部 `TICK_NSEC`(HZ)、`BASE_SLICE`(核数)、五个 `sched_feat` 开关。

## Linux 上观察真机(对照模拟器)

```bash
gcc -O2 -pthread -o 05-demo 05-demo.c && ./05-demo
# 另开终端:
watch -n1 'grep -E "vruntime|deadline|slice|nr_switches|nr_migrations|load.weight" /proc/$(pgrep 05-demo)/task/*/sched'
cat /sys/kernel/debug/sched/debug | sed -n '/cpu#0/,/cpu#1/p'   # 这颗核的树:avg_vruntime / min_vruntime / 每个任务的 vruntime、eligible、deadline
cat /sys/kernel/debug/sched/features                              # RUN_TO_PARITY PREEMPT_SHORT DELAY_DEQUEUE ...
cat /sys/kernel/debug/sched/base_slice_ns /proc/sys/kernel/sched_cfs_bandwidth_slice_us
sudo perf sched record -- sleep 2 && sudo perf sched latency --sort max
sudo perf stat -e sched:sched_migrate_task,sched:sched_switch,sched:sched_wakeup -a sleep 5
sudo bpftrace 05-sched-trace.bt
```

cgroup 带宽(主线③):

```bash
sudo mkdir /sys/fs/cgroup/demo
echo "200000 100000" | sudo tee /sys/fs/cgroup/demo/cpu.max       # 限 2 核
echo $$ | sudo tee /sys/fs/cgroup/demo/cgroup.procs
./05-demo /sys/fs/cgroup/demo                                     # 每秒打印 nr_periods / nr_throttled / throttled_usec
```

## gdb / kgdb 断点(需要带调试信息的 vmlinux,最省事是 QEMU + `-s`)

```
b pick_eevdf                  # fair.c:907   挑人
b place_entity                # fair.c:5266  醒来放回(看 lag 放大)
b update_entity_lag           # fair.c:702   睡下去存 lag(看夹紧)
b check_preempt_wakeup_fair   # fair.c:8764  唤醒抢占
b sched_balance_rq            # fair.c:11669 一次均衡
b task_hot                    # fair.c:9260  热不热
b throttle_cfs_rq             # fair.c:5915  整组下树
b distribute_cfs_runtime      # fair.c:6191  周期到点放回
```
