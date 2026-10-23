"""本次成片的图示副本：保留原文七图主题，校准 glibc 2.34 / LP64 条件。

仅写当前成片目录，不修改原文或原 SVG。使用已有 Chromium 渲染，无新增依赖。
"""
from pathlib import Path
import html
from playwright.sync_api import sync_playwright

OUT = Path(__file__).resolve().parent
BG, INK, SUB, CLAY, LINE = '#F5F0E8', '#2B2620', '#6B5D4F', '#C15F3C', '#D8CCBA'

def tx(x, y, value, size=25, color=INK, weight='normal'):
    return f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" font-weight="{weight}">{html.escape(value)}</text>'

def panel(x, y, w, h, title, lines, fill='#FBF8F2', size=25):
    s=f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="18" fill="{fill}" stroke="{LINE}" stroke-width="2"/>'
    s+=tx(x+25,y+44,title,30,CLAY,'bold')
    for i,t in enumerate(lines):s+=tx(x+25,y+92+i*(size+16),t,size)
    return s

def fig(title, subtitle, content, foot):
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1920 1080" font-family="Noto Sans CJK SC">'
      f'<rect width="1920" height="1080" fill="{BG}"/>' + tx(65,75,title,44,INK,'bold')
      +tx(65,125,subtitle,25,SUB)+content+tx(65,1030,foot,23,SUB)+'</svg>')

def arrow(x1,y1,x2,y2,label=''):
    s=f'<path d="M{x1},{y1} L{x2},{y2}" stroke="{CLAY}" stroke-width="4" fill="none"/>'
    if y2>y1:s+=f'<path d="M{x2-9},{y2-14} L{x2},{y2} L{x2+9},{y2-14}" fill="none" stroke="{CLAY}" stroke-width="4"/>'
    else:s+=f'<path d="M{x2-14},{y2-9} L{x2},{y2} L{x2-14},{y2+9}" fill="none" stroke="{CLAY}" stroke-width="4"/>'
    return s+tx((x1+x2)/2+12,(y1+y2)/2-8,label,22,SUB)

def table(headers, rows, widths):
    s=''; xs=[65]
    for w in widths:xs.append(xs[-1]+w)
    for ri,row in enumerate([headers]+rows):
        y=175+ri*139
        for ci,val in enumerate(row):
            s+=f'<rect x="{xs[ci]}" y="{y}" width="{widths[ci]}" height="139" fill="'+('#E8DFD0' if ri==0 else '#FBF8F2')+f'" stroke="{LINE}"/>'
            for j,line in enumerate(val.split('|')):s+=tx(xs[ci]+16,y+39+j*34,line,24 if ci else 25,CLAY if ri==0 else INK,'bold' if ri==0 else 'normal')
    return s

figs={}
s=panel(65,175,1790,125,'进程边界：内核提供虚拟地址空间隔离',['malloc 管理本进程可用的虚拟内存；驻留物理页与页表由内核管理。'])
for i in range(3):s+=panel(65+i*600,340,560,170,f'线程 {i+1} 的 tcache',['每线程一份指针索引；命中时不取 arena 锁','默认 64 桶，每桶上限 7；命中率取决于负载'],size=23)
s+=arrow(340,510,340,570,'未命中')+arrow(950,510,950,570,'未命中')
s+=panel(65,570,850,345,'main_arena：池状态 + 一把锁 + 关联 heap',['控制面：mutex / top / binmap / next / system_mem','空闲索引：fastbinsY + unsorted / small / large bins','物理载体：in-use 与 free chunks + top chunk','空间不足：主 arena 可经 brk 扩展，也可能用 mmap','tcache 里的 chunk 仍属于原 arena 的 heap'],size=25)
s+=panel(955,570,900,345,'线程 arena：相同索引结构，独立池锁',['多个线程可共享 arena；并非一个线程必须一个池','非主 arena 的 heap 区域通常由 mmap 获取','arena 达到上限后复用；64 位默认上限按 CPU 数算','池分片减少竞争，也可能增加驻留量与碎片','tcache 是线程旁路，不是 arena 内的子池'],size=25)
figs['03-overview']=fig('四件事骨架：chunk + bin + arena + tcache','glibc 2.34 / Linux LP64；默认参数是条件，不是永久不变量。',s,'物理字节由 chunk 表示，空闲查找由 bin 表示，池与锁由 arena 表示，线程快路径由 tcache 表示。')

