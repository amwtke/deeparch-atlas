# 阶段 6:Linux 文件 IO 全链路 与 Windows NT I/O 栈的对照

> 前五份把 Linux 的五层从"是什么"讲到"源码和数字"。这一份把它放到另一套从头设计的 I/O 栈旁边 —— Windows NT —— 看哪些选择是约束逼出来的(两边一样),哪些是血统带来的(两边不同)。按你定的范围:**比到底,篇幅压在上面三层**(接口层、I/O 管理器与 IRP 对 VFS 与 bio、缓存管理器对 page cache),下面四层合成一章。
>
> **依据**:Windows 内核不开源。Windows 侧的说法来自微软文档(learn.microsoft.com 的 Win32 / WDK 页)、Windows Internals(Russinovich 等)和少量逆向分析文章,每处给出处,拿不准的标「待核」,不编数字。Linux 侧沿用 6.12 和前几份的行号。
>
> 主角文件沿用:`/mnt/nvme/notes.txt`;Windows 侧对应 `D:\notes.txt`(NTFS,4 KiB 簇)。

---

## 约束清单速查(C1 ~ C12)

> 引用约定:编号永远带短名。五条根:R1·速度断崖(C2 C6 C9)/ R2·硬件多样(C1 C4)/ R3·接口固定(C8 C11)/ R4·多进程共享(C3 C5 C12)/ R5·活过断电(C7 C10)。

#### C1·厂商定接口
硬件接口由厂商 / 标准定义,内核无法统一。**口诀**:语言不归我管 → 每种盘一个翻译。
#### C2·设备慢且异步
设备比 CPU 慢 10³ ~ 10⁷ 倍,完成是异步事件。**口诀**:发完就走,中断再回。
#### C3·特权态门槛
寄存器 / DMA / 中断只能在特权态操作。**口诀**:进程只能请求,不能动手 —— 每次请求都要过一次系统调用。
#### C4·定长块
持久设备最小读写单位是固定大小的块。**口诀**:读 1 字节也搬一整块。
#### C5·多核并发
多核多进程并发发起 IO。**口诀**:一把锁等于浪费所有核。
#### C6·介质形状相反
机械盘怕乱序,NVMe 怕喂不饱。**口诀**:没有对所有盘都对的策略。
#### C7·跨块不原子
单块写原子、多块不原子。**口诀**:找一个单块写定生死。
#### C8·流 vs 块
程序要"名字 + 变长流",介质只给"编号 + 定长块"。**口诀**:账本必须也在盘上。
#### C9·速差+局部性
DRAM 与介质差 10² ~ 10⁵ 倍,访问有局部性。**口诀**:读过的大概率再读。
#### C10·内存装不下
缓存须淘汰、须延迟回写,存在不一致窗口。**口诀**:write 返回 ≠ 在盘上。
#### C11·POSIX接口冻结
实现开放增长,接口几十年固定。**口诀**:一侧冻结,一侧生长。
#### C12·同文件多开
同一文件多进程同时打开,各有偏移,对象只有一份。**口诀**:file 是打开实例,inode 是对象。

---

## §0 从 Deep 走到 Comparison:三件事记住

承上:Deep 的三条主线落在三个对象上 —— `kiocb` 里的 `IOCB_NOWAIT` 开关、`request.tag` 那条线、`io_rings` 两个环。把 NT 放到旁边,这三个对象各自对上一个"长得不一样但解同一道题"的东西。三件事就是三对。

### §0.1 事一:异步建在同步上,还是同步建在异步上 —— 从 C2·设备慢且异步 + C11·POSIX接口冻结 推出

因为完成永远是异步事件(C2·设备慢且异步),两边都躲不开;又因为两边继承的接口语义相反(C11·POSIX接口冻结 冻住的是 Unix 的"`read` 返回时数据已在 buf";NT 继承的是 VMS 的"`$QIO` 发出去,AST 回调通知")→ 要解决"把异步完成表达给进程"→ Linux 的解法是**异步建在同步上**:`read_iter` 是可以睡的函数调用,io_uring 用 `IOCB_NOWAIT` 先试、回调挂页 / 挂 bio、io-wq 兜底三级拼出异步(Deep §4.2.3 / §4.2.4);NT 的解法是**同步建在异步上**:每个请求从 I/O 管理器起就是一个可以 pending 的包(IRP),"同步"只是内核替你在文件对象的事件上等一下再返回。

### §0.2 事二:两边都长出了同一条"快路径" —— 从 C9·速差+局部性 推出

因为缓存命中是常态(C9·速差+局部性),而完整的请求机制(Linux 的 bio → request → tag,NT 的 IRP 走完驱动栈)对一次 memcpy 来说太重 → 要解决"命中时别走全套"→ Linux 用 `IOCB_NOWAIT` 当场完成;NT 用 **Fast I/O**:I/O 管理器先查文件系统登记的 `FAST_IO_DISPATCH` 表,调 `FastIoRead` 直接从缓存拷,返回 FALSE 才造 IRP。两边独立长出了"乐观先试、失败再走全套"的同一个形状,连"不等待"的开关都对得上:`FsRtlCopyRead` 的 `Wait = FALSE` 在页不在内存时返回 FALSE 而不阻塞 —— 这就是 `IOCB_NOWAIT`。

### §0.3 事三:缓存按什么索引 —— 从 C8·流 vs 块 + C10·内存装不下 推出

因为缓存里放的是"文件的第几页"而不是"盘的第几块"(C8·流 vs 块,What 阶段就定下的 (inode, index) 键),又因为缓存要淘汰、要延迟回写(C10·内存装不下)→ 要解决"用什么结构管这些页、谁负责把缺的页搬进来"→ Linux 用 **XArray**,键是 (inode, 页号),文件系统显式查、显式发 bio;NT 把文件按 **256 KB 的视图映射进内核虚拟地址空间**(每个视图一个 VACB),缓存管理器只做 memcpy,页不在就触发**缺页**,由内存管理器发 paging I/O 把它拉进来。一个用索引结构,一个用页表;一个显式搬,一个靠缺页。

### §0 结论

| 事 | Linux | Windows NT | 为什么存在 |
|---|---|---|---|
| 一 异步在哪一层表达 | `read_iter` 同步函数链 + 三级拼接;包(bio)只在 ②③ 之间出现 | 包(IRP)从 ① 之上就出现,每层可 pending;同步 = 内核替你等 | C2·设备慢且异步 两边一样;C11·POSIX接口冻结 两边冻住的语义相反 |
| 二 快路径 | `IOCB_NOWAIT` 命中当场完成 | Fast I/O:`FastIoRead` → `FsRtlCopyRead` → 缓存 memcpy,不造 IRP | C9·速差+局部性 两边一样 → 同形 |
| 三 缓存索引 | XArray (inode, index);显式查、显式发 bio | 256 KB 视图映射进内核地址空间;memcpy 触发缺页,Mm 发 paging I/O | C8·流 vs 块 + C10·内存装不下 两边一样;结构不同是因为 NT 先有 section 对象可复用 |

三件事的关系:事一决定了事二、事三的形状 —— NT 的 IRP 太重,所以 Fast I/O 是必需品;NT 的内存管理器先有 section 对象(可执行文件映射),所以缓存复用它。往下走到块层以后,两边的差异收敛到接近零(§6)。

---

## §1 一张极简概览图

![两套 I/O 栈并排:上三层差异大,下四层趋同](pics/06-overview.svg)

从图上能读出五件事:

1. 七行对七行,**差异从上往下递减**:接口层和"I/O 管理器对 VFS"两行差异最大,驱动和硬件两行几乎重合。
2. 两边都有一条**绕过主路径的快路径**(Fast I/O 与 `IOCB_NOWAIT`),都从接口层直通缓存。
3. NT 的"包"(IRP)边界画在接口层正下方;Linux 的"包"(bio)边界画在文件系统正下方 —— **包的位置**是两张图最深的差别。
4. 两边缓存都夹在文件系统和块层之间当旁路,但 NT 的缓存旁边多了一个内存管理器 —— 缓存管理器自己不管页,页归 Mm。
5. 块层以下,两边都有一段 SCSI 血统的窄腰(Linux 的 libata 时代 / NT 的 SRB),之后接 NVMe 原生驱动;Windows 到 2025 年的 Server 版才有绕开 SCSI 磁盘层的 `nvmedisk.sys`。

---

## §2 设计动机简表:Windows NT I/O 栈

### §2.1 Windows NT I/O 栈(I/O 管理器 + IRP + 缓存管理器 + IOCP / IoRing)

