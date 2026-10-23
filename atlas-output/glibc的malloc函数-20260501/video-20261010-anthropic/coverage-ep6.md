# 第六集覆盖与事实核对

输入：`../glibc的malloc函数-atlas.md`，第六篇，原始行 2629—3280。
本稿为全新起草，未读取或复用旧 VMD；保留源文问题、推导与结论，源 MD 未修改。
输出：`glibc-malloc-ep6-comparison.vmd`，24 场景，7 种视觉，口播及自动朗读 example 合计 3675 非空白字符；按 7.3 字/秒加场景缓冲，约 9 分钟。
角色：比较与决策。主问题：相近约束为什么存在多条不同路线，怎样按负载权重选择？

## 推导草图

- 锚点：少量线程的普通程序与数百线程长跑容器，使用相同分配接口却重视不同指标。
- 本质问题：成本在缓存、共享协调、尺寸反查和页归还之间怎样交换？
- 旧方案：ptmalloc 在兼容接口下组合多大小索引、多 arena、线程缓存与系统资源路径。
- 击穿约束：线程数量、跨线程释放比例和峰值预算改变默认取舍的权重。
- 抽象：局部化缓存 + 批量共享补退 + 独立的信息契约和归还机制。
- 预测：线程缓存总量随线程分布变化；CPU/P 缓存改变所有权单位；带布局释放提供更多信息，却不必改变后端。
- 验证：官方 jemalloc、两条 TCMalloc、mimalloc、Go、Rust 文档核对组织与版本。
- 边界：同名项目与版本不能混用；容器总预算不是局部分配器的免故障承诺。
- 迁移：先列约束权重与指标，再测量，写明回退和撤销条件。

## 逐节覆盖

| 原文必讲项 | 工程载体与验证 | VMD 场景 | 处理 |
|---|---|---|---|
| §0.1 同问题不同解与基线 | 双栏负载、成本方向 | 2、4、23 | 保留；Layout 明确为接口契约 |
| §0.2 六维比较 | 元数据、所有权、碎片、释放、负载、预算 | 3、18、19 | 保留；从属性列表转为可观测问题 |
| §0.3 容器维度 | 四层内存账与预算边界 | 15、20、21 | 保留；删除绝对免 OOM 保证 |
| §1.1 ptmalloc 动机与优劣 | 兼容、混合大小、缓存、条件归还 | 4 | 保留主链；删除无证据的线程数胜负阈值和产品默认名单 |
| §1.2、§3.1 jemalloc | 人物、arena/cache、percpu 配置、decay | 5—7 | 保留；percpu 默认 disabled，不再误写默认 CPU 关联 |
| §1.3、§3.2 TCMalloc | 人物、两仓库对照、三层补退 | 8—10 | 保留；区分 gperftools per-thread 与现代 Google per-CPU |
| §1.4、§3.3 mimalloc | 合著研究、页本地链、远端交接、purge | 11—13 | 保留；不把全路径写成无同步，不固定总行数 |
| §1.5、§3.4 Go | per-P mcache/mcentral/mheap、GC、软限制 | 14—15 | 保留；P 不等同 goroutine/OS thread/物理核 |
| §1.6、§3.5 Rust Layout | C/Rust 契约对比、System 与可换后端 | 16—17 | 保留；接口给信息≠所有后端已删元数据 |
| §1.7 复述精确度、时间压缩 | 所有权单位核对、早期机制不由晚期产品“发明” | 4、6、8、9 | 保留元教训；原文修订自身不再作不可检验的事实来源 |
| §2 SVG 设计空间 | `pics/06-design-space-map.png`；主控校准表 | 18 | 完整展示；保留独立维度问题，不固化错误坐标 |
| §4.1 元数据/锁/碎片/释放契约 | 组织对照和后端边界 | 3、6、9、10、12、14、16—19 | 主链全部保留，拆成多个窄图 |
| §4.2 应用域与部署 | 条件选型、公平实验、预算 | 19—21 | 保留工程需求；品牌部署名单留在源文，不朗读不准确默认断言 |
| §5.1 容器三问 | 活对象、缓存、整页、计费 | 20 | 保留并区分 RSS、allocator 统计、cgroup 口径 |
| §5.2 各路线归还 | trim/mmap、decay、purge、Go limit、Rust 后端 | 4、7、13、15、17、20 | 保留；具体参数仅讲官方核对项，未执行任何部署改动 |
| §5.3 分层职责 | 预算输入、机制、观测、回退 | 21 | 保留；从“永不允许底层感知”校为责任与信息边界 |
| §6.1 五条平行演化 | 单一排名失效、不同成本交换 | 2、19、23 | 保留 |
| §6.2 三条元规则 | 新契约/接口共存/层级责任 | 16—17、21—22 | 保留；最终归并四规则见第七集 |
| §6.3 新负载重估 | 设备内存/异步的约束变化 | 第七集 15 | 系列跨集明确保留；不伪造“Tokio独立allocator”结论 |
| §6.4 空白象限 | 64+16 简化账、正交检查、历史迁移 | 22 | 保留；余量很小时元数据也可能触发 OOM，不能保证不会 |
| §7 C1 高频小块、C7 并发 | 本地缓存与批次、所有权变化 | 3、4、6、9、10、12、14 | 保留 |
| §7 C2 调用成本、C3 堆尾、C4 页粒度 | 条件归还与整页清退 | 4、7、13、20 | 保留；全文机制推导前五集已充分展开，本集比较成本方向 |
| §7 C5 释放信息 | 块头、页映射、布局契约 | 4、10、16—18 | 保留；编号 C5 配 sidebar |
| §7 C6 碎片 | 规格与整页可归还条件 | 3、7、19、20 | 保留；不把统计规律当任意负载严格定理 |
| §8 灵魂问题与认知收益 | 条件选择一图流 | 23、24 | 保留；自然预告 Synthesis |

