#!/usr/bin/env python3
"""Minimal, dependency-free Markdown -> dark-tech HTML converter for the atlas fused doc.
Usage: md2html.py <in.md> <out.html> <brand-subtitle>
- image-only lines become <figure> with the SVG inlined (block-level, never inside <p>)
- `<a id="X" name="X"></a>` lines assign id X to the next heading
- headings get sequential ids sec1.. unless pre-assigned
- `# 📍 ...` headings become h1.stage-card with colour class
"""
import sys, re, os, html

SRC, OUT, SUB = sys.argv[1], sys.argv[2], sys.argv[3]
base = os.path.dirname(os.path.abspath(SRC))
lines = open(SRC, encoding='utf-8').read().split('\n')

# ---------- inline ----------
def inline(s):
    codes = []
    def keep(m):
        codes.append('<code>%s</code>' % html.escape(m.group(1)))
        return '\x00%d\x00' % (len(codes) - 1)
    s = re.sub(r'`([^`]+)`', keep, s)
    s = html.escape(s, quote=False)
    s = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', lambda m: '<img alt="%s" src="%s">' % (m.group(1), m.group(2)), s)
    s = re.sub(r'\[([^\]]+)\]\(([^)\s]+)\)', lambda m: '<a href="%s">%s</a>' % (m.group(2), m.group(1)), s)
    s = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', s)
    s = re.sub(r'(?<![\w*])\*(?!\s)([^*\n]+?)(?<!\s)\*(?![\w*])', r'<em>\1</em>', s)
    s = re.sub(r'~~(.+?)~~', r'<del>\1</del>', s)
    s = re.sub(r'&lt;br\s*/?&gt;', '<br>', s)
    s = re.sub(r'\x00(\d+)\x00', lambda m: codes[int(m.group(1))], s)
    return s

# ---------- block helpers ----------
out = []
secn = 0
pending_id = None
stage_colour = 0

def hid():
    global secn, pending_id
    if pending_id:
        i, pending_id = pending_id, None
        return i
    secn += 1
    return 'sec%d' % secn

def is_table_sep(l):
    return re.match(r'^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$', l) is not None

def split_row(l):
    l = l.strip()
    if l.startswith('|'): l = l[1:]
    if l.endswith('|') and not l.endswith('\\|'): l = l[:-1]
    cells = re.split(r'(?<!\\)\|', l)
    return [c.replace('\\|', '|').strip() for c in cells]

def figure(alt, src):
    p = os.path.join(base, src)
    if src.endswith('.svg') and os.path.exists(p):
        svg = open(p, encoding='utf-8').read()
        svg = re.sub(r'^\s*<\?xml[^>]*\?>\s*', '', svg)
        return '<figure>%s<figcaption>%s</figcaption></figure>' % (svg, html.escape(alt))
    return '<figure><img alt="%s" src="%s"><figcaption>%s</figcaption></figure>' % (html.escape(alt), src, html.escape(alt))

def is_block_start(l):
    s = l.strip()
    return (s == '' or re.match(r'^#{1,6}\s', s) or s.startswith('>') or s.startswith('```')
            or re.match(r'^(-{3,}|\*{3,})$', s) or re.match(r'^(\s*)([-*+]|\d+\.)\s', l)
            or re.match(r'^!\[[^\]]*\]\([^)]+\)\s*$', s) or s.startswith('<a id=')
            or (s.startswith('|') and '|' in s[1:]))

def render_list(block):
    """block: list of (indent, marker, text) ; returns html"""
    res = []
    stack = []  # (indent, tag)
    for indent, marker, text in block:
        tag = 'ol' if marker[0].isdigit() else 'ul'
        while stack and indent < stack[-1][0]:
            res.append('</li></%s>' % stack.pop()[1])
        if stack and indent == stack[-1][0]:
            res.append('</li>')
        elif not stack or indent > stack[-1][0]:
            if stack: res[-1] = res[-1]  # keep
            res.append('<%s>' % tag)
            stack.append((indent, tag))
        res.append('<li>' + inline(text))
    while stack:
        res.append('</li></%s>' % stack.pop()[1])
    return ''.join(res)

i = 0
n = len(lines)
para = []

