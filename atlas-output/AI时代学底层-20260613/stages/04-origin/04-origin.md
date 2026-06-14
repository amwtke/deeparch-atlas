# 阶段 4：现实对照——权威与实证，给我们的结论做交叉验证

> 说明：用户判断"AI 这波**史无前例**"，故**不套历史类比**。改为去查**当下的权威声音 + 实证研究**，看我们前三阶段从第一性原理 + 用户实战推出的结论，是不是"空穴来风"。
> 规矩：只引**可查证**来源、附 URL；且**不只挑附和的**——把挖到的**最强反证**也端上来。只有这样，"不是空穴来风"才真的立得住。

## §0 我们要验的结论（回顾）

1. **AI 是放大器，不是均衡器**（产出 = 判断力 × 增益）；
2. **底层认知长出的"判断力/尺子"是那个乘数**（更懂底层 → 更能驾驭 AI）；
3. **验证 / 兜底是瓶颈**（C4、C6）；**AI 会自信地错**（C1、C3）。

下面五条佐证 + 一条反证，逐条对照。

## §1 佐证一：「AI 放大已有的专长」——几乎是我们论点的逐字版

**Simon Willison**（Django 共同创始人、Datasette 作者，25+ 年从业）：

- 他直接写道：**"LLMs amplify existing expertise"**（LLM 放大你已有的专长），并坦言自己之所以用得好，源于 **"25+ years of professional coding experience"**。
- 又说：**"Using LLMs to write code is difficult and unintuitive."**（用 LLM 写代码是困难且反直觉的）——不是谁都能轻松驾驭。

