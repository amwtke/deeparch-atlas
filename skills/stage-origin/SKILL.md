---
name: atlas-stage-origin
description: atlas 套件的 Origin 阶段教学子 skill。讲解一个技术"是怎么来的"——创作者面对的烦躁、初试、死胡同、顿悟、成型与遗憾。**必须使用 web search 查一手资料**(创作者访谈、邮件列表、RFC、传记等),不允许编故事。讲完调用 three-options 进入 🌉分水岭——让用户决定"满足导出"或"继续 Deep"。仅由 atlas 入口 SKILL.md 调度时使用,不应被独立调用。
---

# atlas / stage-origin

## 阶段目标

让用户理解:**这个技术不是凭空发明,是创作者在特定历史约束下做出的局部最优选择**。

创作者当年面对的约束组合 ≠ 今天的约束组合——这个差距决定了今天我们看到的设计有哪些"历史债"。

---

## 硬约束:必须使用 web search

这是 Origin 阶段与其他阶段最大的差异——**严禁基于训练数据编故事**。

收到调度后,**立即使用 web search** 查找:

1. **创作者本人的一手发言**(优先级最高):
   - 访谈(文字 / 视频)
   - 博客、推特、邮件列表发言
   - 项目早期 RFC、commit 历史、设计文档
   - 论文(尤其是创作者署名的)
2. **创作者传记、回忆录、序言、后记**
3. **关键时间节点**:第一次提出 / 第一版发布 / 重大转折

搜索关键词建议(以 malloc 为例):
- "Doug Lea malloc history"
- "dlmalloc origins paper"
- "Doug Lea SUNY Oswego"
- "ptmalloc history Wolfram Gloger"

**禁止**:
- 没查资料就基于训练数据写故事
- 把推测当事实
- 引用未经查证的二手转述

---

## 讲解结构(300~400 行)

输出到 `stages/04-origin.md`:

```markdown
# 阶段 4:<主题> 是怎么来的

## 引子:创作者当年的烦躁
[他遇到了什么具体痛苦?用一手资料引用的话,带 URL 标注]

例:
> Doug Lea 在 1996 年的 paper 序言里写道:"在 1980 年代末,我做并发数据结构研究,
> 顺手用 SunOS 4 自带的分配器,但发现它的碎片严重到影响实验结果..."
> [来源:Doug Lea, "A Memory Allocator", 1996, https://gee.cs.oswego.edu/dl/html/malloc.html]

## 起:初试
[他第一次尝试是什么?思路是什么?]

## 承:死胡同
[他撞到的墙、走过的弯路 —— 这是 Origin 的灵魂段落]

要求:
- 失败比成功更能让读者理解"为什么最终选了 X"
- 列出至少 2 个被放弃的方案 + 各自为什么放弃
- 这些放弃的方案可能正好是 Comparison 阶段会出现的对比对象

## 转:顿悟
[他怎么找到关键 insight 的]

通常不是单点发明,而是**已有 trick 的新组合**:
- 例如 Doug Lea:Knuth boundary tag(1968)+ bin 分档 + wilderness chunk + mmap 大对象
- 关键不是发明 trick,而是**针对当时的工作负载选对组合**

## 合:成型与遗憾
[最终方案 + 它后续的演化 + 创作者本人的反思]

要求:
- 必须包含"遗憾" —— 哪些设计选择今天看是技术债?
- 创作者本人对某些设计的反思(从一手资料里找)
- 后续的演化(被谁 fork、改造,如 ptmalloc / jemalloc / tcmalloc)

## 《约束回扣》
[创作者当年面对的约束组合 ≠ 今天的约束组合]

例:
> "Doug Lea 1987 年面对的约束是 C1+C2+C5+C6,**C4(多核)那时还不存在**。
> 这就是为什么 ptmalloc2 / jemalloc / tcmalloc 都要在 chunk 之上重做一层——
> 它们在偿还 1987 年单核假设留下的债。"

## 呼应灵魂问题
[一段话,从历史角度回看灵魂问题]

例如灵魂问题"chunk 为什么是 16B 不是 8B":
> "Doug Lea 在 1987 年决定 16B 时,面对的约束是 32 位机器上 size_t 是 4B,但他
> 加入了 prev_size 字段(也是 4B)和 size+flags 字段(4B)。1996 年迁移到 64 位时,
> 这两个字段自然变成 8B 各一个,共 16B。所以 16B 不是凭空选的,是 64 位指针 ABI
> 的自然结果。"

## 一手资料引用列表
[必须明确标注每条引用的 URL、年份、作者]

例:
- Doug Lea, "A Memory Allocator", 1996. https://...
- Doug Lea, "Some storage allocator implementation issues", c.l.c-club mailing list, 1991. https://...
- Wolfram Gloger, "ptmalloc history", LinuxThreads mailing list, 1996. https://...

## 无一手资料的部分(如果有)
[坦诚标注:"以下细节无一手资料,以下为基于二手转述的推测,可信度较低"]
```

