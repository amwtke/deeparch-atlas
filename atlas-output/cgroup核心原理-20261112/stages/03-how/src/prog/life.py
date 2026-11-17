# life.py:report 主进程 fork 出一个 worker;worker 依次 烧 CPU → 要内存 → 写盘 → 生一个孩子 → 退出
import os, time
def setname(s):
    with open('/proc/self/comm', 'w') as f: f.write(s)
setname('report'); time.sleep(0.3)
if os.fork() == 0:
    setname('worker')
    t = time.monotonic()
    while time.monotonic() - t < 0.2: pass                     # 烧 0.2 秒 CPU
    buf = b'x' * (20 << 20)                                     # 要 20 MiB 内存
    fd = os.open('/var/tmp/worker.dat', os.O_WRONLY | os.O_CREAT | os.O_TRUNC)
    os.write(fd, buf[:8 << 20]); os.fsync(fd); os.close(fd)     # 写 8 MiB,等它落盘
    if os.fork() == 0: os._exit(0)                              # 生一个孩子
    os.wait(); os._exit(0)                                      # 退出
os.wait()
