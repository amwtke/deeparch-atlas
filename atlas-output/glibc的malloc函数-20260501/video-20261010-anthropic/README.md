# glibc malloc 大电影 · 全新脚本与视频

本次交付完成：8 份独立 VMD、8 个 1920×1080 MP4、字幕、场景时间轴、七张图示副本、八张工程总结卡、一套封面与一份整稿简介。正文采用 Anthropic 暖橙主题；封面采用大电影金字样式。已上传 B 站为一个稿件、8 个分 P，提交后核验状态为审核中。

总时长：77.05 分钟。原输入文档及旧产物保留；本目录脚本全部重新起草。

| 集 | 阶段 | VMD 场景 | 实际时长 | 脚本 | 视频 | 原文覆盖 |
|---|---|---:|---:|---|---|---|
| 0 | 目录 | 7 | 3:29 | [VMD](glibc-malloc-ep0-toc.vmd) | [MP4](glibc-malloc-ep0-toc.mp4) | 七章总览 |
| 1 | What | 17 | 7:03 | [VMD](glibc-malloc-ep1-what.vmd) | [MP4](glibc-malloc-ep1-what.mp4) | [覆盖矩阵](coverage-ep1.md) |
| 2 | Why | 20 | 8:28 | [VMD](glibc-malloc-ep2-why.vmd) | [MP4](glibc-malloc-ep2-why.mp4) | [覆盖矩阵](coverage-ep2.md) |
| 3 | How | 30 | 13:40 | [VMD](glibc-malloc-ep3-how.vmd) | [MP4](glibc-malloc-ep3-how.mp4) | [覆盖矩阵](coverage-ep3.md) |
| 4 | Origin | 23 | 9:34 | [VMD](glibc-malloc-ep4-origin.vmd) | [MP4](glibc-malloc-ep4-origin.mp4) | [覆盖矩阵](coverage-ep4.md) |
| 5 | Deep | 24 | 10:15 | [VMD](glibc-malloc-ep5-deep.vmd) | [MP4](glibc-malloc-ep5-deep.mp4) | [覆盖矩阵](coverage-ep5.md) |
| 6 | Comparison | 24 | 11:40 | [VMD](glibc-malloc-ep6-comparison.vmd) | [MP4](glibc-malloc-ep6-comparison.mp4) | [覆盖矩阵](coverage-ep6.md) |
| 7 | Synthesis | 24 | 12:53 | [VMD](glibc-malloc-ep7-synthesis.vmd) | [MP4](glibc-malloc-ep7-synthesis.mp4) | [覆盖矩阵](coverage-ep7.md) |

每集渲染器另加入一个品牌引入场景。旁白为中文；字幕和时间轴分别在同名 `.srt` 与 `.scenes.json`。

[整稿简介](glibc-malloc-ep0-toc.desc.txt) · [主封面](cover-atlas.png) · [完整校验记录](verification.json)

生成遵循输入文档的 What / Why / How / Origin / Deep / Comparison / Synthesis 主线、知识点和因果推导，改写为口播、图解和源码高亮。必要的事实修正记录在每章覆盖矩阵中；未逐字照搬错误或混用版本。源码固定为 glibc 2.34，常见 LP64 条件。

重点校正包括：24 字节请求正规化为 32 字节块、对应 tcache 桶 0；glibc 2.34 使用 tcache_get；8 KiB 与 200 KiB 不是必然的 brk/mmap 路由；映射阈值有运行历史；2002 年 glibc 2.3 已含 ptmalloc2。现代分配器比较也标明项目、版本与预算边界。

全部 8 个渲染进程正常退出；VMD lint 无错误；媒体完整性、预期时长、音频静音检查和独立全文件解码通过。当前 VMD 哈希与对应视频校验记录一致，输入文档哈希保持不变，16 个上游源码片段与固定版本原文件逐段匹配。校验明细保存在 logs/。

图示使用现有 Chromium 与 Noto Sans CJK SC 在本目录重新排版、校准和渲染，原 SVG 保留。七个人物均在 VMD 中介绍；五人的照片已目视核验，另两人使用现有渲染器的文字降档。来源见 [照片记录](pics/portrait-sources.json)。

src/05-demo.c 已在本机以严格编译警告检查编译并运行。Linux glibc 的 strace/GDB 命令是可复现的教学步骤，本次未声称在 macOS 观察到了 Linux 分配路径。

视频项目只校正了一条与当前 skill 冲突的内部记忆，未修改媒体引擎。未提交或推送 Git。用户随后授权 B 站上传，已完成发布提交并核验全部 8 个分 P、封面与简介。

B 站投稿：[glibc malloc 大电影 — 7 集深度解读](https://www.bilibili.com/video/BV1PSpY6tEBd)（BV1PSpY6tEBd，提交后核验状态：审核中）。[上传回执](upload-receipt.json) · [远端核验](logs/upload-remote-verification.json)。
