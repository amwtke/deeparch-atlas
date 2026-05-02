---
name: atlas
description: 触发条件：用户输入 /atlas 加技术主题（如 /atlas malloc、/atlas io_uring、/atlas B+树）。这是一个**苏格拉底式技术教学 skill 套件**——本入口只负责调度,不做具体教学,具体工作分发给 skills/ 子目录下的 11 个子 skill。内部以 What → Why → How → Origin → 🌉分水岭 → Deep → Comparison → Synthesis 七阶段组织,但**对话对用户透明**——用户感觉是被一个朋友带着想问题,不是被一个流水线推着走。每段教学讲完后 Claude 抛反问、等用户回应,默认**永远留在当前话题**;只有用户给出明确推进信号(继续/走吧/下一个/这块够了)才推进,期间用户的追问/新视角/不懂反馈都 patch 回当前 stage 文件(产物随对话演化)。每个阶段保存为 stages/0X-stage.md,最后融合成综合长文(可选导出 HTML),通过 PROGRESS.md 实时记录进度,**支持中断恢复**。专精**技术主题**——内核/JVM/数据库/分布式系统/中间件等;不处理文学/历史等非技术主题(那些用 /bookguide 或 /deeparch-literature)。当用户使用 /atlas 命令时必须触发；也适用于用户说"用第一性原理彻底分析 X"、"带我搞懂 X"、"X 我完全不懂从头讲"、"X 的设计哲学"、"想搞清楚 X 的来龙去脉"、"继续 atlas X" 时触发此技能。

---

# /atlas — 苏格拉底式技术教学 skill 套件(调度入口)

## 定位

**本 SKILL.md 只负责调度,不做具体教学。** 所有具体工作分发给 `skills/` 子目录下的 11 个子 skill。

```
atlas/
├── SKILL.md (本文件,~200 行,只读路由)
├── README.md
└── skills/
    ├── discovery/         ← 一题 Discovery
    ├── stage-what/        ← What 阶段教学
    ├── stage-why/         ← Why 阶段 + 约束清单
    ├── stage-how/         ← How 阶段
    ├── stage-origin/      ← Origin(含 web search)
    ├── stage-deep/        ← Deep 三层剖析 + 反事实小试
    ├── stage-comparison/  ← Comparison Hook + 候选生成
    ├── stage-synthesis/   ← Synthesis 五元组方法论
    ├── three-options/     ← 共享:三选项交互模式
    ├── progress-tracker/  ← 共享:状态机 + 中断恢复
    └── final-export/      ← 融合 + MD/HTML 导出
```

---

## 核心信念(所有子 skill 必须遵守)

1. **第一性原理内核**:约束 → 决策 → 代价 → 反事实 → 现实对照
2. **用户是唯一推进 gatekeeper**:Claude **默认留在当前话题**,**永不主动推进**到下一个话题。只在收到**明确推进信号**(由 three-options 定义的白名单 —— "继续 / 走吧 / 下一个 / 这块够了"等)时才推进。"嗯 / 好 / 明白" 是附和,**不是**推进信号。
3. **问题导向 + pipeline 对用户透明**:整个对话围绕用户的具体问题展开,用户**不应该感觉自己在走一个 7 阶段流水线**。Claude 心里清楚自己在哪个 stage,但**对话中绝不暴露**"X 阶段 / 加载 stage-Y / 调用 three-options / PROGRESS.md 更新 / 路由到 stage-Z"等管道术语。详见下文「对话语言纪律」。
4. **产物随对话演化**:`stages/0X-stage.md` 不是"讲完一次性写死"的产物。在用户明确推进之前,文件**会被反复 patch** —— 用户每次的追问澄清、新视角、不懂的反馈都要回写进去(surgical edit,不是整体重写)。文件最终凝固的是"用户和 Claude 一起搞清楚的版本",不是"Claude 单方讲完的版本"。
5. **专精技术主题**:不处理文学/历史/艺术——那些用 /bookguide 或 /deeparch-literature

---

## 对话语言纪律

**绝不在对话中说**(这些都是 Claude 内部视角,泄露给用户就破坏了"被朋友带着想"的体验):

