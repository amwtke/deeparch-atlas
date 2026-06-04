<!-- ===== 第三篇 / 共三篇:两个洞。最终拼入 05-deep.md。deeparch-md 方法,架构图 HTML,总分结构。 ===== -->

<!-- @video: scene=spotlight -->
# 三、两个洞:veth 与 volume 的内核实现

> 心法回扣:What 阶段说"墙是默认,洞是例外;每个洞都凿在某一扇 namespace 墙上"。第一篇造了六面墙,这一篇看怎么在墙上**凿受控的洞**:**洞一 veth 凿 net 墙**(让孤岛能通信)、**洞二 volume 凿 mnt 墙**(让数据能持久)。先各凿一个洞演示(总),再分两个洞钻内核(分)。

## 概览

namespace 把容器关成孤岛:net 窗让它有独立网络栈但与外界断开,mnt 窗让它有独立挂载树但只看得见自己的 `/`。可纯隔离没法干活 —— 服务要通信、数据要持久。于是要在墙上**凿洞**:

- **洞一 · veth**(virtual ethernet):一对虚拟网卡,一头在容器 net 窗、一头在宿主。容器从自己的 `eth0` 发包,内核**直接把帧递到管子另一头** —— 这就是孤岛对外的网线。
- **洞二 · volume**:一个 bind mount,把宿主的某个目录**嫁接进容器的挂载树**。容器访问那个路径,直接落到宿主文件系统,**绕过 overlay、不走 copy_up** —— 这就是有状态数据的持久竖井。

两个洞凿在不同的墙上,但本质相同:**在隔离的默认之上,开一个指向外部的受控入口。**

## 生活类比:在墙上接网线、凿竖井

容器是一间四面封死的保密屋:

- **veth 像穿墙的一根对讲线** —— 在墙上钻个孔,穿一根线,一头在屋里(`eth0`),一头在楼道(宿主)。屋里说话,线另一头立刻听到。线是成对的,一拉两头都动。
- **volume 像凿一口直通楼下仓库的升降井** —— 屋里地板上开个口,直通楼下的公共仓库(宿主目录)。往井里放东西,楼下仓库立刻有;屋子拆了(容器删了),仓库还在。

> 关键:这两个都是**受控开口**,不是把墙推倒。屋子还是那间隔离的屋子,只是被精确地开了一根线、一口井。**洞 ≠ 拆墙。**

## 架构全景图(HTML)

> 完整版:[`pics/05-3-holes-arch.html`](pics/05-3-holes-arch.html)。下方为内嵌图。

<!-- @video: scene=layers title=两个洞 -->
<div style="background:#0a0c10;color:#e8eef5;font-family:'JetBrains Mono',monospace;padding:18px;border-radius:10px">
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">
    <div style="background:#0e1d14;border:1.6px solid #40c060;border-radius:8px;padding:12px">
      <div style="color:#88ff88;font-weight:700;text-align:center">洞一 · veth(凿 net 墙)</div>
      <div style="border:1px dashed #c08040;border-radius:6px;padding:6px;margin:6px 0;text-align:center;color:#ffaa55;font-size:11px">容器 netns:eth0(veth 一头)</div>
      <div style="text-align:center;color:#40c060;font-size:11px">▲ priv-&gt;peer ▼ 一对一互指(RCU)</div>
      <div style="border:1px dashed #40c060;border-radius:6px;padding:6px;margin:6px 0;text-align:center;color:#88ff88;font-size:11px">宿主 netns:另一头 → 插 docker0</div>
      <div style="font-size:10px;color:#7fd99f;text-align:center;margin-top:6px">veth_xmit 把 skb 直接递给对端(零拷贝)</div>
    </div>
    <div style="background:#16263a;border:1.6px solid #4080c0;border-radius:8px;padding:12px">
      <div style="color:#88c0ff;font-weight:700;text-align:center">洞二 · volume(凿 mnt 墙)</div>
      <div style="font-size:11px;color:#9fb4c8;background:#0d1117;border:1px solid #2a3340;border-radius:6px;padding:8px;margin:6px 0;line-height:1.7">/ ← overlay(易失,走 copy_up)<br>└─ <span style="color:#88c0ff;font-weight:700">/data ← bind mount 竖井</span><br>&nbsp;&nbsp;&nbsp;&nbsp;▼ 直通宿主,绕过 overlay<br>&nbsp;&nbsp;宿主 /var/lib/docker/volumes/…(持久)</div>
      <div style="font-size:10px;color:#7fa8cc;text-align:center;margin-top:6px">挂载树里加一个直通宿主的入口</div>
    </div>
  </div>
  <div style="text-align:center;background:#11161d;border:1px solid #c08040;border-radius:8px;padding:8px;margin-top:10px;color:#ffc48a">veth = net 墙上的穿墙网线(peer 指针);volume = mnt 墙上的直通竖井(bind mount)。隔离默认,连通显式。</div>
