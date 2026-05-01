# 阶段 3:glibc 的 malloc 大致怎么工作

## 接续 Why 阶段

你在 Why 阶段已经自己用 4 层推理和 buddy/NUMA zone 两个类比,把 malloc 的形状几乎勾出来了。这一轮的本分 —— 把那 4 层抽象推理**精确化**成 ptmalloc2 里你能指着源码说的具体组件:

| 你的推理 | ptmalloc2 的具体组件 |
|---------|---------------------|
| **"必须记账,最朴素是链表串起来"**(第 1 层) | **chunk header**(每块内联 size + 3 个标志位)—— 反向偏移就能查 |
| **"参考 buddy,链接 chunk 找到所有分配空间"**(第 2 层) | **chunk 双向邻接**(物理地址上前后相邻的 chunk 可以 O(1) 查 + 合并) |
| **"分桶,快速找合适大小"**(第 3 层) | **bin** —— 4 类桶:fastbin / smallbin / largebin / unsorted bin |
| **"多线程分区,类似 NUMA zone"**(第 4 层) | **arena** —— 主 arena(brk 扩) + 线程 arena(mmap 扩),数量上限 `8 × CPU 核数` |

**剩下两个组件没在你推理里直接出现,但被前提观察隐含**:

| 隐含的需求 | ptmalloc2 的具体组件 |
|-----------|---------------------|
| **"brk 还不掉中间 + mmap 整页"**(C3 + C4) | **top_chunk** —— arena 末端"剩饭",新分配优先从这切;**M_MMAP_THRESHOLD = 128 KB** —— 大块走 mmap 直分(可还) |

下面把这些组件怎么协作,串成一次完整工作流程。

---

## 用户视角凝固:层级关系澄清(进程 / arena / bin / chunk 怎么嵌套?)

(本节由对话凝固 —— 用户主动问"glibc 是不是分进程加载、不同进程独立?然后 arena / bin / chunk 怎么嵌套?"。这两个问题揭示了一个关键的责任分层,先把它澄清,再看后面的流程会顺得多。)

### 层级 1:进程隔离(由 Linux 内核给,不是 ptmalloc2 给)

glibc(`libc.so.6`)是一个**共享库**,每个进程加载它时:

```
进程 A 的地址空间                            进程 B 的地址空间
┌──────────────────────────┐                ┌──────────────────────────┐
│  libc.so.6 代码段         │ ←─共享物理页─→ │  libc.so.6 代码段         │
│  (malloc/free 指令本身)   │                │  (内核 mmap 同一份只读)   │
├──────────────────────────┤                ├──────────────────────────┤
│  libc.so.6 数据段         │                │  libc.so.6 数据段         │
│  ❌ 不共享 —— per-process  │                │  ❌ 不共享                │
│    - main_arena 实例      │                │    - main_arena 实例      │
│    - 各种全局变量、锁     │                │    - 全局变量、锁         │
├──────────────────────────┤                ├──────────────────────────┤
│  进程 A 的 heap (brk 扩)  │                │  进程 B 的 heap           │
├──────────────────────────┤                ├──────────────────────────┤
│  thread arena × N (mmap)  │                │  thread arena × N         │
└──────────────────────────┘                └──────────────────────────┘
```

**关键点**:

- **指令共享、状态独立**:多个进程跑同一份 `malloc()` 代码,但 `main_arena`、bins、chunks 等所有状态各有一套
- **进程隔离 = 内核责任**:这不是 ptmalloc2 自己做的,是 Linux 内核给每个进程独立 page table 自然带来的
- **ptmalloc2 看不见"进程"**:它假设自己只服务一个进程内的所有线程,顶层就是 arena

> ⚠️ 没有"glibc 域"这一层。如果你听到"glibc 分域加载",大概率是把"进程隔离"误说成"域"。准确表述:**进程隔离由内核给,arena 多池由 ptmalloc2 给**。

### 层级 2:进程内的 arena / bin / chunk 嵌套

进程内 ptmalloc2 的层级图(从粗到细):

