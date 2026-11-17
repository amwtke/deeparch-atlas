#!/usr/bin/env python3
"""把 src/logs/*.log(实跑日志原文)渲染成终端样式的 SVG,放进 pics/。

图里的每一行文字都逐字取自日志,本脚本只负责排版和上色,不改内容:
  - 提示符行(root@lima-cg:...# 或 $ 开头):提示符绿色,命令白色
  - ### 开头的行:步骤说明,橙色
  - 命中「关键证据」正则的输出行:蓝底高亮
  - 超过一屏宽的行按终端的方式折行

用法:python3 02-render-shots.py        (在 src/ 目录下,或任意目录)
"""
import html
import re
import unicodedata
from pathlib import Path

SRC = Path(__file__).resolve().parent
LOGS = SRC / "logs"
PICS = SRC.parent / "pics"

W = 1200            # viewBox 宽
PAD_X = 28
FONT = 14
CH = 8.43           # 14px 等宽字体的 ASCII 字宽
COLS = int((W - 2 * PAD_X) / CH)   # 一行能放多少列
LH = 21             # 行高
BAR = 34            # 标题栏高
TOP = BAR + 30
FOOT = 46

PROMPT_RE = re.compile(r"^(\S+@\S+:\S*# |\$ )(.*)$")


def disp_width(s: str) -> int:
    return sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in s)


def wrap(s: str, cols: int):
    """按显示宽度折行,行为同终端自动折行。"""
    out, cur, w = [], "", 0
    for c in s:
        cw = 2 if unicodedata.east_asian_width(c) in "WF" else 1
        if w + cw > cols:
            out.append(cur)
            cur, w = "", 0
        cur += c
        w += cw
    out.append(cur)
    return out


def render(name: str, title: str, lines, highlights=(), source=""):
    hl = [re.compile(p) for p in highlights]
    rows = []   # (kind, text, prompt_len)
    for raw in lines:
        raw = raw.rstrip("\n").expandtabs(8)
        m = PROMPT_RE.match(raw)
        if m:
            parts = wrap(raw, COLS)
            rows.append(("prompt", parts[0], len(m.group(1))))
            rows += [("cmd", p, 0) for p in parts[1:]]
        elif raw.startswith("### "):
            rows += [("note", p, 0) for p in wrap(raw, COLS)]
        else:
            kind = "hl" if any(h.search(raw) for h in hl) else "out"
            rows += [(kind, p, 0) for p in wrap(raw, COLS)]
    while rows and rows[0][1] == "":
        rows.pop(0)

    H = TOP + len(rows) * LH + FOOT
    o = []
    o.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
             f'font-family="JetBrains Mono, Consolas, monospace" font-size="{FONT}">')
    o.append(f'  <rect width="{W}" height="{H}" fill="#0a0c10"/>')
    o.append(f'  <rect x="8" y="8" width="{W-16}" height="{H-16}" rx="10" fill="#0d1117" stroke="#30363d"/>')
    o.append(f'  <path d="M8,{BAR+8} L{W-8},{BAR+8}" stroke="#30363d"/>')
    o.append('  <circle cx="30" cy="25" r="6" fill="#ff5f56"/><circle cx="50" cy="25" r="6" fill="#ffbd2e"/>'
             '<circle cx="70" cy="25" r="6" fill="#27c93f"/>')
    o.append(f'  <text x="{W/2}" y="30" text-anchor="middle" fill="#8892a0" font-size="13">{html.escape(title)}</text>')

    y = TOP
    for kind, text, plen in rows:
        if kind == "hl":
            o.append(f'  <rect x="{PAD_X-6}" y="{y-15}" width="{W-2*PAD_X+12}" height="{LH}" fill="#1e3a5f" opacity="0.55"/>')
        common = f'x="{PAD_X}" y="{y}" xml:space="preserve" style="white-space:pre"'
        if kind == "prompt":
            p, c = html.escape(text[:plen]), html.escape(text[plen:])
            o.append(f'  <text {common}><tspan fill="#88ff88">{p}</tspan><tspan fill="#e0e6f0">{c}</tspan></text>')
        else:
            fill = {"cmd": "#e0e6f0", "note": "#ffaa55", "hl": "#88c0ff", "out": "#a8b3c2"}[kind]
            o.append(f'  <text {common} fill="{fill}">{html.escape(text)}</text>')
        y += LH

    vmname = "cg-lab" if "cg-lab" in title else "cg"
    day = "2026-11-14" if any(k in name for k in ("cgmax", "cgpids", "cgio")) else "2026-11-13"
    foot = f"实跑留档 {day} · Lima 虚拟机 {vmname} · 日志原文 {source} · 提示符由留档脚本打印,命令与输出为真实执行结果"
    o.append(f'  <text x="{W/2}" y="{H-22}" text-anchor="middle" fill="#5c6675" font-size="11">{html.escape(foot)}</text>')
    o.append("</svg>")
    PICS.mkdir(exist_ok=True)
    (PICS / name).write_text("\n".join(o) + "\n", encoding="utf-8")
    print(f"{name}: {len(rows)} 行, {W}x{H}")


