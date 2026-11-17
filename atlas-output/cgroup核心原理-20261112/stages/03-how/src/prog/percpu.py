# percpu.py <秒>:这几秒里,每个 report-w 各自用了多少 CPU、待在哪颗核上
import os, sys, time
def snap():
    out = {}
    for p in os.listdir('/proc'):
        if not p.isdigit(): continue
        try: s = open(f'/proc/{p}/stat').read()
        except OSError: continue
        if s[s.index('(') + 1:s.rindex(')')] == 'report-w':
            f = s[s.rindex(')') + 2:].split()
            out[int(p)] = (int(f[11]) + int(f[12]), int(f[36]))     # CPU 时间(tick),所在的核
    return out
d = float(sys.argv[1]); a = snap(); t = time.monotonic(); time.sleep(d); b = snap(); d = time.monotonic() - t
tick = os.sysconf('SC_CLK_TCK'); rows = []
for pid in sorted(b):
    if pid in a: rows.append((b[pid][1], pid, (b[pid][0] - a[pid][0]) / tick / d * 100, a[pid][1]))
for core, pid, pct, core0 in sorted(rows):
    print(f"  核 {core}   pid {pid}   {pct:5.1f}%" + ("" if core == core0 else f"   (开始时在核 {core0})"))
by = {}
for core, pid, pct, _ in rows: by.setdefault(core, []).append(pct)
print("按核合计:" + "   ".join(f"核 {c}:{len(v)} 个进程共 {sum(v):.1f}%" for c, v in sorted(by.items())) + f"   总计 {sum(r[2] for r in rows):.1f}%")
