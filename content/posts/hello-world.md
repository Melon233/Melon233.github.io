---
title: "第一篇：博客搭好了"
date: 2025-09-26
draft: false
slug: "hello-world"
tags: ["随笔", "Hugo"]
categories: ["站点搭建"]
summary: "用 Hugo + PaperMod + GitHub Pages 搭起来的个人博客，记录一下思路。"
---

## 为什么选 Hugo

搭这个博客前对比过几个方案，最后选了 Hugo，主要三点：

1. **构建快**——几百篇文章也是毫秒级，改完立刻能看到效果。
2. **单文件二进制**——不需要装 Go、不需要 Ruby，一个可执行文件搞定。
3. **GitHub Pages 原生友好**——配好 Actions 后 `git push` 就自动发布。

## 目录结构速查

```text
my-blog/
├── content/
│   └── posts/          # 所有文章放这里，Markdown 格式
├── themes/PaperMod/    # 主题（以 submodule 形式引入）
├── hugo.yaml           # 全局配置
└── .github/workflows/  # 自动部署脚本
```

## 日常写作流程

新建一篇文章：

```bash
hugo new content posts/my-new-post.md
```

本地预览（带草稿、实时热重载）：

```bash
hugo server --buildDrafts
```

然后打开 <http://localhost:1313> 就能看到效果。写完推上去：

```bash
git add .
git commit -m "post: 新增文章"
git push
```

## 几个记住就少踩坑的点

- 文章头部的 `draft: true` 默认不会发布，本地预览要加 `--buildDrafts`。
- 图片放 `static/images/`，引用写 `/images/xxx.png`。
- 文件名建议用英文短横线，避免中文路径带来的编码问题。

> 接下来就把这里当成自己的笔记本，持续往里写。
