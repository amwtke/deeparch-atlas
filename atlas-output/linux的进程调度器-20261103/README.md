# Linux 进程调度器大电影 · 脚本与视频

本次交付：8 份独立 VMD、8 个 1920×1080 MP4（含字幕 .srt 与场景时间轴 .scenes.json）、11 张原文图示 PNG、8 张总结卡、一张大电影封面、一份整稿简介。正文为 Anthropic 暖橙主题，源码固定 Linux v6.12（jsDelivr gh/torvalds/linux@v6.12，副本在 video-notes/src/）。

总时长：93.2 分钟。原输入文档 `linux的进程调度器-atlas.md` 与 stages/ 未改动（sha256 dbc10215d7d4…）。

B 站：BV1nbWm6wEJe https://www.bilibili.com/video/BV1nbWm6wEJe（1 个稿件 8 分 P，标题「Linux 调度器从 for 循环到 sched_ext 深度解读（93 分钟大电影）」）

| 集 | 阶段 | VMD 场景 | 实际时长 | 脚本 | 视频 | 原文覆盖 |
|---|---|---:|---:|---|---|---|
| 0 | 目录 | 8 | 3:48 | [VMD](linux-sched-ep0-toc.vmd) | linux-sched-ep0-toc.mp4 | 七集总览 |
| 1 | What | 29 | 10:32 | [VMD](linux-sched-ep1-what.vmd) | linux-sched-ep1-what.mp4 | [覆盖矩阵](video-notes/coverage-ep1.md) |
| 2 | Why | 32 | 13:58 | [VMD](linux-sched-ep2-why.vmd) | linux-sched-ep2-why.mp4 | [覆盖矩阵](video-notes/coverage-ep2.md) |
| 3 | How | 38 | 14:56 | [VMD](linux-sched-ep3-how.vmd) | linux-sched-ep3-how.mp4 | [覆盖矩阵](video-notes/coverage-ep3.md) |
| 4 | Origin | 35 | 12:39 | [VMD](linux-sched-ep4-origin.vmd) | linux-sched-ep4-origin.mp4 | [覆盖矩阵](video-notes/coverage-ep4.md) |
| 5 | Deep | 37 | 13:29 | [VMD](linux-sched-ep5-deep.vmd) | linux-sched-ep5-deep.mp4 | [覆盖矩阵](video-notes/coverage-ep5.md) |
| 6 | Comparison | 33 | 11:04 | [VMD](linux-sched-ep6-comparison.vmd) | linux-sched-ep6-comparison.mp4 | [覆盖矩阵](video-notes/coverage-ep6.md) |
| 7 | Synthesis | 35 | 12:42 | [VMD](linux-sched-ep7-synthesis.vmd) | linux-sched-ep7-synthesis.mp4 | [覆盖矩阵](video-notes/coverage-ep7.md) |

每集渲染器另加品牌引入场景。分 P 上传时使用 parts/ 下的中文分 P 名硬链接（同一文件，不占额外空间）。

[整稿简介](linux-sched-ep0-toc.desc.txt) · [主封面](cover-atlas.png)（HTML 源 video-notes/cover-atlas.html，video-notes/render_cover.py 用 Playwright 截图） · [校验记录](verification.json) · [上传请求](upload-request.json) · [上传回执](upload-receipt.json) · 渲染日志与逐集校验在 video-notes/logs/。

人物照片来源见 pics/portrait-sources.json；只对目检确认为本人的照片做了人物场景（Linus Torvalds、Ingo Molnar、Dave Cutler），Con Kolivas、Peter Zijlstra、Tejun Heo、David Vernet 以文字场景带过。各集相对原文的事实修正记录在 video-notes/coverage-ep*.md。

流程：7 个并行起草分支各写一集（派工单 video-notes/BRIEF.md），主控逐集独立复审（lint、禁词、源码逐字比对、事实抽查、出帧目检）后打 video-notes/ready-epN，串行渲染队列 video-notes/render-queue.sh 只渲染已标记的集并做完整解码校验。

ASCII 框图对齐：渲染器 ascii 场景的字宽是等宽 13px、中文 22px（不是 26px），按「中文占 2 列」补空格的框线会偏。video-notes/ascii-src/ 保存各集的列模型源文件，video-notes/ascii_px_align.py 把它们按真实像素重排成正式 VMD。以后改 ascii 场景请改 ascii-src 里的副本再重新生成，不要直接改已重排的 VMD 里的空白。
