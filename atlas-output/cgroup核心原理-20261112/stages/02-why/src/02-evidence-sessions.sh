#!/usr/bin/env bash
# 留档用的「会话」脚本:把 02-why.md 里的每个实验按终端会话的样子跑一遍,
# 每条命令先打印提示符 + 命令原文,再真正执行,输出原样落到日志里。
# 提示符那一行是本脚本打印的(用户名 / 主机名 / 目录取自真实环境),命令与输出都是真实执行结果。
#
# 用法(Mac 上):limactl shell cg sudo bash -s -- <会话名> < 02-evidence-sessions.sh > logs/<会话名>.log
# 会话名:env | cpu0 | nice | taskset | setsid | ulimit | oom | same
#         | cgcpu | cgmem | cgescape | v1 | v2rule | cgweight | cgboth | cglow | cgmax | cgpids | cgio
# 运行环境:Lima 虚拟机 cg(Ubuntu 26.04.1,内核 7.0.0-38,4 核 8G),root 身份
#
# 安全边界:这台虚拟机上还跑着别的真服务(mysqld / clickhouse / redis),所以所有实验都关在
# 一个沙箱组 /sys/fs/cgroup/host01 里(内存上限 3G),把它当成文中的那台机器。
#   - 「没有 cgroup 的世界」= 沙箱里不再分组,所有进程挤在同一本账里(本脚本的 shell 自己也搬进去)
#   - 「有 cgroup 的世界」  = 沙箱里再分 db / report 两个子组(shell 留在外面)
# 结束时沙箱里的进程一次杀光、目录删掉,不碰沙箱外的任何进程。
exec 2>&1
set -u
cd /tmp
run() { printf '%s@%s:%s# %s\n' "$(whoami)" "$(hostname)" "$(pwd)" "$*"; eval "$*"; }
note() { printf '\n### %s\n' "$*"; }
SB=/sys/fs/cgroup/host01
HOME_CG=/sys/fs/cgroup$(sed -n 's/^0:://p' /proc/self/cgroup)

sandbox_flat()  { mkdir -p $SB; echo 3G > $SB/memory.max; echo $$ > $SB/cgroup.procs; }
sandbox_split() { mkdir -p $SB; echo 3G > $SB/memory.max
                  echo "+cpu +memory +pids" > $SB/cgroup.subtree_control; mkdir -p $SB/db $SB/report; }
leave() {
  echo $$ > $HOME_CG/cgroup.procs 2>/dev/null
  [ -d $SB ] || return 0
  echo 1 > $SB/cgroup.kill 2>/dev/null; sleep 0.6
  find $SB -depth -type d -exec rmdir {} \; 2>/dev/null
  rm -f /tmp/db.py /tmp/report.py /tmp/hold.py /tmp/vm.py /tmp/forkn.py /tmp/cpuof.py /tmp/ingroup /tmp/two_threads.py /tmp/memof /var/tmp/db.dat /var/tmp/rep.dat
}
trap leave EXIT

