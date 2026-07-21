---
name: atlas
description: 苏格拉底式深度技术探索与文档生成工作流。用户显式输入 Codex 的 $atlas 加技术主题、Claude Code 的 /atlas 加技术主题，或提出“用第一性原理彻底分析 X”“带我搞懂 X”“从头讲 X”“X 的设计哲学/来龙去脉”“继续 atlas X”时使用。围绕灵魂问题按 What、Why、How、Origin、Deep、Comparison、Synthesis 渐进教学，持续写入 atlas-output 并支持中断恢复。适用于内核、JVM、数据库、分布式系统、中间件等复杂技术；不用于文学历史主题或简单语法/API 查询。
---

# Atlas Codex adapter

1. 先解析本适配目录的真实文件系统位置；若它从用户级目录 symlink 进来,要跟随 symlink 到源码目录。
2. 完整读取真实适配目录下的 `../../../SKILL.md`，把它作为 Atlas 的共享入口指令执行。
3. 从源码仓库根目录解析 `skills/<name>/SKILL.md` 等共享指令资源；`atlas-output/` 等运行产物仍按共享入口约定,相对于用户当前工作目录创建。
4. 把 `skills/*/SKILL.md` 当作 Atlas 的内部按需资源，不要把它们作为独立顶层技能调用。

本文件只负责 Codex 发现与转发，不复制工作流逻辑。共享行为以仓库根 `SKILL.md` 为唯一事实来源。
