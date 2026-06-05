# docker技术的来龙去脉 Atlas Progress

## 元数据
- **主题**: docker技术的来龙去脉
- **短名**: docker
- **工作目录**: atlas-output/docker-20260603/
- **创建时间**: 2026-06-03T06:46:35Z
- **上次更新**: 2026-06-05T15:17:22Z
- **当前阶段**: final-export(Synthesis 已封存;融合中:MD + HTML 暗色科技风;融合完成后终末 commit + push origin main)

## 灵魂问题(Discovery 收集)
> "容器到底是什么?它和虚拟机的根本区别在哪?当一个容器真正跑起来的那一刻,Linux 内核里到底发生了什么 —— namespace、cgroups、镜像分层各自扮演什么角色?"

（用户重心选了 A 本质派：从"它根本不是虚拟机"切入，逐个钉死 namespace / cgroups / 镜像分层，搞懂一个容器跑起来时内核里到底发生了什么。起头从本质，收尾到演化。）

## 进度状态机
- [x] 0. Discovery
- [x] 1. What
- [x] 2. Why（含约束清单建立）
- [x] 3. How
- [x] 4. Origin
- [x] 5. 分水岭决定（用户选「继续深钻」→ Deep）
- [x] 6. Deep
- [x] 7. Comparison（可选）
- [x] 8. Synthesis
- [x] 9. 导出格式询问（用户直接指定 MD+HTML）
- [ ] 10. 融合输出

## 约束清单（Why 阶段建立，后续阶段引用；收编史 7→4→3 均由用户裁定，C1~C3 自此真冻结）
| # | 主约束（压力） | 来源 | 不可再分性（七桩子事实一桩不丢） |
|---|--------------|------|----------------------------------|
| C1 | 硬件必须高效用于用户计算（榨干硬件）——三连锁：①闲置是浪费→必须共享 ②共享默认互害→必须隔离 ③隔离太贵也是浪费→隔离必须便宜 | 经济现实 + Unix 语义 + OS 结构 | ①经济账（利用率 5~15%，账单物理，幕二）②共享视图+资源不设防（40 年全局命名生态，幕一）③完整 OS 重资产（GB/分钟/内存税，幕三）；③咬回①成闭环 |
| C2 ★ | 环境必须跟应用走（用户钦点核心） | FHS/动态链接生态 | 环境长在机器上（应用=二进制+libs+配置散落全局路径，幕四+幕一依赖打架）；单独只逼出 AMI，叠加 C1③ 才坍缩成容器镜像 |
| C3 | 发布必须去人化，且机器可验真 | 规模浪潮 + 存储语义 | ①人力不随规模扩展（O(台数×环境×频率)，人是常数，幕五+暗线）②字节无身份（文件名≠内容，验证穷尽到反编译，幕五） |

口诀速记：C1 榨干硬件→必须共享→必须隔离→隔离必须便宜 / C2★ 环境是机器属性→必须打包跟应用走 / C3 人不能扩容+文件名≠内容→机器接管+哈希验真

逼出映射：C1→namespace+cgroups 墙+共享内核不带厂房 / C2★→镜像+overlayfs / C3→API 化流水线+sha256 内容寻址（三大支柱：隔离/打包/运维）

## 用户疑问/追问审计

