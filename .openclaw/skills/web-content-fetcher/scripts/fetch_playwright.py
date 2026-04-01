#!/usr/bin/env python3
"""
使用 Playwright 的网页正文提取脚本（支持 JS 渲染页面）
专门用于微信公众号等需要浏览器环境的页面

用法：
  python3 fetch_playwright.py <url> [max_chars]

示例：
  python3 fetch_playwright.py https://mp.weixin.qq.com/s/xxx 30000
"""

import sys
import re
import html2text
from scrapling.fetchers import DynamicFetcher


def fix_lazy_images(html_raw):
    """
    微信公众号等平台用 data-src 懒加载图片，src 为占位符。
    将 data-src 的值提升为 src，确保 html2text 能正确渲染图片。
    """
    html_raw = re.sub(
        r'<img([^>]*?)\sdata-src="([^"]+)"([^>]*?)>',
        lambda m: f'<img{m.group(1)} src="{m.group(2)}"{m.group(3)}>',
        html_raw
    )
    return html_raw


def scrapling_fetch(url, max_chars=30000):
    # 使用 DynamicFetcher（基于 playwright，支持 JS 渲染）
    fetcher = DynamicFetcher()
    page = fetcher.fetch(url, headless=True, browser='chromium')

    h = html2text.HTML2Text()
    h.ignore_links = False
    h.ignore_images = False
    h.body_width = 0  # 不自动换行

    # 微信公众号专用选择器
    if "mp.weixin.qq.com" in url:
        selectors = ["div#js_content", "div.rich_media_content"]
    else:
        selectors = [
            'article',
            'main',
            '.post-content',
            '.entry-content',
            '.article-body',
            '[class*="body"]',
            '[class*="content"]',
            '[class*="article"]',
        ]

    for selector in selectors:
        els = page.css(selector)
        if els:
            html_raw = fix_lazy_images(els[0].html_content)
            md = h.handle(html_raw)
            md = re.sub(r'\n{3,}', '\n\n', md).strip()
            if len(md) > 300:
                return md[:max_chars], selector

    # fallback：全页转 Markdown
    html_raw = fix_lazy_images(page.html_content)
    md = h.handle(html_raw)
    md = re.sub(r'\n{3,}', '\n\n', md).strip()
    return md[:max_chars], 'body(fallback)'


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("用法: python3 fetch_playwright.py <url> [max_chars]", file=sys.stderr)
        sys.exit(1)

    url = sys.argv[1]
    max_chars = int(sys.argv[2]) if len(sys.argv) > 2 else 30000

    text, selector = scrapling_fetch(url, max_chars)
    print(text)