s=panel(65,175,1790,135,'线程维度：tcache entries[64] + counts[64]',['默认每桶最多 7 个 chunk；桶 0 对应 32 B chunk，桶 1 对应 48 B chunk；先查线程缓存，再进入池。'],size=25)
s+=panel(65,345,1790,125,'arena 控制面：struct malloc_state',['mutex / flags / have_fastchunks / top / last_remainder / binmap / next / next_free / attached_threads / system_mem'],size=24)
s+=panel(65,505,565,290,'fastbinsY：独立指针数组',['同桶同大小，单链表 LIFO','LP64 桶步长 16 B，首桶 32 B','释放时通常先不合并','分配路径可带原子链头操作','与双链表 bins 的布局不同'],size=25)
s+=panel(665,505,580,290,'bins：双链表哨兵数组',['unsorted：归类前的一次暂存机会','small：固定 chunk 尺寸','large：范围桶 + 有序索引','LP64 smallbin 边界为 1024 B','bin 编号与 C 数组偏移不同'],size=25)
s+=panel(1280,505,575,290,'chunk 与 heap：物理载体',['同一 heap 内的块按地址相邻','在用块不挂空闲 bin 链','已释放块可挂 tcache / bin','top 是尚未切给应用的尾部','非主 arena 可关联多个 heap'],size=25)
s+=panel(65,830,1790,130,'两个独立维度，不要把逻辑链表误认为物理连续',['tcache 的所有权属于当前线程；chunk 所属 arena 由地址和元数据确定，跨线程释放不改变这一归属。'],size=25)
figs['03-arena-hierarchy']=fig('层级与所有权：线程缓存旁路，arena 容纳索引与 heap','按 glibc 2.34 / LP64 校正原图桶号、尺寸和内核锁表示；小块快路径仍有边界。',s,'fastbinsY 与 bins 分离首先服务不同链表和操作语义；布局紧凑是收益，固定 cache line 偏移不是跨平台保证。')

s=''
blocks=[('A','32 B','在用'),('B','48 B','fastbin'),('C','64 B','在用'),('D','1280 B','unsorted'),('E','32 B','在用'),('F','80 B','smallbin'),('G','208 B','在用'),('H','96 B','smallbin'),('I','608 B','在用'),('top','未分配','尾部')]
for i,(name,size,state) in enumerate(blocks):s+=panel(65+i*179,210,165,215,name,[size,state],fill='#E8DFD0' if state=='在用' else '#FBF8F2',size=23)
s+=tx(65,470,'低虚拟地址 → 高虚拟地址：这里画的是 heap 内的字节布局，不是物理页帧。',28,SUB)
for i,(title,lines) in enumerate([('fastbinsY[1]',['链头 → B','48 B chunk','单链表 / 延迟合并']),('unsorted bin',['哨兵 ⇄ D','不同大小均可暂存','归类前的复用机会']),('smallbin 5 / 6',['5：哨兵 ⇄ F (80 B)','6：哨兵 ⇄ H (96 B)','同桶精确尺寸']),('large bins',['范围桶 / 大小排序','图中暂未挂块','必要时从 unsorted 归类'])]):s+=panel(65+i*450,560,415,260,title,lines,size=25)
s+=panel(65,860,1790,110,'同一块，两种视图',['bin 只链接空闲块，不移动物理位置；chunk 可改变索引归属，也可与相邻空闲块合并。'],size=25)
figs['03-physical-vs-logical']=fig('物理布局与逻辑索引：同一组 chunk 的两个视角','glibc 2.34 / LP64；示意块尺寸满足 16 B 对齐，未按尺寸比例绘制。',s,'在用块 A/C/E/G/I 没有空闲 bin 归属；释放并不自动等于归还内核，合并也不等于立即缩小 RSS。')

s=''
events=[('1987','dlmalloc',['Doug Lea','通用分配器目标','速度 / 空间 / 可移植性','boundary tags 与分桶']),('1990s','ptmalloc',['Wolfram Gloger','共享进程中的并发需求','多 arena 逐步形成','锁边界随数据分片']),('2002','glibc 2.3',['NEWS 记录 malloc 重写','基于 dlmalloc 2.7.0','更早 glibc 已有 arena','并非 2006 首次整合']),('2017','glibc 2.26',['DJ Delorie 等','per-thread tcache','减少热点 arena 锁访问','缓存成本与检查同步演进']),('后续','持续演进',['指针保护 / 检查改进','运行时与业务专用池','负载改变，约束重估','不是通用 allocator 消失'])]
for i,(year,title,lines) in enumerate(events):
 s+=panel(65+i*360,215,335,470,year+' '+title,lines,size=25)
 if i<4:s+=arrow(400+i*360,720,425+i*360,720)
s+=panel(65,790,1790,205,'平行路线：不是后来者只能复制前人的形状',['jemalloc：多 arena + size classes + thread caches；CPU 绑定是配置选择。','TCMalloc：区分 gperftools 的线程缓存与现代 Google TCMalloc 的 per-CPU 模式。','mimalloc：按页组织空闲链与线程局部管理；通用接口下仍有不同取舍。'],size=24)
figs['04-timeline']=fig('演化时间线：每一代都在重估资源、负载与锁竞争','年份以 glibc NEWS 与作者原文为准；不把某个独立发行包日期当作集成时间。',s,'一手依据：Doug Lea A Memory Allocator；glibc 2.3 NEWS；glibc 2.26 发布记录与 tcache 提交讨论。')

