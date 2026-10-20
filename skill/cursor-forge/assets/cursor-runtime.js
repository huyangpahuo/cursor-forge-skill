/**
 * cursor-runtime.js — cursor-forge 的前端运行时
 *
 * 两种用法:
 *   1) 推荐:由 cursor_convert.py 生成的 cursor.js = 本文件 + 数据内嵌,
 *      接入只需一行:<script src="<静态目录>/<包名>/cursor.js" defer></script>
 *   2) 分离:先引 data.js(定义 window.CURSOR_KIT_DATA),再引本文件原样拷贝。
 *
 * 行为要点(改动前请确认理解,这些都是踩过坑换来的):
 *   - 资源基路径从本脚本自身的 src 推导,支持子路径部署(GitHub Pages 项目页等);
 *     动态注入场景可给 <script> 加 data-base="..." 或预设 window.CURSOR_KIT_BASE;
 *   - 自行注入 <style>:html 常规态 + 链接/文本/禁用/忙碌等元素态 + 每个状态的
 *     [data-cursor="<状态>"] 规则,全部 var() 静态兜底 + 关键字兜底 + !important
 *     (cursor 是纯装饰属性,接管站点散落的 cursor:pointer 不会破坏交互);
 *   - 动画 = rAF 单循环逐状态推进,按每帧各自的 ms(数据里是数组);
 *   - 光标为全矢量 SVG,与 DPR 无关,任何缩放档都锐利,单档声明无歧义;
 *   - 只在 (pointer:fine) 且未开启"减少动态效果"时才跑动画,否则停在首帧;
 *   - 全部帧预加载,避免状态切换瞬间闪回系统指针;
 *   - 标签页切到后台暂停,回来重置计时避免连跳;
 *   - window.CursorKit 提供 pack/states/base 与 on()/off() 开关,预览页会用到。
 */
