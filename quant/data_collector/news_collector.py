"""
新闻数据采集模块
从多个免费来源采集黄金/财经相关新闻

数据源:
- 金十数据 (jin10) - 快讯 flash_newest.js
- 新浪财经 (sina) - 待实现 Step 2
- RSS 聚合 (Google News / Investing.com) - feedparser
- 东方财富 (eastmoney) - 待实现 Step 2
"""
import json
import logging
import re
import time
from datetime import datetime
from typing import Dict, List

import requests
from bs4 import BeautifulSoup

from quant.common.db_pool import get_db_connection

try:
    import feedparser

    HAS_FEEDPARSER = True
except ImportError:
    HAS_FEEDPARSER = False

logger = logging.getLogger(__name__)

# 黄金/财经相关关键词
KEYWORDS = [
    "黄金",
    "贵金属",
    "gold",
    "美联储",
    "Fed",
    "利率",
    "通胀",
    "CPI",
    "非农",
    "美元",
    "期货",
    "央行",
    "降息",
    "加息",
    "GDP",
    "PMI",
    "避险",
    "地缘",
]

# RSS 源列表 (按优先级)
RSS_FEEDS = [
    {
        "name": "Google News - Gold",
        "url": "https://news.google.com/rss/search?q=gold+price&hl=en",
        "category": "commodity",
    },
    {
        "name": "Google News - 黄金",
        "url": "https://news.google.com/rss/search?q=%E9%BB%84%E9%87%91&hl=zh-CN&gl=CN&ceid=CN:zh-Hans",
        "category": "commodity",
    },
    {
        "name": "Investing.com Commodities",
        "url": "https://www.investing.com/rss/news_14.rss",
        "category": "commodity",
    },
]


