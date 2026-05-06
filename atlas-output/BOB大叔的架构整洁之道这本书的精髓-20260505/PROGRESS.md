# BOB大叔的架构整洁之道这本书的精髓 Atlas Progress

## 元数据
- **主题**: BOB大叔的架构整洁之道这本书的精髓
- **短名**: BOB大叔的架构整洁之道这本书的精髓
- **工作目录**: atlas-output/BOB大叔的架构整洁之道这本书的精髓-20260505/
- **创建时间**: 2026-05-05
- **上次更新**: 2026-05-06(How 阶段封存,推进到 Origin —— 今日暂停)
- **当前阶段**: Origin(待启动)

## 灵魂问题(Discovery 收集)
> "完整理解《架构整洁之道》的设计哲学与可落地方法"

(用户初次回复"我完全不懂,从头讲" —— 默认走"完整理解"路径,后续阶段如有更具体的问题浮现,会随时补强收敛点)

## 进度状态机
- [x] 0. Discovery
- [x] 1. What
- [x] 2. Why(含约束清单建立)
- [x] 3. How
- [ ] 4. Origin
- [ ] 5. 分水岭决定
- [ ] 6. Deep
- [ ] 7. Comparison(可选)
- [ ] 8. Synthesis
- [ ] 9. 导出格式询问
- [ ] 10. 融合输出

## 约束清单(Why 阶段建立,后续阶段引用)
| # | 约束 | 来源 | 不可再分性 |
|---|------|------|-----------|
| C1 | 新需求持续到来,加新需求常被迫改老代码 → 引入回归(OCP 失败陷阱) | Lehman 定律(1980)+ OCP(Meyer 1987 / BOB 1988) | 需求会变(系统不变就死)+ 改老代码必有未知风险 → 必须有扩展点 |
| C2 | 技术栈/供应商的不可控演化(技术变化 + 强制替换) | 经济+政策事实(供应商市场 + 信创等政策约束)+ Lehman 演化模型 | 供应商不可控 + 业务/技术演化速率不对称 → 业务核心必须不依赖 framework |
| C3 | 系统复杂度增长时,"超级方法/超级类"必然涌现(除非架构对抗) | 路径依赖效应 + Miller's Law(1956,7±2)+ 软件熵增定律 | 加新功能塞进现有类是阻力最小路径 + 这种倾向不会自动停止(熵增是默认) |
| C4 | 测试反馈速度决定生产力("无 UT 上线即调试"自我强化负螺旋) | Michael Feathers《Working Effectively with Legacy Code》(2004)+ 软件工程经济学 | 慢测试 → 不写 → 不敢改 → 僵化(三步合一,自我强化) |
| C5 | 改一处的代价跟波及面成正比 —— 统领所有原则的元约束 | Boehm COCOMO + Brooks《人月神话》+ 信息论(联合熵增长) | 总成本 = 改动量+风险评估+测试+沟通,各项 ∝ 波及面(经济铁律) |

## 用户疑问/追问审计

