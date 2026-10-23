"""Extract real encoded frames for scene-by-scene visual review."""
from pathlib import Path
import json
import math
import subprocess
import sys
from PIL import Image, ImageDraw

out = Path(__file__).resolve().parent
for ep in map(int, sys.argv[1:]):
    vmd, = out.glob(f'glibc-malloc-ep{ep}-*.vmd')
    scenes = json.loads(vmd.with_suffix('.scenes.json').read_text())
    target = out / 'logs' / f'frames-ep{ep}'
    target.mkdir(exist_ok=True)
    sheet = Image.new('RGB', (1800, math.ceil(len(scenes) / 3) * 362), '#f5f0e7')
    draw = ImageDraw.Draw(sheet)
    for j, scene in enumerate(scenes):
        timestamp = scene['start'] + (scene['end'] - scene['start']) * 0.67
        path = target / f'{scene["idx"]:02}-{scene["type"]}.png'
        subprocess.run(['ffmpeg', '-v', 'error', '-ss', str(timestamp), '-i',
                        str(vmd.with_suffix('.mp4')), '-frames:v', '1', '-y', str(path)], check=True)
        with Image.open(path) as frame:
            sheet.paste(frame.resize((600, 338)), ((j % 3) * 600, (j // 3) * 362))
        draw.text(((j % 3) * 600 + 8, (j // 3) * 362 + 340),
                  f'{scene["idx"]}: {scene["type"]} @ {timestamp:.1f}s', fill='#332b24')
    sheet.save(out / 'logs' / f'contact-ep{ep}.jpg', quality=92)
    print('FRAMES', ep, len(scenes), flush=True)
