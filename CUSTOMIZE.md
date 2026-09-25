# 外观定制指南

本文档说明如何自定义本站外观，**核心原则是：不修改 `themes/PaperMod/` 里的任何文件**，
所有定制都放在项目根目录，这样主题升级时你的改动不会被覆盖。

---

## 一、原理：Hugo 的查找顺序

Hugo 找模板和资源时，按以下优先级：

```
1. 项目根的 layouts/ 、assets/ 、static/
2. themes/<主题名>/layouts/ 、assets/ 、static/
```

**同名文件，项目根目录的会完全覆盖主题的。** 这就是所有定制手段的基础。

---

## 二、四种定制方式（由浅入深）

### 方式 1：改配置（零代码）

编辑 `hugo.yaml`。主题通常暴露大量开关，例如：

```yaml
params:
  ShowReadingTime: true      # 是否显示阅读时间
  ShowShareButtons: false    # 是否显示分享按钮
  ShowCodeCopyButtons: true  # 代码块复制按钮
  defaultTheme: auto         # auto / light / dark
```

**优先用这种方式**，最稳，主题升级零影响。

---

### 方式 2：追加 CSS（推荐，最常用）

**任何放在 `assets/css/extended/` 下的 `.css` 文件都会被自动加载**，
并追加到主题样式之后，所以你的规则天然拥有更高优先级。

```
assets/css/extended/
├── chinese-typography.css   # 已有的：中文排版
└── my-theme-color.css       # 想加什么就新建一个
```

> 目前已有的文件：`chinese-typography.css`，负责中文字体栈、行高、代码块、表格等排版。

---

### 方式 3：覆盖局部模板（partial）

主题把页面拆成许多小片段。想改某个片段：

```bash
# 1. 复制主题的片段到项目根
mkdir -p layouts/partials
cp themes/PaperMod/layouts/_partials/footer.html layouts/partials/footer.html

# 2. 编辑 layouts/partials/footer.html
#    只改这个文件，主题其他部分照常工作
```

常用片段位置：

| 片段 | 作用 |
|---|---|
| `_partials/head.html` | `<head>` 区域，加统计脚本、字体等 |
| `_partials/footer.html` | 页脚 |
| `_partials/home_info.html` | 首页大标题区 |
| `_partials/header.html` | 顶部导航 |
| `_partials/extend_head.html` | 空钩子，专门给你插入代码用 |

> 💡 注意主题用的是 `layouts/_partials/`（新式），Hugo 也兼容 `layouts/partials/`，
> 两者都能被识别。

---

### 方式 4：重写整个页面布局

最彻底。想完全控制某类页面的 HTML：

```
layouts/
├── _default/single.html    # 所有文章页
├── _default/list.html      # 所有列表页
├── index.html              # 首页
└── 404.html                # 404 页面
```

---

## 三、换配色：覆盖 CSS 变量

这是改主题色**最稳的方式**——变量名是主题的公开接口，升级不会失效。

新建 `assets/css/extended/my-theme-color.css`：

```css
/* 亮色 */
:root {
    --theme: rgb(255, 255, 255);   /* 页面背景 */
    --entry: rgb(255, 255, 255);   /* 卡片背景 */
    --primary: rgb(30, 30, 30);    /* 主文字 / 标题 */
    --secondary: rgb(108, 108, 108); /* 次要文字 */
    --tertiary: rgb(214, 214, 214);  /* 更浅的线条 */
    --content: rgb(31, 31, 31);    /* 正文 */
    --code-bg: rgb(245, 245, 245); /* 行内代码底色 */
    --border: rgb(238, 238, 238);  /* 边框 */
    --radius: 8px;                 /* 圆角 */
    --gap: 24px;                   /* 元素间距 */
}

/* 暗色（注意选择器写法） */
:root[data-theme="dark"] {
    --theme: rgb(29, 30, 32);
    --primary: rgb(218, 218, 219);
    --content: rgb(196, 196, 197);
    /* ... */
}
```

**完整变量表**在 `themes/PaperMod/assets/css/core/theme-vars.css`，可直接查看。

---

## 四、已做过的定制记录

| 项目 | 位置 | 说明 |
|---|---|---|
| 中文排版 | `assets/css/extended/chinese-typography.css` | 字体栈、行高 1.85、代码块、表格、引用块 |
| 页脚版权 | `hugo.yaml` 的 `startYear` + 覆盖的 `footer.html` | 建站当年显示 `© 2026`，之后自动变成区间 |
| 甜瓜图标 | `static/` + `make_favicon.py` | 见 README |

> 页脚**覆盖了模板**——因为要移除主题硬编码的 “Powered by” 署名，
> 并让版权年份自动生成。见下方说明。

### 版权年份如何自动更新

年份按「**建站年 – 当前年**」自动生成，**跨年后无需手动修改**：

