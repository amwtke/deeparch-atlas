#!/usr/bin/env bash
# 留档用的「会话」脚本:把 01-what.md 里的每个实验按终端会话的样子重跑一遍,
# 每条命令先打印提示符 + 命令原文,再真正执行,输出原样落到日志里。
# 提示符那一行是本脚本打印的(用户名 / 主机名 / 目录取自真实环境),命令与输出都是真实执行结果。
#
# 用法(Mac 上):limactl shell cg sudo bash -s -- <会话名> < 01-evidence-sessions.sh > logs/<会话名>.log
# 会话名:env | systemd | join | half1 | probe | four | duty
# 运行环境:Lima 虚拟机 cg(Ubuntu 26.04.1,内核 7.0.0-38,4 核 8G),root 身份
exec 2>&1
set -u
cd /tmp
run() { printf '%s@%s:%s# %s\n' "$(whoami)" "$(hostname)" "$(pwd)" "$*"; eval "$*"; }
note() { printf '\n### %s\n' "$*"; }
N=111111111          # 约 2 秒 CPU 的工作量(本机校准值)
NS=27777777          # 约 0.5 秒 CPU 的工作量
H=/sys/fs/cgroup/half
IN='bash -c '"'"'echo $$ > /sys/fs/cgroup/half/cgroup.procs; exec "$@"'"'"' _'

mk_programs() {
cat > /tmp/work.py <<'PY'
import sys, time
def burn(n):                      # 纯计算:做 n 次乘加
    x = 0
    for i in range(n):
        x += i * i
    return x
t0 = time.monotonic(); c0 = time.process_time()
burn(int(sys.argv[1]))
t1 = time.monotonic(); c1 = time.process_time()
print(f"墙上时间={t1-t0:.2f}s  CPU时间={c1-c0:.2f}s", flush=True)
PY
cat > /tmp/gaps.py <<'PY'
import sys, time
dur = float(sys.argv[1]); thr = 0.002      # 相邻两次读时钟相差超过 2 ms = 刚才被拿下核了
t0 = time.monotonic(); last = t0; seg = t0; segs = []
while True:
    now = time.monotonic()
    if now - last > thr:
        segs.append((seg - t0, last - t0, now - last)); seg = now
    last = now
    if now - t0 > dur:
        break
if not segs:
    print(f"{dur*1000:.0f} ms 内没有出现超过 2 ms 的停顿")
for a, b, g in segs[:6]:
    print(f"跑 {a*1000:6.1f} → {b*1000:6.1f} ms(连续 {(b-a)*1000:5.1f} ms),然后停 {g*1000:5.1f} ms")
PY
}
STAT="grep -E 'usage_usec|nr_periods|nr_throttled|throttled_usec'"

case "${1:-}" in
env)
  run "uname -sr"
  run "grep PRETTY_NAME /etc/os-release"
  run "nproc"
  run "free -h | head -2"
  run "stat -fc %T /sys/fs/cgroup"
  run "cat /sys/fs/cgroup/cgroup.controllers"
  run "cat /sys/fs/cgroup/cgroup.subtree_control"
  run "cat /proc/self/cgroup"
  ;;
systemd)
  run "systemd-run --unit=report-demo -p CPUQuota=50% -p MemoryMax=512M sleep 30"
  sleep 1
  run "cd /sys/fs/cgroup/system.slice/report-demo.service"
  run "cat cpu.max"
  run "cat memory.max"
  run "cat cgroup.procs"
  run "ps -o pid,comm -p \$(cat cgroup.procs)"
  cd /tmp; systemctl stop report-demo
  ;;
