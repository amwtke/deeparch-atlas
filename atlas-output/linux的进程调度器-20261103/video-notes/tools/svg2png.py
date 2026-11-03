import sys, re, glob
from pathlib import Path
from playwright.sync_api import sync_playwright
base = Path(sys.argv[1]); out = base / 'pics'; out.mkdir(exist_ok=True)
pat = sys.argv[2] if len(sys.argv) > 2 else '0[1-7]-*'
svgs = sorted(glob.glob(str(base / 'stages' / pat / 'pics' / '*.svg')))
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={'width': 1920, 'height': 1080})
    for svg in svgs:
        txt = open(svg, encoding='utf-8').read()
        m = re.search(r'viewBox="0 0 (\d+) (\d+)"', txt); w, h = int(m.group(1)), int(m.group(2))
        H = round(1920 * h / w)
        html = f'<html><body style="margin:0;background:#0a0c10">{txt}</body></html>'
        html = re.sub(r'<svg ', f'<svg style="width:1920px;height:{H}px;display:block" ', html, count=1)
        pg.set_viewport_size({'width': 1920, 'height': H}); pg.set_content(html); pg.wait_for_timeout(300)
        dst = out / (Path(svg).stem + '.png'); pg.screenshot(path=str(dst), full_page=False)
        print('✓', dst.name, f'{1920}x{H}')
    b.close()
