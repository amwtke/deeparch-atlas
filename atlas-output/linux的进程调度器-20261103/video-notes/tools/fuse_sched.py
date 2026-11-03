#!/usr/bin/env python3
"""Fuse stages/*/*.md into <short>-atlas.md for the linux的进程调度器 run (per skills/final-export/SKILL.md)."""
import re, os, sys

RUN = sys.argv[1]
SHORT = 'linux的进程调度器'
VERIFY = sys.argv[2] if len(sys.argv) > 2 else None
os.chdir(RUN)

stages = [
    ('01-what', 'What', '它是什么', 0),
    ('02-why', 'Why', '为什么必须存在', 1),
    ('03-how', 'How', '大致怎么工作', 2),
    ('04-origin', 'Origin', '是怎么来的', 3),
    ('05-deep', 'Deep', '深度剖析', 4),
    ('06-comparison', 'Comparison', '横向对照', 5),
    ('07-synthesis', 'Synthesis', '设计哲学与方法论', 6),
]
cn_num = ['一', '二', '三', '四', '五', '六', '七']

def load(stage):
    p = f'stages/{stage}/{stage}.md'
    s = open(p, encoding='utf-8').read()
    out = []; skip = False
    for l in s.split('\n'):
        if l.startswith('## 修订记录'):
            break
        if l.startswith('## 约束清单速查'):
            skip = True; continue
        if skip and l.startswith('## '):
            skip = False
        if skip:
            continue
        out.append(l)
    body = '\n'.join(out).rstrip() + '\n'
    body = re.sub(r'\]\((pics|src)/', rf'](stages/{stage}/\1/', body)
    body = re.sub(r'`(pics|src)/([^`]+)`', rf'`stages/{stage}/\1/\2`', body)
    return body

def constraint_block():
    s = open('stages/03-how/03-how.md', encoding='utf-8').read().split('\n')
    i = next(k for k, l in enumerate(s) if l.startswith('## 约束清单速查'))
    j = next(k for k in range(i + 1, len(s)) if s[k].startswith('## '))
    blk = s[i + 1:j]
    out = []
    for l in blk:
        if l.startswith('> '):
            out.append('> 后文所有 `Cn·短名` 引用都对应下面 8 条;**各篇不再重复列**。它们在第二篇 Why 里从「一核一队列先来先跑」起一刀一刀推出(八刀八条,一刀一条),后面五篇交叉引用。每条是 markdown 标题,后文用 `[C1](#c1)` 一类链接或 `Ctrl+F` 搜 `C3` 跳回这里。')
            continue
        m = re.match(r'^#### (C\d+) — (.*)$', l)
        if m:
            out.append(f'<a id="{m.group(1).lower()}" name="{m.group(1).lower()}"></a>')
            out.append(f'#### {m.group(1)}·{m.group(2)}')
            continue
        out.append(l)
    return '\n'.join(out).strip('\n')