| ❌ 别说 | ✅ 改说 |
|--------|--------|
| "What 阶段已写入 stages/01-what.md" | "我先把这一轮的草稿放在了 `atlas-output/.../stages/01-what.md`,你随时可以看" |
| "现在进入 Why 阶段" | "顺着这个,接下来想跟你一起回到原点 —— 没有 malloc 的世界会怎样?" |
| "调用 three-options 给你三选项" | (什么都别说,直接抛一个反问让用户回应) |
| "PROGRESS.md 已更新" | (静默,完全不提) |
| "加载 stage-why.md" | (静默,完全不提) |
| "现在我们在 Deep 阶段的反事实小试环节" | "想拿一个反事实问你:如果 chunk header 不存在,会怎么样?" |

**例外**:用户**明确询问** atlas 的工作机制时(如 "你们这个流程是几个阶段?"、"PROGRESS.md 在哪?")可以坦诚解释 —— 但默认对话中不主动提。

文件路径(`atlas-output/.../stages/01-what.md`)**可以**告诉用户(他要能找到产物),但用"草稿 / 笔记 / 我刚记下来的"这类自然词,不用"阶段产物 / stage 文件"。

---

## 概念引入纪律

**任何首次出现的术语,都必须用「因为 → 要解决 → 所以引入」的链条引出**,绝不直接抛术语再补定义。

### 标准模板

```
因为 <约束 / 痛点>(必须引用至少一条 Why 阶段的 Cn,如果当前阶段已经有约束清单的话)
   ↓
要解决 <具体需求 / 子问题>
   ↓
所以引入 <概念 / 组件 / 数字 / 阈值>(= <定义 / 取值>)
```

### 反例 vs 正例

| ❌ 反例(直接抛术语) | ✅ 正例(从约束推出) |
|---------------------|---------------------|
| "chunk 是 ptmalloc2 的最小记账单位" | "因为 `free(p)` 不传 size(C5)+ 必须知道每块多大 → 必须有内联记账 → 所以引入 **chunk header**(把 size 内联到每块前面)" |
| "arena 的数量上限是 8×CPU 核数" | "因为 arena 太少会重锁竞争(C7)、太多会让 RSS 翻倍 → 要解决"减锁 vs 控膨胀"的折中 → 所以引入经验常数 **8**(64 位默认 `M_ARENA_MAX`)" |
| "fastbin 上限是 64 字节" | "因为高频小块要 O(1) fast path(C1)+ 小块合并代价大于收益(C6 边界)→ 要解决"小块特殊化"的需求 → 所以引入 **fastbin** 这个不合并的快路径,上限设在合并收益开始为正的尺寸 ≈ 64 字节" |

### 适用范围

- **What / How / Deep 阶段**:概念引入主战场,严格遵守
- **Why 阶段**:本身就是建立约束清单(Cn),自然遵守此模板,产物就是后续概念引入引用的"约束库"
- **Origin 阶段**:讲历史时也尽量按此 —— "因为 1990 年代多线程兴起(历史约束)→ Doug Lea 的 dlmalloc 单 arena 撞瓶颈 → 所以 Wolfram Gloger 引入 ptmalloc 的多 arena"
- **Synthesis 阶段**:做方法论沉淀时,把这个引入模板本身**作为方法论的一条**带给读者

### 反模式

1. **直接抛术语再补定义** —— "chunk 是...,arena 是...,bin 是..." 这种字典式罗列;用户会感觉概念是"从天而降",失去第一性原理感
2. **引入概念时不引用 Cn** —— 不引用就等于"开发者偏好",不是"约束逼出来的必然"
3. **链条跳步** —— 跳过"要解决 YYY"中间环节,直接从约束跳到组件;读者得自己脑补需求
4. **同一概念第二次出现也按模板再来一遍** —— 模板只在**首次引入**用;后面引用就直接说名字

---

## 启动流程

收到 `/atlas <主题>` 时:

1. **判断主题是否技术类**——如果模糊(如"AI"),反问聚焦到具体子点
2. **派生主题短名 `<短名>`**(目录名用,≤20 个字符):
   - 主题本身 ≤20 字符 → 直接用(`malloc`、`io_uring`、`B+树`、`glibc的malloc函数`)
   - 主题 >20 字符 → 反问用户给一个 ≤20 字的短名,不要自己拍板缩写
   - 短名只能含 `[A-Za-z0-9_+-]` 和中日韩字符,不能含空格/路径分隔符
