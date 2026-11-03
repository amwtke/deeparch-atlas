#!/bin/bash
# 为 B 站多 P 上传建 parts/ 下的中文分 P 名硬链接(同一文件,不占额外空间;*.mp4 已在 .gitignore)
D="/Users/jin.xiao/workshop/deeparch-atlas/atlas-output/linux的进程调度器-20261103"
B=linux-sched
mkdir -p "$D/parts"; rm -f "$D/parts"/*.mp4
link() { ln "$D/$B-$1.mp4" "$D/parts/$2.mp4" && echo "  $2"; }
link ep0-toc        "P0 目录：七集路线图"
link ep1-what       "P1 What：谁上台、跑多久、在哪颗核，调度器的四问骨架"
link ep2-why        "P2 Why：从一核一队列砍八刀，逼出八条约束"
link ep3-how        "P3 How：账、标记、搬人，内核用什么把八条约束化解掉"
link ep4-origin     "P4 Origin：O(1)、CFS、EEVDF、sched_ext，五个转折点和他们的人"
link ep5-deep       "P5 Deep：钻进 6.12，挑人、均衡、throttle 各在源码哪一行"
link ep6-comparison "P6 Comparison：Windows NT 的 32 级优先级对 Linux 的账，哪些是约束哪些是血统"
link ep7-synthesis  "P7 Synthesis：五元组、五步法，再拿 MySQL 线程池走一遍"
ls -la "$D/parts"