transitions = {
    'What': ('讲解员 → 论证者(共情模式)',
      '上面用「只有一支话筒的圆桌会」和一张四问全景图,立起了调度器的骨架:何时换、换谁、各多少、在哪换,规则只看账不看人。但只看骨架不知道它为什么非得长成这样。下一篇回到原点:把八颗核收成一颗、把调度器全拿掉,只留一个先来先跑的队列,让 xz、mysqld、redis 在上面排队,看它在哪一步撞墙 —— 每撞一次墙,就逼出一条不可再分的约束。读完你会拿到八刀八条约束 C1 ~ C8,它们是后面五篇所有设计决策的唯一依据。'),
    'Why': ('论证者 → 实操员(实践模式)',
      '八条约束立住了:只在打断点换、未来不可知、份额与延迟两头要、挑人须便宜、核各自为政、份额按组算、有人要硬保证、核不等速且耗电。但约束只说「必须解决什么」,不说「内核用哪几样东西、按什么顺序解决」。下一篇换成实操员的视角,用同一台 8 核机器上的 mysqld / redis / xz 贯穿:每核一本账和六层类栈长什么样、四个数(权重、虚拟时间、lag、deadline)怎么涨怎么比、标记怎么变成真换人、三种搬人各在什么时候、容器的配额怎么落到每个线程头上。先立三件核心组件,再按四问走,fair 账、多核、cgroup 带宽三块写最厚 —— 那是你前两轮没碰过或卡过的地方。'),
    'How': ('实操员 → 讲故事的人(沉浸模式)',
      '到这里你已经能顺着四问把每个机制说出来。但「它今天这样工作」不等于「它只能这样工作」:为什么 2002 年要改成每核一本账、2007 年为什么把猜意图的启发式整个删掉、1995 年就写在论文里的 EEVDF 为什么等了 28 年才进内核、2024 年为什么又允许 BPF 把挑人规则整个换掉。每一样都是某个人在某个年代的约束下做的选择。下一篇换成讲故事的人:Ingo Molnár、Con Kolivas、Paul Turner、Peter Zijlstra、Tejun Heo,加上学术线上的 Waldspurger 和 Stoica —— 资料严格一手,查不到的地方明说。'),
    'Origin': ('讲故事的人 → 工程师(工程师模式)',
      '五个转折点解释了形状从哪来。但形状落到 Linux 6.12 的源码里,是哪个函数、哪一行、按什么判据、花多少纳秒?下一篇换成工程师,把三条主线钉到源码上:EEVDF 挑人全程(lag 从零讲起,逐 tick 走表,并用一个可以在 macOS 上跑的模拟器核对手算)、多核的唤醒选核与周期均衡、cgroup 的层级份额与带宽 throttling。每条主线三层(操作层 / 函数逻辑层 / 底层原理层),贴 6.12 原文逐句注释,然后做反事实小试:如果不这样设计还能怎么做,各违反哪条约束。三个判据会在这一篇里浮出来:eligible 且 deadline 最早、有利可图且不热才搬、整组按周期借还。'),
    'Deep': ('工程师 → 评论家(比较模式)',
      '三条主线钉到行号和纳秒之后,还剩一个问题没法在 Linux 内部回答:这些选择里哪些是约束逼出来的,哪些只是血统带来的?答案要靠另一套从头设计的内核来对照。下一篇换成评论家,把 Linux 放到 Windows NT 的 dispatcher 旁边 —— Cutler 从 VMS 出发,在同样八条约束下做了一套 32 级优先级加提升的调度器,至今没有换成账。四问逐问比:何时换、换谁、各多少、在哪换;两边一样的,是约束的函数;两边不同的,追到「信不信事件能说明意图」这一件事上。最后拿 SQL Server 的 SQLOS 看用户态协作式调度为什么能绕开其中两条约束。'),
    'Comparison': ('评论家 → 哲学家(反思模式)',
      '对照完你手里有了判别法:一个设计是必然还是偶然,看另一套从头设计的系统在同一约束下是否也这么做。最后一篇换成哲学家,把前六篇的证据收成结论和方法:一张五元组表把十几个设计决策各过一遍「约束 → 代价 → 反事实 → 现实对照」的筛,逐条取消一条约束看谁反超,洞察各一节,三个别的领域里的同构(块层 IO 调度器、Go runtime、TCP 公平队列),然后把五步法离题套到 MySQL 线程池上,看这套问法能不能搬走。'),
}

def stage_lines(stage):
    return sum(1 for _ in open(f'stages/{stage}/{stage}.md', encoding='utf-8'))

soul = """> **"一个 CPU 面前有 N 个想跑的任务,内核每次到底按什么规则挑下一个?这条规则(权重 → 虚拟时间 → lag + deadline)是被哪些约束逼出来的、为什么 20 年里换了三代(O(1) → CFS → EEVDF)?多核和 cgroup 又把这条「挑人规则」扩展成了什么(谁把任务搬到别的核,容器的 CPU 上限怎么落到每个线程头上)?"**"""

bodies = {st: load(st) for st, *_ in stages}

