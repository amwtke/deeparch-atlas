# 扮演报表任务:主进程 fork 出 N 个 worker,每个 worker 死循环烧 CPU
#   report.py <N> [间隔秒]     每隔「间隔秒」fork 一个(默认不等)
import os, sys, time
n = int(sys.argv[1]); gap = float(sys.argv[2]) if len(sys.argv) > 2 else 0
def setname(s):
    with open('/proc/self/comm', 'w') as f: f.write(s)
setname('report')
for i in range(n):
    if os.fork() == 0:
        setname('report-w')
        while True:
            for _ in range(200000): pass
    time.sleep(gap)
while True:
    try: os.wait()
    except ChildProcessError: break
