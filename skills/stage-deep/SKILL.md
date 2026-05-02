---
name: atlas-stage-deep
description: atlas 套件的 Deep 阶段教学子 skill。从 How 阶段的"骨架级理解"切到"机制级精确理解"——三层剖析(操作层 / 函数逻辑层 / 底层原理层)、端到端场景时间线、每个核心机制后的"反事实小试"。讲完调用 three-options,然后进入 Comparison Hook(询问是否横向对比)。仅由 atlas 入口 SKILL.md 调度时使用,不应被独立调用。
---

# atlas / stage-deep

## 阶段目标

从 How 阶段的骨架,切到**机制级精确理解**——每个核心机制都要能解释"为什么这样设计 + 付出了什么代价 + 还能怎么设计"。

这是 atlas 教学流的最重段(600~900 行)——也是最容易膨胀的段。**严格控制在 900 行以内**,超过就是没分清主次。

---

## 讲解结构(600~900 行)

输出到 `stages/05-deep/05-deep.md`(每个 stage 一个顶层目录,自包含 — 详见入口 SKILL.md「图示偏好 / 文件位置约定」):

```markdown
# 阶段 5:<主题> 的深度剖析

## 三层剖析

### 操作层(Operation Layer)
[用户/调用方视角:API、配置、使用模式]

要求:
- 每个核心 API / 配置项配伪代码或示例
- 说明常见用法与注意事项
- 用约束编号交叉引用(如"这个 API 的设计对应 C5")

### 函数逻辑层(Function Logic Layer)
[关键函数/方法的内部逻辑、调用链、数据流转]

要求:
- 关键函数逐一剖析(入参 → 处理 → 出参)
- 用 ASCII 流程图表示调用链
- 标注关键设计决策

### 底层原理层(Underlying Principle Layer)
[内核原语、系统调用、硬件特性、为什么这样设计]

要求:
- 涉及的内核原语、syscall、硬件特性
- 为什么这样设计(trade-off 分析)
- 用约束编号交叉引用代价

## 端到端场景时间线
[选 1~2 个典型场景,用时间线叙事描述完整生命周期]

```
T=0ms   [组件A] 触发事件 X
T=1ms   [组件B] 接收并处理 → 状态变更
T=5ms   [内核]  执行系统调用 Y
...
```

## 可运行演示代码(必备)

**Deep 阶段必须配套生成可运行 demo**,跟时间线 / 反事实小试形成"理论 + 实证"配对。读者**能编译能运行**才算把"机制"从概念落到地面。

### 输出位置

`stages/0X-stage/src/0X-demo.<ext>`(扩展名跟主题对应:malloc → `.c`;Java GC → `.java`;Go runtime → `.go`;Linux 调度 → 可能是带 `Makefile` 的内核模块或 perf script)。

如果 demo 不只一个文件(比如内核模块需要 Makefile + .c),`stages/0X-stage/src/` 下直接放完整可运行包(多文件树)。

### demo 内容要求

1. **触发本阶段讲解的具体路径** —— 每个场景 / 每个核心机制至少有一段最简代码触发它的源码路径
2. **可编译 + 可运行** —— 给出**具体编译指令**(如 `gcc -O0 -g demo.c -o demo`)+ **依赖说明**(glibc / libc 版本、内核版本、CPU 特性等)
3. **配套调试 tips**(critical):
   - 运行命令(可能含 env var,如 `MALLOC_TRACE=trace.log ./demo`)
   - 期望输出 / 观察方式(RSS 变化用 `/proc/<pid>/status`、syscall 数用 `strace`、cache miss 用 `perf stat`)
   - 调试推荐(`gdb` 设源码断点位置,如 `b _int_malloc`)
4. **代码注释贴源码 path** —— 关键行用注释标注它会触发哪段源码,用 `→` 链给出 call stack:
   ```c
   void *p1 = malloc(24);   // → __libc_malloc → tcache_get → return
   free(p1);                // → __libc_free → tcache_put(无锁 thread-local)
   ```

### 配套源码追踪小节

每段 demo 代码后面跟一节"**源码逐步追踪**":贴 glibc 关键函数 50~150 行原文(不要全文,挑关键段),逐句解释或用 inline 注释。读者把 demo 跑起来 + 看追踪 = 能完整理解一次内存分配的真实路径。

### 例(malloc 主题三场景)

`stages/05-deep/src/05-demo.c`:
```c
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

