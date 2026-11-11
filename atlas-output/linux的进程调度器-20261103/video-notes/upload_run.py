"""B 站多 P 上传：8 个 mp4 作为 1 个稿件的 8 个分 P。先写文件再跑，输出直接重定向到日志。
用法: venv/bin/python upload_run.py <D> "<稿件标题>"  > logs/upload.log 2>&1
"""
import sys, os, json, hashlib, datetime
from pathlib import Path
sys.path.insert(0, "/Users/jin.xiao/workshop/deeparch-video/scripts")
import bili_upload

D = Path(sys.argv[1]); title = sys.argv[2]
B = "linux-sched"
PARTS = [
    ("ep0-toc", "P0 目录：七集路线图"),
    ("ep1-what", "P1 What：一颗只认下一条指令的 CPU，调度器替它做了什么"),
    ("ep2-why", "P2 Why：从一次只跑一个程序砍六刀，调度器为什么非得长成这样"),
    ("ep3-how", "P3 How：账本、三扇门、调度类链，调度器到底怎么答三问"),
    ("ep4-origin", "P4 Origin：调度器 33 年，一个被否决的问题怎么在二十年后翻案"),
    ("ep5-deep", "P5 Deep：换人只换一根栈，三条主线钉到 6.12 源码行号"),
    ("ep6-comparison", "P6 Comparison：同一个按键，Windows 和 Linux 凭的理由完全不同"),
    ("ep7-synthesis", "P7 Synthesis：不是最聪明的算法，是八条约束筛剩下的"),
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
tags = ["Linux", "调度器", "CFS", "EEVDF", "vruntime", "上下文切换", "cgroup", "sched_ext", "eBPF", "内核源码", "操作系统", "系统设计"]
desc = (D / f"{B}-ep0-toc.desc.txt").read_text()
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