**初衷**:1988 年微软请来 DEC 的 Dave Cutler 设计一个可移植、支持多处理器、带安全模型的新内核。Cutler 团队带着 VMS 的经验(`$QIO` 异步 I/O + AST 回调,1977),把"所有 I/O 都是异步的,同步只是上层等一下"写进了内核的驱动合同 —— 任何一层都可以把请求标成 pending。NT 3.1 于 1993 年 7 月发布;I/O 完成端口在 NT 3.5(1994)加入,目标是让服务器用少量线程处理大量并发 I/O(NT 3.5 于 1994 年 9 月 21 日发布;Banga 等人的 USENIX 论文写明 "Windows NT 3.5 added … I/O completion port",微软自己的页面没写版本号)。

**擅长**:
- 大量并发、每个都要等设备的 I/O,线程数远小于在飞请求数(文件服务器、数据库、Web 服务器)
- 文件、socket、管道、设备用同一个等待原语:一个端口收所有完成
- 可插拔的驱动栈:过滤驱动、类驱动 / 端口驱动分层,第三方驱动插进栈里互不认识也能协作,每层都能异步

**不擅长**:
- 就绪式编程:没有 `poll` 的等价物,`WaitForMultipleObjects` 上限 64 个句柄;要在 Windows 上做 epoll 风格的 API(libuv、Rust mio),只能走未公开的 `\Device\Afd` 接口模拟就绪
- 每个请求一次系统调用、每次收割一次系统调用(2021 年 IoRing 之前没有共享环),高 IOPS 下系统调用成本不可摊销
- 每个请求分配并逐层传递一个 IRP;缓存命中路径走不起它,所以必须另开 Fast I/O
- 内核不开源,行为只能靠文档和逆向

**典型应用场景**:
- SQL Server:`FILE_FLAG_NO_BUFFERING` + 重叠 I/O + 完成端口,自己管缓冲池
- IIS / `http.sys`:内核态 HTTP 栈,把完成投递给工作进程
- .NET 运行时线程池的 I/O 线程:`ThreadPool.BindHandle` 把句柄绑到完成端口
- Node.js(libuv)与 Rust tokio(mio)在 Windows 上的事件循环:完成端口之上用 `\Device\Afd` 模拟就绪

(Linux 侧的四件事前几份已经讲过,不重复。)

---

## §3 对照一:接口层 —— IOCP 对 epoll 与 io_uring

### §3.1 对比维度

等就绪还是等完成;每次 I/O 进几次内核;线程谁来管。

### §3.2 IOCP 的核心做法

一次 `ReadFile` 在完成端口下的全程:

1. `CreateFile(…, FILE_FLAG_OVERLAPPED)` 打开;`CreateIoCompletionPort(h, port, key, 0)` 把句柄绑到端口。最后一个参数是**并发值**:允许同时在跑的线程数,0 表示等于 CPU 数(微软文档)。
2. `ReadFile(h, buf, len, NULL, &ov)` → `NtReadFile` → I/O 管理器造一个 IRP 往驱动栈发;驱动把它标成 pending,`ReadFile` 返回 `ERROR_IO_PENDING`。buf 从这一刻起归内核,直到完成。
3. 线程去干别的,或者调 `GetQueuedCompletionStatus(port, …)` 在端口上睡;Vista 起有 `…Ex` 一次取一批。
4. 设备完成 → `IoCompleteRequest` 沿驱动栈回走 → I/O 管理器把一个**完成包**(字节数、key、`OVERLAPPED*`)排进端口的队列。
5. 端口按 **LIFO** 唤醒最近睡下的那个线程(它的缓存最热),交给它**最老**的包(包按 FIFO 排);微软文档原话:"threads that block their execution on an I/O completion port are released in last-in-first-out (LIFO) order"。
6. 并发值生效:在跑的线程数到了上限,新完成的包就排着,等某个线程睡回端口。这是内核替你做的线程节流。

**为什么一个队列两头两种顺序**(第 5 步):线程 LIFO 保的是**热** —— 最近睡下的线程,栈和刚碰过的数据还在这个核的 L1 / L2 里,TLB 里还有它的页表项,叫醒它最便宜;第二层收益是最久没醒的线程一直睡着,池子能看出它们多余而收掉,活跃线程数自然压到并发值附近(C5·多核并发 的两种成本:切换和缓存,都省)。这和 Deep §3.2 `blk_mq_complete_request_remote` 用 IPI 把完成送回提交那个核、io_uring 的 task_work 回到提交进程自己的上下文跑,是同一个动机。包 FIFO 保的不是吞吐(顺序不改变活的总量),是**公平**:没有哪个包被晾在后面饿死,每个完成的等待有上界 —— 和 mq-deadline 用扇区树管吞吐、用 FIFO 管不饿死(How §4.4.1)是同一个结构,只是两套顺序分别用在线程和包上。

两个和 Linux 对得上的细节:

- **命中时同步返回**:缓冲命中的 `ReadFile` 会当场完成、返回 TRUE,但完成包**仍然会**投进端口 —— 你会收到两次。Vista 加了 `SetFileCompletionNotificationModes(FILE_SKIP_COMPLETION_PORT_ON_SUCCESS)` 才关掉重复投递。这和 Deep §4.4 候选 E 是同一个问题:快路径和完成模型怎么拼。
- **IoRing(Windows 11,2021)**:`NtCreateIoRing` 建一个 `IORING_OBJECT`,分配一个 section 同时映射到内核和用户态,里面是提交队列(head / tail + `NT_IORING_SQE` 数组,上限 0x10000 条)和完成队列(`IORING_CQE`:`UserData`、结果码、信息值,上限 0x20000 条);`NtSubmitIoRing` 一次提交一批。首版只有读、登记文件、登记缓冲区、取消四种操作;22H2(22621)加了写和 flush,环版本升到 3(依据 Yarden Shafir 2022 年的跟进文章;微软 Learn 迄今没给这两个 Build 函数的参考页,只有操作码枚举和 `IsIoRingOpSupported`)。形状就是 io_uring。

### §3.3 在五元组上的差异

| | epoll(Linux,2002) | io_uring(Linux 5.1,2019) | IOCP(NT 3.5,1994) | IoRing(Windows 11,2021) |
|---|---|---|---|---|
| 模型 | 就绪 | 完成 | 完成 | 完成 |
| 核心对象 | `eventpoll`:红黑树 + `rdllist` | `io_rings`:两个共享内存环 | 端口:内核队列对象,包 FIFO、等待线程 LIFO | `IORING_OBJECT` + 一个 section 同时映射两边 |
| 元数据位置 | 内核 | 用户态可见 | 内核 | 用户态可见 |
| 每个 I/O 进内核次数(C3·特权态门槛) | ≥ 2(等 + 读) | 0 ~ 1 | 2(发 + 收),收可批量 | 0 ~ 1 |
| 磁盘文件(C2·设备慢且异步) | 不支持,`EPERM` | 支持,三级拼接 | 支持,IRP 天生 | 首版只支持读 |
| 线程模型(C5·多核并发) | 无,自己建线程 | 无;SQPOLL 是内核线程替你提交 | 内置:并发值 + LIFO 唤醒 | 无 |
| 命中快路径 | 不适用 | `IOCB_NOWAIT` 当场完成,cqe 直接写 | 同步返回 + 仍投包;Vista 加开关 | 同 io_uring |
| 代价 | 只管 socket;读要自己做 | 三级拼接,io-wq 兜底;接口复杂 | 每请求一次系统调用;没有就绪语义 | 操作集小;新 |

### §3.4 为什么 Windows 这么选

三条约束的权重和 Linux 不同:

- **C2·设备慢且异步 的解法在下层已经有了**。IRP 从驱动层起就是 pending 的(§4),完成模型对 NT 是零成本 —— 把完成包排进一个队列就行。Linux 要到 2019 年才有同等的东西,因为它的下层是同步函数链,先得把异步拼出来。
- **C5·多核并发 的代价更高**。NT 没有 `fork`,线程创建贵、每个线程带内核栈;1994 年的服务器目标是"少量线程、大量连接"。所以端口自带线程节流(并发值)和缓存友好的唤醒顺序(LIFO),Linux 把这些留给用户态。
- **C3·特权态门槛 的价格当时不值得省**。1994 年没有 Spectre,也没有百万 IOPS 的盘;每请求一次系统调用够用了。直到 io_uring 证明了共享环的价值,Windows 11 才补上 IoRing。

反向的证据也有:**从完成模拟就绪和从就绪补完成一样别扭**。libuv、Rust mio 要在 Windows 上提供 epoll 风格的接口,只能往 `\Device\Afd` 驱动发 `AFD_POLL` 请求、再把这个请求的完成当作就绪事件 —— 用完成端口模拟出一个就绪队列。说明两者是两种模型,不是一个 API 的两种写法(呼应 Deep §0.3)。

### §3.5 这个对比突出了什么

