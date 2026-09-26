#!/usr/bin/env python3
"""
Notion 导出 → Hugo 文章转换器
============================================================

用途
----
把 Notion「导出 → Markdown & CSV」得到的内容，转换成本站可直接发布的
Hugo 文章，并解决 Notion 导出常见的几个坑：

  1. 外链图片会过期  → 下载到 static/images/，替换为本地路径
  2. 缺少 front matter → 自动生成 title / date / slug / tags / summary
  3. 标题重复出现     → 正文里与 title 相同的首个 H1 自动删除
  4. 文件名尾部乱码   → 去掉 Notion 追加的 32 位十六进制 ID
  5. 中文文件名       → 保留原文，但 URL 用你指定的英文 slug

用法
----
    # 1. 把 Notion 导出的 zip 解压到 _inbox/ 目录
    # 2. 预览将要做的改动（不写入任何文件）
    python3 tools/notion_import.py --dry-run

    # 3. 实际转换
    python3 tools/notion_import.py

    # 4. 本地预览确认，然后提交
    ../.tools/hugo server --buildDrafts

目录约定
--------
    _inbox/          放置 Notion 导出的原始 md 与图片（会被脚本读取）
    content/posts/   转换后的文章输出到这里
    static/images/   图片下载到这里

只依赖 Python 标准库，无需 pip 安装任何东西。
"""

import argparse
import hashlib
import os
import re
import shutil
import sys
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime

# ---------------------------------------------------------------- 路径

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INBOX = os.path.join(ROOT, "_inbox")
POSTS = os.path.join(ROOT, "content", "posts")
IMAGES = os.path.join(ROOT, "static", "images")

# Notion 导出文件名尾部的 ID，长度不固定（常见 8 / 12 / 32 位十六进制）。
# 统一用「空格 + 纯十六进制」判定，且要求长度 >= 8，避免误伤正常词尾。
NOTION_ID_RE = re.compile(r"\s+[0-9a-fA-F]{8,}$")
# 兼容无空格的连字符形式，如 "笔记-8f3a2b1c4d5e"
NOTION_DASH_ID_RE = re.compile(r"-[0-9a-fA-F]{8,}$")

# Markdown 图片语法：![alt](url)
MD_IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
# Notion 有时导出为 <img src="...">
HTML_IMAGE_RE = re.compile(r'<img[^>]+src="([^"]+)"[^>]*>')

USER_AGENT = "Mozilla/5.0 (compatible; notion-import/1.0)"

# 允许的图片扩展名
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".bmp", ".avif"}


# ---------------------------------------------------------------- 工具


def log(msg, level="info"):
    prefix = {"info": "  ", "ok": "✅ ", "warn": "⚠️  ", "err": "❌ ", "step": "\n▶ "}
    print(f"{prefix.get(level, '  ')}{msg}")


def strip_notion_id(name):
    """去掉 Notion 追加的文件 ID（8 / 12 / 32 位十六进制，带空格或连字符）。"""
    name = NOTION_ID_RE.sub("", name)
    # 仅当剩余部分还足够长时才去掉连字符形式的 ID，避免把 "abc-12345678" 清空
    candidate = NOTION_DASH_ID_RE.sub("", name)
    if candidate.strip():
        name = candidate
    return name.strip()


def slugify(text):
    """
    生成安全的 URL slug。中文会被剔除，因此对中文标题会得到空串，
    此时由调用方回退到日期序号方案。
    """
    # 归一化，去掉重音符号
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


def now_iso():
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S+08:00")


def guess_date_from_file(path):
    """从文件修改时间推断日期，作为未指定时的回退。"""
    ts = os.path.getmtime(path)
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%dT%H:%M:%S+08:00")


# ---------------------------------------------------------------- 图片