int main(void) {
    // 场景 1: tcache 命中(thread-local 无锁,~15 ns)
    void *p1 = malloc(24);                   // → __libc_malloc → tcache_get
    free(p1);                                // → __libc_free → tcache_put

    // 场景 2: brk 路径(走 arena,fastbin/tcache miss → unsorted/largebin → top_chunk → sbrk)
    void *p2 = malloc(8 * 1024);             // 8KB,走 brk → _int_malloc → sysmalloc
    free(p2);                                // → 标 free,合并相邻,挂回 unsorted bin

    // 场景 3: mmap 路径(超 M_MMAP_THRESHOLD = 128KB)
    void *p3 = malloc(200 * 1024);           // 200KB → sysmalloc → mmap syscall
    free(p3);                                // → IS_MMAPED 标志位 → munmap syscall

    return 0;
}
```

编译运行:
```bash
gcc -O0 -g stages/05-deep/src/05-demo.c -o stages/05-deep/src/05-demo
strace -e trace=brk,mmap,munmap ./stages/05-deep/src/05-demo
```

期望 syscall 输出(典型):
```
brk(NULL)             = 0x55...           # arena 初始化触发
brk(0x55...8000)      = 0x55...8000       # 场景 2 触发 sbrk 扩 heap
mmap(NULL, 204800, ...) = 0x7f...         # 场景 3 触发 mmap
munmap(0x7f..., 204800) = 0                # 场景 3 free 触发 munmap
```

## 反事实小试(每个核心机制后)
"如果不这样设计,还能怎么做?"

要求:
- 至少 2~3 个候选方案
- 每个候选标明:违反的约束 + 代价 + 现实里有没有人这么做
- 结论:在当前约束组合下,<主题> 的选择是局部最优

例:
> ### 反事实小试:为什么 chunk 内联 16B header,不放到外部哈希表?
> 
> - **候选 A**:外部哈希表(指针 → 大小映射)
>   - 违反 C1:每次 free 多一次 cache miss + 哈希计算
>   - 致命伤:哈希表自己要管理内存(无限递归)
>   - 现实:无人采用
> 
> - **候选 B**:固定 size class(所有分配按档对齐)
>   - 不违反 C5(指针 → size class 可以用页表反查)
>   - 代价:内部碎片放大、不适合任意大小
>   - 现实:jemalloc / tcmalloc / mimalloc 都部分采用
> 
> - **候选 C**:让 free 接口带 size 参数(消解 C5)
>   - 完全消解 C5
>   - 但需要语言层面 ABI 支持(C 改不动)
>   - 现实:Rust(sized dealloc)、C++17 sized deallocation
> 
> **结论**:在 C 语言 ABI(C7)给定的前提下,chunk 内联 header 是 C1+C5 联合
> 下的局部最优。但如果允许改 ABI,候选 C 是更优解——这就是为什么现代分配器在
> Rust 上能更精简。

## 《约束回扣》
[Deep 阶段的每个核心机制对应到约束清单的哪几条 + 代价]

要求:
- 一段话(150~200 字)
- 把本阶段所有重要机制串成"约束-决策-代价"的小型表

## 呼应灵魂问题
[精确回答灵魂问题]

Deep 阶段是大部分灵魂问题的精确回答位置。如果到这里灵魂问题仍未完全回答,
说明 Deep 阶段挑选的剖析重点没对准——需要在「换角度」中调整。
```