def flush_para():
    global para
    if para:
        out.append('<p>%s</p>' % inline(' '.join(x.strip() for x in para)))
        para = []

while i < n:
    l = lines[i]
    s = l.strip()
    m = re.match(r'^<a id="([^"]+)"', s)
    if m and s.endswith('</a>'):
        flush_para(); pending_id = m.group(1); i += 1; continue
    if s == '':
        flush_para(); i += 1; continue
    m = re.match(r'^(#{1,6})\s+(.*)$', s)
    if m:
        flush_para()
        lvl = len(m.group(1)); txt = m.group(2).strip()
        the_id = hid()
        if lvl == 1 and txt.startswith('📍'):
            out.append('<h1 id="%s" class="stage-card c%d">%s</h1>' % (the_id, stage_colour, inline(txt)))
            stage_colour += 1
        elif lvl == 1 and secn == 1 and the_id == 'sec1':
            out.append('<h1 id="%s" class="doc-title">%s</h1>' % (the_id, inline(txt)))
        elif lvl == 2 and (txt.startswith('🚀') or txt.startswith('❓') or txt.startswith('✅')):
            out.append('<h2 id="%s" class="tail-card">%s</h2>' % (the_id, inline(txt)))
        else:
            out.append('<h%d id="%s">%s</h%d>' % (lvl, the_id, inline(txt), lvl))
        i += 1; continue
    if s.startswith('```'):
        flush_para()
        lang = s[3:].strip(); buf = []; i += 1
        while i < n and not lines[i].strip().startswith('```'):
            buf.append(lines[i]); i += 1
        i += 1
        out.append('<pre><code class="lang-%s">%s</code></pre>' % (html.escape(lang), html.escape('\n'.join(buf))))
        continue
    if re.match(r'^(-{3,}|\*{3,})$', s):
        flush_para(); out.append('<hr>'); i += 1; continue
    m = re.match(r'^!\[([^\]]*)\]\(([^)]+)\)\s*$', s)
    if m:
        flush_para(); out.append(figure(m.group(1), m.group(2))); i += 1; continue
    if s.startswith('>'):
        flush_para(); buf = []
        while i < n and lines[i].strip().startswith('>'):
            buf.append(re.sub(r'^\s*>\s?', '', lines[i])); i += 1
        # recursive-lite: paragraphs split on blank lines, with inner lists
        inner = []; cur = []
        def fl():
            if cur: inner.append('<p>%s</p>' % inline(' '.join(cur))); cur.clear()
        for b in buf:
            if b.strip() == '':
                fl(); continue
            lm = re.match(r'^(\s*)([-*+]|\d+\.)\s+(.*)$', b)
            if lm:
                fl()
                if inner and inner[-1].startswith('<ul>') and inner[-1].endswith('</ul>'):
                    inner[-1] = inner[-1][:-5] + '<li>%s</li></ul>' % inline(lm.group(3))
                else:
                    inner.append('<ul><li>%s</li></ul>' % inline(lm.group(3)))
            else:
                cur.append(b.strip())
        fl()
        out.append('<blockquote>%s</blockquote>' % ''.join(inner)); continue
    if s.startswith('|') and i + 1 < n and is_table_sep(lines[i + 1]):
        flush_para()
        hdr = split_row(l); i += 2; rows = []
        while i < n and lines[i].strip().startswith('|'):
            rows.append(split_row(lines[i])); i += 1
        t = '<table><thead><tr>' + ''.join('<th>%s</th>' % inline(c) for c in hdr) + '</tr></thead><tbody>'
        for r in rows:
            r = r + [''] * (len(hdr) - len(r))
            t += '<tr>' + ''.join('<td>%s</td>' % inline(c) for c in r[:len(hdr)]) + '</tr>'
        t += '</tbody></table>'
        out.append(t); continue
    lm = re.match(r'^(\s*)([-*+]|\d+\.)\s+(.*)$', l)
    if lm:
        flush_para(); block = []
        while i < n:
            lm = re.match(r'^(\s*)([-*+]|\d+\.)\s+(.*)$', lines[i])
            if lm:
                block.append([len(lm.group(1).replace('\t', '    ')), lm.group(2), lm.group(3)]); i += 1
            elif lines[i].strip() != '' and lines[i].startswith((' ', '\t')) and block and not is_block_start(lines[i].strip()):
                block[-1][2] += ' ' + lines[i].strip(); i += 1  # lazy continuation
            elif lines[i].strip() == '' and i + 1 < n and re.match(r'^(\s*)([-*+]|\d+\.)\s+', lines[i + 1]):
                i += 1  # loose list, keep going
            else:
                break
        out.append(render_list(block)); continue
    # paragraph (lazy continuation until block start)
    para.append(l); i += 1
    while i < n and not is_block_start(lines[i]):
        para.append(lines[i]); i += 1
    flush_para()

