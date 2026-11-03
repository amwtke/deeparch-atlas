# Linux 的进程调度器 · 自动运行的一轮

2026-11-03,用户授权助手**自己跑完整轮**:品味从前两轮(Linux文件IO全链路、Linux进程全链路)的对话提炼,灵魂问题由助手代定,七份草稿、收尾核实、导出、八集大电影、封面、B 站上传、推送 main 全部自动完成。本文件是交付清单;品味画像与每个阶段的取舍记录在 [PROGRESS.md](PROGRESS.md)。

## 主产物

| 产物 | 文件 | 说明 |
|---|---|---|
| 综合长文(MD) | [linux的进程调度器-atlas.md](linux的进程调度器-atlas.md) | 4474 行,中文约 7.2 万字,14 张图;文末附 78 条待核的统一核实表 |
| 综合长文(HTML) | [linux的进程调度器-atlas.html](linux的进程调度器-atlas.html) | 暗色科技风,左时间线右卡片,SVG 内嵌 |
| 七份草稿 | `stages/0X-*/0X-*.md` | 各自自包含:约束速查 + 正文 + 待核结论 + 修订记录;图在同目录 `pics/`,代码在 `src/` |
| 模拟器 | [stages/05-deep/src/05-eevdf-sim.py](stages/05-deep/src/05-eevdf-sim.py) | 无依赖 Python,`python3 -I` 在 macOS 上可跑;复现 How §3.6 五拍表与 §14 的 64 ms |
| 收尾核实 | [verify-results.md](verify-results.md) | 78 条:已核 52 / 改写 2 / 部分核实 15 / 随前述结论 2 / 无法核实 5 / 示例值与假设 2 |
| 大电影 | `linux-sched-ep0-toc.mp4` ~ `linux-sched-ep7-synthesis.mp4` | 8 集 1920×1080,字幕 .srt 与场景时间轴同名;脚本为同名 .vmd;校验记录在 `video-notes/logs/` |
| 封面与目录卡 | `cover-atlas.png`、`pics/ep0-card-*.png` | 时尚风(紫 → 品红 → 琥珀渐变 + 玻璃卡片);HTML 源在 `video-notes/` |
| B 站 | [BV17U4M6dEwn](https://www.bilibili.com/video/BV17U4M6dEwn) | 1 个稿件 8 分 P,标题「Linux 进程调度器深度解读：从 nice 到 EEVDF、多核与 cgroup（98 分钟大电影）」;回执 `upload-receipt.json` |

## 这一轮是怎么定品味的(摘要,全文见 PROGRESS.md「品味画像」)

1. 先立一个人记得住的骨架 —— 本轮是**四问**:何时换 / 换谁 / 各多少 / 在哪换。
2. Why 从最裸的起点一刀一条:从「一核一队列先来先跑」砍八刀,C1 ~ C8,引用一律 `Cn·短名`。
3. 先陈述后逼问;每节一个点名的例子(mysqld#3 / redis / xz / k8s 容器);核心转换给算例并用模拟器核对。
4. 关键转换画 SVG + 函数链;源码钉 Linux 6.12 带行号;demo 伪代码 + 可跑模拟器。
5. 节首先说结论;类比到数据库 / Windows NT / TCP;弱项(lag、多核均衡、cgroup 带宽)按 结构 / 原理 / 机制 / 策略 加厚。
6. 反问改成选择式并当场《从头走一遍》;《你上一轮的视角》继承用户在上一轮的三句原话。
7. 事实先标待核,导出前统一核实并把结果表写进文档。

## 灵魂问题(助手代定)

> 一个 CPU 面前有 N 个想跑的任务,内核每次到底按什么规则挑下一个?这条规则是被哪些约束逼出来的、为什么 20 年里换了三代?多核和 cgroup 又把这条「挑人规则」扩展成了什么?

## 七篇一句话

| 篇 | 行数 | 一句话 |
|---|---|---|
| What | 274 | 调度器 = 四问,规则只看账不看人;两个数据库口味的钩子 |
| Why | 318 | 八刀八条约束;三代换代各改写哪条 |
| How | 810 | 每核一本账与类栈 / fair 账的四个数 / 标记与出口 / 三种搬人 / cgroup 带宽 / 硬保证 |
| Origin | 424 | O(1) → RSDL·SD 与 CFS → 学术线 → 带宽与 PELT → EEVDF → sched_ext,一手资料 52 条 |
| Deep | 1626 | 三条主线钉到 6.12 行号;EEVDF 模拟器;唯一的 ns 时间线;反事实 17 个候选 |
| Comparison | 492 | Windows NT dispatcher 按四问逐问比;SQLOS 是取消 C2 后的另一局部最优 |
| Synthesis | 492 | 五元组 14 行过筛、必保 11 条、三个同构、五步法 + MySQL 线程池演练、十年赌注 |

## 大电影分集

总时长 98.2 分钟(8 集,1920×1080,Anthropic 暖橙主题,源码固定 Linux 6.12)。每集脚本为同名 `.vmd`,字幕 `.srt`、场景时间轴 `.scenes.json` 同名;逐集校验记录在 `video-notes/logs/*.verification.json`;原文覆盖矩阵在 `video-notes/coverage-epN.md`。分 P 上传用 `parts/` 下的中文分 P 名硬链接。

| 集 | 阶段 | 场景 | 时长 | 脚本 | 原文覆盖 |
|---|---|---|---:|---|---|
| 0 | 目录 | 8 | 4:56 | [VMD](linux-sched-ep0-toc.vmd) | 七集路线 + 人物 + 约束 + 收益四张时尚卡 |
| 1 | What | 26 | 11:58 | [VMD](linux-sched-ep1-what.vmd) | [覆盖矩阵](video-notes/coverage-ep1.md) |
| 2 | Why | 23 | 13:45 | [VMD](linux-sched-ep2-why.vmd) | [覆盖矩阵](video-notes/coverage-ep2.md) |
| 3 | How | 28 | 15:27 | [VMD](linux-sched-ep3-how.vmd) | [覆盖矩阵](video-notes/coverage-ep3.md) |
| 4 | Origin | 24 | 12:50 | [VMD](linux-sched-ep4-origin.vmd) | [覆盖矩阵](video-notes/coverage-ep4.md) |
| 5 | Deep | 27 | 15:02 | [VMD](linux-sched-ep5-deep.vmd) | [覆盖矩阵](video-notes/coverage-ep5.md) |
| 6 | Comparison | 20 | 10:56 | [VMD](linux-sched-ep6-comparison.vmd) | [覆盖矩阵](video-notes/coverage-ep6.md) |
| 7 | Synthesis | 26 | 13:20 | [VMD](linux-sched-ep7-synthesis.vmd) | [覆盖矩阵](video-notes/coverage-ep7.md) |

封面:`cover-atlas.png`(HTML 源 `video-notes/cover-atlas.html`,Playwright 截图);目录卡:`pics/ep0-card-{route,people,cons,gains}.png`(源 `video-notes/toc-cards.html`)。人物照片来源见 `pics/portrait-sources.json`;只对目检确认为本人的照片做了人物场景(Molnár、Stoica、Waldspurger、Heo、Torvalds、Cutler),Zijlstra / Turner / Kolivas / Galbraith 以文字出场。

## 运行记录

- 时间:2026-11-03 02:40 ~ 13:30(见 PROGRESS.md 各阶段审计)。两次撞到 5 小时用量上限(04:30 → 08:00 恢复;09:20 → 13:00 恢复),中断的分支恢复后续完,没有重做。
- 并行:How / Origin、Deep / Comparison、Synthesis / 收尾核实、七集脚本各由独立分支起草,主控合并、核对、导出。
- 没有改动 skill 源码;只在本目录内写文件。
