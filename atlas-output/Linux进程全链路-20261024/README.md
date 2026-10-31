# Linux 进程全链路大电影 · 脚本与视频

本次交付：8 份独立 VMD、8 个 1920×1080 MP4（含字幕 .srt 与场景时间轴 .scenes.json）、9 张原文图示 PNG、8 张工程总结卡、一套大电影封面、一份整稿简介。正文为 Anthropic 暖橙主题，源码固定 Linux v6.12（jsDelivr gh/torvalds/linux@v6.12，副本在 video-notes/src/）。

总时长：88.16 分钟。原输入文档 `Linux进程全链路-atlas.md` 与 stages/ 未改动（sha256 55d5be1d545b…）。

B 站：BV1LTxC6mE5N https://www.bilibili.com/video/BV1LTxC6mE5N（1 个稿件 8 分 P，标题「Linux 进程从 execve 到 exit 深度解读（88 分钟大电影）」）

| 集 | 阶段 | VMD 场景 | 实际时长 | 脚本 | 视频 | 原文覆盖 |
|---|---|---:|---:|---|---|---|
| 0 | 目录 | 7 | 3:06 | [VMD](linux-process-ep0-toc.vmd) | linux-process-ep0-toc.mp4 | 七集总览 |
| 1 | What | 27 | 10:56 | [VMD](linux-process-ep1-what.vmd) | linux-process-ep1-what.mp4 | [覆盖矩阵](video-notes/coverage-ep1.md) |
| 2 | Why | 29 | 12:21 | [VMD](linux-process-ep2-why.vmd) | linux-process-ep2-why.mp4 | [覆盖矩阵](video-notes/coverage-ep2.md) |
| 3 | How | 39 | 14:35 | [VMD](linux-process-ep3-how.vmd) | linux-process-ep3-how.mp4 | [覆盖矩阵](video-notes/coverage-ep3.md) |
| 4 | Origin | 31 | 9:19 | [VMD](linux-process-ep4-origin.vmd) | linux-process-ep4-origin.mp4 | [覆盖矩阵](video-notes/coverage-ep4.md) |
| 5 | Deep | 37 | 14:57 | [VMD](linux-process-ep5-deep.vmd) | linux-process-ep5-deep.mp4 | [覆盖矩阵](video-notes/coverage-ep5.md) |
| 6 | Comparison | 28 | 10:49 | [VMD](linux-process-ep6-comparison.vmd) | linux-process-ep6-comparison.mp4 | [覆盖矩阵](video-notes/coverage-ep6.md) |
| 7 | Synthesis | 31 | 12:03 | [VMD](linux-process-ep7-synthesis.vmd) | linux-process-ep7-synthesis.mp4 | [覆盖矩阵](video-notes/coverage-ep7.md) |

每集渲染器另加品牌引入场景。分 P 上传时使用 parts/ 下的中文分 P 名硬链接（同一文件，不占额外空间）。

[整稿简介](linux-process-ep0-toc.desc.txt) · [主封面](cover-atlas.png)（HTML 源 video-notes/cover-atlas.html，Playwright 截图） · [校验记录](verification.json) · [上传回执](upload-receipt.json) · 渲染日志与逐集校验在 video-notes/logs/。

人物照片来源见 pics/portrait-sources-ep*.json；只对目检确认为本人的照片做了人物场景（Thompson、Torvalds、Drepper、Cutler），Arcangeli 以文字场景带过。各集相对原文的事实修正记录在 video-notes/coverage-ep*.md。流程：7 个并行起草分支各写一集，主控逐集独立复审（lint、禁词、源码逐字比对、照片与 ASCII 出帧目检）后打 video-notes/ready-epN，串行渲染队列 video-notes/render-queue.sh 只渲染已标记的集并做完整解码校验。
