# 框架接入手册

转换产物(下称 `<pack>` 目录):`svg/<state>/*.svg` 帧图、`cursor.js`(单文件,
数据内嵌)、`data.js`、`preview.html`。**接入 = 拷目录 + 加一行 script**,但每个
框架的"静态目录在哪、往哪注入、子路径怎么写"不同,按下表处理。

## 框架检测(按优先级看文件)

| 看到什么 | 类型 |
|---|---|
| `astro.config.*` | Astro |
| `hugo.toml` / `config.toml` 含 `hugo` | Hugo |
| `package.json` 依赖含 `hexo` | Hexo |
| `.vitepress/` | VitePress |
| `.vuepress/` | VuePress |
| `package.json` 依赖含 `next` | Next.js |
| `nuxt.config.*` | Nuxt |
| `wp-content/` | WordPress |
| 只有 `*.html` | 纯静态 HTML |

## 纯静态 HTML(含多页站)

- 资源:站点根建 `cursors/<pack>/`,整个输出目录拷入。
- 注入:每个页面 `</body>` 前(或 `<head>` 加 `defer`):
  `<script src="cursors/<pack>/cursor.js" defer></script>`
- 相对路径随页面深度变化,深层页面写 `../` 或用绝对路径;file:// 直开也能用。
- 多页站每个页面都要加。

## Astro

- 资源:`public/cursors/<pack>/`。
- 注入:布局组件(通常是 `src/layouts/Layout.astro` 或主题的 `BaseHead.astro`)里:
  ```astro
  <script is:inline src="/cursors/<pack>/cursor.js" defer></script>
  ```
- **坑:必须 `is:inline`**。Astro 默认会处理裸 `<script>`(打包/改写),加 `is:inline`
  才原样输出。这是 Astro 接入唯一高频翻车点。
- 子路径部署(base 配置过):`src={`${import.meta.env.BASE_URL}cursors/<pack>/cursor.js`}`。
- 验证:`npm run dev` 后检查 Network。

## Hexo

- 资源:`source/cursors/<pack>/`(会原样拷到 public;**别放原始 .ani/.cur**,8MB+ 会被
  原样部署)。
- 注入(推荐,与主题无关):站点根建 `scripts/cursor.js`(Hexo 的扩展目录,不是前端 js):
  ```js
  hexo.extend.injector.register('body_end', '<script src="/cursors/<pack>/cursor.js" defer></script>');
  ```
  也可改主题布局 head(`themes/<t>/layout/*.ejs` 找 `</head>`)——换主题会丢,不推荐。
- 子路径:把 `src` 写成 `<%- url_for('cursors/<pack>/cursor.js') %>`(注入器里用
  `hexo.config.root` 拼接)。
- 验证:`hexo clean && hexo server`。

## Hugo

- 资源:`static/cursors/<pack>/`(或 `assets/` 走管道,静态目录最简单)。
- 注入:项目级 `layouts/partials/head/custom.html`(大多数主题预留了该扩展点,没有就
  查主题文档找 head 扩展 partial;再没有就把主题的 baseof/head partial 拷到项目
  `layouts/` 同路径覆盖,**不要直接改 themes/ 下的文件**——升级会丢)。
- 子路径:用 Hugo 的 URL 管道,别写死 `/`:
  `<script src="{{ "cursors/<pack>/cursor.js" | relURL }}" defer></script>`。
- 验证:`hugo server`,生成的 public/ 里抽查 cursors/ 是否在。

## VitePress / VuePress

- 资源:`docs/.vitepress/public/cursors/<pack>/`(VitePress)或 `docs/.vuepress/public/`。
- 注入:config 的 `head` 数组(VitePress 在 `.vitepress/config.*`):
  ```js
  head: [['script', { src: '/cursors/<pack>/cursor.js', defer: '' }]]
  ```
- 子路径:配置了 `base` 就把 `src` 前缀改成 base 值。
- 验证:`npm run docs:dev`。

## Next.js / Nuxt / 其他 SPA

- 资源一律进 `public/`(Nuxt 3 同)。
- Next.js 注入:`app/layout.tsx` 里 `import Script from "next/script"` 后
  `<Script strategy="afterInteractive" src="/cursors/<pack>/cursor.js" />`;pages 路由放
  `pages/_app.tsx`。next/image 无关,不需要处理。
- Nuxt 注入:`nuxt.config.ts` 的 `app.head.script: [{ src: '/cursors/<pack>/cursor.js', defer: true }]`。
- SPA 路由切换不会丢:运行时的 CSS 变量挂在 `document.documentElement` 上。

## WordPress

- 资源:子主题目录 `wp-content/themes/<child>/cursors/<pack>/`。
- 注入:子主题 `functions.php`:
  ```php
  add_action('wp_footer', function () {
    echo '<script src="' . get_stylesheet_directory_uri() . '/cursors/<pack>/cursor.js" defer></script>';
  });
  ```
- 坑:后台/编辑器界面不用接管,前台够用;缓存插件记得刷新。

## 通用陷阱

1. **绝对路径 `/cursors/...` 在子路径部署会 404**(如 `user.github.io/repo/`)。判断
   方法:看部署 URL 有没有仓库名后缀。运行时从 script 的 `src` 推导帧图基路径,所以
   只要 script 本身加载成功,帧图就一定对——**唯一要保证的是 script src 写对**。
2. 帧图目录名(`svg/<state>/`)是 data 里 frames 路径的一部分,别单独移动/改名。
3. 主题自带的 `cursor:pointer` 会被运行时的 `!important` 接管,这是预期行为。
4. 同一页面只接一个包;换包重新生成即可。
5. CDN 场景:整个输出目录可原样上传到 OSS/CDN,`cursor.js` 里写 `data-base` 或用
   `window.CURSOR_KIT_BASE` 指向 CDN 前缀。
