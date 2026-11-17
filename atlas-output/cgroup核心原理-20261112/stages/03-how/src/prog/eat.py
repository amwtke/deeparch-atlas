# eat.py <M>:改名叫 eat,吃 M MiB 内存后退出
import sys
with open('/proc/self/comm', 'w') as f: f.write('eat')
hold = [b'x' * (10 << 20) for _ in range(int(sys.argv[1]) // 10)]
