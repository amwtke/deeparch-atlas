#!/bin/bash
# oomrun.sh <轮数>:同一个组内 OOM 场景跑若干轮,每轮记下杀了几个
SB=/sys/fs/cgroup/host01
for r in $(seq 1 $1); do
  mkdir -p $SB/report; echo 300M > $SB/report/memory.max
  bpftrace t12-oomrace.bt > race$r.out 2>&1 &
  for i in $(seq 1 40); do grep -q Attached race$r.out 2>/dev/null && break; sleep 0.25; done; sleep 0.3
  ./ingroup report python3 hold.py report-w 150 > /dev/null &
  ./ingroup report python3 hold.py report-w 80 > /dev/null &
  sleep 2
  ./ingroup report python3 hold.py report-w 100 10 0.1 > /dev/null &
  sleep 3.5; pkill -INT bpftrace; sleep 1
  echo "=== 第 $r 轮:oom_kill $(awk '/^oom_kill /{print $2}' $SB/report/memory.events),活下来 $(pgrep -c -x report-w) 个"
  echo 1 > $SB/report/cgroup.kill; sleep 0.6; rmdir $SB/report
done
