# ep4 覆盖与证据矩阵

主角色：来路 / 演化史；输入原文 Origin 行 1688–2112，另读约束速查行 46–103 与收尾核实表行 4067–4118（Origin #1 涉及本篇；What #1、Deep #14 的 Redis 数字只在旁白里以“二十 GB 的堆”带过，不报具体毫秒）。

主链：你敲一个 ls，fork 复制一遍再被 execve 扔掉 → 这个形状是 1969 年图省事定下的 → 四个人、三个反复出现的形状（小改动赢 / 前提一变就重做 / 便宜的共享欠正确性的债）→ Thompson：两步因为 fork 最好写，好处是后来长出来的 → Linus：硬件切换在 Wine + 多核下无处兜底，改软件切换并拆出 mm / active_mm → Leroy 到 Drepper：线程就是 task，管理线程的活全塞回内核 → Arcangeli 到 Hildenbrand：copy on write 有了第三个主人，判据从 mapcount 到 page_count 再到独占位 → 债总留在当年还不存在的那条约束上。

| 原文必讲项 | 证据载体 | 场景 | 处理 |
|---|---|---|---|
| §0 三件事 | 三行分层表 | 3 | 保留，压成“小改动 / 前提消失 / 共享欠债” |
| §1 概览图 | pics/04-overview.png | 4 | 整图保留，按图例（彩框选择 / 灰框接力 / 红框债）讲 |
| §2.1 没有 fork 的 shell | Ritchie 1984 [R1] | 5–6 | 人物 Ken Thompson（照片已核）；shell 主循环、exit 装回 shell、tty 文件 |
| §2.2 27 行汇编、两步的真实原因 | [R1] 原文；Thompson 1989 访谈 [T1] | 7–8 | ASCII 双栏“合成一步 vs 只加 fork”改动清单；Ritchie 的“mainly because of the ease” |
| §2.3 两堵墙：chdir、IO 指针 | [R1] | 9 | 保留：cd 内建、struct file 共享偏移 |
| §2.5 你的视角：职责清晰 | [R1]、[B1]、[D0] | 10 | 认一半拧紧一半：是活下来的原因不是出生原因；窗口里普通系统调用；完整拷贝与多线程 fork 的代价 |
| §2.4 HotOS 2019 判词 | [B1] | 11 | 保留 1304 / 7.2% 中的 1304 与 41 两个数 |
| §3.1 打 A 打 B | Linus 1992 帖（核实表 Origin #1） | 12 | 人物 Linus（照片已核）；按核实结论：4 MB、1991 年 1 月，引帖子而非书 |
| §3.2 0.01：一个结构、ljmp 切换 | [L1] release notes；[L2] 0.01 sched.h 真源码 | 13–14 | 先讲 386 硬件切换原理，再上 0.01 switch_to 宏（kernel.org Historic 官方 tarball 逐字摘录） |
| §3.3 1998 软件切换 | [L3][L4] | 15–16 | ASCII 双栏 2.0.x vs 2.1.x；“修 bug 优先”原话；浮点保存写错后修好 |
| §3.4 mm 与 active_mm | [L5] | 17 | 保留内核线程 mm 为空、借 active_mm |
| §3.5 TSS 没死、调度器接力 | 原文 | 17 | sp0 一句；O(1) / CFS / EEVDF 只点名不展开（原文标“本份未查”） |
| §4.1 LinuxThreads | [X1] README | 18 | 保留每线程一 pid、信号发错人、约 1000 线程、管理线程 |
| §4.2–4.3 M:N vs 1:1 | [D1] | 19–20 | 人物 Drepper（照片已核）；ASCII 双栏；O(1) 消除理由；TLS 8192 |
| §4.4 管理线程的每件事塞回内核 | [D1] 表 | 21 | 五行分层图 |
| §4.4 数字 / §4.5 遗憾 | [D1][D2] | 22 | 15 分钟到 2 秒；16 KiB 内核栈、虚拟线程回到 M:N；NGPT 放弃（二手）不讲 |
| §5.1 三线程丢读 | [A1] | 23–24 | 先讲第三个主人的原理，再用时间线走五步 |
| §5.2 五轮修补 | [A3][A4][A5][A6] | 25–26 | 状态线五节点；2020-08 commit 09854ba 变更后 do_wp_page 真源码 |
| §5.3 mapcount vs page_count 之争 | [A7][A8][A9] | 27 | ASCII 双栏；Linus “mapcount 对 COW 毫无意义” |
| §5.4–5.5 三种失败与 PageAnonExclusive | [A11][W2]；v6.12 mm/memory.c | 28 | 三种失败、独占位、6.12 写时缺页先问独占位；“朝正确方向一步” |
| §6 约束回扣表 | 四行对照 | 29 | ASCII 表；去掉“BSD 引入 COW”的说法（原文标未查一手） |
| §7 呼应六问 | — | 30 | 化入总结卡与收尾 |
| 一手资料列表 / 无一手资料部分 | — | — | 文档保留，不朗读；二手项（NGPT 放弃、Piggin 转述、Gunthorpe 观点、ELF 来历）不进旁白 |

