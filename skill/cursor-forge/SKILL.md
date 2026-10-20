---
name: cursor-forge
description: Convert any Windows cursor pack (.ani/.cur, any naming/language, with or without Installer.inf) into one drop-in cursor.js that gives any website or blog — plain HTML, Astro, Hexo, Hugo, VitePress, Vue, React/Next, WordPress — fully animated custom mouse cursors as resolution-independent vector SVG frames, with correct hotspots, per-frame timing, uniform sizes and an auto-generated preview page. Use when the user mentions 鼠标指针/光标/自定义光标/指针包/pointer/cursor, hands over .ani or .cur files or a cursor pack folder/zip, wants animated cursors on their site or blog, or asks why .ani cursors don't work in browsers.
---

# Cursor Forge:Windows 光标包 → 网页动画鼠标指针(全矢量 SVG)

产出单文件 `cursor.js`(运行时+数据合一),接入只需一行 `<script src defer>`,
任何框架通用。每帧是精确矢量 SVG,浏览器在设备分辨率上光栅化——任何 DPR/缩放
都锐利。动画由 JS 逐帧换 url 实现(SVG 动画本身不会被播放)。

## 工作流

1. **识别输入**:光标包 = 目录,或**压缩包直接给**(zip/7z/rar 等,自动解压定位,
   嵌套压缩包最多解 3 层,免手动解压;rar 依赖 WinRAR/7-Zip 或 Win10+ 自带 tar)。
   包内 `.ani`(动画)/`.cur`(静态),通常含 `Installer.inf`(**权威角色映射,必读**);
   子目录(如"可替换素材")不处理。
2. **转换**(需 Python3 + `pip install pillow py7zr rarfile`):
   ```bash
   python scripts/cursor_convert.py <光标包目录或压缩包> <输出目录> [--size 32] [--name 包名]
   ```
   读终端映射表;"未识别"文件问用户是否要用 `data-cursor="<状态>"` 手动接。
3. **预览**:打开输出目录 `preview.html`(file:// 即可)。核对:状态映射正确、
   动画流畅、热点对位(箭头尖端 = 点击点)、各状态大小统一。
4. **接入**:按 [references/framework-adapters.md](references/framework-adapters.md)
   判断框架 → 整个输出目录拷进静态目录 → 注入一行 `<script defer>`。子路径部署
   (GitHub Pages 项目页)按手册各框架的写法处理。
5. **验证**:cursor.js 与若干 svg 返回 200;悬停链接→手指、聚焦输入框→文本;
   `--ck-normal` 变量值随时间变;模拟触屏无报错。
6. **交付**:帧目录 + cursor.js + preview.html + 已改的注入点。提醒:原始
   .ani/.cur 别放进静态目录。

## 硬限制(不可绕过)

- cursor 的 SVG width/height ≤128px,超限整条声明作废;
- **Safari 不支持 svg 光标** → 落到关键字兜底(系统光标),已知取舍;
- `url() x y` 热点必填且须在图内;iframe 内部接管不了;
- 运行时内置:触屏跳过、`prefers-reduced-motion` 停首帧、后台暂停、rAF 被抑制
  环境自动退化为定时器、pjax/SPA 安全。改 `assets/cursor-runtime.js` 前先懂这些。

## 资料

- [references/windows-cursor-format.md](references/windows-cursor-format.md)
  — .ani/.cur/inf 二进制结构、AND 掩码(黑方块坑)、浏览器行为、管线决策
- [references/framework-adapters.md](references/framework-adapters.md)
  — 各框架的静态目录、注入点、子路径写法、验证命令
