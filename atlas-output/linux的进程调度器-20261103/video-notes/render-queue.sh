#!/bin/bash
# 串行渲染队列：只渲染主控已打 ready-epN 标记的集；mp4 已存在且 >1MB 跳过
D="/Users/jin.xiao/workshop/deeparch-atlas/atlas-output/linux的进程调度器-20261103"
REPO=/Users/jin.xiao/workshop/deeparch-video
B=linux-sched
cd "$REPO"
caffeinate -i -w $$ &
EPS="ep0-toc ep1-what ep2-why ep3-how ep4-origin ep5-deep ep6-comparison ep7-synthesis"
remaining="$EPS"
while [ -n "$remaining" ]; do
  next=""
  for ep in $remaining; do
    n=${ep%%-*}; n=${n#ep}
    MP4="$D/$B-$ep.mp4"
    if [ -f "$MP4" ] && [ $(stat -f%z "$MP4") -gt 1000000 ]; then continue; fi
    if [ -f "$D/video-notes/ready-ep$n" ]; then
      echo "$(date '+%F %T') >>> render $ep" >> "$D/video-notes/logs/queue.log"
      sha_before=$(shasum -a 256 "$D/$B-$ep.vmd" | cut -d' ' -f1)
      ./deeparch-video "$D/$B-$ep.vmd" --theme anthropic --lint strict > "$D/video-notes/logs/render-ep$n.log" 2>&1
      rc=$?
      sha_after=$(shasum -a 256 "$D/$B-$ep.vmd" | cut -d' ' -f1)
      venv/bin/python "$D/video-notes/verify_ep.py" "$D" "$B-$ep" "$rc" "$sha_before" "$sha_after" >> "$D/video-notes/logs/queue.log" 2>&1
      echo "$(date '+%F %T') <<< done $ep rc=$rc" >> "$D/video-notes/logs/queue.log"
    else
      next="$next $ep"
    fi
  done
  remaining=$(echo $next)
  [ -n "$remaining" ] && sleep 30
done
echo "$(date '+%F %T') QUEUE COMPLETE" >> "$D/video-notes/logs/queue.log"