```
进程(per-process,内核给的边界)
  │
  └── arena × N (主 arena + 线程 arena;数量上限 8×CPU 核数)
        │
        ├── 「头」状态机:
        │     ├── mutex (并发锁,arena 的访问入口)
        │     ├── top_chunk 指针 (指向 arena 末端那块连续未切的"剩饭")
        │     ├── next / next_free (跟其他 arena 串成全局链表)
        │     └── system_mem (本 arena 向内核要了多少内存)
        │
        ├── 「空闲表」bins[]  (空闲 chunk 的"分桶仓库")
        │     ├── fastbins[0~9]    → chunk → chunk → ... (单链表,小块、不合并)
        │     ├── unsorted bin[1]  → chunk → chunk → ... (临时缓冲,刚 free 的先扔这)
        │     ├── smallbins[2~63]  → chunk ⇄ chunk ⇄ ... (双链表,固定步长)
        │     └── largebins[64~]   → chunk ⇄ chunk ⇄ ... (双链表 + size 排序)
        │     ─────────────────────────────────────────────────────────
        │     注意:bin 不"持有" chunk 的所有权 —— 它只是
        │     空闲 chunk 在等下次复用时,**临时挂在某条链表上**的位置。
        │     在用的 chunk 不在任何 bin 链表里(参考下方的 in-use chunks)。
        │
        ├── 「在用」chunks (返回给应用的,不在任何 bin 上)
        │     ├── chunk(in-use) ←─ p1 = malloc(24)
        │     ├── chunk(in-use) ←─ p2 = malloc(80)
        │     ├── chunk(in-use) ←─ p3 = malloc(200)
        │     └── ...
        │
        └── 「物理布局」(arena 的 heap 段在虚拟地址空间里)
              ┌─────────────────────────────────────────┐
              │ in-use │ free │ in-use │ free │ in-use │ ... │ top_chunk │
              └─────────────────────────────────────────┘
                  ↑      ↑                          ↑
              chunk_A  chunk_B(在 fastbin 链上)  arena 末尾(top_chunk)
              (返给     ↑
               app)    free 的 chunk 物理上还在 heap 里,
                       只是同时也挂在 fastbin / smallbin / ... 某条空闲链上
```

**三件事记住**:

1. **chunk 是物理实体**(heap 上一块连续字节),要么"在用"(被 app 持有指针)要么"空闲"(挂在某条 bin 链表上)
2. **bin 是组织视图**(空闲链表的桶),只是给 chunk 在"等复用期间"做的索引;chunk 本身在 heap 上的位置不变
3. **arena 是容器**,持有一组 bin + 一段 heap + 一把锁 + 当前 top_chunk

**类比**(回扣你 Why 阶段的内核镜像):

| ptmalloc2 | Linux 内核物理页层 |
|----------|---------------------|
| arena | NUMA zone(独立的内存池 + 锁) |
| bin(空闲分桶链表) | buddy 的 free_area[](按 order 分桶的空闲链表) |
| chunk(已切出的字节块) | page(已分配的物理页) |
| in-use 链表 vs bin 链表 | 已分配 vs free_area 队列 |

读完这张层级图,后面 5 步骨架的每一步你就能精确定位:**"这一步是在改 arena 的什么字段"** / **"这一步是在 chunk 的哪个桶之间移动"**。

---

## 核心机制骨架(一次 `malloc(24)` + `free(p)` 的端到端流程)

### 步骤 1:`malloc(24)` 入口 —— 找当前线程的 arena,拿锁

```
应用线程调 p = malloc(24)
       ↓
找到本线程绑定的 arena
   主线程     → main_arena(进程启动时创建,用 brk 扩)
   其他线程  → thread arena(首次 malloc 触发创建,用 mmap 扩)
   线程数 > 8×CPU 核数  → 复用已有 arena(竞锁,但避免 arena 失控膨胀)
       ↓
拿 arena 的 mutex 锁
```

> **arena 的存在**化解 **C7**(多核并发)。锁的粒度是 arena 级,不是全局。

### 步骤 2:在 arena 里**查 bin**

bin 是 arena 内的 4 类空闲链表,按 chunk 大小分桶:

```
fastbin       │ < 64 B  (固定 16 字节步长,共 ~10 个桶)│ 不合并、单链表、最快路径
smallbin      │ 64 B ~ 512 B  (固定 16 字节步长)        │ 双链表、合并相邻
largebin      │ ≥ 512 B  (size class 分桶)              │ 双链表 + 大小排序
unsorted bin  │ 任意大小                                │ 临时缓冲,刚 free 的先扔这等下次
```

```
查桶顺序:
   ① 先看 fastbin(快路径,小块直接挂回不合并)
   ② 再看 unsorted bin(刚 free 的临时位置,可能撞上合适的)
   ③ 最后看 smallbin / largebin
       ↓
    找到合适大小的 chunk → 切下来 → 标 in-use → 返回 user data 指针 ✓
```