Linux 的"就绪优先"不是必然,是 Unix fd 语义的路径依赖;NT 的"完成优先"也不是必然,是 VMS 的路径依赖。两边最终各补上了对方那一半:Linux 2019 补完成模型(io_uring),Windows 2021 补共享环(IoRing),Windows 生态用 `\Device\Afd` 补就绪模型。**就绪与完成各有不可替代的场景**:就绪适合"缓冲区自己管、一个 socket 上多次小读";完成适合"缓冲区交出去、尤其是磁盘"。这就是 Deep §4.3 "方向必然、年份偶然"在另一套系统上的验证。

---

## §4 对照二:I/O 管理器与 IRP 对 VFS 与 bio

### §4.1 对比维度

请求是"函数调用链"还是"包";包的边界画在哪一层。

### §4.2 NT 的核心做法

![同一次未命中读:Linux 的函数调用链 vs NT 的请求包,快路径与挂起的表达一一对应](pics/06-irp-vs-bio.svg)

图上左右各一条路,中间是同一道题的两个答案;下面的三个一一对应是这一章的骨架。先看图再读文字。

**IRP(I/O Request Packet)** 是 NT 所有 I/O 的载体:一个头(状态、用户缓冲区或 MDL、发起线程、标志)加 N 个 **栈位**(`IO_STACK_LOCATION`),设备栈里每个驱动一个栈位,里面放这一层看到的主功能码(`IRP_MJ_READ`)、参数(偏移、长度)和完成例程。一次 `NtReadFile` 的全程:

1. I/O 管理器分配 IRP,填第一个栈位,`IoCallDriver` 交给设备栈最顶层(通常是过滤驱动或文件系统)。
2. 每一层的分发例程三选一(微软的「处理 IRP 的几种方式」速查表):**完成**(填状态,`IoCompleteRequest`);**转发**(复制栈位给下一层,可选 `IoSetCompletionRoutine`,`IoCallDriver`);**挂起**(`IoMarkIrpPending`,返回 `STATUS_PENDING`,把 IRP 放进自己的队列)。文档要求:不完成也不转发就**必须**标 pending,否则 I/O 管理器会在例程返回时把它当完成处理。
3. 设备做完 → 端口驱动 `IoCompleteRequest` → I/O 管理器沿栈位**往上回走**,逐层调完成例程(可以返回 `STATUS_MORE_PROCESSING_REQUIRED` 把 IRP 截下来再用)。
4. 到顶:I/O 管理器往发起线程排一个内核 APC,在那个线程的上下文里把状态、字节数写回用户态的 `OVERLAPPED`、触发事件;句柄绑了完成端口就改为排完成包(§3.2 第 4 步)。
5. **同步句柄**(没开 `FILE_FLAG_OVERLAPPED`):`NtReadFile` 在返回前自己等文件对象的事件。同步是建在异步上的一层薄壳。

#### §4.2.1 IRP 不是块层的包:它怎么能在 ① 就造出来

IRP 和 bio 不是同一种东西。bio 里是扇区号、页列表、完成回调,块层拿到就能执行;IRP 是一个**信封**,扇区号是后来才写进去的:

| 部分 | 内容 | 谁填、什么时候 |
|---|---|---|
| 头 | 用户缓冲区的描述(MDL:一张已钉住的物理页清单)、发起线程、状态、标志 | I/O 管理器,造 IRP 时 |
| 栈位 1 | `IRP_MJ_READ`、文件对象、**文件内字节偏移**、长度、完成例程 | I/O 管理器,给设备栈最顶层 |
| 栈位 2 | 同样的字段,偏移已换算成**卷内字节偏移** | 文件系统(NTFS)算完映射后填 |
| 栈位 3 ~ N | 分区偏移、磁盘偏移、SRB 指针 | 卷管理、分区管理、磁盘类驱动各填自己下一层的 |

栈位数量在打开时就知道(`DeviceObject->StackSize`,设备栈多深就多少个),一次分配用到底。每层只读自己的栈位,算完把结果写进下一层的栈位(`IoGetNextIrpStackLocation` / `IoCopyCurrentIrpStackLocationToNext`),再 `IoCallDriver`。所以 NT 并没有在 ① 就算出扇区 —— 它只是把"一路上每层要用的参数槽"提前分配好了。**扇区号出现的时间点两边一样:文件系统查完映射之后。**

三个配套机制:

- **碎片文件**:一个栈位只能装一段连续的卷偏移。文件在盘上是三段,NTFS 就用 `IoMakeAssociatedIrp` 造三个关联 IRP,各描述一段、各自往下走,三个都完成主 IRP 才完成 —— 和 ext4 对两个 extent 造两个 bio 是同一件事(Deep §3.3.2 两 extent 算例),只是 Linux 的 bio 本来就是那时才造,NT 是把信封复制了几份(微软 FastFAT 样例源码里单段复用主 IRP 填下一栈位直接下发,多段才拆关联 IRP;NTFS 闭源,按 WDK 规则推定相同)。
- **MDL**:信封头里那张物理页清单让底下任何一层拿到的都是可直接 DMA 的目标,不必回到进程地址空间。Linux 的对应物是 bio 里的 `bio_vec`,缓冲读要等 page cache 查完才有;`O_DIRECT` 路径上 `bio_iov_iter_get_pages`(Deep §4.2.4)做的就是 MDL 这件事。
- **缓存路径上包也是晚造的**:"同一个信封走到底"只对不走缓存的读成立。缓存读的 IRP 到 NTFS 就停了,NTFS 调 `CcCopyRead` 从缓存拷;页不在,memcpy 缺页,**内存管理器另造一个 paging IRP**(`IRP_PAGING_IO | IRP_NOCACHE`)发给 NTFS,那个才是走到盘上的包(§5.2 第 4 步)。所以真正到盘的包两边都是在未命中那一刻造的:Linux 由预读造 bio,NT 由 Mm 造 paging IRP。

于是 §0.1 / §4.6 那句"NT 的包从 ① 起"要读成:**NT 的信封从 ① 起,扇区和 Linux 一样晚**。两边真正的差别只剩一条 —— 用户看到的那个请求,在 NT 是一个可以被排队、挂起、截住的对象,在 Linux 是一次函数调用。

**Fast I/O** 是这条路的逃生门。造 IRP、走栈、排 APC 对一次缓存命中的 memcpy 来说太重,所以 I/O 管理器在造 IRP 之前先查文件系统登记的 `FAST_IO_DISPATCH` 表(第一项 `FastIoCheckIfPossible`,第二项 `FastIoRead`);微软建议文件系统把 `FastIoRead` 直接指向 `FsRtlCopyRead`,它调缓存管理器的 `CcCopyRead` 从缓存拷。文档原话:当 `FsRtlCopyRead` 返回 FALSE,或 IoStatus 显示拷贝失败,调用方必须改造一个常规的读 IRP。`Wait = FALSE` 时,拿不到锁或页不在内存就返回 FALSE 而不阻塞。文件上一旦有排他的字节范围锁,文件系统要把 `IsFastIoPossible` 标成 `FastIoIsQuestionable`。

**过滤驱动 / minifilter**:因为所有请求都是 IRP,任何驱动都能插进设备栈看到每一个请求(杀毒、加密、配额、备份都这么做);Filter Manager 把这件事标准化成 minifilter。这是 IRP 设计最直接的收益。

### §4.3 Linux 的对应物

- ① 没有包。`vfs_read` → `f_op->read_iter` 是**函数调用**,可以睡;文件系统之间叠加靠 VFS 挂载(bind、overlayfs),不是请求包逐层传。
- 包从 ② 往下才出现:`bio` 带 `bi_sector` / `bi_io_vec` / `bi_end_io`(Deep §3.2),块设备叠加(dm、md)靠**克隆 bio** 往下发,不是在同一个包里加栈位。
- 异步在 ① 的表达是**事后加的**:`kiocb.ki_complete` 非空就是异步(2002 年 AIO 为 `O_DIRECT` 加,iomap 沿用,Deep §4.2.4);缓冲读到 2020 年才有页回调。
- 快路径:`IOCB_NOWAIT`(2017)。不是绕开包 —— ① 本来就没有包 —— 而是绕开睡眠。

Deep 的三件货物对 NT 的三件货物:

| Linux | Windows NT | 一样的地方 | 不一样的地方 |
|---|---|---|---|
| `file` + `inode`(C12·同文件多开) | `FILE_OBJECT` + FCB(文件系统私有的文件控制块)+ section 对象 | 打开实例与对象分开 | NT 的"对象"没有 VFS 级的统一结构,FCB 归文件系统自己定义 |
| `folio` | 缓存视图里的页,归内存管理器 | 都是缓存和 mmap 共享的物理页 | Linux 由文件系统直接操作 folio;NT 的文件系统通过虚拟地址间接碰页(§5) |
| `bio` → `request` | IRP → SRB(端口驱动的 SCSI 请求块) | 到块层都变成"扇区 + 缓冲区列表 + 完成回调" | NT 的 IRP 在 ① 就有;bio 在 ② 之下才有 |

