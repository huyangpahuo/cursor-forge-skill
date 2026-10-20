# cursor-forge · 把 Windows 鼠标指针装进任何网站

AI Agent Skill:Windows 光标包(`.ani`/`.cur`)→ **一行代码接入**的网页自定义动画
鼠标指针。**全矢量 SVG 输出**,纯 HTML / Astro / Hexo / Hugo / VitePress / Vue /
Next / WordPress 通吃。

对 AI 说:"帮我把 XX 光标包做成我博客的鼠标指针"即可。

## 原理(为什么是 SVG)

浏览器 CSS `cursor` 不支持动画,但支持 `url(*.svg)` 并在**设备分辨率**上光栅化
矢量——任何 DPR/缩放档都锐利(位图光标在 125%/150% 屏必然发糊)。动画由内置
运行时逐帧换 url 实现(SVG 动画不会被播放)。

## 能力

| 能力 | 说明 |
|---|---|
| inf 权威映射 | 解析光标包安装 inf(Windows 官方角色映射,两种形态都解),中文文件名/一物多名不接错;缺失时中英文别名启发式兜底 |
| 压缩包直读 | 目录或 zip/7z/rar 压缩包直接作为输入:自动解压定位、嵌套压缩包最多解 3 层、老 zip 中文名按 GBK 还原、防 zip-slip;rar 依赖 WinRAR/7-Zip 或 Win10+ 自带 tar |
| 一行接入 | `cursor.js` = 运行时+数据合一;资源路径自动推导,子路径部署不翻车 |
| 全矢量 + 统一像素风格 | 每帧逐像素转 `<rect>` 行程合并 SVG,统一 crispEdges 硬边(以 Anya 光标为基准),半透明 fill-opacity 精确保留 |
| 大小统一 | 状态级联合画幅:同状态所有帧同尺寸容器,动画不脉动、状态间视觉一致 |
| 逐帧节奏 | .ani 的 rate 块逐帧时长如实还原 |
| 全状态 | 15+ 状态覆盖链接/文本/忙碌/禁用/帮助/缩放/手写笔/copy/alias/zoom…悬停真实元素即切换 |
| 健壮运行时 | 触屏跳过、减少动态效果停首帧、后台暂停、rAF 被抑制自动退化定时器、帧预加载 |
| 自带预览 | 产物含 preview.html:状态卡片、真实元素体验区、接入代码、动画开关 |
| 框架手册 | Astro `is:inline`/Hexo 注入器/Hugo partial/WP 函数等坑位已写成 Agent 可执行文档 |

黑方块修复:大量光标包透明度只在 1bit AND 掩码里(alpha 通道损坏或缺失),
解码后必须把掩码套到 alpha 上——这是"静态 .cur 变黑方块"的根因,已处理。

## 使用

```bash
pip install pillow py7zr rarfile
python scripts/cursor_convert.py <光标包目录或压缩包> <输出目录> [--size 32] [--name 包名]
```

输入直接给 zip/7z/rar 等压缩包也行(免手动解压;rar 依赖 WinRAR/7-Zip 之一,
或 Windows 10+ 自带的 tar 兜底)。

输出:`svg/<状态>/<i>.svg` + `cursor.js`(一行接入)+ `data.js` + `preview.html`。
安装 skill:整个 `cursor-forge/` 放进 `.agents/skills/`(项目)或
`~/.agents/skills/`(全局)。

## 目录

```
cursor-forge/
├── SKILL.md                          # Agent 工作流
├── scripts/
│   ├── cursor_convert.py             # CLI 入口(命令不变)
│   └── cursorforge/
│       ├── mapping.py                # 状态映射:inf 解析 + 文件名启发式
│       ├── cursorfmt.py              # .ani/.cur 二进制解析(含 AND 掩码修复)
│       ├── svgout.py                 # 像素 → 矢量 SVG
│       ├── pipeline.py               # 转换主流程
│       └── preview.py                # preview.html 生成
├── assets/cursor-runtime.js          # 运行时模板(数据内嵌点)
└── references/
    ├── windows-cursor-format.md      # 格式/坑位速查
    └── framework-adapters.md         # 框架接入手册
```

## 已实测

目录输入 + 压缩包直读全覆盖:zip(中文文件名/垃圾文件/双层目录)、7z、zip 套 zip、
六个真实 deviantart 风格 .rar(内层中文目录),输出与目录输入逐字节一致;形态上覆盖
Scheme 型 inf、逐角色 inf、1bpp 单色、无 inf 纯启发式、动画/静态混合。状态映射/
动画/热点/大小统一全部通过。

## 已知限制

Safari 不支持 svg 光标(落系统光标);iframe 内部接管不了;单帧 SVG 的
width/height ≤128px(浏览器硬限制)。
