# 阶段 5:malloc 三条路径源码追踪(glibc 2.34+)

## 约束清单速查(C1~C7)

> 后文所有 `Cn` 引用都对应下面 7 条。Deep 阶段聚焦在**端到端源码追踪**:把前 4 个 stage 累积的所有抽象,**钉死在 glibc 2.34+ 真实 call stack 上**。

#### C1 — 高频小块

应用对动态内存的请求是**高频小块**:每秒 10⁵~10⁷ 次,典型 16~256 字节。
**不可再分**:C++ / 现代脚本运行时的语义现实。
**口诀**:量大频高 → 必须 O(1) 快

#### C2 — syscall 贵

**syscall 至少几百 ns**,比函数调用贵 2 个数量级。
**不可再分**:CPU 特权级机制(SYSCALL/SYSRET、ring 切换)本身的代价。
**口诀**:进内核贵 → 必须批量摊薄

#### C3 — brk 中间还不掉

**`brk` 只能移动 program break**,heap 中间块还不掉。
**不可再分**:brk 语义就是改一个 long,无"还任意一块"能力。
**口诀**:中间还不掉 → 用户态自己攥着

#### C4 — mmap 整页

**`mmap` 最小粒度是一整页**(常见 4 KB)。
**不可再分**:CPU MMU 页表项最细粒度就是一页。
**口诀**:整页 → 小块走它必浪费

#### C5 — free(p) 不传 size

**`free(p)` 只接受指针,不传 size**。
**不可再分(精度升级,见 Origin §2.4.5)**:**技术 + 生态复合** —— 1989 ANSI C ABI + 接口共存让 allocator 必须 worst case 兼容。
**口诀**:不传 size → 必须每块自带元数据

#### C6 — 碎片必然

**长跑应用必然产生碎片**。
**不可再分**:Knuth 50% 规则。
**口诀**:碎片必然 → 必须有合并机制

#### C7 — 多核并发

**必须支持多线程并发分配/释放**。
**不可再分(精度升级,见 04-origin.md §5.5)**:**时代性约束** —— 1996 浮现,2017 加深,2026+ 在 async 反向演化。
**口诀**:多核 → 必须减锁竞争

---

## §0 从 Origin 走到 Deep:三件事记住

Origin 阶段你看到了"组件随时代叠加";Deep 阶段回答另一个问题:**那些抽象组件怎么落到一次真实的 `malloc()` 调用里?glibc 2.34+ 的源码里,call stack 长什么样?**

How 给了你三件事(chunk / bin / arena);Origin 告诉你这三件事是 40 年叠加的。**Deep 把这一切固定到一次具体的 alloc/free 上,看真实的 call stack**。

不挑独立机制做反事实(那是机制视角),而是**挑三个有代表性的 size**,让它们走完全不同的路径。三个 size 选得很精心 —— 它们对赌了 ptmalloc2 三个不同的假设:

### §0.1 一次 alloc 的"路径"是 ptmalloc2 设计的最佳测量尺

ptmalloc2 不是单一算法,**是三条主路径 + 复杂的 fallback 网络**。哪条路径触发取决于 size + 当前 arena 状态:

- size **在 [16, 1032]B** → tcache 优先(thread-local 无锁,~15 ns 完成)
- size 中等(64B~128KB)+ tcache miss → 走 arena lock + bin search + 必要时 sbrk 扩 heap
- size **≥ 128KB** → 直接 mmap,绕过整个 arena 体系

**真实应用里 90%+ 的请求走 tcache**;剩下的 ~9% 走 brk 中等路径;< 1% 走 mmap。但**这三条路径都得有,缺一不可**。

### §0.2 三条主路径在 size 轴上"对赌不同假设"

每条路径假设了不同的"这次 alloc 长什么样":