</div>

---

# 总:亲手各凿一个洞

## 洞一:凿一根 veth,穿过 net 墙

<!-- @video: scene=code title=veth demo -->
```bash
#!/usr/bin/env bash   # root 跑
ip netns add c1
ip link add veth-h type veth peer name veth-c   # ★ 造一对(配对在内核 veth_newlink 完成)
ip link set veth-c netns c1                       # 一头塞进容器 netns
ip addr add 10.1.1.1/24 dev veth-h; ip link set veth-h up
ip netns exec c1 ip addr add 10.1.1.2/24 dev veth-c
ip netns exec c1 ip link set veth-c up
ip netns exec c1 ip link set lo up
ip netns exec c1 ping -c 2 10.1.1.1               # 容器 → 宿主:通了 = 洞凿成
```

```text
PING 10.1.1.1 (10.1.1.1) 56(84) bytes of data.
64 bytes from 10.1.1.1: icmp_seq=1 ttl=64 time=0.038 ms
64 bytes from 10.1.1.1: icmp_seq=2 ttl=64 time=0.041 ms
--- 10.1.1.1 ping statistics ---
2 packets transmitted, 2 received, 0% packet loss
```

一个本来与世隔绝的 net 窗,接上一根 veth 就能和外界说话了。`time=0.038 ms` 这么快,是因为根本没上物理网线(下面看源码)。

## 洞二:凿一口 bind mount 竖井,穿过 mnt 墙

<!-- @video: scene=code title=volume demo -->
```bash
#!/usr/bin/env bash   # root 跑
mkdir -p /srv/hostdata
echo "我在宿主上" > /srv/hostdata/note.txt

unshare --mount --fork bash -c '
  mount --bind /srv/hostdata /mnt      # ★ 把宿主目录 bind 进本 mnt 窗的 /mnt
  echo "[容器内] 读到:$(cat /mnt/note.txt)"
  echo "容器也写了一行" >> /mnt/note.txt
'
echo "[宿主] 现在文件内容:"
cat /srv/hostdata/note.txt             # 容器写的东西,宿主这边也在 —— 竖井直通
```

```text
[容器内] 读到:我在宿主上
[宿主] 现在文件内容:
我在宿主上
容器也写了一行
```

容器在自己隔离的挂载树里,通过 `/mnt` 直接读写了宿主的目录;`unshare` 退出后,宿主的文件还在 —— **数据独立于容器存活**。这就是 volume 持久化的本质。

---

# 分:两个洞逐个钻(用户态 → 内核实现)

## 洞一 · veth(凿 net 墙):一对互指的设备

**【用户态】** `ip link add veth-h type veth peer name veth-c` 造**一对**虚拟网卡;`ip link set veth-c netns c1` 把一头塞进容器 net 窗。这一对就是穿过 net 墙的网线。

**【内核实现 · 配对】** `veth_newlink()`,真源码(`drivers/net/veth.c`):

```c
static int veth_newlink(struct net_device *dev, ...)
{
	/* … 创建并注册两个 net_device:dev 和 peer … */
	err = register_netdevice(peer);
	/* … */
	err = register_netdevice(dev);
	/* … */

	/* tie the deviced together */
	priv = netdev_priv(dev);
	rcu_assign_pointer(priv->peer, peer);   /* ★ dev 的 peer 指向 peer */
	/* … */
	priv = netdev_priv(peer);
	rcu_assign_pointer(priv->peer, dev);    /* ★ peer 的 peer 指回 dev */
	/* … */
	return 0;
}
```

