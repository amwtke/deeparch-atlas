#!/usr/bin/env bash
# 05-scx-demo.sh —— 装一个 BPF 调度器、看它接管、再看看门狗把它踢回 fair
#
# 需要:Linux ≥ 6.12,CONFIG_SCHED_CLASS_EXT=y;clang ≥ 16、libbpf、bpftool;内核源码树里的 tools/sched_ext
#       (或 https://github.com/sched-ext/scx 的 scx_simple / scx_qmap 二进制)。root 权限。
# 运行:sudo ./05-scx-demo.sh /path/to/linux-6.12
set -euo pipefail
SRC=${1:-/usr/src/linux-6.12}
SYSFS=/sys/kernel/sched_ext

echo "== 0. 编译内核自带的示例调度器(第一次约 1 分钟)"
make -C "$SRC/tools/sched_ext" -j"$(nproc)" >/dev/null
BIN="$SRC/tools/sched_ext/build/bin"

echo "== 1. 装载前:$SYSFS/state 应为 disabled"
cat $SYSFS/state

echo "== 2. 装载 scx_simple(tools/sched_ext/scx_simple.bpf.c:全局一条按 vtime 排序的 DSQ)"
"$BIN/scx_simple" &            # → bpf(BPF_LINK_CREATE, struct_ops) → ext.c bpf_scx_reg → scx_ops_enable
SCX_PID=$!
sleep 1
echo "-- state / ops / switch_all:"
cat $SYSFS/state $SYSFS/root/ops $SYSFS/switch_all | paste -sd' '
echo "   期望:enabled simple 1 —— 所有 fair 任务已被 scx_ops_enable 挪进 ext 类(switch_all=1)"
echo "-- dmesg 最后一行应是 sched_ext: BPF scheduler \"simple\" enabled"
dmesg | grep sched_ext | tail -1
echo "-- 此时每次换人:__pick_next_task 跳过 fast path → for_each_active_class 跳过 fair(switched_all)"
echo "   → balance_scx → balance_one → SCX_CALL_OP(dispatch) → scx_bpf_consume(SHARED_DSQ) → pick_task_scx 弹本地 DSQ"

echo "== 3. 正常卸载:Ctrl-C 等价"
kill -INT $SCX_PID; wait $SCX_PID 2>/dev/null || true
sleep 0.5
dmesg | grep sched_ext | tail -1
echo "   期望:sched_ext: BPF scheduler \"simple\" disabled (unregistered from user space)"

echo
echo "== 4. 看门狗:用 scx_qmap 的 -t 选项故意让每第 N 个用户任务不被派发(待核 #26 选项拼写)"
echo "   scx_qmap 自带 timeout_ms = 5000,所以 5 s 内 check_rq_for_timeouts 会发现 runnable_at 过期"
timeout 20 "$BIN/scx_qmap" -t 3 || true
sleep 0.5
dmesg | grep -E "sched_ext|failed to run for" | tail -3
echo "   期望两行:"
echo "   sched_ext: BPF scheduler \"qmap\" disabled (runnable task stall)"
echo "   sched_ext: qmap: <comm>[<pid>] failed to run for 5.xxxs"
echo "   —— 这就是 scx_ops_error_kind(SCX_EXIT_ERROR_STALL) → scx_ops_disable_workfn:"
echo "      先 scx_ops_bypass(true) 保证所有任务能跑,再逐个 p->sched_class = fair,最后关 __scx_ops_enabled"
cat $SYSFS/state