def download_image(url, dry_run=False):
    """
    下载图片到 static/images/，返回可用的站点路径 /images/xxx.ext。
    失败时返回 None，由调用方决定保留原链接还是告警。
    """
    try:
        parsed = urllib.parse.urlparse(url)
        ext = os.path.splitext(parsed.path)[1].lower()
        if ext not in IMAGE_EXTS:
            ext = ".png"

        # 用 URL 的哈希做文件名，避免重名冲突且便于去重
        digest = hashlib.sha1(url.encode("utf-8")).hexdigest()[:12]
        # 尽量保留原文件名，提升可读性
        base = os.path.basename(parsed.path)
        base = strip_notion_id(os.path.splitext(base)[0]) or "image"
        base = re.sub(r"[^A-Za-z0-9._-]+", "-", base).strip("-") or "image"
        filename = f"{base}-{digest}{ext}"
        dest = os.path.join(IMAGES, filename)

        if os.path.exists(dest):
            return f"/images/{filename}", True  # 已存在，跳过下载

        if dry_run:
            return f"/images/{filename}", False

        os.makedirs(IMAGES, exist_ok=True)
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read()
        with open(dest, "wb") as f:
            f.write(data)
        return f"/images/{filename}", False

    except (urllib.error.URLError, urllib.error.HTTPError, OSError, ValueError):
        return None, False


def localize_images(text, dry_run=False):
    """
    把正文里的外链图片换成本地路径。
    返回 (新正文, 下载数, 失败数)。
    """
    downloaded = 0
    failed = 0

    def repl(match):
        nonlocal downloaded, failed
        alt, url = match.group(1), match.group(2)

        # 已经是本地路径或 data URI，原样保留
        if url.startswith("/") or url.startswith("data:"):
            return match.group(0)

        # 本地相对路径（Notion 导出的图片文件夹），尝试直接复制
        if not url.startswith(("http://", "https://")):
            src = os.path.join(INBOX, urllib.parse.unquote(url))
            if os.path.exists(src):
                ext = os.path.splitext(src)[1].lower() or ".png"
                base = re.sub(r"[^A-Za-z0-9._-]+", "-",
                              os.path.splitext(os.path.basename(src))[0]) or "image"
                digest = hashlib.sha1(src.encode()).hexdigest()[:8]
                filename = f"{base}-{digest}{ext}"
                dest = os.path.join(IMAGES, filename)
                if not dry_run and not os.path.exists(dest):
                    os.makedirs(IMAGES, exist_ok=True)
                    shutil.copy2(src, dest)
                downloaded += 1
                return f"![{alt}](/images/{filename})"
            failed += 1
            return match.group(0)

        # 外链图片：下载到本地
        local_path, existed = download_image(url, dry_run=dry_run)
        if local_path:
            if not existed:
                downloaded += 1
            return f"![{alt}]({local_path})"
        failed += 1
        return match.group(0)

    new_text = MD_IMAGE_RE.sub(repl, text)

    # 处理 <img> 标签形式
    def repl_html(match):
        nonlocal downloaded, failed
        url = match.group(1)
        if url.startswith("/") or url.startswith("data:"):
            return match.group(0)
        local_path, existed = download_image(url, dry_run=dry_run)
        if local_path:
            if not existed:
                downloaded += 1
            return f"![]({local_path})"
        failed += 1
        return match.group(0)

    new_text = HTML_IMAGE_RE.sub(repl_html, new_text)
    return new_text, downloaded, failed


# ---------------------------------------------------------------- 解析


def split_front_matter(text):
    """若已存在 YAML front matter，拆出来，避免重复添加。"""
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            return parts[1].strip(), parts[2].lstrip("\n")
    return None, text


def read_meta(text):
    """从已有 front matter 里读取字段（简易解析，够用即可）。"""
    meta = {}
    for line in text.splitlines():
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(.*)$", line)
        if m:
            key, val = m.group(1), m.group(2).strip()
            meta[key] = val.strip("\"'")
    return meta


