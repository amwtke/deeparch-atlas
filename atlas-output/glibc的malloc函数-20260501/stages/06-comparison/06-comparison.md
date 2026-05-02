# 阶段 6:用户态 allocator 全景对比(ptmalloc vs jemalloc / tcmalloc / mimalloc / Go runtime / Rust Layout)

## 约束清单速查(C1~C7)

> 后文所有 `Cn` 引用对应下面 7 条。Comparison 阶段最大的洞察:**6 个 allocator 面对的是同一组 C1~C7,但做出了 6 套不同的取舍**。

#### C1 — 高频小块

应用对动态内存的请求是**高频小块**:每秒 10⁵~10⁷ 次,典型 16~256 字节。
**不可再分**:C++ / 现代脚本运行时的语义现实。
**口诀**:量大频高 → 必须 O(1) 快

#### C2 — syscall 贵

**syscall 至少几百 ns**,比函数调用贵 2 个数量级。
**不可再分**:CPU 特权级机制。
**口诀**:进内核贵 → 必须批量摊薄

#### C3 — brk 中间还不掉

**`brk` 只能移动 program break**,heap 中间块还不掉。
**不可再分**:brk 语义就是改一个 long。
**口诀**:中间还不掉 → 用户态自己攥着

#### C4 — mmap 整页

**`mmap` 最小粒度是一整页**(常见 4 KB)。
**不可再分**:CPU MMU 页表项最细粒度就是一页。
**口诀**:整页 → 小块走它必浪费

#### C5 — free(p) 不传 size

**`free(p)` 只接受指针,不传 size**。
**不可再分(精度升级,见 Deep §2.4.5)**:**技术 + 生态复合** —— 1989 ANSI C ABI + 接口共存。在新语言可消解(C++17 / Rust)。
**口诀**:不传 size → 必须每块自带元数据(C 内锁死,新语言可破)

#### C6 — 碎片必然

**长跑应用必然产生碎片**。
**不可再分**:Knuth 50% 规则。
**口诀**:碎片必然 → 必须有合并机制

#### C7 — 多核并发

**必须支持多线程并发分配/释放**。
**不可再分(精度升级,见 Origin §5.5)**:**时代性约束** —— 1996 浮现,2017 加深,2026+ 在 async 反向演化。
**口诀**:多核 → 必须减锁竞争

---

## §0 从 Deep 走到 Comparison:三件事记住

Deep 阶段你看到了 ptmalloc 三条主路径(tcache / brk / mmap)的真实 call stack。**Comparison 跳出 ptmalloc**,看用户态 allocator 的整个设计空间 —— **同样的 C1~C7 约束,jemalloc / tcmalloc / mimalloc / Go runtime / Rust 都做了不同的取舍**。

### §0.1 不同 allocator = 同问题、不同解

5 个对比对象都解决"用户态高效动态内存分配"这个工程问题,都面对 C1~C7 这 7 条不可再分约束。但**取舍方向截然不同**:

