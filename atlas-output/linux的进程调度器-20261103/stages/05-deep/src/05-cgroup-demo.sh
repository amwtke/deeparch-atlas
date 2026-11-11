#!/usr/bin/env bash
# 05-cgroup-demo.sh —— 组调度 + 带宽控制的两个可观察效果
#
# 需要:cgroup v2 已挂载在 /sys/fs/cgroup(systemd 发行版默认),root 权限,CPU0 可用。
# 运行:sudo ./05-cgroup-demo.sh
# 对应源码:cpu.weight → core.c cpu_weight_write_u64 → sched_group_set_shares → fair.c calc_group_shares
#          cpu.max    → core.c cpu_max_write → tg_set_cfs_bandwidth;超额 → fair.c throttle_cfs_rq
set -euo pipefail
CG=/sys/fs/cgroup
A=$CG/atlas-A; B=$CG/atlas-B
cleanup() { pkill -P $$ 2>/dev/null || true; sleep 0.3; rmdir $A $B 2>/dev/null || true; }
trap cleanup EXIT

echo "+cpu" > $CG/cgroup.subtree_control 2>/dev/null || true
mkdir -p $A $B
echo 100 > $A/cpu.weight     # A 组权重 100
echo 300 > $B/cpu.weight     # B 组权重 300 → 同一个核上 B 应拿 75%,A 拿 25%

spin() { taskset -c 0 bash -c 'while :; do :; done' & echo $!; }

echo "== 实验 1:A 组 3 个忙循环,B 组 1 个忙循环,全部压在 CPU0"
pA=(); for i in 1 2 3; do p=$(spin); echo $p > $A/cgroup.procs; pA+=($p); done
pB=$(spin); echo $pB > $B/cgroup.procs
sleep 3
echo "-- 每个进程最近 3 s 的 CPU 占比(top):"
top -b -n 1 -p $(IFS=,; echo "${pA[*]},$pB") | awk 'NR>7 {printf "  pid %-7s %5s%%\n", $1, $9}'
echo "   期望:B 的那个 ≈ 75%,A 的三个各 ≈ 8%(没有 cgroup 时四个各 25%)"
echo "-- 内核侧:A 组在 CPU0 的 group entity 权重(/sys/kernel/debug/sched/debug 里 cfs_rq[0]:/atlas-A 的 .se->load.weight)"
grep -A 30 "cfs_rq\[0\]:/atlas-A" /sys/kernel/debug/sched/debug 2>/dev/null | grep -E "se->load.weight|h_nr_running" | head -2 || echo "   (需要 CONFIG_SCHED_DEBUG + debugfs)"

echo
echo "== 实验 2:给 B 组加带宽上限 cpu.max = 50000 100000(每 100 ms 最多 50 ms)"
echo "50000 100000" > $B/cpu.max
sleep 2
echo "-- B 组 cpu.stat:"
grep -E "nr_periods|nr_throttled|throttled_usec" $B/cpu.stat | sed 's/^/   /'
echo "   期望:nr_throttled 每 100 ms 增加 1(B 组每个周期都在 50 ms 处被 throttle_cfs_rq 挂起,"
echo "         下个周期 sched_cfs_period_timer → distribute_cfs_runtime → unthrottle_cfs_rq 放回)"
echo "-- 此时 top:B 应掉到 ≈ 50%,A 的三个各 ≈ 16%"
top -b -n 1 -p $(IFS=,; echo "${pA[*]},$pB") | awk 'NR>7 {printf "  pid %-7s %5s%%\n", $1, $9}'