def extract_title(body, fallback):
    """
    取正文第一个 H1 作为标题，并从正文中移除它（避免与 front matter 重复）。
    """
    m = re.search(r"^#\s+(.+?)\s*$", body, re.MULTILINE)
    if m:
        title = m.group(1).strip()
        # 连同后面可能的一个空行一起去掉
        body = body[:m.start()] + body[m.end():]
        body = body.lstrip("\n")
        return title, body
    return fallback, body


def make_summary(body, limit=120):
    """从正文抽取一段纯文本作为摘要。"""
    text = body
    # 去掉图片、代码块、行内代码、链接语法
    text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    text = MD_IMAGE_RE.sub("", text)
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", text)
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"[*_>#\-]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "…"


def make_slug(title, path, explicit=None):
    """
    决定 slug。优先顺序：
      1. 调用方显式指定（Notion front matter 里的 slug，或 --slug 参数）
      2. 标题里能转写出 ASCII 的部分
      3. 中文标题兜底：用「日期-序号」，比哈希可读，且同一批次内稳定

    注意：中文标题无法生成有意义的英文 slug，因此推荐在 Notion 里
    用「标题」写中文、在 front matter 里补一行 slug: my-post-name。
    """
    if explicit:
        return explicit.strip()

    s = slugify(title)
    if s:
        return s

    # 兜底：日期 + 当天序号，避免哈希带来的不可读与不稳定
    date = datetime.fromtimestamp(os.path.getmtime(path)).strftime("%Y-%m-%d")
    seq = _next_sequence(date)
    return f"{date}-{seq}"


_SEQ_CACHE = {}


def _next_sequence(date_prefix):
    """为同一日期分配递增序号，并跳过内容目录里已存在的 slug。"""
    n = _SEQ_CACHE.get(date_prefix, 0) + 1
    while True:
        candidate = f"{date_prefix}-{n}"
        if not os.path.exists(os.path.join(POSTS, candidate + ".md")):
            _SEQ_CACHE[date_prefix] = n
            return n
        n += 1



# ---------------------------------------------------------------- 转换


def extract_inline_meta(body):
    """
    解析正文开头的 `key: value` 行，作为补充元数据。

    Notion 没有 front matter 概念，但可以直接在页面最上方写：

        slug: my-first-post
        tags: Hugo, 笔记

        # 标题
        正文……

    这些行会被识别并移除，不残留在正文里。
    支持的 key：slug / tags / summary / date / draft / categories / title
    """
    allowed = {"slug", "tags", "summary", "date", "draft", "categories", "title"}
    meta = {}
    lines = body.splitlines()
    consumed = 0

    for line in lines:
        stripped = line.strip()
        if not stripped:
            # 元数据块内部允许空行；一旦还没开始就遇到空行，说明没有元数据
            if consumed:
                consumed += 1
                continue
            break

        m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(.+)$", stripped)
        if m and m.group(1).lower() in allowed:
            meta[m.group(1).lower()] = m.group(2).strip().strip("\"'")
            consumed += 1
        else:
            break

    if meta:
        body = "\n".join(lines[consumed:]).lstrip("\n")
    return meta, body


