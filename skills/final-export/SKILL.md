---
name: atlas-final-export
description: atlas 套件的最终导出子 skill。在 Synthesis 完成后,询问用户导出格式(MD / MD+视频脚本提示 / MD+HTML),然后融合 stages/*.md 成综合长文,可选生成暗色科技风 HTML,最后用 present_files 输出。仅由 atlas 入口 SKILL.md 调度时使用,不应被独立调用。
---

# atlas / final-export

## 阶段目标

把所有阶段的产物**融合成最终综合长文**,根据用户选择生成对应导出格式,呈现给用户。

---

## 执行流程

### 第一步:询问导出格式

用 `ask_user_input_v0`(单选):

```
所有阶段已完成。你想怎么导出最终产物?

[仅综合 MD]
[综合 MD + 视频脚本提示(后续可用 /deeparch-video-script)]
[综合 MD + 暗色科技风 HTML]
```

记录用户选择到 PROGRESS.md(调用 progress-tracker)。

### 第二步:融合 stages/*.md → 综合 MD

读取 `stages/` 目录下所有存在的 stage.md 文件,按编号顺序融合成 `<短名>-atlas.md`。

**融合不是简单拼接**——需要做以下处理:

#### 2.0 路径重写(必备!)

**所有 stage 内部用相对路径引用图 / 代码**(如 `pics/03-overview.svg` / `src/05-demo.c`),融合到顶层 `<短名>-atlas.md` 后,**这些相对路径全部失效**(因为 atlas.md 跟 stages/ 同级)。

**融合时必须做路径重写**:

```python
# 各 stage 内部的相对引用,改成相对 atlas.md 的路径
'pics/03-overview.svg' → 'stages/03-how/pics/03-overview.svg'
'pics/04-timeline.svg' → 'stages/04-origin/pics/04-timeline.svg'
'src/05-demo.c' → 'stages/05-deep/src/05-demo.c'
# ...
```

具体规则(对每个 stage `0X-stage-name/`):

- markdown 链接 / 图片 `](pics/0X-...)` → `](stages/0X-stage-name/pics/0X-...)`
- markdown 链接 / 图片 `](src/0X-...)` → `](stages/0X-stage-name/src/0X-...)`
- 行内 code 引用 `` `pics/0X-...` `` → `` `stages/0X-stage-name/pics/0X-...` ``
- 行内 code 引用 `` `src/0X-...` `` → `` `stages/0X-stage-name/src/0X-...` ``

**例外**:**修订记录里的历史描述**(`| 2026-XX-XX | ... 创建了 \`pics/03-...\` ...`)**不要改** —— 那是 stage 内部修订记录的延续,描述过去事件,改了反而破坏历史含义。

**HTML 同步修**:HTML 里 SVG 内嵌没问题,但**非 SVG 链接**(如 `.html` 富排版版 / 代码文件链接)是 `<a href="pics/...">`,也需要相应的路径重写。

#### 2.1 顶部加《导读地图》

```markdown
# <主题> | atlas 综合文档

## 导读地图

本文是关于 <主题> 的综合长文,围绕**第一性原理**展开,陪伴用户一个阶段一个阶段把这个技术搞透。

**灵魂问题**(从 Discovery 收集):
> "<...>"

**覆盖阶段**:
- ✅ What(它是什么)
- ✅ Why(为什么必须存在,含约束清单 C1~Cn)
- ✅ How(大致怎么工作)
- ✅ Origin(它怎么来的)
- ✅ / ❌ Deep(机制级精确剖析)
- ✅ / ❌ Comparison(横向对照)
- ✅ Synthesis(设计哲学与方法论沉淀)

**全长**:约 XXXX 行,深读约 XX 分钟,跳读约 XX 分钟。

**阅读路径建议**:
- 想快速建立心智 → 直接看 [What](#) + [Why](#)
- 想看清设计为什么这样 → 看 [Why](#) + [Deep](#) + [Synthesis](#)
- 想横向对比 → 直接看 [Comparison](#)
- 想拿走方法论 → 直接看 [Synthesis 5.5](#)

**目录**:
- [What](#what)
- [Why](#why)
- ...
```

#### 2.2 每篇之间加 80~150 字过渡段

做心智模式切换引导。例如 What → Why 的过渡:

```markdown
---

> 上面我们用一张地图建立了对 <主题> 的骨架认知——它是什么、它的"邻居"是谁。
> 但只看地图无法理解它的存在意义。下一篇我们要回到原点:**没有 <主题> 的世界
> 会怎样?它面对的不可再分约束是什么?** 接下来你会从游客模式切换到共情模式——
> 跟着工程师当年的痛苦一起,理解这个技术为什么必须存在。

---
```

每个篇章之间都有这种过渡段,做风格切换:
- What → Why:讲解员 → 论证者(共情模式)
- Why → How:论证者 → 实操员(实践模式)
- How → Origin:实操员 → 讲故事的人(沉浸模式)
- Origin → Deep:讲故事的人 → 工程师(工程师模式)
- Deep → Comparison:工程师 → 评论家(比较模式)
- Comparison → Synthesis:评论家 → 哲学家(反思模式)

#### 2.3 末尾加《延伸阅读 + Q&A 钩子》

```markdown
## 延伸阅读

如果你想继续探索:
- `/atlas <相邻主题 1>`:<理由>
- `/atlas <相邻主题 2>`:<理由>
- `/atlas <相邻主题 3>`:<理由>

(从 Comparison / Synthesis 阶段的内容里提取相邻主题)

## Q&A 钩子(开放问题)

读完之后,你可以继续追问:
1. <开放问题 1>
2. <开放问题 2>
3. <开放问题 3>
```

#### 2.4 保存到 `<短名>-atlas.md`

### 第三步:根据用户选择,生成附加产物

#### 选择"仅综合 MD"

跳过附加产物,直接进入第四步。

#### 选择"综合 MD + 视频脚本提示"

不生成视频脚本本身(那是 /deeparch-video-script 的职责),但在最终输出时**明确提示**:

```
综合 MD 已生成。要把它转成视频脚本,接下来用:
/deeparch-video-script <主题>

它会基于本文生成 .vmd 格式的视频脚本,可直接输入 deeparch-video pipeline 生成 MP4。
```

#### 选择"综合 MD + 暗色科技风 HTML"

生成 `<短名>-atlas.html`,样式参考用户偏好:

- 背景 `#0a0c10`
- 字体:JetBrains Mono(代码) + Noto Sans SC(中文)
- 布局:左侧时间线导航 + 右侧色标卡片
- 风格参考用户之前的 `process-address-space.html`

具体实现:
- HTML 结构包含整个综合 MD 内容(用 marked.js 等运行时渲染,或预先转换好)
- 左侧时间线显示阶段(What / Why / How / Origin / Deep / Comparison / Synthesis)
- 点击时间线跳到对应阶段
- 每个阶段开始处用色标卡片(每个阶段一种颜色)

### 第四步:调用 progress-tracker 标记完成

最终状态机:

```
- [x] 9. 导出格式询问
- [x] 10. 融合输出
```

### 第五步:用 present_files 输出

输出顺序(主输出在前):

设 `WORKDIR = atlas-output/<短名>-<yyyymmdd>/`(从 PROGRESS.md 元数据「工作目录」字段读出)。

```python
present_files([
    f"{WORKDIR}<短名>-atlas.md",          # 主输出
    f"{WORKDIR}<短名>-atlas.html",        # (若选了 HTML)
    f"{WORKDIR}stages/01-what/01-what.md",
    f"{WORKDIR}stages/02-why/02-why.md",
    # ... 其他 stages
    f"{WORKDIR}PROGRESS.md",
])
```

### 第六步:终末封存 + push 到远程(产物封存协议的收尾)

整个 pipeline 走完,**最后 commit 一次** + push 到远程仓库(见入口 SKILL.md 的「产物封存协议」):

```bash
cd <repo root>
git add atlas-output/<短名>-<yyyymmdd>/    # 把综合 MD / HTML / 最终 PROGRESS.md 封存
git commit -m "atlas(<短名>): pipeline complete — final export

格式:<MD only / MD+视频 / MD+HTML>
覆盖阶段:<列出走过的阶段>
灵魂问题:已闭环回答 / 未完整回答(说明)"

git push origin main
```

- push 失败(网络 / 权限 / 冲突)时,在对话中告知用户具体错误信息 + 给出排查建议,**不要 force-push**
- 如果远程分支不是 `main`,使用当前 git 配置的默认远程分支
- push 成功后,在第七步的对话摘要里**简短提一句**"产物已 push 到远程"(这是 pipeline 真正的"完工"信号,值得提)

### 第七步:在对话中给最终摘要

```
🎉 atlas 流程完成。

主产物:<短名>-atlas.md(共 XXXX 行)
覆盖阶段:[列出走过的阶段]
灵魂问题:"<...>"——[已 / 未] 完整回答

附加产物:
- (若选 HTML)<短名>-atlas.html
- stages/*.md(可单独读)
- PROGRESS.md(审计痕迹)

(产物已封存并 push 到远程:<remote URL>)

下一步建议:
[根据用户的导出选择给出建议]
- (若选 MD+视频)用 /deeparch-video-script <主题> 转视频脚本
- (若选 MD+HTML)HTML 已生成,可直接打开
- 通用建议:用 /atlas <相邻主题> 继续探索
```

---

## 注意事项

- **融合不是拼接**——必须加导读地图、过渡段、延伸阅读
- **过渡段是 atlas 的核心特色**——风格切换作为阅读节奏,不要省略
- **HTML 生成失败时**——优雅降级,告知用户"HTML 生成失败,但 MD 已完成",不影响主输出
- **present_files 主输出在前**——用户最先看到综合 MD,而不是 stages 文件

---

## 反模式

1. **融合时简单拼接 stages 文件** —— 失去 atlas 综合长文的价值
2. **省略过渡段** —— 失去风格切换作为阅读节奏的核心特色
3. **HTML 生成失败时整体失败** —— 应该优雅降级
4. **不调用 progress-tracker 标记完成** —— PROGRESS.md 状态不一致
5. **present_files 顺序错乱** —— 用户应先看到主输出
6. **融合后不重写各 stage 内部相对路径** —— 各 stage 内部的 `pics/...` / `src/...` 是相对各 stage 目录的;融合到顶层 atlas.md 后这些相对路径全部失效,图渲染不出来,代码引用断。**融合时必须自动重写为 `stages/0X-stage-name/pics/...` / `stages/0X-stage-name/src/...`**(修订记录里的历史描述保留原样,那是过去事件不影响阅读)。详见上文「2.0 路径重写」
