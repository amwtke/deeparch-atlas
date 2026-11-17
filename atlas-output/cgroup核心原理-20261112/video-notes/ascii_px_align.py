"""按渲染器真实像素宽度重排 ascii 场景里的空白。

render_ascii_diagram 的字宽是固定的：等宽字符 13px，CJK / 全角 22px（不是 26px）。
作者按「中文占 2 列」用半角空格补齐，框线会越排越偏。本脚本保留每个非空白字符，
只把每段空白换成「全角空格 x f + 半角空格 x h」，使下一个字符尽量落回 列号 x 13px 的网格。

用法: ascii_px_align.py <列模型源 vmd> [--out <目标 vmd>]
输入必须是 video-notes/ascii-src/ 下的列模型文件（只用半角空格、中文按 2 列对齐）；
已重排过的文件不能再当输入。
"""
import re, sys, unicodedata
from pathlib import Path

BOX = "┌┐└┘├┤┬┴─│╔╗╚╝║═╠╣╦╩┼+|-"
ARROW = "→←↑↓▶▷►◄■□●○"
MONO, WIDE = 13, 22
STRUCT = "┌┐└┘├┤┬┴│┼▼▲"


def is_cjk(ch):
    cp = ord(ch)
    return ((0x4E00 <= cp <= 0x9FFF) or (0x3400 <= cp <= 0x4DBF) or (0xF900 <= cp <= 0xFAFF)
            or (0x3000 <= cp <= 0x303F) or (0xFF00 <= cp <= 0xFFEF) or (0x2E80 <= cp <= 0x2EFF)
            or (0xFE30 <= cp <= 0xFE4F))


def px(ch):
    if ch in BOX:
        return MONO
    if ch in ARROW or is_cjk(ch):
        return WIDE
    return MONO


def cols(ch):
    return 2 if unicodedata.east_asian_width(ch) in "WF" else 1


def best_gap(target):
    best = None
    for f in range(0, 60):
        for h in range(0, 100):
            w = MONO * h + WIDE * f
            if w < MONO:
                continue
            if w > target + WIDE:
                break
            key = (abs(w - target), f + h)
            if best is None or key < best[0]:
                best = (key, h, f)
    return best[1], best[2]


def relayout(line):
    """返回 (新行, 重排前各结构字符偏移, 重排后各结构字符偏移)，偏移 = 实际像素 - 原始列号 x 13"""
    out, x, x0, col, i, n = [], 0, 0, 0, 0, len(line)
    before, after = [], []
    while i < n:
        ch = line[i]
        if ch in " \u3000":
            j = i
            while j < n and line[j] in " \u3000":
                col += cols(line[j]); x0 += px(line[j]); j += 1
            if j >= n:
                break
            nxt = line[j]
            if (j - i) == 1 and ch == " " and nxt not in STRUCT and nxt not in BOX:
                h, f = 1, 0          # 词间单个空格原样保留，欠的像素留给后面的宽空白补
            else:
                h, f = best_gap(col * MONO - x)
            out.append("\u3000" * f + " " * h)
            x += MONO * h + WIDE * f
            i = j
        else:
            if ch in STRUCT:
                before.append(x0 - col * MONO); after.append(x - col * MONO)
            out.append(ch); x += px(ch); x0 += px(ch); col += cols(ch); i += 1
    return "".join(out), before, after


def process(text):
    lines = text.split("\n")
    out, in_ascii, stats = [], False, []
    for ln in lines:
        if ln.startswith("[visual:"):
            in_ascii = bool(re.match(r"\[visual:\s*ascii\b", ln))
            out.append(ln); continue
        if in_ascii and (ln.startswith("[") or ln.strip() == "---"):
            in_ascii = False
        if in_ascii and ln.strip():
            new, eb, ea = relayout(ln)
            before = max([abs(e) for e in eb] or [0])
            after = max([abs(e) for e in ea] or [0])
            stats.append((before, after, new))
            out.append(new)
        else:
            out.append(ln)
    return "\n".join(out), stats


if __name__ == "__main__":
    p = Path(sys.argv[1]); t = p.read_text()
    new, stats = process(t)
    worst_b = max([s[0] for s in stats] or [0]); worst_a = max([s[1] for s in stats] or [0])
    bad = [s for s in stats if s[1] > 6]
    print(f"{p.name}: {len(stats)} ascii 行, 最大偏移 {worst_b}px -> {worst_a}px, 仍 >6px 的行 {len(bad)}")
    for b in bad[:8]:
        print("   ", b[1], repr(b[2][:70]))
    if "--out" in sys.argv:
        Path(sys.argv[sys.argv.index("--out") + 1]).write_text(new); print("   written")
