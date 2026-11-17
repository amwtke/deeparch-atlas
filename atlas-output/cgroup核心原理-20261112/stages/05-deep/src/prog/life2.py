# life2.py:report 主进程 fork 一个 worker;worker 先烧 0.3 秒 CPU(会被限流几次),
#          再每 50 毫秒要 10 MiB 内存,直到撞上 memory.max 被杀;主进程收尸后退出
import os, time
def setname(s):
    with open('/proc/self/comm', 'w') as f: f.write(s)
setname('report'); time.sleep(0.2)
if os.fork() == 0:
    setname('worker')
    t = time.monotonic()
    while time.monotonic() - t < 0.3: pass
    hold = []
    while True:
        hold.append(b'x' * (10 << 20)); time.sleep(0.05)
_, st = os.wait()
print(f"report:worker 退出,状态 {st}(9 号信号 = SIGKILL)", flush=True)