## 一手核对来源与纠错边界

核对日期：2026-10-10。版本默认只用于说明对应官方文档，不对用户部署作推断。

- [jemalloc 官方手册](https://jemalloc.net/jemalloc.3.html)：多 arena、线程 tcache、可选 percpu；percpu_arena 默认关闭；dirty 默认 10 秒渐进 decay；muzzy 默认参数并非原文的 10000。保留路线而不照搬旧默认。
- [Google TCMalloc 设计](https://google.github.io/tcmalloc/design.html)：支持 per-CPU 和 legacy per-thread；前端/中间/后端与批量补退；unsized 释放可通过 pagemap 找信息。现代代码不是所有 gperftools 参数的目标。
- [gperftools TCMalloc 设计](https://gperftools.github.io/gperftools/tcmalloc.html)：经典线程缓存路线。未核实的 Chrome/ClickHouse 当前默认断言不进入口播。
- [Microsoft mimalloc 论文](https://www.microsoft.com/en-us/research/publication/mimalloc-free-list-sharding-in-action/)：Daan Leijen、Ben Zorn、Leonardo de Moura，2019；三种页本地空闲链与维护节奏。
- [mimalloc 官方 README](https://github.com/microsoft/mimalloc)：跨线程释放有原子操作；清退常保留虚拟范围；当前 v3 purge delay 默认 1000ms，原文 100ms 不可作跨版本结论。删除“.NET 6+ 全面默认/整个 Rust 社区主流默认”的无证据断言。
- [Go GC 官方指南](https://go.dev/doc/gc-guide)：GOMEMLIMIT 自 Go 1.19 提供，显式软限制；口径不是进程 RSS，原生资源可能在外，预算过低会增 GC 压力。
- [Go runtime malloc 源码注释](https://go.dev/src/runtime/malloc.go)：mcache/mcentral/mheap 与 per-P 组织。GC 不消灭全部元数据。
- [Rust GlobalAlloc](https://doc.rust-lang.org/std/alloc/trait.GlobalAlloc.html)、[Layout](https://doc.rust-lang.org/core/alloc/struct.Layout.html)、[System](https://doc.rust-lang.org/std/alloc/struct.System.html)：布局匹配契约与不安全接口；Layout 不是独立实现；System 依平台；安全代码可泄漏，不能说绝不 leak。
- [glibc 调节参数](https://sourceware.org/glibc/manual/latest/html_node/Malloc-Tunable-Parameters.html)：arena 上限与 trim 等选项，行为受路径/条件影响。未将“永远不归还”保留为事实。

图像由主控根据原文结构校准后生成，源 SVG/MD 未被本 agent 改动。人物照片由主控统一实搜与核验，已加入 Jason Evans、Sanjay Ghemawat、Daan Leijen 的本地照片 URL。

人物年代补充：Jason Evans 的 [2006 BSDCan 设计论文](https://papers.freebsd.org/2006/bsdcan/evans-jemalloc/)；Sanjay Ghemawat 的 [TCMalloc 原文与现维护者说明](https://gperftools.github.io/gperftools/tcmalloc.html) 明确标为 2000 年代初工作，不推断当前任职。