(function () {
  "use strict";

  var DATA = /*__CURSOR_DATA__*/null || window.CURSOR_KIT_DATA;
  if (!DATA || !DATA.states) return;

  var root = document.documentElement;
  var styleEl = null;
  var rafId = null;
  var running = false;
  var timers = {};

  // ---- 资源基路径 -----------------------------------------------------------
  var base = "";
  var el = document.currentScript;
  if (el) {
    if (el.dataset && el.dataset.base) {
      base = el.dataset.base;
    } else if (el.src) {
      base = el.src.replace(/[^\/]*\.js(\?.*)?$/, "");
    }
  } else if (window.CURSOR_KIT_BASE) {
    base = window.CURSOR_KIT_BASE;
  }

  // ---- 工具 -----------------------------------------------------------------
  var KEYWORD = {
    normal: "auto", link: "pointer", text: "text", busy: "wait",
    working: "progress", unavailable: "not-allowed", help: "help",
    move: "move", crosshair: "crosshair", ew: "ew-resize", ns: "ns-resize",
    nwse: "nwse-resize", nesw: "nesw-resize", pen: "text", alt: "auto",
    person: "pointer", pin: "pointer", copy: "copy", alias: "alias",
    "zoom-in": "zoom-in", "zoom-out": "zoom-out",
  };

  // 命令式选择器 -> 状态(元素该显示什么光标由语义决定,不靠 data-cursor)
  var RULES = {
    link: 'a,button,[role="button"],label,select,summary,.btn,' +
      'input[type="button"],input[type="submit"],input[type="reset"],' +
      'input[type="checkbox"],input[type="radio"],input[type="file"],' +
      'input[type="color"],input[type="range"]',
    text: 'input[type="text"],input[type="search"],input[type="password"],' +
      'input[type="email"],input[type="url"],input[type="tel"],' +
      'input[type="number"],input[type="date"],input[type="time"],' +
      'input[type="datetime-local"],input[type="month"],input[type="week"],' +
      'textarea,[contenteditable="true"],[contenteditable=""]',
    busy: '[aria-busy="true"]',
    unavailable: '[disabled],[aria-disabled="true"]',
    move: '[draggable="true"]',
  };
  var UTIL_CLASSES = {
    ew: ".ew-resize,.col-resize",
    ns: ".ns-resize,.row-resize",
    nwse: ".nwse-resize",
    nesw: ".nesw-resize",
  };

  function q(path) {
    return 'url("' + (base + path).replace(/"/g, "%22") + '")';
  }

  // 第 i 帧的 cursor url(SVG 矢量与 DPR 无关,单档声明无歧义)
  function urls(st, i) {
    var f = st.frames[i], h = st.hot[i];
    return f ? q(f) + " " + h[0] + " " + h[1] : "";
  }

  function paint(key, i) {
    var v = urls(DATA.states[key], i);
    if (v) root.style.setProperty("--ck-" + key, v);
  }

  function injectStyle() {
    if (styleEl) return;
    var css = [];
    // 每个状态先给一条 [data-cursor] 通用规则,再叠元素语义规则
    Object.keys(DATA.states).forEach(function (key) {
      var v0 = urls(DATA.states[key], 0);
      var kw = KEYWORD[key] || "auto";
      css.push('[data-cursor="' + key + '"]{cursor:var(--ck-' + key + "," + v0 +
               ")," + kw + " !important}");
    });
    Object.keys(RULES).forEach(function (key) {
      if (!DATA.states[key]) return;
      var v0 = urls(DATA.states[key], 0);
      css.push(RULES[key] + "{cursor:var(--ck-" + key + "," + v0 + ")," +
               (KEYWORD[key] || "auto") + " !important}");
    });
    Object.keys(UTIL_CLASSES).forEach(function (key) {
      if (!DATA.states[key]) return;
      var v0 = urls(DATA.states[key], 0);
      css.push(UTIL_CLASSES[key] + "{cursor:var(--ck-" + key + "," + v0 + ")," +
               (KEYWORD[key] || "auto") + " !important}");
    });
    if (DATA.states.normal) {
      var v0 = urls(DATA.states.normal, 0);
      css.push("html,body{cursor:var(--ck-normal," + v0 + "),auto !important}");
    }
    styleEl = document.createElement("style");
    styleEl.id = "cursor-kit-style";
    styleEl.textContent = css.join("\n");
    document.head.appendChild(styleEl);
  }

  function preload() {
    Object.keys(DATA.states).forEach(function (key) {
      DATA.states[key].frames.forEach(function (f) {
        var img = new Image();
        img.src = base + f;
      });
    });
  }

  // ---- 动画循环 -------------------------------------------------------------
  var animated = [];
  var rafId = null;
  var tid = null;        // 退化模式的定时器句柄
  var watchdogId = null;
  var degraded = false;  // rAF 被环境抑制时退化为 setTimeout 驱动
  var lastTickAt = 0;

  function advance(now) {
    for (var i = 0; i < animated.length; i++) {
      var key = animated[i];
      var st = DATA.states[key];
      var t = timers[key];
      if (now >= t.next) {
        var dur = st.ms[t.frame] || 100;
        t.next = Math.max(t.next + dur, now);
        t.frame = (t.frame + 1) % st.frames.length;
        paint(key, t.frame);
      }
    }
  }

  function nextDelay(now) {
    var d = 100;
    for (var i = 0; i < animated.length; i++) {
      var t = timers[animated[i]];
      if (t) d = Math.min(d, Math.max(4, t.next - now));
    }
    return d;
  }

  function loop(now) {
    lastTickAt = now;
    advance(now);
    if (degraded) {
      tid = setTimeout(function () { loop(performance.now()); },
                       nextDelay(performance.now()));
    } else {
      rafId = requestAnimationFrame(loop);
    }
  }

  function startLoop() {
    var fine = window.matchMedia("(pointer: fine)").matches;
    var calm = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (!fine || calm || !animated.length || rafId || tid) return;
    degraded = false;
    var now = performance.now();
    lastTickAt = now;
    animated.forEach(function (key) {
      timers[key].next = now + (DATA.states[key].ms[0] || 100);
    });
    rafId = requestAnimationFrame(loop);
    // 看门狗:有些环境 rAF 永不回调(被遮挡的 webview、部分内嵌浏览器),
    // 300ms 无心跳就退化为定时器驱动,光标不至于停在首帧
    if (watchdogId) clearInterval(watchdogId);
    watchdogId = setInterval(function () {
      if (degraded || !rafId || !running) return;
      if (performance.now() - lastTickAt > 300) {
        degraded = true;
        cancelAnimationFrame(rafId);
        rafId = null;
        loop(performance.now());
      }
    }, 250);
  }

  function stopLoop() {
    if (rafId) {
      cancelAnimationFrame(rafId);
      rafId = null;
    }
    if (tid) {
      clearTimeout(tid);
      tid = null;
    }
    if (watchdogId) {
      clearInterval(watchdogId);
      watchdogId = null;
    }
  }

  document.addEventListener("visibilitychange", function () {
    if (document.hidden) {
      stopLoop();
    } else if (running) {
      startLoop();
    }
  });

  // ---- 启动 / 开关 ----------------------------------------------------------
  function init() {
    if (running) return;
    running = true;
    injectStyle();
    preload();
    animated = [];
    Object.keys(DATA.states).forEach(function (key) {
      var st = DATA.states[key];
      timers[key] = { frame: 0, next: 0 };
      paint(key, 0); // 立即铺首帧,把热点正确的光标顶上去
      if (st.frames.length > 1) animated.push(key);
    });
    startLoop();
  }

  function shutdown() {
    running = false;
    stopLoop();
    if (styleEl) {
      styleEl.remove();
      styleEl = null;
    }
    Object.keys(DATA.states).forEach(function (key) {
      root.style.removeProperty("--ck-" + key);
    });
  }

  init();

  window.CursorKit = {
    version: "2.0",
    pack: DATA.pack,
    states: Object.keys(DATA.states),
    base: base,
    on: init,
    off: shutdown,
  };
})();