mk_programs() {
cat > /tmp/db.py <<'PY'
# 扮演 mysqld 的替身:4 个「连接」进程,各自不停地做查询;一次查询 = 一小段定量的纯计算
import os, time
CONN = 4            # 4 个连接
DUR = 8             # 跑 8 秒
K = 270000          # 一次查询 = 27 万次乘加,本机独占一颗核时约 5 ms

def setname(s):
    with open('/proc/self/comm', 'w') as f: f.write(s)

def cpu_by_name():  # 读 /proc/<pid>/stat:名字叫 db-sim / report-w 的进程各用了多少 CPU 时间
    out = {}
    for p in os.listdir('/proc'):
        if not p.isdigit(): continue
        try: s = open(f'/proc/{p}/stat').read()
        except OSError: continue
        name = s[s.index('(') + 1:s.rindex(')')]
        if name in ('db-sim', 'report-w'):
            f = s[s.rindex(')') + 2:].split()
            out[int(p)] = (name, int(f[11]) + int(f[12]))
    return out

def conn(w, end):
    setname('db-sim'); lat = []
    while True:
        t = time.monotonic()
        if t >= end: break
        x = 0
        for i in range(K): x += i * i
        lat.append(time.monotonic() - t)
    os.write(w, ' '.join(f'{v:.6f}' for v in lat).encode()); os._exit(0)

end = time.monotonic() + DUR; pipes = []
for _ in range(CONN):
    r, w = os.pipe()
    if os.fork() == 0:
        os.close(r); conn(w, end)
    os.close(w); pipes.append(r)
time.sleep(0.3); a = cpu_by_name(); ta = time.monotonic()
time.sleep(DUR - 0.8); b = cpu_by_name(); tb = time.monotonic()
lat = []
for r in pipes:
    buf = b''
    while True:
        c = os.read(r, 65536)
        if not c: break
        buf += c
    lat += [float(v) for v in buf.split()]
    os.wait()
lat.sort(); n = len(lat)
print(f"查询 {n} 次({n / DUR:.0f} 次/秒)  平均 {sum(lat) / n * 1000:.1f} ms  p99 {lat[int(n * 0.99)] * 1000:.1f} ms")
tot = {}; cnt = {}
for pid, (name, t1) in b.items():
    if pid in a:
        tot[name] = tot.get(name, 0) + (t1 - a[pid][1]); cnt[name] = cnt.get(name, 0) + 1
tick = os.sysconf('SC_CLK_TCK')
print("这段时间的 CPU:" + "   ".join(f"{k}×{cnt[k]} 合计 {tot[k] / tick / (tb - ta) * 100:.0f}%" for k in sorted(tot)))
PY
cat > /tmp/report.py <<'PY'
# 扮演报表任务:主进程 fork 出 N 个 worker
#   report.py cpu N [unpin]   每个 worker 死循环烧 CPU;带 unpin 时,1 秒后 worker 自己解除绑核
#   report.py mem N M         每个 worker 一点点吃到 M MiB 内存,然后睡着
import os, sys, time
mode, n = sys.argv[1], int(sys.argv[2])
extra = sys.argv[3] if len(sys.argv) > 3 else ''

def setname(s):
    with open('/proc/self/comm', 'w') as f: f.write(s)

for i in range(n):
    if os.fork() == 0:
        setname('report-w')
        if mode == 'cpu':
            t0 = time.monotonic(); done = extra != 'unpin'
            while True:
                for _ in range(200000): pass
                if not done and time.monotonic() - t0 > 1:
                    old = sorted(os.sched_getaffinity(0))
                    os.sched_setaffinity(0, range(os.cpu_count()))
                    if i == 0:
                        print(f"worker {os.getpid()}:sched_setaffinity 成功,允许的核从 {old} 变成 {sorted(os.sched_getaffinity(0))}", flush=True)
                    done = True
        else:
            hold = []
            try:
                for _ in range(int(extra) // 10):
                    hold.append(b'x' * (10 << 20)); time.sleep(0.2)      # 每 200 ms 再吃 10 MiB
            except MemoryError:
                print(f"worker {os.getpid()}:申请内存失败", flush=True)
            time.sleep(600)
        os._exit(0)
setname('report')
while True:
    try: os.wait()
    except ChildProcessError: break
PY
cat > /tmp/hold.py <<'PY'
# hold.py <名字> <M>:改名后占住 M MiB 内存不放(扮演 mysqld 的缓冲池)
import os, sys, time
name, m = sys.argv[1], int(sys.argv[2])
with open('/proc/self/comm', 'w') as f: f.write(name)
hold = [b'x' * (50 << 20) for _ in range(m // 50)]
print(f"{name}(pid {os.getpid()})已占住 {m} MiB", flush=True)
time.sleep(600)
PY
cat > /tmp/vm.py <<'PY'
import mmap
m = mmap.mmap(-1, 1 << 30)          # 向内核要 1 GiB 匿名内存,但一页都不去碰
rss = [l for l in open('/proc/self/status') if l.startswith('VmRSS')][0].split()[1]
print(f"映射 1 GiB 成功;此刻真正占住的物理内存 VmRSS = {int(rss) // 1024} MiB")
PY
cat > /tmp/forkn.py <<'PY'
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
cat > /tmp/cpuof.py <<'PY'
# cpuof.py <秒>:数这几秒里,名字叫 db-sim / report-w 的进程合计用了多少 CPU(读 /proc/<pid>/stat)
import os, sys, time
def snap():
    out = {}
    for p in os.listdir('/proc'):
        if not p.isdigit(): continue
        try: s = open(f'/proc/{p}/stat').read()
        except OSError: continue
        name = s[s.index('(') + 1:s.rindex(')')]
        if name in ('db-sim', 'report-w'):
            f = s[s.rindex(')') + 2:].split()
            out[int(p)] = (name, int(f[11]) + int(f[12]))
    return out
d = float(sys.argv[1]); a = snap(); time.sleep(d); b = snap(); tot = {}; cnt = {}
for pid, (name, t1) in b.items():
    if pid in a:
        tot[name] = tot.get(name, 0) + (t1 - a[pid][1]); cnt[name] = cnt.get(name, 0) + 1
tick = os.sysconf('SC_CLK_TCK')
print(f"{d:.0f} 秒内的 CPU:" + "   ".join(f"{k}×{cnt[k]} 合计 {tot[k] / tick / d * 100:.0f}%" for k in sorted(tot)))
PY
cat > /tmp/ingroup <<'SH'
#!/bin/sh
# 用法:ingroup <组名> <命令...>    先入组,后变身
echo $$ > /sys/fs/cgroup/host01/$1/cgroup.procs
shift
exec "$@"
SH
chmod +x /tmp/ingroup
cat > /tmp/two_threads.py <<'PY'
import os, threading, time
def side():
    print(f"副线程 tid = {threading.get_native_id()}", flush=True); time.sleep(120)
print(f"进程 pid = {os.getpid()}(主线程的 tid 也是它)", flush=True)
threading.Thread(target=side, daemon=True).start(); time.sleep(120)
PY
}
KLOG="journalctl -k --since $(date +%T) -o cat --no-pager"

case "${1:-}" in
env)
  note "这台虚拟机上还有别的真服务在跑,实验不能碰它们"
  run "ps -eo rss,comm --sort=-rss | head -4"
  run "free -m | head -2"
  note "圈一个沙箱组当作文中的那台机器:内存上限 3G,不限 CPU"
  run "mkdir /sys/fs/cgroup/host01"
  run "echo 3G > /sys/fs/cgroup/host01/memory.max"
  run "cat /sys/fs/cgroup/host01/memory.max"
  note "把当前 shell 搬进去;之后它起的所有进程都生在沙箱里"
  run "echo \$\$ > /sys/fs/cgroup/host01/cgroup.procs"
  run "cat /proc/self/cgroup"
  run "nproc"
  ;;
cpu0)
  mk_programs; sandbox_flat
  run "cat db.py | head -5"
  note "1. 只有 db-sim 在跑"
  run "python3 db.py"
  note "2. report 起 8 个 worker,db-sim 再跑一遍"
  run "python3 report.py cpu 8 &"
  sleep 1
  run "python3 db.py"
  ;;
nice)
  mk_programs; sandbox_flat
  note "1. report 降到最低优先级(nice 19),8 个 worker"
  run "nice -n 19 python3 report.py cpu 8 &"
  sleep 1
  run "python3 db.py"
  note "2. db-sim 没活的时候,nice 19 的 report 吃多少"
  run "python3 cpuof.py 3"
  run "pkill -f report.py"
  sleep 0.5
  note "3. 还是 nice 19,但 report 这次起 400 个 worker"
  run "nice -n 19 python3 report.py cpu 400 &"
  sleep 2
  run "python3 db.py"
  ;;
