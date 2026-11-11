# 05-deep / src —— 可运行的实证

| 文件 | 对应主线 | 需要 |
|---|---|---|
| `05-switch-demo.c` + `05-sched-switch.bt` | 主线一:一次换人的全路径(门 1 抢占 / 门 2 睡 / fork 伪造栈) | gcc、bpftrace ≥ 0.20,任意 Linux ≥ 6.x 都能跑;源码行号按 6.12 |
| `05-cgroup-demo.sh` | 主线二:组调度权重 + cpu.max 带宽 throttle | cgroup v2,root |
| `05-scx-demo.sh` | 主线三:装载 scx_simple、卸载、用 scx_qmap 触发看门狗 | 6.12 + CONFIG_SCHED_CLASS_EXT,clang/libbpf,root |

```bash
gcc -O0 -g -pthread 05-switch-demo.c -o 05-switch-demo
sudo bpftrace 05-sched-switch.bt      # 终端 A
./05-switch-demo                       # 终端 B
sudo ./05-cgroup-demo.sh
sudo ./05-scx-demo.sh /usr/src/linux-6.12
```

每个脚本的「期望输出」写在脚本自己的 echo 里。gdb 想停在换人现场:`b __switch_to`(需 kgdb / qemu + `-s`),或者在用户态只看结果:`perf stat -e context-switches,cpu-migrations ./05-switch-demo`。
