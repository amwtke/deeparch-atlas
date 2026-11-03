# 大电影分集脚本 · 共享简报(给每集的起草分支)

本目录 `D = /Users/jin.xiao/workshop/deeparch-atlas/atlas-output/linux的进程调度器-20261103`,视频仓库 `REPO = /Users/jin.xiao/workshop/deeparch-video`。基名 `linux-sched`。

## 必读
1. `REPO/skills/deeparch-video-script/SKILL.md` 全文(VMD 格式、场景类型、Anthropic 主题禁用场景、多音词、`--atlas` 模式规格、对外禁词)。
2. `REPO/skills/deeparch-video-gen/SKILL.md` 的「--atlas 大电影模式规格」段(每集 vmd 必备结构:开场过场 spotlight、结尾下集预告)。
3. 本集对应的 stage 文件 `D/stages/0X-*/0X-*.md`(以它为准,不是融合稿)+ `D/stages/03-how/03-how.md` 顶部的约束速查(C1 ~ C8)。
4. 上一轮的同集脚本作为风格样板:`/Users/jin.xiao/workshop/deeparch-atlas/atlas-output/Linux进程全链路-20261024/linux-process-epN-*.vmd` 与其 `video-notes/coverage-epN.md`。

## 产物(每集)
- `D/linux-sched-epN-<chap>.vmd`(chap ∈ what / why / how / origin / deep / comparison / synthesis)
- `D/pics/epN-summary-card.json` + 用 `REPO/scripts/summary_card.py <json> -o D/pics/epN-summary-card.png` 渲染(参考上一轮 `pics/ep1-summary-card.json` 的字段)
- `D/video-notes/coverage-epN.md`:覆盖与证据矩阵(原文必讲项 → 场景 → 处理),同上一轮格式
- 通过 lint:`cd REPO && ./venv/bin/python scripts/vmd_lint.py D/linux-sched-epN-<chap>.vmd --theme anthropic --profile generic` 0 错误(渲染流水线的门禁就是 generic + strict;不要用 book profile,它的 BOOK-CHAPTERS / NUM-RECAP 规则不适用于本系列)
- 通过自检:`./venv/bin/python D/video-notes/review_ep.py D/linux-sched-epN-<chap>.vmd` 输出 `ISSUES 0`(它检查旁白禁词、画面豆腐字、源码逐字比对 `D/video-notes/src/linux-6.12/`)

## 硬规则
- 旁白禁词:`atlas`、场景类型名(facetime / html_slide / spotlight / code / layers / recap / analogy / timeline / ascii / statemap / diff),"第 N 篇 / 阶段文件 / PROGRESS" 等管道词。说"这一集 / 这份长文 / 八条约束"。
- 约束引用口播一律"C 几·短名"(如"C3 份额与延迟两头要"),画面可写 `C3·份额与延迟两头要`。
- 源码场景一律 `code_explain`,代码必须是 `D/video-notes/src/linux-6.12/` 里的逐字连续子串(允许 `...` 省略行);标题带文件与行号(来自 Deep 的 file:line)。
- 每张本集 SVG 对应一个 `html_slide`(图在 `D/pics/<stem>.png`,1920 宽),口播讲"从图上能读出的几件事"。
- 人物场景 `facetime`:有照片的用 `photo: D/pics/person-<slug>.jpg`(ingo-molnar / ion-stoica / carl-waldspurger / tejun-heo / linus-torvalds / dave-cutler / ken-thompson);Peter Zijlstra / Paul Turner / Con Kolivas / Mike Galbraith 没有可验证照片 → 仍可 facetime 但省略 photo(占位框),或用 text 场景带过。
- 数字只用 stage 文件里的;待核项以各 stage 文末「待核」表的结论为准(主控会把收尾核实的改写清单发给你,收到后同步改旁白)。
- 每集开头:`# 第 N 集 X 阶段 — <带钩子的标题>` + `[intro-line] …`(一句话,进品牌片头)+ 场景 1 过场 spotlight;每集结尾:下集预告 spotlight / title。ep7 结尾加升华 + 一键三连。
- 贯穿机器与任务:8 核 x86-64 两组 L3、HZ = 250、Linux 6.12;mysqld ×16、redis ×1、xz(nice 19)、PostgreSQL 后端、k8s 容器限 2 核。开场钩子:容器限 2 核 p99 抖;PG 100 后端 + Redis 的 nice 与 taskset。
- Anthropic 暖橙主题:对比一律 ascii 双栏,不用 news_title / data / diff。
- 场景预算与目标时长:ep1 What 14 场景 ~9 min;ep2 Why 12 场景 ~10 min;ep3 How 22 ~ 24 场景 ~13 min;ep4 Origin 18 场景 ~11 min;ep5 Deep 20 场景 ~13 min;ep6 Comparison 14 场景 ~10 min;ep7 Synthesis 18 场景 ~11 min。估时 = 口播字数 / 5.4 + 场景数 × 1.5 s。
- 风格:先结论后展开;每个机制一个点名例子(mysqld#3 / redis / xz);数字说口语("三毫秒""百分之九十五");反问用选择式并当场给答案;不要在每集末加"你拿走了什么"的长总结(总结卡一张即可)。

## 分集标题(已定)
| 集 | 文件 | 标题 |
|---|---|---|
| 0 | linux-sched-ep0-toc.vmd | Linux 调度器大电影 — 七集路线图(主控自写,时尚风目录卡) |
| 1 | linux-sched-ep1-what.vmd | 第 1 集 What 阶段 — 谁上台、跑多久、在哪颗核:调度器的四问骨架 |
| 2 | linux-sched-ep2-why.vmd | 第 2 集 Why 阶段 — 从一核一队列砍八刀,逼出八条约束 |
| 3 | linux-sched-ep3-how.vmd | 第 3 集 How 阶段 — 账、标记、搬人:内核用什么把八条约束化解掉 |
| 4 | linux-sched-ep4-origin.vmd | 第 4 集 Origin 阶段 — O(1)、CFS、EEVDF、sched_ext:五个转折点和他们的人 |
| 5 | linux-sched-ep5-deep.vmd | 第 5 集 Deep 阶段 — 钻进 6.12:挑人、均衡、throttle 各在源码哪一行 |
| 6 | linux-sched-ep6-comparison.vmd | 第 6 集 Comparison 阶段 — Windows NT 的 32 级优先级对 Linux 的账:哪些是约束,哪些是血统 |
| 7 | linux-sched-ep7-synthesis.vmd | 第 7 集 Synthesis 阶段 — 五元组、五步法,再拿 MySQL 线程池走一遍 |

## 完成时回复主控
场景数 / 类型分布 / 口播字数 / 估时 / lint 与 review 结果 / 用到的图与人物 / 对原文的事实修正(如有)。
