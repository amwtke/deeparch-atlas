# exit.py:report 主进程 fork 一个 worker;worker 占 50 MiB,0.6 秒后退出;
#         主进程故意等 1.6 秒才去收尸(这中间 worker 是僵尸),再过 0.6 秒自己退出
import os, time
def setname(s):
    with open('/proc/self/comm', 'w') as f: f.write(s)
setname('report')
if os.fork() == 0:
    setname('worker')
    hold = b'x' * (50 << 20)
    time.sleep(0.6)
    os._exit(0)
time.sleep(1.6); os.wait(); time.sleep(0.6)
