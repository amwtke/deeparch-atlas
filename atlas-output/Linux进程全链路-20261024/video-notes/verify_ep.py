import json, subprocess, sys, hashlib
from pathlib import Path
D, base, rc, sb, sa = sys.argv[1:6]
D = Path(D); mp4 = D / f"{base}.mp4"
res = {"file": mp4.name, "render_rc": int(rc), "vmd_sha256": sb, "checks": {}}
if not mp4.exists():
    res["status"] = "FAIL"; print(json.dumps(res, ensure_ascii=False)); sys.exit(0)
pr = json.loads(subprocess.run(["ffprobe","-v","error","-show_streams","-show_format","-of","json",str(mp4)],capture_output=True,text=True).stdout)
v = [s for s in pr["streams"] if s["codec_type"]=="video"][0]; a = [s for s in pr["streams"] if s["codec_type"]=="audio"]
dur = float(pr["format"]["duration"]); res.update(duration_seconds=round(dur,2), bytes=mp4.stat().st_size, resolution=[v["width"],v["height"]], video=v["codec_name"], audio=a[0]["codec_name"] if a else None)
adur = float(a[0].get("duration", 0)) if a else 0
dec = subprocess.run(["ffmpeg","-v","error","-i",str(mp4),"-f","null","-"],capture_output=True,text=True)
sc = D / f"{base}.scenes.json"; srt = D / f"{base}.srt"
log = (D/"video-notes"/"logs"/f"render-{base.split('-')[2]}.log").read_text(errors="ignore")
res["checks"] = {"resolution_1920x1080": [v["width"],v["height"]]==[1920,1080], "audio_covers_video": adur >= dur - 1.0,
  "srt_present": srt.exists(), "scenes_sidecar": sc.exists(), "full_decode": dec.returncode==0 and not dec.stderr.strip(),
  "renderer_self_checks": "全部校验通过" in log, "vmd_unchanged_during_render": sb==sa}
res["mp4_sha256"] = hashlib.sha256(mp4.read_bytes()).hexdigest()
res["status"] = "PASS" if all(res["checks"].values()) and int(rc)==0 else "FAIL"
(D/"video-notes"/"logs"/f"{base}.verification.json").write_text(json.dumps(res, ensure_ascii=False, indent=2))
print(json.dumps({k:res[k] for k in ("file","status","duration_seconds")}, ensure_ascii=False))
