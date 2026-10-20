"""状态映射:inf 权威解析(两种形态)+ 中英文文件名启发式。"""
import os
import re

# ---------------------------------------------------------------- 状态映射表

# Windows 光标角色(inf 注册表键名,小写)-> 网页状态名
# 网页状态 = CSS cursor 关键字能表达的角色 + 若干扩展状态(经 data-cursor 属性使用)
ROLE_TO_STATE = {
    "arrow": "normal", "pointer": "normal",
    "help": "help",
    "appstarting": "working",
    "wait": "busy",
    "crosshair": "crosshair", "precisionhair": "crosshair",
    "ibeam": "text",
    "nwpen": "pen", "pen": "pen",
    "no": "unavailable",
    "sizens": "ns", "sizewe": "ew",
    "sizenwse": "nwse", "sizenesw": "nesw",
    "sizeall": "move",
    "uparrow": "alt",
    "hand": "link",
    "person": "person", "pin": "pin",
}

# "Schemes" 注册表值的逗号列表按 Windows 固定槽位顺序排列(前 15 个是经典顺序,
# Win10 起可能追加 Person/Pin),inf 里没有逐角色注册行时按位还原映射
SCHEME_ORDER = [
    "arrow", "help", "appstarting", "wait", "crosshair", "ibeam", "nwpen", "no",
    "sizens", "sizewe", "sizenwse", "sizenesw", "sizeall", "uparrow", "hand",
    "person", "pin",
]

# 文件名(去扩展名、去 _NNpx 后缀、转小写)-> 状态名;inf 缺失/漏文件时的兜底
# 收集自常见光标包命名,中英对照;exact 优先,substring 兜底
ALIAS_EXACT = {
    "normal": "normal", "arrow": "normal", "default": "normal", "regular": "normal",
    "aero_arrow": "normal", "cursor": "normal", "指针": "normal", "箭头": "normal",
    "link": "link", "link_select": "link", "linkselect": "link", "hand": "link",
    "handwriting": "pen", "手": "link", "手型": "link",
    "text": "text", "text_select": "text", "textselect": "text", "ibeam": "text",
    "beam": "text", "文本": "text", "插入": "text",
    "busy": "busy", "wait": "busy", "hourglass": "busy", "忙": "busy",
    "忙碌": "busy", "转圈": "busy", "等待": "busy", "沙漏": "busy",
    "working": "working", "working_background": "working", "background": "working",
    "app_starting": "working", "appstarting": "working", "工作": "working",
    "后台": "working", "无响应": "busy",
    "unavailable": "unavailable", "no": "unavailable", "blocked": "unavailable",
    "unavralible": "unavailable", "不可用": "unavailable", "禁止": "unavailable",
    "help_select": "help", "帮助": "help", "问号": "help", "？": "help",
    "move": "move", "sizeall": "move", "all_scroll": "move", "allscroll": "move",
    "drag": "move", "移动": "move", "上下左右": "move", "四向箭头": "move",
    "crosshair": "crosshair", "precision": "crosshair", "precision_select": "crosshair",
    "cell": "crosshair", "精确定位": "crosshair", "精确选择": "crosshair",
    "十字": "crosshair", "+": "crosshair",
    "horizontal": "ew", "ew": "ew", "ew_resize": "ew", "size_we": "ew",
    "col_resize": "ew", "左右": "ew", "水平": "ew", "←→": "ew",
    "vertical": "ns", "ns": "ns", "ns_resize": "ns", "size_ns": "ns",
    "row_resize": "ns", "上下": "ns", "垂直": "ns", "↑↓": "ns",
    "nwse": "nwse", "nwse_resize": "nwse", "size_nwse": "nwse",
    "diagonal_1": "nwse", "resize_1": "nwse", "diagonal1": "nwse", "↖↘": "nwse",
    "nesw": "nesw", "nesw_resize": "nesw", "size_nesw": "nesw",
    "diagonal_2": "nesw", "resize_2": "nesw", "diagonal2": "nesw", "↙↗": "nesw",
    "hardwriting": "pen", "笔": "pen", "手写": "pen", "nwpen": "pen",
    "alternate": "alt", "alternate_select": "alt", "uparrow": "alt",
    "候选": "alt", "备用": "alt",
    "person": "person", "person_select": "person", "人员": "person",
    "pin": "pin", "location": "pin", "位置": "pin",
    "×": "unavailable",
    # X11 / Linux 主题常见命名(连字符统一转下划线后匹配)
    "right_ptr": "normal", "x_cursor": "normal", "wayland_cursor": "normal",
    "left_side": "ew", "right_side": "ew", "top_side": "ns", "bottom_side": "ns",
    "bottom_left_corner": "nesw", "top_right_corner": "nesw",
    "bottom_right_corner": "nwse", "top_left_corner": "nwse",
    "center_ptr": "alt", "down_arrow": "alt", "left_arrow": "alt", "up_arrow": "alt",
    "dnd_move": "move", "dnd_no_drop": "unavailable", "no_drop": "unavailable",
    "not_allowed": "unavailable", "color_picker": "crosshair",
    "context_menu": "link", "pointer": "link",
    # CSS 有对应关键字、但无 Windows 角色的扩展状态(经 data-cursor 使用)
    "copy": "copy", "alias": "alias", "zoom_in": "zoom-in", "zoom_out": "zoom-out",
    # cir*/dot* 风格前缀(同状态的另一种样式,已占用则自动跳过)
    "cirew": "ew", "cirns": "ns", "cirnwse": "nwse", "cirnesw": "nesw",
    "cirmove": "move", "cirall": "move",
    "dotew": "ew", "dotns": "ns", "dotnwse": "nwse", "dotnesw": "nesw",
    "dotmove": "move", "dotall": "move",
}
# 子串匹配兜底(按顺序,先命中先用;比如 "help_select" 先被 exact 吃掉,这里是救 "Help Selector" 这类)
ALIAS_SUBSTR = [
    ("nwse", "nwse"), ("nesw", "nesw"), ("↖↘", "nwse"), ("↙↗", "nesw"),
    ("horizontal", "ew"), ("vertical", "ns"), ("←→", "ew"), ("↑↓", "ns"),
    ("link", "link"), ("hand", "link"), ("手", "link"),
    ("text", "text"), ("ibeam", "text"), ("文本", "text"),
    ("busy", "busy"), ("wait", "busy"), ("转圈", "busy"), ("无响应", "busy"),
    ("working", "working"), ("后台", "working"),
    ("unavail", "unavailable"), ("不可用", "unavailable"), ("blocked", "unavailable"),
    ("help", "help"), ("帮助", "help"), ("问号", "help"),
    ("move", "move"), ("sizeall", "move"), ("上下左右", "move"),
    ("precision", "crosshair"), ("crosshair", "crosshair"), ("精确定位", "crosshair"),
    ("pen", "pen"), ("笔", "pen"), ("手写", "pen"),
    ("alternate", "alt"), ("候选", "alt"),
    ("normal", "normal"), ("arrow", "normal"), ("指针", "normal"), ("busy", "busy"),
]

