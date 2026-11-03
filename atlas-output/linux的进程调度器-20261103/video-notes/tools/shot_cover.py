import sys
from playwright.sync_api import sync_playwright
src, out, dur = sys.argv[1], sys.argv[2], sys.argv[3]
html = open(src, encoding='utf-8').read().replace('DURATION', dur)
tmp = out + '.html'; open(tmp, 'w', encoding='utf-8').write(html)
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={'width':1920,'height':1080})
    pg.goto('file://' + tmp); pg.wait_for_timeout(800)
    pg.screenshot(path=out, full_page=False); b.close()
print('ok', out)
