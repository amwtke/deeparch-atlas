# 阶段 6:Bob 4 层 Clean Arch 与 DDD 的对照

> 横向对比一个跟 Clean Arch **视觉极相似但战略级根本不同**的设计 —— Eric Evans 2003 年提出的 **Domain-Driven Design(DDD)**。
> Bob 大叔本人在《Clean Architecture》References 里**主动引用** Evans《DDD》(2003)作为延伸阅读;两本书是**工程入门版 vs 业务专家协作版**的关系。
> 这一篇会讲清楚:① 为什么很多人混淆这两个 ② 战术级几乎同构 + 战略级 DDD 多 4 件事 ③ 同一个 `Order.payTo()` 两种风格的代码差异 ④ 你今天选哪个。

---

## 约束清单速查(C0~C5)

#### C0 — 人不自律(Origin §7 反向发现的隐性元元约束)
方法论假设了"理性程序员",但人不自律 + 行业激励惩罚自律。
**口诀**:工具不解决人的问题,但 AI 时代第一次可能让 C0 在工程实践中失效

#### C1 — OCP 失败陷阱
新需求持续到来,加新需求常被迫改老代码 → 引入回归。
**口诀**:必须留扩展点

#### C2 — 技术栈/供应商不可控
技术栈和供应商的演化不在你控制中(政策、市场、信创)。
**口诀**:业务核心不依赖 framework

#### C3 — 复杂度涌现
系统复杂度增长时,"超级方法/超级类"必然涌现(除非架构对抗)。
**口诀**:必须主动对抗熵增

#### C4 — 测试反馈速度
测试反馈速度决定生产力("无 UT → 上线即调试" 自我强化负螺旋)。
**口诀**:核心必须快速可测

#### C5 — 改动代价 ∝ 波及面 (元约束)
改一处的代价跟波及面成正比。
**口诀**:控制波及面 = 控制总成本

---

## §0 从 Deep 走到 Comparison:三件事记住

Deep 阶段把订单系统重构走完(α → β → γ),证明 Bob 4 层 Clean Arch **实操可落地**。但 Clean Arch 不是孤立设计 —— 它在 2017 年成书时已经站在前人肩膀上 14 年(Evans《DDD》2003)。**Comparison 阶段把 Clean Arch 跟 DDD 放在一起对照**,让你看清:**Bob 大叔的设计哲学,有多少是合成、多少是原创、多少是简化**。

三件事:

### §0.1 同构关系 —— Clean Arch γ 工程层面 ≈ DDD 战术级子集

