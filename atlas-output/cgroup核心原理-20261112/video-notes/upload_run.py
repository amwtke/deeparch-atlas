"""B 站多 P 上传：8 个 mp4 作为 1 个稿件的 8 个分 P。先写文件再跑，输出直接重定向到日志。
用法: venv/bin/python upload_run.py <D> "<稿件标题>"  > logs/upload.log 2>&1
"""
import sys, os, json, hashlib, datetime
from pathlib import Path
sys.path.insert(0, "/Users/jin.xiao/workshop/deeparch-video/scripts")
import bili_upload

D = Path(sys.argv[1]); title = sys.argv[2]
B = "cgroup"
PARTS = [
    ("ep0-toc", "P0 目录：三个问题和七集路线"),
    ("ep1-what", "P1 What：一个组就是一个目录，限额是谁写进去的"),
    ("ep2-why", "P2 Why：老工具为什么管不住，五条约束怎么来的"),
    ("ep3-how", "P3 How：五个接入点，超限以后内核怎么处理"),
    ("ep4-origin", "P4 Origin：2006 到 2016，从多棵树到一棵树"),
    ("ep5-deep", "P5 Deep：Linux 7.0 源码里的三条主线"),
    ("ep6-comparison", "P6 Comparison：对照 Windows Job Object"),
    ("ep7-synthesis", "P7 Synthesis：八个设计想法，用到数据库资源组"),
]
(D / "parts").mkdir(exist_ok=True)
parts = []
for ep, name in PARTS:
    assert "/" not in name
    src = D / f"{B}-{ep}.mp4"; dst = D / "parts" / f"{name}.mp4"
    v = json.loads((D / "video-notes" / "logs" / f"{B}-{ep}.verification.json").read_text())
    assert v["status"] == "PASS", (ep, v["status"])
    if dst.exists():
        dst.unlink()
    os.link(src, dst)
    parts.append(dst)
assert len(parts) == 8
tags = ["Linux", "cgroup", "cgroup v2", "容器", "Docker", "资源隔离", "内存控制器", "OOM", "CFS带宽控制", "内核源码", "操作系统", "系统设计"]
assert len(tags) <= 12 and all(len(t) <= 20 for t in tags)
desc = (D / f"{B}-ep0-toc.desc.txt").read_text()
assert len(desc) <= 2000
assert "atlas" not in (title + desc + ",".join(tags) + "".join(n for _, n in PARTS)).lower()
cover = D / "cover-atlas.png"; assert cover.exists()
req = {"platform": "bilibili", "title": title, "tags": tags, "cover": cover.name, "desc_file": f"{B}-ep0-toc.desc.txt",
       "parts": [{"file": p.name, "bytes": p.stat().st_size, "sha256": hashlib.sha256(p.read_bytes()).hexdigest()} for p in parts],
       "multipart": True, "season": None, "charging": False, "scheduled": False,
       "authorized_at": datetime.datetime.now().astimezone().isoformat(timespec="seconds")}
(D / "upload-request.json").write_text(json.dumps(req, ensure_ascii=False, indent=2))
for p in parts:
    print(" ", p.name, flush=True)
r = bili_upload.upload_multipart([str(p) for p in parts], str(Path.home() / ".biliup/cookies.json"),
                                 title=title, desc=desc, tags=tags, cover_path=str(cover))
print("RESULT", r, flush=True)
