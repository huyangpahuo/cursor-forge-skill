""".ani/.cur 二进制解析:RIFF 帧、ICONDIRENTRY 热点、AND 掩码透明修复。"""
import io
import struct

try:
    from PIL import Image, ImageChops
except ImportError:
    raise SystemExit("缺少依赖:pip install pillow")

# ---------------------------------------------------------------- .ani/.cur 解析


def read_chunks(data, start=12, end=None):
    """遍历 RIFF 块,返回 [(块ID, body偏移, body大小)]。块大小按 2 字节对齐。"""
    end = len(data) if end is None else end
    pos, out = start, []
    while pos + 8 <= end:
        cid = data[pos:pos + 4]
        size = struct.unpack("<I", data[pos + 4:pos + 8])[0]
        out.append((cid, pos + 8, size))
        pos += 8 + size + (size & 1)
    return out


def parse_ani(path):
    """解析 .ani(RIFF/ACON),返回 (帧字节列表[每个是完整 .cur], 每帧毫秒列表)。"""
    data = open(path, "rb").read()
    if data[:4] != b"RIFF" or data[8:12] != b"ACON":
        raise ValueError("不是 ANI 文件")

    frames, rate, seq, default_rate = [], None, None, None
    for cid, off, size in read_chunks(data):
        if cid == b"anih":
            hdr = struct.unpack("<9I", data[off:off + 36])
            default_rate = hdr[6]  # 单位 jiffie(1/60 秒)
        elif cid == b"rate":
            rate = list(struct.unpack("<%dI" % (size // 4), data[off:off + size]))
        elif cid == b"seq ":
            seq = list(struct.unpack("<%dI" % (size // 4), data[off:off + size]))
        elif cid == b"LIST" and data[off:off + 4] == b"fram":
            body = data[off + 4:off + size]
            for sub_id, sub_off, sub_size in read_chunks(body, start=0):
                if sub_id == b"icon":
                    frames.append(body[sub_off:sub_off + sub_size])

    if seq:
        frames = [frames[i] for i in seq if i < len(frames)]
    ms = [round(r * 1000.0 / 60.0) for r in (rate or [default_rate or 6])]
    # rate 长度不足时用最后一项补齐
    while len(ms) < len(frames):
        ms.append(ms[-1] if ms else 100)
    return frames, ms[:len(frames)] if frames else []


def cur_entries(data):
    """读 .cur/.ico 目录,返回按优劣排序的 [(字节数, 图像偏移, 热点x, 热点y, 宽, 高)]。"""
    count = struct.unpack("<H", data[4:6])[0]
    out = []
    for i in range(count):
        e = data[6 + i * 16:6 + (i + 1) * 16]
        if len(e) < 16:
            continue
        x_hot, y_hot, nbytes = struct.unpack("<HHI", e[4:12])
        w, h = e[0] or 256, e[1] or 256  # 0 表示 256
        off = struct.unpack("<I", e[12:16])[0]
        out.append((nbytes, off, x_hot, y_hot, w, h))
    out.sort(reverse=True)  # 最大(最清晰)的优先
    return out


def apply_and_mask(img, blob):
    """把 1bit AND 掩码套到 alpha 通道:掩码透明位 -> alpha 0。

    很多光标包的透明度只写在 AND 掩码里,alpha 通道是坏的(全 255)甚至没有
    (1bpp/24bpp)——只信 Pillow 解出的 alpha 会得到"黑方块光标"。掩码不透明位
    保留原 alpha,32bpp 的真实半透明不受影响。PNG 压缩条目自带完整 alpha,不经过这里。
    """
    if len(blob) < 40:
        return img
    biSize = struct.unpack("<I", blob[0:4])[0]
    if biSize < 40:  # BITMAPCOREHEADER 布局不同,极罕见,不动
        return img
    biWidth = struct.unpack("<i", blob[4:8])[0]
    biHeight2 = struct.unpack("<i", blob[8:12])[0]
    bpp = struct.unpack("<H", blob[14:16])[0]
    if biWidth != img.width or biHeight2 <= 0 or biHeight2 // 2 != img.height:
        return img
    height = biHeight2 // 2
    ncolors = struct.unpack("<I", blob[32:36])[0] or (1 << bpp if bpp <= 8 else 0)
    xor_row = ((biWidth * bpp + 31) // 32) * 4
    mask_off = biSize + ncolors * 4 + xor_row * height
    mask_row = ((biWidth + 31) // 32) * 4
    if mask_off + mask_row * height > len(blob):
        return img
    mask_img = Image.new("L", (biWidth, height), 255)
    m = mask_img.load()
    for y in range(height):
        base = mask_off + (height - 1 - y) * mask_row  # BMP 行自底向上
        row = blob[base:base + mask_row]
        for x in range(biWidth):
            if (row[x >> 3] >> (7 - (x & 7))) & 1:
                m[x, y] = 0
    img.putalpha(ImageChops.multiply(img.getchannel("A"), mask_img))
    return img


def parse_cur(data):
    """解码一帧 .cur,返回 (RGBA Image, 热点x, 热点y)。
    热点从 ICONDIRENTRY 读(wPlanes/wBitCount 字段被复用);
    图像整个文件交给 Pillow(它懂 ICO 内嵌 BMP 的高度双倍问题),
    但 PNG 压缩的 entry(Vista+ 格式)必须按偏移切出来单独解;
    BMP 条目还要用 AND 掩码修正 alpha(见 apply_and_mask)。
    """
    entries = cur_entries(data)
    if not entries:
        raise ValueError("空的光标文件")
    _, off, hx, hy, _, _ = entries[0]
    blob = data[off:off + entries[0][0]]
    if blob[:4] == b"\x89PNG":
        img = Image.open(io.BytesIO(blob))
        img.load()
        img = img.convert("RGBA")
    else:
        img = Image.open(io.BytesIO(data))
        img.load()
        img = img.convert("RGBA")
        img = apply_and_mask(img, blob)
    return img, hx, hy


def cur_native_size(data):
    entries = cur_entries(data)
    return (entries[0][4], entries[0][5]) if entries else (0, 0)