### What 阶段
- 用户选择 A(痛点驱动)+ B(下次能用,新项目从一开始建对)
- 用户主动要求展开 SOLID(SRP/OCP/LSP/ISP/DIP)+ 组件 6 原则(REP/CCP/CRP/ADP/SDP/SAP),且要求缩写全部展开
- 用户描述了具体屎山场景:多区适配的环境监测系统(Spring Boot + Oracle + MyBatis + Vue + 微信小程序 + 大屏),A 区代码 copy 到 B 区改、无 UT、上线即调试、老人离开、新人接手 —— 已作为 What 文档的"对照底片"贯穿使用
- 推荐 Michael Feathers《修改代码的艺术》作为补充(C 级救援需求的真正药方)
- 第 1 次产物迭代(patch-1): 用户反馈"降格"太书面 + 医院类比对程序员不如电商订单贴 → §2 整段重写为电商订单系统(含 `OrderService` 绑死 vs `Order` 独立 Java 代码对照),§1 + §4 中"降格"替换为"把它们当成配件、不是主角"
- 第 2 次产物迭代(patch-2): 用户反馈"detail"用语不通俗 + "显示器"比喻奇怪 → "detail" 全文替换为"配件"(§4 词条改为 "配件 / detail" 双语对照保留连接到原书);§1 第 2 项的"今晚用什么显示器"换成用户原话的汽车轮胎/音响/内饰 vs 动力系统对照;§8 ASCII 框线同步补空格对齐。讨论中曾提议过"适配件"被否决(理由:跟 Adapter 视觉冲突,后续读 SOLID/Plugin 章节会混淆)
- 用户回答 What 阶段反问("框架是配件 vs 必须用 Spring 不矛盾"):用户独立提出"如果换了核心就变了,如果换了核心还在则是配件" —— 跟 BOB 第 5 章原话 "Business rules ARE the system" 同构。
- 第 3 次产物迭代(patch-3): 把用户原创的"身份测试"小节补进 §1 末尾,关联到 BOB 第 5 章原话
- 用户主动提供绝佳真实案例:公司当前面临国产化(信创)转型,Oracle→达梦 + Spring Boot→东方通,**正在经历"举步维艰"** —— 这例子直接证明"框架是配件"原则的工程经济价值(差距 5-10 倍代码改动量)。这是 What→Why 最强桥梁,Why 阶段约束清单的 C1/C2(技术供应商不可控、变化频率不对称)在此处萌芽
- 第 4 次产物迭代(patch-4): §1 身份测试后追加"信创(国产化)真实案例"4 行对照表 box;成为该原则最有说服力的现实证据
- 第 5 次产物迭代(patch-5): §5 LSP 重写 —— 引入 BOB 升华版定义(不只继承)+ 4 维度行为契约表(precondition/postcondition/invariant/history)+ 用 `WorkOrderRepository`(Oracle vs 达梦)Java 代码做主例(直接连用户的国产化迁移痛点);Rectangle/Square 降级为"经典玩具例子"附记 | 用户反馈 LSP 难懂、Rectangle 例子脱离实战
- 第 6 次产物迭代(patch-6): §6 开头新增"11 条原则的尺度对照"小节 —— 6 行对照表展示 SOLID ↔ 组件 6 的对应关系 + 双向因果(SOLID 是必要条件,但 REP 是组件级独有,无法从 SOLID 推出) | 用户问:SOLID 是公理、组件 6 条是推论吗?给精确回答
- 用户追问:"6 个原则是组件层面 Use Case 层面的规则?" —— 这是把"组件"和"Use Case 层"概念误等同;在 atlas 教学中这是非常常见的混淆,需要明确正交性
- 第 7 次产物迭代(patch-7): §6.0 尺度对照之后追加"重要澄清:组件 ≠ Use Case 层"box —— 用对照表展示"打包粒度轴"(类/组件/系统)和"架构关注点轴"(同心圆四层)是正交的两个独立 dimension;具体例子展示 Entity 组件 / Use Case 组件 / Adapter 组件都各自要遵守组件 6 条;一句话总结正交关系
- 用户提议:把"什么时候用 SOLID、什么时候用组件 6"的概览图放在 §5 SOLID 之前作为预览,并建议用 SVG 而非 ASCII
- 第 8 次产物迭代(patch-8): 新增 §4.5「一张图先看清」小节(夹在 §4 和 §5 之间),配 SVG `pics/01-scale-map.svg`(暗色科技风,viewBox 1200×600,5 类语义色稳定):展示打包粒度轴(类/组件/系统 → SOLID/组件 6/同心圆)+ 架构关注点轴(Entity/Use Case/Adapter/Framework)+ 两个具体例子(`WorkOrder` 类、`dispatch-workflow.jar` 组件)展示两轴正交关系;一句话总结"两个独立维度,不要混"
- 用户问 DIP 的"高层模块/底层模块"具体指什么?是否高层 = 业务、底层 = 框架?—— 直觉对,但需补充"抽象的定义权"这个最容易误解的关键点
- 第 9 次产物迭代(patch-9): §5 D(DIP)开头补"高层 vs 底层"明确说明(高层 = Entity+Use Case,底层 = Adapter+Framework);末尾追加"⚠️ 抽象的定义权"box —— 业务 `import JpaRepository<T>` 是 ❌ 假 DIP(接口由框架定义),业务模块自定义接口才是 ✓ 真 DIP;直接连接国产化迁移
- 用户问 SRP 和 ISP 是否有重叠?—— 直觉部分对,但角度不同
- 第 10 次产物迭代(patch-10): §5 ISP 之后、D 之前新增"💡 SRP vs ISP 它们的区别"对照 box —— 5 行展示两条原则的看的对象/谁的视角/判断标准/失败长啥样/主战场差异,说明可以独立成立,重叠区是 God class + God interface

