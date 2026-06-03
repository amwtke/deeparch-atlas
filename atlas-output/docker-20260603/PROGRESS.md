# docker技术的来龙去脉 Atlas Progress

## 元数据
- **主题**: docker技术的来龙去脉
- **短名**: docker
- **工作目录**: atlas-output/docker-20260603/
- **创建时间**: 2026-06-03T06:46:35Z
- **上次更新**: 2026-06-03T09:54:34Z
- **当前阶段**: What 已封存完成；下次启动进入 Why（进入前按"推进 reconfirm"纪律确认用户已读 01-what.md 全文 / 愿意推进）

## 灵魂问题(Discovery 收集)
> "容器到底是什么?它和虚拟机的根本区别在哪?当一个容器真正跑起来的那一刻,Linux 内核里到底发生了什么 —— namespace、cgroups、镜像分层各自扮演什么角色?"

（用户重心选了 A 本质派：从"它根本不是虚拟机"切入，逐个钉死 namespace / cgroups / 镜像分层，搞懂一个容器跑起来时内核里到底发生了什么。起头从本质，收尾到演化。）

## 进度状态机
- [x] 0. Discovery
- [x] 1. What
- [ ] 2. Why（含约束清单建立）
- [ ] 3. How
- [ ] 4. Origin
- [ ] 5. 分水岭决定
- [ ] 6. Deep
- [ ] 7. Comparison（可选）
- [ ] 8. Synthesis
- [ ] 9. 导出格式询问
- [ ] 10. 融合输出

## 约束清单（Why 阶段建立，后续阶段引用）
| # | 约束 | 来源 | 不可再分性 |
|---|------|------|-----------|
| (Why 阶段写入) | | | |

## 用户疑问/追问审计

### What 阶段
- 第 1 次产物迭代:用户答对 `ps` 方向性探针(宿主看得到容器进程 / 容器看不到宿主)→ 提炼"单向玻璃 + 不对称是容器 vs VM 试金石"洞见 → 已 patch 文件:新增 §2.1「一个一眼分辨容器还是 VM 的小实验」
- 第 2 次新视角:用户自己提出心法"Docker = 砌墙 + 凿洞(4 堵墙 + 2 个洞,可能数错)"→ 精确化为「2 类墙(namespace 6 窗 + cgroups)+ 1 块地板(overlayfs)+ 2 个洞(veth 凿 net 墙 / volume 凿 mnt 墙)」,点出"每个洞都凿在某扇 ns 墙上"的对偶 → 已 patch 文件:新增 §0「心法:砌墙 + 凿洞」+ 第 7 张图 01-walls-and-holes.svg
- 第 3 次新视角/追问:用户继续延伸类比(cgroup=电表/水表✓;overlayfs=日历?;"Docker 借鉴现实生活")→ 评估:cgroup=电表满分(补 CPU/IO 限速 vs 内存 OOM kill);overlayfs≠日历(日历只接住"累积写入",漏分层/复用/CoW),改为"一摞透明胶片";meta 洞见肯定+分层(字面借词 container/image/registry/volume/port/bridge/mount vs 工程传统 ns/cgroups/CoW)+"类比是脚手架"告诫 → 已 patch:§4.4 加"透明胶片"类比 + 新增 §0.1 旁注「Docker 从生活借词」
- 第 4 次新视角:用户自创"集装箱=车间(工人+机器=应用+依赖),水电煤气接口标准化→房间可搬到别的大楼"=独立推导出可移植性/OCI 论点 → 肯定+精确化:集装箱真正创新=接口标准化(=OCI 存在理由);关键边界=可移植有前提(需兼容内核 ABI),Linux 间随便搬但 Win/Mac 需 Docker Desktop 偷塞 Linux VM;回扣灵魂问题(共用内核→既轻又绑定内核家族,是硬币两面) → 已 patch:新增 §3.1「第二个类比:集装箱→可移植」+ 第 8 张图 01-shipping-container-portability.svg
- 第 5 次需求:用户要"按这种类比生成图,尽量有生活也有技术细节" → 做了「生活↔技术 对照图册」(左生活/右真实技术参数),用户追加"要"后补满 6 张:①01-life-tech-overview(大楼↔主机)②01-life-tech-namespace(单向玻璃房↔6类ns)③01-life-tech-cgroups(三块表↔cpu.max/memory.max/io.max+OOM)④01-life-tech-overlayfs(透明胶片↔lowerdir/upperdir/CoW/whiteout)⑤01-life-tech-network(管道井+市政↔veth/bridge/iptables MASQUERADE)⑥01-life-tech-pipeline(物业接力↔dockerd/containerd/runc/shim) → 已 patch:§3.2「生活↔技术 对照图册」含全 6 张。What 阶段 pics 累计 14 张图。
- 第 6 次产物迭代:揭晓 512MB/64GB 探针(答案=64GB,因 /proc/meminfo 未 namespace 化;两道墙独立;JVM/Node OOM 事故;治法 /sys/fs/cgroup/memory.max + UseContainerSupport + LXCFS;水位计 vs 水表类比)→ 已 patch:新增 §4.5「墙是漏的:512MB 容器自报 64GB」,作为通往 Why 的桥(墙有缝/有代价/有取舍)

### Why 阶段
- (无)

### How 阶段
- (无)

### Origin 阶段
- (无)

### Deep 阶段
- (无)

### Comparison 阶段
- (无)

### Synthesis 阶段
- (无)

## 选定的对比对象（Comparison Hook 后填入）
- (无)

## 选定的导出格式（导出阶段填入）
- (待定)
