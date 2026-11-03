#!/usr/bin/env python3
"""
05-eevdf-sim.py — 按 Linux v6.12 kernel/sched/fair.c 的 fair 类规则做的最小单核模拟器。
只依赖标准库。用法:
    python3 -I 05-eevdf-sim.py how36       # How §3.6 三任务五拍场景(默认)
    python3 -I 05-eevdf-sim.py how14       # How §14 反问:redis 带 lag 醒来能连跑多久
    python3 -I 05-eevdf-sim.py long        # 300 ms 长跑:份额与权重对账
    python3 -I 05-eevdf-sim.py deep26      # Deep §2.6 反问:B 睡 20 ms 醒来 lag 记成多少、能否抢 A

对应的 6.12 函数(行号见 05-deep.md §2.2):
    calc_delta_fair      fair.c:289   vruntime 增量 = delta × 1024 / weight
    avg_vruntime_add/sub fair.c:620/630  两个累加器
    avg_vruntime         fair.c:651   V = min_vruntime + avg_vruntime / avg_load(含 curr)
    entity_lag           fair.c:692   lag 夹在 ±max(2·slice, TICK_NSEC)(虚拟单位)
    update_entity_lag    fair.c:702   出队时存 vlag
    vruntime_eligible    fair.c:726   V ≥ v_i,用乘法避免除法
    update_min_vruntime  fair.c:761   min_vruntime 只前进,前进时修正 avg_vruntime
    pick_eevdf           fair.c:907   eligible 里 deadline 最早;RUN_TO_PARITY 护 curr
    update_deadline      fair.c:1007  跑满 slice 才推 deadline,返回 true 表示该换人
    did/do_preempt_short fair.c:1166/1177  PREEMPT_SHORT
    update_curr          fair.c:1216  记账
    place_entity         fair.c:5266  lag 守恒放大:vl_i = (W + w_i)·vl'_i / W
    enqueue_entity       fair.c:5382
    dequeue_entity       fair.c:5476  DELAY_DEQUEUE:超支的睡眠者留在树上
    set_next_entity      fair.c:5560  HACK:vlag = deadline 作 slice 保护标记
    put_prev_entity      fair.c:5638
    requeue_delayed_entity fair.c:6919
    check_preempt_wakeup_fair fair.c:8764  唤醒抢占 = 放回后再挑一次
    sched_prio_to_weight core.c:10012
"""
import sys

NSEC_PER_MSEC = 1_000_000
TICK_NSEC = 4 * NSEC_PER_MSEC           # CONFIG_HZ = 250
BASE_SLICE = 3 * NSEC_PER_MSEC          # 8 核:0.75 ms × (1 + ilog2(8)) = 3 ms
NICE_0_LOAD = 1024
PLACE_LAG = RUN_TO_PARITY = PREEMPT_SHORT = DELAY_DEQUEUE = DELAY_ZERO = True

sched_prio_to_weight = [
    88761, 71755, 56483, 46273, 36291, 29154, 23254, 18705, 14949, 11916,
    9548, 7620, 6100, 4904, 3906, 3121, 2501, 1991, 1586, 1277,
    1024, 820, 655, 526, 423, 335, 272, 215, 172, 137,
    110, 87, 70, 56, 45, 36, 29, 23, 18, 15]


def nice_to_weight(nice):
    return sched_prio_to_weight[nice + 20]


def div_s64(a, b):  # C 的除法:向零截断
    q = abs(a) // abs(b)
    return q if (a >= 0) == (b > 0) else -q


class SE:
    def __init__(self, name, nice, vruntime, slice_ns=BASE_SLICE, custom=False):
        self.name = name
        self.weight = nice_to_weight(nice)
        self.vruntime = vruntime
        self.slice = slice_ns
        self.custom_slice = custom
        self.deadline = 0
        self.vlag = 0
        self.on_rq = False
        self.sched_delayed = False
        self.exec_start = 0
        self.sum_exec = 0
        self.seq = 0

    def calc_delta_fair(self, delta):           # fair.c:289
        if self.weight != NICE_0_LOAD:
            return delta * NICE_0_LOAD // self.weight
        return delta


