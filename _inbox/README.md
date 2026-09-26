# Notion 导入暂存目录

把 Notion「导出 → Markdown & CSV」解压后的 `.md` 文件和图片放进这里，
然后运行转换脚本。

## 使用步骤

```bash
cd my-blog

# 1. 解压 Notion 导出的 zip 到这里
unzip ~/Downloads/导出文件.zip -d _inbox/

# 2. 预览（不写入文件、不下载图片）
python3 tools/notion_import.py --dry-run

# 3. 实际转换
python3 tools/notion_import.py
```

转换完成后：

- `.md` 源文件会被自动删除
- 结果输出到 `content/posts/`
- 图片下载到 `static/images/`

## 指定英文 URL

中文标题无法生成有意义的英文 slug，脚本会回退成 `2026-09-26-1` 这种形式。
想用可读的 URL，在 Notion 页面**最开头**加一行：

```text
slug: my-first-post
tags: Hugo, 笔记

# 我的第一篇技术笔记

正文……
```

脚本会识别 `slug:` 等元数据行，并在生成的 front matter 中使用它们，
这些行不会残留在正文里。

支持的 key：`slug` `tags` `summary` `date` `draft` `categories` `title`

## 注意

本目录的内容不会提交到 Git（见 `.gitignore`），只有这个说明文件例外。