body = '\n'.join(out)

# ---------- nav ----------
nav = []
title = re.search(r'<h1 id="sec1" class="doc-title">(.*?)</h1>', body).group(1)
for m in re.finditer(r'<h([12]) id="([^"]+)"(?: class="([^"]+)")?>(.*?)</h[12]>', body):
    lvl, hid_, cls, txt = m.groups()
    txt = re.sub(r'<[^>]+>', '', txt)
    if cls == 'doc-title': continue
    if cls and cls.startswith('stage-card'):
        nav.append('<a class="tl %s" href="#%s"><span class="dot"></span>%s</a>' % (cls.split()[1], hid_, txt))
    elif lvl == '2' and (txt.startswith('导读') or txt.startswith('约束清单速查') or txt.startswith('🚀') or txt.startswith('❓') or txt.startswith('✅')):
        if txt.startswith('✅') and nav and 'tl-sep' not in nav[-1]:
            nav.append('<div class="tl-sep"></div>')
        nav.append('<a class="tl c7" href="#%s"><span class="dot"></span>%s</a>' % (hid_, txt))
        if txt.startswith('约束清单速查'):
            nav.append('<div class="tl-sep"></div>')

CSS = """
:root{--bg:#0a0c10;--panel:#11161c;--line:#222a33;--tx:#c9d1d9;--mut:#8b949e;--hd:#e6edf3;
--c0:#4080c0;--c1:#c04040;--c2:#40c060;--c3:#c08040;--c4:#8040c0;--c5:#40b0c0;--c6:#c04080;--c7:#8b949e;}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{margin:0;background:var(--bg);color:var(--tx);
font-family:'Noto Sans SC',-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
line-height:1.85;font-size:16px;}
code,pre{font-family:'JetBrains Mono',Consolas,monospace;}
nav.timeline{position:fixed;top:0;left:0;width:240px;height:100vh;overflow-y:auto;
background:#0c0f14;border-right:1px solid var(--line);padding:26px 14px;}
.tl-brand{font-family:'JetBrains Mono',monospace;font-weight:700;font-size:20px;color:var(--hd);margin-bottom:22px;}
.tl-brand span{display:block;font-size:11px;color:var(--mut);font-weight:400;margin-top:4px;line-height:1.5}
a.tl{display:flex;align-items:center;gap:10px;color:var(--mut);text-decoration:none;
padding:8px 10px;border-radius:8px;font-size:13.5px;margin-bottom:3px;border-left:3px solid transparent;line-height:1.4}
a.tl:hover{background:var(--panel);color:var(--tx);}
a.tl.active{background:var(--panel);color:var(--hd);}
a.tl .dot{width:10px;height:10px;border-radius:50%;flex:0 0 auto;}
.tl.c0 .dot{background:var(--c0)} .tl.c1 .dot{background:var(--c1)} .tl.c2 .dot{background:var(--c2)}
.tl.c3 .dot{background:var(--c3)} .tl.c4 .dot{background:var(--c4)} .tl.c5 .dot{background:var(--c5)}
.tl.c6 .dot{background:var(--c6)} .tl.c7 .dot{background:var(--c7)}
.tl-sep{height:1px;background:var(--line);margin:10px 6px}
main{margin-left:240px;max-width:900px;padding:50px 56px 120px;}
h1,h2,h3,h4{color:var(--hd);line-height:1.4;scroll-margin-top:16px}
h1{font-size:28px;margin:54px 0 22px;font-weight:700;}
h1.doc-title{font-size:34px;margin-top:6px;border:0;padding:0;}
h1.stage-card,h2.tail-card{padding:14px 20px;border-radius:10px;background:var(--panel);border-left:6px solid var(--mut);font-size:24px;border-bottom:0}
h1.stage-card.c0{border-left-color:var(--c0)} h1.stage-card.c1{border-left-color:var(--c1)}
h1.stage-card.c2{border-left-color:var(--c2)} h1.stage-card.c3{border-left-color:var(--c3)}
h1.stage-card.c4{border-left-color:var(--c4)} h1.stage-card.c5{border-left-color:var(--c5)}
h1.stage-card.c6{border-left-color:var(--c6)}
h2{font-size:23px;margin:38px 0 14px;padding-bottom:7px;border-bottom:1px solid var(--line);}
h3{font-size:19px;margin:28px 0 12px;color:#b9c4d0;}
h4{font-size:16px;margin:22px 0 8px;color:#9fb0c0;font-family:'JetBrains Mono',monospace;}
p{margin:13px 0;}
a{color:#7fb2ff;}
strong{color:#fff;font-weight:600;}
code{background:#161b22;border:1px solid var(--line);border-radius:5px;padding:1px 6px;font-size:13.5px;color:#ffb07a;}
pre{background:#0d1117;border:1px solid var(--line);border-radius:10px;padding:14px 16px;overflow-x:auto;font-size:13px;line-height:1.6}
pre code{background:none;border:0;padding:0;color:#d2dae3;font-size:13px}
blockquote{margin:16px 0;padding:12px 18px;background:rgba(128,140,160,.07);
border-left:4px solid #4a5563;border-radius:0 8px 8px 0;color:#b8c2cd;}
blockquote p{margin:7px 0;}
ul,ol{padding-left:24px;margin:12px 0;} li{margin:7px 0;}
li>ul,li>ol{margin:4px 0}
hr{border:0;border-top:1px solid var(--line);margin:34px 0;}
table{border-collapse:collapse;width:100%;margin:18px 0;font-size:14px;display:block;overflow-x:auto;}
th,td{border:1px solid var(--line);padding:9px 12px;text-align:left;vertical-align:top;}
th{background:#1a212b;color:var(--hd);font-weight:600;}
tr:nth-child(even) td{background:rgba(255,255,255,.015);}
figure{margin:24px 0;text-align:center;background:#070a0e;border:1px solid var(--line);border-radius:10px;padding:14px;}
figure svg{max-width:100%;height:auto;display:block;margin:0 auto;}
figure img{max-width:100%}
figcaption{margin-top:10px;color:var(--mut);font-size:13px;}
del{color:var(--mut)}
@media(max-width:860px){nav.timeline{display:none}main{margin-left:0;padding:28px 18px}}
"""