> bin 的 4 类分工化解 **C6**(碎片管理)+ **C1**(高频小块要 O(1) 查找);具体桶的边界、查找算法、为什么 fastbin 上限是 64 字节 —— 是 Deep 阶段的事。

### 步骤 3:bin 都没货 → 从 top_chunk 切 / 向内核要

```
                bin 都找不到合适的
                        ↓
        ┌──────────────────────────────┐
        ↓                              ↓
    请求 ≥ 128 KB?                  请求 < 128 KB
   (M_MMAP_THRESHOLD)
        ↓                              ↓
   YES                            从 top_chunk 切
   绕开 arena                     (arena 末端那块"剩饭")
   直接 mmap 一块                       ↓
   独立 VMA                        够 → 切了返回 ✓
   返回 ✓                          不够 → 继续向下
                                       ↓
                            主 arena   |   thread arena
                                ↓      |        ↓
                            brk()      |    mmap() 一块新区域
                            推 program |    挂到 arena 后面
                            break       (子 arena 不能用 brk,
                                         brk 只能服务主 arena)
                                ↓                 ↓
                            从扩出来的新空间切 → 返回 ✓
```

> 这一步对应 **C1 + C2 + C3 + C4** —— 批量向内核要(brk 一次推一大段、mmap 整页)、双通道分粒度(brk 字节级 + mmap 任意可还)、top_chunk 让大多数小请求在用户态就解决,不进内核。

### 步骤 4:`free(p)` 入口 —— 反向偏移找 chunk header

```
应用调 free(p)
   ↓
p 不是 chunk 起点!chunk 在 p 之前几个字节
   ↓
反向偏移读 chunk header:
   ┌─────────────────────────────────────┐
   │  prev_size  │ size + 3 个标志位     │  ← header (这就是 user 推的"必须记账")
   ├─────────────────────────────────────┤
   │           user data (← p 指向这里)   │  ← user data 起点
   └─────────────────────────────────────┘
   ↓
从 size 字段拿到 chunk 大小 → 化解 C5(free(p) 不传 size 也能知道大小)
从标志位 NON_MAIN_ARENA 拿到所属 arena → 化解锁定问题
   ↓
拿 arena 锁
```

> **chunk header 的 3 个标志位**(都塞在 size 字段的低 3 位 —— 因为对齐到 8 字节,低 3 位本来就是 0,能复用):
> - `PREV_INUSE`(bit 0):前一个 chunk 是不是在用?用于判断能否向前合并
> - `IS_MMAPED`(bit 1):本块是不是 mmap 来的?用于决定 free 是直接 munmap 还是挂回 bin
> - `NON_MAIN_ARENA`(bit 2):本块属于主 arena 还是线程 arena?用于查锁
>
> **size + 3 个标志位塞同一个 word** —— 这是 ptmalloc2 最经典的位压缩技巧,精确化解了 C5(只 1 个指针定位 + 全部元数据)。Deep 阶段会精确剖析。

### 步骤 5:合并 + 挂回 bin + **默认不还内核**

```
chunk 标 free
   ↓
检查物理上前后相邻的 chunk:
    前一个 free?(看 PREV_INUSE 标志位)→ 向前合并
    后一个 free?(顺指针检查)         → 向后合并
   ↓
合并后的大 chunk 选择目的桶:
    走 mmap 路径(IS_MMAPED=1)? → munmap() 立即还内核
    本块 < 64 B?                  → fastbin(不合并、最快)
    其他?                         → unsorted bin(临时位置)
   ↓
默认就停在这 ✗ 不还内核
   (要真正还,要么走 mmap,要么调 malloc_trim 主动收缩 brk)
```

> 这一步对应 **C2 + C3 + C6** —— 合并降低碎片;默认不还内核,因为 syscall 贵 + brk 物理上还不掉中间块(只能末尾整体回缩)。

---

## 一个最小伪代码 demo(40 行,串起 5 步骨架)