源码出处（副本均在 video-notes/src/）：
- linux-0.01__include__linux__sched.h：取自 https://www.kernel.org/pub/linux/kernel/Historic/linux-0.01.tar.gz（sha256 24454f83…1dc68d），场景 14 摘第 162–181 行，逐字一致（含 tab）。
- linux-09854ba94c6a__mm__memory.c：https://raw.githubusercontent.com/torvalds/linux/09854ba94c6aad7886996bfbee2530b3d8a7f4f4/mm/memory.c，场景 26 摘第 2926–2945 行；整段统一去掉一级缩进（解析器会剥掉首行行首空白，统一去一级避免首行错位），每行都是源行的后缀，空行保留。commit-09854ba94c6a.patch 为 GitHub .patch 原文，核对“17 insertions, 42 deletions”和“dark out / sunglasses”注释。
- v6.12__mm__memory.c：https://cdn.jsdelivr.net/gh/torvalds/linux@v6.12/mm/memory.c；第 3723–3726 行 `PageAnonExclusive(vmf->page) || wp_can_reuse_anon_folio(...)` 支撑“6.12 写时缺页先问独占位”；第 3623–3626 行墨镜注释仍在（folio 版措辞），支撑“6.12 里还在”。

事实处理：
- 按核实表 Origin #1：只说 1991 年 1 月、386、4 MB，“骄傲极了”出自 1992 年邮件列表帖子；不说 DX33。
- 原文 §1 “每一行右端都有红框”与图不符（Linus 行右端是灰框 EEVDF、Drepper 行没有红框），旁白改为按图例讲：红框是后来暴露的债。
- 原文 §5.3 说 2009 年是“该复制时没复制”；按 Hildenbrand [A11] 的分类，2009 与 2021 两个 bug 都是“错复制”（父进程的写被复制走、DMA 落进旧页）。视频只讲两次的共同结果“DMA 写进旧页、父进程读丢”，侧栏写成“fork 后父进程的写被复制走 / 多一个引用又被复制走”，不用“没复制”的说法。
- “COW 要等 1980 年代 BSD 才有”原文标为未查一手，约束回扣表改写为“后来的 copy on write”，不点 BSD。
- 2009 年 Arcangeli 补丁只说“fork 时直接给子进程拷一页”，不说是否进主线（原文只有二手转述）。
- Hildenbrand 的自评按 LWN [W2] 转述为“朝正确方向的一步”，不加引号原话之外的判断。
- 图 04-overview 源 SVG 里 Arcangeli 行最右的小字说明被画布截断（“2021-01 Arcangeli 反…”），属源图问题，未改原图，旁白不念这行。

人物：facetime 3 位（Thompson、Torvalds、Drepper）；Arcangeli 无可核实本人照片（同名意大利演员），改由文字场景 23 引出；Leroy、Hildenbrand 只在文字与旁白中出现。来源记录 pics/portrait-sources-ep4.json。

验收：31 场景，10 种视觉类型（spotlight 6、title 1、layers 2、html_slide 2、facetime 3、text 8、ascii 5、code_explain 2、timeline 1、statemap 1）；旁白 3343 字（本集无 example），按 5.4 字/秒加场间 1.5 秒估约 11.1 分钟（上一部同口径估 11.2 实际 9.4，预计实际 9.5~10 分钟）。`vmd_lint --theme anthropic`：0 错误、6 告警（两段源码多段高亮 CODE-MULTI-HL；spotlight 数字 NUM-RECAP 误报 ×4）。旁白无 atlas、无场景类型术语、无 markdown；画面与侧栏无箭头符号和带圈数字（用 -> 与阿拉伯数字）。五个 ASCII 图按渲染器 13 px / 22 px 字宽补齐，用默认渲染器出帧目检竖线对齐（框顶标题行误差 ≤4 px）。总结卡 pics/ep4-summary-card.png 1920×1080 已目检无溢出。未新建 story 插件。

分P标题建议：P4 Origin：fork 只有 27 行汇编，四个人替它还了五十年的债