taskset)
  mk_programs; sandbox_flat
  note "1. 把 report 绑在 3 号核上(子进程会继承)"
  run "taskset -c 3 python3 report.py cpu 8 &"
  sleep 1
  run "python3 db.py"
  run "pkill -f report.py"
  sleep 0.5
  note "2. report 由普通用户 lima 来跑,worker 里多了一行 sched_setaffinity"
  run "runuser -u lima -- taskset -c 3 python3 report.py cpu 8 unpin &"
  sleep 2
  run "python3 db.py"
  ;;
setsid)
  sandbox_flat
  note "1. 一个作业:父 shell 带 3 个子进程,其中第 3 个调用了 setsid"
  run "setsid bash -c 'sleep 301 & sleep 302 & setsid sleep 303 & wait' &"
  sleep 1
  run "ps -o pid,ppid,pgid,sid,args -C sleep | grep -E 'PID|30[123]'"
  PG=$(ps -o pgid= -C sleep -o args= | awk '/301/ {print $1}')
  note "2. 按进程组把这个作业整个杀掉"
  run "kill -- -$PG"
  sleep 0.5
  run "ps -o pid,ppid,pgid,sid,args -C sleep | grep -E 'PID|30[123]'"
  ;;
ulimit)
  mk_programs; sandbox_flat
  note "1. 每个进程最多 512 MiB:单个进程要 600 MiB,被拒"
  run "bash -c 'ulimit -v 524288; python3 -c \"x = b\\\"x\\\" * (600 << 20)\"'"
  note "2. 同样的限制下,8 个 worker 每个要 300 MiB"
  run "bash -c 'ulimit -v 524288; python3 report.py mem 8 300' &"
  sleep 7.5
  run "ps -o pid,vsz,rss,comm -C report-w"
  run "ps -o rss= -C report-w | awk '{s += \$1} END {printf \"8 个 worker 合计占住 %d MiB\\n\", s / 1024}'"
  note "3. 它量的是地址空间,不是真占住的内存"
  run "cat vm.py"
  run "python3 vm.py"
  run "bash -c 'ulimit -v 524288; python3 vm.py' 2>&1 | tail -1"
  ;;
