import re, sys
from pathlib import Path
from playwright.sync_api import sync_playwright
D = Path(sys.argv[1])
svgs = sorted(D.glob("stages/*/pics/*.svg"))
with sync_playwright() as p:
    b = p.chromium.launch()
    for s in svgs:
        t = s.read_text()
        t = re.sub(r'font-family="[^"]+"', 'font-family="Noto Sans CJK SC"', t)
        t = re.sub(r"font-family:\s*[^;\"']+", "font-family: Noto Sans CJK SC", t)
        vb = [float(x) for x in re.search(r'viewBox="([^"]+)"', t).group(1).split()]
        w, h = vb[2], vb[3]
        scale = 1920 / w
        pg = b.new_page(viewport={"width": int(w), "height": int(h)}, device_scale_factor=scale)
        pg.set_content(f'<html><body style="margin:0;background:white">{t.replace("<svg", "<svg style=\'display:block;width:%dpx;height:%dpx\'" % (w, h), 1)}</body></html>')
        pg.wait_for_timeout(300)
        out = D / "pics" / (s.stem + ".png")
        pg.screenshot(path=str(out), clip={"x": 0, "y": 0, "width": w, "height": h})
        pg.close(); print(out.name)
    b.close()
