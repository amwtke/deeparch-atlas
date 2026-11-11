import re, sys, subprocess
from pathlib import Path
D = Path("/Users/jin.xiao/workshop/deeparch-atlas/atlas-output/linux的进程调度器-20261103")
vmd = Path(sys.argv[1]); t = vmd.read_text()
scenes = [s for s in re.split(r'\n---\n', t) if '[visual:' in s]
narr = []; issues = []
types = {}
for i, s in enumerate(scenes, 1):
    m = re.search(r'\[visual:\s*(\w+)', s); ty = m.group(1); types[ty] = types.get(ty, 0) + 1
    n = s.split('[narration]', 1)[1].strip() if '[narration]' in s else ''
    ex = re.search(r'\[example\](.*?)(?=\n\[narration\]|\Z)', s, re.S)
    narr.append(n + (ex.group(1) if ex else ''))
    if re.search(r'(?i)atlas|facetime|html_slide|\bcode\b|spotlight|adv_animation|statemap|recap|analogy|layers|timeline|ascii|场景类型|visual:', n): issues.append(f"S{i} narration 术语: {n[:40]}")
    if re.search(r'\*\*|`|^#', n, re.M): issues.append(f"S{i} narration markdown")
    vis = s.split('[narration]')[0]
    if ty not in ('code', 'code_explain') and re.search(r'[→①②③④⑤⑥⑦⑧⑨]', vis): issues.append(f"S{i} 画面豆腐字 {re.findall(r'[→①-⑨]', vis)[:3]}")
    if ty in ('code', 'code_explain'):
        title = re.search(r'\[visual:[^\]]*\]', s).group(0)
        body = s.split(']', 1)[1] if False else s[s.index(title)+len(title):]
        code = re.split(r'\n===HIGHLIGHT===|\n\[narration\]|\n\[sidebar\]|\n\[example\]', body)[0].strip('\n')
        if re.search(r'伪代码|示意|demo|演示', title): continue
        srcs = [p for p in (D/'video-notes'/'src').rglob('*') if p.is_file()] if (D/'video-notes'/'src').exists() else []
        txts = [p.read_text(errors='ignore') for p in srcs]
        ok = any(code in x for x in txts)
        if not ok:
            # line-by-line fallback (allow '...' elision lines)
            lines = [l for l in code.split('\n') if l.strip() and l.strip() not in ('...', '…', '/* ... */')]
            miss = [l for l in lines if not any(l in x for x in txts)]
            issues.append(f"S{i} 源码非连续子串（{title[:60]}），{len(miss)} 行找不到: {miss[:2]}")
chars = sum(len(re.sub(r'\s', '', x)) for x in narr)
print(f"{vmd.name}: {len(scenes)} 场景, 类型 {types}, 口播 {chars} 字, 估时 {(chars/5.4+len(scenes)*1.5)/60:.1f} min")
first = scenes[0]; last = scenes[-1]
print("首场:", re.search(r'\[visual:\s*\w+', first).group(0), first.split('\n')[first.split('\n').index([l for l in first.split('\n') if l.startswith('[visual')][0])+1][:30])
print("末场:", re.search(r'\[visual:\s*\w+', last).group(0), '|', last.split('[narration]')[-1].strip()[-60:])
for x in issues: print("  !", x)
print("ISSUES", len(issues))
