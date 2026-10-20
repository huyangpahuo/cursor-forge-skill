# -*- coding: utf-8 -*-
"""
cursor-forge:把 Windows 光标包(.ani 动画 / .cur 静态)转换成任何网站可用的
自定义鼠标指针——全矢量 SVG 输出,无 PNG。

SVG 光标由浏览器在设备分辨率上光栅化,任何 DPR/缩放档都锐利;SVG 动画不会被
播放,动画由运行时逐帧换 url 实现。

用法:
  python cursor_convert.py <光标包目录或压缩包> <输出目录> [--size 32] [--name 名称]

输入直接给 zip/7z/rar 等压缩包也行,自动解压并定位包内容(嵌套压缩包最多解 3 层),
无需手动解压。rar 需要 WinRAR/7-Zip 之一,或 Windows 10+ 自带的 tar 兜底。

输出:
  <输出目录>/svg/<state>/<i>.svg   各状态帧图(全矢量,统一 crispEdges 像素风格)
  <输出目录>/cursor.js             单文件运行时(数据已内嵌,一行 <script> 接入)
  <输出目录>/data.js               window.CURSOR_KIT_DATA = {...}(机器可读清单)
  <输出目录>/preview.html          预览/验收页

模块划分(见 cursorforge/ 包):
  mapping    状态映射(inf 两种形态权威解析 + 中英文文件名启发式)
  cursorfmt  .ani/.cur 二进制解析(RIFF 帧/ICONDIRENTRY 热点/AND 掩码透明修复)
  svgout     像素 -> 矢量 SVG(行程合并 <rect>)
  pipeline   转换主流程(inf 映射->多尺寸取最大源->联合画幅->逐帧 SVG->产物)
  preview    preview.html 生成
  archive    压缩包直读(zip/7z/rar 自动解压定位,免手动解压)
"""

import argparse
import shutil

from cursorforge.archive import prepare_src
from cursorforge.pipeline import convert


def main():
    ap = argparse.ArgumentParser(description="Windows 光标包 -> 网页自定义鼠标指针(全矢量 SVG)")
    ap.add_argument("src", help="光标包目录或压缩包(zip/7z/rar 等,免手动解压)")
    ap.add_argument("out", help="输出目录")
    ap.add_argument("--size", type=int, default=32,
                    help="光标 CSS 尺寸 px(默认 32,上限 128;矢量与 DPR 无关,一档即可)")
    ap.add_argument("--name", default=None, help="光标包名称(默认取目录名)")
    ap.add_argument("--no-preview", action="store_true", help="不生成 preview.html")
    args = ap.parse_args()

    pack_dir, tmp_root = prepare_src(args.src)
    try:
        convert(pack_dir, args.out, size=max(8, min(args.size, 128)), name=args.name,
                preview=not args.no_preview)
    finally:
        if tmp_root:
            shutil.rmtree(tmp_root, ignore_errors=True)


if __name__ == "__main__":
    main()