oom)
  mk_programs; sandbox_flat
  note "1. db-sim 先占住 1500 MiB(扮演 mysqld 的缓冲池);这台「机器」一共 3072 MiB"
  run "python3 hold.py db-sim 1500 &"
  DBP=$!; sleep 2.5
  note "2. report 起 8 个 worker,每个慢慢吃到 300 MiB(合计 2400 MiB)"
  run "python3 report.py mem 8 300 &"
  sleep 9
  note "3. 内核日志:谁触发的,谁被杀了"
  run "$KLOG | grep -E 'invoked oom-killer|oom-kill:|Killed process'"
  note "4. 活下来的"
  run "ps -o pid,rss,comm -C db-sim,report-w"
  run "wait $DBP; echo \"db-sim 的退出状态 = \$?(137 = 128 + 9,被 SIGKILL 杀死)\""
  ;;
same)
  mk_programs; sandbox_flat
  note "磁盘 IO:report 写一个 1 GiB 的临时文件(普通的带缓冲写),并且给它最低的 IO 优先级"
  run "grep ^Cached: /proc/meminfo"
  run "ionice -c 3 dd if=/dev/zero of=/var/tmp/report.tmp bs=1M count=1024 2>&1 | tail -1"
  run "grep ^Cached: /proc/meminfo"
  note "同样的写,但要求 dd 等数据真正落到盘上再返回"
  run "ionice -c 3 dd if=/dev/zero of=/var/tmp/report.tmp bs=1M count=1024 conv=fsync 2>&1 | tail -1"
  rm -f /var/tmp/report.tmp
  note "进程数:用 ulimit -u 限成 30。先看普通用户 lima 名下已经有多少个"
  run "ps -L -u lima --no-headers | wc -l"
  run "runuser -u lima -- bash -c 'ulimit -u 30; python3 forkn.py 100'"
  sleep 3.5
  note "同样的限制,换成 root(容器里的进程常常就是 root)"
  run "bash -c 'ulimit -u 30; python3 forkn.py 100'"
  sleep 3.5
  ;;
cgcpu)
  mk_programs; sandbox_split
  run "cat ingroup"
  note "1. host01 下面分两个组;report 这一组每 100 ms 合计最多 50 ms"
  run "ls -d /sys/fs/cgroup/host01/*/"
  run "echo '50000 100000' > /sys/fs/cgroup/host01/report/cpu.max"
  note "2. report 8 个 worker(不用 nice,不绑核)"
  run "./ingroup report python3 report.py cpu 8 &"
  disown -a; sleep 1
  run "./ingroup db python3 db.py"
  run "echo 1 > /sys/fs/cgroup/host01/report/cgroup.kill"
  sleep 0.5
  note "3. report 400 个 worker"
  run "./ingroup report python3 report.py cpu 400 &"
  disown -a; T0=$(date +%s)
  while [ "$(pgrep -c -x report-w)" -lt 400 ] && [ $(( $(date +%s) - T0 )) -lt 120 ]; do sleep 1; done
  run "pgrep -c -x report-w"
  run "./ingroup db python3 db.py"
  run "grep -E 'usage_usec|nr_periods|nr_throttled' /sys/fs/cgroup/host01/report/cpu.stat"
  ;;