**逐行读:** veth 的全部魔法就这两行 `rcu_assign_pointer(priv->peer, …)` —— **两个设备各存一个指向对方的 `peer` 指针,一对一互指**。这就是"一根网线两头"在内核里的真身:不是真有根线,是两个 `net_device` 互相记住了对方。

**【内核实现 · 传输】** `veth_xmit()`,真源码(`drivers/net/veth.c`):

```c
static netdev_tx_t veth_xmit(struct sk_buff *skb, struct net_device *dev)
{
	struct veth_priv *priv = netdev_priv(dev);
	struct net_device *rcv;
	/* … */
	rcu_read_lock();
	rcv = rcu_dereference(priv->peer);       /* ① 拿到管子另一头 */
	/* … */
	ret = veth_forward_skb(rcv, skb, rq, use_napi);  /* ② 直接喂给对端的接收路径 */
	/* … */
}
```

**逐行读:** 容器从 `eth0`(veth 一头)发包 → `veth_xmit` 用 `rcu_dereference(priv->peer)` 找到另一头(①)→ `veth_forward_skb` **把 skb 直接塞进对端设备的接收队列**(②,内部走 `__dev_forward_skb` → `netif_rx`)。**没有物理介质、没有序列化上线,就是把数据结构从一头递到另一头** —— 所以 demo 里 ping 只要 0.038ms。

> **凿穿 net 墙 = 给隔离的 net 窗,塞一个"peer 在墙外"的设备。** 包从这个设备出去,内核直接递到墙外那一头(再插 docker0,见 How 第三篇网络洞的完整旅程)。

## 洞二 · volume(凿 mnt 墙):把宿主目录嫁接进挂载树

**【用户态】** `mount --bind /srv/hostdata /mnt`(底层 `MS_BIND`)。runc 则按 OCI 配置里的 `mounts` 项,在容器 mnt 窗里做同样的 bind mount。

**【内核实现】** 调用链(`fs/namespace.c`,该文件 5000+ 行,这里给**准确调用链 + 真函数名**,不伪造逐字):

```
mount(--bind) → do_mount → path_mount
  └─ 检测到 MS_BIND → do_loopback(path, old_name, recurse)
       └─ clone_mnt(old_mnt, old_dentry, flag)
       │     // ★ 造一个【新的 struct mount】,但它指向【同一个 dentry/inode】
       │     //   = 同一份宿主文件,在挂载树里多了一个"入口"
       └─ graft_tree / attach_recursive_mnt(mnt, parent, mp)
             // 把这个新 mount 嫁接到容器挂载树的目标挂载点(如 /data)
```

**逐行读:** bind mount 的核心是 `clone_mnt()` —— **它不复制数据,只造一个新的挂载点对象,指向同一个底层 `dentry`(宿主那个真实目录)**;再由 `attach_recursive_mnt` 把它**嫁接进容器的那棵挂载树**(就是第一篇 `copy_mnt_ns → copy_tree` 复制出来的那棵)。于是:

- 容器的 `/`(根)由 overlay 提供(易失、走 copy_up);
- 但 `/data` 这个挂载点,被嫁接成了**直通宿主真实目录的入口** —— 访问它**绕过 overlay,直接落到宿主 fs**。

> **凿穿 mnt 墙 = 在容器隔离的挂载树里,嫁接一个指向宿主目录的 mount 入口。** 它既让数据持久(独立于容器),又绕过了 overlay 的写放大(回扣 What §4.4 / 第二篇:数据库挂 volume 既为持久也为避开 copy_up 税)。

---

## 底层原理层:洞的共性与"洞 ≠ 拆墙"

- **墙默认,洞例外。** namespace 让容器默认与外界隔离(net 孤岛、mnt 独立树);洞是**显式凿出来的受控通道**,没凿就是断的。
- **两洞凿在不同墙,机制同源。** veth 凿 net 墙(用 `peer` 指针把帧递到墙外),volume 凿 mnt 墙(用 `clone_mnt` 把宿主入口嫁接进挂载树)。共性:**在隔离之上,开一个指向外部的受控入口** —— veth 的入口是 peer 设备,volume 的入口是 host dentry。
- **洞 ≠ 拆墙(关键辨析)。** 洞保留墙、只开受控口:容器仍在独立 net 窗(只是有根 veth)、仍在独立 mnt 窗(只是某点直通宿主)。而 `--network host` / `--pid=host` 是**整扇拆墙**(直接不开那扇窗,共享宿主),放弃隔离。看任何容器网络/存储配置,先问一句:**这是凿洞(保留隔离+受控连通)还是拆墙(放弃隔离)?**
- **回扣心法:** What §0 "砌墙 + 凿洞"的内核版至此闭环 —— 第一篇 6 把刀砌墙(`copy_*`),这一篇 2 种术凿洞(`veth_newlink` / `clone_mnt`)。

