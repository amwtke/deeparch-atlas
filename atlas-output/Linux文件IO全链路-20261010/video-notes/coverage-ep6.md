# ep6 覆盖与证据矩阵

主角色：综合 / 决策（横向对照）。输入原文 Comparison 行 3278–3763，收尾核实表行 4215–4242，约束速查行 45–102。只写本集文件，未改源 MD、stages、原 SVG 或其他集。

主链：同一块 NVMe 盘读同一页（未命中）→ Linux 一串函数调用、NT 一个逐层填写的 IRP → 哪些形状是约束逼的、哪些是血统 → 接口层（就绪 vs 完成）→ 包的边界（IRP 信封 vs bio）→ 由此推出的三件后果（Fast I/O 必需、钩子拿参数 vs 过滤驱动拿包、叠加只能两层）→ 包≠并行、数据库在飞数 → 异步守恒与时间线 → 缓存同功能异结构 → 下四层趋同 → 判别法：约束一样形状就一样。

| 原文必讲项 | 证据载体 | 场景 | 处理 |
|---|---|---|---|
| 开篇锚点：notes.txt 与 D:\notes.txt 同盘同页 | 口播 + title | 2 | 保留 |
| §1 两栈并排图 | pics/06-overview.png | 3 | 整图保留，按行讲差异递减与包边界 |
| §2 NT 设计动机简表 | Dave Cutler 人物页 + text | 4–5 | 保留初衷、擅长、不擅长；典型应用压成 SQL Server 与 libuv 两例 |
| §3.2 IOCP 一次 ReadFile 全程 | timeline 六步 | 7 | 保留；并发值 0 = CPU 数（核实表 #10） |
| §3.2 线程 LIFO / 包 FIFO 各保什么 | text + sidebar C5 | 8 | 保留：热与压线程数 / 公平与有界等待；Linux IPI 回提交核作对照 |
| §3.3–3.5 四接口对照、各补一半 | 双栏 ASCII + sidebar C3 | 9–10 | 保留；表中 IOCP 命中重复投包细节文档保留 |
| §0 / §4.2 包的位置是最深分叉 | pics/06-irp-vs-bio.png | 11–12 | 整图保留，讲三个一一对应 |
| §4.2.1 IRP 是信封，扇区号出现时间两边一样 | ASCII 信封结构 | 13 | 保留；关联 IRP、MDL、paging IRP 三个配套文档保留 |
| §4.2 Fast I/O 与 Wait=FALSE 对 IOCB_NOWAIT | text + sidebar C9 | 14 | 保留，作为"包太重"的推断验证 |
| §4.6 特性 1：钩子位置与拿到什么 | rw_verify_area 真码 + text | 15–16 | 保留；L560 / L470 / L474 / L573 口播点名 |
| §4.6 overlayfs 代理、页挂叶子 inode | text + ovl_read_iter 真码 | 17–18 | 保留 copy-up 只在 sidebar 提；Docker 一百容器共享一份页作例 |
| §4.6 套娃上限 FILESYSTEM_MAX_STACK_DEPTH | super.c 深度检查真码 | 19 | 保留：0/1/2、16 KB 内核栈、NT 叠驱动只加栈位 |
| §4.6 特性 2：可挂起即异步 | ASCII 信封 + 口播 | 13 | 合并进信封场景 |
| §4.6.1 包≠并行、函数调用≠锁 | text + sidebar C2 | 20 | 保留并行 vs 在飞两词 |
| §4.6.2 数据库在飞数 | text + sidebar C10 | 21 | 保留 InnoDB、PG 18、SQL Server；InnoDB 收割线程默认数与"模拟 AIO"文档保留 |
| §4.7 异步守恒三种接法、Unix 四理由 | text | 22–23 | 保留三种接法与年份；四理由压成三条入例子 |
| §4.7.1–4.7.2 时间线与"并发定方向、代价比定年份" | timeline 七节点 | 24 | 保留；SPDK 一步文档保留 |
| §5 缓存管理器对 page cache | 双栏 ASCII + sidebar C8 C10 | 25 | 保留同功能异结构与 section 复用；预读算法、lazy writer 1/8、32 位视图限制文档保留 |
| §6 下四层趋同 | layers 四行 | 26 | 保留 NTFS 日志 5 秒检查点、SCSI 窄腰、Server 2025 原生驱动 |
| §7 约束回扣 | text + sidebar C7 C12 C2 C11 | 27 | 保留同 / 异两栏与判别法 |
| §8 呼应：必须的定义 | 总结卡 takeaway + 场景 27 例子 | 27–28 | 保留 |
| §9 出处与待核 | 本文件 | — | 文档保留，不朗读 |

