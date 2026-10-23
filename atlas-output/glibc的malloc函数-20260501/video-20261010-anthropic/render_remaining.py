"""Local serial render and independent integrity verification for this delivery."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

OUT = Path(__file__).resolve().parent
REPO = Path('/Users/jin.xiao/workshop/deeparch-video')


def checked(args, **kwargs):
    return subprocess.run(args, check=True, **kwargs)


def verify(vmd):
    mp4 = vmd.with_suffix('.mp4')
    probe = json.loads(checked(['ffprobe', '-v', 'error', '-show_format', '-show_streams',
                              '-of', 'json', str(mp4)], capture_output=True, text=True).stdout)
    duration = float(probe['format']['duration'])
    video = next(s for s in probe['streams'] if s['codec_type'] == 'video')
    audio = next(s for s in probe['streams'] if s['codec_type'] == 'audio')
    assert (video['width'], video['height']) == (1920, 1080)
    assert duration > 10 and float(audio['duration']) > duration - 1
    scenes = json.loads(vmd.with_suffix('.scenes.json').read_text())
    assert abs(duration - scenes[-1]['end']) < 0.2
    assert vmd.with_suffix('.srt').stat().st_size > 100
    checked(['ffmpeg', '-v', 'error', '-xerror', '-i', str(mp4), '-f', 'null', '-'],
            capture_output=True, text=True)
    log = (OUT / 'logs' / f'render-ep{vmd.stem.split("-ep")[1].split("-")[0]}.log').read_text()
    assert all('✓ [' + name + ']' in log for name in ['file_integrity', 'duration_check', 'audio_silence'])
    assert '全部校验通过（3 项）' in log
    result = dict(file=mp4.name, duration_seconds=duration, bytes=mp4.stat().st_size,
                  render_exit_code=0, full_decode='PASS', audio=audio['codec_name'],
                  video=video['codec_name'], resolution=[video['width'], video['height']],
                  scene_duration='PASS', renderer_checks='PASS',
                  vmd_sha256=hashlib.sha256(vmd.read_bytes()).hexdigest())
    (OUT / 'logs' / f'{vmd.stem}.verification.json').write_text(
        json.dumps(result, ensure_ascii=False, indent=2))
    print('VERIFIED', mp4.name, f'{duration / 60:.2f} min', flush=True)
    return result


if __name__ == '__main__':
    for ep in range(int(sys.argv[1]), int(sys.argv[2]) + 1):
        vmd, = OUT.glob(f'glibc-malloc-ep{ep}-*.vmd')
        before = hashlib.sha256(vmd.read_bytes()).hexdigest()
        print('RENDER', ep, vmd.name, time.strftime('%H:%M:%S'), flush=True)
        with (OUT / 'logs' / f'render-ep{ep}.log').open('w') as log:
            checked([str(REPO / 'deeparch-video'), str(vmd), str(vmd.with_suffix('.mp4')),
                     '--theme', 'anthropic', '--lint', 'strict', '--lang', 'zh'],
                    cwd=REPO, stdout=log, stderr=subprocess.STDOUT,
                    env={**os.environ, 'PYTHONUNBUFFERED': '1'})
        assert hashlib.sha256(vmd.read_bytes()).hexdigest() == before
        verify(vmd)