cgmem)
  mk_programs; sandbox_split
  note "1. report 这一组合计最多 512 MiB"
  run "echo 512M > /sys/fs/cgroup/host01/report/memory.max"
  run "./ingroup db python3 hold.py db-sim 1500 &"
  sleep 2.5
  note "2. report 起 8 个 worker,每个要 300 MiB"
  run "./ingroup report python3 report.py mem 8 300 &"
  sleep 9
  note "3. 内核日志与两个组各自的账"
  run "$KLOG | grep 'Killed process' | cut -c1-64"
  run "$KLOG | grep 'oom-kill:' | head -1"
  run "grep oom_kill /sys/fs/cgroup/host01/report/memory.events /sys/fs/cgroup/host01/db/memory.events"
  run "cat /sys/fs/cgroup/host01/report/memory.current /sys/fs/cgroup/host01/db/memory.current"
  note "4. 活下来的"
  run "ps -o pid,rss,comm -C db-sim,report-w"
  ;;
cgescape)
  mk_programs; sandbox_split
  note "1. 同一个作业放进 report 组:setsid 换得了会话,换不了组"
  run "./ingroup report setsid bash -c 'sleep 301 & sleep 302 & setsid sleep 303 & wait' &"
  disown -a; sleep 1
  run "ps -o pid,pgid,sid,cgroup,args -C sleep | grep -E 'PID|30[123]'"
  note "2. 普通用户 lima 在 report 组里:想把自己挪去 db 组,想改自己组的上限"
  run "./ingroup report runuser -u lima -- bash -c 'echo \$\$ > /sys/fs/cgroup/host01/db/cgroup.procs'"
  run "./ingroup report runuser -u lima -- bash -c 'echo max > /sys/fs/cgroup/host01/report/cpu.max'"
  run "ls -l /sys/fs/cgroup/host01/report/cgroup.procs /sys/fs/cgroup/host01/report/cpu.max"
  note "3. 按组一次杀光,一个不漏"
  run "echo 1 > /sys/fs/cgroup/host01/report/cgroup.kill"
  sleep 0.5
  run "ps -o pid,args -C sleep | grep -c '30[123]'"
  ;;