join)
  note "1. 先跑:一个父 shell 起 8 个吃 CPU 的子进程"
  run "setsid bash -c 'for i in {1..8}; do yes >/dev/null & done; echo \$\$ > /tmp/parent.pid; wait' &"
  sleep 1
  P=$(cat /tmp/parent.pid); KIDS=$(pgrep -P $P | xargs); K1=${KIDS%% *}
  run "cat /tmp/parent.pid"
  run "pgrep -P $P | xargs"
  run "cat /proc/$P/cgroup"
  note "2. 后建组,只把父进程写进去,再设限"
  run "mkdir /sys/fs/cgroup/demo"
  run "echo $P > /sys/fs/cgroup/demo/cgroup.procs"
  run "echo \"50000 100000\" > /sys/fs/cgroup/demo/cpu.max"
  note "3. 名单:组里只有父进程,子进程没跟过来"
  run "cat /sys/fs/cgroup/demo/cgroup.procs"
  run "cat /proc/$P/cgroup"
  run "cat /proc/$K1/cgroup"
  note "4. 采样 3 秒:8 个 yes 各吃多少 CPU,demo 组的账上有多少"
  run "grep usage_usec /sys/fs/cgroup/demo/cpu.stat"
  run "top -b -d 3 -n 2 | grep -E 'PID|yes' | tail -9"
  run "grep usage_usec /sys/fs/cgroup/demo/cpu.stat"
  note "5. 补救:把 8 个子进程逐个写进 demo 组"
  run "for k in $KIDS; do echo \$k > /sys/fs/cgroup/demo/cgroup.procs; done"
  run "cat /sys/fs/cgroup/demo/cgroup.procs | xargs"
  sleep 1
  note "6. 再采样 3 秒"
  run "$STAT /sys/fs/cgroup/demo/cpu.stat"
  run "top -b -d 3 -n 2 | grep -E 'PID|yes' | tail -9"
  run "$STAT /sys/fs/cgroup/demo/cpu.stat"
  note "7. 收拾:组里的进程一次杀光,删组"
  run "echo 1 > /sys/fs/cgroup/demo/cgroup.kill"
  sleep 0.5
  run "rmdir /sys/fs/cgroup/demo && echo 已删除"
  rm -f /tmp/parent.pid
  ;;
half1)
  mk_programs
  run "cat work.py"
  note "不设限,直接跑"
  run "python3 work.py $N"
  note "建一个 0.5 核的组;先入组、后变身,再跑同一份活"
  run "mkdir $H"
  run "echo \"50000 100000\" > $H/cpu.max"
  run "$STAT $H/cpu.stat"
  run "$IN python3 work.py $N"
  run "$STAT $H/cpu.stat"
  rmdir $H
  ;;
probe)
  mk_programs
  mkdir $H; echo "50000 100000" > $H/cpu.max
  note "探针:不设限,跑 500 ms"
  run "python3 gaps.py 0.5"
  note "探针:放进 0.5 核的组,跑 500 ms"
  run "$IN python3 gaps.py 0.5"
  note "组里先放 3 个烧 CPU 的任务,再让第 4 个进程跑探针"
  run "for i in 1 2 3; do $IN python3 work.py 999999999 >/dev/null & done"
  sleep 0.35
  run "$IN python3 gaps.py 0.5"
  echo 1 > $H/cgroup.kill; wait 2>/dev/null; sleep 0.3; rmdir $H
  ;;
four)
  mk_programs
  mkdir $H; echo "50000 100000" > $H/cpu.max
  note "4 个任务并行,不设限"
  run "time (for i in 1 2 3 4; do python3 work.py $N & done; wait)"
  note "4 个任务并行,放进 0.5 核的组"
  run "$STAT $H/cpu.stat"
  run "time (for i in 1 2 3 4; do $IN python3 work.py $N & done; wait)"
  run "$STAT $H/cpu.stat"
  rmdir $H
  ;;
duty)
  mk_programs
  mkdir $H
  note "同一份约 0.5 秒 CPU 的活,配额逐级调小"
  run "python3 work.py $NS"
  for q in 50000 25000 12500 5000; do
    run "echo \"$q 100000\" > $H/cpu.max; $IN python3 work.py $NS"
  done
  rmdir $H
  ;;
*) echo "用法:bash -s -- env|systemd|join|half1|probe|four|duty"; exit 1;;
esac