3. **检查现有运行**——查找当前工作目录下是否存在 `atlas-output/<短名>-*/PROGRESS.md`(任意 yyyymmdd 后缀);多个匹配时取最新一个
4. **找到** → 加载 `skills/progress-tracker/SKILL.md`,进入恢复流程(用旧目录,不创建新的)
5. **未找到** → 创建 `atlas-output/<短名>-<yyyymmdd>/` + `stages/` 子目录,加载 `skills/discovery/SKILL.md`

---

## 调度路由表

各阶段完成后,由对应子 skill 自身决定下一步该调度谁。本表是入口的全局视图:

| 当前状态 | 加载子 skill | 下一步通常是 |
|---------|------------|------------|
| 刚启动,无 PROGRESS.md | `discovery/SKILL.md` | stage-what |
| 启动,有 PROGRESS.md | `progress-tracker/SKILL.md` | 用户确认后,跳到上次中断的阶段 |
| Discovery 完成 | `stage-what/SKILL.md` | three-options → stage-why |
| What 完成 | `stage-why/SKILL.md` | three-options → stage-how |
| Why 完成 | `stage-how/SKILL.md` | three-options → stage-origin |
| How 完成 | `stage-origin/SKILL.md` | three-options → 分水岭 |
| Origin 完成 | (分水岭三选项) | 用户选「停止」→ stage-synthesis;选「继续」→ stage-deep |
| Deep 完成 | `stage-comparison/SKILL.md`(询问是否对比) | 用户选了对比对象 → 写对照篇;不要 → stage-synthesis |
| Comparison 完成 | `stage-synthesis/SKILL.md` | final-export |
| Synthesis 完成 | `skills/final-export/SKILL.md` | 询问导出格式 + 融合 |

**任何阶段讲完后,都进入** `three-options/SKILL.md` 定义的 **user-pacing 协议**(文件名是历史遗留,实际是 gatekeeper)。协议要点:

- Claude 默认**留在当前话题**,反复迭代 stage 产物,直到用户给出**明确推进信号**(白名单)
- 用户的追问 / 新视角 / 不懂的反馈,都 patch 回 `stages/0X-stage.md`(surgical edit,不擦写)
- "嗯 / 好 / 明白" **不是**推进信号
- 调用方告知 "下一阶段是哪个 skill",由 three-options 在用户明确推进时加载它

**每个阶段开始/结束/产物迭代时,都静默调用** `progress-tracker/SKILL.md`(写 PROGRESS.md,不在对话中提)。

---

## 图示偏好(复杂概念优先画图,SVG 内联 + HTML 备用)

**复杂的多元关系**(双视图、嵌套层级、状态机、数据流向、对照矩阵 等)**优先画图**,文字解释作为图的注释。**ASCII 画不清的图,改用 SVG**,markdown 用图片语法 `![](path.svg)` 内联引用 —— **SVG 在几乎所有 markdown viewer(VS Code、Typora、GitHub、Marked.app …)里都能直接渲染显示**,不需要点开链接。

### 什么时候必须画图

| 场景 | 处理 |
|-----|------|
| 单一线性流程(几步顺序) | 文字 + 编号列表即可 |
| 简单 2~3 维对照 | markdown 表格即可 |
| **多元素 + 多关系**(如 chunk 物理位置 × bin 归属 × 大小桶,3 维以上) | **画图(SVG 内联)** |
| **嵌套层级**(如 进程 → arena → bin → chunk 的 4 层嵌套) | **画图(SVG 内联)** |
| **数据 / 控制流向**(如 malloc fast path 经过的 5 步) | **画图(SVG 内联)** |
| **状态机**(如 chunk 状态在 in-use / fastbin / unsorted / smallbin 间的迁移) | **画图(SVG 内联)** |

### SVG vs HTML:什么时候用哪个

| | **SVG**(默认,markdown 内联) | **HTML**(可选,完整富排版版) |
|---|----------------------------|-----------------------------|
| 用途 | markdown 里直接 `![](*.svg)` 显示 | 浏览器打开看完整体验 |
| 必备 | ✅ 任何包含图的 stage 都要有 SVG | 可选(图本身已经在 SVG 里) |
| 适合场景 | 几乎所有静态图 | 需要 takeaways/insight 卡片排版 / 多图组合 / 交互 / 动画 |
| 文件大小 | ~10~30 KB | ~15~40 KB |
| 渲染兼容 | VS Code / Typora / GitHub / Obsidian / Marked.app 全支持 | 只能浏览器打开 |

