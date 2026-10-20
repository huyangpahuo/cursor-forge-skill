# -*- coding: utf-8 -*-
"""压缩包直读:zip/7z/rar 等自动解压并定位光标包目录,用户无需手动解压。

分层策略:zip 走标准库;7z/rar 优先 Python 库;失败退 CLI(7z -> Windows 自带
tar/bsdtar)。解压到临时目录,定位含 .ani/.cur 最多的目录;嵌套压缩包(下载站
常见 zip 套 zip)自动再解,最多 3 层。调用方负责用完清理返回的临时根目录。
"""

import os
import shutil
import subprocess
import tempfile
import zipfile

CURSOR_EXTS = (".ani", ".cur")
ARCHIVE_EXTS = (".zip", ".7z", ".rar", ".cab", ".iso", ".tar", ".gz", ".bz2", ".xz")
WINRAR_CANDIDATES = (
    r"C:\Program Files\WinRAR\UnRAR.exe",
    r"C:\Program Files\WinRAR\WinRAR.exe",
    r"C:\Program Files (x86)\WinRAR\UnRAR.exe",
)
BSDTAR = r"C:\Windows\System32\tar.exe"


def prepare_src(src):
    """输入是目录 -> 原样返回;是压缩包 -> 解压并定位包目录。
    返回 (包目录, 临时根目录或 None;调用方 finally 里 shutil.rmtree 清理)。"""
    if os.path.isdir(src):
        return src, None
    if not os.path.isfile(src):
        raise SystemExit("错误:输入不存在 %s" % src)
    if not src.lower().endswith(ARCHIVE_EXTS):
        raise SystemExit("错误:不支持的文件类型 %s(支持目录或 %s 压缩包)" %
                         (os.path.basename(src), "/".join(ARCHIVE_EXTS[:3])))
    root = tempfile.mkdtemp(prefix="cursorforge_")
    try:
        staged = os.path.join(root, "pack")
        _extract(src, staged)
        pack = _locate(staged, depth=0)
        if not pack:
            raise SystemExit("错误:压缩包里找不到 .ani/.cur 文件(嵌套超过 3 层,或不是光标包)")
        return pack, root
    except Exception:
        shutil.rmtree(root, ignore_errors=True)
        raise


def _extract(archive, dest):
    """按格式选解压器,逐个尝试,全部失败给出可操作的提示。"""
    os.makedirs(dest, exist_ok=True)
    low = archive.lower()
    if low.endswith(".zip"):
        handlers = [_extract_zip]
    elif low.endswith(".7z"):
        handlers = [_extract_7z_lib, _extract_cli_7z, _extract_cli_bsdtar]
    elif low.endswith(".rar"):
        handlers = [_extract_rar_lib, _extract_cli_7z, _extract_cli_bsdtar]
    else:
        handlers = [_extract_cli_7z, _extract_cli_bsdtar]

    errors = []
    for h in handlers:
        try:
            h(archive, dest)
            if os.listdir(dest):
                return
            errors.append("%s: 解出内容为空" % h.__name__)
        except Exception as e:
            errors.append("%s: %s" % (h.__name__, e))
            for f in os.listdir(dest):
                p = os.path.join(dest, f)
                shutil.rmtree(p, ignore_errors=True) if os.path.isdir(p) else os.remove(p)
    raise SystemExit("解压失败:%s\n  尝试过 %s\n  建议:pip install py7zr rarfile,"
                     "或安装 7-Zip / WinRAR 后重试" %
                     (os.path.basename(archive), ";".join(errors)))


def _extract_zip(archive, dest):
    with zipfile.ZipFile(archive) as zf:
        real_dest = os.path.realpath(dest)
        for info in zf.infolist():
            name = info.filename
            # 无 UTF-8 标记的老压缩包:中文文件名按 GBK 还原(zipfile 默认按 cp437 解)
            if not info.flag_bits & 0x800:
                try:
                    name = name.encode("cp437").decode("gbk")
                except (UnicodeEncodeError, UnicodeDecodeError):
                    pass
            parts = [p for p in name.replace("\\", "/").split("/") if p not in ("", ".")]
            if not parts or parts[0] == "__MACOSX" or any(p.startswith(".") for p in parts):
                continue  # 系统垃圾/隐藏文件
            target = os.path.realpath(os.path.join(dest, *parts))
            if not target.startswith(real_dest + os.sep):
                continue  # zip-slip 防护
            if name.endswith("/"):
                os.makedirs(target, exist_ok=True)
                continue
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with zf.open(info) as s, open(target, "wb") as o:
                shutil.copyfileobj(s, o)


def _extract_7z_lib(archive, dest):
    import py7zr
    with py7zr.SevenZipFile(archive) as z:
        z.extractall(dest)


def _extract_rar_lib(archive, dest):
    import rarfile
    for exe in WINRAR_CANDIDATES:  # rarfile 需要外部解压器,优先复用已装的 WinRAR
        if os.path.exists(exe):
            rarfile.UNRAR_TOOL = exe
            break
    rarfile.RarFile(archive).extractall(dest)


def _extract_cli_7z(archive, dest):
    exe = shutil.which("7z") or shutil.which("7za")
    if not exe:
        raise FileNotFoundError("7z 不在 PATH")
    subprocess.run([exe, "x", archive, "-y", "-o" + dest],
                   check=True, capture_output=True)


def _extract_cli_bsdtar(archive, dest):
    exe = BSDTAR if os.path.exists(BSDTAR) else shutil.which("bsdtar")
    if not exe:
        raise FileNotFoundError("无 bsdtar")
    subprocess.run([exe, "-xf", archive, "-C", dest],
                   check=True, capture_output=True)


def _locate(root, depth):
    """定位光标包目录:.ani/.cur 最多者胜;一个都没有则解嵌套压缩包再找。"""
    best, best_n = None, 0
    for dp, _, fs in os.walk(root):
        n = sum(1 for f in fs if f.lower().endswith(CURSOR_EXTS))
        if n > best_n:
            best, best_n = dp, n
    if best:
        return best
    if depth >= 2:
        return None
    archives = sorted((os.path.join(dp, f) for dp, _, fs in os.walk(root)
                       for f in fs if f.lower().endswith((".zip", ".7z", ".rar"))),
                      key=os.path.getsize, reverse=True)
    if not archives:
        return None
    nested = os.path.join(os.path.dirname(root.rstrip("/\\")), "nested%d" % (depth + 1))
    _extract(archives[0], nested)
    return _locate(nested, depth + 1)