```yaml
copyright: ""          # 留空则用下面的自动逻辑；填了则优先用填的内容

params:
  startYear: 2026      # 建站年份
```

模板逻辑在 `layouts/_partials/footer.html`：

```go
{{- $startYear := site.Params.startYear | default 2026 }}
{{- $currentYear := now.Year }}
{{- $yearText := cond (eq $startYear $currentYear)
        (printf "%d" $currentYear)
        (printf "%d–%d" $startYear $currentYear) }}
```

效果：

| 构建年份 | 页脚显示 |
|---|---|
| 2026（建站当年） | `© 2026 Chino. All rights reserved.` |
| 2027 | `© 2026–2027 Chino. All rights reserved.` |
| 2030 | `© 2026–2030 Chino. All rights reserved.` |

**起始年与当前年相同时只显示一个年份**，出现时间跨度后才变成区间。

署名取 `params.author`，改作者名只需动配置，不用碰模板。

> 📌 **注意**：别把年份写死在 `copyright` 里。硬编码的问题是它永远不会变，
> 到了明年就变成错误信息了。这个坑本站踩过一次。

### 如何只保留版权、去掉页脚的其余部分

PaperMod 的页脚由三段组成，前两段可以通过配置控制：

```yaml
copyright: ""              # 第一段：版权（留空则自动生成年份区间）

params:
  footer:
    hideCopyright: false   # false = 显示版权；true = 完全隐藏
    text: ""               # 第二段：自定义文字，留空即不显示
```

第三段 “Powered by Hugo & PaperMod” 是主题硬编码在
`themes/PaperMod/layouts/_partials/footer.html` 里的，**没有配置开关**。
若确实想去掉，只能覆盖该模板（方式 3）：

```bash
mkdir -p layouts/_partials
cp themes/PaperMod/layouts/_partials/footer.html layouts/_partials/footer.html
# 然后删掉其中 “Powered by” 那个 <span> 区块
```

> ⚠️ 主题作者请求保留这行署名。若移除，建议在别处（如关于页）注明使用了 Hugo 与 PaperMod。

---

## 五、常用改动速查

### 加网站统计（如 Google Analytics）

在 `hugo.yaml` 加：

```yaml
services:
  googleAnalytics:
    ID: G-XXXXXXXXXX
```

或复制 `extend_head.html` 钩子自行插入脚本。

### 加「关于」页面

```bash
hugo new content about.md
```

然后编辑 `content/about.md`，并把 front matter 改成：

```yaml
---
title: "关于"
layout: "page"
---
```

最后在 `hugo.yaml` 的 `menu.main` 里加一项：

```yaml
    - identifier: about
      name: 关于
      url: /about/
      weight: 15
```

### 改首页大标题

`hugo.yaml` → `params.homeInfoParams` 的 `Title` 和 `Content`。

### 加自定义字体

在 `assets/css/extended/` 新建 CSS：

```css
@font-face {
    font-family: "LXGW WenKai";
    src: url("/fonts/lxgw-wenkai.woff2") format("woff2");
    font-display: swap;
}

body {
    font-family: "LXGW WenKai", var(--font-sans);
}
```

字体文件放 `static/fonts/`。

### 修改文章宽度

```css
:root {
    --main-width: 760px;   /* 默认 720px */
    --nav-width: 1024px;
}
```

---

## 六、注意事项

**① 改完 CSS 为什么线上没变化？**
Hugo 会给样式表加**内容指纹**（文件名里的长哈希）。内容一变，URL 就变，缓存自动失效。
如果没变化，检查 Git 是否推送成功、Actions 是否跑完。

**② 为什么 `static/` 里的文件要手动强刷？**
因为 `static/` 是**原样拷贝**，不经过资源管道，**没有指纹**。favicon 就属于这种，
所以浏览器缓存很顽固。

**③ 主题升级会不会冲掉定制？**
不会。你的东西都在项目根，主题是 `git submodule`，两者物理隔离。
升级命令：

```bash
git submodule update --remote --merge themes/PaperMod
git commit -am "chore: update theme"
```

**④ 怎么知道主题有哪些可配置项？**
直接看主题源码，这是最快的方式：

```bash
# 看所有配置项被读取的地方
grep -rn "site.Params" themes/PaperMod/layouts/ | head -40

# 看 CSS 变量表
cat themes/PaperMod/assets/css/core/theme-vars.css
```

---

## 七、本地调试流程

```bash
cd my-blog

# 启动预览（含草稿，实时热重载）
../.tools/hugo server --buildDrafts

# 打开 http://localhost:1313
# 改 CSS / 配置 / 模板 都会自动刷新

# 不用时 Ctrl+C 停止
```

> ⚠️ 启动预览服务前先确认端口没被占用。若 1313 被占，用 `--port 1314`。