### §4.4 在五元组上的差异

| | Linux | Windows NT |
|---|---|---|
| 核心抽象 | ① 函数指针表(`file_operations`)+ 调用链;②③ 之间才有包(bio) | 从 ① 起就是包(IRP),每层一个栈位 |
| 异步表达 | `ki_complete` 非空即异步(事后加) | `IoMarkIrpPending` + `STATUS_PENDING`,任何一层都能挂起(从头就有) |
| 栈叠加 | 文件系统靠挂载;块设备靠 bio 克隆 | 任意驱动插进设备栈,IRP 逐层传;minifilter 标准化 |
| 快路径 | `IOCB_NOWAIT`:绕开睡眠 | Fast I/O:绕开 IRP |
| 处理 C2·设备慢且异步 | 三级拼接(NOWAIT / 回调 / io-wq) | 包天生可 pending |
| 处理 C3·特权态门槛 | 一次系统调用一个请求(io_uring 前) | 一次系统调用一个请求(IoRing 前) |
| 代价 | 异步是补丁;缓冲读 2020 年才真异步 | 每个 I/O 分配 IRP、走完整栈、排 APC;快路径是必需品不是优化 |

### §4.5 为什么 NT 这么选

- **C1·厂商定接口 加上一条 Linux 没有的约束:驱动在树外**。NT 要让第三方的二进制驱动插进栈里互不认识还能协作,包 + 每层栈位是最通用的合同:每一层只看自己的栈位,往下传就复制一份。Linux 所有驱动在同一棵源码树里,函数调用链最便宜,不需要二进制合同。
- **VMS 血统**让 pending 成为默认(§0.1),包是 pending 的自然载体:一个可以被放进队列、被截住、被回走的东西。
- **代价**是每次 I/O 都要分配和走完这个包。所以 Fast I/O 不是锦上添花 —— 没有它,缓存命中的读也要造 IRP、排 APC,NT 的文件读会比 Unix 慢一个量级。

Linux 把包的边界放在 ②③ 之间,是因为那里是异步**不可避免**的第一层(设备完成靠中断),再往上用函数调用更省;2001 年 bio 诞生时就是这么定的(Origin §4)。两边都把包放在"从这一层起必须异步"的地方,只是对"从哪一层起必须异步"的回答不同:NT 说从接口层起,Linux 说从块层起。

### §4.6 这个对比突出了什么

**包边界的位置**是两套栈最深的分叉,其余差异都是它的后果:NT 有 Fast I/O 是因为 IRP 重;NT 的完成端口零成本是因为 IRP 可 pending;Linux 的 io_uring 要三级拼接是因为 ① 没有包。Linux 的"① 是同步函数链"不是必然,是 Unix 血统加"驱动在树内"这个组织形态的产物。

把请求做成对象,直接养出 NT 的两个特性:

1. **谁能看到每个请求**:对象在设备栈里逐层传,任何第三方驱动插进栈就能看到、改掉、拦下每一个 I/O —— 杀毒、加密、配额、备份都靠这个,后来标准化成 minifilter。Linux 的 ① 没有对象可拦,对应功能散在 LSM 钩子、fanotify、FUSE、overlayfs 里,各盖一部分。

   Linux 上要做"每次 read 先过一道检查、不合格就拒绝",位置在 ① 最前面、进文件系统之前的两行(6.12 `fs/read_write.c`),不在文件系统与块层之间 —— 到了那里请求已是 bio,只有扇区没有文件和进程,而且缓存命中的读根本不经过块层:

   ```
   L560  rw_verify_area(READ, file, pos, count)                 ← vfs_read 第一件事
   L470      security_file_permission(file, mask)               ← LSM 钩子(SELinux / AppArmor / BPF LSM),可拒绝
   L474      fsnotify_file_area_perm(file, mask, ppos, count)   ← fanotify FAN_ACCESS_PERM:用户态守护进程回答允许 / 拒绝,按访问杀毒挂这
   L573  fsnotify_access(file)                                  ← 读完之后:只通知,不能否决
   ```

   钩子不比 NT 靠后,差别在钩子手里拿着什么:

   | | Linux 的钩子 | NT 的 minifilter |
   |---|---|---|
   | 拿到什么 | `file`、读写标志、偏移和长度 | 整个 IRP:缓冲区、偏移、长度、完成例程 |
   | 读之前 | 能拒绝 | 能拒绝、能改参数、能自己完成它 |
   | 读之后 | 只收到通知 | 完成例程里拿到数据,可以改(透明解密在这做) |
   | 看得到数据吗 | 不能 | 能 |
   | 多个过滤者的顺序 | LSM 全局钩子链;fanotify 按优先级 | 按设备栈高度明确排序 |
   | 想碰数据 | 叠一个完整文件系统:ecryptfs / overlayfs / FUSE | 一个过滤驱动 |

   少的那样东西就是"包":Linux 的钩子看到的是一次调用的参数,NT 的过滤驱动看到的是一个能跟着请求走到底、回来时还带着数据的对象。

   表里"叠一个完整文件系统"指的是 overlayfs 这类**叠加文件系统**:自己不管盘上任何块,把两个已有目录合成一个视图(`mount -t overlay -o lowerdir=…,upperdir=…,workdir=… /merged`),下层只读、上层可写,读只在下层的文件就转调底层文件系统那个真实文件的 `read_iter`,要改就先整个拷到上层(copy-up)。Docker 镜像分层就是它。它在 ② 的位置,但"设备"是另一个文件系统的文件;它能拦住每一次文件操作,代价是要实现一整套文件系统接口,而不是注册一个过滤器。

   它的工作方式是**代理,不是搬运**:mount 只发生一次(记住几个目录的位置,底层文件系统必须已挂好),之后不再 mount 任何东西、不碰盘。打开时对真实文件做一次普通打开,把底层的 `struct file` 装进自己的 file 里;读写、mmap 全部转调那个真实文件(6.12 `fs/overlayfs/file.c`):

   ```
   L144  ovl_open → L27 ovl_open_realfile:对下层 / 上层的真实文件做普通打开,得到 ext4 的 struct file
   L171  file->private_data = realfile                         ← overlayfs 的 file 肚子里装着 ext4 的 file
   L267  ovl_read_iter → backing_file_read_iter(realfile, …)
         → fs/backing-file.c L183 vfs_iter_read(realfile, …)   ← 就是调 ext4 的 read_iter
   L418  ovl_mmap → backing_file_mmap(realfile, …) → L342 call_mmap(realfile)   ← mmap 也映射 ext4 的文件
   ```

   于是 page cache 的页挂在 **ext4 的 inode** 上,不在 overlayfs 的 inode 上:走 `/merged` 和走 `/lower` 的两个进程共享同一份页 —— C12·同文件多开 的要求,打开实例可以很多,对象只有一个,缓存跟着对象走。挂在 overlayfs 自己的 inode 上就会同一文件两份页、改了互不知道。Docker 一百个容器共享同一个基础镜像层,底下的文件在 page cache 里只有一份,也是这个原因。

   **套娃有上限,上限本身就是论据**。overlayfs 可以叠在 overlayfs 上,但 `include/linux/fs.h` L275 定了 `FILESYSTEM_MAX_STACK_DEPTH 2`:挂载时取下层里最深的 `s_stack_depth` 加一(`fs/overlayfs/super.c` L1126-1134),超过 2 就拒绝,报 "maximum fs stacking depth exceeded" —— ext4 是 0,叠一层是 1,再叠是 2,第三层不行。原因正是"① 是函数调用链":每套一层,`read` 就多一个嵌套的 `read_iter` 调用帧,全压在同一个 16 KB 的内核栈上(x86-64 `THREAD_SIZE` = 4 页),每层还各有自己的锁要保证嵌套顺序。NT 没有这个限制:过滤驱动叠一层只是 IRP 多一个栈位,分发例程调完就返回,挂起的请求不占任何线程的栈,十几层过滤驱动叠在一起是常态。同一件事,一边受内核栈限制只能两层,一边只受包里栈位数量限制 —— "包 vs 函数调用"的差别在这里变成一个具体数字。不管套几层,页始终挂在最底下那个真实 inode 上:每层 overlay 手里都是下一层的 file 对象,最后落到同一个叶子。
2. **完成怎么通知**:任何一层都能 `IoMarkIrpPending` 后返回,I/O 管理器事后把完成送回去(APC 或完成包)。完成模型对 NT 是零成本的,因为每个请求本来就是一个能放下再捡起来的东西。

#### §4.6.1 两个常见误解:包 ≠ 并行,函数调用 ≠ 锁

容易把"包能排队"读成"包带来多线程并行、函数调用要加锁所以并发上不去"。两点都不成立:

