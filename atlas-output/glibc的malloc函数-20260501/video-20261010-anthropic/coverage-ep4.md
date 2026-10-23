# ep4 覆盖与校正

主链：线程增加却排队 → 空间复用基础 → 数据和同步一起分片 → 本地缓存避开公共管理 → 空间、安全和负载边界。

| 源文档必讲项 | 证据 | 场景 | 处理 |
|---|---|---|---|
| Origin §0、§1 三代演进 | 固定 glibc 2.3 源码与官方公告 | 1–3、14 | 保留，校正 2006 整合说法 |
| §2 Lea 的起点、专用→通用 | [作者回顾](https://gee.cs.oswego.edu/dl/html/malloc.html) | 4–7 | 保留 |
| §3 共享状态与锁粒度 | 结构推导，明确非作者亲历叙述 | 8–10 | 保留因果，删除未证实死胡同故事 |
| §4 多 arena、跨线程释放 | [glibc 2.3 源码](https://raw.githubusercontent.com/bminor/glibc/glibc-2.3/malloc/malloc.c)、src/arena.c | 11–13、16 | 保留；上限与虚拟空间、RSS分开 |
| §5.1 tcache | [官方补丁](https://sourceware.org/pipermail/libc-alpha/2017-July/083110.html)、[官方评审](https://sourceware.org/pipermail/libc-alpha/2017-July/083116.html) | 17–19 | 保留；不声称固定加速倍数 |
| §5.2 安全权衡 | glibc 2.34 malloc.c tcache_get/put 与 _int_free | 20 | 保留防御边界；不继承错误 CVE 归因 |
| §5.4–5.5 专用负载与约束变化 | [Go 运行时源码](https://go.dev/src/runtime/malloc.go)、[Rust System 文档](https://doc.rust-lang.org/std/alloc/struct.System.html) | 21 | 保留缓存单位；校正“异步即几百万份TLS/自动失效”“Rust默认mimalloc” |
| §6–8 成本与历史债 | 对应管理机制 | 15–22 | 保留回退价值与迁移原则 |
| §9–10 引用与未知 | [2002-10-03 发布公告](https://sourceware.org/legacy-ml/libc-alpha/2002-10/msg00048.html) | 3、10、16、22 | 引用保留于此；未知动机不当史实讲 |

更正：glibc 2.3 源码头部写 ptmalloc2-20011215 基于 dlmalloc 2.7.0（2001），已证实 2002 版本包含该实现，并不把它当多 arena 最早出现时间。删除“dlmalloc从未支持锁”的绝对论断（后续独立实现有 USE_LOCKS），删除共同 fork 为整个 allocator 生态单一起因的猜测。旧 fastbin/unsorted 命中率不存在本次测量，不报固定百分比。每集独立开场、结尾和总结卡符合主流程分集要求。