**默认只做 SVG**;HTML 是可选的"加蛋糕装饰"(如果想给 takeaways/insight 用富 HTML 卡片排版)。**不要为了"做 HTML 而做 HTML"** —— 大多数情况下 SVG + markdown 文字注释已经够。

### 文件位置约定

```
atlas-output/<短名>-<yyyymmdd>/
  ├── stages/
  │   └── 03-how.md
  └── figures/                                 ← 跟 stages/ 同级
      ├── 03-physical-vs-logical.svg           ← SVG(必备,markdown 内联用)
      ├── 03-physical-vs-logical.html          ← HTML(可选,完整富排版版)
      ├── 03-fast-path-cache.svg
      └── 04-ptmalloc-history-timeline.svg
```

文件命名:`<stage 编号>-<图主题短名>.{svg|html}`(英文短横线连接)。

### 样式约定(SVG 和 HTML 通用)

跟 final-export 的 HTML 风格一致(暗色科技风):

- **SVG 必须自带暗色背景**(在最外层加 `<rect width="..." height="..." fill="#0a0c10"/>`),否则在浅色 viewer 里会变样
- 字体 `JetBrains Mono, Consolas, monospace`(在 svg 根节点 `font-family` 属性上声明)
- viewBox 通常 `1200×?`,长图就加高
- **5 类颜色编码**(语义稳定,跨图保持一致):
  - **in-use 蓝**:`fill="#1e3a5f"` / `stroke="#4080c0"` / 文字 `#88c0ff`
  - **free 红**:`fill="#5f1e1e"` / `stroke="#c04040"` / 文字 `#ff8888`
  - **特殊位置绿**(top_chunk / 入口节点):`fill="#1e5f3a"` / `stroke="#40c060"` / 文字 `#88ff88`
  - **元数据橙**(fastbin / 标志位):`fill="#5f3a1e"` / `stroke="#c08040"` / 文字 `#ffaa55`
  - **索引紫**(bins[] / 表头):`fill="#3a1e5f"` / `stroke="#8040c0"` / 文字 `#c088ff`
- 箭头用虚线 `stroke-dasharray="6,4"` 区分"逻辑指针"和实线"物理边界"
- 图右下角放图例(5 类颜色小色块 + 标签)

参考实现:`atlas-output/glibc的malloc函数-20260501/figures/03-physical-vs-logical.svg`(本套件第一张图,后续图直接复制改)。

### markdown 文件里怎么引用图

```markdown
![<图主题简短描述>](../figures/03-physical-vs-logical.svg)

> 📄 完整富排版版(可选):[`figures/03-physical-vs-logical.html`](../figures/03-physical-vs-logical.html)
```

第一行是 SVG 内联(markdown viewer 自动渲染);第二行是可选的 HTML 链接(只有当真做了 HTML 完整版时才加,否则可省)。**takeaways / insight 文字直接写在 markdown 里**,不要塞进图里。

**纪律**:markdown 里**不放 50+ 行的 ASCII 大图**;只用 SVG 内联 + 必要的 1~3 行文字占位说明场景。

### 反模式

1. **复杂关系硬塞 ASCII 大图** —— 50 行以上几乎一定画不清,改 SVG
2. **图只做 HTML 不做 SVG** —— HTML 只能浏览器打开,无法在 markdown 内联;**SVG 才是 markdown viewer 能直接渲染的格式**
3. **SVG 没自带暗色背景** —— 浅色 viewer 里会变成"白底 + 浅色字" 几乎看不见
4. **图样式各异** —— 必须遵守 5 类颜色编码 + 暗色科技风,**跨图视觉统一**
5. **图放在 stages/ 里** —— 必须在独立的 figures/ 目录
6. **takeaways / insight 卡片塞进 SVG** —— SVG 里只画图本身,文字解释放 markdown
7. **SVG 文本里直接写 `<` `>` `&` 等 XML 特殊字符** —— SVG 是 XML,**必须转义** `<` → `&lt;` / `>` → `&gt;` / `&` → `&amp;`,否则 XML 解析失败、整个图不渲染。**写完 SVG 用 `xmllint --noout file.svg` 验证一遍**(无输出 = 合法)

---

## Stage 产物结构纲领(Why 之后所有 stage 通用)