v1)
  mk_programs
  cleanup_v1() {
    [ -n "${TP:-}" ] && kill $TP 2>/dev/null
    sleep 0.3
    for h in freezer net_cls; do
      [ -d /tmp/v1/$h ] || continue
      for p in $(cat /tmp/v1/$h/*/tasks 2>/dev/null); do echo $p > /tmp/v1/$h/tasks 2>/dev/null; done
      rmdir /tmp/v1/$h/*/ 2>/dev/null; sleep 0.5; umount /tmp/v1/$h 2>/dev/null; rmdir /tmp/v1/$h
    done
    rmdir /tmp/v1 2>/dev/null; sleep 1
    # 卸载后这棵 v1 树偶尔会残留(/proc/cgroups 里层级号不回 0):重新挂一次再卸掉即可
    for h in freezer net_cls; do
      if [ "$(awk -v h=$h '$1 == h {print $2}' /proc/cgroups)" != 0 ]; then
        mkdir -p /run/v1chk; mount -t cgroup -o $h none /run/v1chk && umount /run/v1chk; rmdir /run/v1chk
      fi
    done
  }
  trap 'cleanup_v1; leave' EXIT
  note "1. v1 的挂法:每种资源各挂一棵树(这里挂两棵还能用的:freezer 和 net_cls)"
  run "mkdir -p /tmp/v1/freezer /tmp/v1/net_cls"
  run "mount -t cgroup -o freezer none /tmp/v1/freezer"
  run "mount -t cgroup -o net_cls none /tmp/v1/net_cls"
  run "ls /tmp/v1/freezer"
  note "2. 两棵树各建各的组,同一个 shell 在两棵树上各占一个位置"
  run "mkdir /tmp/v1/freezer/A /tmp/v1/net_cls/X"
  run "echo \$\$ > /tmp/v1/freezer/A/cgroup.procs; echo \$\$ > /tmp/v1/net_cls/X/cgroup.procs"
  run "cat /proc/\$\$/cgroup"
  note "3. v1 允许把一个进程的两个线程拆到两个组"
  run "python3 two_threads.py &"
  TP=$!; sleep 1
  T2=$(ls /proc/$TP/task | grep -v "^$TP\$" | head -1)
  run "mkdir /tmp/v1/freezer/B; echo $T2 > /tmp/v1/freezer/B/tasks"
  run "grep -H freezer /proc/$TP/task/*/cgroup"
  note "4. 这台内核里,v1 的内存控制器和 cpuset 已经没有编进来"
  run "grep -E 'MEMCG_V1|CPUSETS_V1' /boot/config-\$(uname -r)"
  ;;
v2rule)
  mk_programs; sandbox_split
  trap 'kill ${TP:-} 2>/dev/null; leave' EXIT
  note "1. v2 只认进程:把副线程的 tid 写进 cgroup.procs,整个进程一起搬"
  run "python3 two_threads.py &"
  TP=$!; sleep 1
  T2=$(ls /proc/$TP/task | grep -v "^$TP\$" | head -1)
  run "echo $T2 > /sys/fs/cgroup/host01/report/cgroup.procs"
  run "grep -H . /proc/$TP/task/*/cgroup"
  note "2. v2 不许「组里有进程、同时又给子组分资源」"
  run "mkdir -p /sys/fs/cgroup/host01/db/sub"
  run "echo \$\$ > /sys/fs/cgroup/host01/db/cgroup.procs"
  run "echo +memory > /sys/fs/cgroup/host01/db/cgroup.subtree_control"
  note "把进程挪到叶子上,再开就可以了"
  run "echo \$\$ > /sys/fs/cgroup/host01/db/sub/cgroup.procs"
  run "echo +memory > /sys/fs/cgroup/host01/db/cgroup.subtree_control && echo 成功"
  note "反过来:已经给子组分资源的组,不再收进程"
  run "echo \$\$ > /sys/fs/cgroup/host01/db/cgroup.procs"
  ;;
cgweight)
  mk_programs; sandbox_split
  note "1. 只分组,不封顶:report 的 cpu.max 是默认值 max,两个组的权重都是默认的 100"
  run "cat /sys/fs/cgroup/host01/report/cpu.max"
  run "cat /sys/fs/cgroup/host01/db/cpu.weight /sys/fs/cgroup/host01/report/cpu.weight"
  note "2. report 400 个 worker,db-sim 4 个进程"
  run "./ingroup report python3 report.py cpu 400 &"
  disown -a; T0=$(date +%s)
  while [ "$(pgrep -c -x report-w)" -lt 400 ] && [ $(( $(date +%s) - T0 )) -lt 120 ]; do sleep 1; done
  run "pgrep -c -x report-w"
  run "./ingroup db python3 db.py &"
  sleep 2.5
  run "ps -o psr= -C db-sim | sort -n | xargs echo 第 2 秒,4 个 db-sim 所在的核:"
  sleep 3
  run "ps -o psr= -C db-sim | sort -n | xargs echo 第 5 秒,4 个 db-sim 所在的核:"
  wait %% 2>/dev/null; sleep 0.3
  note "3. 权重不变(100 比 100),这次手工把 4 个 db-sim 一个核放一个"
  run "./ingroup db python3 db.py &"
  sleep 0.5
  run 'i=0; for p in $(pgrep -x db-sim); do taskset -cp $i $p > /dev/null; i=$((i+1)); done'
  sleep 3
  run "ps -o psr= -C db-sim | sort -n | xargs echo 4 个 db-sim 所在的核:"
  wait %% 2>/dev/null; sleep 0.3
  note "4. 不钉核,把 db 组的权重调到 900(report 还是 100)"
  run "echo 900 > /sys/fs/cgroup/host01/db/cpu.weight"
  run "./ingroup db python3 db.py &"
  sleep 4
  run "ps -o psr= -C db-sim | sort -n | xargs echo 4 个 db-sim 所在的核:"
  wait %% 2>/dev/null; sleep 0.3
  note "5. db-sim 没活的时候,权重只有 100 的 report 吃多少"
  run "python3 cpuof.py 3"
  ;;