### What 阶段
- 第 1 次产物迭代:用户答对 `ps` 方向性探针(宿主看得到容器进程 / 容器看不到宿主)→ 提炼"单向玻璃 + 不对称是容器 vs VM 试金石"洞见 → 已 patch 文件:新增 §2.1「一个一眼分辨容器还是 VM 的小实验」
- 第 2 次新视角:用户自己提出心法"Docker = 砌墙 + 凿洞(4 堵墙 + 2 个洞,可能数错)"→ 精确化为「2 类墙(namespace 6 窗 + cgroups)+ 1 块地板(overlayfs)+ 2 个洞(veth 凿 net 墙 / volume 凿 mnt 墙)」,点出"每个洞都凿在某扇 ns 墙上"的对偶 → 已 patch 文件:新增 §0「心法:砌墙 + 凿洞」+ 第 7 张图 01-walls-and-holes.svg
- 第 3 次新视角/追问:用户继续延伸类比(cgroup=电表/水表✓;overlayfs=日历?;"Docker 借鉴现实生活")→ 评估:cgroup=电表满分(补 CPU/IO 限速 vs 内存 OOM kill);overlayfs≠日历(日历只接住"累积写入",漏分层/复用/CoW),改为"一摞透明胶片";meta 洞见肯定+分层(字面借词 container/image/registry/volume/port/bridge/mount vs 工程传统 ns/cgroups/CoW)+"类比是脚手架"告诫 → 已 patch:§4.4 加"透明胶片"类比 + 新增 §0.1 旁注「Docker 从生活借词」
- 第 4 次新视角:用户自创"集装箱=车间(工人+机器=应用+依赖),水电煤气接口标准化→房间可搬到别的大楼"=独立推导出可移植性/OCI 论点 → 肯定+精确化:集装箱真正创新=接口标准化(=OCI 存在理由);关键边界=可移植有前提(需兼容内核 ABI),Linux 间随便搬但 Win/Mac 需 Docker Desktop 偷塞 Linux VM;回扣灵魂问题(共用内核→既轻又绑定内核家族,是硬币两面) → 已 patch:新增 §3.1「第二个类比:集装箱→可移植」+ 第 8 张图 01-shipping-container-portability.svg
- 第 5 次需求:用户要"按这种类比生成图,尽量有生活也有技术细节" → 做了「生活↔技术 对照图册」(左生活/右真实技术参数),用户追加"要"后补满 6 张:①01-life-tech-overview(大楼↔主机)②01-life-tech-namespace(单向玻璃房↔6类ns)③01-life-tech-cgroups(三块表↔cpu.max/memory.max/io.max+OOM)④01-life-tech-overlayfs(透明胶片↔lowerdir/upperdir/CoW/whiteout)⑤01-life-tech-network(管道井+市政↔veth/bridge/iptables MASQUERADE)⑥01-life-tech-pipeline(物业接力↔dockerd/containerd/runc/shim) → 已 patch:§3.2「生活↔技术 对照图册」含全 6 张。What 阶段 pics 累计 14 张图。
- 第 6 次产物迭代:揭晓 512MB/64GB 探针(答案=64GB,因 /proc/meminfo 未 namespace 化;两道墙独立;JVM/Node OOM 事故;治法 /sys/fs/cgroup/memory.max + UseContainerSupport + LXCFS;水位计 vs 水表类比)→ 已 patch:新增 §4.5「墙是漏的:512MB 容器自报 64GB」,作为通往 Why 的桥(墙有缝/有代价/有取舍)
- 第 7 次新视角(2026-06-04,通读草稿期间):用户提出"VM 搬车间要重建整个厂房 vs Docker 只搬车间、标准接口一插就跑"的生活化对比 → 精确化:藏着「部署/搬运单位」概念(VM 单位=厂房/整套 OS,容器单位=车间/app+依赖),快的根源="厂房不在行李里,在目的地等你"(=不带内核)→ 已 patch:§2 表格后新增「搬家故事」callout;补齐 01-what.md 修订记录表(7 行)

### Why 阶段
- 开场对齐(2026-06-04):用户选 A 痛点驱动;确认四幕剧本并贡献两段亲历 —— ①VMware 搭环境之痛(从 OS 开始搭,镜像大启动慢)入第三幕;②2009 年 30 万在线 IM 凌晨发布(几十台对称部署、2:00-6:00 窗口、md5 人工核对、反编译验功能、发现/回滚靠人)成第五幕压轴 → 捅出 C7(字节无身份)这条原四幕没有的约束;③补时代背景"web 大规模集群时代,人肉运维 100 台是极限"→ C6;④"13 年看到 docker 兴奋不亚于现在看到 LLM"收进尾声。约束清单立 C1~C7(7 条,动态决定非预设)。初稿 + 3 张 SVG(五幕总览/痛→约束映射/欺骗层次)已生成。
- 第 1 次新视角+产物迭代:用户答"只留一条"探针选 C5(环境跟应用走)并要求精简为 4 条 → 肯定其历史精确性(墙非 Docker 发明,镜像才是;引爆点是打包不是隔离)+ 精确化(C5 单独只逼出 AMI,心脏需要骨架)→ 约束清单收编 7→4:旧C3+C1+C2→新C1 合租互害 / 旧C4→C2 单位降级 / 旧C5→C3★ 环境随行(钦点核心) / 旧C6+C7→C4 去人化+验真;七桩事实降级为子事实一桩不丢;02-why.md 全文重组 + 两张 SVG 同步改号;收编发生在下游引用之前,C1~C4 自此冻结
- 第 2 次新视角+产物迭代:用户提出 ①C1 命名要更通俗(资源利用率角度:让 CPU/内存更多用于用户计算) ②C2 可由 C1 推出,应合并 → 验证其推导成立(效率压力的三连锁:闲置浪费→共享 / 共享互害→隔离 / 隔离太贵也是浪费→隔离必须便宜;第③环咬回第①环成闭环;C2 的"事实"独立但"命令"=效率×事实,归并名正言顺)→ 二次收编 4→3:新C1「榨干硬件」(主张用用户原话) / C3★→C2★ / C4→C3;幕一二三恰好一幕一环喂 C1;三条压力=隔离/打包/运维三大支柱;全文+两图+底账同步;C1~C3 真冻结(下一站起挂机制)。"镜像不装什么"探针顺延待答
- 第 3 次探针通过+产物迭代:用户答验收探针 ①镜像不装内核 ✓ ②"内核是统一的厂房设施/最高等级统一抽象"→ 精确化:目的地内核版本并不统一(5.15 vs 4.18),真底气是接口三性质 —— 窄(唯一接触面=几百个 syscall)/ 稳(Linus 铁律 We do not break userspace,只加新孔不改旧孔)/ 单向(新内核跑旧用户态✓,反之 io_uring→ENOSYS;精确表述:目的地内核 ≥ 所用最新插孔)+ uname -r 手验 → 已 patch:C1③ 下新增「内核接口是国标插座」小节,标记为 How 的第一个洞口(namespace 谎言就撒在此接口)