| 路径 | 触发 size | 假设的"典型场景" | 对应 [Cn](#c1) |
|-----|----------|---------------|--------------|
| **tcache** | < 1032B,tcache 有货 | 高频小对象循环(`std::string`、STL 节点)| [C1](#c1) + [C7](#c7) |
| **brk** | tcache miss / 中等块 | 长跑应用的稀疏中等分配 | [C2](#c2) + [C3](#c3) + [C6](#c6) |
| **mmap** | ≥ 128KB | 大 buffer 一次性使用,short-lived | [C2](#c2) + [C3](#c3) + [C4](#c4) |

**关键洞察 — 哪条都不能"通吃"**:tcache 不能存大块(thread-local 空间紧);brk 不能立即还(C3);mmap 整页浪费太大(C4)。三条路径**互补三个假设**,组合起来才覆盖整个 size × frequency 空间。

### §0.3 跟踪源码 = 把 §0~§4 的所有抽象固定到具体 call stack

前 4 个 stage 教过的所有概念(chunk header、tcache、bin、arena、`IS_MMAPED` 标志、`sysmalloc`、`brk`、`mmap`)在 Deep 阶段**全部出现在同一段 call stack 里**。读懂三条 call stack = **把 ptmalloc2 整个吸收为肌肉记忆**。

### §0 结论:三件事记住

| | 关键事实 | 为什么重要 |
|---|--------|----------|
| **三条主路径** | tcache(无锁)/ brk(arena 锁 + sbrk)/ mmap(独立 syscall) | 一次 alloc 走哪条,完全由 **size + tcache 状态** 决定 |
| **size 对赌假设** | <1032B 假设小高频;[64B,128KB] 假设中等长跑;≥128KB 假设大短暂 | 哪条假设错了,那条路径就是性能 / RSS 的瓶颈 |
| **耗时差 ~300x** | tcache ~15 ns;brk ~500 ns;mmap ~5000 ns | 同一个 `malloc()` 调用,差 30~300 倍是常态;**只有看 call stack 才能解释这种差距** |

后面 §2~§5 把三条路径用真实 demo 代码 + glibc 2.34+ 源码逐步追踪;§6 量化对比;§7 约束回扣;§8 呼应灵魂。

---

## §1 三路径 call stack 对比图

§0 给了你三条路径的"为什么有三条";这张图给你**三条 call stack 并列**的横向对比 —— 同一个 `malloc()` 入口,size 一变,路径完全分叉:

![三路径 call stack 对比](pics/05-call-stack-three-paths.svg)

**几件能从图上读出来的事**:

1. **入口都是 `__libc_malloc`** —— 然后立刻按 size + tcache 状态分叉
2. **tcache 路径最短**(~9 个调用,完全在 user space)
3. **brk 路径最长**(~14 个调用,跨 1 次 syscall + 1 次锁)
4. **mmap 路径中等**(~10 个调用,跨 syscall 但**不需锁** —— 因为绕过 arena)
5. **`IS_MMAPED` 标志位**让 free 时能路由回 munmap(C5 化解的精彩之处)

---

## §2 演示代码 + 编译 + 调试

### §2.1 demo 代码

完整可运行 demo 在 `src/05-demo.c`(同目录的 `src/` 子目录),三个场景顺序触发三条路径:

```c
// 场景 1: tcache 路径
void *p1a = malloc(24);  free(p1a);   // 第 1 次:tcache 空,走 _int_malloc 填 tcache
void *p1b = malloc(24);  free(p1b);   // 第 2 次:tcache 命中(~15 ns 无锁)

// 场景 2: brk 路径
void *p2 = malloc(8 * 1024);          // 8KB → tcache miss → _int_malloc → sysmalloc → sbrk
free(p2);                             // → coalesce → unsorted bin push(默认不还内核)

// 场景 3: mmap 路径
void *p3 = malloc(200 * 1024);        // 200KB ≥ M_MMAP_THRESHOLD → mmap syscall
free(p3);                             // → IS_MMAPED → 直接 munmap syscall
```

详细注释 + marker 输出见源文件。

### §2.2 编译

```bash
gcc -O0 -g -o stages/05-deep/src/05-demo stages/05-deep/src/05-demo.c
```

`-O0` 关优化(避免 inline 让追踪变难);`-g` 加调试信息(给 gdb 用)。

### §2.3 strace 追踪 syscall

```bash
strace -e trace=brk,mmap,munmap stages/05-deep/src/05-demo 2>&1 | head -30
```

预期(关键 syscall 节选):

```text
[起步阶段]
brk(NULL)                        = 0x55a...8000      # 取当前 program break
brk(0x55a...22000)               = 0x55a...22000     # 第一次扩 heap(给 main_arena 用)

[场景 1: malloc(24) - tcache - 完全不进内核 - 0 syscall]
write(1, "[MARKER] === scenarios start ===\n", 33) = 33
... (无 brk/mmap 输出 - 全部走 tcache)

[场景 2: malloc(8KB) - 触发 sbrk 扩 heap]
brk(0x55a...24000)               = 0x55a...24000     # 扩 heap 8KB+ overhead

[场景 3: malloc(200KB) - mmap syscall]
mmap(NULL, 204800, PROT_READ|PROT_WRITE,
     MAP_PRIVATE|MAP_ANONYMOUS, -1, 0) = 0x7f...c000  # 独立 VMA,跟 arena heap 分离
munmap(0x7f...c000, 204800)      = 0                  # free(p3) 立即触发
```

**重点观察**:
- 场景 1 完全没有 `brk` / `mmap` 输出 —— 验证了 tcache 不进内核
- 场景 2 触发 1 次 `brk`(扩 heap),**没有 munmap**(free 时不还内核,挂回 unsorted bin)
- 场景 3 触发 1 次 `mmap` + 1 次 `munmap`(IS_MMAPED 立即还)

### §2.4 gdb 关键断点

```bash
gdb stages/05-deep/src/05-demo
(gdb) b __libc_malloc       # 入口
(gdb) b _int_malloc          # arena 路径核心
(gdb) b sysmalloc            # 大块路径(brk/mmap 触发处)
(gdb) b _int_free            # free 入口
(gdb) run
(gdb) bt                     # 看 call stack
(gdb) c                      # 继续到下一个断点
```

---

## §3 场景 1:`malloc(24)` → tcache 路径

### §3.1 触发条件

- `malloc(24)` → checked_request2size(24) = **32B**(24 用户 + 16 chunk header,对齐到 16B)
- `tc_idx = csize2tidx(32) = (32 - 16) / 16 = 1` → 命中 tcache 桶 1
- 假设 tcache->entries[1] 非空(第 2 次或之后的 alloc)→ **直接命中,无锁**

### §3.2 关键源码追踪

#### `__libc_malloc` 入口(简化版)

文件:`glibc/malloc/malloc.c`(2.34+)

```c
void *
__libc_malloc (size_t bytes)
{
  mstate ar_ptr;
  void *victim;

  /* (1) tcache 早期分支 — 在 arena_get 之前就检查 */
  size_t tbytes = checked_request2size (bytes);          /* 24 → 32 */
  if (tbytes == 0) {
    __set_errno (ENOMEM);
    return NULL;
  }
  size_t tc_idx = csize2tidx (tbytes);                   /* 32 → 1 */

  MAYBE_INIT_TCACHE ();                                   /* 首次进入时初始化 thread-local tcache */

  /* (2) 关键路径 - tcache 命中直接返回,完全不走 arena */
  DIAG_PUSH_NEEDS_COMMENT;
  if (tc_idx < mp_.tcache_bins
      && tcache != NULL
      && tcache->counts[tc_idx] > 0)
    {
      victim = tcache_get (tc_idx);
      return tag_new_usable (victim);                     /* MTE 标记后返回 */
    }
  DIAG_POP_NEEDS_COMMENT;

  /* (3) tcache miss,走 arena 慢路径 */
  if (SINGLE_THREAD_P)
    {
      victim = _int_malloc (&main_arena, bytes);
      ...
    }
  ...
}
```

**关键逻辑**:整个 tcache 命中路径**在 `_int_malloc` 之前就 return** —— 完全跳过 arena lock + bin search。

#### `tcache_get_n` —— 真正的 pop 操作

```c
static __always_inline void *
tcache_get_n (size_t tc_idx, tcache_entry **ep)
{
  tcache_entry *e;
  if (ep == &(tcache->entries[tc_idx]))
    e = *ep;                                              /* 直接读 entries[tc_idx] */
  else
    e = REVEAL_PTR (*ep);                                 /* 通过 PROTECT_PTR 解码(防 ROP)*/

  if (__glibc_unlikely (!aligned_OK (e)))
    malloc_printerr ("malloc(): unaligned tcache chunk detected");

  /* 链表 pop:把 entries[tc_idx] 指向下一个 chunk */
  if (ep == &(tcache->entries[tc_idx]))
    *ep = REVEAL_PTR (e->next);
  else
    *ep = PROTECT_PTR (ep, REVEAL_PTR (e->next));

  --(tcache->counts[tc_idx]);                            /* 计数减 1 */
  e->key = 0;                                             /* 清 key 标记(被 alloc 走了)*/
  return (void *) e;
}
```

**关键 trick — `e->key`**:tcache 2.30+ 加的安全防护(CVE 后果)。free 时设 `key = tcache_key`(进程内唯一);再次 free 同一指针时检查 key 命中 → 抛 `double free or corruption (fasttop)`。alloc 时清 0,代表"已被取走,可重新 free"。

#### `tcache_put` —— free 时的 push

```c
static __always_inline void
tcache_put (mchunkptr chunk, size_t tc_idx)
{
  tcache_entry *e = (tcache_entry *) chunk2mem (chunk);

  e->key = tcache_key;                                    /* 防 double free */
  e->next = PROTECT_PTR (&e->next, tcache->entries[tc_idx]);  /* 加密指针 */
  tcache->entries[tc_idx] = e;                            /* 单链表头插 */
  ++(tcache->counts[tc_idx]);
}
```

**整个 push 完全无锁** —— `tcache` 是 `__thread` thread-local,每个线程独占一份,根本不需要 mutex。这就是 [C7](#c7) per-thread 免锁的精髓。

### §3.3 性能特征

- **call stack 深度**:~9 层(`main` → `malloc` → `__libc_malloc` → `tcache_get_n` → `chunk2mem` → return)
- **触摸的 cache line**:tcache 头(1)+ chunk(1)= **2 个 cache line**(都在 thread-local,大概率 L1 命中)
- **syscall 数**:0
- **锁次数**:0
- **典型耗时**:~15 ns(假设 L1 命中)

### §3.4 反事实小试 — 如果没有 tcache 会怎样?

候选 A:回到 glibc < 2.26 的 fastbin-only 时代:
- `malloc(24)` 必须 lock(arena->mutex)→ pop fastbin → unlock
- arena lock 在多线程下是热点(2 cache line miss + 1 atomic)→ ~30 ns
- **2× 慢**;且锁竞争下退化更狠

候选 B:per-CPU 而不是 per-thread(jemalloc 路线):
- 不需要 thread-local storage,但需要 `RDTSCP` 拿当前 CPU(~10 cycle)+ 处理 CPU 迁移(thread 被调度到别的核时,缓存不命中)
- 实测略慢于 per-thread,但 thread 数 >> CPU 数时更稳

候选 C:硬塞所有 chunk size 进 tcache(没有上限):
- 64 桶 × 7 chunk × 1KB 平均 ~= 450KB / 线程 → 1000 线程 = 450MB 浪费
- 上限 1032B 是"覆盖率 vs 内存"的精确折中点

**结论**:tcache per-thread + 上限 1032B + 每桶 7 chunk 是 [C1](#c1) + [C7](#c7) 联合下的局部最优。

---

## §4 场景 2:`malloc(8KB)` → brk 路径

### §4.1 触发条件

- `malloc(8192)` → tbytes = 8192 + 16 = **8208B**
- `tc_idx = csize2tidx(8208) = (8208 - 16) / 16 = 512` —— **远超 `mp_.tcache_bins = 64`** → tcache miss
- size > MAX_FAST_SIZE(默认 64B)→ fastbin 不适用
- size 落在 largebin 范围(≥ 512B)→ largebin search
- 假设 fresh process,largebin / unsorted 都空 → 走 top_chunk
- top_chunk 不够 8208B → 触发 sysmalloc 扩 heap → **`sbrk(SYSCALL)`**

### §4.2 关键源码追踪

#### `_int_malloc` 中等大块路径(简化)

文件:`glibc/malloc/malloc.c`

```c
static void *
_int_malloc (mstate av, size_t bytes)
{
  INTERNAL_SIZE_T nb;       /* normalized request size */
  ...

  nb = checked_request2size (bytes);                    /* 8192 → 8208 */

  /* (1) fastbin 路径 - size > 80 不适用,跳过 */
  if ((unsigned long) (nb) <= (unsigned long) (get_max_fast ()))
    {
      /* fastbin pop ... */
    }

  /* (2) smallbin 路径 - 8208 > 512,跳过 */
  if (in_smallbin_range (nb))
    {
      idx = smallbin_index (nb);
      ...
    }
  else
    {
      idx = largebin_index (nb);                         /* 进入 largebin */
      if (atomic_load_relaxed (&av->have_fastchunks))
        malloc_consolidate (av);                         /* 合并所有 fastbin chunk */
    }

  /* (3) unsorted bin scan - 顺手归位 + 看有没有撞上精确匹配的 */
  for (;; )
    {
      int iters = 0;
      while ((victim = unsorted_chunks (av)->bk) != unsorted_chunks (av))
        {
          ...
          /* 假设 unsorted 空或不匹配,跳过 */
        }

      /* (4) largebin 精确匹配 - 假设无货 */
      if (!in_smallbin_range (nb))
        {
          bin = bin_at (av, idx);
          /* search largebin ... */
        }

      /* (5) use_top - 从 top_chunk 切 */
      victim = av->top;
      size = chunksize (victim);

      if ((unsigned long) (size) >= (unsigned long) (nb + MINSIZE))
        {
          remainder_size = size - nb;
          remainder = chunk_at_offset (victim, nb);
          av->top = remainder;
          set_head (victim, nb | PREV_INUSE);
          set_head (remainder, remainder_size | PREV_INUSE);
          return chunk2mem (victim);
        }

      /* (6) top_chunk 不够 - 触发 sysmalloc */
      else
        {
          ...
          void *p = sysmalloc (nb, av);
          ...
          return p;
        }
    }
}
```

**关键路径**:**unsorted bin scan + largebin search + top_chunk 不够 → sysmalloc**。

#### `sysmalloc` 触发 sbrk 扩 heap(关键片段)

```c
static void *
sysmalloc (INTERNAL_SIZE_T nb, mstate av)
{
  ...
  /* (1) 大块特殊路径 - 200KB+ 走 mmap_chunk(场景 3 走这里) */
  if ((unsigned long) (nb) >= (unsigned long) (mp_.mmap_threshold)
      && (mp_.n_mmaps < mp_.n_mmaps_max))
    {
      char *mm;
      ...
      mm = (char *) (MMAP (0, size, mtag_mmap_flags | PROT_READ | PROT_WRITE,
                           MAP_PRIVATE|MAP_ANONYMOUS|MAP_NORESERVE));
      ...
    }

  /* (2) 中等块走 sbrk 扩 heap(场景 2 走这里) */
  size = nb + (av == &main_arena ? MINSIZE : (HEAP_MAX_SIZE - 1)) + ...;
  size = ALIGN_UP (size, pagesize);
  brk = (char *) (MORECORE (size));                     /* MORECORE 默认就是 sbrk syscall */
  if (brk != (char *) (MORECORE_FAILURE))
    {
      /* 把扩出来的内存挂到 av->top 上 */
      av->top = (mchunkptr) brk;
      ...
    }
  ...
}
```

`MORECORE` 是宏,在 Linux 上 `#define MORECORE sbrk`(`syscall(SYS_brk, ...)`)。

#### `_int_free` 反向追踪(简化)

free 时 `__libc_free` → `_int_free`:

```c
static void
_int_free (mstate av, mchunkptr p, int have_lock)
{
  INTERNAL_SIZE_T size;
  mchunkptr nextchunk;
  ...

  size = chunksize (p);                                  /* 反向偏移读 size 字段 */

  /* (1) IS_MMAPED 路径 - 场景 3 走这里 */
  if (chunk_is_mmapped (p))
    {
      munmap_chunk (p);                                  /* 直接 munmap */
      return;
    }

  /* (2) tcache 路径 - 如果 size 在 tcache 范围,场景 1 走这里 */
  size_t tc_idx = csize2tidx (size);
  if (tcache != NULL && tc_idx < mp_.tcache_bins
      && tcache->counts[tc_idx] < mp_.tcache_count)
    {
      tcache_put (p, tc_idx);
      return;
    }

  /* (3) fastbin 路径 - size 在 fastbin 范围,直接 push */
  if ((unsigned long)(size) <= (unsigned long)(get_max_fast ()))
    {
      fastbin_push (p, av);
      return;
    }

  /* (4) 中等大块路径 - 场景 2 free 走这里 */
  if (!have_lock)
    __libc_lock_lock (av->mutex);

  /* (4a) 检查后一个 chunk - 不是 top */
  nextchunk = chunk_at_offset (p, size);

  /* (4b) 向前合并 - 看 PREV_INUSE 位 */
  if (!prev_inuse (p))
    {
      prevsize = prev_size (p);
      size += prevsize;
      p = chunk_at_offset (p, -((long) prevsize));
      unlink_chunk (av, p);
    }

  /* (4c) 向后合并 - 看 nextchunk 的 IN_USE */
  if (nextchunk != av->top && !nextinuse)
    {
      unlink_chunk (av, nextchunk);
      size += chunksize (nextchunk);
    }

  /* (4d) 挂回 unsorted bin */
  set_head (p, size | PREV_INUSE);
  set_foot (p, size);
  /* link to unsorted bin */
  ...

  if (!have_lock)
    __libc_lock_unlock (av->mutex);
}
```

**关键观察 — 场景 2 的 free 路径**:
1. 反向偏移读 chunk header → `size = 8208` ([C5](#c5) 的化解)
2. `IS_MMAPED` 没设 → 走 arena 路径
3. tcache 范围超 → tcache 不收
4. fastbin 不适用
5. lock arena → 检查相邻 chunk,可能向前/向后合并 ([C6](#c6) 化解)
6. 标 PREV_INUSE,挂回 unsorted bin
7. **不还内核**(默认行为,见 [C2](#c2) + [C3](#c3))→ RSS 不降

### §4.3 性能特征

- **call stack 深度**:~14 层
- **触摸的 cache line**:arena 头(2)+ unsorted/largebin sentinel(2)+ top_chunk(1)+ chunk(1)= **6 个 cache line**
- **syscall 数**:1(`brk` 扩 heap)
- **锁次数**:1(arena->mutex,在 `_int_malloc` 期间持锁)
- **典型耗时**:~500-1000 ns(取决于是否撞上 syscall)

### §4.4 反事实小试 — 如果默认 free 就还内核会怎样?

候选:让 free 8KB 时也调 munmap(`MAP_ANON` 子区域 + munmap)
- ✅ RSS 立刻降,不堆积
- ❌ 下次 malloc(8KB) 必须重新 mmap → +5000 ns syscall
- ❌ 长跑应用每秒 10⁵ 次 alloc/free 8KB → 10⁵ syscall/s = CPU 时间被 syscall 吃掉
- 现实:无人采用(`malloc_trim` 是手动的,默认不开)

**结论**:默认不还内核 = 牺牲 RSS 换 alloc/free 的延迟稳定性。这是 [C2](#c2) + [C6](#c6) 的折中。

---

## §5 场景 3:`malloc(200KB)` → mmap 路径

### §5.1 触发条件

- `malloc(204800)` → tbytes = 204800 + 16 = **204816B**
- `204816 ≥ mp_.mmap_threshold = 131072(128KB)` → 直接走 mmap_chunk
- **不进 arena,不抢锁**

### §5.2 关键源码追踪

#### `sysmalloc` 中的 mmap 分支(从 §4.2 已贴的 sysmalloc 代码摘出)

```c
if ((unsigned long) (nb) >= (unsigned long) (mp_.mmap_threshold)
    && (mp_.n_mmaps < mp_.n_mmaps_max))
  {
    char *mm;
    INTERNAL_SIZE_T size;
    size_t pagesize = GLRO (dl_pagesize);
    bool tried_mmap = false;

    /* size 向上对齐到页边界(204816 → 208896 = 51 pages × 4KB) */
    size = ALIGN_UP (nb + SIZE_SZ, pagesize);

    /* mmap syscall 拿独立 VMA */
    mm = (char *) (MMAP (0, size,
                         mtag_mmap_flags | PROT_READ | PROT_WRITE,
                         MAP_PRIVATE | MAP_ANONYMOUS | MAP_NORESERVE));

    if (mm != MAP_FAILED)
      {
        /* 标志位:这块是 mmap 来的,free 时认得 */
        mchunkptr p = (mchunkptr) mm;
        set_head (p, size | IS_MMAPED);                  /* bit 1 = IS_MMAPED */

        /* 统计 */
        atomic_increment (&mp_.n_mmaps);
        atomic_max (&mp_.max_n_mmaps, mp_.n_mmaps);
        ...

        return chunk2mem (p);
      }
  }
```

**关键 trick — `IS_MMAPED` 标志位**:这个 bit 在 chunk header 的 size 字段 bit 1。free 时看到它就直接走 munmap,不走 arena 路径(详见 §4.2 的 `_int_free`)。

#### `munmap_chunk` —— free 时直接还内核

```c
static void
munmap_chunk (mchunkptr p)
{
  size_t pagesize = GLRO (dl_pagesize);
  INTERNAL_SIZE_T size = chunksize (p);

  uintptr_t mem = (uintptr_t) chunk2mem (p);
  uintptr_t block = (uintptr_t) p - prev_size (p);
  size_t total_size = prev_size (p) + size;

  /* 一致性 check - 防 corruption / fake mmap chunk */
  if (block & (pagesize - 1)) {
    malloc_printerr ("munmap_chunk(): invalid pointer");
    return;
  }

  atomic_decrement (&mp_.n_mmaps);
  atomic_add_relaxed (&mp_.mmapped_mem, -total_size);

  /* 直接 munmap syscall */
  __munmap ((char *) block, total_size);
}
```

**完全绕过 arena**。RSS 立即降回 200KB 之前的水平。

### §5.3 性能特征

- **call stack 深度**:~10 层
- **syscall 数**:**2**(alloc 时 mmap,free 时 munmap)
- **锁次数**:0(完全绕过 arena)
- **典型耗时**:~5000 ns(syscall + 内核 VMA 管理 + 51 个 page table entry 设置)
- **RSS 行为**:alloc 后立即增长 200KB;free 后立即降 200KB(VMA 回收)

### §5.4 反事实小试 — 如果 M_MMAP_THRESHOLD = 1MB 会怎样?

候选 A:阈值 = 1MB
- 200KB 走 brk 而不是 mmap
- ✅ 延迟从 5000ns → 500ns(一次性快)
- ❌ free 后 200KB **不能立即还内核**(brk 中间还不掉,[C3](#c3))→ RSS 累积
- ❌ 长跑应用 RSS 单调增 → OOM
- 现实:无人这么调(动态升级机制让"刚好略超阈值的高频请求"自动适配)

候选 B:阈值 = 16KB(更激进 mmap)
- 16KB+ 都立即还,RSS 控制完美
- ❌ 16KB 请求很高频(典型 buffer)→ 每次 mmap+munmap 要 ~10000 ns → 应用变慢
- ❌ 内部碎片 25%(16KB 请求向上对齐到页 = 16KB,但 chunk overhead 让实际可用变少)
- 现实:32-bit 系统因为地址空间紧,默认就是 16KB(接受这个权衡)

**结论**:128KB(64-bit 默认)是 [C2](#c2) syscall 频率 + [C3](#c3) RSS 控制 + [C4](#c4) 整页浪费 三重约束的精确折中。

---

## §6 三路径性能对比

把三条路径的关键指标并列:

| 维度 | tcache(场景 1) | brk(场景 2) | mmap(场景 3) |
|------|---------------|------------|-------------|
| **触发 size** | < 1032B + tcache 有货 | 中等(64B~128KB)+ tcache miss | ≥ 128KB |
| **call stack 深度** | ~9 | ~14 | ~10 |
| **syscall 数** | **0** | 1(brk)| 2(mmap + munmap)|
| **arena 锁次数** | **0** | 1 | 0 |
| **触摸 cache line** | 2(thread-local) | 6(跨 arena 多区域) | 4(arena + chunk header) |
| **典型耗时** | **~15 ns** | ~500-1000 ns | ~5000 ns |
| **free 后 RSS 变化** | 不变(挂回 tcache) | **不变**(挂回 unsorted) | **立即降**(munmap) |
| **对应主要 [Cn](#c1)** | [C1](#c1) + [C7](#c7) | [C2](#c2) + [C3](#c3) + [C6](#c6) | [C2](#c2) + [C3](#c3) + [C4](#c4) |

**关键观察 — 没有"最优"路径,只有"最匹配场景"的路径**:

- 高频小对象循环 → tcache 完美(15 ns)
- 中等长跑分配(如游戏 entity / 协议 buffer)→ brk 合理(500 ns,RSS 复用)
- 大 buffer 一次性使用(如 jpeg 解码 buffer / 大 log 缓冲)→ mmap 合理(5000 ns,但 free 立即还,长跑无负担)

**三条路径互补对赌不同假设;ptmalloc2 的"通用性"就来自这种互补**。

---

## §7 约束回扣 —— 三路径精确化解 [C1](#c1)~[C7](#c7)

| 路径 | 化解约束 | 化解方式 |
|------|--------|--------|
| **tcache** | [C1](#c1) + [C7](#c7) | per-thread 桶 + 完全无锁 push/pop;高频小块的最快路径 |
| **brk(arena)** | [C1](#c1) + [C2](#c2) + [C3](#c3) + [C6](#c6) + [C7](#c7) | 多 arena 减锁;sbrk 一次扩一大段摊薄 syscall;不还内核避免 brk 限制;合并相邻 free chunk |
| **mmap** | [C2](#c2) + [C3](#c3) + [C4](#c4) | 大块走 mmap 立即还;syscall 频率低(大块本来就不多);整页浪费率低(200KB / 4KB = 0.4%)|
| **chunk header 16B + 标志位** | [C5](#c5) | free(p) 反向偏移读 size + 标志位决定路由(IS_MMAPED 区分 mmap/arena 路径)|
| **arena 64MB 对齐 + NON_MAIN_ARENA bit** | [C5](#c5) + [C7](#c7) | free 时 O(1) 反查 chunk 所属 arena |
| **fastbin / unsorted / smallbin / largebin** | [C1](#c1) + [C6](#c6) | brk 路径中,4 类 bin 按"刚 free 时序 + size 大小"双维加速查找 |

**所有这些都是被 [C1](#c1)~[C7](#c7) 单向逼出来的**。三条路径不是"算法选择",而是"约束倒逼出的必然分叉"。

---

## §8 呼应灵魂问题

你的灵魂问题:**"malloc 要解决的工程问题是什么?"**

走完 What → Why → How → Origin → **Deep**,这个问题已经**100% 闭环**:

- **是什么**:用户态高效动态内存分配
- **为什么**:7 条不可再分硬约束 [C1](#c1)~[C7](#c7)
- **怎么工作**:chunk(物理)+ bin(索引)+ arena(容器)三件事 + 5 步骨架
- **怎么来的**:1987 dlmalloc → 2006 ptmalloc2 → 2017 tcache 三代叠加(约束随时代浮现)
- **真实 call stack 长什么样**(本阶段):**三条主路径** —— tcache(~15 ns 无锁)/ brk(~500 ns + arena 锁 + sbrk)/ mmap(~5000 ns 双 syscall)

### Deep 阶段最大的认知收益

1. **从"知道有什么"升级到"看见怎么走"** —— 你能 trace 一次具体 alloc 经过的每个函数,每行源码触发哪个分支
2. **抽象组件落到地面** —— chunk header / IS_MMAPED 位 / arena lock / tcache_put 这些 Origin/How 阶段反复说的概念,在 Deep 阶段全部出现在同一段 call stack 里
3. **size 是 ptmalloc2 的"路径选择器"** —— 一个简单的 `size_t bytes` 参数,经过 3 个判断分支(tcache_bins / fastbin / mmap_threshold),路径完全分叉
4. **demo + strace + gdb 三件套**(`src/05-demo.c`)—— 让"理论"可被验证,**任何关于 ptmalloc2 路径行为的疑问都能跑代码验证**

### 灵魂问题的最终答案

**malloc 要解决的工程问题** = **在 7 条硬约束下,用同一个 `void *malloc(size_t)` 接口,把 size × frequency × 多线程的整个空间合理覆盖**。三条主路径(tcache / brk / mmap)是这个覆盖问题的工程解。**没有任何一条路径单独够用 —— 它们组合起来才是 malloc**。

到这里,你已经能跟人完整聊清楚 malloc 的所有层次:
- What:它是什么
- Why:为什么必须存在
- How:怎么工作的(三件事)
- Origin:怎么来的(三时代叠加)
- **Deep:真实的 call stack 在源码里长什么样**(本阶段)

下一步可选 → **Comparison**(横向对比 jemalloc / tcmalloc / mimalloc)或 **Synthesis**(收束方法论)。

---

## 修订记录

| 时间 | 修订摘要 | 触发原因 |
|------|---------|---------|
| 2026-05-02 17:30 | 初稿(第 2 轮重启):严格按新「Stage 开场对齐纪律」(渐进式 + 追加 reconfirm)对齐 6 个维度后才生成。聚焦三场景源码追踪 vs 第 1 轮的"6 机制独立反事实"。§0 三件事 = 三条主路径(tcache 无锁 / brk arena+sbrk / mmap 独立 syscall)+ size 对赌假设;§1 SVG 三 call stack 并列对比图;§2 demo + 编译 + strace + gdb 调试;§3-§5 三条路径源码追踪(每路径含 §X.1 触发条件 + §X.2 关键源码 + §X.3 性能特征 + §X.4 反事实);§6 三路径性能对比表;§7 约束回扣;§8 呼应灵魂(100% 闭环);demo 在 src/05-demo.c(可运行 + strace 验证)| 用户在 Deep 第 2 轮渐进式对齐:聚焦 + 端到端源码追踪 + 三场景(24B/8KB/200KB)+ alloc+free + glibc 2.34+ + 可运行 demo;追加 reconfirm 后 OK |
