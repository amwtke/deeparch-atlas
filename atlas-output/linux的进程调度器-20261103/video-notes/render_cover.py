import sys
from pathlib import Path
from playwright.sync_api import sync_playwright
D = Path(sys.argv[1]); dur = sys.argv[2]; photo = sys.argv[3]; out = sys.argv[4]
html = (D/"video-notes/cover-atlas.html").read_text().replace("DURATION", dur).replace("PHOTO", Path(photo).resolve().as_uri())
tmp = D/"video-notes/_cover_render.html"; tmp.write_text(html)
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width":1920,"height":1080})
    pg.goto(tmp.as_uri()); pg.wait_for_timeout(1200); pg.screenshot(path=out); b.close()
tmp.unlink(); print(out)
