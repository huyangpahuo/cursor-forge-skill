"""像素 -> 矢量 SVG:逐像素行程合并 <rect>,统一 crispEdges 硬边。"""


def svg_from_pixels(img, css_w, css_h):
    """光标帧 -> 精确矢量 SVG(逐像素行程合并成 <rect>,统一 crispEdges 硬边)。

    viewBox 用源图像素网格,width/height 是 CSS 逻辑尺寸,浏览器在设备分辨率上
    光栅化矢量——任何 DPR/缩放档都锐利(位图光标在高分屏发糊的根因就是位图
    被放大)。半透明像素用 fill-opacity 精确保留。统一像素风格(以 Anya 光标
    为基准):crispEdges 让所有包观感一致、边缘永远锐利。同一状态各帧传入
    相同的画幅尺寸(联合画幅),容器统一、帧间不脉动。
    """
    w, h = img.size
    sw, sh = css_w, css_h
    px = img.load()
    rects = []
    used = [[False] * w for _ in range(h)]
    for y in range(h):
        x = 0
        while x < w:
            if used[y][x] or px[x, y][3] <= 8:
                x += 1
                continue
            r, g, b, a = px[x, y]
            x2 = x + 1
            while x2 < w and not used[y][x2] and px[x2, y] == (r, g, b, a):
                x2 += 1
            y2 = y + 1
            while y2 < h and all(not used[y2][xx] and px[xx, y2] == (r, g, b, a)
                                 for xx in range(x, x2)):
                y2 += 1
            for yy in range(y, y2):
                for xx in range(x, x2):
                    used[yy][xx] = True
            fill = "#%02x%02x%02x" % (r, g, b)
            op = ' fill-opacity="%s"' % round(a / 255.0, 3) if a < 250 else ""
            rects.append('<rect x="%d" y="%d" width="%d" height="%d" fill="%s"%s/>'
                         % (x, y, x2 - x, y2 - y, fill, op))
            x = x2
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" '
            'viewBox="0 0 %d %d" shape-rendering="crispEdges">%s</svg>'
            % (sw, sh, w, h, "".join(rects)))