page = """<!DOCTYPE html>
<html lang="zh-CN"><head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>%s</title>
<link rel="preconnect" href="https://fonts.googleapis.com"/>
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&family=Noto+Sans+SC:wght@400;500;700&display=swap" rel="stylesheet"/>
<style>%s</style></head>
<body>
<nav class="timeline">
<div class="tl-brand">atlas<span>%s</span></div>
%s
</nav>
<main>
%s
</main>
<script>
(function(){
  var links=[].slice.call(document.querySelectorAll('a.tl'));
  var targets=links.map(function(a){return document.getElementById(a.getAttribute('href').slice(1));});
  function upd(){
    var y=window.scrollY+120, cur=-1;
    for(var i=0;i<targets.length;i++){ if(targets[i]&&targets[i].offsetTop<=y) cur=i; }
    links.forEach(function(a,i){ a.classList.toggle('active',i===cur); });
  }
  window.addEventListener('scroll',upd,{passive:true}); upd();
})();
</script>
</body></html>
""" % (re.sub(r'<[^>]+>', '', title).replace(' | atlas 综合长文', ' | atlas'), CSS, SUB, '\n'.join(nav), body)
open(OUT, 'w', encoding='utf-8').write(page)
print('wrote', OUT, len(page), 'bytes;', body.count('<figure>'), 'figures;', secn, 'headings')
