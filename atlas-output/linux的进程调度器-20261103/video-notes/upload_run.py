import sys, json, hashlib, datetime
from pathlib import Path
sys.path.insert(0, "/Users/jin.xiao/workshop/deeparch-video/scripts")
import bili_upload
D = Path(sys.argv[1])
parts = sorted((D / "parts").glob("P*.mp4"))
assert len(parts) == 8, parts
title = sys.argv[2]
tags = ["Linux","调度器","EEVDF","CFS","nice","cgroup","CPU限额","负载均衡","内核源码","操作系统","Windows NT","MySQL线程池"]
desc = (D / "linux-sched-ep0-toc.desc.txt").read_text()
assert "atlas" not in (title + desc + ",".join(tags)).lower()
req = {"platform": "bilibili", "title": title, "tags": tags, "cover": "cover-atlas.png", "desc_file": "linux-sched-ep0-toc.desc.txt",
       "parts": [{"file": p.name, "bytes": p.stat().st_size, "sha256": hashlib.sha256(p.read_bytes()).hexdigest()} for p in parts],
       "multipart": True, "season": None, "charging": False, "scheduled": False,
       "authorized_at": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
       "authorization": "用户 2026-11-03 对话中一次性授权:生成大电影后提交 B 站并推送 main"}
(D / "upload-request.json").write_text(json.dumps(req, ensure_ascii=False, indent=2))
for p in parts: print(" ", p.name, flush=True)
r = bili_upload.upload_multipart([str(p) for p in parts], str(Path.home() / ".biliup/cookies.json"),
                                 title=title, desc=desc, tags=tags, cover_path=str(D / "cover-atlas.png"))
print("RESULT", r, flush=True)