- **函数调用不等于加锁**。Linux 的读路径没有全局锁:一百个进程在一百个核上同时进 `read_iter`,各走各的;XArray 查找用 RCU,只有碰同一个页才锁那一个页,写才拿 inode 的 `i_rwsem`;块层每核一个硬件队列、每队列一把锁(Deep §3.2)。"一把锁浪费所有核"的全局 `queue_lock` 是 blk-mq 之前的事,2013 ~ 2019 年拆掉了(Origin §4)。Linux 的并行度不是被函数调用限制的。
- **NT 的 IRP 分发也是函数调用**。`IoCallDriver` 就是在发起线程里调下一层的分发例程,一层层调下去。包没有让"处理"变成多线程;它让"处理"可以在任何一层停下来、返回到调用者、之后在中断上下文或别的线程里继续。**多线程不是包带来的,可停才是。**

要分开两个词:**并行**(多少个核同时在跑)和**在飞**(一个线程手里同时挂着多少个未完成的请求)。两边都能把核用满;差别在在飞数和固定开销:

| | Linux ①② 函数调用 | NT IRP 包 |
|---|---|---|
| 多核并行(C5·多核并发) | 不受限,锁按对象分 | 不受限 |
| 一个线程的在飞数(C2·设备慢且异步) | 1;要更多就得 io_uring 三级拼接或多线程 | 任意,发完就返回 |
| 每个请求的固定开销 | 几乎没有 | 分配 + 走栈位 + APC,所以 Fast I/O 是必需品 |
| 阻塞兜底 | io-wq 线程(Deep §4.2.3) | NTFS 把不能立即完成又不能等的 IRP 交给系统工作线程(Windows Internals 所述的 posting) |
| 吞吐上限 | 盘(时间线 85% 在设备) | 盘 |

函数调用链的代价在"占住线程",包的代价在"每次都付固定开销";吞吐最后都卡在盘上,两边一样。

#### §4.6.2 现实版:数据库在 Linux 上怎么拿到在飞数

io_uring 之前,想同时等几百个盘上的页,Linux 上的数据库只有一条真异步的路 —— 先放弃 page cache。InnoDB(MySQL 5.5 起,2010)的配方是三件事叠起来:

| 做法 | 解决什么 | 对应 Deep §4.4 的候选 |
|---|---|---|
| `innodb_flush_method = O_DIRECT` | 自己有 buffer pool,不要内核再缓存一份(C10·内存装不下 的双份浪费);自己控制写顺序(C7·跨块不原子:doublewrite 与 redo 的先后,Why 阶段 R5 展开) | 候选 C 的温和版 |
| `innodb_use_native_aio = ON`,走 `io_submit` | `O_DIRECT` 的 bio 自带回调(Deep §4.2.4),所以 2002 年的 AIO 对它是真异步:一个线程 `io_submit` 几百个读,发完就返回,在飞数任意 | 候选 B |
| `innodb_read_io_threads` / `innodb_write_io_threads`,默认各 4 | 不是替你读的,是调 `io_getevents` 收割完成、跑回调的;没有 libaio 的平台退回"模拟 AIO",那才是每线程自己 `pread` 的线程池 | 候选 D 的兜底 |

对照 PostgreSQL:2025 年之前一直是缓冲读 + 同步 `pread`,在飞数靠多进程堆,预读靠 `posix_fadvise` 给内核打提示 —— 候选 D + 候选 A 的混合;PostgreSQL 18(2025 年 9 月)才加异步 I/O 子系统,`io_method` 可选 `worker`(默认,进程池替你读)或 `io_uring`。两个数据库一个二十年前就走 `O_DIRECT` + AIO,一个到 2025 年才走到 io_uring:在 Linux 上"在飞数"一直是应用自己要想办法的事。

绕回 Windows:SQL Server 的配方和 InnoDB 一模一样 —— `FILE_FLAG_NO_BUFFERING` + 重叠 I/O + 完成端口,自己管缓冲池(§2.1)。区别是在 NT 上这就是默认路径,什么都不用放弃;在 Linux 上要放弃 page cache、依赖 libaio、再配收割线程。同一个应用、同一个需求,两边付的代价不同 —— 这是上表"在飞数"那一行的现实版。

### §4.7 底层从第一天就异步,顶层为什么晚了 45 年 —— 异步是守恒的

你的观察:硬件和内核本来就靠中断通信,中断就是事件;Linux 内核内部那条路(Deep §3)正是"造 bio 发出去、进程睡、盘 DMA 写页、MSI-X 中断、`bio_endio` 唤醒"。内核是事件驱动的,它只是没把事件交给进程。所以问题不是"软件为什么没做异步",是**"发出去到回来"这段空档被谁吸收了**。只有三种接法:

| 谁接 | 做法 | 代价 | 谁选了它 |
|---|---|---|---|
| 调度器 | 进程发完就睡,CPU 去跑别的进程;事件来了唤醒它 | 每个在飞请求占一个进程或线程 | Unix 1974 |
| 内核缓存 | 预读提前把事件发出去,进程只在真需要那页时才睡 | 只对有局部性的读有效(C9·速差+局部性) | 两边都选:page cache 与缓存管理器 |
| 应用 | 内核把完成事件交给进程,进程自己管缓冲区生命周期、状态机、取消、错误 | 编程模型复杂;缓冲区归属要重新定义 | VMS 1977、NT 1993、Linux 2019 |

Unix 选第一种,1974 年有四个很硬的理由:

1. **并发单位是进程,不是线程**。Unix 没有线程,`fork` 便宜,"一个进程一个在飞请求"是自然的;整个系统异步、每个进程同步,多道程序把两者接起来。NT 1989 年设计时线程已是一等公民、目标是服务器,要的是"一个线程多个在飞",第三种接法才划算。
2. **同步 `read` 删掉了一整类问题**。缓冲区在调用期间归内核、返回就归你;没有"返回之后内核还会写你的 buf"(§3.4 / Deep §4.3.1 第 2 条);没有完成通知、取消、乱序。这些在 Unix 里只能用信号表达,而信号是最糟的事件机制 —— POSIX AIO(1993)用信号或线程送完成,没人愿意用。
3. **几十年里阻塞的代价看不见**。盘毫秒级,一次上下文切换微秒级,千分之一。只要在飞数不需要大于 1,阻塞比通知便宜:阻塞是数据到了切一次,通知是切一次再多一次系统调用(C3·特权态门槛)。单请求程序阻塞永远更省。
4. **缓存已经把大部分异步收益给了文件**。预读在内核里就是异步发请求,命中的读本来不等盘;用户程序没有异步 API,但 90% 的读已经享受了异步。缺的只是未命中时**用户可见**的完成。

第三种接法变得划算,要等两个条件同时成立:在飞数必须大于每线程 1(C10k,1999;socket 先得到就绪模型,因为它的缓冲区本来就在内核里),以及盘的延迟逼近切换的代价(NVMe 10 μs 对 1 ~ 2 μs,2011 年后);Spectre(2018)抬高系统调用价格是扳机。这是 Deep §4.3 "方向必然、年份偶然"背后的机制。NT 早做不是看得远,是它的并发单位(线程)和血统(VMS)正好让第三种接法从第一天就便宜。

#### §4.7.1 你的总结,加两个节点

你的话:**"一开始一个进程一个 I/O,阻塞了也只是那个进程阻塞,其他进程没影响,所以没必要做成异步;后来服务器要求并发高了,进程代价变得可观,才出现 epoll 这种模型。"** 骨架就是这个。补两个节点,因为"epoll 这种模型"比 epoll 早二十年:

| 年份 | 一个进程对多少 I/O | 发生了什么 |
|---|---|---|
| 1974 | 一个进程一个 I/O | 阻塞只伤自己,调度器吸收异步 |
| 1983 | 一个进程看多个 fd | BSD `select`:就绪模型第一次出现,为终端和 socket;每次把全部 fd 传进去问一遍,O(登记数) |
| 1995 | 一个线程一个 I/O | pthreads:把进程模型缩小一号继续用;Apache 的 prefork / worker 就是这条路 |
| 1999 | 两条路同时撞墙 | C10k:`select` 的 O(n),和每连接一线程的内存(栈 + 内核结构)与切换次数,同时变得可观 |
| 2002 | 一个进程看上万个 fd | epoll:就绪模型的可扩展实现,O(就绪数)。**模型没变,变的是复杂度** |
| 2019 | 一个线程多个在飞 | io_uring:完成模型,磁盘文件第一次能异步。**这才是"应用接住异步"那一步** |

两个精确的点:

