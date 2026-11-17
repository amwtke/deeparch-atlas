# hold.py <名字> <M> [每步MiB 间隔秒]:改名后一点点吃到 M MiB 内存,然后占住不放
import os, sys, time
name, m = sys.argv[1], int(sys.argv[2])
step = int(sys.argv[3]) if len(sys.argv) > 3 else 10
gap = float(sys.argv[4]) if len(sys.argv) > 4 else 0
with open('/proc/self/comm', 'w') as f: f.write(name)
hold = []
for _ in range(m // step):
    hold.append(b'x' * (step << 20)); time.sleep(gap)
print(f"{name}(pid {os.getpid()})已占住 {m} MiB", flush=True)
time.sleep(600)