```c
// 简化的 malloc 伪代码 —— 真实 ptmalloc2 复杂得多,但骨架就是这个
void *malloc(size_t n) {
    arena_t *a = get_thread_arena();        // 步骤 1: 找 arena (C7)
    lock(a->mutex);

    // 步骤 2: 查 bin (C6 分桶 + C1 快路径)
    chunk_t *c = NULL;
    if (n < FASTBIN_MAX) c = fastbin_pop(a, n);
    if (!c)              c = unsorted_bin_search(a, n);
    if (!c)              c = smallbin_or_largebin_search(a, n);
    if (c) { unlock(a->mutex); return chunk_to_userptr(c); }

    // 步骤 3: top_chunk / brk / mmap (C1+C2+C3+C4)
    if (n >= M_MMAP_THRESHOLD) {              // 大块走 mmap
        c = mmap_new_chunk(n);                // IS_MMAPED=1
    } else if (a->top_size >= n) {            // 从 top_chunk 切
        c = split_top_chunk(a, n);
    } else if (a == &main_arena) {            // 主 arena 用 brk 扩
        a->top = brk_extend(a->top, EXTEND_SIZE);
        c = split_top_chunk(a, n);
    } else {                                  // 线程 arena 用 mmap 扩
        a->top = mmap_extend(a->top, EXTEND_SIZE);
        c = split_top_chunk(a, n);
    }
    unlock(a->mutex);
    return chunk_to_userptr(c);
}

void free(void *p) {
    chunk_t *c = userptr_to_chunk(p);         // 步骤 4: 反向偏移 (C5)
    arena_t *a = chunk_arena(c);              // header 标志位查 arena
    lock(a->mutex);

    if (c->size & IS_MMAPED) {                // 例外:mmap 块直接还
        unlock(a->mutex);
        munmap_chunk(c);
        return;
    }

    c = coalesce_with_neighbors(a, c);        // 步骤 5: 合并 (C6)
    if (c->size < FASTBIN_MAX) fastbin_push(a, c);
    else                       unsorted_bin_push(a, c);
    unlock(a->mutex);
    // 默认就停在这,不还内核 (C2+C3)
}
```

读完这段你应该能指着每一行说"这一行对应到 Cn 或第 X 层推理"。**ptmalloc2 几万行源码,结构上就是这个伪代码的真实工程化** —— 复杂度的来源是:边界条件、性能优化、多种安全检查(防 double free / chunk overflow / use-after-free)。骨架本身并不复杂。

---

## 一张对比图:朴素方案 vs glibc 的 malloc

| 维度 | 朴素方案 | glibc 的 malloc | 对应约束 |
|------|---------|----------------|---------|
| 每秒 10⁵ 次小分配的 syscall 数 | 10⁵ 次 | ~10² 次(批量) | C1 + C2 |
| free 之后中间块还内核 | 做不到(brk 限制) | 不还,挂回 bin 等复用 | C3 |
| 碎片管理 | 程序员自己 | bin 分桶 + 合并 | C6 |
| 24 字节小请求的真实物理占用 | 4 KB(mmap 整页,170× 浪费) | ~32 字节(brk 字节级) | C4 |
| 1 MB 大请求的释放 | brk 路径还不掉中间 | mmap 路径 munmap 立即还 | C3 + C4 |
| 多线程 malloc 并发 | 应用层自己锁 | arena 多池自动减竞争 | C7 |
| free(p) 不传 size 怎么知道大小 | 不知道 | 反向偏移读 chunk header | C5 |

每一行差异都对应 Why 阶段某条 Cn 的具体化解。

---

## 三个常见误解

### 误解 1:`free(p)` 之后这块内存就还给操作系统了

**真相**:**默认不会**。free 只是把 chunk 挂回 arena 的 bin / fastbin / unsorted bin,等下次 `malloc(...)` 复用。**例外**只有两个:
- 这块原本走 mmap 路径(IS_MMAPED=1)→ 立即 `munmap` 还
- 主动调 `malloc_trim()` → ptmalloc2 检查 heap 末尾连续空闲段,收缩 brk

这就是为什么生产环境里"明明 free 了内存,top 里 RSS 纹丝不动"是常态 —— 不是泄漏,是**故意攥着等复用**。

### 误解 2:malloc 内部就一个全局空闲表,所有线程共享

**真相**:有多个 **arena**,每个独立维护自己的 4 类 bin、top_chunk、heap 段。多线程下,锁的粒度是 **arena 级**(不是全局)—— 这就是为什么多核 malloc 不会被一把全局锁卡死。

但 arena 数量**有上限**(典型 `8 × CPU 核数`,可改 `M_ARENA_MAX`)。线程数远超这个数,会触发 arena 复用,锁竞争就回来了 —— 这是 ptmalloc2 跟 jemalloc / tcmalloc 的核心权衡差异。Comparison 阶段会展开。