### How 阶段
- 开场对齐(2026-06-04):用户选 B 机制档;反向报三件事(insight层"共享平面上移"/机制层"镜像overlayfs核心发明"/果实层"web标配弹性伸缩")→ 合龙为砌墙术/叠行李术/流水线验真术,两处纠偏(电表归C1→误解#1;弹性是果实→误解#4);用户两次追加:光盘磁带类比(→§3.4,multisession遮挡=whiteout,不能改vs不准改,C2-C3承重梁)+ git语义/部署code化(→§3.1/§3.5,Dockerfile=源码,IaC,层缓存=增量编译)。初稿+7图生成。
- 第 1 次探针交锋:"拆哪步塌回 2009"用户选第 4 步(备行李,= 摘 C2★ 心脏,自洽于其核心判断)→ 推演级联塌陷成立;揭出题人答案第 2 步(验真,= 挖 C3 眼睛,比 2009 更糟:工业效率散播未验真字节);合龙"打包与验真从来是一对"(C2★/C3 第三次成对)→ 已 patch:新增 §5.1 思想实验小节
- 第 1 次追问(通读中):①"顺序敏感/连坐"没懂 → 展开:缓存键=(父层+指令+文件内容)链,父层变则下游全失效(git 链/光盘 session 同构),坏/好排法 Node 实例 → patch §3.1;②overlayfs 文件如何存储/路径/索引查找 → 核心:overlay 不存一字节(每层=ext4 上普通目录树),路径=各层根下同位投影,查找=按层探测先见即得/whiteout 即停/目录合并/dcache 兜底 → 新增 §3.6 + 第 8 张图 03-overlay-lookup.svg
- 第 2 次追问:"overlay 不存数据,那每一层是什么?"→ 拆主语歧义:不存数据的是 overlayfs 机制(投影仪),层=ext4 上普通目录树(真数据);层的语义=文件级全量 diff(新增全量/修改后完整新版而非行级补丁/whiteout 墓碑,呼应 copy_up 整文件);铁证=umount 后各层文件分毫不少 → 已 patch:新增 §3.6.1
- 第 3 次新视角:用户自建"方块模型"(列=路径/行=层;新增/修改压旧版/红方块删除;三种查找)求验证 → 95 分:①②全对(尤其自己补出"文件级全量");拧一处 —— "新增=最上层找到"解绑(新增可在任何层),三种查找坍缩为一条规则(第一个方块说了算);补红方块=否定命中、空格=部分树("层的便宜便宜在空格上")、目录例外 → 已 patch:新增 §3.6.2(署读者原创)+ 第 9 张图 03-cube-grid-model.svg
- 第 4 次追问:"改最底层方块,向上各层要逐层补修改版吗?"→ 不:运行时只放一块直入 upper(唯一可写行;空格不挡探测;中间层共享冻结不可补;copy_up 源=当前命中的最上块);构建时想真改 L1=重铸新链 L1′→连坐 L2′L3′(=§3.1 缓存连坐在存储侧),旧链不销毁;统一律「层从不被修改,只被遮盖(运行时)或被替换(构建时)」,不可变性第四次撑场 → 已 patch:新增 §3.6.3
- 第 5 次需求:要求画"改 L1 后如何重组镜像"图 → 第 10 张图 03-rebuild-chain.svg(左旧链冻结存活/中"不存在修改只存在重铸+连坐"/右新链:L1′ 真变·L2′L3′ 指令未改但连坐重铸·全新 manifest;底部统一律 + 内容寻址去重彩蛋)嵌入 §3.6.3
- 第 6 次追问+需求:"net ns 隔离了 route table/iptables/等等(帮我列全),容器几乎断开,Tomcat 怎么提供服务?包怎么进出?要详析+画图" → 新增 §6.4 支线四:八件家当全清单(设备/IP/路由表/iptables+conntrack/端口空间/ARP/lo/sysctl,socket 列表彩蛋);进门=DNAT 引渡(只改目的)+conntrack 账本回程("第一个包走规则,后续走账本");出门=MASQUERADE 化妆(为什么:私网地址回程必迷路,SNAT 本质=给回程可达的收件地址)+账本还原;对称律"改写只为让包找到回家的路";--network host 对照彩蛋 → 3 张新图(11~13:netns-isolation/inbound-journey/outbound-journey),How pics 累计 13 张
- 第 7 次结构反馈+重组:用户指出"文章结构乱,要按主旨 6墙2洞 分章重组;凿洞1(写/存储)与 overlay 必须同章;凿洞2(网络)把 6.1/6.4 合并成章,用 ES+SpringBoot 例子讲清 172 网段是内部 IP、互通走哪一层(bridge=二层走 MAC)" → 全文重组:§2 墙(OOM 并入 §2.4) / §3 地板+洞一(copy-up 并入 §3.4,新增 §3.7 volume=凿穿 mnt 墙的竖井) / §4 洞二(§4.1 八件家当 + §4.2 重写为 SpringBoot 调 ES 八跳逐层标注表[L7/L4→L3 直连路由→ARP→L2 帧→bridge 查 FDB 只看 MAC→L3 收包→L4 socket],172=小区私网,自定义网络才有 DNS 彩蛋 + §4.3 进门 + §4.4 出门 + §4.5 对称律) / §5 指挥部 / §6 端到端;§0 加"全篇地图(墙与洞)"表;packet-journey 图主角改为 SpringBoot→ES;§10 回扣表补"洞一 volume"行;全部跨引修正
- 第 8 次需求(打断追加):§2 开头要先介绍 6窗3表2洞 各是什么/作用 + 各解决 C1~C3 的什么问题 → 新增 §2.0「点名册」:六窗每扇挂 C1② 具体痛(互见互杀/端口打架/路径打架/门牌串户/IPC 撞 key/特权外溢),net 窗标洞二凿点、mnt 窗标地板挂点+洞一凿点;三表每块挂幕一具体践踏 + 超额脾气 + "让合租从赌运气变成有合同"使命 + pids/cpuset 诚实备注;两洞出生证(洞一=C2★ 边界,洞二=C1② 反作用+C3 账)+ "洞 vs 拆墙"辨析
- 第 9 次答卷交锋:用户交 NAT 卷并自述完整出门模型求修正 → 判卷:①veth 拓扑满分;②"网桥通过 ARP 知道 IP"错位 → docker0 一人分饰两角(L2=FDB 只认 MAC / L3=宿主网卡+网关,ARP 表在端点);③"ARP 查不到才给网关"次序反 → 路由表先行定下一跳,ARP 只翻译网关(容器从不 ARP 网段外地址),网桥上交宿主栈后由宿主路由表+MASQUERADE 接力("路由选路,NAT 改名"=分工不是替代,回应用户"可能是 NAT 而不是路由表"的怀疑);四张表各答一问;最小改写律收卷(NAT 只改断回程的字段→透明/隐身是副产品)→ 已 patch:新增 §4.6
- 第 10 次判卷:用户复述两条总结 ①"IP 查找下一跳,MAC 到达下一跳" ②"docker0 工作在二层,IP 路由在宿主与容器内部" → 双双判对 + 精确化:①IP 身兼端到端身份(目的 IP 全程不变)+逐跳决策,MAC 单链路执行(逐跳换),"IP 是终点站名,MAC 是接力棒,ARP 是翻译官";②"路由住在协议栈里,协议栈住在 netns 里"(宿主一张/每容器一张),网桥只是走廊 → 已 patch:§4.6 +(5)两句收口口诀

### Origin 阶段
- 开场对齐(2026-06-04):用户选 B(技术接力)为骨 A(人物剧情)为肉;时间跨度 1979→2022 三段(前传/主线/尾声)无异议;资料严格度选混合档(转折点一手+背景综述);追加个人记忆"网上看到 docker,共享内核+打包依赖,惊呆了,解决了我对分布式系统所有的迷惑与恐惧"→ 织入尾声「大洋两岸的同一个瞬间」,并点出他一眼读出的正是 C1+C2★。初稿+3 图生成,引用双清单(一手 8 条+综述 7 条)+无一手坦诚清单。
- 第 1 次探针交锋:"四样行李哪样击中你"用户答"镜像是 docker 最伟大的发明"→ 三重验证闭环(直觉 2013/推导 C2★/史证 v0.1=LXC 包装纸)+ 公案判词(镜像=价值,docker run=传播系数)+ 历史终审(引擎死/命令垄断没/Dockerfile 有对手,唯镜像成 OCI 标准)→ 已 patch:尾声+「证词的最后一页」。Origin 内容讨论趋于收敛,下一步呈现🌉分水岭。

### Deep 阶段
- 开场对齐(2026-06-04):用户选 B 聚焦档 + 机制甲(runc 出生三连招)乙(overlay copy-up)丁(网络 veth+NAT)+ demo 环境①自包含特权容器。反事实默认 6 候选(用户未否决)。初稿生成:05-deep.md(三层剖析×3 + 反事实6×3 + 出生时间线 + 95%闭环)+ 4 SVG + 3 demo。要点:甲钉死"为什么 C 抢跑 Go"(单线程内核规矩+demo 实证 EINVAL+/proc/self/exe+CVE-2019-5736)；乙钉死"copy_up=整文件→改1B抄1GB"(demo du 实测+whiteout c0:0)；丁钉死"对称律"(自带假互联网主机,tcpdump 抓 SNAT隐身/DNAT透明)。源码一律标注"结构骨架,不假装逐字原文"。
- 用户反馈"这篇不太行" → 诊断 B(源码骨架不够实);用户确认:用 deeparch-md skill 方法(/Users/xiaojin/workshop/deeparch-video/skills/deeparch-md.md,只读不改该项目)把甲乙丁源码讲透,不需可跑 demo,供生成视频 → web 拉取真源码(runc nsenter.go 构造器 + nsexec.c 状态机 + 内核 copy_up.c 的 do_splice_direct 整文件循环 + veth.c 的 veth_xmit)→ 按 deeparch-md 套路推倒重写 05-deep.md(生活类比/ASCII全景/三层剖析逐行真源码/时间线/API附录/Q&A/@video标记/@facetime占位)。约定不运行 facetime_search.py(在 deeparch-video 项目内),人物 photo 留空待用户自行补。
- 用户三拒(甲乙丁/deeparch-md 版都"不行"),给定新线索:废弃甲乙丁,改「6墙/3表/2洞」三点,每点深入 Linux 内核源码 + SVG,不限篇幅逻辑为先。已清空旧 pics/src。为降风险先做第一点验格式:【第一点 clone→6墙】整块完成 = web 拉 torvalds/linux 主线真源码逐行(kernel/nsproxy.c 的 create_new_namespaces 五扇窗串调 + copy_namespaces 的 CLONE_NS_ALL&~CLONE_NEWUSER 快路径与 CAP_SYS_ADMIN 检查 + kernel/pid_namespace.c 的 create_pid_namespace 讲 PID 1 幻觉=level+idr + unshare_nsproxy_namespaces 讲 pid_ns_for_children 只对子进程生效)+ user 窗为何特殊(在 copy_creds 不在 nsproxy)+ all-or-nothing goto 回滚 + SVG 05-clone-6walls.svg。第二点(三个表:cgroup css/memcontrol try_charge/CFS throttle/blk-throttle)、第三点(两个洞:veth_xmit/veth_newlink + fs/namespace.c bind mount)占位待补,等用户确认第一点格式即按同规格连写。
- 用户第四次反馈"不够完美,太简单了" → 明确新规格:按 deeparch-md skill 的完整方法(概览/生活类比/架构全景图/三层剖析/端到端时间线/API附录/Q&A/延伸阅读+@video标记)分别套到 6墙/3表/2洞,生成 3 个文档再拼成 05-deep;唯一改动=架构全景图从 ASCII 改 HTML。已清旧。第一篇 05-1-walls.md 按此完整规格做出(比上版深得多:加了概览/给新员工配独立视图的生活类比/HTML 架构图[内嵌+独立 pics/05-1-walls-arch.html]/三层剖析[操作层 3syscall + 函数逻辑层 4 函数真源码逐行:create_new_namespaces 派生链+回滚、copy_namespaces 的 CLONE_NEWUSER 抠除铁证、create_pid_namespace 的 level+idr 造 PID 1、unshare 的 pid_ns_for_children + alloc_pid numbers[] 双号、底层原理 trade-off]/端到端时间线/API+源码附录/6 条 Q&A/延伸阅读)。等用户验第一篇格式,过则同规格连写 05-2-tables.md(3表)+ 05-3-holes.md(2洞),再 cat 成 05-deep.md。
- 用户第五次反馈(对第一篇)：前面总结好，后面要更细致，改"总分"结构：①总=先写 mini-docker C 代码演示 6 墙效果+贴控制台输出作铁证(C 代码直接贴 md)；②分=对着用户态代码，6 扇窗各一小节，每节从用户态 syscall 深入到内核实现关键代码。已照做：写 src/05-mini-docker.c(80 行 clone 六 flag + uid_map 同步，Linux 专属，Mac linter 报错是环境误报不改)；05-1-walls.md 重构为 总(C+控制台输出+宿主vs容器铁证表)+ 分(6 小节 uts/pid/ipc/mnt/net/user，每节【用户态】+【内核实现】贴真源码逐行：uts copy_utsname memcpy / pid create_pid_namespace level+idr / ipc create_ipc_ns 四个 init_ns 空表 / mnt copy_mnt_ns→copy_tree 复制挂载树[fs/namespace.c 太大用准确调用链非伪造] / net copy_net_ns→setup_net 遍历 pernet_list 最贵 / user create_user_ns level+owner+kuid_has_mapping 挂 cred)+ 底层原理"先继承再分叉"+时间线+API表+6 QA。5 扇窗 web 拉到 torvalds 主线真源码,mnt 因文件大用调用链。等用户验此细致度，过则同规格写 3表/2洞。
- 用户第六次反馈(对第一篇)：基本可以了(=格式锁定)+增强 net 窗：列出容器隔离了哪些网络表(iptables/路由策略/arp 表等)说明作用。已 patch 05-1-walls.md 墙五:加 11 行表(net_device/IP/FIB路由/RPDB路由策略/ARP邻居/iptables nat/conntrack/端口/socket/TC/sysctl net.*)+作用+隔离效果,接 setup_net 的 pernet_list,勾向洞二。**格式确认通过,开始连写第二、三篇。** 第二篇(3个表)拉 cgroup 三 controller 真源码中:mm/memcontrol.c try_charge_memcg(内存) / kernel/sched/fair.c CFS throttle(CPU) / block/blk-throttle.c(IO)。
- **Deep 三篇全部完成并拼接**(2026-06-05):05-1-walls.md(6墙)+ 05-2-tables.md(3表)+ 05-3-holes.md(2洞),每篇总分结构+真源码+HTML 架构图。05-2:总=cgroup v2 掐进程(OOM 137 铁证)，分 memory(try_charge_memcg 逐字真源码:page_counter_try_charge→try_to_free_mem_cgroup_pages→mem_cgroup_oom)/cpu(CFS __account_cfs_rq_runtime→throttle_cfs_rq 真函数名调用链)/io(__blk_throtl_bio→tg_within_bps/iops_limit→tg_dispatch_time 真函数名);底层原理"流量vs存量"解释为何内存杀别的限速。05-3:总=veth pair 跨 netns ping + bind mount 持久 demo，分 veth(veth_newlink 双 rcu_assign_pointer peer 逐字 + veth_xmit)/volume(do_loopback→clone_mnt→attach_recursive_mnt 真函数名);"洞≠拆墙"辨析。拼接:05-deep-header.md(灵魂问题+三部分导览+C1~C3速查+约束对应)+ cat 三篇 → 05-deep.md(996 行)。3 张独立 HTML 图(pics/05-{1,2,3}-*-arch.html)转义修复后 xmllint OK。mini-docker.c(Linux 专属)。等用户验收整篇 Deep。

### Comparison 阶段
- 开场对齐(2026-06-05):恢复会话后渐进式 4 问收敛 —— ①岔路口选「比一比」②对比域选「圈内比」③用户点名 LXC + podman ④隔离轴补位选 Kata(弃 gVisor)。三面镜子恰好一镜一约束:LXC→C2★(容器的单位)/ podman→C3(控制面)/ Kata→C1③(隔离的墙)。reconfirm 无追加。初稿 06-comparison.md(约束速查 + §0 三镜 + §1 2×2 设计空间图 + §2 出生证明[初衷/擅长/不擅长/谁在用] + §3~§5 三组对照[五元组表] + §6 回扣 + §7 呼应 98% 闭环)+ pics/06-overview.svg(墙轴×行李轴四象限,docker 与传统 VM 成对角,podman 同格第三维,gVisor 骑线)。判词主线:墙是公共件 / 指挥部是偶然 / 便宜会过期 → 不变量 = C2★ 镜像 + C3 流水线。跨站回扣:LXCFS 接 What §4.5 / 统一律反面接 How §3.6.3 / conmon·crun 接 How §5 + Deep nsexec / rootless 接 Deep 墙六 / 国标插座搬进房间接 Why C1③。
- 第 1 次需求(2026-06-05):用户验收初稿方向("感觉可以")+ 追加"KVM 跟 docker 的区别与联系" → 定位为类目纠错而非第四面镜子(KVM 不答题,它供货):新增 §5.6 —— KVM = 内核第二套隔离原语(物理墙发动机,/dev/kvm,2.6.20 与 cgroups 2.6.24 前后脚进主线,Qumranet/红帽);金句"VM 在宿主上就是一个 QEMU 进程,vCPU=线程";容器进程 vs 客机进程四行对照(执行模式/看到的内核/边界/成本);层层对位表(KVM↔ns+cgroups / QEMU↔runc / qcow2·AMI↔OCI 镜像 / libvirt↔dockerd)→ 行李行揭示"墙的生意≠行李的生意";三条联系(同根两头下注 / 互为嵌套[云 k8s 节点=KVM 墙内砌逻辑墙;Kata=容器流水线里藏物理墙] / KVM=Kata 降价战军火商)。§1 读图清单 5→6 件事 + SVG 加 KVM 地基注。→ 已 patch 文件:§5.6 + §1 + 修订记录。探针升级:旧问「为何 2026 默认仍是 runc」折入新问「双层墙之下,Kata 的刚需买家是谁」,挂起待答。
- 第 1 次新视角(2026-06-05):用户贡献递进双问 ——「在一个 Linux 内核里能否再启动一个新版本内核」应作为 KVM 的引出问题(KVM = CPU hypervisor 能力的封装,让用户态进程启动全新内核);更深一问「macOS 没有 Linux 内核怎么跑 docker」(macOS 有 KVM 类似物,先启动 Linux 内核再在其上跑 docker)→ 双双验证成立 + 三处精确化:①KVM 封装的不只 Intel(VT-x/AMD-V/ARM 扩展统一进 /dev/kvm);②namespace 原理上接不了"换内核"(换视图不换地基;uts 窗只换 nodename 不换 release)—— 容器之轻的代价 = 厂房钉死(接 Why 国标插座单向性 + What 搬家故事);③macOS 对等物 = Hypervisor.framework,Docker Desktop 栈 = hvf→HyperKit/Virtualization.framework→LinuxKit 迷你内核→dockerd→容器,Windows = WSL2 方言版;嵌套孪生对偶(云上嵌套买隔离 / Mac 嵌套买兼容)→ 金句「逻辑墙运应用,物理墙运内核」;Apple 2025 Containerization = 每容器一台 microVM(Kata 形状)彩蛋 → 已 patch 文件:§5.6 重构为 §5.6.1~§5.6.3 双问递进 + 修订记录两行。新探针:Mac 上 volume 挂载为何出了名的慢(考"物理墙边界税"迁移),挂起待答。
- 第 2 次需求(2026-06-05):用户要求把探针「Mac volume 为何慢」直接写进文档,并宣布"加完就完毕" → 新增 §5.6.4 问题三(最贴身):Linux 基线 = 洞一是同一内核里的 VFS 记账(回扣 How §3.7 竖井 + Deep 洞二 do_loopback→clone_mnt→attach_recursive_mnt),免费;Mac = 源码在 XNU/APFS、容器在隐藏 VM 的 Linux 内核,每次文件操作过境物理墙(guest VFS→virtiofs/gRPC-FUSE→virtio 队列→macOS 文件服务→APFS);单次 µs vs 本地 dcache ns(贵三个数量级)× node_modules stat 风暴 = 出名的慢;三代撬棍(osxfs→gRPC-FUSE→virtiofs)抹不平"两内核不共享 page cache/dcache + fsevents↔inotify 翻译税";民间疗法反推原理(named volume 回单内核 / mutagen 不过境 / devcontainer 源码进 VM 侧)= 治法只有"别让热路径穿物理墙";对偶收口「洞凿在逻辑墙上是门,凿在物理墙上是海关」= §5.3 Kata IO 边界税同款 → 已 patch:§5.6.4 + 修订记录。用户宣布本篇完毕 → 已抛推进 reconfirm(全文是否看过),待确认后封存。
- 第 2 次产物迭代(2026-06-05):用户指示「KVM 与 docker」单独成章 → §5.6 升格为 ## §6(新增独立章引言:不算第四面镜子[不答 docker 的考卷]但纠缠最深;子节 §5.6.1~4 → ### §6.1~§6.4);原 §6 约束回扣 → §7、§7 呼应灵魂问题 → §8;§1 读图清单"详见 §5.6"→"详见 §6";修订记录补行。终稿结构:速查 + §0 三镜 + §1 概览 + §2 出生证明 + §3~§5 三镜对照 + §6 KVM 三问 + §7 回扣 + §8 呼应(98%)。推进 reconfirm 仍挂起待答。

### Synthesis 阶段
- 开场对齐(2026-06-05):渐进式 5 问收敛 —— ①目标读者=教学他人/团队分享 ②基线=水平混搭团队(主线按"用过没拆过",关键术语一句话脚注)③用户钦点必保三洞察:6墙3表2洞=核心架构 / 三约束=催生背景 / 镜像=最核心创新(程序+依赖环境一起打包)→ 直接定为 §0 三承重梁 ④方法论泛化演示=要,套 K8s ⑤篇幅=详尽讲义版 ~8000 字。追加 reconfirm 用户答"ok"无追加。硬核模式(Deep 已完成)初稿生成:约束速查(带新人导读)+ §0 三承重梁 + 新人五句话脚注 + §1 全旅程概览图(三约束→三支柱→三镜+KVM 地基+五步环)+ §2 五元组表 13 行(决策×约束×代价×反事实×现实对照,竖读第二列=13 行挂 3 约束 / 竖读第五列=每行都有人真走另一条路)+ §3 同构×3(git=镜像存储哲学同构 / JVM=国标插座收口位对照 / 集装箱=用户 What 类比正式收编)+ §4 局部最优论证(逐条取消约束→最优解漂移→现实都有人活着)+ §5 时代局限演化表(化石置换史,含 Docker 公司 2019 卖企业业务 vs 标准永生)+ §6 五步法(每步 docker 实例+口诀+提问模板五连)+ §7 现场泛化拆 K8s(K1 容器会死/K2 要互相找/K3 舰队超人=C3 舰队版;"上一层的解是下一层的题";swarm/Nomad/ECS 对照;双价目表双最优;留 3 道练手题)+ §8 产物对账回扣 + §9 灵魂问题三版本答案(电梯/工程/哲学)宣布 100% 闭环。
- 第 1 次探针交锋(2026-06-05):收束探针「同事反驳 namespace 才是核心」用户接招 —— 部分认下(隔离=必要条件)+ 驳回(产品化补齐最后一公里=镜像,让大众易用易理解才获胜)→ 判卷:结构全对,且独立重推出 Origin 判词「镜像=价值,docker run=传播系数」;精确化:①必要条件不参与决胜(2013 年墙=人人有份的公共件)②"最后一公里"的约束语言=最后一条未解约束(C2★+C3)③"易被采纳"本身是一条约束(采纳约束:认知/迁移成本,zones 优雅却绑死 Solaris 为反例)→ 已 patch:新增 §4.1 预演反驳(署读者观点)+ §6 第一步增补采纳约束 + 修订记录。已抛收尾询问(还要盘哪块,还是收工进导出),等用户决定。

## 选定的对比对象（Comparison Hook 后填入）
- LXC（维度:容器的单位 —— 整套系统 vs 单个应用;拷问 C2★）
- podman（维度:控制面 —— 常驻守护进程 vs fork-exec;拷问 C3）
- Kata Containers（维度:隔离的墙 —— 共享内核 vs 每实例独立内核;拷问 C1③）
- （对齐过程:用户主动点名 LXC + podman;隔离轴在 gVisor/Kata 二选一中选了 Kata）

## 选定的导出格式（导出阶段填入）
- MD + HTML（用户在 Synthesis 收尾时直接指定："融合吧,md+html"）