`stages/0X-stage.md` 按下面骨架组织,适用 How / Origin / Deep / Comparison / Synthesis(各 stage 的「三件事」内容不同 —— How=核心组件 / Origin=演化里程碑 / Deep=反事实 / Comparison=维度差异 / Synthesis=五元组,但**顶层结构一样**)。

### 标准骨架

```
# 阶段 X:<主题> <本阶段动词>
## 约束清单速查(C1~Cn)              ← 顶部速查(Why 后必备),`#### Cn — 一句话` 标题级 anchor
## §0 从 上阶段 走到 本阶段:三件事记住    ← 纲领(从上阶段 Cn 推本阶段 ~3 核心组件)
## §1 一张极简概览图                  ← 鸟瞰(SVG 1200×400~600,先看再钻)
## §2 ~ §N 细节展开                  ← 序号 §X / §X.Y / §X.Y.Z 三级
## §N+1 约束回扣(组件 → Cn)         ← 闭环
## §N+2 呼应灵魂问题                  ← Y% 闭环 + 留白
## 修订记录(无序号)                  ← 每次 patch 一行
```

### 顶部约束速查表

**用 `#### Cn — 一句话` markdown 标题做 anchor,不要表格内 inline HTML 锚点**。GFM 自动给标题生成 lowercased ID(`#c1`、`#c2`...),后文用 `[C1](#c1)` 跳转;outline 中也直接看到全部 n 条 Cn。

> **约束数量 n 不预设** —— **由主题复杂度动态决定**,在 stage-why 阶段建立。简单主题(如某具体算法)可能 3~4 条;中等(如 malloc / B+树 / io_uring)5~7 条;复杂(如分布式共识 / 操作系统调度 / GC)8~12 条。**严禁硬编码 "7 条"**(那是 malloc 主题的偶然结果)。详见 `skills/stage-why/SKILL.md` 「约束清单的数量」+ 反模式 18。

**纪律:每个 stage 文档(How / Origin / Deep / Comparison / Synthesis)的速查表必须独立完整列出全部 n 条,不能用 "同 stages/03-how.md 顶部速查表" 这种 reference 偷懒**。三个理由:

1. `[C1](#c1)` 这种 markdown 锚点链接**只在本文件内有效**;跨文件 reference 不一定能跳
2. 读者打开任何一个 stage 文档,应该立刻看到全部 n 条 Cn(自包含)
3. 后续 stage 可能想给某条 Cn 增加"在本阶段的精度"(如 Origin §5.5 的"约束反向演化"、Deep §2.4.5 的"复合分解"),独立列才能在每个 stage 各自拼接精度

每条 3 行紧凑:

```markdown
#### C1 — 高频小块
应用对动态内存的请求是**高频小块**(每秒 10⁵~10⁷ 次)。
**不可再分**:C++ / 现代脚本运行时的语义现实。
**口诀**:量大频高 → 必须 O(1) 快
```

⚠️ **反例**:`| <a id="c1"></a>**C1** | ... |` —— 很多 viewer(VS Code 默认 / CommonMark strict)**不解析表格 cell 内的 inline HTML**,会把标签当文本显示出来,视觉上很丑。详见反模式 14。

### §0「三件事记住」纪律

- **承上**:1~2 段把上阶段约束串起来,说本节本分是把它们精确化成 ~3 个组件
- **每件事**:用「因为 Cx + Cy(必须引用) → 要解决 ZZZ → 所以引入 <组件>」严格推导(参见「概念引入纪律」)
- **结论**:一张三件事横向对照表(`是什么 / 为什么存在` 2 列)
- **关系**:三件事如何嵌套/协作,为 §2 钻细节铺路

**只引最核心的 3 个**,不是 5 个不是 7 个。多余细节留给 §2 之后展开。三件事一旦立住,后面所有细节都能挂在三件事下不散。

### §1 极简概览图

- 文件命名 `figures/0X-overview.svg`,viewBox 1200×400~600(比详细图小,一眼看完)
- 只画**三件事的空间关系 + 1 个具体例子**(不画完整二维结构 / 全字段列表)
- 详细图(完整结构、全字段)留给 §2 内的小节,文件命名区分:
  - `0X-overview.svg`(鸟瞰,§1 用)
  - `0X-<topic>.svg`(细节,§2~§N 内具体小节用)
- markdown 引用:`![<一句话描述>](../figures/0X-overview.svg)` + 列表形式写"5 件能从图上读出来的事"

### 章节序号纪律