class CfsRq:
    def __init__(self, min_vruntime):
        self.min_vruntime = min_vruntime
        self.avg_vruntime = 0      # Σ (v_i − min_vruntime) × w_i,树上实体,不含 curr
        self.avg_load = 0          # Σ w_i
        self.tree = []             # 按 deadline 排(红黑树的等价物)
        self.curr = None
        self.nr_running = 0
        self.clock = 0
        self.need_resched = False
        self.seq = 0
        self.log = []

    # ---- 累加器 ----
    def key(self, se):
        return se.vruntime - self.min_vruntime

    def __enqueue_entity(self, se):             # fair.c:852 + avg_vruntime_add
        self.avg_vruntime += self.key(se) * se.weight
        self.avg_load += se.weight
        self.seq += 1
        se.seq = self.seq
        self.tree.append(se)
        self.tree.sort(key=lambda e: (e.deadline, e.seq))

    def __dequeue_entity(self, se):             # fair.c:861 + avg_vruntime_sub
        self.avg_vruntime -= self.key(se) * se.weight
        self.avg_load -= se.weight
        self.tree.remove(se)

    def avg_vruntime_update(self, delta):        # fair.c:640
        self.avg_vruntime -= self.avg_load * delta

    def V(self):                                 # avg_vruntime(), fair.c:651
        avg, load = self.avg_vruntime, self.avg_load
        c = self.curr
        if c and c.on_rq:
            avg += self.key(c) * c.weight
            load += c.weight
        if load:
            if avg < 0:
                avg -= (load - 1)
            avg = div_s64(avg, load)
        return self.min_vruntime + avg

    def vruntime_eligible(self, vruntime):       # fair.c:726
        avg, load = self.avg_vruntime, self.avg_load
        c = self.curr
        if c and c.on_rq:
            avg += self.key(c) * c.weight
            load += c.weight
        return avg >= (vruntime - self.min_vruntime) * load

    def eligible(self, se):
        return self.vruntime_eligible(se.vruntime)

    def entity_lag(self, V, se):                 # fair.c:692
        vlag = V - se.vruntime
        limit = se.calc_delta_fair(max(2 * se.slice, TICK_NSEC))
        return max(-limit, min(limit, vlag))

    def update_entity_lag(self, se):             # fair.c:702
        se.vlag = self.entity_lag(self.V(), se)

    def update_min_vruntime(self):               # fair.c:761
        c = self.curr
        vruntime = self.min_vruntime
        if c:
            if c.on_rq:
                vruntime = c.vruntime
            else:
                c = None
        if self.tree:
            tmin = min(e.vruntime for e in self.tree)
            vruntime = tmin if not c else min(vruntime, tmin)
        delta = vruntime - self.min_vruntime      # __update_min_vruntime, fair.c:747
        if delta > 0:
            self.avg_vruntime_update(delta)
            self.min_vruntime = vruntime

    # ---- 记账 ----
    def update_deadline(self, se):               # fair.c:1007
        if se.vruntime - se.deadline < 0:
            return False
        if not se.custom_slice:
            se.slice = BASE_SLICE
        se.deadline = se.vruntime + se.calc_delta_fair(se.slice)
        return True

    def did_preempt_short(self, curr):           # fair.c:1166
        if not PREEMPT_SHORT or curr.vlag == curr.deadline:
            return False
        return not self.eligible(curr)

    def do_preempt_short(self, pse, se):         # fair.c:1177
        if not PREEMPT_SHORT or pse.slice >= se.slice or not self.eligible(pse):
            return False
        if pse.deadline < se.deadline:
            return True
        return not self.eligible(se)

    def update_curr(self):                       # fair.c:1216
        c = self.curr
        if c is None:
            return
        delta = self.clock - c.exec_start
        if delta <= 0:
            return
        c.exec_start = self.clock
        c.sum_exec += delta
        c.vruntime += c.calc_delta_fair(delta)
        resched = self.update_deadline(c)
        self.update_min_vruntime()
        if self.nr_running == 1:
            return
        if resched or self.did_preempt_short(c):
            self.need_resched = True

    # ---- 入队 / 出队 ----
    def place_entity(self, se, initial=False):   # fair.c:5266
        V = self.V()
        if not se.custom_slice:
            se.slice = BASE_SLICE
        vslice = se.calc_delta_fair(se.slice)
        lag = 0
        if PLACE_LAG and self.nr_running:
            lag = se.vlag
            load = self.avg_load
            if self.curr and self.curr.on_rq:
                load += self.curr.weight
            lag = lag * (load + se.weight)
            lag = div_s64(lag, load) if load else lag
        se.vruntime = V - lag
        if initial:
            vslice //= 2
        se.deadline = se.vruntime + vslice

    def enqueue_entity(self, se, initial=False): # fair.c:5382(唤醒路径,se != curr)
        self.update_curr()
        self.place_entity(se, initial)
        self.nr_running += 1
        self.__enqueue_entity(se)
        se.on_rq = True

    def dequeue_entity(self, se, sleep=True):    # fair.c:5476
        self.update_curr()
        if DELAY_DEQUEUE and sleep and not self.eligible(se):
            se.sched_delayed = True              # 留在树上继续被 V 甩
            return False
        self.update_entity_lag(se)
        if se is not self.curr:
            self.__dequeue_entity(se)
        se.on_rq = False
        self.nr_running -= 1
        self.update_min_vruntime()
        return True

    def finish_delayed_dequeue(self, se):        # fair.c:5468
        se.sched_delayed = False
        if DELAY_ZERO and se.vlag > 0:
            se.vlag = 0

    def requeue_delayed_entity(self, se):        # fair.c:6919
        if DELAY_ZERO:
            self.update_entity_lag(se)
            if se.vlag > 0:
                self.nr_running -= 1
                if se is not self.curr:
                    self.__dequeue_entity(se)
                se.vlag = 0
                self.place_entity(se)
                if se is not self.curr:
                    self.__enqueue_entity(se)
                self.nr_running += 1
        se.sched_delayed = False

    def set_next_entity(self, se):               # fair.c:5560
        if se.on_rq:
            self.__dequeue_entity(se)
            se.vlag = se.deadline                 # HACK:slice 保护标记
        se.exec_start = self.clock
        self.curr = se

    def put_prev_entity(self, prev):             # fair.c:5638
        if prev.on_rq:
            self.update_curr()
            self.__enqueue_entity(prev)
        self.curr = None

    # ---- 挑人 ----
    def pick_eevdf(self):                        # fair.c:907
        curr = self.curr
        first = self.tree[0] if self.tree else None
        if self.nr_running == 1:
            return curr if (curr and curr.on_rq) else first
        if curr and (not curr.on_rq or not self.eligible(curr)):
            curr = None
        if RUN_TO_PARITY and curr and curr.vlag == curr.deadline:
            return curr
        best = None
        for se in self.tree:                     # 树按 deadline 排;增广搜索等价于"第一个 eligible"
            if self.eligible(se):
                best = se
                break
        if best is None or (curr and curr.deadline < best.deadline):
            best = curr
        return best

    def pick_next_entity(self):                  # fair.c:5613
        se = self.pick_eevdf()
        if se and se.sched_delayed:              # 延迟出队的人被挑中 = 真正出队
            self.update_entity_lag(se)
            self.__dequeue_entity(se)
            se.on_rq = False
            self.nr_running -= 1
            self.update_min_vruntime()
            self.finish_delayed_dequeue(se)
            return None
        return se

    def check_preempt_wakeup_fair(self, pse):    # fair.c:8764
        se = self.curr
        if se is None or self.need_resched:
            return
        self.update_curr()
        if self.do_preempt_short(pse, se) and se.vlag == se.deadline:
            se.vlag = se.deadline + 1
        if self.pick_eevdf() is pse:
            self.need_resched = True

    def schedule(self):                          # __schedule → pick_task_fair 的单层版本
        prev = self.curr
        if prev is not None:
            self.put_prev_entity(prev)
        while True:
            nxt = self.pick_next_entity()
            if nxt is not None or not self.tree:
                break
        if nxt is not None:
            self.set_next_entity(nxt)
        self.need_resched = False
        return nxt

    # ---- 展示 ----
    def row(self, ents):
        V = self.V()
        cells = []
        for e in ents:
            if not e.on_rq:
                cells.append(f"{e.name:8s} 睡 vlag={e.vlag/NSEC_PER_MSEC:+.3f}")
                continue
            lag = (V - e.vruntime) / NSEC_PER_MSEC
            flag = "*" if e is self.curr else ("d" if e.sched_delayed else " ")
            cells.append(f"{e.name:8s}{flag} v={e.vruntime/NSEC_PER_MSEC:9.3f} lag={lag:+7.3f} dl={e.deadline/NSEC_PER_MSEC:9.3f}")
        return f"V={V/NSEC_PER_MSEC:9.3f} | " + " | ".join(cells)