cols=[('缓存命中：malloc(24)',['__libc_malloc：请求规范化','LP64：24 → 32 B chunk','csize2tidx(32) → 桶 0','tcache 存在，桶内有可复用块','tcache_get(0) 弹出缓存块','返回已经是用户指针的 e','不进入 arena 锁 / 不调用内核','free：_int_free → tcache_put','前提：未超范围，缓存尚未满']),('池内查找 / 扩展：malloc(8KB)',['__libc_malloc → arena_get','多线程路径获取 arena mutex','_int_malloc：bins → top','能复用就不必发生 syscall','main arena 的 top 不足时','sysmalloc 可经 MORECORE/brk','非主 arena 通常扩 mmap heap','free：缓存/合并/池内复用','不是每次 8KB 都必然 brk']),('独立映射：malloc(200KB)',['先进入分配入口与池内查找','无法复用且达到映射条件时','sysmalloc → mmap 分支','检查阈值、计数与失败回退','页对齐映射，设置 IS_MMAPPED','独立于 arena heap 的映射','free：__libc_free 检查标志','munmap_chunk → munmap','阈值可动态变化，RSS看触页'])]
s=''
for i,(title,lines) in enumerate(cols):s+=panel(65+i*605,190,570,700,title,lines,size=25)
s+=tx(65,955,'请求大小只是路由条件之一；缓存状态、池内空闲块、阈值、映射上限与初始化都会改变实际路径。',26,SUB)
figs['05-call-stack-three-paths']=fig('三条路径：缓存命中、arena 管理、独立 mmap','固定 glibc 2.34 / Linux LP64；展示条件路径，成本差异须用目标负载实测。',s,'mmap 分支不保证绕过 arena 锁；这里的 tcache_get 与桶号来自固定版本源码，而非后续版本的 tcache_get_n。')

rows=[['ptmalloc','free(p) 反查|内联块头','线程缓存 + 多 arena|不等于无限扩展','trim / mmap 归还|由路径与阈值决定'],['jemalloc','外置元数据与 size class|仍兼容 malloc/free','thread caches + arenas|percpu_arena 可选','dirty/muzzy decay 等|需结合配置与负载'],['TCMalloc','页到 span 等反查|仍兼容 malloc/free','现代 Google per-CPU|gperftools per-thread','回收策略与配置有关|不是固定归还时延'],['mimalloc','页组织与尺寸类别|仍兼容 malloc/free','线程局部管理|页内分片空闲链','purge 策略可配置|不保证固定 RSS'],['Go / Rust','Go：运行时类型与 GC|Rust：Layout 是契约','Go：mcache/per-P 等|Rust：取决于实现','GOMEMLIMIT 是软限制|Rust：取决于底层分配器']]
s=table(['方案','接口与元数据','局部化 / 并发','归还与容器边界'],rows,[285,495,520,490])
figs['06-design-space-map']=fig('设计空间：用独立维度比较，别把方案排成单一名次','保留原文“元数据契约 × 归还策略”的问题；这些是可配置行为，图中位置不是永久物理常数。',s,'GOMEMLIMIT 不等于自动读取 cgroup，也不是进程 RSS 硬上限；容器限制须由部署与应用层共同提供。')

rows=[['资源单位','chunk|虚拟字节块','Object|运行时对象','对象 / slab 页|区分单元与承载','buffer frame / Pod|页帧 / 调度任务'],['空闲与定位','bin / tcache|地址相邻 ≠ 链表相邻','分配区 / 空闲表|Generation 不是 bin','freelist / partial|按对象类别组织','hash/LRU/queue|定位、替换、候选'],['池与边界','arena / heap|线程缓存为旁路','Heap / regions|由 GC 实现决定','kmem_cache / perCPU|不是进程 arena','pool / Node|锁边界 / 调度边界'],['信息反查','指针 → chunk|头中尺寸与标志','runtime 类型信息|GC 还负责可达性','cache / 地址元数据|kmem_cache_free≠kfree','page id / Pod spec|索引与调度缓存'],['局部化代价','tcache + 多 arena|缓存滞留 / 碎片','TLAB 等|分配快不等于GC免费','per-CPU 缓存|并发规则仍存在','分片 / 缓存|不能直接等同无锁']]
s=table(['比较维度','ptmalloc','JVM GC','Linux SLUB','数据库 / K8s'],rows,[265,380,380,380,385])
figs['07-isomorphic-systems']=fig('跨领域同构：迁移问题结构，不复制具体实现','五个维度：资源单位、索引、池边界、信息反查、局部化；相似角色并不意味着机制一一等价。',s,'数据库默认页：InnoDB 常见 16 KB，PostgreSQL 常见 8 KB；K8s 调度不是一个 glibc 式内存分配器。')

if __name__=='__main__':
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True)
        page=browser.new_page(viewport={'width':1920,'height':1080},device_scale_factor=1)
        for name,svg in figs.items():
            src=OUT/'pics'/f'{name}.svg';src.write_text(svg,encoding='utf-8')
            page.set_content('<html><style>html,body{margin:0;width:1920px;height:1080px}svg{display:block}</style>'+svg+'</html>')
            page.evaluate('document.fonts.ready')
            page.screenshot(path=str(OUT/'pics'/f'{name}.png'))
            print('RENDERED',name,flush=True)
        browser.close()