## 端到端场景时间线

<!-- @video: scene=timeline title=docker run -p + -v 的洞 -->
```
docker run -p 8080:80 -v db:/var/lib/mysql mysql 时,runc 凿两个洞:
T=0    net 洞:dockerd(libnetwork)建 veth pair → veth_newlink 互指 peer
T+1      一头 set netns 进容器 → 容器 eth0;另一头插 docker0
T+2      写 iptables DNAT(-p 8080:80 那条)→ 外网能进(How 第三篇完整旅程)
T=0'   mnt 洞:runc 按 OCI mounts 配置
T+1'     mount --bind /var/lib/docker/volumes/db/_data → 容器 /var/lib/mysql
T+2'     clone_mnt + 嫁接进容器挂载树 → mysql 数据直落宿主、绕过 overlay
———— 两洞凿好,容器既能被访问(net),又能持久存数据(volume)————
```

## API / 源码参考附录

| 洞 | 凿哪扇墙 | 用户态 | 内核实现 | 文件 |
|----|--------|--------|---------|------|
| veth | net 窗 | `ip link add … type veth peer …` | `veth_newlink`(peer 互指)+ `veth_xmit`(递 skb) | `drivers/net/veth.c` |
| volume | mnt 窗 | `mount --bind /src /dst` | `do_loopback` → `clone_mnt` → `attach_recursive_mnt` | `fs/namespace.c` |

## 常见问题 Q&A

<!-- @video: emphasis=normal -->
**Q1:veth pair 删一头,另一头会怎样?**
A:veth 是成对的,删除一端,内核会把另一端也清掉(peer 指针失效)。容器销毁时它的 net 窗连同里面的 veth 一端消失,宿主端的 peer 也随之删除 —— 所以容器没了不会留下半截 veth。

**Q2:bind mount 和 cp 复制有什么区别?**
A:本质不同。`cp` 是把数据复制一份(两份独立);bind mount 的 `clone_mnt` **不复制数据,只是让同一份宿主目录在容器挂载树里多了一个访问入口**。改任一边,另一边立刻可见(同一个 inode)。

**Q3:为什么 volume 能绕过 overlay 的写放大?**
A:因为 volume 是直接 bind 到宿主真实文件系统(ext4/xfs)的挂载点,根本不在 overlay 的联合视图里。写它走的是底层 fs 的正常写路径,没有 copy_up 那回事(第二篇/What §4.4)。所以数据库数据目录必须挂 volume。

**Q4:容器互访(同宿主两容器)为什么那么快?**
A:都是 veth + docker0 网桥,`veth_xmit` 把 skb 直接递到对端接收队列,中间只过一次二层网桥转发,全程在内存里,不上物理网线。所以纳秒~微秒级。

**Q5:`--network host` 和 veth 模式的区别在源码层是什么?**
A:`--network host` = clone 时不带 `CLONE_NEWNET`(第一篇),容器共享宿主 net 窗,根本不需要 veth(也没有隔离)。veth 模式 = 容器有独立 net 窗(隔离)+ 一根 veth(受控连通)。前者是拆墙,后者是凿洞。

**Q6:一个容器能挂多个 volume、接多个 veth 吗?**
A:能。挂载树里可以嫁接任意多个 bind mount(多个 volume);net 窗里可以插任意多个 veth(多网络)。每个都是独立的一个洞,机制相同。

## 延伸阅读

<!-- @video: skip -->
- 内核源码:`drivers/net/veth.c`(`veth_newlink` / `veth_xmit` / `veth_forward_skb`)· `fs/namespace.c`(`do_loopback` / `clone_mnt` / `attach_recursive_mnt`)
- `man 2 mount`(MS_BIND)· `man 8 ip-link`(veth)
- How 阶段第三篇(网络洞的完整报文旅程:veth → bridge → NAT)