def run(rq, ents, events, until, verbose_every_tick=True):
    """events: list of (t_ns, kind, se) kind ∈ {'wake'}; 睡眠由 se.burst 决定。"""
    t = 0
    ticks = [k * TICK_NSEC for k in range(1, until // TICK_NSEC + 1)]
    wakes = sorted(events)
    sleeps = {}   # se -> absolute time it will block
    rq.clock = 0
    picked = rq.schedule()
    print(f"t=  0.000 ms  初始挑人 → {picked.name if picked else '-'}")
    print(" " * 14 + rq.row(ents))
    if picked is not None and getattr(picked, "burst", None):
        sleeps[picked] = t + picked.burst
    while True:
        nt = min([ticks[0] if ticks else until + 1,
                  wakes[0][0] if wakes else until + 1,
                  min(sleeps.values()) if sleeps else until + 1])
        if nt > until:
            break
        t = nt
        rq.clock = t
        what = []
        # 1) 阻塞
        for se, ts in list(sleeps.items()):
            if ts == t and se is rq.curr:
                what.append(f"{se.name} 算完 {se.burst/1000:.0f} μs 要睡")
                real = rq.dequeue_entity(se, sleep=True)
                what.append("真出队" if real else "DELAY_DEQUEUE 留树上")
                del sleeps[se]
                rq.need_resched = True
        # 2) tick
        if ticks and ticks[0] == t:
            ticks.pop(0)
            before = rq.need_resched
            rq.update_curr()                     # task_tick_fair → entity_tick → update_curr
            what.append("tick" + (" → 标记" if rq.need_resched and not before else ""))
        # 3) 唤醒
        while wakes and wakes[0][0] == t:
            _, _, se = wakes.pop(0)
            if se.sched_delayed:
                rq.requeue_delayed_entity(se)
                what.append(f"{se.name} 醒(延迟出队中 → requeue)")
            else:
                rq.enqueue_entity(se)
                what.append(f"{se.name} 醒 place_entity")
            rq.check_preempt_wakeup_fair(se)
            if rq.need_resched:
                what.append("唤醒抢占 → 标记")
        # 4) 出口:有标记就换人
        if rq.need_resched or rq.curr is None:
            prev = rq.curr
            nxt = rq.schedule()
            if nxt is not prev:
                what.append(f"换人 → {nxt.name if nxt else '-'}")
                if nxt is not None and getattr(nxt, "burst", None):
                    sleeps[nxt] = t + nxt.burst
            else:
                what.append(f"重挑还是 {nxt.name}")
        if what and (verbose_every_tick or any(k in " ".join(what) for k in ("换人", "醒", "睡"))):
            print(f"t={t/NSEC_PER_MSEC:7.3f} ms  " + ";".join(what))
            print(" " * 14 + rq.row(ents))
    rq.clock = until
    rq.update_curr()
    return rq


def scenario_how36(until_ms=20, verbose=True):
    print("=== How §3.6:mysqld#3(nice 0) + xz(nice 19) 在树上,redis(nice -10) 睡着 vlag=+0.50 ms,t=10 ms 醒来算 50 μs ===")
    base = 1200 * NSEC_PER_MSEC
    rq = CfsRq(min_vruntime=base)
    m = SE("mysqld#3", 0, base)
    x = SE("xz", 19, base)
    r = SE("redis", -10, base)
    r.burst = 50_000
    r.vlag = 500_000
    for e in (m, x):
        e.deadline = e.vruntime + e.calc_delta_fair(BASE_SLICE)   # 相当于已经 place 过
        rq.nr_running += 1
        rq._CfsRq__enqueue_entity(e)
        e.on_rq = True
    run(rq, (m, x, r), [(10 * NSEC_PER_MSEC, "wake", r)], until_ms * NSEC_PER_MSEC, verbose)
    return rq, (m, x, r)


def scenario_how14():
    print("=== How §14:redis(nice -10) 醒来时 lag 为正,核上只有 mysqld#3 在跑;redis 醒后不睡,看它连跑多久 ===")
    for label, vlag in (("按题目 +4.000 ms(不夹紧,直接赋值)", 4_000_000), ("按 entity_lag 夹紧 +0.643 ms", 643_000)):
        base = 1200 * NSEC_PER_MSEC
        rq = CfsRq(min_vruntime=base)
        m = SE("mysqld#3", 0, base)
        r = SE("redis", -10, base)
        r.vlag = vlag
        m.deadline = m.vruntime + m.calc_delta_fair(BASE_SLICE)
        rq.nr_running += 1
        rq._CfsRq__enqueue_entity(m)
        m.on_rq = True
        print(f"--- {label} ---")
        rq.clock = 0
        rq.schedule()
        rq.clock = 1 * NSEC_PER_MSEC              # mysqld 先跑了 1 ms
        rq.update_curr()
        rq.enqueue_entity(r)
        rq.check_preempt_wakeup_fair(r)
        print(f"t=  1.000 ms  redis 醒 place_entity;唤醒抢占{'成立' if rq.need_resched else '不成立'}")
        print(" " * 14 + rq.row((m, r)))
        rq.schedule()
        t = 1 * NSEC_PER_MSEC
        first_switch = None
        tick_no = 0
        while t < 120 * NSEC_PER_MSEC:
            t += TICK_NSEC
            rq.clock = t
            rq.update_curr()
            tick_no += 1
            if rq.need_resched:
                prev = rq.curr
                nxt = rq.schedule()
                if nxt is not prev and first_switch is None:
                    first_switch = t
                    print(f"t={t/NSEC_PER_MSEC:7.3f} ms  tick → 标记 → 换人 → {nxt.name}(redis 连跑了 {(t - NSEC_PER_MSEC)/NSEC_PER_MSEC:.0f} ms)")
                    print(" " * 14 + rq.row((m, r)))
                    break
            if tick_no % 4 == 0:
                print(f"t={t/NSEC_PER_MSEC:7.3f} ms  tick(重挑还是 {rq.curr.name})")
                print(" " * 14 + rq.row((m, r)))
        if first_switch is None:
            print("120 ms 内没换人")


def scenario_long():
    print("=== 300 ms 长跑:mysqld#3 + xz 常驻,redis 每 10 ms 醒一次算 50 μs;只打印换人事件,最后对账份额 ===")
    base = 1200 * NSEC_PER_MSEC
    rq = CfsRq(min_vruntime=base)
    m = SE("mysqld#3", 0, base)
    x = SE("xz", 19, base)
    r = SE("redis", -10, base)
    r.burst = 50_000
    r.vlag = 500_000
    for e in (m, x):
        e.deadline = e.vruntime + e.calc_delta_fair(BASE_SLICE)
        rq.nr_running += 1
        rq._CfsRq__enqueue_entity(e)
        e.on_rq = True
    wakes = [(k * 10 * NSEC_PER_MSEC, "wake", r) for k in range(1, 30)]
    until = 300 * NSEC_PER_MSEC
    run(rq, (m, x, r), wakes, until, verbose_every_tick=False)
    tot = sum(e.sum_exec for e in (m, x, r))
    print(f"--- 300 ms 对账(实际跑的真实时间 / 占比;xz 与 mysqld 争抢时按权重应为 15 : 1024 = 1.4% : 98.6%)---")
    for e in (m, x, r):
        print(f"{e.name:8s} {e.sum_exec/NSEC_PER_MSEC:8.3f} ms  {100*e.sum_exec/tot:5.1f}%")


def scenario_deep26():
    print("=== Deep §2.6:两个 nice 0 任务 A、B。B 睡前 lag +20 ms(未夹紧的理论值),睡 20 ms;A 独占。B 醒来:lag 记成多少?能否立刻抢 A? ===")
    base = 1200 * NSEC_PER_MSEC
    rq = CfsRq(min_vruntime=base)
    a = SE("A", 0, base)
    b = SE("B", 0, base)
    a.deadline = a.vruntime + a.calc_delta_fair(BASE_SLICE)
    rq.nr_running += 1
    rq._CfsRq__enqueue_entity(a)
    a.on_rq = True
    rq.clock = 0
    rq.schedule()
    # B 睡下去那一刻的 lag:直接走 entity_lag 看夹紧
    V = rq.V()
    b.vruntime = V - 20 * NSEC_PER_MSEC
    raw = (V - b.vruntime) / NSEC_PER_MSEC
    b.vlag = rq.entity_lag(V, b)
    print(f"B 睡下去:理论 lag = {raw:+.3f} ms,entity_lag 夹在 ±max(2×3 ms, 4 ms) = ±6 ms → 存下 vlag = {b.vlag/NSEC_PER_MSEC:+.3f} ms")
    for t_ms in (4, 8, 12, 16, 20):
        rq.clock = t_ms * NSEC_PER_MSEC
        rq.update_curr()
        rq.need_resched = False               # A 独占,update_curr 的 nr_running==1 提前返回
    rq.clock = 20 * NSEC_PER_MSEC
    rq.enqueue_entity(b)
    rq.check_preempt_wakeup_fair(b)
    print(f"t= 20.000 ms  B 醒 place_entity;A 跑了 20 ms;唤醒抢占{'成立' if rq.need_resched else '不成立'}")
    print(" " * 14 + rq.row((a, b)))
    nxt = rq.schedule()
    print(f"              出口挑人 → {nxt.name}")
    t = 20 * NSEC_PER_MSEC
    for _ in range(6):
        t += TICK_NSEC
        rq.clock = t
        rq.update_curr()
        tag = "tick"
        if rq.need_resched:
            prev = rq.curr
            nxt = rq.schedule()
            tag += f" → 标记 → {'换人 → ' + nxt.name if nxt is not prev else '重挑还是 ' + nxt.name}"
        print(f"t={t/NSEC_PER_MSEC:7.3f} ms  {tag}")
        print(" " * 14 + rq.row((a, b)))


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "how36"
    {"how36": scenario_how36, "how14": scenario_how14, "long": scenario_long, "deep26": scenario_deep26}[which]()