STATE_CN = {
    "normal": "常规选择", "link": "链接/手指", "text": "文本输入", "busy": "忙碌",
    "working": "后台工作", "unavailable": "不可用", "help": "帮助", "move": "移动",
    "crosshair": "精确定位", "ew": "左右调整", "ns": "上下调整", "nwse": "对角调整↖↘",
    "nesw": "对角调整↙↗", "pen": "手写笔", "alt": "向上箭头/备用", "person": "人员选择",
    "pin": "位置选择", "copy": "复制", "alias": "别名/快捷方式",
    "zoom-in": "放大", "zoom-out": "缩小",
}

# ---------------------------------------------------------------- .inf 解析


def read_text_guess(path):
    """inf 常见 GBK 编码。只认带 BOM 的 UTF-16(GBK 字节盲解 UTF-16 会"成功"出乱码),
    其余依次试 UTF-8(严格)与 GBK。"""
    raw = open(path, "rb").read()
    if raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return raw.decode("utf-16")
    for enc in ("utf-8-sig", "gbk"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("gbk", errors="replace")


def parse_inf(path):
    """解析安装 inf,返回 {状态名: 文件名}。两种形态:
    1) 逐角色注册行:HKCU,"Control Panel\\Cursors",<Role>,0x...,"%...\\file.ani"
    2) Scheme 字符串:HKCU,"Control Panel\\Cursors\\Schemes",...,"f1,f2,..."(按 SCHEME_ORDER 还原)
    """
    text = read_text_guess(path)
    lines = []
    for ln in text.splitlines():
        ln = ln.strip()
        if not ln or ln.startswith(";") or ln.startswith("//"):
            continue
        lines.append(ln)

    # [Strings] 段:KEY = "值"(引号可省)
    strings = {}
    section = ""
    for ln in lines:
        m = re.match(r"^\[(.+?)\]", ln)
        if m:
            section = m.group(1).strip().lower()
            continue
        if section == "strings":
            m = re.match(r"^([^=]+?)\s*=\s*(.*)$", ln)
            if m:
                val = m.group(2).strip()
                if len(val) >= 2 and val[0] == '"' and val[-1] == '"':
                    val = val[1:-1]
                strings[m.group(1).strip().lower()] = val

    def subst(s):
        # %KEY% 用 [Strings] 替换;未知占位符(%10% 这类系统目录)删掉
        return re.sub(r"%([^%]+)%",
                      lambda m: strings.get(m.group(1).lower(), ""), s)

    def basename(p):
        return os.path.basename(p.replace("\\", "/")).strip().lower()

    roles = {}

    # 形态 1:逐角色行(可能出现在任意注册段)
    for ln in lines:
        m = re.match(
            r'HKCU\s*,\s*"Control Panel\\Cursors"\s*,\s*([A-Za-z_]+)\s*,.*?"([^"]*)"\s*$',
            ln)
        if m:
            role = m.group(1).lower()
            state = ROLE_TO_STATE.get(role)
            if state:
                fn = basename(subst(m.group(2)))
                if fn:
                    roles[state] = fn

    # 形态 2:Scheme 字符串(仅当形态 1 一条都没命中时使用,避免互相覆盖)
    if not roles:
        for ln in lines:
            if '"Control Panel\\Cursors\\Schemes"' not in ln:
                continue
            m = re.search(r',\s*"([^"]*,[^"]*)"\s*$', ln)
            if not m:
                continue
            items = [basename(subst(x)) for x in subst(m.group(1)).split(",")]
            for i, fn in enumerate(items):
                if i < len(SCHEME_ORDER) and fn:
                    roles[ROLE_TO_STATE[SCHEME_ORDER[i]]] = fn
            break

    return roles



def resolve_state_by_name(stem):
    """文件名启发式:先 exact,再子串。返回状态名或 None(表示未知)。"""
    s = stem.lower().strip()
    s = re.sub(r"[_\-\s]?\d{2,3}px$", "", s)  # 转圈_32px -> 转圈
    s = re.sub(r"[\s\-]+", "_", s)  # X11 风格连字符 -> 下划线
    if s in ALIAS_EXACT:
        return ALIAS_EXACT[s]
    for sub, state in ALIAS_SUBSTR:
        if sub in s:
            return state
    return None