- **2 级**:`## §X` 大节
- **3 级**:`### §X.Y` 中节
- **4 级**:`#### §X.Y.Z` 关键引用点(可省略序号,但要引用的就保留)
- 速查表、修订记录这种"非主线"小节**不加序号**(用 `## 约束清单速查` / `## 修订记录`)

好处:① VS Code/Typora outline 折叠展开 ② 修订记录里"§3.5.1 加了 cache locality" 读者精确定位 ③ 跨 stage 引用方便。

### 末尾闭环

- **§N 约束回扣表**:`组件 → 对应 Cn → 精确化解方式` 三列,读者验证"每个组件都被某条 Cn 单向逼出来"
- **§N+1 呼应灵魂问题**:本阶段把灵魂问题闭环到 X%,剩下 (100-X)% 留给后续哪个阶段
- **修订记录**:无序号,放文末,每次 patch 加一行 `| 时间 | 修订摘要 | 触发原因 |`

---

## Stage 推进 reconfirm 纪律(推进信号 ≠ 已读完产物)

**核心问题**:用户给出推进白名单信号(如选「分水岭三选项」中的「继续」),但他可能**只是基于 Claude 对话里的简述回应**,**没读完产物本身**。Claude 误把"推进信号"当成"已吸收产物",推进后用户失去仔细读产物的机会,后续 stage 全是基于"未消化的前一阶段"。

### 纪律(推进前必做)

收到任何明确推进信号(`走吧 / 下一个 / 推进 / 继续往下走` 等白名单)后,**不要立刻封存 + 加载下一 stage**。先反问一句让用户最后确认:

> "你确认要推进了吗?(`stages/0X-stage.md` 全文你看过 / 想先看一下再决定?)"

按对话语言纪律,实际表述自然化(替换 "stage" 为 "话题 / 这一块"):
- "你确认要推进了吗?草稿在 `stages/0X-stage.md`,有没有再想 patch 的?"
- "真要往下走?或者你想先把刚才那段笔记看完?"

**用户回应处理**:

| 用户回应 | Claude 行为 |
|---------|------------|
| "看过了 / 确认推进 / 是的走" | 进入封存 + 加载下一 stage |
| "还没看完 / 我看一下 / 等等 / 让我先读读" | **留在当前 stage**,等用户读完;期间任何追问 / 不懂仍按 user-pacing 协议 patch 文件 |
| "没回应 / 模糊"(说"嗯""好""差不多"但没明确"看过了") | 当作"还没看完"留住,**宁可多等一句不要替用户推进** |

### 为什么这条很关键

atlas 的核心 UX 契约是 "用户主导节奏"。**"推进信号 = 已吸收产物"是 Claude 的隐性假设,不是用户的承诺**。一次错误推进的代价 = 用户后续 stage 读得迷糊 + 必须回退或重读;reconfirm 一句话的代价远低于此。

详细执行步骤见 `skills/three-options/SKILL.md` 「A. 明确推进信号(放行)」step 1。

---

## 产物封存协议(git snapshot)

atlas 把每次 stage 推进当作"产物已经凝固"的时刻,**自动用 git 封存**当前的 `atlas-output/<短名>-<yyyymmdd>/` 改动 + 任何 skill 自身的改动。整个 pipeline 走完才 push 到远程。

### 触发时机

| 时机 | 动作 |
|------|------|
| 用户给出**明确推进信号**(由 three-options 判定),Claude 加载下一阶段 skill **之前** | `git add -A` + commit 一次 |
| `final-export` 把综合 MD / HTML 都生成完后 | 最后再 commit 一次 + `git push origin main` |

### commit message 格式

```
atlas(<短名>): finish <stage 名> stage

<可选:一句话总结这一轮用户接住的核心要点 / 留下的笔记修订>
```

例:
```
atlas(glibc的malloc函数): finish What stage

用户独立推出 brk/mmap 双通道 + syscall 量级开销 + 碎片三件事;笔记加了《朴素方案崩塌点》小节 + brk vs mmap 5 维对照表。
```

### 静默执行

git 操作**完全静默** —— 对话中**不提**"已 commit / git push 完成"等。用户感受到的是流畅的 stage 切换;封存在背景进行。仅当 git 操作失败时,才在对话中告知用户(失败不打断教学,但需要让他知道封存断了)。

### 不封存的内容

