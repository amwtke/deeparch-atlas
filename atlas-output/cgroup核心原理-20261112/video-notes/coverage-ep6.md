# ep6 Comparison 覆盖与证据矩阵

输入:`cgroup核心原理-atlas.md` 第 6058~6168 行(Comparison 篇 §0~§6 + 待核清单)。vmd:`video-notes/ascii-src/cgroup-ep6-comparison.vmd`,19 场景,口播约 2080 字,估时 6.9 分钟。本集没有源码场景和实测场景(原文无实验,Windows 一侧全部出自微软文档)。Windows 一侧的 API 名、版本号、引文只取自原文。未改动源 MD、stages、原 SVG。

| 原文必讲项 | 画面载体 | 场景 | 处理 |
|---|---|---|---|
| 开篇:为什么拿 Job Object 对照(来历不同) | spotlight | 1 | 保留 |
| 只比五件事、没有实验 | text + sidebar | 2 | 保留 |
| §0 三件事 + 约束来源(C1 C3 / C5 / C2) | layers + sidebar | 3 | 保留;§0 结论表压成三行 |
| §1 全景图 06-overview | pics/06-overview.png(html_slide) | 4 | 整图保留,按左右两栏、底栏讲;图中「共 9 个控制器」没讲 |
| §2 组/嵌套/父管子树/账向上汇总/子进程默认继承 | ascii 双栏 | 6 | 保留 |
| §2 容器 | 6 旁白 | 6 | 压缩:只留「Windows 容器用 job 分组记账」 |
| §2 子进程例外、不能换组、配置方式权限 | ascii 双栏 | 7 | 保留;句柄权限在画面写 JOB_OBJECT_LIMIT_BREAKAWAY_OK,旁白只说「权限在句柄上,更严」,不念 PROCESS_SET_QUOTA 等名 |
| §2 嵌套时子 job 进程须为父 job 子集 | statemap | 8 | 新增串联场景 |
| §2 CPU 上限 / 按比例 | ascii 双栏 | 9 | 保留;weight/最小值最大值模式只在旁白点到 |
| §3 超内存一杀一拒:记提交量 vs 先答应后兑现 | ascii 双泳道 | 11 | 保留 |
| §3 C2 回扣、fork 有返回值对照 | timeline + sidebar | 12 | 保留;fork 对照来自原文第三节 §8.3 / §9.1 |
| §3 末段「提交量介于地址空间与物理页之间」「预订 1 GB 用 10 MB」 | — | — | 不讲:原文标明是作者按两边内存模型做的对照(待核清单 4),不是文档原话 |
| §4 公共框架为什么 Linux 有、Windows 没有 | ascii 双栏 | 14 | 保留 §0.2 的说法(很多家各加 vs 微软一家加);「就够用、更简单」「谁也不能等谁」两句是原文标的解读(待核清单 5),不讲 |
| §4 代价:定期检查、通知会丢 | ascii 双栏 | 15 | 保留 |
| §2 进程数、磁盘 IO 回收 | ascii 双栏(画面) | 15 | 进程数、IO 只上画面,旁白不讲(为控制时长);ActiveProcessLimit 超限行为原文未查,画面只写「活动进程数上限」 |
| §2 IO 速率控制不再支持;Windows 8 CPU 速率控制 | 14 画面 + 旁白 | 14 | 旁白只留 CPU 速率控制;IO 1607 在画面上 |
| §5 约束回扣(C1~C5) | ascii | 16 | 保留;C4 写「这一集不比较」 |
| §6 呼应三个问题 | text + sidebar | 17 | 保留 |
| 本集总结 | pics/ep6-summary-card.png | 18 | 新增 |
| 下集预告 | spotlight | 19 | 新增 |
| 待核清单 2、3、6(ActiveProcessLimit 行为、IO 收回原因、server silo) | — | — | 不讲:都是原文标「未查」的项 |

## 相对原文的事实修正

无。