#### 为什么偏偏是 `8 × CPU 核数`?(用「因为 → 要解决 → 所以引入」推一遍)

**因为**:arena 太少 → 多线程锁竞争重(线程远多于 arena → 抢同一把锁 → 退回全局锁时代);**arena 太多** → 每个 arena 独立持有自己的 heap 段 + bins + top_chunk,而且 **arena 之间的空闲块无法跨 arena 复用**(锁分离的代价就是空闲表也分离)→ arena 数翻倍 → RSS 接近翻倍 + cache locality 变差。

**要解决**:在"减锁竞争"和"控制内存膨胀"之间找一个不严谨但够用的折中点 —— 让大多数 workload 下:① 锁竞争已经摊到几乎看不见;② arena 数仍然小到 RSS 不爆。

**所以引入**:经验拍板的常数 **8**(64 位 `M_ARENA_MAX` 默认值;32 位是 2,因为 32 位地址空间紧)。**没有任何严格推导**,就是工程经验值 —— 类似 Linux 内核里大量 magic number。来源是 ptmalloc2 源码 `malloc/arena.c` 中的 `__libc_mallopt` 默认逻辑。

#### 超过 `8 × CPU 核数` 的线程数会怎样?

ptmalloc2 **不会**为更多线程开新 arena,而是让新线程**复用**已有 arena —— 找一个最空闲的(arena 之间通过 `next` 链串成全局表),加锁等待。**接受锁竞争,换内存稳定**。

| 操作 | 行为 |
|------|------|
| 1~8×N 个线程(N=核数) | 每个线程拿独立 arena,几乎无锁竞争 |
| 8×N+1 个线程开始 | 新线程复用已有 arena,出现等锁;arena 数到此**停止增长** |
| 1024 个线程,8 核机器(arena 上限 64) | 每个 arena 平均被 16 线程共享,锁竞争中等 |

**典型调优经验**:

- **数百线程的高并发 server**:常调小到 `MALLOC_ARENA_MAX=2~4`(线程已经够多,arena 多了反而 RSS 失控)
- **单线程或少线程的 batch job**:不用调,默认值就够
- **极端**:`MALLOC_ARENA_MAX=1` 退回单池,简单但锁瓶颈
- **想彻底绕开这个权衡**:换 jemalloc(per-CPU arena 而非 per-thread)或 tcmalloc(thread-local cache + 中央堆),两者用不同的方式同时压住 RSS 和锁竞争。Comparison 阶段会精确对比。

### 误解 3:chunk 大小 = 你 malloc 请求的字节数

**真相**:**chunk 实际比你请求的大**。它包含:
- **chunk header**(`prev_size` + `size+标志位`,通常 16 字节)
- **对齐填充**(typical x86_64 对齐到 16 字节边界)

所以 `malloc(24)` 实际占用约 **32 字节**(24 + 16 字节 header,但 header 跟下一块共享部分空间因为 PREV_INUSE 这个 trick)。**精确的 chunk 布局算法是 Deep 阶段的事** —— 但你现在能感觉到为什么需要 header(就是你说的"必须记账")。

---

## 《约束回扣》

How 阶段呈现的每一个组件,**精确对应 Why 阶段某条 Cn 的具体化解**:

| 组件 | 对应约束 | 精确化解方式 |
|------|---------|------------|
| **arena + per-arena mutex** | C7(多核并发) | 锁粒度从全局降到 arena 级 |
| **fastbin / smallbin / largebin / unsorted bin** | C6(碎片管理)+ C1(高频小块) | 分桶 O(1) 查找 + 不同策略对不同 size 范围 |
| **top_chunk** | C1 + C2(批量要,把 syscall 摊薄) | 大多数小请求在用户态就被服务,不进内核 |
| **brk 扩主 arena heap / mmap 扩线程 arena** | C3 + C4(brk 限制 + mmap 整页) | 主 arena 用 brk 字节级 + 线程 arena 用 mmap 任意位置 |
| **chunk header 内联 size + 3 标志位** | C5(free(p) 不传 size) | 反向偏移读 header 拿大小 + arena 信息 |
| **合并相邻 free chunk** | C6(碎片管理) | 减少长跑后的碎片累积 |
| **默认不还内核**(只挂回 bin) | C2 + C3 | syscall 贵 + brk 物理还不掉中间,合理选择不还 |
| **M_MMAP_THRESHOLD = 128 KB** | C3 + C4(双通道分粒度) | 大块走 mmap(可立即还,但浪费 4 KB);小块走 brk |
| **M_ARENA_MAX = 8 × CPU 核数** | C7(并发上限的工程权衡) | 太少 → 锁竞争;太多 → 内存膨胀 + 跨 arena 调度开销 |