class NewsCollector:
    """新闻数据采集器

    从多个免费来源采集黄金 / 财经相关新闻，返回统一格式的字典列表。

    每条新闻格式::

        {
            "datetime": "2026-03-12 17:40:00",
            "source":   "jin10",
            "title":    "...",
            "content":  "...",
            "url":      "...",
            "category": "macro",
        }
    """

    def __init__(self, request_interval: float = 3.0):
        self.request_interval = request_interval
        self.session = requests.Session()
        self.session.proxies = dict(http=None, https=None)
        # 绕过系统代理，避免 ConnectionResetError
        self.session.proxies = {"http": None, "https": None}
        self.session.trust_env = False
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/125.0.0.0 Safari/537.36"
                ),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            }
        )
        logger.info("NewsCollector 初始化, 请求间隔: %.1fs", request_interval)

    # ------------------------------------------------------------------
    # 公共接口
    # ------------------------------------------------------------------

    def fetch_all(self) -> List[Dict]:
        """从所有来源采集最新新闻"""
        all_news: List[Dict] = []

        for source_name, fetch_func in [
            ("jin10", self.fetch_jin10),
            ("sina", self.fetch_sina_finance),
            ("rss", self.fetch_rss),
            ("eastmoney", self.fetch_eastmoney),
        ]:
            try:
                news = fetch_func()
                all_news.extend(news)
                logger.info("%s 采集到 %d 条新闻", source_name, len(news))
            except NotImplementedError:
                logger.debug("%s 尚未实现, 跳过", source_name)
            except Exception as e:
                logger.error("%s 采集失败: %s", source_name, e)
            time.sleep(self.request_interval)

        logger.info("总计采集 %d 条新闻", len(all_news))
        return all_news

    # ------------------------------------------------------------------
    # 金十数据
    # ------------------------------------------------------------------

    def fetch_jin10(self) -> List[Dict]:
        """采集金十数据快讯

        金十数据通过 ``flash_newest.js`` 暴露最新快讯，
        返回格式为 ``var newest = [<JSON array>]``。
        """
        url = "https://www.jin10.com/flash_newest.js"
        results: List[Dict] = []

        try:
            resp = self.session.get(url, timeout=10)
            resp.raise_for_status()
        except requests.RequestException as e:
            logger.warning("金十数据请求失败: %s", e)
            return results

        # 解析 JS 变量: var newest = [...];
        text = resp.text.strip()
        match = re.search(r"var\s+newest\s*=\s*(\[.*\])", text, re.DOTALL)
        if not match:
            logger.warning("金十数据响应格式异常, 无法解析 JSON")
            return results

        try:
            items = json.loads(match.group(1))
        except json.JSONDecodeError as e:
            logger.warning("金十数据 JSON 解析失败: %s", e)
            return results

        for item in items:
            try:
                data = item.get("data", {})
                content = data.get("content", "")
                title = data.get("title", "")
                source_link = data.get("source_link", "") or data.get("link", "")

                # 跳过无内容的条目
                if not content and not title:
                    continue

                news_item = {
                    "datetime": item.get("time", ""),
                    "source": "jin10",
                    "title": title,
                    "content": self._clean_html(content),
                    "url": source_link or "https://www.jin10.com/flash",
                    "category": self._classify_jin10(item),
                    "important": item.get("important", 0),
                }
                results.append(news_item)
            except Exception as e:
                logger.debug("金十数据条目解析失败: %s", e)
                continue

        logger.info("金十数据采集到 %d 条快讯", len(results))
        return results

    @staticmethod
    def _classify_jin10(item: Dict) -> str:
        """根据金十数据频道标签分类"""
        channels = item.get("channel", [])
        # channel 含义: 1=要闻, 2=全球, 3=中国, 4=央行, 5=数据
        if 4 in channels or 5 in channels:
            return "macro"
        if 3 in channels:
            return "china"
        if 2 in channels:
            return "global"
        return "general"

    # ------------------------------------------------------------------
    # RSS 聚合
    # ------------------------------------------------------------------

    def fetch_rss(self) -> List[Dict]:
        """从多个 RSS 源采集新闻

        使用 feedparser 库解析 RSS/Atom。若 feedparser 未安装则返回空列表。
        """
        if not HAS_FEEDPARSER:
            logger.warning("feedparser 未安装, 跳过 RSS 采集 (pip install feedparser)")
            return []

        results: List[Dict] = []

        for feed_info in RSS_FEEDS:
            feed_name = feed_info["name"]
            feed_url = feed_info["url"]
            category = feed_info.get("category", "general")

            try:
                # feedparser 可以直接 parse URL，但为了控制 timeout 用 session
                resp = self.session.get(feed_url, timeout=15)
                resp.raise_for_status()
                feed = feedparser.parse(resp.content)
            except requests.RequestException as e:
                logger.warning("RSS [%s] 请求失败: %s", feed_name, e)
                continue
            except Exception as e:
                logger.warning("RSS [%s] 解析异常: %s", feed_name, e)
                continue

            if feed.bozo and not feed.entries:
                logger.warning("RSS [%s] 解析失败 (bozo): %s", feed_name, feed.bozo_exception)
                continue

            count = 0
            for entry in feed.entries[:30]:  # 最多取 30 条
                try:
                    # 提取发布时间
                    pub_time = ""
                    if hasattr(entry, "published_parsed") and entry.published_parsed:
                        pub_time = time.strftime("%Y-%m-%d %H:%M:%S", entry.published_parsed)
                    elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
                        pub_time = time.strftime("%Y-%m-%d %H:%M:%S", entry.updated_parsed)

                    title = entry.get("title", "")
                    # 部分 RSS 的 summary/description 含 HTML
                    raw_summary = entry.get("summary", "") or entry.get("description", "")
                    content = self._clean_html(raw_summary)
                    link = entry.get("link", "")

                    if not title:
                        continue

                    news_item = {
                        "datetime": pub_time,
                        "source": "rss",
                        "title": title,
                        "content": content[:500],  # 截断过长内容
                        "url": link,
                        "category": category,
                        "feed_name": feed_name,
                    }
                    results.append(news_item)
                    count += 1
                except Exception as e:
                    logger.debug("RSS [%s] 条目解析失败: %s", feed_name, e)
                    continue

            logger.info("RSS [%s] 采集到 %d 条", feed_name, count)
            time.sleep(1)  # RSS 源之间间隔

        return results

    # ------------------------------------------------------------------
    # 待实现 (Step 2)
    # ------------------------------------------------------------------

    def fetch_sina_finance(self) -> List[Dict]:
        """采集新浪财经黄金/期货相关新闻

        使用新浪滚动新闻 API (feed.mix.sina.com.cn) 获取期货/贵金属频道的最新资讯，
        然后用关键词过滤出黄金相关内容。
        """
        results: List[Dict] = []

        # 新浪滚动新闻 API — pageid/lid 对应不同频道
        # pageid=155, lid=1686 → 期货频道; pageid=21, lid=1279 → 贵金属
        api_configs = [
            {
                "url": "https://feed.mix.sina.com.cn/api/roll/get",
                "params": {
                    "pageid": "155",
                    "lid": "1686",
                    "num": "30",
                    "versionNumber": "1.2.4",
                    "encode": "utf-8",
                },
                "category": "futures",
            },
            {
                "url": "https://feed.mix.sina.com.cn/api/roll/get",
                "params": {
                    "pageid": "21",
                    "lid": "1279",
                    "num": "30",
                    "versionNumber": "1.2.4",
                    "encode": "utf-8",
                },
                "category": "commodity",
            },
        ]

        for cfg in api_configs:
            try:
                resp = self.session.get(cfg["url"], params=cfg["params"], timeout=15)
                resp.raise_for_status()
                data = resp.json()
            except requests.RequestException as e:
                logger.warning("新浪财经 API 请求失败 (%s): %s", cfg["category"], e)
                continue
            except (json.JSONDecodeError, ValueError) as e:
                logger.warning("新浪财经 API 响应解析失败 (%s): %s", cfg["category"], e)
                continue

            result = data.get("result", {})
            items = result.get("data", [])
            if not isinstance(items, list):
                logger.warning("新浪财经 API 返回数据格式异常 (%s)", cfg["category"])
                continue

            for item in items:
                try:
                    title = item.get("title", "").strip()
                    if not title:
                        continue

                    # 摘要 / 正文
                    summary = item.get("summary", "") or item.get("intro", "") or ""
                    content = self._clean_html(summary)[:500]

                    # 发布时间 (Unix timestamp → 格式化)
                    ctime = item.get("ctime", "") or item.get("createtime", "")
                    pub_time = ""
                    if ctime:
                        try:
                            # ctime 可能是 "2026-03-12 17:00:00" 或 unix timestamp
                            if ctime.isdigit():
                                pub_time = datetime.fromtimestamp(int(ctime)).strftime(
                                    "%Y-%m-%d %H:%M:%S"
                                )
                            else:
                                pub_time = ctime
                        except (ValueError, OSError):
                            pub_time = ctime

                    link = item.get("url", "") or item.get("link", "")

                    news_item = {
                        "datetime": pub_time,
                        "source": "sina",
                        "title": title,
                        "content": content,
                        "url": link,
                        "category": cfg["category"],
                    }
                    results.append(news_item)
                except Exception as e:
                    logger.debug("新浪财经条目解析失败: %s", e)
                    continue

            logger.info("新浪财经 [%s] 采集到 %d 条", cfg["category"], len(items))
            time.sleep(self.request_interval)

        # 如果 API 失败，降级抓取网页
        if not results:
            results = self._fetch_sina_fallback()

        # 关键词过滤
        filtered = self._filter_by_keywords(results)
        logger.info("新浪财经共采集 %d 条, 过滤后 %d 条", len(results), len(filtered))
        return filtered

    def _fetch_sina_fallback(self) -> List[Dict]:
        """降级方案: 直接抓取新浪财经黄金频道 HTML"""
        results: List[Dict] = []
        urls = [
            ("https://finance.sina.com.cn/gold/", "commodity"),
            ("https://finance.sina.com.cn/futmarket/", "futures"),
        ]

        for page_url, category in urls:
            try:
                resp = self.session.get(page_url, timeout=15)
                resp.raise_for_status()
                resp.encoding = resp.apparent_encoding or "utf-8"
                soup = BeautifulSoup(resp.text, "html.parser")
            except requests.RequestException as e:
                logger.warning("新浪财经网页抓取失败 (%s): %s", page_url, e)
                continue

            # 查找新闻链接 — 典型结构: <a href="..." target="_blank">标题</a>
            links = soup.find_all("a", href=True)
            for a_tag in links:
                href = a_tag.get("href", "")
                title = a_tag.get_text(strip=True)

                # 过滤: 只要 doc.sina / finance.sina 的文章链接
                if not title or len(title) < 8:
                    continue
                if not re.search(r"(doc|finance)\.sina\.com\.cn", href):
                    continue
                # 排除导航链接
                if re.search(r"(javascript|#|void)", href, re.IGNORECASE):
                    continue

                news_item = {
                    "datetime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "source": "sina",
                    "title": title,
                    "content": "",
                    "url": href if href.startswith("http") else f"https:{href}",
                    "category": category,
                }
                results.append(news_item)

            time.sleep(self.request_interval)

        # 去重 (按 URL)
        seen_urls: set = set()
        unique: List[Dict] = []
        for item in results:
            if item["url"] not in seen_urls:
                seen_urls.add(item["url"])
                unique.append(item)

        return unique

    def fetch_eastmoney(self) -> List[Dict]:
        """采集东方财富期货/贵金属新闻

        优先使用东方财富公开的快讯 API，失败则降级抓取期货资讯网页。
        """
        results: List[Dict] = []

        # ---------- 方式 1: 东方财富快讯 API ----------
        # columns: 102=期货, 250=贵金属
        api_success = False
        for col_id, category in [("102", "futures"), ("250", "commodity")]:
            try:
                api_url = "https://np-listapi.eastmoney.com/comm/web/getNewsByColumns"
                params = {
                    "columns": col_id,
                    "pageSize": "30",
                    "pageIndex": "0",
                    "needContent": "1",
                    "fields": "title,content,showTime,url,mediaName",
                }
                resp = self.session.get(api_url, params=params, timeout=15)
                resp.raise_for_status()
                data = resp.json()
            except requests.RequestException as e:
                logger.warning("东方财富 API 请求失败 (col=%s): %s", col_id, e)
                continue
            except (json.JSONDecodeError, ValueError) as e:
                logger.warning("东方财富 API 响应解析失败 (col=%s): %s", col_id, e)
                continue

            items = data.get("data", {})
            if isinstance(items, dict):
                items = items.get("list", []) or items.get("items", [])
            if not isinstance(items, list):
                logger.warning("东方财富 API 数据格式异常 (col=%s)", col_id)
                continue

            api_success = True
            for item in items:
                try:
                    title = (item.get("title", "") or "").strip()
                    if not title:
                        continue

                    raw_content = item.get("content", "") or item.get("digest", "") or ""
                    content = self._clean_html(raw_content)[:500]

                    show_time = item.get("showTime", "") or item.get("date", "") or ""
                    link = item.get("url", "") or item.get("Art_Url", "")
                    if link and not link.startswith("http"):
                        link = f"https:{link}"

                    news_item = {
                        "datetime": show_time,
                        "source": "eastmoney",
                        "title": title,
                        "content": content,
                        "url": link,
                        "category": category,
                    }
                    results.append(news_item)
                except Exception as e:
                    logger.debug("东方财富 API 条目解析失败: %s", e)
                    continue

            logger.info("东方财富 API [col=%s] 采集到 %d 条", col_id, len(items))
            time.sleep(self.request_interval)

        # ---------- 方式 2: 降级抓取网页 ----------
        if not api_success:
            results = self._fetch_eastmoney_fallback()

        # 关键词过滤
        filtered = self._filter_by_keywords(results)
        logger.info("东方财富共采集 %d 条, 过滤后 %d 条", len(results), len(filtered))
        return filtered

    def _fetch_eastmoney_fallback(self) -> List[Dict]:
        """降级方案: 抓取东方财富期货资讯网页"""
        results: List[Dict] = []
        pages = [
            ("https://futures.eastmoney.com/a/cqhzx.html", "futures"),
            ("https://futures.eastmoney.com/a/cgzqh.html", "commodity"),
        ]

        for page_url, category in pages:
            try:
                resp = self.session.get(page_url, timeout=15)
                resp.raise_for_status()
                resp.encoding = resp.apparent_encoding or "utf-8"
                soup = BeautifulSoup(resp.text, "html.parser")
            except requests.RequestException as e:
                logger.warning("东方财富网页抓取失败 (%s): %s", page_url, e)
                continue

            # 东方财富列表页常见结构: <li> 包含 <a> 和 <span class="time">
            for li in soup.find_all("li"):
                a_tag = li.find("a", href=True)
                if not a_tag:
                    continue

                title = a_tag.get_text(strip=True)
                href = a_tag.get("href", "")
                if not title or len(title) < 6:
                    continue
                if not re.search(r"eastmoney\.com", href):
                    continue

                # 尝试提取时间
                time_span = li.find("span", class_=re.compile(r"time|date", re.I))
                pub_time = ""
                if time_span:
                    pub_time = time_span.get_text(strip=True)

                news_item = {
                    "datetime": pub_time or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "source": "eastmoney",
                    "title": title,
                    "content": "",
                    "url": href if href.startswith("http") else f"https:{href}",
                    "category": category,
                }
                results.append(news_item)

            time.sleep(self.request_interval)

        return results

    # ------------------------------------------------------------------
    # 待实现 (Step 3)
    # ------------------------------------------------------------------

    def save_to_db(self, news_list: List[Dict]) -> int:
        """将新闻列表存入 PostgreSQL（适配已有 news_raw 表结构）。

        已有表结构:
            id, time, source, title, content, url, author, content_hash, embedding_id, created_at

        Returns:
            实际插入的条数（已存在的会被跳过）。
        """
        if not news_list:
            return 0

        import hashlib

        insert_sql = """
        INSERT INTO news_raw (time, source, title, content, url, content_hash)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (content_hash) DO NOTHING;
        """

        # 确保 content_hash 有唯一约束
        ensure_index_sql = """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'news_raw_content_hash_key'
            ) THEN
                BEGIN
                    ALTER TABLE news_raw ADD CONSTRAINT news_raw_content_hash_key UNIQUE (content_hash);
                EXCEPTION WHEN duplicate_table THEN
                    NULL;
                END;
            END IF;
        END $$;
        """

        inserted = 0
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    # 确保唯一约束存在
                    cur.execute(ensure_index_sql)
                    conn.commit()

                    for item in news_list:
                        dt_str = item.get("datetime", "")
                        # 解析时间；解析失败则用当前时间
                        try:
                            dt_val = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S") if dt_str else datetime.now()
                        except (ValueError, TypeError):
                            dt_val = datetime.now()

                        # 用 source + title 生成 content_hash 去重
                        hash_input = f"{item.get('source', '')}-{item.get('title', '')}"
                        content_hash = hashlib.md5(hash_input.encode('utf-8')).hexdigest()

                        cur.execute(
                            insert_sql,
                            (
                                dt_val,
                                item.get("source", "unknown"),
                                item.get("title", ""),
                                item.get("content", ""),
                                item.get("url", ""),
                                content_hash,
                            ),
                        )
                        if cur.rowcount > 0:
                            inserted += 1

                    conn.commit()

            logger.info("新闻入库完成: 提交 %d 条, 实际插入 %d 条 (去重)", len(news_list), inserted)
        except Exception as e:
            logger.error("新闻入库失败: %s", e, exc_info=True)

        return inserted

    def run_loop(self, interval: int = 300):
        """持续采集循环，每隔 interval 秒执行一次 fetch_all → save_to_db。

        Args:
            interval: 采集间隔（秒），默认 300（5 分钟）。
        """
        logger.info("新闻采集循环启动, 间隔 %d 秒", interval)
        try:
            while True:
                try:
                    news = self.fetch_all()
                    saved = self.save_to_db(news)
                    logger.info(
                        "本轮采集完成: 采集 %d 条, 入库 %d 条",
                        len(news),
                        saved,
                    )
                except Exception as e:
                    logger.error("本轮采集异常: %s", e, exc_info=True)

                logger.info("等待 %d 秒后开始下一轮采集...", interval)
                time.sleep(interval)
        except KeyboardInterrupt:
            logger.info("收到中断信号, 新闻采集循环已停止")

    # ------------------------------------------------------------------
    # 工具方法
    # ------------------------------------------------------------------

    @staticmethod
    def _clean_html(html: str) -> str:
        """清洗 HTML 标签"""
        if not html:
            return ""
        soup = BeautifulSoup(html, "html.parser")
        return soup.get_text(strip=True)

    @staticmethod
    def _filter_by_keywords(news_list: List[Dict]) -> List[Dict]:
        """按关键词过滤相关新闻"""
        filtered = []
        for item in news_list:
            text = (item.get("title", "") + item.get("content", "")).lower()
            if any(kw.lower() in text for kw in KEYWORDS):
                filtered.append(item)
        return filtered


# ------------------------------------------------------------------
# 独立测试入口
# ------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    )

    collector = NewsCollector(request_interval=2.0)

    # 测试金十数据
    print("\n=== 金十数据快讯 ===")
    jin10_news = collector.fetch_jin10()
    for n in jin10_news[:5]:
        print(f"  [{n['datetime']}] {n['content'][:80]}")
    print(f"  共 {len(jin10_news)} 条")

    # 测试 RSS
    print("\n=== RSS 新闻 ===")
    rss_news = collector.fetch_rss()
    for n in rss_news[:5]:
        print(f"  [{n['datetime']}] {n['title'][:80]}")
    print(f"  共 {len(rss_news)} 条")

    # 测试关键词过滤
    all_news = jin10_news + rss_news
    filtered = NewsCollector._filter_by_keywords(all_news)
    print("\n=== 关键词过滤 ===")
    print(f"  总计 {len(all_news)} 条, 过滤后 {len(filtered)} 条")
    for n in filtered[:5]:
        print(f"  [{n['source']}] {n.get('title') or n.get('content', '')[:60]}")
