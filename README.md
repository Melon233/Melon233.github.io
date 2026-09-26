# 博客使用手册

站点源码在 `my-blog/`，技术栈：**Hugo (extended) + PaperMod 主题 + GitHub Actions 自动部署**。

Hugo 二进制在 `../.tools/hugo`（单文件，未装进系统）。

---

## 一、上线前的两处必改

打开 `hugo.yaml`，把所有 `YOUR_USERNAME` 换成你的 GitHub 用户名：

```yaml
baseURL: "https://你的用户名.github.io/"
```

以及 `params.socialIcons` 里的 GitHub 链接。

**`baseURL` 写错会导致全站 CSS 和图片 404**，这是新手第一大坑，务必先改。

---

## 二、部署到 GitHub Pages

### 1. 建仓库

在 GitHub 新建仓库，名字**必须是**：

```
你的用户名.github.io
```

例如用户名是 `karon`，仓库名就是 `karon.github.io`。只有这样才能得到 `https://karon.github.io` 这种干净地址。

建仓库时**不要**勾选 "Add a README"（避免和本地冲突）。

### 2. 关联远程并推送

```bash
cd my-blog
git remote add origin https://github.com/你的用户名/你的用户名.github.io.git
git branch -M main
git push -u origin main
```

### 3. 开启 Pages

仓库页面 → **Settings** → 左侧 **Pages** → 在 **Build and deployment** 下把 **Source** 改成 **GitHub Actions**。

> 注意：不要选 "Deploy from a branch"，否则我们写的 Actions 工作流不会生效。

### 4. 等待发布

推送后自动触发构建。到仓库的 **Actions** 标签页能看到进度：

- 绿色 ✅ = 成功，此时访问 `https://你的用户名.github.io`
- 红色 ❌ = 失败，点进去看是 `build` 还是 `deploy` 挂了

首次生效可能要等 1~3 分钟。

---

## 三、日常写作

### 新建文章

```bash
cd my-blog
../.tools/hugo new content posts/文章文件名.md
```

建议文件名用英文短横线，比如 `hugo-tips.md`，然后改 front matter：

```toml
---
title: "文章标题"
date: 2026-09-26
draft: false          # true 时不会发布
tags: ["标签1"]
categories: ["分类"]
summary: "列表页显示的摘要"
---
```

### 本地预览

```bash
cd my-blog
../.tools/hugo server --buildDrafts
```

打开 <http://localhost:1313>。改文件会实时刷新，`Ctrl+C` 停止。

### 从 Notion 导入文章

如果习惯在 Notion 里写作，可以用转换脚本发布。流程：

**1. 在 Notion 里导出**

页面右上角 `⋯` → **Export** → 格式选 **Markdown & CSV** → 导出得到 zip。

> ⚠️ 一定要选「Markdown & CSV」，不要选「Markdown」。前者是 zip 包，
> 图片会作为独立文件一起导出；后者会把内容塞进单个文件，图片仍是外链。

**2. 解压到 `_inbox/`**

```bash
cd my-blog
unzip ~/Downloads/导出文件.zip -d _inbox/
```

**3. 预览转换结果**

```bash
python3 tools/notion_import.py --dry-run
```

这一步**不写入文件、不下载图片**，只显示每篇会被转成什么样子。
建议先跑一次，确认标题、slug、摘要符合预期。

**4. 执行转换**

```bash
python3 tools/notion_import.py
```

脚本会自动处理：

| 问题 | 处理方式 |
|---|---|
| 外链图片会过期 | 下载到 `static/images/`，正文替换为 `/images/xxx.png` |
| 没有 front matter | 自动生成 title / date / slug / summary |
| H1 与 title 重复 | 提取 H1 作为标题，并从正文移除 |
| 文件名带 Notion ID | 去掉尾部十六进制 ID |
| 中文标题无英文 slug | 回退为 `日期-序号`，如 `2026-09-26-1` |

**5. 检查并发布**

```bash
../.tools/hugo server --buildDrafts   # 本地预览
git add . && git commit -m "post: 新增文章" && git push
```

**关于 slug（URL 地址）**

中文标题无法生成有意义的英文 slug，脚本会回退成 `2026-09-26-1` 这种形式。
如果想用可读的 URL，**在 Notion 页面里加一行 front matter 风格的内容**：

````markdown
slug: my-first-post

# 我的第一篇技术笔记

正文……
````

脚本会识别 `slug:` 行并使用它。（放在 Notion 页面的最开头，用代码块或纯文本都行。）

### 发布

```bash
git add .
git commit -m "post: 新增文章"
git push
```

推上去后 Actions 会自动构建部署，等一两分钟刷新线上页面即可。

---

## 四、目录说明

```text
my-blog/
├── content/
│   ├── posts/            # 文章都放这里
│   └── search.md         # 搜索页
├── layouts/              # 覆盖主题的模板（首页、详情页、页脚、头部）
├── assets/css/extended/  # 自定义样式（自动加载，不改主题源码）
├── tools/
│   └── notion_import.py  # Notion 导出转换脚本
├── _inbox/               # Notion 导入暂存区（内容不提交）
├── themes/PaperMod/      # 主题（git submodule）
├── static/               # 静态资源；图片放 static/images/
├── hugo.yaml             # 全局配置
└── .github/workflows/
    └── deploy.yml        # 自动部署脚本
```

---

## 五、常见问题

**Q：改了 `hugo.yaml` 但线上没变化？**
Hugo 服务器有缓存，本地重启用 `hugo server --disableFastRender`；线上确认 Actions 跑完了。

**Q：图片显示不出来？**
放 `static/images/foo.png`，文章里写 `![说明](/images/foo.png)`（注意开头是 `/`）。

**Q：主题更新怎么拉？**
```bash
git submodule update --remote --merge themes/PaperMod
git commit -am "chore: update theme"
```

**Q：Actions 报错找不到主题？**
`deploy.yml` 里必须有 `submodules: recursive`，已经配好了；若你手动克隆过仓库，要 `git submodule update --init --recursive`。

**Q：想用自定义域名？**
在 `static/` 下建一个内容为域名的 `CNAME` 文件，然后在域名商处配 CNAME 解析到 `你的用户名.github.io`，Pages 设置里填域名并开启 HTTPS。

**Q：仓库必须公开吗？**
免费账号用 Pages 必须公开仓库。所以**千万不要把密钥、私人笔记提交进去**，`draft: true` 也不等于删除。

---

## 六、本地环境备忘

这台机器没有 Homebrew、没有 node/npm、没有 go，但都**不需要**——Hugo 是单文件二进制，已放在 `../.tools/hugo`，直接调用即可。

若哪天想全局使用：

```bash
sudo cp ../.tools/hugo /usr/local/bin/hugo
```