---

## 执行流程

1. **静默标记阶段开始**(调用 progress-tracker,对话不提)
2. **使用 web search** 查找一手资料(必做,不可跳过)
3. **生成 stages/04-origin.md** 第一稿,引用必须带 URL
4. **在对话中自然地讲故事 + 列资料来源**(不说"Origin 阶段已写入..."):
   ```
   我去查了一手资料,把它的来路(顿悟时刻 + 死胡同 + 遗憾)整理在了
   atlas-output/.../stages/04-origin.md,引了 X 篇 <列关键来源>。

   关键转折:<一句话复述顿悟时刻>。

   先问你一个:<反问>
   ```
5. **进入 user-pacing 协议**(skills/three-options/SKILL.md)处理常规追问/新视角,**patch stages/04-origin.md**
6. **🌉 分水岭节点**(本阶段独有):当用户**对 Origin 内容本身没有更多想问**时,**显式问一次** —— 这不是普通的"推进信号",而是一个**深度选择**:

   ```
   到这里,你已经能跟别人完整聊清楚 <主题> 是什么、为什么、怎么工作、怎么来的。
   接下来想怎么走?
   - 想继续深入源码层(机制级精确剖析、反事实小试)→ 我们继续
   - 觉得到这里够了,想直接收束成一份综合长文 → 我可以跳过 Deep / Comparison
   - 还想就 Origin 这部分再聊聊 → 直接说

   你怎么想?
   ```

7. **分水岭路由**(根据用户的明确表达):
   - "够了 / 收束 / 导出 / 不要 Deep" → 加载 `skills/stage-synthesis/SKILL.md`(用现有 4 阶段的产物做轻量 Synthesis),完成后 final-export
   - "继续深入 / 想看源码 / 走 Deep" → 加载 `skills/stage-deep/SKILL.md`
   - 用户继续追问 Origin → 回到 user-pacing 协议,patch stages/04-origin.md

   **分水岭节点不能省略** —— 这是用户对"深度走多深"的关键自主权,不能 Claude 替他决定。

---

## 关键设计:为什么 Origin 在 How 之后、Deep 之前

这是 atlas v2 → 套件版的核心顺序设计:

- **What → Why → How → Origin** 形成一个**完整的"基础认知闭环"**:
  技术是什么、为什么需要、怎么工作、历史怎么来——读者到这里已经能跟人聊这个技术了
- 这是普通用户可以停下的合理位置
- Deep / Comparison / Synthesis 是专业级钻研,不是所有人都需要

**分水岭让用户主动选择**——而不是 Claude 替他决定走多深。

---

## 反模式

1. **不查 web search 直接基于训练数据编故事** —— Origin 的硬底线
2. **引用没标 URL 和年份** —— 一手资料必须可验证
3. **没有"承:死胡同"段落** —— Origin 的灵魂段落,必须有失败
4. **没有"合:遗憾"段落** —— 没有遗憾就是吹捧,不是分析
5. **不用分水岭三选项,用普通三选项** —— 错过让用户主动选择深度的关键时机
6. **分水岭"满足导出"路径直接跳到 final-export 而跳过 Synthesis** —— Synthesis 必须有(轻量版)