- **epoll 没有改模型**。进程还是睡在 `epoll_wait` 里,异步还是调度器在吸收,只是一次睡觉等很多个 fd。真正让应用自己接住异步的,Linux 上是 2019 年的 io_uring。
- **socket 先得到解法,是因为它的就绪状态是现成的**:数据本来就在内核的接收缓冲区里,"有没有数据"有意义;磁盘文件没有这个状态(数据永远在盘上),所以要等完成模型 —— 这是 Deep §4.2.1 `file_can_poll` 那两行 `EPERM` 的根子。

#### §4.7.2 一句话:并发需求驱动 OS 一步步接近硬件的真异步

这是你的话,可以当这一章的结论。两个脚注让它更准:

1. **驱动力有两个**。并发需求(每线程在飞数要大于 1)推动了 1983 ~ 2002 那几步,就绪模型就够;最后一步走到完成模型,是另一个力推的 —— 盘快到和 CPU 同量级、Spectre 把系统调用抬价,阻塞的代价第一次可测。**并发决定方向,代价比决定年份**(Deep §4.3)。
2. **"接近硬件的真异步"是形状上的收敛**。NVMe 给内核的接口是一对提交 / 完成队列加门铃;io_uring 给用户态的接口也是一对提交 / 完成队列加门铃(Deep §4.2.2),IoRing 同样;SPDK 是极限,用户态直接摸 NVMe 的队列。每一步都在拆掉一层吸收异步的中介:

| 步 | 谁吸收空档 | 用户看到的形状 |
|---|---|---|
| 1974 阻塞 `read` | 调度器 | 函数调用 |
| 1983 `select`、2002 epoll | 调度器,但一次睡等很多个 | 就绪列表 |
| 2019 io_uring、2021 IoRing | 应用 | 一对环,和硬件同形 |
| SPDK | 应用,连内核都不在中间 | 硬件自己的环 |

---

## §5 对照三:缓存管理器对 page cache

### §5.1 对比维度

缓存按什么索引;谁负责把数据搬进来。

### §5.2 NT 的核心做法

NT 的**缓存管理器(Cc)** 不自己管页,它是**内存管理器(Mm)** 的前台:

1. 文件系统打开文件时调 `CcInitializeCacheMap`,为这个文件对象建私有缓存映射(per handle,记录预读历史)和共享缓存映射(per 文件)。
2. 缓存的虚拟地址空间被切成 **256 KB 的块**,每块一个 **VACB**(Virtual Address Control Block),记录"这块当前映射的是哪个文件的哪 256 KB"。一个视图定长,一次映射不跨两个视图,视图按 LRU 回收(微软 Probert 讲义 / Windows Internals)。
3. 缓存命中的读:Fast I/O → `FsRtlCopyRead` → `CcCopyRead(文件对象, 偏移, 长度)` → 找到(或建立)覆盖这段偏移的 VACB → **从视图的虚拟地址 memcpy 到用户 buf**。
4. 页不在物理内存:memcpy 时**缺页** → Mm 查 section 对象的原型 PTE → Mm 向文件系统发一个带 `IRP_PAGING_IO | IRP_NOCACHE` 的读 IRP → NTFS → 卷 → 盘 → 页填好 → memcpy 继续。文件系统收到的 paging I/O 和普通读走同一个 `IRP_MJ_READ` 入口,只是标志不同,所以 NTFS 必须能区分"用户的读"和"Mm 替缓存发的读",否则会递归。
5. **预读**:每个打开实例的私有缓存映射记录**最近两次读的位置**,连续三次读才建立模式,能外推步长(包括反向);`FILE_FLAG_SEQUENTIAL_SCAN` 下不记历史、直接顺序预读且预读量翻倍、始终领先调用者一个读的距离;`FILE_FLAG_RANDOM_ACCESS` 关预读。粒度 64 KB 不是缓存管理器的默认(它默认一页),是 NTFS / FAT 自己调 `CcSetReadAheadGranularity` 设的(fastfat 样例 `READ_AHEAD_GRANULARITY = 0x10000`)。出处:Windows Internals 6e Part 2 第 11 章。
6. **延迟写**:lazy writer 每秒跑一次,把最近没刷的脏页中的八分之一排进写队列;临时文件默认不刷(微软性能调优文档)。
7. **绕过**:`FILE_FLAG_NO_BUFFERING`,要求偏移和长度按扇区对齐 —— 和 `O_DIRECT` 一样,C4·定长块 的直接暴露。
8. **mmap**:`CreateFileMapping` / `MapViewOfFile` 用的是同一个 section 对象,和缓存共享物理页 —— 和 Linux 的 `filemap_fault` 与 `filemap_read` 共享 folio 同构。

### §5.3 Linux 的对应物

Deep §2 讲过的:`inode->i_mapping` 的 XArray,键是页号;`filemap_get_pages` 三级尝试(批量查、同步预读、单页保底);预读窗口 4 → 16 → 32 页;脏页由比例阈值加 30 s 过期触发回写;`O_DIRECT` 绕过;mmap 和 read 共享 folio。文件系统**显式**查 XArray、**显式**造 bio(`ext4_mpage_readpages`),没有缺页参与(mmap 路径除外)。

### §5.4 在五元组上的差异

| | Linux page cache | NT 缓存管理器 + 内存管理器 |
|---|---|---|
| 索引结构 | XArray,键 = (inode, 页号) | 内核虚拟地址 + VACB(256 KB 视图),底下是 section 的原型 PTE |
| 谁把数据搬进来 | 文件系统显式发 bio | memcpy 缺页 → Mm 发 paging I/O → 文件系统 |
| 命中路径 | `filemap_get_read_batch` 查表 → `copy_folio_to_iter` | `CcCopyRead` 找 VACB → memcpy |
| 预读 | 窗口翻倍 4 → 16 → 32,`IOCB_NOWAIT` 时可跳过 | 私有缓存映射记最近两次读,三次成模式;顺序扫描标志下翻倍;粒度 64 KB 由文件系统设 |
| 回写 | 比例阈值 + 过期时间(`page-writeback.c`) | lazy writer 每秒 1/8 |
| 与 mmap | 同一 folio | 同一 section |
| 绕过 | `O_DIRECT`,对齐要求 | `FILE_FLAG_NO_BUFFERING`,对齐要求 |
| 处理 C9·速差+局部性 | 预读 + 保留 | 预读 + 保留 |
| 处理 C10·内存装不下 | LRU 淘汰 + 延迟回写 | 视图 LRU 回收 + 页由 Mm 淘汰 + lazy writer |
| 代价 | 查表成本;文件系统要自己造 bio | 32 位时代缓存受虚拟地址空间限制,VACB 要回收;每次缺页多走一次 Mm;文件系统要分辨 paging I/O 防递归 |

### §5.5 为什么 NT 这么选

NT 的内存管理器从第一天就有 **section 对象**(映射可执行文件、共享内存都靠它),于是"把文件的一段映射进地址空间、缺页时从文件拉"这套机制已经存在;缓存管理器只要把文件映射进内核地址空间再 memcpy,就复用了整套分页器,内核里只有一份"从文件取页"的逻辑。代价是缓存走虚拟地址:32 位时代内核地址空间紧张,所以视图只有 256 KB 且要 LRU 回收;每次缺页都多经过一次 Mm。

Linux 的 page cache 1995 年底(1.3.50)就有,read 与 mmap 从 2.0(1996)起共用同一份页,write 到 2.3.7(1999 年 6 月,Ingo Molnar 完成 page cache 与 buffer cache 的统一)才全部走 page cache,从一开始就是显式索引;而且内核直接映射了全部物理内存,碰一个页不需要先建视图。两边各自用现成的东西,得到两种结构。

### §5.6 这个对比突出了什么

C9·速差+局部性 和 C10·内存装不下 把两边逼出了**完全相同的功能清单**:缓存、预读、延迟写、与 mmap 共享页、对齐的绕过通道。不同的只有索引机制,而那是由各自内核"先有什么"决定的。缓存这一层上,约束决定功能,血统决定结构。

---

## §6 下面四层:到了块层以下两边趋同

### §6.1 ② NTFS 与 `$LogFile` 对 ext4 与 jbd2 —— C7·跨块不原子

NTFS 的 `$LogFile` 是写前日志:只记**元数据**(MFT、位图、目录),不记用户数据;每条记录带单调递增的 LSN,带 redo 和 undo 信息;文件分重启区(两份)和环形日志区,定期写检查点(Windows Internals 6e Part 2 第 12 章:每 5 秒写一条检查点记录),恢复时从检查点开始分析。和 Why 阶段 R5·活过断电 展开的 WAL 五步、环形日志 head / tail 完全同构;对应 ext4 的 `data=writeback`,比默认的 `data=ordered` 少一个"数据先于元数据落盘"的保证。差异在**日志什么**(NTFS 元数据,ext4 可选),不在**要不要日志**。

### §6.2 ③ 存储栈:卷管理器 / 分区管理器 / 磁盘类驱动 / storport 对 blk-mq —— C1·厂商定接口 + C5·多核并发 + C6·介质形状相反