- `.DS_Store`(在 `.gitignore` 里)
- 教学过程中的临时修订草稿(如果有) —— 只封存"用户给推进信号那一刻"的 stage 文件状态
- skill 源码的偶然修改不该在 stage 推进时一并 commit —— skill 改动应该独立 commit(由开发者人工触发)

具体执行细则见 `skills/three-options/SKILL.md` 的「放行前封存」步骤,以及 `skills/final-export/SKILL.md` 的「最终 push」步骤。

---

## 子 skill 加载规则

### 加载时机

子 skill 按需加载,**不在启动时全部加载**——这是 skill 套件相对于 monolithic 的核心好处:

- Claude 上下文里始终保留:**入口 SKILL.md**(本文件)
- 用户进入某阶段时,**追加加载**:对应阶段子 skill + three-options + progress-tracker
- 阶段切换时,**前一阶段子 skill 可以从上下文移除**(由 Claude 自行管理上下文长度)

### 加载方式

Claude 通过 `view` 工具读 `skills/<sub-skill>/SKILL.md`,把内容作为指令执行。

**注意**:子 skill 之间**强耦合,只服务于 atlas pipeline**——它们假设 PROGRESS.md 存在、灵魂问题已记录、约束清单可查。子 skill 不设计为独立调用(那是 /primer / /deeparch-md 的职责)。

---

## 共享上下文(所有子 skill 都依赖)

### 工作目录约定

工作目录是**当前工作目录下**的 `atlas-output/<短名>-<yyyymmdd>/`(相对路径,不是 `/mnt/...` 的绝对路径)。

```
atlas-output/<短名>-<yyyymmdd>/
├── stages/                          ← 阶段产物
│   ├── 01-what.md
│   ├── 02-why.md
│   └── ...
├── <短名>-atlas.md                  ← 最终融合产物
├── <短名>-atlas.html                ← (可选)HTML 版
└── PROGRESS.md                      ← 状态机
```

- **`<短名>`** 在启动流程派生,贯穿目录名和最终产物文件名。文档**正文**里的标题、引用仍用主题原文(如 "B+树"、"io_uring"),只有文件系统可见的名字用短名。
- **`<yyyymmdd>`** 是首次创建时的日期,后续恢复用同一个目录,不刷新日期。
- 同一主题想完全重启 → 删旧目录 / 用 progress-tracker 的「重新开始」选项。

### PROGRESS.md 字段(由 progress-tracker 维护)

- **灵魂问题**:Discovery 收集的具体问题(后续阶段都向它收敛)
- **进度状态机**:Checkbox 列表标记走到哪了
- **用户疑问审计**:每阶段「追问」「换角度」的记录
- **约束清单**:Why 阶段建立的 C1, C2, ... (后续阶段交叉引用)
- **当前阶段**:用于中断恢复时定位
- **上次更新时间**

### 灵魂问题(贯穿所有阶段)

Discovery 收集的具体问题(如"chunk 为什么是 16B 不是 8B"),**所有阶段子 skill 都必须让讲解向它收敛**。子 skill 在每章末尾应该呼应这个问题。

### 约束清单(Why 阶段建立后,贯穿后续)

C1, C2, ... 是 atlas 的脊梁。**所有后续阶段必须用约束编号交叉引用**——讲到某机制时说"这对应 C3 + C5"——不引用就散了。

---

## 反模式(套件级,所有子 skill 必须避免)