cgboth)
  mk_programs; sandbox_split
  note "1. 两个旋钮同时用:report 最多半颗核;抢的时候 db 比 report 是 900 比 100"
  run "echo '50000 100000' > /sys/fs/cgroup/host01/report/cpu.max"
  run "echo 900 > /sys/fs/cgroup/host01/db/cpu.weight"
  run "./ingroup report python3 report.py cpu 400 &"
  disown -a; T0=$(date +%s)
  while [ "$(pgrep -c -x report-w)" -lt 400 ] && [ $(( $(date +%s) - T0 )) -lt 180 ]; do sleep 1; done
  run "pgrep -c -x report-w"
  note "2. db 忙的时候"
  run "grep -E 'usage_usec|nr_periods|nr_throttled' /sys/fs/cgroup/host01/report/cpu.stat | xargs"
  run "./ingroup db python3 db.py &"
  sleep 4
  run "ps -o psr= -C db-sim | sort -n | xargs echo 4 个 db-sim 所在的核:"
  wait %% 2>/dev/null; sleep 0.2
  run "grep -E 'usage_usec|nr_periods|nr_throttled' /sys/fs/cgroup/host01/report/cpu.stat | xargs"
  note "3. db 闲的时候"
  run "python3 cpuof.py 3"
  run "grep -E 'usage_usec|nr_periods|nr_throttled' /sys/fs/cgroup/host01/report/cpu.stat | xargs"
  ;;
cglow)
  # 在专用虚拟机 cg-lab 上跑。沙箱 host01 这次只给 1G,两个组抢这 1G
  mk_programs
  cat > /tmp/memof <<'SH'
#!/bin/sh
# memof:两个组各自账上有多少内存,其中多少是文件页(页缓存)、多少是匿名页(程序自己申请的)
for g in db report; do
  d=/sys/fs/cgroup/host01/$g
  printf '%-7s 合计 %5d MiB   文件页 %5d MiB   匿名页 %5d MiB   memory.low %s\n' $g \
    $(( $(cat $d/memory.current) >> 20 )) \
    $(( $(awk '$1=="file"{print $2}' $d/memory.stat) >> 20 )) \
    $(( $(awk '$1=="anon"{print $2}' $d/memory.stat) >> 20 )) \
    "$(cat $d/memory.low)"
done
SH
  chmod +x /tmp/memof
  dd if=/dev/urandom of=/var/tmp/db.dat bs=1M count=700 status=none
  dd if=/dev/urandom of=/var/tmp/rep.dat bs=1M count=700 status=none
  sync; echo 1 > /proc/sys/vm/drop_caches
  sandbox_split; echo 1G > $SB/memory.max
  run "cat /sys/fs/cgroup/host01/memory.max"
  run "ls -l --block-size=M /var/tmp/db.dat /var/tmp/rep.dat | awk '{print \$5, \$9}'"
  note "1. 先试按比例:内存有没有 weight 这个旋钮"
  run "ls /sys/fs/cgroup/host01/db/ | grep -E '^(cpu|memory)\.(weight|max|high|low|min)$'"
  note "2. 不设保护:db 先把自己的 700M 数据文件读进页缓存,然后 report 也读 700M"
  run "./ingroup db cat /var/tmp/db.dat > /dev/null"
  run "./memof"
  run "./ingroup report cat /var/tmp/rep.dat > /dev/null"
  run "./memof"
  run "grep -H pgsteal /sys/fs/cgroup/host01/db/memory.stat | head -1"
  note "3. 清掉页缓存,给 db 组 memory.low = 700M,同样的顺序再来一遍"
  run "echo 1 > /proc/sys/vm/drop_caches"
  run "echo 700M > /sys/fs/cgroup/host01/db/memory.low"
  run "./ingroup db cat /var/tmp/db.dat > /dev/null"
  run "./memof"
  run "./ingroup report cat /var/tmp/rep.dat > /dev/null"
  run "./memof"
  run "grep -E '^low ' /sys/fs/cgroup/host01/db/memory.events"
  note "4. 换成程序自己申请的内存(匿名页,这台机器没有 swap):db 占 700M,report 要 600M"
  run "echo 1 > /proc/sys/vm/drop_caches"
  run "./ingroup db python3 hold.py db-sim 700 &"
  sleep 3
  run "./ingroup report python3 hold.py report-w 600 &"
  sleep 4
  run "./memof"
  run "$KLOG | grep -E 'oom-kill:|Killed process' | cut -c1-150"
  run "ps -o pid,rss,comm -C db-sim,report-w"
  ;;
