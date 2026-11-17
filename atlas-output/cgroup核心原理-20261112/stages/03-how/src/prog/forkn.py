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
