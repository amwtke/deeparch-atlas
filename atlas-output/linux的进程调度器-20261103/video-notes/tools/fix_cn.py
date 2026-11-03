#!/usr/bin/env python3
"""Normalize bare constraint IDs (C1..C8) in prose to `Cn·短名`.
Skips: code fences, inline code, `#### Cn —` headings, table rows whose first cell is Cn,
ranges like `C1 ~ C8`, and IDs already followed by `·`.
Usage: fix_cn.py file.md [...]
"""
import re, sys
NAMES = {'1': '只在打断点换', '2': '未来不可知', '3': '份额与延迟两头要', '4': '挑人须便宜',
         '5': '核各自为政', '6': '份额按组算', '7': '有人要硬保证', '8': '核不等速且耗电'}
ID = re.compile(r'(?<![A-Za-z0-9_/#\-])C([1-8])(?![0-9·])')

def fix_segment(p):
    def rep(m):
        after = p[m.end():m.end() + 4]
        before = p[max(0, m.start() - 4):m.start()]
        if re.match(r'\s*[~～]', after) or re.search(r'[~～]\s*$', before):
            return m.group(0)
        return 'C%s·%s' % (m.group(1), NAMES[m.group(1)])
    return ID.sub(rep, p)

def fix_line(l):
    parts = re.split(r'(`[^`]*`)', l)
    return ''.join(p if p.startswith('`') else fix_segment(p) for p in parts)

for f in sys.argv[1:]:
    lines = open(f, encoding='utf-8').read().split('\n')
    fence = False; changed = 0; res = []
    for l in lines:
        if l.strip().startswith('```'):
            fence = not fence; res.append(l); continue
        if fence or l.startswith('#### C') or re.match(r'^\|\s*C[1-8]\s*\|', l):
            res.append(l); continue
        nl = fix_line(l)
        changed += (nl != l); res.append(nl)
    open(f, 'w', encoding='utf-8').write('\n'.join(res))
    print(f, 'lines changed', changed)
