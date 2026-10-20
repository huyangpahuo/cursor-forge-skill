# Windows 光标格式与浏览器行为速查

转换异常时按此排查。脚本已处理全部已知坑,这里记原理。

## .ani(RIFF 容器)

```
RIFF....ACON
├─ anih  (36B 头,第 7 个 uint32 = 默认每帧行 jiffie 数,1 jiffie = 1/60 秒)
├─ rate  (可选,每帧 jiffie 数组——逐帧时长可以不同)
├─ seq   (可选,帧播放顺序,允许复用帧)
└─ LIST('fram')
   ├─ icon  (一个完整的 .cur 文件)
   └─ ...
```

- RIFF 块大小按 **2 字节对齐**(`size & 1` 补齐),否则第二帧起全部错位;
- `seq` 存在时按 seq 重排(重复帧由内容去重复用同一 SVG);
- `rate` 与帧数不齐时用最后一项补齐。

## .cur / .ico(ICONDIRENTRY)

```
偏移 0-3  : bWidth, bHeight, bColorCount, bReserved(0 表示 256)
偏移 4-5  : wPlanes   —— .cur 里复用为 热点X
偏移 6-7  : wBitCount —— .cur 里复用为 热点Y
偏移 8-11 : dwBytesInRes
偏移 12-15: dwImageOffset
```

1. **热点在 entry 的 4-8 字节**,不在文件头;
2. BMP 内嵌 ICO 的 biHeight 是"高×2"(XOR+AND 掩码),整个文件直接给
   `Image.open`,Pillow 懂;别自己按偏移切片;
3. PNG 压缩 entry(Vista+ 常见,数据以 `\x89PNG` 开头)必须按
   `dwImageOffset/dwBytesInRes` 切出来单独解;
4. **透明度可能在 AND 掩码不在 alpha**(黑方块根因):大量包是 32bpp 但 alpha 全
   255(坏通道)或 1bpp/24bpp(无 alpha),真实透明度在 XOR 后的 1bit AND 掩码
   (1=透明,行自底向上、32bit 对齐,偏移 = 头 + 调色板 + XOR 大小)。Pillow 解
   32bpp 不应用掩码 → 透明区按黑渲染成黑方块。修法:掩码乘到 alpha 上;
5. 多尺寸 .cur:图像与热点取同一 entry(最大的);
6. 有些帧内容本就是全不透明像素画(Minecraft 方块贴图),不是 bug。

## .inf 安装文件(权威映射信源)

两种形态,优先解析:

形态一,逐角色注册行:
```
HKCU,"Control Panel\Cursors",Arrow,0x00020000,"%10%\%CUR_DIR%\%pointer%"
```
角色 → 网页状态:Arrow→normal、Help→help、AppStarting→working、Wait→busy、
Crosshair→crosshair、IBeam→text、NWPen→pen、No→unavailable、SizeNS→ns、
SizeWE→ew、SizeNWSE→nwse、SizeNESW→nesw、SizeAll→move、UpArrow→alt、
Hand→link、Person→person、Pin→pin(自造角色如 precisionhair 按 crosshair)。

形态二,Scheme 字符串(无逐角色行时按固定槽位顺序还原):
```
Arrow, Help, AppStarting, Wait, Crosshair, IBeam, NWPen, No,
SizeNS, SizeWE, SizeNWSE, SizeNESW, SizeAll, UpArrow, Hand, [Person, Pin]
```

- `%VAR%` 引用 `[Strings]` 段,先替换(未知占位符如 `%10%` 删掉);
- **编码大概率 GBK**;只认带 BOM 的 UTF-16,否则 UTF-8 严格失败后走 GBK
  (盲试 UTF-16 会"解码成功"出乱码);
- inf 文件名大小写与实际文件可能不一致,小写匹配;
- inf 声明但目录缺失的文件静默跳过,回退文件名启发式。

## 文件名启发式(inf 缺失时)

归一化:小写、去结尾 `_NNpx`、连字符/空格转下划线。中英对照精确匹配(指针→
normal、手→link、文本→text、转圈/无响应→busy、笔→pen、帮助/？→help、
上下左右→move、＋→crosshair、×→unavailable、←→→ew、↑↓→ns、↖↘→nwse、↙↗→
nesw、候选→alt;X11:all-scroll→move、col-resize→ew、bottom_left_corner→nesw
等;扩展状态 copy/alias/zoom-in/zoom-out),精确不中再子串匹配。

## 浏览器行为(实测)

- CSS cursor 不支持任何动画格式;SVG 动画也不播 → 动画只能 JS 换帧;
- **多个 url() 是有序回退列表,不是按 DPR 择优**(每张按 1x 处理,生效的永远是
  第一张;加载期会出现"先大后小"跳变)→ 永远单 url 声明;
- SVG 光标:Chrome/Firefox/Edge 支持,**Safari 不支持**(落关键字兜底);
- cursor 的 SVG width/height ≤128px,超限整条声明作废;
- `url() x y` 热点必填且须在图内;
- 触屏无指针(`(pointer: fine)` 判断);`prefers-reduced-motion: reduce` 停首帧;
  rAF 可能被环境抑制(遮挡的 webview)→ 看门狗退化为 setTimeout;
- iframe 内部(嵌入播放器)无法接管;
- 换帧用 CSS 变量挂 `:root`(`--ck-<state>`),pjax/SPA 换页不丢。

## 管线决策(为什么这么做)

- **全矢量 + 统一 crispEdges**:SVG 在设备分辨率光栅化,任何 DPR/缩放锐利;
  统一像素风格(以 Anya 为基准)让所有包观感一致;半透明用 fill-opacity 保留;
- **状态级联合画幅**:逐帧独立归一化会让动画帧逐帧脉动、状态比例失衡;
  并集画幅 = 相同大小容器,帧间稳定、状态视觉统一,帧内位移设计保留;
- **多尺寸取最大源**:矢量细节最全;像素画的大尺寸源是小格放大,行程合并
  自动归并,不吃亏;
- **逐帧 ms 数组**:rate 块允许每帧不同时长,只存第一帧是隐性 bug;
- **帧去重**:md5 相同复用同一 SVG(seq 复用、循环动画常见);
- 解码一律 `convert("RGBA")` 后再处理。