NT 的块层是一串驱动:`volmgr`(卷)→ `partmgr`(分区)→ `disk.sys`(磁盘类驱动,把 IRP 变成 SRB,里面是 SCSI 的 CDB)→ `storport.sys`(端口驱动,管队列、DMA、中断)→ miniport(具体控制器)。**窄腰是 SCSI**:NVMe 盘的 miniport `stornvme.sys`(Windows 8.1 起)把 SCSI 命令翻译成 NVMe 命令,微软文档给了对照表(Read 16 → NVMe Read,Unmap → Dataset Management),1903 起符合 SCSI Translation Reference 1.5。Linux 走过同一段:SATA 盘曾经通过 libata 伪装成 SCSI;但 2011 年 NVMe 驱动直接挂在块层上,2014 年 blk-mq 为它重做了块层(Origin §4),没有翻译层。Windows 到 **Server 2025** 才加原生 NVMe 驱动 `nvmedisk.sys` 绕开 SCSI 磁盘层(微软公开;客户端通过注册表启用属于非官方做法)。多队列:Linux 每核一个硬件队列上下文显式可见(Deep §3.3);storport 的队列到 CPU 映射微软没有公开(stornvme 闭源);公开的只有 Storport 的性能配置项 —— 完成 DPC 重定向回发起 I/O 的核、MSI-X 消息范围、NUMA 亲和,以及每个请求可选"最优 MSI-X 消息"。

### §6.3 ④ `stornvme.sys` 对 `drivers/nvme` —— C1·厂商定接口

两边都是 NVMe 规范的实现:每核一对提交 / 完成队列、门铃寄存器、MSI-X 中断、命令 ID 回传。形状由规范规定,没有设计空间;差别只在上面接的是 SRB 还是 request。

### §6.4 ⑤ 硬件

同一块盘。

### §6.5 结论

从 ② 往下,两边的差异只剩"NT 多一层 SCSI 翻译、晚十年才去掉"。硬件约束 C1·厂商定接口 / C4·定长块 / C6·介质形状相反 / C7·跨块不原子 两边完全一样,解法也一样:日志、分层驱动、每核一队列、命令 ID。**约束一样的地方,形状就一样**;上三层不一样,是因为那里多了一条约束之外的东西:血统。

---

## §7 约束回扣

| 约束 | Linux 的化解 | NT 的化解 | 同 / 异 | 异的来源 |
|---|---|---|---|---|
| C2·设备慢且异步 | 块层起用 bio 异步;① 靠三级拼接 | ① 起 IRP 可 pending | 异 | VMS vs Unix 的接口语义(C11) |
| C3·特权态门槛 | epoll 2 次 → io_uring 0 ~ 1 次 | IOCP 2 次 → IoRing 0 ~ 1 次 | 同(晚 2 年) | — |
| C5·多核并发 | epoll 就绪链表;线程模型留给用户态 | 完成端口 + 并发值 + LIFO | 异 | NT 线程贵、无 fork |
| C9·速差+局部性 | page cache + 预读 + `IOCB_NOWAIT` 快路径 | 缓存管理器 + 预读 + Fast I/O 快路径 | 同形 | — |
| C10·内存装不下 | 比例阈值回写 + LRU | lazy writer + 视图 LRU + Mm 淘汰 | 同 | — |
| C8·流 vs 块 | XArray (inode, index) | 256 KB 视图 + section | 功能同、结构异 | 各自先有什么(XArray vs section) |
| C11·POSIX接口冻结 | 冻住"read 返回即有数据" | 冻住"发出去再通知" | 各冻各的 | 血统 |
| C12·同文件多开 | `file` / `inode` | `FILE_OBJECT` / FCB | 同 | — |
| C1·厂商定接口 | 块层 M+N;nvme 原生 | 类 / 端口 / miniport;SCSI 窄腰,2025 才原生 | 同形,异在窄腰 | NT 驱动在树外,二进制合同要更保守 |
| C4·定长块 | `O_DIRECT` 对齐 | `NO_BUFFERING` 对齐 | 同 | — |
| C6·介质形状相反 | 调度器可换;NVMe 用 none | storport 队列策略(stornvme 的队列映射未公开) | 同向 | — |
| C7·跨块不原子 | jbd2,三档 | `$LogFile`,只记元数据 | 同 | — |

读法:**同**的那些行,约束在两边一样重,解法也一样 —— 它们是"必须这么设计"的部分;**异**的那些行,全部能追到两条血统(VMS / Unix)或一个组织形态(驱动在树外 / 树内),它们是"Linux 碰巧这么设计"的部分。

---

## §8 呼应你的问题

你问的是"VFS、驱动层、块设备层各自怎么设计,以及为什么必须这么设计"。对照给了"必须"二字一个可检验的定义:**另一套从头设计的系统,在同一条约束下是不是也长成了这样**。

- **必须的**(两边一样):块层以下的全部形状;缓存 + 预读 + 延迟写 + 绕过通道这套功能;写前日志;打开实例与对象分开;一个完成模型(两边都走到了,只是年份差 25 年);一条快路径。
- **不必须的**(两边不同):包的边界画在 ① 之上还是 ②③ 之间;就绪优先还是完成优先;缓存按索引结构还是按虚拟地址;线程节流在内核还是用户态。这些都能追到 1974 年的 `read` 语义和 1977 年的 `$QIO` 语义。

到这里,灵魂问题闭环到 **98%**。剩下 2% 是方法论层面的:怎么把"约束 → 必然,血统 → 偶然"这个判别法带到下一个你要拆的系统上 —— 留给收束那一份。

---

## §9 资料来源与待核

**Windows 侧出处**(正文引用的):