def convert_file(src_path, dry_run=False, keep_source=False):
    """转换单个 .md 文件，返回输出路径或 None。"""
    with open(src_path, encoding="utf-8") as f:
        raw = f.read()

    existing_fm, body = split_front_matter(raw)
    meta = read_meta(existing_fm) if existing_fm else {}

    # 正文开头的 `key: value` 行也作为元数据（Notion 里没有 front matter）
    inline_meta, body = extract_inline_meta(body)
    for k, v in inline_meta.items():
        meta.setdefault(k, v)

    # 标题：优先用元数据，其次正文 H1，最后用文件名
    file_stem = strip_notion_id(os.path.splitext(os.path.basename(src_path))[0])
    title_from_body, body = extract_title(body, file_stem)
    title = meta.get("title") or title_from_body

    # 图片本地化
    body, dl, fail = localize_images(body, dry_run=dry_run)

    # 生成 front matter
    date = meta.get("date") or guess_date_from_file(src_path)
    slug = make_slug(title, src_path, meta.get("slug"))
    summary = meta.get("summary") or make_summary(body)
    tags = meta.get("tags") or "[]"

    # tags 统一成 YAML 列表形式
    if tags and not tags.startswith("["):
        tags = "[" + ", ".join(f'"{t.strip()}"' for t in tags.split(",") if t.strip()) + "]"

    front = (
        "---\n"
        f'title: "{title}"\n'
        f"date: {date}\n"
        "draft: false\n"
        f'slug: "{slug}"\n'
        f"tags: {tags}\n"
        f'summary: "{summary}"\n'
        "---\n\n"
    )

    out_name = f"{slug}.md"
    out_path = os.path.join(POSTS, out_name)
    content = front + body.strip() + "\n"

    if dry_run:
        log(f"{os.path.basename(src_path)}", "info")
        print(f"      → {out_name}")
        print(f"        标题: {title}")
        print(f"        日期: {date}")
        print(f"        标签: {tags}")
        print(f"        摘要: {summary[:60]}{'…' if len(summary) > 60 else ''}")
        print(f"        图片: 下载 {dl} 张" + (f"，失败 {fail} 张" if fail else ""))
        return None

    os.makedirs(POSTS, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(content)

    if not keep_source:
        os.remove(src_path)

    log(f"{os.path.basename(src_path)} → content/posts/{out_name}"
        + (f"  (图片 {dl} 张)" if dl else "")
        + (f"  ⚠️ {fail} 张图片下载失败，仍为外链" if fail else ""), "ok")
    return out_path


def main():
    ap = argparse.ArgumentParser(
        description="把 Notion 导出的 Markdown 转换成 Hugo 文章")
    ap.add_argument("--dry-run", action="store_true",
                    help="只预览结果，不写入任何文件、不下载图片")
    ap.add_argument("--keep-source", action="store_true",
                    help="转换后保留 _inbox/ 里的原始文件")
    ap.add_argument("--inbox", default=INBOX,
                    help=f"输入目录，默认 {INBOX}")
    args = ap.parse_args()

    inbox = args.inbox
    if not os.path.isdir(inbox):
        log(f"找不到输入目录：{inbox}", "err")
        log("请把 Notion 导出的 md 文件（及图片）放进该目录后重试。", "info")
        return 1

    # 跳过目录说明文件，避免把 _inbox/README.md 当成文章转换
    SKIP_NAMES = {"readme.md", "index.md", "license.md"}

    md_files = sorted(
        os.path.join(inbox, n) for n in os.listdir(inbox)
        if n.lower().endswith(".md")
        and not n.startswith(".")
        and n.lower() not in SKIP_NAMES
        and os.path.isfile(os.path.join(inbox, n))
    )

    if not md_files:
        log(f"{inbox} 里没有 .md 文件", "warn")
        return 1

    log(f"在 {os.path.relpath(inbox, ROOT)}/ 找到 {len(md_files)} 个 Markdown 文件", "step")
    if args.dry_run:
        log("预览模式：不会写入文件，也不会下载图片", "warn")

    converted = 0
    for path in md_files:
        try:
            if convert_file(path, dry_run=args.dry_run,
                            keep_source=args.keep_source):
                converted += 1
        except Exception as e:  # noqa: BLE001 - 单篇失败不应中断整批
            log(f"{os.path.basename(path)} 转换失败：{e}", "err")

    if args.dry_run:
        log(f"\n预览完成，共 {len(md_files)} 篇。确认无误后去掉 --dry-run 实际执行。", "step")
    else:
        log(f"\n完成，共转换 {converted} 篇。", "step")
        log("下一步：", "info")
        print("    ../.tools/hugo server --buildDrafts   # 本地预览")
        print("    git add . && git commit -m 'post: 新增文章' && git push")
    return 0


if __name__ == "__main__":
    sys.exit(main())
