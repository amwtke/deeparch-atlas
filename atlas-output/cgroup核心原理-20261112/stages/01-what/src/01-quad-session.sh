#!/usr/bin/env bash
# 留档用的「会话」脚本(后补的一段):一个组的目录、四个文件、四种资源。
# 约定同 01-evidence-sessions.sh:提示符行由本脚本打印,命令与输出都是真实执行结果。
#
# 用法(Mac 上):cd /tmp && limactl shell cg-lab sudo bash -s < 01-quad-session.sh > logs/quad.log
# 运行环境:Lima 专用实验机 cg-lab(Ubuntu 26.04.1,内核 7.0.0-38,4 核 4G),root 身份
exec 2>&1
set -u
cd /tmp
run() { printf '%s@%s:%s# %s\n' "$(whoami)" "$(hostname)" "$(pwd)" "$*"; eval "$*"; }
note() { printf '\n### %s\n' "$*"; }
SB=/sys/fs/cgroup/host01
HOME_CG=/sys/fs/cgroup$(sed -n 's/^0:://p' /proc/self/cgroup)
leave() {
  echo $$ > $HOME_CG/cgroup.procs 2>/dev/null
  [ -d $SB ] || return 0
  echo 1 > $SB/cgroup.kill 2>/dev/null; sleep 0.6
  find $SB -depth -type d -exec rmdir {} \; 2>/dev/null
  rm -f /tmp/ingroup /tmp/burn.py /tmp/eat.py /tmp/forkn.py /var/tmp/report.tmp
}
trap leave EXIT
cat > /tmp/ingroup <<'SH'
#!/bin/sh
# 用法:ingroup <组名> <命令...>    先入组,后变身
echo $$ > /sys/fs/cgroup/host01/$1/cgroup.procs
shift
exec "$@"
SH
chmod +x /tmp/ingroup
cat > /tmp/burn.py <<'PY'
# burn.py <N>:fork 出 N 个死循环,烧 CPU
import os, sys
for _ in range(int(sys.argv[1])):
    if os.fork() == 0:
        while True: pass
os.wait()
PY
cat > /tmp/eat.py <<'PY'
# eat.py <M>:每 0.05 秒吃 10 MiB,一直吃到 M MiB
import sys, time
hold = []
for i in range(int(sys.argv[1]) // 10):
    hold.append(b'x' * (10 << 20)); time.sleep(0.05)
print(f"吃到了 {sys.argv[1]} MiB", flush=True)
PY
cat > /tmp/forkn.py <<'PY'
# forkn.py <N>:连续 fork N 个子进程(每个睡 3 秒),数成功了几个
import os, sys, time
n = int(sys.argv[1]); ok = 0
for i in range(n):
    try:
        if os.fork() == 0:
            time.sleep(3); os._exit(0)
        ok += 1
    except OSError as e:
        print(f"第 {ok + 1} 次 fork 失败:{e}"); break
print(f"想要 {n} 个子进程,成功 fork 出 {ok} 个")
PY
mkdir -p $SB; echo "+cpu +memory +io +pids" > $SB/cgroup.subtree_control; mkdir -p $SB/report $SB/db

note "0. 这个内核能管哪些种类的资源(每一种由一个「控制器」负责)"
run "cat /sys/fs/cgroup/cgroup.controllers"
note "1. 一个组就是一个目录。四种资源的上限,是目录里的四个文件"
run "ls /sys/fs/cgroup/host01/report | grep -E '^(cpu|memory|io|pids)\.max\$'"
run "cd /sys/fs/cgroup/host01/report && grep -H . cpu.max memory.max pids.max; cd /tmp"
note "2. 往四个文件里各写一个数"
run "echo '50000 100000'         > /sys/fs/cgroup/host01/report/cpu.max      # CPU:每 100 ms 合计最多 50 ms"
run "echo 300M                   > /sys/fs/cgroup/host01/report/memory.max   # 内存:合计最多 300 MiB"
run "echo '253:0 wbps=10485760'  > /sys/fs/cgroup/host01/report/io.max       # 磁盘:这块盘每秒最多写 10 MiB"
run "echo 20                     > /sys/fs/cgroup/host01/report/pids.max     # 进程数:最多 20 个"
note "3. 抢 CPU:8 个死循环。看组的 CPU 账 2 秒里涨了多少"
run "./ingroup report python3 burn.py 8 &"
disown -a; sleep 1.5
run "grep usage_usec /sys/fs/cgroup/host01/report/cpu.stat; sleep 2; grep usage_usec /sys/fs/cgroup/host01/report/cpu.stat"
echo 1 > $SB/report/cgroup.kill; sleep 0.6
note "4. 吃内存:一个进程想吃 400 MiB"
run "./ingroup report python3 eat.py 400; echo 退出状态 = \$?"
run "grep oom_kill /sys/fs/cgroup/host01/report/memory.events"
note "5. 狂写盘:写 30 MiB"
run "./ingroup report dd if=/dev/zero of=/var/tmp/report.tmp bs=1M count=30 oflag=direct 2>&1 | tail -1"
note "6. 狂生进程:想 fork 100 个"
run "./ingroup report python3 forkn.py 100"
note "7. 旁边的 db 组什么数都没写,同样的事不受影响"
run "./ingroup db dd if=/dev/zero of=/var/tmp/report.tmp bs=1M count=30 oflag=direct 2>&1 | tail -1"
run "./ingroup db python3 forkn.py 100"
