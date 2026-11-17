#!/usr/bin/env bash
# 留档用的「会话」脚本:把 03-how.md 里的每个实验按终端会话的样子跑一遍,
# 每条命令先打印提示符 + 命令原文,再真正执行,输出原样落到日志里。
# 提示符那一行是本脚本打印的(用户名 / 主机名 / 目录取自真实环境),命令与输出都是真实执行结果。
#
# 用法(Mac 上):cd /tmp && limactl shell cg-lab sudo bash -s -- <会话名> < 03-evidence-sessions.sh > logs/<会话名>.log
# 会话名:t0 | t1 | t3 | t3n | t2 | t4 | tree | fw | pids | life | hooks | free | table | cost | wb | exit
# 运行环境:Lima 专用实验机 cg-lab(Ubuntu 26.04.1,内核 7.0.0-38,4 核 4G),root 身份,只跑本文的实验
# 小程序与跟踪脚本在 prog/ 目录,实验机通过只读挂载直接读到这个目录,开跑前拷到 /tmp
exec 2>&1
set -u
PROG="/Users/jin.xiao/workshop/deeparch-atlas/atlas-output/cgroup核心原理-20261112/stages/03-how/src/prog"
cd /tmp; cp "$PROG"/* /tmp/
run() { printf '%s@%s:%s# %s\n' "$(whoami)" "$(hostname)" "$(pwd)" "$*"; eval "$*"; }
note() { printf '\n### %s\n' "$*"; }
SB=/sys/fs/cgroup/host01
HOME_CG=/sys/fs/cgroup$(sed -n 's/^0:://p' /proc/self/cgroup)
sandbox() { mkdir -p $SB; echo 2G > $SB/memory.max
            echo "+cpu +memory +pids" > $SB/cgroup.subtree_control; mkdir -p $SB/db $SB/report; }
leave() {
  echo $$ > $HOME_CG/cgroup.procs 2>/dev/null
  pkill -INT bpftrace 2>/dev/null
  echo madvise > /sys/kernel/mm/transparent_hugepage/enabled
  [ -d $SB ] || return 0
  echo 1 > $SB/cgroup.kill 2>/dev/null; sleep 0.6
  find $SB -depth -type d -exec rmdir {} \; 2>/dev/null
  rm -f /tmp/ingroup /tmp/*.py /tmp/*.bt /tmp/*.out /tmp/load.sh /var/tmp/rep.dat /var/tmp/wb.dat /var/tmp/c1.tmp /var/tmp/c2.tmp
}
trap leave EXIT
bt_bg() {   # 后台起一个跟踪脚本,等它挂好探针
  run "bpftrace $1 > $2 2>&1 &"
  for i in $(seq 1 40); do grep -q Attached $2 2>/dev/null && break; sleep 0.25; done; sleep 0.3
}
bt_stop() { pkill -INT bpftrace; sleep 1; }
wait_workers() { T0=$(date +%s); while [ "$(pgrep -c -x report-w)" -lt $1 ] && [ $(( $(date +%s) - T0 )) -lt 120 ]; do sleep 0.5; done; }

case "${1:-}" in
t0)
  sandbox
  run "cat ingroup"
  note "1. 先挂上跟踪脚本,再让 report 入组并 fork 出 3 个 worker"
  bt_bg t0-fork.bt t0.out
  run "./ingroup report python3 report.py 3 0.2 &"
  disown -a; sleep 1.5; bt_stop
  run "grep -v -e Attached -e '^\$' t0.out"
  note "2. 四个进程各自的组籍(从 /proc 看)"
  run "for p in \$(pgrep -x 'report|report-w'); do echo \"\$p \$(cat /proc/\$p/cgroup)\"; done"
  ;;
t1)
  sandbox
  note "1. report 组限半颗核,8 个 worker"
  run "echo '50000 100000' > /sys/fs/cgroup/host01/report/cpu.max"
  run "./ingroup report python3 report.py 8 &"
  disown -a; wait_workers 8; sleep 1.5
  note "2. 数 2 秒:记了多少笔账,其中多少笔动了公共额度池"
  run "grep usage_usec /sys/fs/cgroup/host01/report/cpu.stat"
  run "bpftrace t1-cpuacct.bt | grep ."
  run "grep usage_usec /sys/fs/cgroup/host01/report/cpu.stat"
  ;;
t3)
  sandbox
  note "0. report 组限半颗核,这次起 7 个 worker(4 颗核,必有一颗核上只有 1 个)"
  run "echo '50000 100000' > /sys/fs/cgroup/host01/report/cpu.max"
  run "./ingroup report python3 report.py 7 &"
  disown -a; wait_workers 7; sleep 1.5
  note "1. 3 秒里,7 个 worker 各自拿到多少 CPU、待在哪颗核上"
  run "python3 percpu.py 3"
  note "2. 两个周期的时间线(毫秒)"
  run "bpftrace t3-throttle.bt | grep ."
  ;;
t3n)
  sandbox
  note "1. 8 个 worker,限半颗核"
  run "echo '50000 100000' > /sys/fs/cgroup/host01/report/cpu.max"
  run "./ingroup report python3 report.py 8 &"
  disown -a; wait_workers 8; sleep 1.5
  run "bpftrace t3-count.bt | grep ."
  run "echo 1 > /sys/fs/cgroup/host01/report/cgroup.kill"
  sleep 0.6
  note "2. 400 个 worker(先不设限把进程起齐,再写上限),限半颗核"
  run "echo max > /sys/fs/cgroup/host01/report/cpu.max"
  run "./ingroup report python3 report.py 400 &"
  disown -a; wait_workers 400
  run "pgrep -c -x report-w"
  run "echo '50000 100000' > /sys/fs/cgroup/host01/report/cpu.max"
  sleep 1.5
  run "bpftrace t3-count.bt | grep ."
  ;;
t2)
  sandbox
  echo never > /sys/kernel/mm/transparent_hugepage/enabled
  note "0. 为了让页数好数,先关掉透明大页(否则一次缺页可能直接给 512 页)"
  run "cat /sys/kernel/mm/transparent_hugepage/enabled"
  note "1. report 组内存上限 300M;挂上跟踪脚本,让一个 worker 吃 100 MiB"
  run "echo 300M > /sys/fs/cgroup/host01/report/memory.max"
  bt_bg t2-memacct.bt t2.out
  run "./ingroup report python3 hold.py report-w 100 &"
  disown -a; sleep 2.5; bt_stop
  run "grep -v -e Attached -e '^\$' t2.out"
  note "2. 组的账(字节)"
  run "cat /sys/fs/cgroup/host01/report/memory.current /sys/fs/cgroup/host01/memory.current"
  note "3. 抽查这个 worker 的内存页:每一页记在谁头上"
  run "python3 pageowner.py \$(pgrep -x report-w) /sys/fs/cgroup/host01/report"
  ;;
t4)
  sandbox
  echo never > /sys/kernel/mm/transparent_hugepage/enabled
  dd if=/dev/urandom of=/var/tmp/rep.dat bs=1M count=600 status=none; sync; echo 1 > /proc/sys/vm/drop_caches
  run "echo 300M > /sys/fs/cgroup/host01/report/memory.max"
  note "A. 收得回来的内存:在 300M 的组里读一个 600M 的文件(页缓存)"
  bt_bg t4-oom.bt t4a.out
  run "./ingroup report cat /var/tmp/rep.dat > /dev/null"
  sleep 0.5; bt_stop
  run "grep -v -e Attached -e '^\$' t4a.out"
  run "grep -E '^(max|oom|oom_kill) ' /sys/fs/cgroup/host01/report/memory.events | xargs"
  echo 1 > /proc/sys/vm/drop_caches
  note "B. 收不回来的内存(匿名页,没有 swap):两个 worker 先占 150M 和 80M,第三个慢慢吃到 100M"
  bt_bg t4-oom.bt t4b.out
  run "./ingroup report python3 hold.py report-w 150 &"
  run "./ingroup report python3 hold.py report-w 80 &"
  sleep 2
  run "./ingroup report python3 hold.py report-w 100 10 0.1 &"
  disown -a; sleep 3.5; bt_stop
  run "grep -v -e Attached -e '^\$' t4b.out"
  run "ps -o pid,rss,comm -C report-w"
  run "grep -E '^(max|oom|oom_kill) ' /sys/fs/cgroup/host01/report/memory.events | xargs"
  ;;
tree)
  sandbox
  note "1. report 自己的上限是半颗核;父组 host01 先不设限"
  run "echo '50000 100000' > /sys/fs/cgroup/host01/report/cpu.max"
  run "cat /sys/fs/cgroup/host01/cpu.max"
  run "./ingroup report python3 report.py 8 &"
  disown -a; wait_workers 8; sleep 1.5
  run "python3 percpu.py 2 | tail -1"
  note "2. 给父组 host01 写一个更紧的上限:0.3 颗核。report 自己的 cpu.max 一个字没动"
  run "echo '30000 100000' > /sys/fs/cgroup/host01/cpu.max"
  sleep 0.5
  run "grep -H nr_throttled /sys/fs/cgroup/host01/cpu.stat /sys/fs/cgroup/host01/report/cpu.stat"
  run "python3 percpu.py 2 | tail -1"
  run "grep -H nr_throttled /sys/fs/cgroup/host01/cpu.stat /sys/fs/cgroup/host01/report/cpu.stat"
  ;;
fw)
  note "0. 这个内核认识哪些控制器;根组往下开了哪些"
  run "cat /sys/fs/cgroup/cgroup.controllers"
  run "cat /sys/fs/cgroup/cgroup.subtree_control"
  note "1. 建 host01 和它的子组 demo;host01 先不往下开任何控制器。数一数 demo 目录里各种前缀的文件"
  run "mkdir -p /sys/fs/cgroup/host01/demo"
  run "ls /sys/fs/cgroup/host01/demo | cut -d. -f1 | sort | uniq -c | xargs"
  bt_bg t5-framework.bt t5.out
  run "./ingroup demo python3 ticker.py &"
  disown -a; sleep 1.2
  note "2. 在 host01 上往下开 pids 控制器"
  run "echo '+pids' > /sys/fs/cgroup/host01/cgroup.subtree_control"
  run "ls /sys/fs/cgroup/host01/demo | cut -d. -f1 | sort | uniq -c | xargs"
  sleep 1.2
  note "3. 再开 cpu、memory、io"
  run "echo '+cpu +memory +io' > /sys/fs/cgroup/host01/cgroup.subtree_control"
  run "ls /sys/fs/cgroup/host01/demo | cut -d. -f1 | sort | uniq -c | xargs"
  sleep 1.2
  note "4. 再搬一个进程进 demo"
  run "./ingroup demo sleep 30 &"
  disown -a; sleep 0.6; bt_stop
  note "5. 这期间跟踪脚本看到的"
  run "grep -v -e Attached -e '^\$' t5.out"
  ;;
pids)
  sandbox
  note "1. report 组最多 20 个进程;在组里连续 fork 100 个"
  run "echo 20 > /sys/fs/cgroup/host01/report/pids.max"
  bt_bg t6-pids.bt t6.out
  run "./ingroup report python3 forkn.py 100"
  sleep 0.5; bt_stop
  run "grep -v -e Attached -e '^\$' t6.out"
  run "grep -H . /sys/fs/cgroup/host01/report/pids.peak /sys/fs/cgroup/host01/report/pids.events"
  ;;
life)
  sandbox; echo "+io" > $SB/cgroup.subtree_control
  note "1. report 组四种资源各写一个上限"
  run "echo '50000 100000' > /sys/fs/cgroup/host01/report/cpu.max"
  run "echo 300M > /sys/fs/cgroup/host01/report/memory.max"
  run "echo '253:0 wbps=10485760' > /sys/fs/cgroup/host01/report/io.max"
  run "echo 20 > /sys/fs/cgroup/host01/report/pids.max"
  note "2. 挂上跟踪脚本,让 report 生出一个 worker:烧 CPU → 要内存 → 写盘 → 生一个孩子 → 退出"
  bt_bg "t7-life.bt 0" life.out
  run "./ingroup report python3 life.py"
  sleep 0.5; bt_stop
  run "grep -v -e Attached -e '^\$' life.out"
  rm -f /var/tmp/worker.dat
  ;;
hooks)
  sandbox; echo "+io" > $SB/cgroup.subtree_control
  echo '50000 100000' > $SB/report/cpu.max; echo 300M > $SB/report/memory.max
  echo '253:0 wbps=10485760' > $SB/report/io.max; echo 20 > $SB/report/pids.max
  note "同一个 worker 再走一遍,这次每到一个接入点,打印当时的内核调用栈(从下往上读:谁调用了谁)"
  bt_bg "t7-life.bt 1" hooks.out
  run "./ingroup report python3 life.py"
  sleep 0.5; bt_stop
  run "grep -v -e Attached -e bpf_ -e '^\$' hooks.out | sed -E 's/^\\t[0-9a-f]+ ([^+]+)\\+[0-9]+\$/             \\1/'"
  rm -f /var/tmp/worker.dat
  ;;
free)
  sandbox
  cat > /tmp/spin.py <<'PY'
import os, time
with open('/proc/self/comm', 'w') as f: f.write('spin')
while True: pass
PY
  note "1. 两个组里各有一个死循环,谁都没写 cpu.max"
  run "cat /sys/fs/cgroup/host01/db/cpu.max /sys/fs/cgroup/host01/report/cpu.max"
  run "./ingroup db python3 spin.py &"
  run "./ingroup report python3 spin.py &"
  disown -a; sleep 1
  run "bpftrace t8-free.bt | grep ."
  note "2. 只给 report 写一个上限,db 不动"
  run "echo '50000 100000' > /sys/fs/cgroup/host01/report/cpu.max"
  sleep 1
  run "bpftrace t8-free.bt | grep ."
  ;;
table)
  note "五个控制器各自向核心登记了哪些回调(从内核符号表里按名字筛)"
  run "grep -oE '^(pids|cpu_cgroup|mem_cgroup|blkcg|cpuset)_(css_alloc|css_online|css_free|can_attach|attach|can_fork|fork|exit|release)\\b' /sys/kernel/tracing/available_filter_functions | sort | column -c 132 | expand"
  ;;
cost)
  sandbox; echo "+io" > $SB/cgroup.subtree_control
  cat > /tmp/spin.py <<'PY'
import os, time
with open('/proc/self/comm', 'w') as f: f.write('spin')
while True: pass
PY
  cat > /tmp/load.sh <<'SH'
#!/bin/sh
# load.sh:db 组、report 组、根组里各有一个进程吃 40 MiB 内存;db 组和 report 组各直接写 20 MiB 到盘
./ingroup db python3 eat.py 40
./ingroup report python3 eat.py 40
sh -c 'echo $$ > /sys/fs/cgroup/cgroup.procs; exec python3 eat.py 40'
./ingroup db dd if=/dev/zero of=/var/tmp/c1.tmp bs=1M count=20 oflag=direct status=none
./ingroup report dd if=/dev/zero of=/var/tmp/c2.tmp bs=1M count=20 oflag=direct status=none
SH
  chmod +x /tmp/load.sh
  run "cat load.sh"
  note "1. 两个组什么上限都没写"
  run "cd /sys/fs/cgroup/host01 && grep -H . db/cpu.max db/memory.max report/cpu.max report/memory.max; cat db/io.max report/io.max; cd /tmp"
  ./ingroup db python3 spin.py & ./ingroup report python3 spin.py &
  disown -a; sleep 0.5
  bt_bg t9-cost.bt cost1.out
  run "./load.sh"
  sleep 4.5
  run "grep -v -e Attached -e '^\$' cost1.out"
  note "2. 只给 report 写上三个上限,db 还是什么都不写"
  run "echo '50000 100000' > /sys/fs/cgroup/host01/report/cpu.max"
  run "echo 300M > /sys/fs/cgroup/host01/report/memory.max"
  run "echo '253:0 wbps=104857600' > /sys/fs/cgroup/host01/report/io.max"
  sleep 0.5
  bt_bg t9-cost.bt cost2.out
  run "./load.sh"
  sleep 4.5
  run "grep -v -e Attached -e '^\$' cost2.out"
  rm -f /var/tmp/c1.tmp /var/tmp/c2.tmp /tmp/load.sh
  ;;
wb)
  sandbox; echo "+io" > $SB/cgroup.subtree_control
  rm -f /var/tmp/wb.dat
  note "1. report 组限每秒写 10 MiB。组里的一个进程带缓冲地写 30 MiB:不 fsync,也不关文件"
  run "echo '253:0 wbps=10485760' > /sys/fs/cgroup/host01/report/io.max"
  bt_bg t10-wb.bt wb1.out
  run "./ingroup report python3 bufwrite.py 30 &"
  disown -a; sleep 1
  run "cat /sys/fs/cgroup/host01/report/io.stat; grep -E '^file_dirty' /sys/fs/cgroup/host01/report/memory.stat"
  note "2. 在组外(本终端的 shell 不在 report 组里)催内核把脏页写到盘上,看要多久"
  run "cat /proc/self/cgroup; time sync"
  run "cat /sys/fs/cgroup/host01/report/io.stat; grep -E '^file_dirty' /sys/fs/cgroup/host01/report/memory.stat"
  bt_stop
  run "grep -v -e Attached -e bpf_ -e '^\$' wb1.out | sed -E 's/^\\t[0-9a-f]+ ([^+]+)\\+[0-9]+\$/             \\1/'"
  echo 1 > $SB/report/cgroup.kill; sleep 0.5; rm -f /var/tmp/wb.dat
  note "3. 对照:去掉上限,同样的事再做一遍"
  run "echo '253:0 wbps=max' > /sys/fs/cgroup/host01/report/io.max"
  bt_bg t10-wb.bt wb2.out
  run "./ingroup report python3 bufwrite.py 30 &"
  disown -a; sleep 1
  run "time sync"
  bt_stop
  run "grep -v -e Attached -e '^\$' wb2.out"
  rm -f /var/tmp/wb.dat
  ;;
exit)
  sandbox
  echo never > /sys/kernel/mm/transparent_hugepage/enabled
  run "cat exit.py"
  bt_bg t11-exit.bt exit.out
  run "./ingroup report python3 exit.py &"
  disown -a; sleep 0.35
  note "worker 活着(第 0.3 秒)"
  run "ps -o pid,stat,rss,comm -C worker,report; cd /sys/fs/cgroup/host01/report; grep -H . memory.current pids.current; cd /tmp"
  sleep 0.75
  note "worker 已退出,主进程还没收尸(第 1.1 秒)"
  run "ps -o pid,stat,rss,comm -C worker,report; cd /sys/fs/cgroup/host01/report; grep -H . memory.current pids.current; cd /tmp"
  sleep 0.9
  note "主进程收尸之后(第 2.0 秒)"
  run "ps -o pid,stat,rss,comm -C worker,report; cd /sys/fs/cgroup/host01/report; grep -H . memory.current pids.current; cd /tmp"
  sleep 0.6; bt_stop
  note "跟踪脚本看到的"
  run "grep -v -e Attached -e '^\$' exit.out"
  ;;
*) echo "用法:bash -s -- t0|t1|t3|t3n|t2|t4|tree|fw|pids|life|hooks|free|table|cost|wb|exit"; exit 1;;
esac