---

## 执行流程

1. **静默标记阶段开始**(调用 progress-tracker,对话不提)
2. **从 PROGRESS.md 读取约束清单 + 灵魂问题**(本阶段大量交叉引用)
3. **渐进式对齐**(必做,一问一答到收敛 —— 见入口 SKILL.md「Stage 开场对齐纪律」)

   Deep 阶段最容易膨胀,对齐尤其关键。典型**第一个问题(最高层方向性)** 示例:

   > "Deep 阶段你想要的是 **全景**(覆盖 5~8 个机制,每个三层剖析 + 4 反事实候选,~900 行)还是 **聚焦**(挑 2~3 个机制,每个钉死所有反事实,其他机制只列局部最优 + 反例,~500 行)?"

   根据回答**自然展开下一个**。可能的展开链:
   - 答聚焦 → "挑哪 2~3 个机制?(基于前 4 个 stage,你最想钉死哪些具体数字?)"
   - 答全景 → "5~8 个机制范围你想要 Claude 自动挑(基于 How 引出的"具体数字"清单),还是你来报想看哪几个?"
   - 用户报机制 → "反事实小试每个机制做 4 候选(标准)还是 6 候选(更穷举)?"
   - 用户答 → "要不要 ns 级时间线阶梯(L1 tcache ~ L5 mmap 五档耗时对比)?还是文字描述够?"
   - 用户答"够了" → **进入"追加 reconfirm"**(不要立刻写;按入口 SKILL.md「追加 reconfirm」明确问"我已经清楚目标了 —— 你还有什么问题要追加吗?如果没有我就去写 stages/05-deep/05-deep.md 了")

   **严禁一次列 5 个**;**严禁 Claude 觉得清楚了就直接写**。收敛信号:用户的深度档 / 机制清单 / 反事实粒度 / 时间线偏好都已明确,**且用户明确说"没有追加,可以写"**。

4. **生成 stages/05-deep/05-deep.md** 第一稿(根据用户答的对齐口径决定挑几个机制 / 反事实做多少)
5. **在对话中自然地讲清楚关键剖析点 + 抛反事实反问**(不说"Deep 阶段已写入..."):
   ```
   把源码层的精确剖析放在了 atlas-output/.../stages/05-deep/05-deep.md。
   挑了 X 个最核心的机制三层剖析,每个后面都做了一次反事实小试。

   想用一个反事实拷问你:<反问,例如"如果 chunk header 不存在,会怎么样?">
   ```
6. **进入 user-pacing 协议**(skills/three-options/SKILL.md):
   - 追问 / 新视角 / 不懂 → 答 + **patch stages/05-deep/05-deep.md** + 抛新反问
   - 明确推进信号 → 加载 `skills/stage-comparison/SKILL.md`(它会先问"是否要对比"),自然过渡

---

## 注意事项

- **严格控制 900 行**——超过说明没分清主次,需要砍
- **反事实小试是 Deep 阶段的灵魂**——每个核心机制后都要有,这是与 deeparch-md 最大的差异
- **约束编号交叉引用**——每个机制至少标 1 个 Cn
- **机制要"精确"而不是"全面"**——挑 5~8 个最关键的机制深入,不是把所有机制都讲

---

## 反模式

1. **不做反事实小试** —— 退化成 deeparch-md,失去 atlas 价值
2. **超过 900 行** —— 没分清主次,需要砍
3. **机制太多每个都浅** —— 应该挑 5~8 个核心机制深入
4. **不交叉引用约束编号** —— 散了脊梁
5. **不精确回答灵魂问题** —— Deep 是灵魂问题的精确回答位置,缺这步整个学习无锚点
6. **没有可运行 demo 代码** —— Deep 必备 `stages/0X-demo.<ext>`,给读者能编译能运行的实证。有时间线 + 反事实但没 demo 就停在概念层面,落不了地。详见上文《可运行演示代码》
