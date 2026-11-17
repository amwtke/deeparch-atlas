#!/usr/bin/env bash
# 留档用的「会话」脚本:05-deep.md 里的实验。约定同 03-evidence-sessions.sh:
# 提示符行由本脚本打印,命令与输出都是真实执行结果。
# 用法(Mac 上):cd /tmp && limactl shell cg-lab sudo bash -s -- <会话名> < 05-evidence-sessions.sh > logs/<会话名>.log
# 会话名:life | oomrace
# 运行环境:Lima 专用实验机 cg-lab(Ubuntu 26.04.1,内核 7.0.0-38,4 核 4G),root 身份;源码对照上游 v7.0
exec 2>&1
set -u
PROG="/Users/jin.xiao/workshop/deeparch-atlas/atlas-output/cgroup核心原理-20261112/stages/05-deep/src/prog"
cd /tmp; cp "$PROG"/* /tmp/
run() { printf '%s@%s:%s# %s\n' "$(whoami)" "$(hostname)" "$(pwd)" "$*"; eval "$*"; }
note() { printf '\n### %s\n' "$*"; }
SB=/sys/fs/cgroup/host01
HOME_CG=/sys/fs/cgroup$(sed -n 's/^0:://p' /proc/self/cgroup)
leave() {
  echo $$ > $HOME_CG/cgroup.procs 2>/dev/null
  pkill -INT bpftrace 2>/dev/null
  echo madvise > /sys/kernel/mm/transparent_hugepage/enabled
  [ -d $SB ] || return 0
  echo 1 > $SB/cgroup.kill 2>/dev/null; sleep 0.6
  find $SB -depth -type d -exec rmdir {} \; 2>/dev/null
  rm -f /tmp/ingroup /tmp/*.py /tmp/*.bt /tmp/*.out /tmp/oomrun.sh
}
trap leave EXIT
echo never > /sys/kernel/mm/transparent_hugepage/enabled
mkdir -p $SB; echo 2G > $SB/memory.max; echo "+cpu +memory +pids" > $SB/cgroup.subtree_control
case "${1:-}" in
life)
  mkdir -p $SB/report
  note "report 组:CPU 半颗核,内存 300M(透明大页已关,页数好数)"
  run "echo '50000 100000' > /sys/fs/cgroup/host01/report/cpu.max; echo 300M > /sys/fs/cgroup/host01/report/memory.max"
  run "bpftrace t13-life.bt > life.out 2>&1 &"
  for i in $(seq 1 40); do grep -q Attached life.out 2>/dev/null && break; sleep 0.25; done; sleep 0.3
  run "./ingroup report python3 life2.py"
  sleep 0.5; pkill -INT bpftrace; sleep 1
  run "grep -v -e Attached -e '^\$' life.out"
  ;;
oomrace)
  note "同一个组内 OOM 场景(两个 worker 先占 150M、80M,第三个慢慢吃到 100M;上限 300M)跑 4 轮(跟踪脚本也打印闸门挡住的时刻,和受害者被标成「退出中」的时刻)"
  run "./oomrun.sh 4 2>&1 | grep '==='"
  for r in 1 2 3 4; do note "第 $r 轮的跟踪"; LC_ALL=C.UTF-8 sed -n '/ us /p' /tmp/race$r.out | head -24; done
  ;;
*) echo "用法:bash -s -- life|oomrace"; exit 1;;
esac