所有这些都不是"开发者偏好",每一项都被 C1~C7 中的某条**单向逼出来**。这就是 atlas 把 Why 放在 How 之前的根本原因。

---

## 呼应灵魂问题

你的灵魂问题是:**"malloc 要解决的工程问题是什么?"**

到 How 阶段,这个问题已经能**85% 闭环**回答:

- **工程问题**(Why C1~C7)= 高频小块 + syscall 贵 + brk 还不掉中间 + mmap 整页 + free 接口 + 碎片必然 + 多核并发
- **解法**(你 4 层推理 + 第 5 步隐含)= 用户态记账(链表 → buddy 风格 → 分桶)+ 多池减锁 + 双通道分粒度
- **具体组件**(How)= chunk header 内联元数据 + 4 类 bin + top_chunk + arena × N + brk/mmap 双通道 + M_MMAP_THRESHOLD + 默认不还内核

剩下 **15%** 是 Deep 阶段才会精确化的:

- **chunk header 精确字节布局**(为什么 `prev_size` + `size+flags` 共 16 字节而不是 8 或 32)
- **bin 桶边界的精确数字**(为什么 fastbin 上限 64B、smallbin 边界 512B、largebin 怎么按 size class 分)
- **bin 内部数据结构**(链表 / 双链表 / 还是有索引?)
- **fast path 精确步数**(从 `malloc(24)` 调用到返回指针,经过哪几个函数,几次条件分支)
- **安全防护**(double free 检测、chunk size 校验、tcache 投毒防护 —— 这些是 2017 后的重要演化)
- **多线程高并发下 arena 是否成新瓶颈**(这是 ptmalloc2 vs jemalloc / tcmalloc 的核心战场,Comparison 阶段会展开)

每个问题都会在 Deep 阶段绑定一条具体反事实(如果 fastbin 上限改成 128B 会怎样?如果 chunk header 改成 8 字节会怎样?),用反事实精确量化每个数字背后的设计权衡。

> 一句话:**How 给了你 malloc 的"骨架 + 主要组件"** —— 你现在已经能跟人完整讲清楚 ptmalloc2 大致怎么工作。**Deep 才会精确回答"为什么这个数字是这个、那个数字是那个"** —— 把骨架的所有"具体值"用反事实小试逐一钉死。

---

## 修订记录

| 时间 | 修订摘要 | 触发原因 |
|------|---------|---------|
| 2026-05-02 01:20 | 初稿:接续 Why 4 层推理对应到 ptmalloc2 6 个具体组件(chunk header / 邻接 / 4 类 bin / arena / top_chunk / 双通道阈值);5 步骨架端到端流程;40 行伪代码 demo;朴素方案 vs malloc 7 维对比;3 个常见误解;约束回扣 9 项;呼应灵魂问题(85% 闭环 + 15% 留 Deep) | 阶段开始,接续 Why 完成的 commit |
| 2026-05-02 01:35 | 在「核心机制骨架」之前补加新小节《用户视角凝固:层级关系澄清》:画出进程跨边界的双进程对照图(指令共享 + 状态独立)+ arena/bin/chunk 嵌套层级图(arena 头状态 + bins[] 分桶 + in-use chunks + heap 物理布局 + 内核镜像类比);明确"进程隔离 = 内核责任,arena 多池 = ptmalloc2 责任",澄清没有"glibc 域"这一层 | 用户追问 1: glibc 是不是分进程加载、不同进程互不影响?有没有"域"再划 arena? 用户追问 2: 需要 arena/chunk/bin 三者的关系图 |
| 2026-05-02 01:50 | 在「误解 2」末尾追加两个子节《为什么偏偏是 8 × CPU 核数》和《超过会怎样》,严格按"因为 → 要解决 → 所以引入"链条推导;附 4 行调优经验表 + jemalloc/tcmalloc 的不同解法预告 | 用户追问 3: arena 上限 8 × CPU 核数 为什么是 8 倍?超过会怎样? |