- I/O 完成端口:[I/O Completion Ports(learn.microsoft.com)](https://learn.microsoft.com/en-us/windows/win32/fileio/i-o-completion-ports)、[CreateIoCompletionPort](https://learn.microsoft.com/en-us/windows/win32/api/ioapiset/nf-ioapiset-createiocompletionport)
- Fast I/O:[FAST_IO_DISPATCH](https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/ns-wdm-_fast_io_dispatch)、[FsRtlCopyRead](https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/nf-ntifs-_fsrtl_advanced_fcb_header-fsrtlcopyread)、[Registering Fast I/O Dispatch Routines](https://learn.microsoft.com/en-us/windows-hardware/drivers/ifs/registering-fast-i-o-dispatch-routines)
- IRP 处理:[Different ways of handling IRPs - Cheat sheet](https://learn.microsoft.com/en-us/windows-hardware/drivers/kernel/different-ways-of-handling-irps-cheat-sheet)、[IoMarkIrpPending](https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-iomarkirppending)
- 缓存:[File Caching(Win32)](https://learn.microsoft.com/en-us/windows/win32/fileio/file-caching)、[Cache and Memory Manager(性能调优)](https://learn.microsoft.com/en-us/windows-server/administration/performance-tuning/subsystem/cache-memory-management/)、[Probert 讲义 Cache Manager(东京大学镜像)](https://www.i.u-tokyo.ac.jp/edu/training/ss/lecture/new-documents/Lectures/15-CacheManager/CacheManager.pdf)、Windows Internals 6th ed. ch. 11(Cache Manager)
- IoRing:[CreateIoRing](https://learn.microsoft.com/en-us/windows/win32/api/ioringapi/nf-ioringapi-createioring)、[IORING_OP_CODE](https://learn.microsoft.com/en-us/windows/win32/api/ntioring_x/ne-ntioring_x-ioring_op_code)、[I/O Rings – When One I/O Operation Is Not Enough(windows-internals.com)](https://windows-internals.com/i-o-rings-when-one-i-o-operation-is-not-enough/)、[One Year to I/O Ring: What Changed?](https://windows-internals.com/one-year-to-i-o-ring-what-changed/)
- 存储栈:[NVMe Features Supported by StorNVMe](https://learn.microsoft.com/en-us/windows-hardware/drivers/storage/nvme-features-supported-by-stornvme)、[StorNVMe SCSI Translation Support](https://github.com/MicrosoftDocs/windows-driver-docs/blob/staging/windows-driver-docs-pr/storage/stornvme-scsi-translation-support.md)
- `\Device\Afd`:[notgull: \Device\Afd, or, the Deal with the Devil that makes async Rust work on Windows](https://notgull.net/device-afd/)、[Len Holgate: Adventures with \Device\Afd](https://lenholgate.com/blog/2023/04/adventures-with-afd.html)、mio 文档
- NTFS 日志:[HPI 讲义 NTFS Recovery](https://osm.hpi.de/bsArch/2005/Unit08/04_NTFS-Recovery.pdf)、[NTFS LogFile Parser(CodeProject)](https://www.codeproject.com/Tips/1072219/NTFS-LogFile-Parser)

**待核**(并入收尾清单):

1. IOCP 首次出现于 NT 3.5(1994)—— 收尾已核:NT 3.5(1994-09-21 发布)引入,Banga 等人的 USENIX 论文与 NT 3.5 条目均写明;仍没有微软一手页面
2. IoRing 22H2 加写 / flush —— 收尾已核:22H2(22621)起支持 `IORING_OP_WRITE` / `IORING_OP_FLUSH`(环版本 3),依据 Yarden Shafir 2022-04《One Year to I/O Ring》;Learn 迄今没有 `BuildIoRingWriteFile` 的参考页,不要引"最低支持客户端"行
3. NTFS 检查点约 5 秒 —— 收尾已核:Windows Internals 6e Part 2 第 12 章原文 "once every 5 seconds";微软文档未给间隔
4. storport 对 NVMe 多队列的 CPU 映射细节 —— 收尾仍无法核实:stornvme 闭源;公开的只有 Storport 的 `PERF_CONFIGURATION_DATA`(DPC 重定向回发起核、MSI-X 消息范围、NUMA 亲和)与 `STARTIO_PERFORMANCE_PARAMETERS.MessageNumber`(每个请求选最优 MSI-X 消息)
5. 缓存管理器预读窗口算法 —— 收尾已核,结果写进 §5.1 第 5 步与 §5.3 表
6. Linux page cache 与 mmap 统一的年份 —— 收尾已核:1.3.50(1995-12)引入 page cache,2.0 起 read / mmap 共用,2.3.7(1999-06)write 也走 page cache,2.4.10(2001-09)块设备搬到 page cache 上;出处见 07-synthesis 待核汇总 #16
7. NTFS 对盘上单段连续的非缓存读是复用主 IRP 填下一栈位,还是也造关联 IRP —— 收尾部分核实:微软 FastFAT 样例 `deviosup.c` 单 run 走 `FatSingleAsync`,在原 IRP 上填下一栈位直接 `IoCallDriver`;多 run 才走 `FatMultipleAsync` 逐段 `IoMakeAssociatedIrp` + `IoBuildPartialMdl`。NTFS 闭源,按 WDK 规则推定相同

---

## 修订记录

| 时间 | 修订摘要 | 触发原因 |
|---|---|---|
| 2026-10-23 | 初稿:速查 + §0 三件事(异步在哪层表达 / 同一条快路径 / 缓存索引)+ §1 概览 SVG + §2 NT I/O 栈动机简表 + §3 接口层(IOCP / IoRing 对 epoll / io_uring,四列五元组表,`\Device\Afd` 反向证据)+ §4 I/O 管理器与 IRP 对 VFS 与 bio(IRP 五步、Fast I/O、三件货物对照、包边界结论)+ §5 缓存管理器对 page cache(VACB 256 KB、缺页拉页、lazy writer 1/8、十行对照表)+ §6 下四层趋同(`$LogFile`、SCSI 窄腰与 2025 原生 NVMe、stornvme)+ §7 回扣(12 条同 / 异 + 异的来源)+ §8 呼应 98% + §9 出处与 6 条待核 | 对齐收敛:对象 Windows IOCP → 比到底 → 压上面三层 → 无追加 |
| 2026-10-23 | §4.2 新增 §4.2.1「IRP 不是块层的包」:信封四部分表(头 MDL / 栈位 1 文件偏移 / 栈位 2 卷偏移 / 栈位 3~N)、栈位数由 StackSize 定、关联 IRP 对两 extent 两 bio、MDL 对 bio_vec、缓存路径上 Mm 的 paging IRP 也是晚造;把"包从 ① 起"精确为"信封从 ① 起,扇区和 Linux 一样晚";待核 +1(NTFS 单段是否复用主 IRP) | 用户追问:Windows 这么早就把块层的包造好了?怎么做到的? |
| 2026-10-23 | §4.6 补"请求做成对象养出的两个特性"(谁能看到每个请求 / 完成怎么通知);新增 §4.6.1「包 ≠ 并行,函数调用 ≠ 锁」:Linux 读路径无全局锁(RCU / 页锁 / 每核队列)、IoCallDriver 也是函数调用、并行 vs 在飞两个词、五行对照表(并行 / 在飞 / 固定开销 / 阻塞兜底 / 吞吐上限) | 用户答反问:"提早封包→可排队→多线程并行→异步→吞吐大;Linux 函数调用要加锁并发上不去"—— 对一半(可挂起 = 异步),纠一半(并行、锁) |
| 2026-10-23 | 新增 §4.6.2「数据库在 Linux 上怎么拿到在飞数」:InnoDB 三件事表(O_DIRECT / native AIO io_submit / 4+4 收割线程,各对 Deep §4.4 候选)、PostgreSQL 对照(2025 前缓冲同步 + fadvise;PG 18 io_method worker / io_uring)、SQL Server 同配方在 NT 是默认路径 | 用户答反问:"自己用 O_DIRECT 访问磁盘,然后自己维护访问的线程"—— 对,补 O_DIRECT 顺带打开 AIO 真异步这一半 |
| 2026-10-23 | 新增 §4.7「底层从第一天就异步,顶层为什么晚了 45 年」:异步守恒三种接法表(调度器 / 内核缓存 / 应用)、Unix 1974 选调度器的四个理由(进程是并发单位、同步 read 删掉一类问题、阻塞代价看不见、缓存已给收益)、第三种接法划算的两个条件 + 扳机 | 用户新视角:硬件与 OS 本就靠中断通信,从一开始就是异步的,软件晚这么多年必有原因 |
| 2026-10-23 | §4.7 下新增 §4.7.1「你的总结,加两个节点」:记入用户总结(进程模型决定 → 阻塞局部 → 后来并发高才有 epoll);六行时间线(1974 / 1983 select / 1995 pthreads / 1999 C10k / 2002 epoll / 2019 io_uring);两个精确点(epoll 没改模型;socket 先得解是因为就绪状态现成) | 用户总结自己的理解:"进程模型决定的,一个进程一个 io … 后来才出现的 epoll 这种模型" |
| 2026-10-23 | 新增 §4.7.2,标题用用户原话「并发需求驱动 OS 一步步接近硬件的真异步」;两个脚注(驱动力有两个:并发定方向、代价比定年份;形状收敛:NVMe 队列 ↔ io_uring / IoRing 环 ↔ SPDK)+ 四步拆中介表 | 用户一句话总结 |
| 2026-10-23 | §3.2 第 6 步后补「为什么一个队列两头两种顺序」:线程 LIFO = 热(缓存 / TLB)+ 压活跃线程数,对 Deep 的 complete_request_remote 与 task_work;包 FIFO = 公平 / 有界等待,对 mq-deadline 双索引 | 反问「线程 LIFO、包 FIFO 各保什么」用户答「TLB 缓存 / 吞吐量」—— 前半对,后半改为公平 |
| 2026-10-23 | §4.6 特性 1 下补 Linux 的具体做法:`rw_verify_area` L560 → `security_file_permission` L470 → `fsnotify_file_area_perm` L474(fanotify FAN_ACCESS_PERM)→ 读后 `fsnotify_access` L573;为什么不能挂文件系统与块层之间(bio 无文件语义、命中不经块层);六行"钩子拿着什么"对照表 | 反问「Linux 上按访问检查挂哪、靠什么钩子、比 minifilter 少什么」用户答「文件系统与块层之间,靠回调;Windows 更靠前」—— 位置纠正,"少了包"落实 |
| 2026-10-23 | §4.6 特性 1 补 overlayfs 解释(叠加文件系统 / copy-up / Docker)与"代理不是搬运"(ovl_open L144 / realfile L171 / ovl_read_iter L267 → vfs_iter_read / ovl_mmap L418 → call_mmap);页挂 ext4 inode 的结论与 C12 的关系 | 用户两次追问 overlayfs 是什么、是不是"每次读 mount 下层取回再 mount 回 overlay 展示"—— 纠正为一次 mount + file 对象转调 |
| 2026-10-23 | §4.6 overlayfs 段补"套娃有上限":`FILESYSTEM_MAX_STACK_DEPTH 2`(fs.h L275;super.c L1126-1134 检查),原因是函数调用链压同一 16 KB 内核栈 + 锁序;NT 叠过滤驱动只加栈位无此限;页始终挂叶子 inode | 用户观察"套娃,下层还是 overlayfs 还能继续套" |
| 2026-10-23 | 收尾核实:§9 七条逐条标结果;§5.1 第 5 步预读算法按 Windows Internals 6e 改写(两次读历史 / 三次成模式 / 顺序扫描翻倍 / 64 KB 由文件系统设);§5.3 表、§6.1 检查点 5 秒出处、§4.2.1 单段 IRP 复用(FastFAT 样例)、page cache 统一年份(2.3.7,1999)同步修正 | 导出收尾统一核实 |