1. **入口 SKILL.md 加教学逻辑** —— 入口只调度,具体内容在子 skill 里
2. **跳过 progress-tracker 直接推进** —— PROGRESS.md 不更新就失去中断恢复能力
3. **没有明确推进信号就推进**(把"嗯/好/明白"当推进) —— 违反 gatekeeper 契约,用户会感觉被推着走
4. **在对话中暴露 "X 阶段 / 加载 stage-Y / 调用 three-options / PROGRESS.md" 等管道术语** —— 用户应该感觉是被一个朋友带着想问题,不是在跑流水线
5. **stage 产物只在"换角度"时整体重写** —— 应该在每次有信息增量(追问澄清 / 新视角 / 不懂反馈)时 patch 回去,产物随对话演化
6. **追问只在对话里答完就过,不 patch stage 文件** —— 文件就废了,不再反映用户当前理解
7. **子 skill 之间互相调用而不经过入口路由** —— 容易耦合炸开,所有路由通过本 SKILL.md 的调度表
8. **子 skill 设计成"独立可调用"** —— atlas 的子 skill 强耦合于 pipeline,设计为独立可用是过度设计
9. **后续阶段不用约束编号交叉引用** —— C1, C2 是脊梁,不引用就散了
10. **跨界处理文学/历史主题** —— atlas 专精技术
11. **导出格式提前在 Discovery 问** —— 用户走完才知道自己要什么
12. **直接抛概念而不从约束推出来** —— 任何首次出现的术语都必须用「因为 XXX(约束 + 引用 Cn)→ 要解决 YYY → 所以引入 ZZZ」链条引出。详见上文「概念引入纪律」
13. **复杂多元关系硬塞 ASCII 大图** —— 50 行以上的 ASCII art 几乎一定画不清(物理 vs 逻辑 / 嵌套层级 / 状态迁移 等),应改用 HTML(暗色科技风,放在 figures/ 子目录)。详见上文「图示偏好」
14. **顶部约束速查用表格内 inline HTML 锚点** —— 形如 `| <a id="c1"></a>**C1** | ... |` 看似工程,实际 viewer 不解析表格 cell 内的 inline HTML,会把 `<a id>` 标签当文本显示,视觉上很丑。改用 `#### Cn — 一句话` markdown 标题级 anchor(GFM 自动生成 ID,outline 直接可跳)。详见上文「Stage 产物结构纲领」
15. **stage 文档不分章节序号 / 没有顶部速查 / 没有末尾约束回扣 + 呼应灵魂问题** —— 这三件事一起决定 stage 文档是否"骨架完整"。缺一就散。详见上文「Stage 产物结构纲领」
16. **把"推进信号"等同于"已读完产物" / 推进前不 reconfirm** —— 用户给出推进白名单信号(走吧 / 下一个 / 推进等)时,Claude 误以为用户已经吸收完产物就立刻封存 + 加载下一 stage。但用户可能只是基于"对话里的简述"回应,**没读完产物本身**。后续 stage 全是基于"未消化的前一阶段"。**修复**:推进前必须反问一句"你确认要推进了吗?"让用户最后确认,详见上文「Stage 推进 reconfirm 纪律」+ `skills/three-options/SKILL.md` step 1
17. **顶部约束速查用 reference 偷懒**(如 "同 03-how.md 顶部速查表")—— `[C1](#c1)` 锚点链接只在本文件内有效;跨文件 reference 不一定跳。**每个 stage 文档必须独立完整列出全部 n 条** `#### Cn — 一句话`。详见上文「Stage 产物结构纲领」「顶部约束速查表」
18. **硬编码约束数为 7**(或任何固定数字)—— **约束数量 n 由主题复杂度动态决定**,不是预设。malloc 推出 7 条是偶然(这主题足够复杂);简单主题 3~4 条,复杂主题 8~12+ 条都正常。在 stage-why 里根据主题实际情况立 n 条。skill 文件中所有"约束"的引用都用 "C1~Cn" / "n 条" 等动态表达,不写"C1~C7" / "7 条"。详见 `skills/stage-why/SKILL.md` 「约束清单的数量」

---

## 与 Superpowers 的架构对应

| Superpowers | /atlas 套件 |
|-------------|-----------|
| 入口 SKILL.md 只做调度 | 入口 SKILL.md 只做调度 |
| skills/ 子目录 14 个专精 skill | skills/ 子目录 11 个专精 skill |
| TDD discipline 子 skill | three-options 子 skill |
| plan-creation 子 skill | discovery + progress-tracker 子 skill |
| 工程方法论(TDD) | 思考方法论(第一性原理 + 反事实) |
| 渐进式上下文加载 | 渐进式上下文加载 |
| 中断恢复(plan 文件) | 中断恢复(PROGRESS.md) |

两者都是**"轻量入口 + 专精子 skill + 用户主导节奏"** 的三件套。

---

## 注意事项

- **入口 SKILL.md 必须保持简洁**(<250 行),它是套件唯一**始终在上下文里**的文件
- **子 skill 之间通过 PROGRESS.md 通信**,而非直接调用——这让套件容易调试和扩展
- **每个子 skill 的 description 要写明"仅由 atlas 入口调度时使用"**,避免被错误触发
- **HTML 导出**:用户偏好暗色科技风(`#0a0c10` 背景、JetBrains Mono + Noto Sans SC、左侧时间线 + 右侧色标卡片)
