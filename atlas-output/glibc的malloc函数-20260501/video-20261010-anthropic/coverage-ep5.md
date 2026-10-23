# ep5 覆盖与源码核对

主链：相同大小可有不同路径 → 先预测库存提前返回 → 固定 glibc 2.34 验证 → arena库存和缺货补充 → 按来源释放 → 调试/trace/反事实与容器观测。

上游片段全部程序化原样摘自本目录 src/malloc.c 与 src/arena.c；[固定 glibc 2.34 malloc.c](https://raw.githubusercontent.com/bminor/glibc/glibc-2.34/malloc/malloc.c)、[arena.c](https://raw.githubusercontent.com/bminor/glibc/glibc-2.34/malloc/arena.c)。实践命令为教学操作，不冒充上游源码或已实测结果。

| MD 必讲项 | 工程证据 | VMD 场景 | 处理 |
|---|---|---|---|
| Deep §0–1 三路径与调用链图 | 固定源码、pics/05-call-stack-three-paths.png | 1–5、11 | 保留，按条件画分叉 |
| §3.1 尺寸、chunk与桶号 | request2size/csize2tidx 宏 | 6 | 校正24→32→桶0；不机械加16 |
| §3.2 tcache命中/取出/释放 | malloc.c 3184–3204 / 3077–3088 / 3061–3073 | 7–9 | 原样；2.34用tcache_get，不拼较新tcache_get_n |
| §3.3 性能特征 | 可观察经过的工作 | 8–10、23 | 保留免锁/无新syscall因果；删除未实测纳秒、比例、栈深 |
| §3.4 缓存关闭、上限成本反事实 | 容量为零对照、ep4缓存代价 | 10、21–23 | 保留关闭对照；不编造命中率曲线或把16KiB说成2.34可调上限 |
| §4 arena/brk路径 | arena.c 115–132，malloc.c 4256–4278 | 12–15 | 8KiB不一定brk；非主arena扩堆与独立映射分开 |
| §4.2 普通free与合并 | _int_free真实状态流程 | 15 | 保留tcache/fastbin/合并/top与回收条件 |
| §4.4–4.5 RSS与容器分层 | 活对象/保留空间/驻留页/cgroup分层 | 16、20 | 保留排障动作；不继承glibc跨macOS/维护者绝对反对的无来源断言 |
| §5 独立mmap分支与free | malloc.c 2413–2443 / 3251–3278，munmap_chunk | 17–20 | 大块先经_int_malloc，可能持arena锁；free在__libc_free路由munmap |
| §5.4 阈值变化 | __libc_free动态阈值代码 | 19–20 | 初始128KiB不是永恒阈值；已有库存优先 |
| §2 编译、strace、gdb | 新版src/05-demo.c与命令 | 21–22 | Linux glibc运行，明确非本机已验证结果 |
| §6–8 比较/约束回扣与总结 | 源码验证加成本条件 | 23–24 | 以路径成本因果总结，不报300倍固定结论 |

严格前提：常见64位 SIZE_SZ=8、MALLOC_ALIGNMENT=16、MINSIZE=32、未启用MTE；request2size(24)=32；request2size(8192)=8208；csize2tidx(32)=0。200KiB若最终独立mmap，在4KiB页条件下申请208896字节（204KiB），需触页才可解释RSS增长；free撤映射不保证全进程统计立即按同一数字下降。
