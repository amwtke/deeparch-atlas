# pageowner.py <pid> <组目录>:抽查这个进程的匿名内存页,看每一页「记在哪个组头上」
#   /proc/<pid>/pagemap   虚拟页 → 物理页号
#   /proc/kpagecgroup     物理页号 → 这一页所属组的编号(就是组目录的 inode 号)
import os, struct, sys
pid, cgdir = int(sys.argv[1]), sys.argv[2]
want = os.stat(cgdir).st_ino
print(f"{cgdir} 的编号(inode)= {want}")
vas = []
for line in open(f'/proc/{pid}/maps'):
    f = line.split()
    if len(f) == 5 and 'rw' in f[1]:                 # 没有文件名的可写映射 = 匿名内存
        a, b = (int(x, 16) for x in f[0].split('-'))
        if b - a >= (8 << 20): vas.append((a, b))
pm = open(f'/proc/{pid}/pagemap', 'rb'); kc = open('/proc/kpagecgroup', 'rb')
seen = {}; shown = 0; total = 0
for a, b in vas:
    for va in range(a, b, 4096):
        pm.seek(va // 4096 * 8); ent = struct.unpack('Q', pm.read(8))[0]
        if not ent >> 63: continue                   # 这一页还没有物理页
        pfn = ent & ((1 << 55) - 1)
        kc.seek(pfn * 8); owner = struct.unpack('Q', kc.read(8))[0]
        seen[owner] = seen.get(owner, 0) + 1; total += 1
        if shown < 3:
            print(f"  虚拟地址 {va:#x} → 物理页号 {pfn} → 所属组编号 {owner}"); shown += 1
print(f"共查了 {total} 个物理页:" + ",".join(f"{n} 页记在编号 {o} 的组上" for o, n in seen.items()))
