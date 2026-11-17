# ticker.py:改名叫 ticker,每 0.5 秒 fork 一个马上退出的子进程(让跟踪脚本有 fork 可看)
import os, time
with open('/proc/self/comm', 'w') as f: f.write('ticker')
while True:
    if os.fork() == 0: os._exit(0)
    os.wait(); time.sleep(0.5)
