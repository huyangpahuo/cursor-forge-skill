"""转换主流程:映射 -> 多尺寸择源 -> 联合画幅 -> 逐帧 SVG -> data/cursor.js/preview。"""
import hashlib
import json
import os
import sys

from PIL import Image

from .cursorfmt import cur_native_size, parse_ani, parse_cur
from .mapping import parse_inf, resolve_state_by_name
from .preview import write_preview
from .svgout import svg_from_pixels

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

def convert(src_dir, out_dir, size=32, name=None, preview=True):
    src_dir, out_dir = os.path.abspath(src_dir), os.path.abspath(out_dir)
    name = name or os.path.basename(src_dir.rstrip("/\\")) or "cursor-pack"
    if not os.path.isdir(src_dir):
        print("错误:目录不存在 %s" % src_dir)
        sys.exit(1)

    files = sorted(f for f in os.listdir(src_dir)
                   if f.lower().endswith((".ani", ".cur")) and os.path.isfile(os.path.join(src_dir, f)))
    if not files:
        print("错误:%s 里没有 .ani/.cur 文件" % src_dir)
        sys.exit(1)
    lower_map = {f.lower(): f for f in files}  # inf 里路径大小写不一定与实际一致

    # ---------- 1) 状态映射:inf 权威优先,文件名启发式兜底 ----------
    mapping = {}       # 状态名 -> 实际文件名
    inf_source = None
    for f in os.listdir(src_dir):
        if f.lower().endswith(".inf"):
            try:
                roles = parse_inf(os.path.join(src_dir, f))
            except Exception as e:
                print("警告:解析 %s 失败(%s),改用文件名启发式" % (f, e))
                continue
            if roles:
                inf_source = f
                for state, fn in roles.items():
                    if fn in lower_map:
                        mapping[state] = lower_map[fn]
                break

    unknown = []
    for f in files:
        if f in mapping.values():
            continue
        stem = os.path.splitext(f)[0]
        state = resolve_state_by_name(stem)
        if state and state not in mapping:
            mapping[state] = f
        elif not state:
            unknown.append(f)

    # 同一状态多尺寸(如 转圈_32px/64px/128px):解析原生尺寸,择优保留一个
    by_norm = {}
    for st, f in mapping.items():
        by_norm.setdefault(st, []).append(f)
    # 启发式阶段只保留了一个;把"未映射的疑似同状态变体"也归进来
    for f in unknown[:]:
        stem = os.path.splitext(f)[0]
        st = resolve_state_by_name(stem)
        if st and st in by_norm:
            by_norm[st].append(f)
            unknown.remove(f)
    # 矢量时代取原生尺寸最大的源:细节最全(平滑艺术受益),像素画的大尺寸源
    # 是小格放大,行程合并会自动归并成同样的矩形,不吃亏
    for st, cands in by_norm.items():
        if len(cands) > 1:
            def native(fn):
                p = os.path.join(src_dir, fn)
                try:
                    if fn.lower().endswith(".ani"):
                        frames, _ = parse_ani(p)
                        return cur_native_size(frames[0]) if frames else (0, 0)
                    return cur_native_size(open(p, "rb").read())
                except Exception:
                    return (0, 0)
            scored = sorted(((native(f), f) for f in cands),
                            key=lambda t: -t[0][0])
            best = scored[0][1]
            mapping[st] = best
            for _, f in scored[1:]:
                if f in unknown:
                    unknown.remove(f)  # 是尺寸变体,不算未知状态
            print("  多尺寸择优:%s 采用 %s(跳过变体:%s)" %
                  (st, best, ", ".join(f for _, f in scored[1:])))

    if not mapping:
        print("错误:没能从 inf 或文件名推断出任何状态。文件列表:")
        for f in files:
            print("   ", f)
        sys.exit(1)

    # ---------- 2) 逐状态逐帧转换(全矢量输出,无 PNG) ----------
    states_data = {}
    dedupe = {}  # md5 -> 已保存的相对路径
    total_frames = 0
    used_files = []

    for st in sorted(mapping):
        fn = mapping[st]
        path = os.path.join(src_dir, fn)
        try:
            if fn.lower().endswith(".ani"):
                frames, ms = parse_ani(path)
            else:
                frames, ms = [open(path, "rb").read()], [100]
        except Exception as e:
            print("警告:跳过 %s(%s)" % (fn, e))
            continue
        if not frames:
            print("警告:%s 无有效帧,跳过" % fn)
            continue
        used_files.append(fn)

        entry = {"ms": [], "frames": [], "hot": []}

        # 两遍走:先解码全部帧并求**状态级联合画幅**(所有帧内容边界的并集),
        # 再把每帧锚进同一画幅统一尺寸。理由:逐帧独立归一化会让动画帧内容
        # 一大一小就逐帧脉动,且各状态比例失衡;固定画幅 = 相同大小的容器,
        # 帧间稳定、状态间视觉尺寸一致(观感统一的关键)。
        decoded = []  # (帧序号, 原图, 热点x, 热点y, 内容bbox或None)
        for i, cur_bytes in enumerate(frames):
            try:
                img, hx, hy = parse_cur(cur_bytes)
            except Exception as e:
                print("警告:%s 第 %d 帧解码失败(%s),跳过该帧" % (fn, i, e))
                continue
            decoded.append((i, img, hx, hy, img.getbbox()))
        if not decoded:
            print("警告:%s 没有可解码帧,跳过" % fn)
            continue

        ux0 = uy0 = ux1 = uy1 = None
        for _, _, _, _, bbox in decoded:
            if not bbox:
                continue  # 全透明帧(闪烁动画常见)不扩大画幅
            ux0 = bbox[0] if ux0 is None else min(ux0, bbox[0])
            uy0 = bbox[1] if uy0 is None else min(uy0, bbox[1])
            ux1 = bbox[2] if ux1 is None else max(ux1, bbox[2])
            uy1 = bbox[3] if uy1 is None else max(uy1, bbox[3])
        if ux0 is None:
            print("警告:%s 全部帧均为全透明,跳过" % fn)
            continue
        uw, vh = ux1 - ux0, uy1 - uy0
        scale = size / max(uw, vh)           # 缩放系数(全状态帧共用)
        cell_w = max(1, round(uw * scale))   # 画幅 CSS 尺寸(各帧一致)
        cell_h = max(1, round(vh * scale))

        for i, img, hx, hy, bbox in decoded:
            # 帧内容按自身 bbox 贴进联合画幅(保留动画中的位移设计)
            cell = Image.new("RGBA", (uw, vh), (0, 0, 0, 0))
            if bbox:
                cell.paste(img.crop(bbox), (bbox[0] - ux0, bbox[1] - uy0))
            fx, fy = hx - ux0, hy - uy0

            h1x = min(max(round(fx * scale), 0), cell_w - 1)
            h1y = min(max(round(fy * scale), 0), cell_h - 1)

            svg = svg_from_pixels(cell, cell_w, cell_h).encode("utf-8")
            key = hashlib.md5(svg).hexdigest()
            if key in dedupe:
                rel = dedupe[key]
            else:
                rel = "svg/%s/%d.svg" % (st, i)
                dest = os.path.join(out_dir, *rel.split("/"))
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                open(dest, "wb").write(svg)
                dedupe[key] = rel
            entry["frames"].append(rel)
            entry["hot"].append([h1x, h1y])
            entry["ms"].append(ms[i] if i < len(ms) else ms[-1])

        nframes = len(entry["frames"])
        if nframes:
            states_data[st] = entry
            total_frames += nframes
            hot0 = entry["hot"][0]
            print("  %-22s %-14s %3d 帧  %5.0fms/帧  热点(%d,%d)  画幅%dx%d" %
                  (st, os.path.splitext(fn)[0], nframes,
                   entry["ms"][0], hot0[0], hot0[1], cell_w, cell_h))

    if not states_data:
        print("错误:没有任何状态转换成功")
        sys.exit(1)

    # ---------- 3) 生成 data.js / cursor.js / preview.html ----------
    data = {
        "pack": name,
        "size": size,
        "states": states_data,
    }
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "data.js"), "w", encoding="utf-8") as f:
        f.write("/* 由 cursor-forge 生成,请勿手改;供 cursor.js 外部引用模式使用 */\n")
        f.write("window.CURSOR_KIT_DATA = " + json.dumps(data, ensure_ascii=False) + ";\n")

    # 运行时模板在 skill 根的 assets/(本文件位于 scripts/cursorforge/,向上两级)
    runtime_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "..", "assets", "cursor-runtime.js")
    runtime = open(runtime_path, encoding="utf-8").read()
    merged = runtime.replace("/*__CURSOR_DATA__*/null",
                             json.dumps(data, ensure_ascii=False))
    if "/*__CURSOR_DATA__*/null" in runtime:
        with open(os.path.join(out_dir, "cursor.js"), "w", encoding="utf-8") as f:
            f.write(merged)
    else:
        print("警告:运行时模板缺少数据占位符,cursor.js 未生成(请检查 assets/cursor-runtime.js)")

    if preview:
        write_preview(out_dir, name, data)

    # ---------- 4) 汇总 ----------
    total_kb = 0
    for root, _, fs in os.walk(out_dir):
        for f in fs:
            if f.endswith(".svg"):
                total_kb += os.path.getsize(os.path.join(root, f)) / 1024.0
    print("")
    print("完成:%s -> %s" % (name, out_dir))
    print("  %d 个状态,%d 帧(全矢量,统一 crispEdges 像素风格),SVG 合计 %.0f KB;映射信源:%s" %
          (len(states_data), total_frames, total_kb,
           inf_source if inf_source else "文件名启发式(inf 缺失或未命中)"))
    if unknown:
        print("  未识别(未接入):%s" % ", ".join(unknown))
        print("  如需接入可在页面用 data-cursor=\"<状态名>\" 自定义,或重命名后重跑")
    print("  接入:把整个输出目录放进站点静态目录,加一行 "
          '<script src="<静态路径>/%s/cursor.js" defer></script>' % name)
    print("  预览:直接打开 %s" % os.path.join(out_dir, "preview.html"))