→ 对照我们的 **①放大器 + ②底层是乘数**。注意"放大已有专长"和"信噪比由你定"是一回事。
来源：[How I use LLMs to help me write code — Simon Willison](https://simonw.substack.com/p/how-i-use-llms-to-help-me-write-code)

## §2 佐证二：收益**只落在资深身上**（实证 / 顶刊）

发表在 **《Science》** 的研究《Who is using AI to code? Global diffusion and impact of generative AI》据报道发现：genAI 带来的生产力提升，**只在资深开发者身上统计显著**；**早期职业（初级）开发者没有统计显著的收益**。

→ 对照我们的 **①放大器 ≠ 均衡器**：差距不是被抹平，而是被放大；初级不受益（甚至翻负）。
来源：[Science, doi:10.1126/science.adz9311](https://www.science.org/doi/10.1126/science.adz9311)

## §3 佐证三：最后 30% 与"审查瓶颈"——验证是地板

**Addy Osmani**（Google 工程负责人）"The 70% Problem"：

- **70%**："AI can rapidly produce maybe 70% of the code... the scaffolding, the obvious patterns."
- **最后 30%**："edge cases... integration with production systems... making sure that your security, your API keys... that can be just as time consuming as it ever was."
- AI 产出 **"deceptively convincing"**（骗人地像对的），实则 **"held together with duct tape behind the scenes"**（背后拿胶带粘的）。
- **"code review is becoming the new bottleneck."**（代码审查正在变成新瓶颈。）

→ 对照 **C4 验证是地板 / C6**；以及 **C1 自信地错**——"deceptively convincing" 就是你说的"**完美无瑕的错**"。
来源：[AI's 70% problem — Addy Osmani (Zed blog)](https://zed.dev/blog/ai-70-problem-addy-osmani) · [原文 substack](https://addyo.substack.com/p/the-70-problem-hard-truths-about) · [The New Stack: AI 制造资深工程师的审查瓶颈](https://thenewstack.io/is-ai-creating-a-new-code-review-bottleneck-for-senior-engineers/)

## §4 佐证四：人不能不盯——监督无法外包

**Simon Willison**：

- **"The one thing you absolutely cannot outsource to the machine is testing that the code actually works."**（唯一绝对不能外包给机器的，就是验证代码真的能跑。）
- **"If you haven't seen it run, it's not a working system."**（没亲眼见它跑起来，它就不算能用的系统。）
- 他的心智模型：LLM 是一个 **"over-confident pair programming assistant"**（过度自信的结对助手）。

→ 对照 **C4 必须有人验证 + 兜底**（你那"对账"）；以及 **C1/C3 自信地错**（over-confident）。
来源：[How I use LLMs to help me write code — Simon Willison](https://simonw.substack.com/p/how-i-use-llms-to-help-me-write-code)

## §5 佐证五：底层 / fundamentals **更重要了**（共识合唱）

多个**独立**来源指向同一句话——"**fundamentals matter more than ever**"：

- "embracing fundamental practices provides the necessary structure, discipline, and **critical judgment to guide AI effectively**, manage its risks..."
- "True creativity comes from a **deep understanding of the system's structure**... fundamentals matter more than ever."

→ 直接对照你的**灵魂问题**："更懂底层 → 更能驾驭 AI"。这不是你我私见，是一波独立声音的共识。
来源：[The Enduring Craft — Fred Pope](https://www.fredpope.com/blog/development/enduring-craft-software-fundamentals-ai) · [Why Fundamentals Matter More Than Ever — Kayvan Kaseb](https://medium.com/kayvan-kaseb/why-fundamentals-matter-more-than-ever-for-software-engineers-in-the-age-of-creativity-and-ai-205719c75865) · [QCon SF 2025：AI 时代的软件工程基本功](https://qconsf.com/training/nov2025/fundamentals-software-engineering-age-ai)

## §6 诚实的反证：METR——资深开发者用 AI 反而**慢了 19%**

这是我挖到**最强的反证**，必须端上来（只挑附和的就是自欺）：

**METR 随机对照实验（2025）**：

- 16 名资深开源开发者，在自己**贡献多年、平均 22k+ stars、1M+ 行**的成熟仓库上做 246 个真实 issue；
- **"developers take 19% longer to complete issues"**——用 AI 反而**慢了 19%**；
- 更扎心的**认知差**：他们事前预期 AI 提速 **+24%**，事后**仍以为提速了 +20%**——而实测是 **−19%**；
- 用的还是当时前沿的 **Cursor Pro + Claude 3.5/3.7 Sonnet**。

来源：[METR, Measuring the Impact of Early-2025 AI on Experienced OS Developer Productivity](https://metr.org/blog/2025-07-10-early-2025-ai-experienced-os-dev-study/) · [arXiv 2507.09089](https://arxiv.org/abs/2507.09089)

### §6.1 它推翻我们了吗？没有——它把"倍率"那条**精确化**了

- METR 测的是**资深开发者最熟的主场**：他们本就是这套 **1M+ 行**代码的最优解，代码量巨大——**正好撞上 C2（上下文装不下、看不见全局）的硬核**。AI 在你的主场帮不上，反而加了一层验证摩擦（**C6**）。
- 这跟你的 **4–10× 不矛盾**：你的高倍率多发生在**跨域、铺量、非你已精通的主场**（一人 cover 后端→前端→QA→部署）；在你已经"门清"的复杂主场，AI 的边际收益会缩、甚至转负。**倍率视场景而定，可正可负**——这正是"乘法器"而非"恒定加速"的题中之义。
- 而那个**认知差**（以为快、其实慢）恰恰是我们**最深论点的铁证**：**你连"AI 到底帮没帮上"都得靠判断力/度量才看得清**。分不清的人，会**一边变慢、一边自我感觉良好**——这就是没有"尺子"的人的典型状态。

> 一句话：最强反证没动摇"**放大器 ≠ 均衡器 + 判断是乘数**"的内核，只把"4–10×"修正成"**视场景而定、可正可负**"。一个诚实承认"有时会更慢"的结论，比无脑的"AI 必快"**更可信**。

## §7 小结：不是空穴来风

我们从第一性原理 + 你的实战推出的结论，和**独立的权威声音 + 实证数据**，在同一处收敛：

| 我们的结论 | 外部佐证 |
|-----------|---------|
| 放大器 ≠ 均衡器 | Science（收益只对资深）· Willison（"amplify existing expertise"） |
| 验证 / 审查是瓶颈，监督不能外包（C4/C6） | Osmani（"review is the new bottleneck"、最后 30%）· Willison（"cannot outsource testing"） |
| AI 自信地错（C1/C3） | Willison（"over-confident"）· Osmani（"deceptively convincing"） |
| 更懂底层 / fundamentals 更重要（灵魂问题） | "fundamentals matter more than ever" 合唱 |
| 倍率视场景、可正可负（诚实修正） | METR（资深主场 −19% + 认知差） |

**结论站得住，而且因为带上了反证，站得更稳。**

## 资料引用列表（均可点开查证）

1. Simon Willison, *How I use LLMs to help me write code* — https://simonw.substack.com/p/how-i-use-llms-to-help-me-write-code
2. *Who is using AI to code? Global diffusion and impact of generative AI*, **Science** — https://www.science.org/doi/10.1126/science.adz9311
3. Addy Osmani, *The 70% Problem* — https://zed.dev/blog/ai-70-problem-addy-osmani · https://addyo.substack.com/p/the-70-problem-hard-truths-about
4. The New Stack, *Is AI Creating a New Code Review Bottleneck for Senior Engineers?* — https://thenewstack.io/is-ai-creating-a-new-code-review-bottleneck-for-senior-engineers/
5. METR, *Measuring the Impact of Early-2025 AI on Experienced OS Developer Productivity* (2025-07-10) — https://metr.org/blog/2025-07-10-early-2025-ai-experienced-os-dev-study/ · arXiv https://arxiv.org/abs/2507.09089
6. Fred Pope, *The Enduring Craft* — https://www.fredpope.com/blog/development/enduring-craft-software-fundamentals-ai
7. Kayvan Kaseb, *Why Fundamentals Matter More Than Ever* — https://medium.com/kayvan-kaseb/why-fundamentals-matter-more-than-ever-for-software-engineers-in-the-age-of-creativity-and-ai-205719c75865

## 修订记录

| 时间 | 修订摘要 | 触发原因 |
|------|---------|---------|
| 2026-06-14 | 建 Origin（改为"现实对照·权威佐证"，非历史）：5 条佐证（Willison "amplify existing expertise"、Science 收益只对资深、Osmani 70% 问题 + 审查瓶颈、Willison 监督不能外包、fundamentals 合唱）+ 1 条诚实反证（METR −19% + 认知差，用 C2/C6 化解为"倍率视场景"）；全部带 URL | 用户要求跳过历史、改查权威佐证、并明确"不只挑附和的" |