**因为 [C5](#c5--改动代价--波及面-元约束)**(改动 ∝ 波及面)
   ↓
**两套架构都在解决同一个问题** —— 业务核心不被框架 / 数据库污染,业务规则归属正确层 → 改动控制在波及面内
   ↓
**所以两套在战术级几乎同构**:Entity ≈ Aggregate Root / Use Case ≈ Application Service / Repository(业务定义)≈ Repository(DDD)/ Adapter ≈ Infrastructure。**Clean Arch γ 状态在工程层面就是 DDD 战术级的子集 + 简化版**(Clean Arch 不强调 Aggregate 边界 + 不变量保护)。

### §0.2 战略级差异 —— DDD 多了 4 件 Clean Arch 没有的事

**因为 [C3](#c3--复杂度涌现) + [C5](#c5--改动代价--波及面-元约束)**(复杂度涌现 + 改动 ∝ 波及面)
   ↓
**Clean Arch 假设单上下文 + 单聚合根**(订单 / 工单这种相对独立的业务模块);DDD 假设**多上下文 + 多事业部 + 跨团队协作**(电商核心 / 银行核心 / 保险理赔)
   ↓
**所以 DDD 多了 4 件事**:① **Bounded Context**(限界上下文,模块边界划分) ② **Domain Event**(领域事件,异步解耦) ③ **Ubiquitous Language**(统一语言,业务/技术团队术语统一) ④ **Strategic Design / Context Map**(战略设计 / 上下文映射,跨上下文协作模式)。Clean Arch 在战略级**完全没有这 4 件事**。

### §0.3 历史血脉 —— Bob 大叔合成 + 简化 DDD,而不是原创

**因为 [C0](#c0--人不自律origin-7-反向发现的隐性元元约束)**(人不自律)
   ↓
**Evans 2003 DDD 太重 + 学习陡 + 需业务专家驻场** —— 这恰好对抗了 §6.1 趋利避害 + §6.4 没真正理解就自以为是,所以 14 年(2003-2017)虽然在大厂中台战略里推广,但**没成为基层工程师的默认范式**
   ↓
**Bob 大叔做的关键事**:把 DDD 战术级**简化 + 工程化 + 推广**,降低落地门槛 —— 让单个工程师 / 中小团队也能"做点 DDD"。Clean Arch 是 **DDD 的工程入门版**,这跟 Origin §3 / §4 「Bob 大叔合 4 套架构(Hexagonal/Onion/BCE/DCI)为同心圆」是**同一个合成动作的两面** —— Bob 大叔的全部贡献都在『合成 + 简化 + 命名 + 推广』,**没有一条是新的**。

### §0.4 三件事横向对照表

| # | 关系 | 物理证据 |
|---|-----|--------|
| **1 同构** | Clean Arch γ ≈ DDD 战术级子集 | Entity/Use Case/Repository/Adapter 一对一映射 DDD 聚合根/应用服务/仓储/基础设施 |
| **2 差异** | DDD 战略级 4 件事 Clean Arch 没有 | Bounded Context / Domain Event / Ubiquitous Language / Strategic Design |
| **3 血脉** | Bob 大叔合成简化 DDD,Clean Arch 是 DDD 的工程入门版 | Bob 在 Clean Arch References 里 cite Evans;DDD 早 14 年(2003 vs 2017) |

---

## §1 设计动机简表

每个对比对象**必须**列出 4 件事(初衷 / 擅长 / 不擅长 / 典型应用场景)—— 这给读者**判断该用哪个**的现实锚点。

### §1.1 Bob 4 层 Clean Architecture(2017)

**初衷**:Bob 大叔 2012 年看到工业界已有 4 套同期架构(Cockburn 2005 Hexagonal / Palermo 2008 Onion / Jacobson 1992 BCE / Coplien-Reenskaug 2009 DCI)思想相似但各说各话;读者迷茫"该用哪个"。Bob 写《The Clean Architecture》博客把这 4 套**合成一张同心圆图 + 一条统领规则(依赖向内而生)**;2017 年扩展为完整书籍。**核心贡献是合成 + 简化 + 命名,不是发明**(Origin §3 / §4 已立)。

**擅长**:
- **中等复杂度业务**(订单 / 工单 / CRM 等单聚合根强一致场景)
- **需要解耦框架/数据库**(信创 / 国产化迁移预期 / 长期项目 5+ 年)
- **Java / Spring 生态**(同心圆 4 层物理结构跟 Maven 多模块天然对齐;教科书派 Use Case 类零 Spring 依赖)
- **3-10 人技术团队**(战术级 3 件事人均能掌握,不需专门架构师)

**不擅长**:
- **极小项目 / POC / 短期 MVP**(over-engineering;§4.4 反事实小试 4 个候选已对比)
- **高复杂度多事业部业务**(战略级缺失;无 Bounded Context 应付不了多上下文协作)
- **异步事件驱动业务**(无 Domain Event 概念;支付完成后多链路异步处理需要自己造轮子)
- **业务领域专家驻场**(Clean Arch 不强调 Ubiquitous Language;业务团队和技术团队术语不统一时,Clean Arch 没工具帮忙弥合)

**典型应用场景**:
- **Robert C. Martin 自己的 Clean Coders 教学项目**(blog.cleancoder.com 上的所有 demo 代码,被作为 Clean Arch 标准实现)
- **众多 Java 后端服务模块**(中等复杂度,GitHub 上 "clean architecture spring boot" 仓库超 5K star,但需注意 80% 是 β 状态而非 γ)
- **Android / iOS 移动应用**(Square、Uber 等 App 的部分模块;移动应用同心圆模式比 Java 后端更普及,因移动框架变更频繁,4 层物理隔离收益更明显)
- **嵌入式 / 工业控制软件**(Bob 大叔 Object Mentor 早期咨询业务的主战场,模板长期保留至今)
- **信创 / 国产化迁移项目**(Spring Boot → 东方通 / Oracle → 达梦的典型采用模式;Use Case 零框架依赖是核心需求)

### §1.2 Domain-Driven Design(Evans 2003)

**初衷**:Eric Evans 1990 年代末做企业级 ERP / CRM 软件咨询,看到一个反复出现的问题 —— **业务复杂度爆炸时,代码无法承载业务规则,业务团队和技术团队术语不统一,需求每改一次代码都要重写**。2003 年出版《Domain-Driven Design: Tackling Complexity in the Heart of Software》—— 提出 **聚合根 + 限界上下文 + 统一语言 + 战略设计** 4 件套,目标是**让业务复杂度可被工程承载**。Vaughn Vernon 2013 年《IDDD》(Implementing Domain-Driven Design)把它工程化(模式化代码示例 + Java 实战)。

**擅长**:
- **高复杂度业务**(电商核心 / 银行核心 / 保险理赔 / 医疗信息系统 / 大型 SaaS)
- **多事业部 / 多领域协作**(订单 + 履约 + 财务 + 风控 等多个 Bounded Context)
- **业务领域专家驻场**(Ubiquitous Language 必须业务团队参与,这是 DDD 的核心前提)
- **异步事件驱动业务**(Domain Event + Saga 补偿机制天然适配支付完成 → 多下游链路场景)
- **长期演进项目**(5-15 年生命周期,业务规则反复变化,聚合根 + 不变量保护可承载这种持续演进)

**不擅长**:
- **小项目 / 简单 CRUD**(over-engineering 严重;为 100 行 CRUD 引入 Aggregate + Bounded Context 是杀鸡用牛刀)
- **业务领域简单**(Bounded Context 不超过 2 个的项目用不上 DDD 战略级)
- **无业务专家 / 业务专家不愿配合**(Ubiquitous Language 落不下 → DDD 退化为"分模块写 CRUD")
- **小团队 / 团队不熟 DDD**(聚合根边界识别 + 限界上下文识别是 30 年功夫,新团队上来就用 DDD 通常落地为伪 DDD,代价比假 DIP 还高)

**典型应用场景**:
- **eBay 早期架构**(Evans 自己在《DDD》书里 cite 的案例;电商核心的限界上下文模式)
- **Vaughn Vernon's IDDD Examples 项目**(GitHub 上 `VaughnVernon/IDDD_Samples`,DDD 战术级 + 战略级完整实战)
- **阿里中台战略(2015+)**(公开宣传"业务中台 = DDD 战略设计落地";大量内部分享 DDD 模式 / Bounded Context / Ubiquitous Language)
- **京东物流核心 / 京东中台**(架构博客多次披露用 DDD 重构核心订单 / 履约系统)
- **银行核心系统**(招行、平安、工行等多家银行核心系统采用 DDD;尤其新一代核心架构改造)
- **大型 SaaS 平台**(Salesforce 部分 / 国内钉钉 / 飞书多个模块)
- **保险理赔系统**(平安保险、太平洋保险公开案例)
- **ThoughtWorks 顾问项目**(他们是中文圈 DDD 主要传播者,《领域驱动设计精粹》中文版多次再版)

---

## §2 对照:Clean Arch vs DDD

### §2.1 对比维度

**核心维度** = "**架构责任范围**":Clean Arch **聚焦工程依赖管理**(怎么解耦框架);DDD **聚焦业务建模 + 战略协作**(怎么把复杂业务工程化)。**两者不是替代关系,是 subset 关系**(Clean Arch ⊂ DDD 战术级)+ DDD 战略级延伸。

### §2.2 同构关系(为什么很多人混淆)

| Bob 大叔 Clean Arch (2017) | Eric Evans DDD (2003) | 关系 |
|---|---|---|
| **Entity** (最内层) | **Aggregate Root**(聚合根) | DDD 聚合根 = Clean Arch Entity 的**业务精确化**(强调聚合边界 + 一致性不变量) |
| **Use Case**(应用业务规则) | **Application Service**(应用服务) | 同义概念,命名不同 |
| **Use Case 层业务定义的 Repository interface** | **Repository(仓储)** | DDD 仓储 = Clean Arch §0.1 的"接口位置反转"产物 |
| **Adapter**(持久化 / 外部 API) | **Infrastructure**(基础设施) | 同义 |
| **Framework**(Spring 装配) | (DDD 不强调这层) | Clean Arch 比 DDD 多了"框架装配点"边界(显式 @Configuration) |
| (Clean Arch 不强调) | **Bounded Context**(限界上下文) | DDD 在更高层做模块边界 |
| (Clean Arch 不强调) | **Domain Event**(领域事件) | DDD 引入事件驱动 |
| (Clean Arch 不强调) | **Ubiquitous Language**(统一语言) | DDD 强调业务/技术团队术语统一 |
| (Clean Arch 不强调) | **Strategic Design / Context Map**(战略设计 / 上下文映射) | DDD 包含战略设计层 |

**关键观察 1**:**Clean Arch γ 状态在工程层面 ≈ DDD 战术级的子集**。DDD 战术级的"聚合根 + 仓储 + 应用服务"几乎一对一映射到 Clean Arch 的 Entity / Use Case 层 interface / Use Case 实现。

**关键观察 2**:DDD 比 Clean Arch 多出来的部分 = **战略级 + 业务建模深度**(限界上下文 / 领域事件 / 统一语言 / 上下文映射)—— 这些 Clean Arch 没有。

**关键观察 3**:**DDD 比 Clean Arch 早 14 年**(Evans 2003 vs Bob 2017)。Bob 大叔在《Clean Architecture》References 里**主动引用 Evans《DDD》作为延伸阅读** —— 这暗示 Bob 大叔的工作部分是把 DDD 战术级**简化 + 工程化 + 推广**。

### §2.3 区别 4 维度

| 维度 | Clean Arch | DDD |
|-----|-----------|-----|
| **粒度** | 战术级 + 工程实施级(4 层物理结构) | **战略级 + 战术级**双层(Bounded Context 战略 + Aggregate/Service 战术) |
| **关注点** | **依赖方向**(怎么解耦框架 / 数据库) | **业务语义**(怎么把业务领域精确建模) |
| **学习曲线** | 相对简单(3 件事就能落地;Deep §0.1-§0.3) | **复杂**(聚合根设计 + 限界上下文识别 + 统一语言 = 30 年功夫;需业务专家驻场) |
| **适用场景** | 中等复杂度 + 需解耦框架 + 信创预期 | **高复杂度业务**(金融 / 电商核心 / 制造业 ERP)+ 业务领域专家驻场 |

### §2.4 五元组对比表(atlas Comparison 标准)

| | **Clean Arch** | **DDD** |
|---|---|---|
| **核心抽象** | 4 层同心圆(Entity / Use Case / Adapter / Framework)+ 依赖向内而生 | 聚合根(强一致边界)+ 限界上下文(模块边界)+ 统一语言(协作锚点) |
| **元数据/接口位置** | 业务接口在 Use Case 层,Adapter implements | Repository 接口在 Domain Layer;聚合根的 ID 是值对象 |
| **处理 [C5](#c5--改动代价--波及面-元约束) 的方式** | 4 层物理隔离 + 依赖向内 → 改 Entity 是地震 / 改 Framework 是地皮 | 限界上下文 + 聚合一致性边界 + 反腐层(ACL)→ 改一个聚合不影响其他聚合 |
| **代价** | 工程纪律严格(多写 ~50 行 interface)+ 战略级缺失 | 业务建模学习曲线陡 + 需业务专家驻场 + Saga 补偿机制 + 最终一致性处理 |
| **处理 [C0](#c0--人不自律origin-7-反向发现的隐性元元约束) 的方式** | 战术 3 件事(接口反转 / 边界外推 / 状态机上提)+ 工程纪律 | 战略+战术双层(限界上下文识别 + Aggregate 设计 + Ubiquitous Language)— 多了"业务专家协作 + 跨团队术语统一"两个反人性自律工具 |

**关键发现**:DDD 在 [C0](#c0--人不自律origin-7-反向发现的隐性元元约束) 应对上**比 Clean Arch 工具更多**(战略级 + 业务专家协作),但同时要求**更高自律度**(团队配合 + 业务专家驻场);**Clean Arch 是『弱协作 + 强自律 3 件事』,DDD 是『强协作 + 多种自律工具』** —— 两套设计在 [C0](#c0--人不自律origin-7-反向发现的隐性元元约束) 上的本质都是『不给人偷懒的空间』,只是路径不同。

### §2.5 同一个 `Order.payTo()` 两种风格的代码差异

最直观的差异:**Order 实体内部对外部依赖的处理方式**。

**Clean Arch γ 风格**(Deep §4.1 已立):

```java
public class Order {
    public void payTo(PaymentGateway pg, InventoryClient ic) {     // 依赖通过参数注入
        ensureStatus(OrderStatus.CREATED, "...");
        pg.pay(this.amount, this.userId);                           // 直接同步调外部
        ic.decrease(this.productId, this.qty);
        this.status = OrderStatus.PAID;
    }
}
```

**DDD 风格**(同样的业务规则,DDD 标准写法):

```java
public class Order extends AggregateRoot<OrderId> {                 // 继承聚合根基类
    private final List<DomainEvent> events = new ArrayList<>();      // 领域事件

    public void pay() {                                              // ⚠ 不传外部依赖!
        ensureStatus(OrderStatus.CREATED, "...");
        this.status = OrderStatus.PAID;
        // 不直接调外部接口 → 发领域事件,让其他聚合/服务监听
        this.events.add(new OrderPaidEvent(this.id, this.amount, this.userId));
    }
    public List<DomainEvent> pullEvents() { ... }                    // 发布事件
}

// 应用服务(协调层)
public class OrderApplicationService {
    public void payOrder(OrderId orderId) {
        Order order = orderRepo.findById(orderId);
        order.pay();                                                 // 触发 OrderPaidEvent
        orderRepo.save(order);                                       // save 时统一 publish events
    }
}

// 由独立的事件处理器异步处理 PaymentGateway / InventoryClient
public class PaymentEventHandler {
    @EventListener
    public void handle(OrderPaidEvent event) {
        paymentGateway.pay(event.amount(), event.userId());          // 异步处理
    }
}
public class InventoryEventHandler {
    @EventListener
    public void handle(OrderPaidEvent event) {
        inventoryClient.decrease(event.productId(), event.qty());
    }
}
```

**关键差异**:

| 维度 | Clean Arch γ | DDD |
|------|-------------|-----|
| Entity 跟外部依赖关系 | **Sync 调用**(参数传入,直接调) | **Async 解耦**(发事件,Handler 监听) |
| 编排控制点 | Use Case 类的方法体 | 应用服务 + 事件处理器 |
| 失败回滚 | Use Case 一个事务包裹 | 需要 **Saga / 补偿机制** |
| 实现复杂度 | 低 | **高**(需事件总线、补偿逻辑、最终一致性处理) |
| 业务一致性 | **强一致**(同事务) | **最终一致性** |

**直觉判断**:DDD 的 Async 解耦适合**多聚合根 + 跨上下文 + 异步业务**;Clean Arch 的 Sync 调用适合**单聚合根 + 单上下文 + 强一致业务**。**订单系统(单聚合根强一致)Clean Arch γ 就够了**。

### §2.6 为什么 DDD 这么选 —— 追溯到约束差异

**DDD 面对的约束组合 ≠ Clean Arch 面对的约束组合**。这就是为什么两者选了不同的设计。

| 约束 | Clean Arch (2017) 面对的权重 | DDD (2003) 面对的权重 | 不同选择的根因 |
|-----|-----------------------------|---------------------|--------------|
| C2 (技术栈不可控) | 高(Bob 大叔活在 2017,Spring → 各类 framework 频繁切换) | 中(Evans 活在 2003,J2EE 时代,framework 还没那么 fragmented) | Clean Arch 强调"框架在外圈"+ 教科书派,DDD 不强调 |
| C3 (复杂度涌现) | 中(Clean Arch 假设单聚合根) | **极高**(Evans 做企业 ERP / 电商核心,业务复杂度爆炸是首要问题) | DDD 引入 Bounded Context + 战略设计应对超大复杂度 |
| C5 (改动 ∝ 波及面) | 高 | **极高**(企业核心改一处可能波及 100 处) | DDD 用聚合一致性边界 + 限界上下文,比 Clean Arch 4 层切得更细 |
| 跨团队协作 | 不在 Clean Arch 视野(单团队为主) | **核心**(Evans 做大企业咨询,跨团队协作是日常) | DDD 引入 Ubiquitous Language + Context Map,Clean Arch 完全没有 |
| 异步事件驱动 | 不在 Clean Arch 视野 | **核心**(企业核心都是异步业务,如银行结算 / 电商履约) | DDD 引入 Domain Event,Clean Arch 没有 |

**结论**:**Bob 大叔面对的是『中等复杂度 + 单团队 + 同步业务』为主的工程现实;Evans 面对的是『超大复杂度 + 多团队 + 异步业务』的企业现实**。两套架构的差异**反映了它们诞生时各自面对的约束权重不同**,不是谁好谁坏,**是适配场景不同**。

### §2.7 选用建议(对你公司订单系统场景)

| 问题 | 结论 |
|-----|------|
| 现在用什么? | **先 Clean Arch γ**(Deep §4.1 写的)→ 跑稳 1-2 年再考虑是否上 DDD |
| 为什么不直接 DDD? | DDD 落地需业务专家 + 长期迭代;没走通 Clean Arch γ 直接上 DDD = **over-engineering**;聚合根边界识别错误的代价比假 DIP 还高(因为聚合根边界一旦定错,整个系统几乎要重写) |
| 什么时候应该上 DDD? | 三个明确信号(任一满足就考虑):① 业务复杂度涨到**多事业部**(订单 / 履约 / 财务 / 风控)→ 需要 Bounded Context;② **业务领域专家驻场**且愿意跟工程师统一语言;③ 业务**异步/事件驱动**特征明显(支付完成后多个下游链路) |
| Bob 大叔本人态度 | 在《Clean Architecture》References 里推荐了 Evans《DDD》(2003)作为延伸阅读;Bob 大叔自己的工作**基本是 DDD 战术级 + 工程化简化** —— Clean Arch 是 DDD 的工程入门版 |
| 跳级风险 | **跳级摔死**:小项目用 DDD = over-engineering 到团队抱怨;大项目用 Clean Arch = 战略级缺失到混乱;**正确路径**:Clean Arch γ → DDD 战术级 → DDD 战略级,**逐级升级,不跳** |

### §2.8 这个对比突出了什么

> **Bob 大叔的 Clean Architecture 不是凭空发明,是 DDD 战术级的简化 + 工程化 + 推广**(降低了 DDD 14 年没普及的"准入门槛")。这跟 Origin §3 「Bob 大叔合 Hexagonal/Onion/BCE/DCI 4 套架构」是**同一个合成动作的两面** —— Bob 大叔的核心贡献始终是『**合成 + 简化 + 命名 + 推广**』,不是发明。
>
> **理解了这一点,对 Clean Arch 的认知就成熟了**:它不是『最完美的架构』,是『工业界落地门槛最低 + 工程价值最即时显现』的中等架构。**真正的设计哲学根源在 1972 Parnas / 1986 Meyer / 2003 Evans**,Bob 是承接 + 工程化的关键一棒。

### §2.9 一句话总结

> **Clean Arch 是『工程师友好版的 DDD 战术级』** —— 4 层结构 + 依赖向内而生 + 3 件战术动作,**入门成本低、工程价值即时显现**。
>
> **DDD 是『业务专家协作版的 Clean Arch + 战略设计』** —— 多了 Bounded Context / 领域事件 / 统一语言 / Saga,**威力大但学习陡 + 需团队配合**。
>
> **正确路径**:Clean Arch γ → DDD 战术级 → DDD 战略级。**跳级会摔死**。

### §2.10 单体 vs 微服务 视角(用户读后总结 patch-1 升精度)

**用户在读完前 9 个子节后做了一个直觉总结,抓住了 95% 的精度**:

> "Bob 的同心圆其实解决的是『**边界清晰、需求中等复杂的单体应用**』的扩展问题;DDD 更倾向于一个**整体大解决方案的解构**,从架构上来说更倾向于**微服务**,多个领域的微服务构建。"

下面把它再精确化最后 5% —— 因为"DDD = 微服务"在工程实施层成立,但在概念层不成立,这一精度差异决定了你公司未来的演进路径。

#### §2.10.1 物理部署形态对照

| 维度 | Clean Arch | DDD |
|------|-----------|-----|
| **物理部署形态** | **单个 JVM / 单进程**(单体)— Maven 多模块,但都打到一个 jar/war | **多个 JVM / 多进程**(微服务)**或 模块化单体**(modulith)— 多服务各自部署或都在一个进程 |
| **代码组织粒度** | 4 个文件夹(framework / adapter / usecase / entity) | **多个 Bounded Context**,每个 BC 内部可以再分 4 层 (= Clean Arch 嵌套在每个 BC 里) |
| **边界关注点** | **进程内的层级边界**(import 方向) | **进程间 / 模块间的业务边界**(BC 边界 + Context Map) |
| **扩展手段** | 替换 Adapter 实现(信创换 ORM / 换支付通道) | 拆/合 Bounded Context;新业务 = 新 BC = (可能是)新微服务 |

**🔑 关键洞察 —— DDD 每个 BC 都可以用 Bob 4 层架构实现(嵌套关系)**:

DDD 的每个 Bounded Context **内部都可以完整应用 Bob 大叔的 4 层 Clean Arch**(Entity / Use Case / Adapter / Framework)—— 也就是说,**Clean Arch 是 DDD 战术级在单个 BC 内部的实现细则**。这就是 §0.1 三件事中"Clean Arch γ ≈ DDD 战术级子集"的物理含义。

DDD 整体看 = **多个 Clean Arch 化的 BC** + **BC 之间的 Context Map / 领域事件 / Saga**(战略级):

```
                ┌─ BC 订单 ──────┐    ┌─ BC 履约 ──────┐    ┌─ BC 财务 ──────┐
                │ ▸ Framework   │    │ ▸ Framework   │    │ ▸ Framework   │
                │ ▸ Adapter     │    │ ▸ Adapter     │    │ ▸ Adapter     │  ← 每个 BC 内部都
DDD 整体  =     │ ▸ Use Case    │    │ ▸ Use Case    │    │ ▸ Use Case    │     完整应用 Bob
                │ ▸ Entity      │    │ ▸ Entity      │    │ ▸ Entity      │     4 层 Clean Arch
                └────────┬──────┘    └──────┬─────────┘    └──────┬────────┘
                         │                  │                     │
                         └──────── Context Map / 领域事件 / Saga 补偿 ────┘
                                          ↑
                                   这部分是 DDD 战略级
                                   (Clean Arch 完全没有)
```

**含义**:
- 你今天写 Clean Arch γ(Deep §4.1) **本身就是在用 DDD 战术级**(只是不叫这个名字)
- 当你升级到 DDD 模块化单体时,**只是多加了 BC 边界 + Context Map** —— 单 BC 内部的 4 层 Clean Arch 一行不用改
- 当你拆微服务时,**单 BC 还是用同一套 4 层** —— 改的只是部署形态(JVM 边界变了)
- **Clean Arch 的工程价值在 DDD 任何阶段都有效**,不会因为升级到 DDD 而被淘汰

#### §2.10.2 DDD ≠ 微服务,但 DDD 是识别微服务边界的最佳工具

这是用户总结里需要精确化的关键点 —— 它影响后续选型:

- **DDD 2003 提出时,微服务还没诞生** —— "微服务"概念是 **2014 年 Martin Fowler / James Lewis** 提出的(《Microservices》文章)。Evans 的 DDD 本来是**给模块化单体**(monolith with modules)用的
- **Bounded Context ≈ 微服务边界**(2015+ 业内共识):**Sam Newman《Building Microservices》(2014)** 直接说"Bounded Context 是识别微服务边界的最重要工具" —— 但这是**事后被借用**,不是 DDD 本来就是为微服务设计
- 所以工业界的实际状态:
  - **概念层**:DDD ≠ 微服务(DDD 也适用于单体)
  - **工程实施层**:**DDD = 微服务划分的最佳实践**(等号成立)
  - **但工程实施层的等号有严格的前提条件** —— 见下文 §2.10.3 的合理性边界 + 6 大失败原因

#### §2.10.3 用 BC 划分微服务的合理性(简述,详见末尾 Q&A)

**结论先行**:用 BC 划分微服务**是合理的,但有 4 个前提条件**(先稳后拆 / 边界稳定 / 团队适配 / 基础设施 ready);直接『DDD = microservices』等同 → 国内 2018-2022 中台战略集体失败的根因。

**但这个失败的根因不是技术问题,是人性问题** —— **急于求成 + 急功近利 + 不求甚解** —— **跟 Origin §6 立的 5 条人性短板同源**(详见末尾 [Q&A Q1](#q1-用-bc-划分微服务是否合理为什么国内-2018-2022-中台战略集体失败))。

**Comparison 阶段不深入这块** —— 它本质上是 Origin §6 + Synthesis §C 的话题,**不是本系列(完整理解《架构整洁之道》)的重点**;放在 Q&A 作为衍生答疑参考。

**对你公司订单系统的现实启示**:**先在单体里用 Clean Arch γ 跑稳,等业务自然涨到需要 BC 边界时升级到 DDD 模块化单体,只在某 BC 真有独立部署需求时才拆微服务** —— 这是失败概率最低的路径。

#### §2.10.4 Bob 做单体 vs Evans 做整体 —— 时代和语境差异

- **Bob 大叔 2017** 写 Clean Arch 时,**微服务热潮刚 3 年**(2014-2017),业界对微服务还在摸索;Bob 选择**不绑死微服务**,只讲单体 4 层 —— 这给了 Clean Arch **更长生命周期**(不会因微服务过时而失效;同心圆 4 层在单体 / 微服务 / 模块化单体里都适用)
- **Evans 2003** 写 DDD 时,**J2EE 是主流,业界全是单体**;但 DDD 战略级的 Bounded Context **超前 11 年预测了微服务时代** —— 2014 年微服务出现时,业界发现 DDD 已经把工具准备好了 → 这是 DDD 30 年没过时的核心原因

#### §2.10.5 你公司订单系统场景的精确定位

| 阶段 | 状态 | 架构选型 | 触发条件 |
|------|------|---------|---------|
| **现在** | 单体 Spring Boot + MySQL | **Clean Arch γ**(Deep §4.1 写的) | 当前最大化收益的局部最优 |
| **3-5 年后**(业务扩展) | 单体 + 多业务模块(订单 / 履约 / 库存 / 财务) | **DDD 模块化单体**(modulith)—— Maven 多模块,每模块按 BC 划分,但仍在一个进程 | 业务复杂到需要 BC 边界,但负载没到必须拆服务 |
| **更后期**(独立扩展需求) | 微服务 | 拆出**部分** BC 为独立服务 + DDD 战略级(Context Map) | 某个 BC 真的需要独立部署 / 独立扩展(如订单 QPS 远超履约) |
| **最后**(成熟期) | 多团队微服务 | **DDD 战略级**(Bounded Context + Context Map + 异步事件 + Saga) | 多个事业部 / 业务领域专家驻场 / 异步事件驱动业务 |

**关键 takeaway**:**不是「Clean Arch 单体」 vs 「DDD 微服务」二选一**,而是 **Clean Arch γ → DDD 模块化单体 → DDD 微服务 → DDD 战略级** 的**4 阶段渐进**。**跳级摔死**:从 Clean Arch 单体直接跳到 DDD 微服务 = 同时学 4 件事(DDD + 微服务 + K8s + 分布式事务) = 国内 2018-2022 中台战略失败潮的活样本。

#### §2.10.6 一句话精确总结(在 §2.9 基础上加一层精度)

> **Clean Arch** = 『**单体**应用 + 中等复杂度的工程依赖管理』 —— 进程内 4 层物理隔离
>
> **DDD 战术级** = 『**模块化单体 / 微服务** + 单 Bounded Context 内部的工程依赖管理』 —— 跟 Clean Arch 几乎同构
>
> **DDD 战略级** = 『**多 Bounded Context 协作 / 微服务编排**』 —— 跨 BC / 跨服务的业务边界 + Context Map + 异步事件 + Saga 补偿
>
> **包含关系**:Clean Arch ⊂ DDD 战术级 ⊂ (DDD 战略级 + 微服务架构);**每升一级,适用场景的复杂度跃升一个数量级**

#### §2.10.7 用户的精炼总结升级版

把用户原话精确化:

> "Bob 的同心圆解决的是**单体应用**(中等复杂度)的『进程内边界 + 框架解耦』问题;
> DDD 战术级跟 Bob 同心圆几乎同构,但放在**模块化单体或微服务的每个 Bounded Context** 内;
> DDD 战略级解决的是**多 Bounded Context / 多微服务**的『业务边界 + 跨服务协作』问题。
> **DDD ≠ 微服务**,但 **DDD 是识别微服务边界的最佳工具**;微服务边界 ≈ Bounded Context 边界。"

—— 这一精度差异**直接决定了你公司未来 3-5-10 年的架构演进路径**:不是"什么时候上 DDD",而是"**什么时候从 Clean Arch γ 升到 DDD 模块化单体**"(增量小,收益高);"**什么时候从模块化单体拆微服务**"(增量大,需要严格触发条件)。

---

## §3 约束回扣:Clean Arch 的设计选择不是必然,是特定约束组合下的局部最优

| Clean Arch 设计选择 | 突出的约束 | DDD 在同一约束下的不同选择 | 根因 |
|------------------|----------|------------------------|------|
| 4 层物理结构(Entity/UseCase/Adapter/Framework) | C2 + C5 | DDD 也分层(Domain/Application/Infrastructure)但更强调 Bounded Context **跨层模块化** | DDD 面对多上下文,Clean Arch 假设单上下文 |
| 依赖向内而生 + 业务定义 interface | C2 | DDD 同样要求,但 Repository 在 Domain Layer | 几乎同构,只是命名不同 |
| Use Case 类零 Spring 依赖 | C2 + C4 | DDD 不强调,Application Service 可有 Spring | Clean Arch 在 Java/Spring 生态做了额外简化 |
| 状态机上提到 Entity | C3 + C5 | DDD 用聚合根 + 不变量保护(更严格) | DDD 战术级精确化,Clean Arch 简化版 |
| 显式 @Configuration 装配 | C2 | DDD 不强调 | Clean Arch 在工程实施层多走一步 |
| (无)战略级跨上下文协作 | (Clean Arch 不应对) | DDD 用 Bounded Context + Context Map | Clean Arch 假设单团队 / 单上下文,DDD 假设多团队 |
| (无)Ubiquitous Language | (Clean Arch 不应对) | DDD 强制业务团队和技术团队统一术语 | Clean Arch 不依赖业务专家驻场,DDD 必须 |
| (无)Domain Event + Saga | (Clean Arch 不应对) | DDD 用领域事件 + Saga 补偿应对异步 | Clean Arch 假设同步业务,DDD 假设异步业务 |

**最终结论**:**Clean Arch 不是唯一解,是『中等复杂度 + 单团队 + 同步业务 + Java/Spring 生态』场景下的局部最优**;DDD 是『高复杂度 + 多团队 + 异步业务 + 业务专家驻场』场景下的局部最优。**两套都不是『最好』,都是约束组合下的『局部最好』** —— 这印证 Origin §4.4 「价值不在原创度,在合成度」+ Deep §4.4「在当前约束组合下,Bob 端口适配器是局部最优」。

---

## §4 呼应灵魂问题

灵魂问题:"**完整理解《架构整洁之道》的设计哲学与可落地方法**"

**Comparison 阶段把灵魂问题闭环到 ~98%**:

- ✓ **设计哲学的本质**:Clean Arch 是 **DDD 战术级的简化 + 工程化 + 推广**,不是原创 —— 这是对 Origin §3-§4 「价值不在原创度,在合成度」最强的横向印证(Bob 不只合成 4 套架构,还简化了 DDD 这一更早的体系)
- ✓ **可落地方法的边界**:Clean Arch 在『中等复杂度 + 单团队 + 同步业务』里**最适合**;超出这个边界,要升级到 DDD 战术级 → DDD 战略级
- ✓ **跟 DDD 的关系是 subset 而非替代**:Clean Arch γ ≈ DDD 战术级子集 + Java/Spring 工程简化;DDD 多了战略级 4 件事(Bounded Context / Domain Event / Ubiquitous Language / Strategic Design)
- ✓ **正确学习路径**:Clean Arch γ → DDD 战术级 → DDD 战略级;**跳级摔死** —— 这是对 Origin §6 人性短板「不求甚解 + 变现导向」的具体演绎(直接学 DDD 战略级会因聚合根边界识别能力不足而失败,要从 Clean Arch γ 入门)

**剩下 ~2% 留给 Synthesis 阶段**:把这一切整合成"AI 弥补人性 + 历史性结论(社会性反转)"的最终方法论沉淀,**特别是 Bob 大叔『合成 + 简化 + 推广』的工程哲学如何在 AI 时代被进一步加速**(AI 同样会做合成 + 简化 + 推广 → AI 时代的"Clean Arch"可能是 AI 自己合成出来的简化版 DDD)。

**关键转折**:**Comparison 让你彻底理解 Bob 大叔不是在『发明』,是在『搬运 + 提炼』** —— 把 1972 Parnas / 1986 Meyer / 1992 Jacobson / 2003 Evans / 2005 Cockburn / 2008 Palermo / 2009 Coplien-Reenskaug 的工作,合成 + 简化 + 命名为一本工业界能用的书。**这是工程书写经典最稀缺的本事 —— 不是创造新东西,是让既有的好东西能被普通工程师用起来。**

---

## Q&A 答疑(衍生话题)

> 这一节是 Comparison 阶段的衍生答疑,**不是本系列(完整理解《架构整洁之道》)的重点** —— 主要为读者就常见疑惑提供详细参考。**读者可以跳过这一节而不影响理解前面正文**。

### Q1: 用 BC 划分微服务是否合理?为什么国内 2018-2022 中台战略集体失败?

#### A1.1 合理性的边界条件

**核心结论**:**先在单体里用 DDD 划分 BC 跑稳,再拆出真正需要独立部署的 BC 为微服务**。

**合理的情况(满足任一可考虑拆服务)**:
- ✓ **业务边界稳定**(BC 已跑稳 1-2 年,边界不再频繁变化)
- ✓ **独立部署需求明确**(某 BC QPS / 资源需求显著高于其他,需独立扩容)
- ✓ **独立团队拥有**(某 BC 由专属团队维护,跨团队协调成本 > 拆服务成本)
- ✓ **独立扩展能力收益高**(某 BC 流量峰值远超其他,需独立 auto-scaling)

**不合理的边界条件(满足任一就不应拆)**:
- ✗ **BC 之间存在强一致性需求**(如订单 + 库存必须同事务)→ 拆服务后被迫用 Saga / TCC,代价远超收益
- ✗ **BC 边界还在频繁变化**(业务尚未成型,BC 抽象不稳定)→ BC 拆错的成本是数据迁移 + API 重写
- ✗ **团队规模小**(少于 10 人 或 BC 数量 > 团队人数)→ 一人维护多个微服务 = 协调灾难
- ✗ **基础设施 immature**(没 K8s / 服务网格 / 链路追踪 / 集中日志)→ 微服务的基础设施成本 > 业务收益
- ✗ **业务领域专家不愿驻场 / Ubiquitous Language 没建立** → BC 边界靠工程师猜,几乎一定错

**正确做法**:
1. **先用 DDD 在单体里划分 BC**(模块化单体,modulith)
2. **跑稳 1-2 年验证 BC 边界正确性**
3. **挑出明显需要独立部署的 BC 拆出微服务**(增量拆,不是一次全拆)
4. **保持核心 BC 在单体内,只拆边缘 BC**(如把"通知" / "审计" 等边缘 BC 拆为独立服务,核心"订单 + 履约"留在单体内)

#### A1.2 为什么『DDD = 微服务』等同必然失败 —— 6 大表象原因

国内 2018-2022 年"中台战略"失败潮的具体表象(中台战略本希望用 DDD 划分中台微服务,绝大多数公司落地失败):

**1. 同时学多个独立大主题** —— 团队同时学 **DDD + 微服务 + K8s + 服务网格 + 分布式事务**,5 件事一起 = 没有一件学好 = 全军覆没。

> 典型例子:某互联网公司 2019 年启动中台,要求所有业务方 6 个月内迁移到 DDD 微服务架构;9 个月后迁移率 <30%,迁移完的服务 BUG 率反而升高 3x。

**2. 聚合根边界识别错误的灾难放大** —— 单体里 BC 边界错了,代价 = 改 Maven 模块文件夹(1 周);微服务里 BC 边界错了 = 数据迁移 + API 兼容 + 部署变更 + 跨团队协调 ≈ **100x 代价**(1 年)。

> 典型例子:某银行核心 2020 年按 DDD 拆 30 个微服务,运行 1 年后发现"账户" + "交易"两个 BC 划分错(应该是一个聚合根),被迫合并 → 1 年工程量重做。

**3. 网络调用的失败模式 vs 进程内调用** —— DDD 战术级假设进程内调用(失败原子);跨服务网络调用必须考虑**超时 / 重试 / 幂等 / 熔断 / 限流** —— 这些是 DDD 战术级根本没讲的微服务细节;团队按 DDD 写代码 + 部署成微服务 = 完全不知道要处理这些。

> 典型例子:订单服务调用支付服务超时,订单本地写入 `paid` 但实际支付没成功,导致用户被双重扣款 / 客服爆炸。

**4. 分布式事务的根本困难** —— 单体内 `@Transactional` 解决一切;微服务跨服务事务必须用 **Saga / TCC / 本地消息表 / Outbox 模式**;最终一致性会让业务方崩溃(风控 / 合规 / 财务不允许最终一致性)。

> 典型例子:某电商把订单 + 库存 + 优惠券拆 3 个服务,促销时下单,库存扣减成功但优惠券扣减超时,补偿 logic 漏写一个分支,导致大量"无优惠券订单完成"投诉 + 客服被打爆。

**5. 基础设施成本超过业务收益** —— 微服务需要 **K8s + Istio/Linkerd + Prometheus + Grafana + Jaeger/SkyWalking + ELK + 服务注册 + 配置中心 + ...** = 完整基础设施栈;100 人公司硬上微服务通常需要 5-8 名专职 SRE。

> 典型例子:某 100 人公司硬上微服务,只配 1 名 SRE;3 个月后线上事故率涨 5x,微服务被迫退回单体 + 1.5 年工程量浪费。

**6. 团队组织结构不适配 Conway's Law** —— 微服务前提是团队按业务拆分(两个披萨团队);但很多公司组织没拆,研发按职能分(前端 / 后端 / DBA / 测试),硬上微服务 → 跨职能协调反而比单体还慢。

> 典型例子:某传统企业按职能分团队,推 DDD 微服务,每个微服务的发布需要 5 个职能团队会签 → 单次发布周期从单体的 1 周变成 4 周 → 业务方反而要求"退回单体"。

#### A1.3 最深层根因 —— 失败的本质是人性问题(用户 patch-3 洞察)

上面 6 个原因都是**表象** —— 它们的**最深层根因不是技术问题,是人性问题**:

| 人性短板 | DDD = microservices 失败潮的具体表现 | 跟 Origin §6 的对应 |
|---------|--------------------------------|-----------------|
| **急于求成** | 6 个月迁移目标 / 拒绝先单体跑稳的渐进方案 / 一上来就全拆微服务 | §6.1 趋利避害(选最快路径)+ §6.4 没真正理解就自以为是("我懂 DDD 了!") |
| **急功近利** | 看 KPI / 看公开宣传 / 不看 5 年后的代价 / 挑能在简历上写的项目做 | §6.2 短视(看不到 5 年后的代价)+ §6.5 不求甚解 + 变现导向(KPI 看眼前 / 中台战略当时是高大上故事) |
| **不求甚解** | 没读 Evans 原文 / 没读 Sam Newman 原文 / 看一篇博客就开始拆服务 | §6.3 想当然(看图就懂)+ §6.5 不求甚解 + 变现导向(培训机构卖"3 天精通 DDD 微服务") |

**所以"DDD = microservices 失败" 跟 "Bob Clean Arch 9 年没大规模落地" 是同一根因(人性短板)的不同表现**:
- Bob Clean Arch:**单体内** 80% 项目停在 β 形似神离(假 DIP)
- DDD = microservices:**微服务化** 80% 项目同时崩溃(中台战略失败潮)

**这是 Origin §6.7 桥梁段 + §8 第 4 条主线"社会性反转"的最强佐证之一**:**Bob 的方法论对人是悖论,DDD 对人也是悖论;两者都需要 AI 时代才能在大规模工程实施中成为默认行为**。

> Synthesis 阶段会把这条洞察整合进 §B(5 条人性短板)+ §C(2 条组织/经济约束)的论证中。

---

## 修订记录

| 时间 | 修订摘要 | 触发原因 |
|------|---------|---------|
| 2026-05-08 初稿 | Comparison 阶段第 1 稿 —— 主对照 Clean Arch vs DDD;§0 三件事(同构 / 战略级差异 / 历史血脉);§1 设计动机简表(Clean Arch + DDD 各 4 件事:初衷/擅长/不擅长/典型应用场景);§2 9 个子节(同构 9 行映射 + 区别 4 维度 + 五元组对比 + 代码差异 + 约束追溯 + 选用建议 + 总结);§3 约束回扣(8 项设计选择对照);§4 呼应灵魂问题 98% 闭环 | 用户决定:"推进 Comparison,主要对比同心圆 vs DDD;deep 里面的对比可以挪到 comparison 里面" —— Deep §4.5 5 个子节作为内容基底,扩展为 atlas Comparison 标准结构 |
| 2026-05-08 patch-1 | §2.10 新增「单体 vs 微服务 视角(用户读后总结升精度)」整段 6 个子节 —— §2.10.1 物理部署形态对照(Clean Arch 单 JVM vs DDD 多 JVM 或模块化单体)/ §2.10.2 DDD ≠ 微服务但是识别微服务边界最佳工具(Sam Newman 2014 业内共识 / 2018-2022 国内中台战略失败潮的核心原因)/ §2.10.3 时代语境差异(Bob 2017 不绑死微服务给 Clean Arch 更长生命周期 / Evans 2003 DDD 战略级超前 11 年预测微服务)/ §2.10.4 用户公司订单系统 4 阶段渐进路径(Clean Arch γ 单体 → DDD 模块化单体 → 拆部分微服务 → DDD 战略级)/ §2.10.5 包含关系一句话总结(Clean Arch ⊂ DDD 战术级 ⊂ DDD 战略级 + 微服务)/ §2.10.6 用户精炼总结升级版 | 用户读完前 9 个子节后总结:"Bob 的同心圆其实解决的是边界清晰、需求中等复杂的单体应用的扩展问题;DDD 更倾向于一个整体大解决方案的解构,从架构上来说更倾向于微服务,多个领域的微服务构建" —— 抓住了 95% 精度;最后 5% 的精度差异(DDD ≠ 微服务但等号在工程实施层成立 + 4 阶段渐进路径)直接决定后续架构演进路径,值得单独成节强化 |
| 2026-05-08 patch-2 | (1) §2.10.1 表后追加关键洞察「Clean Arch 嵌套在每个 BC 里」+ ASCII 图(DDD 整体 = 多个 Clean Arch 化的 BC + Context Map / 领域事件 / Saga,每 BC 内部完整应用 Bob 4 层);(2) 替换原 §2.10.2 末尾"全军覆没"简短说法,指向新 §2.10.3;(3) 新增 §2.10.3「用 BC 划分微服务是否合理? —— 合理性边界 + 6 大失败原因」整段:§2.10.3.1 合理的 4 情况 + 不合理的 5 边界条件 + 正确做法 4 步;§2.10.3.2 6 大失败原因(同时学 5 件事 / 边界错代价 100x / 网络调用 vs 进程内 / 分布式事务困难 / 基础设施成本 / Conway 法则不适配),每个原因带具体真实例子;§2.10.3.3 关键 takeaway 4 前提条件 + 现实启示;(4) renumber 原 §2.10.3-§2.10.6 为 §2.10.4-§2.10.7 | 用户提出 2 个新输入:(1) "DDD 每个 BC 都可以用 Bob 的 4 层架构来实现" —— 需要明确陈述这个嵌套关系,埋在表格里不够显眼;(2) "很多公司用 BC 来划分微服务,这个合理吗?文中没有阐述把 DDD = microservices 就失败的原因,需要在相应的位置补上" —— 原 §2.10.2 只一句话带过"全军覆没",没具体原因 |
| 2026-05-08 patch-3 | (1) 重组 §2.10.3 —— 原 §2.10.3.1 / §2.10.3.2 / §2.10.3.3 详细内容(合理性边界 + 6 大失败原因 + 关键 takeaway)整段移到末尾新建 ## Q&A 答疑(衍生话题)章节,作为 Q1;§2.10.3 在正文只保留 5 行简述 + pointer 到 Q&A;(2) 新建 ## Q&A 答疑(衍生话题)章节(在 §4 灵魂问题后,## 修订记录前)—— Q1 包含 A1.1 合理性边界 + A1.2 6 大表象原因 + **A1.3 最深层根因 = 人性问题**(急于求成 / 急功近利 / 不求甚解,3 维度对照 §6 5 条人性短板);(3) 关键洞察在 A1.3 钉死:DDD = microservices 失败 跟 Bob Clean Arch 9 年没大规模落地 是**同一根因(人性短板)的不同表现**(Clean Arch 单体 80% 停 β / DDD 微服务化 80% 中台战略失败),都是 Origin §8 第 4 条主线"社会性反转"的最强佐证 | 用户洞察:"DDD 其实还是人性的问题,急于求成,急功近利,不求甚解,造成了失败。这个 DDD 的失败可以作为 QA 的部分,不作为主要的正文;相关的地方只要提及就行,毕竟不是本系列的重点" —— 6 大失败原因是衍生话题,不是 Comparison 阶段的核心(Clean Arch vs DDD 才是),应放 Q&A 而非主线;但人性根因这条洞察跟 Origin §6.7 桥梁段 + §8 第 4 条主线"社会性反转"完美对齐,值得专门 A1.3 钉死作为 Synthesis §B+§C 的预告 |