def read(*names):
    out = []
    for n in names:
        out += (LOGS / n).read_text(encoding="utf-8").splitlines()
    return out


VM = "limactl shell cg — root@lima-cg(Ubuntu 26.04.1 · Linux 7.0.0-38 · 4 核 8G)· 沙箱组 host01"
Q = r"^查询 "
C = r"^(这段时间|\d+ 秒内)的 CPU"

def shot(name, hl, title=VM):
    render(f"02-shot-{name}.svg", title, read(f"{name}.log"), hl, f"src/logs/{name}.log")

shot("env", [r"clickhouse-serv$", r"mysqld$", r"^3221225472$", r"^0::/host01$"])
shot("cpu0", [Q, C])
shot("nice", [Q, C])
shot("taskset", [Q, C, r"sched_setaffinity 成功"])
shot("setsid", [r"sleep 303$"])
shot("ulimit", [r"^MemoryError$", r"合计占住", r"VmRSS", r"Cannot allocate memory"])
shot("oom", [r"invoked oom-killer", r"Killed process \d+ \(db-sim\)", r"退出状态 = 137"])
shot("same", [r"copied", r"^Cached:", r"fork 失败", r"成功 fork 出"])
shot("cgcpu", [Q, C, r"^50000 100000$", r"^usage_usec", r"^nr_periods", r"^nr_throttled", r"^400$"])
shot("cgmem", [r"oom_kill \d+$", r"oom_memcg=/host01/report", r"db-sim$", r"\d report-w$"])
shot("cgescape", [r"0::/host01/report", r"Permission denied", r"^0$"])
shot("v1", [r"^\d+:(net_cls|freezer):/[AX]$", r"freezer:/[AB]$", r"is not set"])
shot("v2rule", [r"0::/host01/report$", r"Device or resource busy", r"^成功$"])
shot("cgweight", [Q, C, r"所在的核: \d", r"^max 100000$", r"^400$"])
shot("cgboth", [Q, C, r"所在的核: \d", r"^usage_usec", r"^400$"])
LAB = "limactl shell cg-lab — root@lima-cg-lab(Ubuntu 26.04.1 · Linux 7.0.0-38 · 4 核 4G,专用实验机)· 沙箱组 host01(1G)"
shot("cglow", [r"^(db|report) +合计", r"^memory\.(low|min|high|max)$", r"^cpu\.weight$", r"^pgsteal", r"^low 0$", r"oom-kill:", r"Killed process"], LAB)
shot("cgmax", [r"oom_memcg=/host01/report", r"Killed process \d+ \(report-w\)", r"oom_kill \d$", r"max \d+$", r"db-sim$"], LAB)
shot("cgpids", [r"fork 失败", r"成功 fork 出", r"pids\.(max|peak|events):"], LAB)
shot("cgio", [r"copied", r"^253:0 ", r"^vda "], LAB)
