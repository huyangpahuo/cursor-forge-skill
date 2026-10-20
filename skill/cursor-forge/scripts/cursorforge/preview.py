"""preview.html 生成:状态卡片/体验区/接入代码/动画开关。"""
import os

from .mapping import STATE_CN

# ---------------------------------------------------------------- preview.html

PREVIEW_TMPL = """<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>__PACK__ · 光标预览</title>
<style>
:root{color-scheme:dark}
*{box-sizing:border-box}
body{margin:0;min-height:100vh;background:#0f1115;color:#e6e8ee;
  font:15px/1.7 system-ui,"Segoe UI","Microsoft YaHei",sans-serif;padding:32px 20px 60px}
.wrap{max-width:960px;margin:0 auto}
h1{font-size:26px;margin:0 0 4px}
h1 small{font-size:14px;color:#8b93a7;font-weight:400;margin-left:10px}
.chips{display:flex;gap:8px;flex-wrap:wrap;margin:14px 0 26px}
.chip{background:#1a1e27;border:1px solid #2a3040;border-radius:99px;padding:3px 12px;
  font-size:12px;color:#aeb6c8}
h2{font-size:17px;margin:34px 0 12px;color:#c6cdda}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));gap:12px}
.card{background:#161a22;border:1px solid #232936;border-radius:12px;padding:14px}
.card .nm{font-weight:600}
.card .cn{color:#8b93a7;font-size:12px;margin-left:6px}
.card .meta{color:#6d7689;font-size:12px;margin-top:2px}
.card .strip{display:flex;gap:2px;margin-top:10px;overflow:hidden;height:40px;align-items:center}
.card .strip img{height:34px;width:auto}
.card:hover{border-color:#44507a}
.playground{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:12px}
.box{background:#161a22;border:1px solid #232936;border-radius:12px;padding:16px}
.box h3{margin:0 0 10px;font-size:14px;color:#aeb6c8;font-weight:600}
a.btnl{color:#7ab2ff;text-decoration:underline}
input[type=text],textarea,select{width:100%;background:#0f1115;color:#e6e8ee;
  border:1px solid #2a3040;border-radius:8px;padding:8px 10px;font:inherit;margin-top:6px}
.row{display:flex;gap:14px;align-items:center;margin-top:8px;flex-wrap:wrap}
button{background:#232b3f;color:#e6e8ee;border:1px solid #2f3a55;border-radius:8px;
  padding:7px 14px;font:inherit;cursor:pointer}
button.ghost{background:transparent}
button[disabled]{opacity:.4}
.snippet{position:relative;background:#0b0d12;border:1px solid #232936;border-radius:12px;
  padding:16px;font:13px/1.6 ui-monospace,Consolas,monospace;color:#9ecbff;
  white-space:pre-wrap;word-break:break-all}
.snippet button{position:absolute;top:10px;right:10px}
.foot{margin-top:30px;color:#6d7689;font-size:13px}
</style>
</head>
<body>
<div class="wrap">
  <h1>__PACK__<small>cursor-forge 光标预览</small></h1>
  <div class="chips">
    <span class="chip" id="chip-dpi">DPI 检测中</span>
    <span class="chip" id="chip-pointer">指针环境检测中</span>
    <span class="chip">__STATS__</span>
  </div>

  <h2>状态一览(把鼠标悬到卡片上,光标就会切换成该状态)</h2>
  <div class="grid">__CARDS__</div>

  <h2>真实元素体验区</h2>
  <div class="playground">
    <div class="box"><h3>链接与按钮</h3>
      <div class="row"><a class="btnl" href="#">我是链接</a>
        <button>按钮</button><button disabled>禁用</button></div></div>
    <div class="box"><h3>文本输入</h3><input type="text" placeholder="点我输入文字">
      <textarea placeholder="多行文本"></textarea></div>
    <div class="box"><h3>其他</h3><div class="row">
      <label><input type="checkbox">复选框</label>
      <select><option>下拉选择</option><option>第二项</option></select></div></div>
  </div>

  <h2>接入你的网站(一行代码)</h2>
  <div class="snippet" id="snippet">&lt;script src="<b>静态目录/__PACK__/cursor.js</b>" defer&gt;&lt;/script&gt;
&lt;!-- Astro 用 &lt;script is:inline src=...&gt;;Hexo/Hugo/VitePress 的注入方式见 skill 文档 --&gt;</div>
  <div class="foot">由 cursor-forge 生成 · 动画开关
    <button class="ghost" id="toggle">关闭光标动画</button></div>
</div>
<script src="./cursor.js" defer></script>
<script defer>
document.addEventListener("DOMContentLoaded", function () {
  var q = function (s) { return document.querySelector(s); };
  q("#chip-dpi").textContent = "devicePixelRatio " + window.devicePixelRatio +
    (window.matchMedia("(pointer: fine)").matches ? "" : "(自定义光标仅桌面显示)");
  q("#chip-pointer").textContent =
    (window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "已开启减少动态效果:停留在首帧" : "动画播放中");
  var btn = q("#toggle"), on = true;
  btn.addEventListener("click", function () {
    on = !on;
    var kit = window.CursorKit;
    if (kit) on ? kit.on() : kit.off();
    btn.textContent = on ? "关闭光标动画" : "开启光标动画";
  });
});
</script>
</body>
</html>
"""


def write_preview(out_dir, name, data):
    cards = []
    for st, entry in data["states"].items():
        frames = entry["frames"]
        imgs = "".join('<img src="./%s" alt="%s">' % (f, st)
                       for f in frames[:10])
        more = "…" if len(frames) > 10 else ""
        anim = "动画 %d 帧" % len(frames) if len(frames) > 1 else "静态"
        cards.append(
            '<div class="card" data-cursor="%s"><div class="nm">%s'
            '<span class="cn">%s</span></div>'
            '<div class="meta">%s · %dms/帧 · 热点(%d,%d)</div>'
            '<div class="strip">%s%s</div></div>' %
            (st, st, STATE_CN.get(st, ""), anim, entry["ms"][0],
             entry["hot"][0][0], entry["hot"][0][1], imgs, more))
    stats = "%d 状态 / %d 帧" % (
        len(data["states"]),
        sum(len(e["frames"]) for e in data["states"].values()))
    html = (PREVIEW_TMPL
            .replace("__PACK__", name)
            .replace("__CARDS__", "".join(cards))
            .replace("__STATS__", stats))
    with open(os.path.join(out_dir, "preview.html"), "w", encoding="utf-8") as f:
        f.write(html)