源码（固定 Linux v6.12，经 jsDelivr gh/torvalds/linux@v6.12 取原文，存 video-notes/src/，三段摘录与原文逐行一致）：

- fs/read_write.c L453–475（rw_verify_area 后半：参数检查、L470 security_file_permission、L474 fsnotify_file_area_perm）；口播另点 vfs_read L560 调用点、L573 fsnotify_access。
- fs/overlayfs/file.c L267–290（ovl_read_iter）；口播背景 L171 file->private_data = realfile。
- fs/overlayfs/super.c L1123–1136（下层深度取最大、s_stack_depth++、超限报 maximum fs stacking depth exceeded）；include/linux/fs.h L275 FILESYSTEM_MAX_STACK_DEPTH 2 在高亮与口播中引用。
- fs/backing-file.c L180–183：is_sync_kiocb 分支才调 vfs_iter_read，高亮据此写"同步读时"。
- Windows 侧无源码场景，全部按原文所引微软文档与 Windows Internals 口述，不展示示意代码。

人物：Dave Cutler，照片来自维基百科条目首图（Commons File:DavidCutler_WindowsAzure.JPG，CC BY 3.0，2008-07-28），已下载到 pics/person-dave-cutler.jpg 并目检为真人肖像，来源记于 pics/portrait-sources-ep6.json。

事实修正与收紧：

1. NVMe 驱动进主线年份：原文 §6.2 写 2011 年直接挂块层；按收尾核实 #6，初版 b60503ba 随 3.3（2012-03）入主线，VMD 改为"2012 年进主线"。
2. backing_file_read_iter 只在同步 kiocb 时调 vfs_iter_read；VMD 高亮写明"同步读时"，不笼统说"就是调 ext4 的 read_iter"。
3. 6.12 的 ovl_read_iter 经 ovl_real_fdget 取真实文件（copy-up 后可换成上层文件），不是直接读 private_data；高亮按真码表述。
4. IoRing 首版只支持读（核实 #9，21H2 build 22000）；22H2 加写与 flush 的出处只有第三方文章，VMD 不展开。
5. storport 的 NVMe 队列到 CPU 映射仍无法核实（#14），VMD 不作任何断言。
6. 原文 §4.7 标题"晚了 45 年"未入画面与口播（spotlight 不引入新数字），改为"为什么这么晚"。

验收：29 场景，10 种视觉类型（spotlight 5、title 1、html_slide 3、facetime 1、text 9、timeline 2、analogy 1、ascii 3、code_explain 3、layers 1）。类比 1 个，复用 iocp-vs-io-uring-post-office，口播含角色映射、共同规则与失效边界。旁白含例子 3721 字符（其中汉字约 2400），按 字数÷5.4 + 场景×1.5 秒 + 3 秒估 12.3 分钟；英文术语占比高，实际以 TTS 为准。`venv/bin/python scripts/vmd_lint.py --theme anthropic` 退出码 0，0 错误 3 告警（均为 CODE-MULTI-HL，源码分段高亮按顺序配旁白）。旁白 atlas 禁词、场景术语、免责与制作用语检查均无输出。总结卡 pics/ep6-summary-card.png 1920×1080 已目检无溢出。未渲染、未提交、未上传。