parts = []
parts.append(f"""# Linux 的进程调度器 | atlas 综合长文

> 一份以 Linux 6.12 为样本、以「四问」为主轴的内核调度器设计笔记 —— 何时换 / 换谁 / 各多少 / 在哪换 · 八刀八条约束 · 三件事三个判据 · 1974 ~ 2024 五个转折点 · 三条主线源码追踪(EEVDF 挑人、多核均衡、cgroup 带宽)· 对照 Windows NT dispatcher · 五元组 + 五步法 + MySQL 线程池验证

---

## 导读地图

本文是 atlas 苏格拉底式技术教学的**最终融合产物**,围绕**第一性原理**展开,一篇一篇把 Linux 的进程调度器搞透,最终带走一套能离开内核领域使用的推导方法。本轮是**自动运行**:品味、灵魂问题与每篇的取舍由助手根据前两轮(Linux 文件 IO 全链路、Linux 进程全链路)的对话提炼后自决,记录在 `PROGRESS.md` 的「品味画像」与「总纲」里。

### 灵魂问题(贯穿全文)

{soul}

走完全文你会从七个角度回答它:它是什么(What)、为什么非得长成「打断点 + 账 + 每核一本 + 组一行 + 类栈」(Why)、每个机制具体怎么做(How)、谁在什么约束下这样做的(Origin)、6.12 源码里到底怎么走(Deep)、换一套血统会长成什么样(Comparison)、这套推导怎么带走(Synthesis)。

### 覆盖的 7 篇

| 篇 | 它讲什么 | 篇幅 |
|---|---|---|
| **What** | 它是什么:一句话定义、圆桌会类比、四问骨架、CPU 给的四样硬件、两个开场钩子(容器限 2 核 p99 抖 / PG 100 后端 + Redis 的 nice 与 taskset) | ~{stage_lines('01-what')} 行 |
| **Why** | 为什么必须存在:从「一核一队列先来先跑」起八刀,一刀一条,逼出 C1 ~ C8 | ~{stage_lines('02-why')} 行 |
| **How** | 大致怎么工作:每核一本账与类栈 → fair 账的四个数 → 标记与出口 → 多核三种搬人 → cgroup 带宽 → 硬保证,伪代码内核 | ~{stage_lines('03-how')} 行 |
| **Origin** | 是怎么来的:O(1)、RSDL / SD 与 CFS、学术线、带宽与 PELT、EEVDF、sched_ext,严格一手资料 | ~{stage_lines('04-origin')} 行 |
| **Deep** | 深度剖析:三条主线钉到 6.12 行号,三个判据,EEVDF 模拟器核对手算,反事实小试,唯一的 ns 时间线 | ~{stage_lines('05-deep')} 行 |
| **Comparison** | 横向对照:Windows NT dispatcher 的 32 级优先级 + 提升 / Job 对象 CPU 限额 / 理想处理器,按四问逐问比,再看 SQLOS | ~{stage_lines('06-comparison')} 行 |
| **Synthesis** | ★ 设计哲学与方法论:五元组 14 行过筛(必然 7 / 选择 5 / 偶然 2)、八次取消约束、24 条洞察与必保 11 条、三个同构(块层 IO 调度器 / Go GMP / fq_codel)、五步法 + MySQL 线程池演练、十年赌注(押 sched_ext 按负载换规则) | ~{stage_lines('07-synthesis')} 行 |

### 阅读路径建议

- **第一次接触调度器** → 顺读(What → Why → How → Origin → Deep → Comparison → Synthesis)
- **想快速建立心智** → 看 [What](#stage-what) + [Why](#stage-why)(约 40 分钟)
- **上一轮在 lag 上卡过** → 直接看 [How §3.4](#stage-how) 和 [Deep §2.4](#stage-deep),那里从零讲 lag 并用模拟器走表
- **只关心容器 CPU 限额为什么抖** → [What 钩子一](#stage-what) → [How §6](#stage-how) → [Deep §4](#stage-deep)
- **想横向对比** → 直接看 [Comparison](#stage-comparison)
- **想拿走方法论** → 直接看 [Synthesis](#stage-synthesis) §2 五元组、§7 五步法与 §7.6 线程池演练、§8 赌注(约 1 小时)

**全长**约 {{TOTAL_LINES}} 行、中文约 {{TOTAL_CJK}} 万字;深读约 6 小时,跳读约 1.5 小时。

### 全文导览

下面七篇按顺序展开,每两篇之间有一段过渡,做心智模式切换 —— 讲解员 → 论证者 → 实操员 → 讲故事的人 → 工程师 → 评论家 → 哲学家。每篇末尾都有「约束回扣」和「呼应你的问题」两节,把该篇内容钉回约束清单与灵魂问题;每篇的反问都改成了选择题,并紧跟《从头走一遍》的自答;《你上一轮的视角》小节继承你在上一轮里跟调度有关的原话。各篇内部的修订记录保留在 `stages/0X-*/0X-*.md` 里,这里不重复;全部待核项在文末统一核实并列表。

---

## 约束清单速查(C1 ~ C8)

{constraint_block()}
""")

