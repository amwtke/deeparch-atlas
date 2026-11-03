"""Replace @@SRC file.c a-b[,c-d]@@ placeholders with verbatim lines from video-notes/src/linux-6.12/kernel/sched/."""
import re, sys
from pathlib import Path
vmd = Path(sys.argv[1]); SRC = Path(__file__).parent / 'src' / 'linux-6.12' / 'kernel' / 'sched'
txt = vmd.read_text()
def rep(m):
    f, ranges = m.group(1), m.group(2)
    lines = SRC.joinpath(f).read_text().split('\n')
    out = []
    for i, r in enumerate(ranges.split(',')):
        a, b = map(int, r.split('-'))
        if i: out.append('\t/* ... */')
        out.extend(lines[a-1:b])
    return '\n'.join(out)
new = re.sub(r'@@SRC (\S+) ([\d,\-]+)@@', rep, txt)
vmd.write_text(new); print('spliced', txt.count('@@SRC'), 'blocks')