### Why 阶段
- 用户选择 A(窄而精,4-6 条),接住 What 阶段的国产化案例 + 屎山诊断作为火种
- 用户主动 redirect C1: 从原候选"变化速率不对称"改为"新需求持续到来 + 改老代码引入回归(OCP 失败陷阱)" —— 用户原话"加 B 需求 A 又挂了"直接进 C1
- 用户 redirect C3: 从原候选"人脑认知带宽有限(Miller's Law)"改为"系统复杂度上升 → 超级方法/超级类涌现",Miller's Law 降级为"物理根因"附记
- 用户 confirm C4: "无 UT 上线即调试"是当下痛,直接进 C4 标题口诀
- C2 / C5 候选讨论中直接通过(C2 = 技术栈/供应商不可控演化,合并了原来"变化速率"+ "供应商不可控";C5 = 改一处代价 ∝ 波及面,作为统领所有原则的元约束)
- 用户给"可以写了"信号,Why 阶段初稿生成 + SVG 概览图(`pics/02-overview.svg`)三层因果链可视化
- 用户回答 Why 阶段反问("只保留一条约束你留哪条?"):选 C1,理由是 C1 是日常 entry point,从 C1 级联到 C3(超级类)→ C4(无UT)→ C2(技术栈崩)→ 综合崩溃;Claude 心里答案是 C5(物理元约束),两种 framing 互补;BOB Chapter 2 选 C5 视角 ("software's primary value is the ability to be changed"),Chapter 1 用 C1 视角(productivity collapse 曲线)
- 第 1 次 Why 产物迭代(patch-1): §3.6 新增「5 条约束的级联关系 —— 屎山的时间演化」小节,把用户的级联链 (C1→C3→C4→C2→综合崩溃) 整理成"层级看 vs 级联看"两种 framing;关键洞察"屎山救援 entry point 是 C1,踩刹车踩在 OCP" —— OCP 从抽象原则升华到"屎山演化第一道刹车"
- 第 2 次 Why 产物迭代(patch-2): §3.5 C5"所有 11 条原则的最终目标都是控制波及面"对照表,11 条缩写全部展开为英文全称 + 中文翻译 | 用户反馈:11 条都是缩写不便记忆