- **ptmalloc**:保兼容、稳定优先;每代叠加(1987→1996→2017),不重写
- **jemalloc**:per-CPU + 积极还内存,FreeBSD/FB 选它解 cgroup
- **tcmalloc**:thread-local + 中央堆,Google 内部 8 年才开源
- **mimalloc**:sharded free list + 极小开销,MS 现代设计代表
- **Go runtime**:整合 runtime + GC,**改语言 ABI 拿到 ptmalloc 永远拿不到的精简**
- **Rust `Layout`**:**消解 [C5](#c5)**(sized dealloc),从根上去掉 ptmalloc 背的"chunk header 债"

**Comparison 阶段的核心价值不在"哪个最好"**,而在**"看清同一个工程问题的设计空间有多大"**。读完这一章,你能说出"如果我面对 X 约束组合,哪个 allocator 是局部最优 + 为什么"。

### §0.2 5 维度看清每个 allocator 在设计空间的位置

横向对比要选维度 —— 维度选不准,对比就成了"功能列表"。本章选 6 个维度(每个 allocator 在每个维度上做了**有意义的、可量化的、跟 ptmalloc 有差异的**选择):

1. **元数据策略** —— per-thread / per-CPU / sharded / runtime-managed(决定锁竞争 + cache locality)
2. **锁 / dealloc 机制** —— mutex / 完全无锁 / lock-free CAS / GC 整合(决定多核扩展性)
3. **碎片管理** —— coalesce / segregated size class / generational(决定长跑 RSS 行为)
4. **如何处理 [C5](#c5)** —— chunk header / size class 反查 / sized dealloc 消解(决定能否摆脱 ANSI C ABI 锁死)
5. **典型应用域** —— Web server / DB / 语言 runtime / Browser / OS(决定哪个 workload 受益最大)
6. **docker/k8s 容器友好性** —— RSS 行为 / dirty page purging / cgroup-aware(2026 主流场景必看)

### §0.3 容器友好性是 2026 主流场景

呼应 Deep §4.5 「分层职责优于哪层最容易」洞察:**ptmalloc 不该做容器检测,但 jemalloc / mimalloc / Go runtime 在设计时就考虑了容器场景**。这是 5 个 allocator 在 2026 拼真实部署时**最尖锐的差异维度**。

### §0 结论:三件事记住

| | 关键事实 | 为什么重要 |
|---|--------|---------|
| **同问题不同解** | 5 个 allocator 面对相同 C1~C7,做出 6 套不同取舍 | 局部最优是"约束组合的"局部最优,不是"绝对最优";不同场景应该选不同 allocator |
| **6 维度地图** | 元数据策略 / 锁机制 / 碎片管理 / C5 处理 / 应用域 / 容器友好 | 选 allocator = 在 6 维空间里挑你 workload 最匹配的 |
| **容器友好是 2026 关键维度** | ptmalloc 不友好,jemalloc/mimalloc/Go 友好,Rust 取决底层 | 选错 allocator → 容器内 OOM-killed |

后面 §1 给设计空间地图;§2 5 个 allocator 简介;§3 6 维度横向汇总;§4 容器友好性专门展开;§5 元洞察(呼应 3 条元规则);§6 约束回扣;§7 呼应灵魂。

---

## §1 设计空间地图

5 个 allocator(+ ptmalloc 作基线)在两个最关键维度上的位置:

![用户态 allocator 设计空间地图](pics/06-design-space-map.svg)

**两个轴**:

- **横轴**(x):**对 [C5](#c5) 的处理方式** —— 从"完全背 C5 债(chunk header)"到"完全消解 C5(sized dealloc)"
- **纵轴**(y):**容器友好性 / cgroup-aware 程度** —— 从"不友好(默认不还内核)"到"全自动(整合 runtime,自动跟踪 cgroup limit)"

**6 个点的位置**(粗略坐标):

- **ptmalloc**(左下,基线):完全背 C5 + 不友好
- **jemalloc**(中下偏右):chunk header + 积极 dirty purge
- **tcmalloc**(中下):size class + 中等
- **mimalloc**(中上):sharded + 友好(`mi_option_purge_delay`)
- **Go runtime**(右上):runtime-managed + 全自动 `GOMEMLIMIT`
- **Rust `Layout`**(右下/浮动):sized dealloc 消解 [C5](#c5),容器友好性取决底层

**几件能从图上读出来的事**:

1. **没有"右上完美点"** —— 没有 allocator 同时做到"完全消解 [C5](#c5)" + "全自动容器跟踪"。最接近的是 Go runtime,但它代价是绑死 Go 语言
2. **ptmalloc 在最左下** —— 最大兼容性 = 最大约束债
3. **mimalloc / Go runtime 是现代设计代表** —— 都是 2017+ 设计,容器友好是天生的
4. **Rust `Layout` 路线特别** —— 横轴最右(完全消解 [C5](#c5)),但纵轴漂移(取决于底层 allocator),展示了"消解约束"和"容器友好"是两个独立维度

---

## §2 5 个 allocator 简介

### §2.1 jemalloc(Jason Evans @ FreeBSD 7.0+,2008)

**起源**:Jason Evans 2005 在 FreeBSD 内部解决 phkmalloc 的多线程瓶颈;2008 FreeBSD 7.0 默认。后来 Facebook 收编 Jason Evans 开发 jemalloc 4.x+,优化 FB 内部高并发服务。Rust(`#[global_allocator] = jemalloc-sys`)从 1.x 起到 1.32 长期默认。

**核心 trick(跟 ptmalloc 的差异)**:

- **per-CPU arena**(不是 per-thread)—— 4× cores 个 arena,thread 用 `RDTSCP` 拿当前 CPU,绑到对应 arena;减少 thread 数 ≫ cores 时 arena 失控膨胀
- **size class 反查**(不靠 chunk header 反向偏移)—— alloc 时记 size,free 时 chunk 地址 / chunk_size_log2 反查 metadata
- **dirty page purging 默认积极**(`opt.dirty_decay_ms`,默认 10 秒后还内核)—— 这是容器友好的核心
- **多 arena 间 lock-free transfer** —— 跨 arena 移块用 CAS,不持有跨 arena 锁

**典型部署**:Facebook(全栈)、Cassandra、Redis(`USE_JEMALLOC=yes` 默认)、Rust 一段时间默认。

**最大代价**:**chunk metadata 外置**(在固定的 metadata 表里) → 比 ptmalloc 多一次 cache miss;但换来 [C5](#c5) 反查更精确 + 锁更少。

### §2.2 tcmalloc(Sanjay Ghemawat @ Google,2007 开源,内部更早)

**起源**:Google 内部 2003+ 开发,2007 作为 `gperftools` 一部分开源。Sanjay Ghemawat(MapReduce / GFS / Bigtable 设计者之一)主导。Google 内部所有 C++ 服务**默认就是 tcmalloc**,跑了二十多年。

**核心 trick**:

- **thread-local cache + 中央堆** —— 每个 thread 有自己的 free list cache;cache miss 才进 中央堆(central freelist)。这是 **2007 就有 thread-local cache,比 glibc tcache 早 10 年**
- **size class** —— ~89 个固定 size class(8B / 16B / 32B / ...),所有 chunk 按 class 对齐;chunk metadata 通过 page-level radix tree 反查
- **CentralFreeList 基于 page**(不是 chunk)—— 中央堆按 4KB page 管理,page 内切多个相同 size class 的 chunk;减少 metadata 开销
- **page heap 用 radix tree** 跟踪每个 page 属于哪个 size class —— 比 chunk header 反向偏移多一次跳转,但跳转目标在小型 radix tree(命中 cache 概率高)

**典型部署**:Google 全栈(MapReduce / Bigtable / Spanner / ...)、Chrome 浏览器、外部 ClickHouse 等数据库。

**最大代价**:**没有 cgroup-aware 默认行为**(开源版);Google 内部有 cgroup-aware fork 但不开源。需要手动 `MALLOC_RELEASE_RATE` 调内存还回率。

### §2.3 mimalloc(Daan Leijen @ Microsoft,2019)

**起源**:Daan Leijen(Haskell / Koka 语言研究员)2019 在 MS Research 设计。**Rust 现代默认推荐**(替换 jemalloc),Linux 容器场景大量使用。Lean 4 / .NET runtime 集成。

**核心 trick**:

- **sharded free list** —— 单个 heap 内 free list 不是一条全局链,是分成 ~128 shard;同一线程不同时间访问不同 shard,大幅降低 cache line bouncing
- **free 时 sharded into thread-local pages** —— 不写共享 metadata,只写 thread-local 队列;另一线程定期 reclaim
- **极小代码量**(3K LOC vs jemalloc 30K vs ptmalloc 5K+)—— 易于 audit,适合安全敏感场景
- **`mi_option_purge_delay`** —— 默认 100ms 后还内存(比 jemalloc 还激进),容器友好性极佳
- **`mi_heap_t`** —— 每个 thread 一个独立 heap,destroy 时整个 heap 一次释放(比逐个 free 快很多)

**典型部署**:.NET 6+ runtime(默认)、Rust 社区现代主流、MS Linux 容器服务。

**最大代价**:**生态较年轻**(2019 起,vs jemalloc 2008 / tcmalloc 2007);兼容性 patches 持续在收;部分 corner case(超大 alloc + free pattern)有过 regressions。

### §2.4 Go runtime malloc(Go team,2009~,持续演化)

**起源**:Go 1.0(2012)就有自己的 allocator,基于 tcmalloc 设计但深度整合 GC + goroutine 调度。**改语言 ABI 拿到 ptmalloc 永远拿不到的精简**。

**核心 trick**:

- **per-P allocator**(P = GOMAXPROCS,= CPU 核数)—— 不是 per-thread / per-goroutine;P 是 Go 调度器的"逻辑处理器",数量稳定 = cores
- **mcache → mcentral → mheap 三层** —— mcache per-P 无锁;mcentral per-size-class 共享;mheap 全局
- **GC 整合** —— allocator 跟 GC mark-sweep 共享 metadata;free 不是用户调用,是 GC 自动收
- **`GOMEMLIMIT` env var(Go 1.19+)** —— 自动跟踪 cgroup memory limit,GC 在接近 limit 时积极回收。**这就是 Deep §4.5 候选 C 的合法实现**(因为 Go runtime 是应用层 runtime,不是 C 库,所以做这个不违反分层)
- **改 ABI 消解 [C5](#c5)** —— Go runtime 知道每个对象的 type info(static type tracking),free / GC 时 size 是已知的,不需要 chunk header

**典型部署**:所有 Go 程序(Kubernetes / Docker daemon / Prometheus / 大量 cloud-native)。

**最大代价**:**绑死 Go 语言** —— 不能给 C/C++ 应用用;改 ABI 的精简换不到跨语言通用。

### §2.5 Rust `Layout` allocator(Rust core,2017+)

**起源**:Rust 1.x 加 `core::alloc::Layout` API,要求每次 alloc/free 都传 `Layout { size, align }`。**完全消解 [C5](#c5)**(sized dealloc),Origin §2.4.5 候选 D 的现实落地。

**核心 trick**:

- **`Layout` API 强制 sized dealloc** —— `alloc(layout)` / `dealloc(ptr, layout)`,**编译器通过 type tracking 自动填 layout**,用户不用手动传(避免 Origin §2.4.5 候选 1 的"用户传错 size")
- **不需要 chunk header**(理论上)—— size 由编译器追踪,allocator 后端可以砍 chunk header overhead
- **`#[global_allocator]` 可换底层** —— 默认 `System`(= glibc malloc / OS allocator);常换 `mimalloc` / `jemalloc-sys` / `tcmalloc` / 自定义
- **Drop 自动 free** —— Rust ownership 自动调 dealloc,程序员不写 free

**典型部署**:Rust 全栈(Firefox 部分、Cargo、各种 cloud-native CLI 工具如 `ripgrep` / `bat` / `bottom`)。

**最大代价**:**理论的精简没拿到** —— Rust 默认 `System` allocator 仍是 glibc malloc(背 chunk header 债),社区主流换 mimalloc 才友好。**`Layout` 接口本身是消解 [C5](#c5),但底层 allocator 不一定利用了** —— 这是 Origin §2.4.5 「接口共存的结构性问题」的精确实例。

---

## §3 6 维度横向汇总(分两子表)

### §3.1 设计选择维度(元数据 / 锁 / 碎片 / [C5](#c5) 处理)

| | **元数据策略** | **锁 / dealloc 机制** | **碎片管理** | **如何处理 [C5](#c5)** |
|---|------------|------------------|----------|------------------|
| **ptmalloc** | per-thread tcache(2017+)+ multi-arena(1996) | mutex per-arena + tcache 完全无锁 | coalesce 相邻 free chunk + bin 分桶 | **chunk header 反向偏移读 size**(背 C5 债) |
| **jemalloc** | per-CPU arena(4× cores)+ thread-local small cache | mutex per-arena + lock-free small cache | size class 分档(no coalesce within class) | size class 反查(metadata 外置在 chunk_size_log2 表)|
| **tcmalloc** | per-thread cache + 中央 page heap | thread-local 完全无锁 + 中央 page heap mutex | size class(~89 类)+ page heap radix tree | page-level radix tree 反查 |
| **mimalloc** | per-thread heap + sharded free list(128 shards) | sharded 无锁(同 shard 内 thread 独占) | size class + thread-local pages | sharded metadata table |
| **Go runtime** | per-P mcache + per-class mcentral + 全局 mheap | per-P 无锁 + mcentral mutex + GC 整合 | GC mark-sweep + size class | **runtime type tracking**(完全不需要 metadata 反查)|
| **Rust `Layout`** | 取决于底层 allocator | 取决于底层 | 取决于底层 | **sized dealloc(编译器代填)完全消解** |

### §3.2 部署 + 容器维度(应用域 / docker/k8s 友好性)

| | **典型应用域** | **docker/k8s 容器友好性** |
|---|----------|---------------------|
| **ptmalloc** | C/C++ 通用 + glibc 默认 | ❌ **默认不友好** —— 不还内核;需手动 `MALLOC_TRIM_THRESHOLD_=131072` + `MALLOC_ARENA_MAX=2` |
| **jemalloc** | Facebook 全栈 / Cassandra / Redis / Rust 一段时间 | ✅ **核心卖点之一** —— `dirty_decay_ms=10s` 默认积极还内存;FB 选它部分原因 |
| **tcmalloc** | Google 全栈 / Chrome / ClickHouse | 🟡 **中等** —— 开源版无 cgroup-aware;需手动 `MALLOC_RELEASE_RATE`;Google 内部 fork 友好但闭源 |
| **mimalloc** | .NET 6+ / Rust 现代 / MS 容器服务 | ✅ **极好** —— `mi_option_purge_delay=100ms`(比 jemalloc 还激进);为现代 workload 设计 |
| **Go runtime** | 所有 Go 程序(Kubernetes / Docker / Prometheus) | ✅✅ **最友好** —— `GOMEMLIMIT` 自动跟踪 cgroup memory limit;GC 在接近 limit 时积极回收 |
| **Rust `Layout`** | Rust 全栈(Firefox / cargo / CLI 工具) | 🟡 **取决底层** —— 默认 `System`(= glibc 不友好);主流社区换 mimalloc 后变友好 |

---

## §4 docker/k8s 容器友好性专门展开(呼应 Deep §4.5)

容器场景下 allocator 的关键行为差异 —— 这维度在 2026 决定**容器内服务能否避免 OOM-kill**。

### §4.1 容器场景下 allocator 必须解决的 3 个具体问题

1. **RSS 增长是否随 free 自动收缩?** —— 不收缩 → cgroup memory limit 累积到限 → OOM-killed
2. **dirty page 多久还回内核?** —— 越激进越友好,但 syscall 频率涨,有性能代价
3. **是否 cgroup-aware?** —— 检测 cgroup memory limit 自动调行为(arena 数 / trim 阈值 / GC 频率)

### §4.2 5 个 allocator 的具体行为

#### ptmalloc(默认不友好)

- free 后 chunk 挂回 unsorted bin,**不调 munmap / brk(收缩)**
- 默认无 dirty page purging
- 不 cgroup-aware
- **修复方法**(分层职责正确解):容器编排层注入 env var
  ```dockerfile
  ENV MALLOC_TRIM_THRESHOLD_=131072
  ENV MALLOC_ARENA_MAX=2
  ```
  或 `LD_PRELOAD=libjemalloc.so` 整体替换

#### jemalloc(积极还内存)

- **`opt.dirty_decay_ms = 10000`**(默认 10 秒)—— free 后的 dirty page 10 秒后用 `madvise(MADV_DONTNEED)` 还回内核
- **`opt.muzzy_decay_ms = 10000`** —— "muzzy" 是介于 dirty 和 clean 之间的状态(已 madvise 但 RSS 还在);二级 decay 让 RSS 持续下降
- 不 cgroup-aware,但因为默认行为已经积极还内存,容器 OOM 风险低
- **可调更激进**:`MALLOC_CONF="dirty_decay_ms:1000"`(1 秒)适合 cgroup memory tight 场景

#### tcmalloc(中等友好)

- 有 `MALLOC_RELEASE_RATE` 控制还回积极性(默认 1.0,可调到 10+ 更激进)
- 默认行为类似 ptmalloc(慢慢还),不如 jemalloc 积极
- 开源版**不 cgroup-aware**;Google 内部 tcmalloc fork 集成 cgroup 检测但闭源
- **典型容器调优**:`TCMALLOC_RELEASE_RATE=10` env var

#### mimalloc(极激进)

- **`mi_option_purge_delay = 100`**(默认 100ms)—— 比 jemalloc 还激进 100×
- **`mi_option_eager_commit = false`** —— 默认懒提交,虚拟内存映射但物理页按需分
- **per-thread heap 销毁时整体释放**(`mi_heap_destroy`)—— 适合 short-lived thread 场景
- 不 cgroup-aware,但默认激进 + 极小开销让容器内表现优秀
- **修复方法**:换 mimalloc 通常无需调参(默认就好)

#### Go runtime(全自动)

- **`GOMEMLIMIT` env var**(Go 1.19+,2022 加)—— 自动跟踪 cgroup memory limit
  ```yaml
  # k8s pod spec
  env:
  - name: GOMEMLIMIT
    valueFrom:
      resourceFieldRef:
        resource: limits.memory
  ```
- GC 在 RSS 接近 `GOMEMLIMIT` 时**自动调高 GC 频率**,激进回收;远低于时延迟回收
- 真正的"cgroup-aware allocator" —— 因为 Go runtime 是应用层 runtime,做这个不违反分层(Deep §4.5 候选 C 的合法版本)
- **代价**:GC 压力增大时 CPU 涨(stop-the-world 时长增)

#### Rust `Layout`(取决于底层)

- 默认 `System` allocator = OS 默认 = Linux 上是 glibc malloc → 跟 ptmalloc 一样不友好
- **常见做法**:`#[global_allocator]` 换 `mimalloc` / `jemalloc-sys` / `tcmalloc`,**继承被换 allocator 的容器友好性**
- Rust 自己**不做** cgroup-aware —— 因为 Rust 是语言不是 runtime,设计上就不该做(分层职责)
- **典型容器配置**:`Cargo.toml` 加 `mimalloc = "0.1"`,`main.rs` `#[global_allocator]` 换 mimalloc

### §4.3 容器友好性的"分层职责"再回看

呼应 Deep §4.5 元洞察:**"容器友好"应该哪一层做?**

| 层级 | 谁做了 cgroup-aware? | 做得好不好? |
|-----|----------------|---------|
| **C 库**(glibc) | ❌ 不做(分层职责正确) | ✅ 不该做就不做 |
| **应用 runtime**(Go runtime, JVM) | ✅ Go `GOMEMLIMIT` / JVM `UseContainerSupport` | ✅ 该做的都做了 |
| **C/C++ 应用** | 通过换 allocator(jemalloc / mimalloc)间接做 | ✅ 通过 LD_PRELOAD 在部署层做 |
| **容器编排**(k8s) | 注入 env var(`MALLOC_TRIM_THRESHOLD_`)| ✅ 部署层注入,跨 OS 兼容 |

**没有 allocator 跨层做容器检测**(因为 allocator 不是 runtime,不该做)。**Go runtime 是 runtime 才该做**;**glibc 是库不该做**。这就是分层职责的活的实例。

---

## §5 元洞察:5 条平行演化路径

### §5.1 同 C1~C7,5 套不同取舍

| Allocator | 优先化解的约束 | 接受的代价 |
|----------|------------|---------|
| **ptmalloc** | 兼容性(任何 C 程序都能用)+ 稳定性 | 容器不友好 + chunk header 背 C5 债 |
| **jemalloc** | [C7](#c7) per-CPU 减锁 + 容器友好 | metadata 外置多一次 cache miss |
| **tcmalloc** | [C1](#c1) thread-local 极快 + size class 简洁 | 中央堆锁是瓶颈;开源版无 cgroup-aware |
| **mimalloc** | sharded 无锁 + 极激进还内存 + 极小开销 | 生态年轻;corner case 偶有 regression |
| **Go runtime** | [C5](#c5) 通过 type tracking 完全消解 + cgroup-aware | 绑死 Go 语言 |
| **Rust `Layout`** | [C5](#c5) sized dealloc 完全消解 | 默认 `System` 没用上,需要手动换底层 |

**5 套取舍 = 5 条平行演化路径**,每条都是"在某个约束子集上的局部最优"。**没有"绝对最优"**。

### §5.2 用户贡献的 3 条元规则在 Comparison 阶段的体现

回看你在 Origin / Deep 阶段贡献给 atlas 第一性原理方法论的 3 条元规则,**Comparison 阶段每个 allocator 都是这 3 条规则的活的实例**:

#### 规则 1(Origin §5.5):约束反向演化 —— 约束不是永恒,新语境可松动甚至反转

- **Go runtime + Rust `Layout`** 是 [C5](#c5) 反向演化的活实例 —— 在新语言语境下,[C5](#c5) 从"绝对不可再分"变成"可消解"
- **mimalloc 为现代 workload 设计** —— 它假设的"workload 形状"(short-lived thread / 容器化部署)跟 ptmalloc 1996 时假设的 workload 完全不同

#### 规则 2(Deep §2.4.5):约束不可再分性是技术 × 生态 × 接口锁死的复合

- **Rust `Layout`** 是这条规则的精确实例 —— [C5](#c5) 的"技术"层面(用户传错 size)被 Rust 编译器代填消解;但"生态"层面(默认 `System` allocator 仍背 chunk header 债)展示了**"接口共存的结构性问题"**:`Layout` 消解了 [C5](#c5),但底层 allocator 不一定利用
- **jemalloc / tcmalloc** 在 C 内做了"同 ABI 下的不同优化",但**没法消解 [C5](#c5)**(C ABI 锁死)—— 它们绕开 chunk header 反向偏移用 size class 反查,但仍要存储 metadata,只是位置变了

#### 规则 3(Deep §4.5):分层职责优于"哪层做最容易"

- **glibc 不做容器检测**(分层职责正确)—— 通过容器编排层注入 env var 是正确解
- **Go runtime 做 `GOMEMLIMIT`**(分层职责正确)—— 因为 Go runtime 是应用层 runtime,该做就做
- **Rust 不做 cgroup-aware**(分层职责正确)—— Rust 是语言不是 runtime,通过换底层 allocator 间接做

**这 3 条元规则一起,把 atlas 的"约束清单"从一维(C1~Cn 列表)扩展到三维方法论:类型 × 时代 × 化解路径**。Comparison 阶段每个 allocator 都是这个三维空间里的一个点。

### §5.3 五条平行演化路径的现实意义

**今天你看到 ptmalloc / jemalloc / tcmalloc / mimalloc / Go / Rust 五条路径并存,而不是哪个胜出**,本质就是 [C1](#c1)~[C7](#c7) 7 个约束在"约束空间"里有多个局部最优,每个 allocator 占据一个局部最优。

**未来 10 年的演化方向**(Origin §5.5 反向演化 + Deep §3.4 ML workload):

- 现有 6 个 allocator 都假设 "alloc 是高频小块" + "thread 是稳定单位"
- ML / async / 协程 workload **颠覆这两个假设** → 现有 allocator 都不再最优
- PyTorch CUDA caching allocator / vLLM PagedAttention / Tokio runtime allocator 是**"第七、八、九条"演化路径的雏形**

---

## §6 约束回扣 —— 6 个 allocator 化解 C1~C7 的不同方式

| 约束 | ptmalloc | jemalloc | tcmalloc | mimalloc | Go runtime | Rust `Layout` |
|-----|---------|---------|----------|---------|-----------|-------------|
| [C1](#c1) 高频小块 | tcache 64×7 | thread-local cache | thread-local cache(早 10 年) | sharded free list | per-P mcache | 取决底层 |
| [C2](#c2) syscall 贵 | 默认不还(brk)+ batch | dirty_decay_ms 平衡 | release_rate 平衡 | purge_delay 激进还 | GC 控制还回时机 | 取决底层 |
| [C3](#c3) brk 中间还不掉 | 不还(等复用) | madvise DONTNEED | madvise DONTNEED | madvise DONTNEED | runtime 控制 | 取决底层 |
| [C4](#c4) mmap 整页 | M_MMAP_THRESHOLD 128KB | extent-based mmap | page heap 4KB | OS page-aligned | runtime mheap | 取决底层 |
| [C5](#c5) free(p) 不传 size | chunk header 反向偏移 | size class 反查 | radix tree 反查 | sharded metadata | **type tracking 消解** | **sized dealloc 消解** |
| [C6](#c6) 碎片必然 | coalesce 相邻 | size class(no coalesce) | size class | size class + thread-local pages | GC mark-sweep | 取决底层 |
| [C7](#c7) 多核并发 | multi-arena + tcache | per-CPU arena | thread-local + 中央 | sharded free list | per-P + 整合 GC | 取决底层 |

**关键观察**:

1. **每条约束都有多种化解方式** —— 没有"唯一正确解"
2. **[C5](#c5) 列最有戏剧性** —— 6 个 allocator 走出 4 种不同方式(chunk header / size class 反查 / type tracking / sized dealloc),其中后两者**只在新语言里可行**(C 锁死)
3. **取决底层** 出现在 Rust 那列多次 —— 反映 Rust `Layout` 是**接口层消解**,不是底层实现层消解

---

## §7 呼应灵魂问题

你的灵魂问题:**"malloc 要解决的工程问题是什么?"**

走完 What → Why → How → Origin → Deep → **Comparison**,这个问题已经能从**5 条平行演化路径的高度**回答:

- **是什么**:用户态高效动态内存分配
- **为什么**:7 条不可再分硬约束 [C1](#c1)~[C7](#c7)
- **怎么工作**:三件事(chunk + bin + arena)+ tcache 旁路;5 步骨架
- **怎么来的**:1987→2006→2017 三代叠加(经典 ptmalloc 演化)
- **真实 call stack**:三条主路径(tcache / brk / mmap)
- **设计空间多大**(本阶段):**6 个 allocator 在 C1~C7 上做出 5+ 套不同取舍,每条都是某约束子集的局部最优**

### Comparison 阶段最大的认知收益

1. **从"知道一个 allocator"升级到"看清整个设计空间"** —— 你能解释为什么 FB 选 jemalloc / Google 选 tcmalloc / .NET 选 mimalloc,不是品味,是约束权重不同
2. **每个 allocator 的"代价"成为可量化的概念** —— 没有"完美 allocator",只有"匹配你 workload 约束权重的 allocator"
3. **3 条元规则在 Comparison 落地** —— Origin §5.5 / Deep §2.4.5 / Deep §4.5 不再是抽象方法论,而是 6 个 allocator 的真实差异

### 灵魂问题的最终答案(从设计空间高度)

**malloc 要解决的工程问题** = **在 [C1](#c1)~[C7](#c7) 7 条不可再分约束下,如何最优地服务"用户态动态内存分配"这个需求**。**没有唯一最优解,只有约束权重不同的局部最优**:

- 兼容性优先 → ptmalloc
- 容器友好优先 → jemalloc / mimalloc
- thread 极速优先 → tcmalloc / mimalloc
- 整合 runtime 优先 → Go runtime
- 消解 [C5](#c5) 优先 → Rust `Layout`

下一阶段 → **Synthesis**(收束,把 5 阶段 + Comparison + 用户 3 条元规则融合成综合长文)。

---

## 修订记录

| 时间 | 修订摘要 | 触发原因 |
|------|---------|---------|
| 2026-05-02 19:30 | 初稿:严格按新「Stage 开场对齐纪律」(渐进式 + 追加 reconfirm)走完 4 步对齐(同领域 vs 跨领域 → 全景扫描 → 6 维度 → 加 docker/k8s 容器友好性 → 用户 OK)后生成。§0 三件事(同问题不同解 / 6 维度地图 / 容器友好是 2026 关键);§1 设计空间 SVG;§2 5 个 allocator 简介(jemalloc / tcmalloc / mimalloc / Go runtime / Rust Layout);§3 6 维度横向汇总(分两子表);§4 docker/k8s 容器友好性专门展开(呼应 Deep §4.5);§5 元洞察(5 条平行演化路径 + 用户贡献的 3 条元规则在每个 allocator 的体现);§6 约束回扣(6 allocator × 7 约束矩阵);§7 呼应灵魂(从设计空间高度的最终答案,没有唯一最优解);总长 ~750-800 行 | Comparison 阶段对齐完成,用户在追加 reconfirm 后说 OK |