for idx, (st, name, desc, col) in enumerate(stages):
    parts.append(f"""
---

<a id="stage-{name.lower()}" name="stage-{name.lower()}"></a>

# 📍 第{cn_num[idx]}篇:{name} — {desc}

{bodies[st].rstrip()}
""")
    if name in transitions:
        t, txt = transitions[name]
        parts.append(f"""
---

> **🔄 心智切换:{t}**
>
> {txt}
""")

if VERIFY and os.path.exists(VERIFY):
    parts.append('\n---\n\n' + open(VERIFY, encoding='utf-8').read().rstrip() + '\n')

parts.append("""
---

## 🚀 延伸阅读

本次留白的几块,各自都够开一个新话题(Claude Code 用 `/atlas <主题>`,Codex 用 `$atlas <主题>`):

- `/atlas 按CPU视角重切进程管理`:一颗 CPU 从上电起在用户态 / 内核态 / 中断上下文之间跳,进程只是它的记账单位 —— 本轮四问里的「何时换」只讲了出口,CPU 视角能把中断、软中断、抢占计数整个摊开。
- `/atlas sched_ext:用BPF写一个调度器`:本轮 Deep 附录只给了机制和数字;自己写一个按 LLC 分组的 DSQ 调度器、在 8 核机器上跑 mysqld + redis,是把「规则只看账」这个结论反过来验证一遍的最好办法。
- `/atlas Linux内存管理:页回收与swap`:cgroup 的 CPU 带宽讲完了,内存那一半(memory.max、LRU / MGLRU、kswapd 本身也是一个被调度的内核线程)是 C6·份额按组算 的另一个战场。
- `/atlas MySQL线程池与连接调度`:Synthesis 只在方法论层面把五步法套了一遍;thread_pool_size、stall_limit、high_prio_tickets 各自对应调度器哪个数,值得单独走一轮。
- `/atlas Go runtime的GMP调度器`:用户态 M:N 调度把内核的四问重做了一遍,但没有 tick(1.14 前)、没有 cgroup、没有 NUMA —— 看它在哪几条约束上作弊、在哪几条上吃亏。

## ❓ Q&A 钩子(开放问题)

读完之后,可以继续追问的几个口子:

1. EEVDF 把「急」压成了短 slice,sched_ext 又允许 BPF 整个替换 fair 类。十年后桌面、服务器、手机会不会跑的根本不是同一个挑人规则?如果会,C2·未来不可知 在三边的权重各是多少?
2. lag 在睡眠时被夹在 ±2 个 slice 内,这个数是 Peter 2023 年拍的。如果把它放开到 ±10 个 slice,redis 这种「醒 50 μs 睡 10 ms」的任务会得到什么、mysqld 会失去什么?有没有一个负载能证明 2 是错的?
3. cgroup 带宽按 100 ms 周期借还,所以 p99 抖动的粒度就是 100 ms。如果改成按 SCHED_DEADLINE 的 CBS 给整组做预算(Deep §4.5 候选),throttling 会消失还是换一种形状?
4. Windows NT 相信「I/O 完成」说明交互意图并给 +1 ~ +8 的提升;Linux 不信,只看账。两边各有 30 年的桌面口碑。有没有一个可复现的实验能判定哪边在「猜意图」这件事上是对的?
5. 周期均衡永远只是近似:两组 L3 之间要差多少才值得搬一个任务?`imbalance_pct = 117` 这个数在 2 路 NUMA 的 128 核机器上还对吗?谁来替它重新调?
""")

doc = ''.join(parts)
total_lines = doc.count('\n') + 1
cjk = len(re.findall(r'[一-鿿]', doc))
doc = doc.replace('{TOTAL_LINES}', str(total_lines)).replace('{TOTAL_CJK}', '%.1f' % (cjk / 10000))
open(f'{SHORT}-atlas.md', 'w', encoding='utf-8').write(doc)
print('lines', total_lines, 'cjk', cjk, 'figures', doc.count('!['))