cgmax)
  # 在专用虚拟机 cg-lab 上跑。接 cglow 第 4 步:同样的匿名页场景,再给 report 组加 memory.max 300M
  mk_programs
  sandbox_split; echo 1G > $SB/memory.max
  run "cat /sys/fs/cgroup/host01/memory.max"
  run "echo 700M > /sys/fs/cgroup/host01/db/memory.low"
  run "echo 300M > /sys/fs/cgroup/host01/report/memory.max"
  run "./ingroup db python3 hold.py db-sim 700 &"
  sleep 3
  run "./ingroup report python3 hold.py report-w 600 &"
  sleep 4
  run "$KLOG | grep -E 'oom-kill:|Killed process' | cut -c1-150"
  run "grep -H oom_kill /sys/fs/cgroup/host01/memory.events /sys/fs/cgroup/host01/db/memory.events /sys/fs/cgroup/host01/report/memory.events"
  run "grep -H -E '^(oom_kill|max) ' /sys/fs/cgroup/host01/report/memory.events.local /sys/fs/cgroup/host01/memory.events.local"
  run "ps -o pid,rss,comm -C db-sim,report-w"
  ;;
cgpids)
  # 在专用虚拟机 cg-lab 上跑。接 §6.2:同一个 fork 测试,这次用组来管
  mk_programs; sandbox_split
  note "1. report 组最多 20 个进程;以 root 身份在组里连续 fork 100 个子进程"
  run "echo 20 > /sys/fs/cgroup/host01/report/pids.max"
  run "./ingroup report python3 forkn.py 100"
  note "2. 组的账"
  run "grep -H . /sys/fs/cgroup/host01/report/pids.max /sys/fs/cgroup/host01/report/pids.peak /sys/fs/cgroup/host01/report/pids.events"
  note "3. 对照:同一时刻 db 组不受影响"
  run "./ingroup db python3 forkn.py 100"
  ;;
cgio)
  # 在专用虚拟机 cg-lab 上跑。接 §6.1:同样的 dd,这次用组来管
  mk_programs; sandbox_split
  echo "+io" > $SB/cgroup.subtree_control
  run "lsblk -o NAME,MAJ:MIN,TYPE,MOUNTPOINT | grep -E 'NAME|vda |vda1'"
  note "1. 不设限:在 report 组里写 50 MiB(绕过页缓存,直接写盘)"
  run "./ingroup report dd if=/dev/zero of=/var/tmp/r1.tmp bs=1M count=50 oflag=direct 2>&1 | tail -1"
  run "cat /sys/fs/cgroup/host01/report/io.stat"
  note "2. report 组在这块盘上每秒最多写 10 MiB"
  run "echo '253:0 wbps=10485760' > /sys/fs/cgroup/host01/report/io.max"
  run "./ingroup report dd if=/dev/zero of=/var/tmp/r2.tmp bs=1M count=50 oflag=direct 2>&1 | tail -1"
  run "cat /sys/fs/cgroup/host01/report/io.stat"
  note "3. 同样的限制,换成带缓冲的写(先进页缓存,由内核线程写盘),等落盘再返回"
  run "./ingroup report dd if=/dev/zero of=/var/tmp/r3.tmp bs=1M count=50 conv=fsync 2>&1 | tail -1"
  run "cat /sys/fs/cgroup/host01/report/io.stat"
  note "4. 对照:db 组没有设限,同样带缓冲地写 50 MiB"
  run "./ingroup db dd if=/dev/zero of=/var/tmp/d1.tmp bs=1M count=50 conv=fsync 2>&1 | tail -1"
  run "cat /sys/fs/cgroup/host01/db/io.stat"
  rm -f /var/tmp/r1.tmp /var/tmp/r2.tmp /var/tmp/r3.tmp /var/tmp/d1.tmp
  ;;
*) echo "用法:bash -s -- env|cpu0|nice|taskset|setsid|ulimit|oom|same|cgcpu|cgmem|cgescape|v1|v2rule|cgweight|cgboth|cglow|cgmax|cgpids|cgio"; exit 1;;
esac