### How 阶段
- 渐进对齐 4 问收敛:深度档=骨架级;三件事=A(同心圆四层+依赖规则+边界DIP);主场景=C(工单状态扭转,Vue→Oracle 全链路);加分项=国产化 Oracle→达梦 Repository 切换实战;概览图=同心圆 + Java 包映射 双视图
- 用户给"ok"信号,How 阶段初稿生成 + SVG 双视图概览图(`pics/03-overview.svg`,viewBox 1200×660,5 类语义色 + 包树映射)
- 文件落在 `stages/03-how/03-how.md`,~430 行,§0 三件事 / §1 概览 / §2 四层细看 / §3 端到端走查 / §4 demo / §5 朴素 vs 真实 / §6 三个误解 / §7 国产化实战 / §8 约束回扣 / §9 呼应灵魂问题
- 第 1 次 How 产物迭代(patch-1): §2.2 后追加 §2.2.1「Use Case 是 Spring Bean 吗?」—— 教科书派(纯 Java + Framework 层 `@Bean` 装配) vs 务实派(直接 `@Service`)对照,判断尺子(换 Spring 为 Guice 要不要改类),4 层 Spring 注解政策对照表(Entity 绝对禁止 / Use Case 看 C2 承受度 / Adapter 完全可以 / Framework 必须) | 用户追问"TransitionWorkOrderUseCase 是 spring bean 吗?" —— 落地最易踩的坑,初稿 §2.2 未覆盖
- 第 2 次 How 产物迭代(patch-2): §2.2.1 内追加「澄清:`@Bean` 装配 ≠ 每次请求实例化一次」子节 —— `@Bean` 方法只在 Spring 启动时调 1 次 → singleton 缓存 → 所有请求共享同一实例;两派运行时性能零差异(差别全在编译时 Use Case 是否依赖 Spring);提及 `@Scope("prototype")` 应加在 Framework 层 `@Bean` 方法上保持 Use Case 类纯净 | 用户追问"如果不是 bean,Framework 层每次都要实例化一个 Use Case 对象了" —— 真实运行时认知误区
- 用户表态:基于"架构要干净 / 不能依赖 Spring 才能跑"的认知,明确选教科书派(对照 §2.2.1 怎么选 box 中的"要应对国产化迁移 / 信创要换框架 → 严格教科书派");这跟 What 阶段的 信创/国产化 真实案例完全对齐,Use Case 类零 Spring 依赖是用户对 [C2](#c2) 承受度做出的明确选择
- 第 3 次 How 产物迭代(patch-3): §2.2.1 「戳破」后追加「『是 Bean』的两个不同精度」子节 —— 区分编译时(类是否依赖 Spring,❌ 不要)vs 运行时(实例是否进容器,✅ 必须进);精炼教科书派精髓 = 「类不是 Bean 类型,但实例是 Bean 对象」「借力 Spring 装配,不让它穿到内层」;给出两条判别尺子:类干净(看不到 Spring import) + 装配通(Controller 能注入到实例);解释了"为什么实例必须进容器" —— 否则 Controller 自己 new 等于手写 mini DI 容器 | 用户用"不能是 Bean"模糊术语承诺教科书派,精度补强:他能达成的是"类不依赖",不是"实例不进容器"(后者做不到也不需要)
- 用户独立推出 BOB 整本书的核心论点:"Spring 是运行时的容器,所以编译时业务代码可以零依赖。用了 Spring 在运行时生成,保持代码的整洁也用了框架。" —— 这跟 BOB 原话 "Frameworks are tools to be used, not architectures to conform to" 同构;是 What 阶段「框架是配件 vs 必须用 Spring 不矛盾」的更深一层表述(那时聚焦"换核心还在 = 配件",这里聚焦"DI 在运行时所以编译时干净")
- 第 4 次 How 产物迭代(patch-4): §2.2.1 末追加「这一节的 takeaway:借力,不依赖」box —— 引 BOB 原话 + 精炼口诀「借力,不依赖」;解释 Spring 运行时装配性质让"代码干净 + 复用框架"不矛盾;补充更深一层根源:Spring 之所以能这样做,因为它基于先于它的两个思想(Fowler 2004 DI Pattern + BOB 1996 DIP),Guice/Dagger/CDI 同源,Spring 只是其优秀实现之一 —— 教科书派的 Use Case 换 DI 框架几乎零修改;末尾把用户原话与 BOB 原话并列双引
- 第 5 次 How 产物迭代(patch-5): §4 demo 末追加 `.framework/UseCaseConfig.java` 显式装配代码(`@Configuration` + `@Bean` 方法) + 4 行说明(位置 = .framework / 作用 = 装配纯 Java Use Case / 效果 = 内层零 Spring 但容器仍有 Bean 实例 / 务实派对比 = 用 `@Service` 省此类但破坏纯净);同步更新 SVG `pics/03-overview.svg` framework 层显式列 `UseCaseConfig.java` 标 ★教科书派关键 | 用户敏锐指出原稿 §4 demo / §1 SVG 漏 `@Configuration` 类 —— 选教科书派后必须显式装配,否则原文跟 §2.2.1 不一致
- 用户独立提出"依赖 = import = 编译顺序"的物理元定义 + 循环依赖示例(虽然举例时把 Controller 误归 framework 层,但核心 insight 完全正确);精度纠正:Controller 物理上在 Adapter 层,Framework 层只放装配工具(`@Configuration`/`SpringBootApplication`/yml);真循环出现在"Use Case import Adapter 实现类"的朴素方案,DIP 反转就是断开此循环
- 第 6 次 How 产物迭代(patch-6): §0.2 内追加 §0.2.0「『依赖』到底是什么意思?(物理本质)」—— 依赖元定义 = `A import B`,B 不存在 A 编译不过;依赖向内 = DAG 拓扑序(Entity→Use Case→Adapter→Framework);4 条关键推论表(业务核心可独立编译 / 单测快 / 信创 jar 可换 / 改 Entity 是地震 vs 改 Framework 是地皮),每条挂一个 Cn;真循环反例(Use Case import OracleRepo 形成 .usecase ↔ .adapter 双向 import → Maven 多模块编译失败);DIP 反转怎么物理断开循环;记忆口诀「依赖 = import = 编译顺序 = 谁能没有谁活下来 = 删掉外层内层仍能 javac」;原 §0.2 主线内容拆成 §0.2.1「依赖规则的具体形态」保留 Java import 限制条款 | 把用户独立提出的元定义钉为 §0.2 的物理基底,把 §0.2 从"抽象规则"升华为"编译时的物理事实"
- 用户提出 4 条直觉判断:(1) Entity+UseCase 不依赖 spring/mysql/kafka 等 framework(✅ 完全正确,确认理解);(2) 自检方法 = 移除 spring jar 从 classpath 看核心代码能否编译过(✅ 新洞察,可操作);(3) 核心可单独发 jar 跨项目共享(✅ 新洞察,正是 REP 原则物理实现);(4) Adapter 与 Framework 可合并(⚠️ 直觉对部分,工程现实合,但信创场景必须分)
- 第 7 次 How 产物迭代(patch-7): §0.2.0 末追加「自检方法:你的项目算不算干净?」—— 实验 1 classpath 移除测试(`mvn compile` 看能否过)+ 实验 2 独立 jar 发布测试(`workorder-core.jar` 只依赖 JDK,< 100KB,跨项目可复用 = REP 原则物理实现);两实验关系(1 ⊃ 2,1 是必要条件);末尾把用户原话作 evidence
- 第 8 次 How 产物迭代(patch-8): §2 末追加 §2.5「⚠️ 常见疑问:Adapter 和 Framework 为什么是两层?(很多人会问能不能合并)」—— 承认直觉来自工程现实(Spring Boot 教程很多合一);但戳破两层本质不同(Adapter = 行为代码/翻译器/高频改/增量替换 vs Framework = 元信息/装配/低频改/整体替换);信创场景两类迁移改动范围对照(Oracle→达梦只动 Adapter / Spring Boot→东方通只动 Framework);判别尺子(信创预期内 → 必须分;短期项目 → 可妥协合并);末尾给用户公司现实落地建议(信创预期内 → 必须 4 层分);末尾把用户原话作 evidence
- 用户诊断文档过长(818 行)抽象信号稀释,明确要求大重构:删 §3 端到端走查 / §5 朴素 vs 真实对照 / §8 约束回扣表 / §7 国产化实战(精华挪到 §2.3/§2.4);§2 强调 Entity+UseCase 是内核可单独编译;§2.2 删 Spring 派别讨论;§7 信创对照表(Oracle→达梦 / Spring Boot→东方通)挪 §2.3/§2.4("非常不错")
- 第 9 次 How 产物迭代(patch-9 大重构): 文档从 818 行 → 463 行(-43%);删 4 大块(旧 §3 / §5 / §7 / §8 整章);§2.2 删除 §2.2.1 整段(Spring 派别讨论 + 借力不依赖 takeaway 等 5 次 patch 内容);§2 新增 §2.0「核心命题:Entity + Use Case 是内核,可单独编译」作为四层细看的引言段;§2.3 内嵌 Oracle→达梦 信创对照表(从旧 §7.2 + §7.3 提取);§2.4 内嵌 Spring Boot→东方通 信创对照表;§2.5 精简,只留"能不能合并"判别 + 信创证据指引;每层介绍末尾加 1 行「关联约束 → Cn」收口;§3 demo 末尾「关键点」精简到 4 条;§5 呼应灵魂问题去掉"端到端走查"提法 | 用户主导的诊断 + 重构,文档单一聚焦"内核 = Entity+UseCase 可单独编译 + 4 层分离的工程价值"

### Origin 阶段
- (无)

### Deep 阶段
- (无)

### Comparison 阶段
- (无)

### Synthesis 阶段
- (无)

## 选定的对比对象(Comparison Hook 后填入)
- (无)

## 选定的导出格式(导出阶段填入)
- (待定)
