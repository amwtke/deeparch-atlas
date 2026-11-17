# bufwrite.py <M>:改名叫 bufwrite,带缓冲地写 M MiB 到一个新文件,不 fsync、不关文件,然后睡着
import os, sys, time
with open('/proc/self/comm', 'w') as f: f.write('bufwrite')
fd = os.open('/var/tmp/wb.dat', os.O_WRONLY | os.O_CREAT | os.O_EXCL)
buf = b'x' * (1 << 20)
for _ in range(int(sys.argv[1])): os.write(fd, buf)
print(f"bufwrite(pid {os.getpid()})写完 {sys.argv[1]} MiB,文件没关,也没 fsync", flush=True)
time.sleep(60)
