"""
新闻数据采集模块测试用例
基于 PRD.md 需求编写
"""
import pytest
import sys
import os
import re
import requests
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from quant.data_collector.news_collector import NewsCollector, KEYWORDS


@pytest.fixture
def collector():
    """创建 NewsCollector 实例"""
    return NewsCollector(request_interval=1.0)


@pytest.fixture
def sample_news_list():
    """样本新闻数据"""
    return [
        {
            "datetime": "2026-03-12 10:00:00",
            "source": "jin10",
            "title": "美联储宣布加息25个基点",
            "content": "美联储今日宣布加息25个基点，符合市场预期",
            "url": "https://www.jin10.com/flash/123",
            "category": "macro",
        },
        {
            "datetime": "2026-03-12 11:30:00",
            "source": "sina",
            "title": "黄金价格突破2000美元",
            "content": "国际黄金价格今日突破2000美元关口",
            "url": "https://finance.sina.com.cn/gold/456",
            "category": "commodity",
        },
    ]


# ==============================================================================
# 1. 数据格式验证
# ==============================================================================


class TestDataFormat:
    """数据格式验证"""

    @pytest.mark.network
    def test_fetch_jin10_returns_list(self, collector):
        """测试 fetch_jin10 返回 List[Dict]"""
        result = collector.fetch_jin10()
        assert isinstance(result, list)
        for item in result:
            assert isinstance(item, dict)

    @pytest.mark.network
    def test_fetch_sina_returns_list(self, collector):
        """测试 fetch_sina_finance 返回 List[Dict]"""
        result = collector.fetch_sina_finance()
        assert isinstance(result, list)
        for item in result:
            assert isinstance(item, dict)

    @pytest.mark.network
    def test_fetch_rss_returns_list(self, collector):
        """测试 fetch_rss 返回 List[Dict]"""
        result = collector.fetch_rss()
        assert isinstance(result, list)
        for item in result:
            assert isinstance(item, dict)

    @pytest.mark.network
    def test_fetch_eastmoney_returns_list(self, collector):
        """测试 fetch_eastmoney 返回 List[Dict]"""
        result = collector.fetch_eastmoney()
        assert isinstance(result, list)
        for item in result:
            assert isinstance(item, dict)

    @pytest.mark.network
    def test_news_has_required_fields(self, collector):
        """测试新闻包含必要字段"""
        news = collector.fetch_jin10()
        if news:
            item = news[0]
            assert "datetime" in item
            assert "source" in item
            assert "title" in item
            assert "content" in item
            assert "url" in item
            assert "category" in item

    @pytest.mark.network
    def test_datetime_field_format(self, collector):
        """测试 datetime 字段格式是否合法"""
        news = collector.fetch_jin10()
        for item in news:
            dt_str = item.get("datetime", "")
            if dt_str:
                # 尝试解析时间格式
                try:
                    datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    pytest.fail(f"datetime 格式不合法: {dt_str}")

    @pytest.mark.network
    def test_source_field_values(self, collector):
        """测试 source 字段值是否在预期范围内"""
        valid_sources = {"jin10", "sina", "rss", "eastmoney"}
        all_news = collector.fetch_all()
        for item in all_news:
            assert item.get("source") in valid_sources, f"未知的 source: {item.get('source')}"

    @pytest.mark.network
    def test_title_not_empty(self, collector):
        """测试 title 不为空"""
        news = collector.fetch_jin10()
        for item in news:
            title = item.get("title", "")
            # 金十数据可能只有 content 没有 title
            if item.get("source") != "jin10":
                assert title, "title 不应为空"

    @pytest.mark.network
    def test_content_no_html_tags(self, collector):
        """测试 content 不包含 HTML 标签"""
        news = collector.fetch_all()
        html_pattern = re.compile(r"<[^>]+>")
        for item in news:
            content = item.get("content", "")
            if content:
                assert not html_pattern.search(content), f"content 包含 HTML 标签: {content[:100]}"


# ==============================================================================
# 2. 数据源可用性
# ==============================================================================


class TestDataSource:
    """数据源可用性"""

    @pytest.mark.network
    def test_fetch_jin10_available(self, collector):
        """测试金十数据能否获取数据"""
        news = collector.fetch_jin10()
        assert isinstance(news, list)
        # 金十数据通常有实时快讯
        assert len(news) > 0, "金十数据未返回任何新闻"

    @pytest.mark.network
    def test_fetch_sina_available(self, collector):
        """测试新浪财经能否获取数据"""
        news = collector.fetch_sina_finance()
        assert isinstance(news, list)
        # 新浪财经应该有新闻
        assert len(news) > 0, "新浪财经未返回任何新闻"

    @pytest.mark.network
    def test_fetch_rss_available(self, collector):
        """测试 RSS 能否获取数据"""
        news = collector.fetch_rss()
        assert isinstance(news, list)
        # RSS 可能因为网络问题返回空列表，但不应该报错

    @pytest.mark.network
    def test_fetch_eastmoney_available(self, collector):
        """测试东方财富能否获取数据"""
        news = collector.fetch_eastmoney()
        assert isinstance(news, list)
        # 东方财富应该有新闻
        assert len(news) > 0, "东方财富未返回任何新闻"

    @pytest.mark.network
    def test_fetch_all_integration(self, collector):
        """测试 fetch_all 综合采集"""
        news = collector.fetch_all()
        assert isinstance(news, list)
        # 至少应该有一个数据源返回数据
        assert len(news) > 0, "fetch_all 未返回任何新闻"


# ==============================================================================
# 3. 数据质量测试
# ==============================================================================


class TestDataQuality:
    """数据质量"""

    @pytest.mark.network
    def test_title_length_reasonable(self, collector):
        """测试新闻标题长度是否合理（> 2 字符）"""
        news = collector.fetch_all()
        for item in news:
            title = item.get("title", "")
            if title:  # 金十数据可能没有 title
                assert len(title) > 2, f"标题过短: {title}"

    @pytest.mark.network
    def test_content_no_html_residue(self, collector):
        """测试新闻内容是否不含残留 HTML"""
        news = collector.fetch_all()
        html_tags = re.compile(r"<(p|div|span|a|br|img|script|style)[^>]*>", re.IGNORECASE)
        for item in news:
            content = item.get("content", "")
            if content:
                assert not html_tags.search(content), f"content 包含残留 HTML: {content[:100]}"

    @pytest.mark.network
    def test_url_format_valid(self, collector):
        """测试 URL 格式是否合法（以 http 开头）"""
        news = collector.fetch_all()
        for item in news:
            url = item.get("url", "")
            if url:
                assert url.startswith("http"), f"URL 格式不合法: {url}"

    @pytest.mark.network
    def test_datetime_not_future(self, collector):
        """测试 datetime 是否为合理的时间（不是未来时间）"""
        news = collector.fetch_all()
        now = datetime.now()
        for item in news:
            dt_str = item.get("datetime", "")
            if dt_str:
                try:
                    dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
                    # 允许 5 分钟的时间误差（考虑服务器时间差异）
                    assert dt <= now + timedelta(minutes=5), f"datetime 是未来时间: {dt_str}"
                except ValueError:
                    pass  # 格式不合法的在其他测试中检查

    @pytest.mark.network
    def test_datetime_not_too_old(self, collector):
        """测试 datetime 是否不是太久以前（不超过 30 天）"""
        news = collector.fetch_all()
        now = datetime.now()
        thirty_days_ago = now - timedelta(days=30)
        for item in news:
            dt_str = item.get("datetime", "")
            if dt_str:
                try:
                    dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
                    # RSS 可能有较旧的新闻，这里只是警告
                    if dt < thirty_days_ago:
                        print(f"警告: datetime 超过 30 天: {dt_str} ({item.get('source')})")
                except ValueError:
                    pass

    @pytest.mark.network
    def test_category_values_valid(self, collector):
        """测试 category 值是否在预期范围内"""
        valid_categories = {
            "macro",
            "commodity",
            "futures",
            "china",
            "global",
            "general",
        }
        news = collector.fetch_all()
        for item in news:
            category = item.get("category", "")
            if category:
                assert category in valid_categories, f"未知的 category: {category}"


# ==============================================================================
# 4. 关键词过滤测试
# ==============================================================================


class TestKeywordFilter:
    """关键词过滤"""

    def test_filter_by_keywords_keeps_relevant(self):
        """测试包含关键词的新闻是否被保留"""
        news_list = [
            {"title": "黄金价格上涨", "content": "今日黄金价格上涨"},
            {"title": "美联储加息", "content": "美联储宣布加息"},
            {"title": "股市行情", "content": "今日股市行情"},
        ]
        filtered = NewsCollector._filter_by_keywords(news_list)
        assert len(filtered) == 2
        assert any("黄金" in item["title"] for item in filtered)
        assert any("美联储" in item["title"] for item in filtered)

    def test_filter_by_keywords_removes_irrelevant(self):
        """测试不包含关键词的新闻是否被过滤"""
        news_list = [
            {"title": "今日天气预报", "content": "明天晴天"},
            {"title": "娱乐新闻", "content": "某明星结婚"},
        ]
        filtered = NewsCollector._filter_by_keywords(news_list)
        assert len(filtered) == 0

    def test_filter_by_keywords_case_insensitive(self):
        """测试关键词过滤是否不区分大小写"""
        news_list = [
            {"title": "GOLD price rises", "content": "Gold market update"},
            {"title": "Fed announces rate hike", "content": "Federal Reserve news"},
        ]
        filtered = NewsCollector._filter_by_keywords(news_list)
        assert len(filtered) == 2

    def test_filter_by_keywords_empty_input(self):
        """测试空输入"""
        filtered = NewsCollector._filter_by_keywords([])
        assert filtered == []

    def test_filter_by_keywords_partial_match(self):
        """测试关键词部分匹配"""
        news_list = [
            {"title": "黄金期货交易", "content": "期货市场分析"},
            {"title": "贵金属投资", "content": "投资建议"},
        ]
        filtered = NewsCollector._filter_by_keywords(news_list)
        assert len(filtered) == 2


# ==============================================================================
# 5. HTML 清洗测试
# ==============================================================================


class TestHtmlClean:
    """HTML 清洗"""

    def test_clean_html_removes_tags(self):
        """测试 _clean_html 是否正确去除 HTML 标签"""
        html = "<p>这是一段<strong>测试</strong>文本</p>"
        cleaned = NewsCollector._clean_html(html)
        assert cleaned == "这是一段测试文本"
        assert "<p>" not in cleaned
        assert "<strong>" not in cleaned

    def test_clean_html_handles_complex_html(self):
        """测试复杂 HTML 的清洗"""
        html = """
        <div class="content">
            <h1>标题</h1>
            <p>段落1</p>
            <p>段落2</p>
            <a href="http://example.com">链接</a>
        </div>
        """
        cleaned = NewsCollector._clean_html(html)
        assert "<div>" not in cleaned
        assert "<h1>" not in cleaned
        assert "<a>" not in cleaned
        assert "标题" in cleaned
        assert "段落1" in cleaned

    def test_clean_html_handles_special_chars(self):
        """测试特殊字符是否处理得当"""
        html = "<p>价格&nbsp;上涨&lt;10%&gt;</p>"
        cleaned = NewsCollector._clean_html(html)
        # BeautifulSoup 会自动处理 HTML 实体
        assert "<p>" not in cleaned
        assert "价格" in cleaned

    def test_clean_html_empty_input(self):
        """测试空输入是否返回空字符串"""
        assert NewsCollector._clean_html("") == ""
        assert NewsCollector._clean_html(None) == ""

    def test_clean_html_plain_text(self):
        """测试纯文本输入"""
        text = "这是纯文本，没有 HTML 标签"
        cleaned = NewsCollector._clean_html(text)
        assert cleaned == text

    def test_clean_html_nested_tags(self):
        """测试嵌套标签"""
        html = "<div><p><span>嵌套<strong>标签</strong>测试</span></p></div>"
        cleaned = NewsCollector._clean_html(html)
        assert cleaned == "嵌套标签测试"
        assert "<" not in cleaned


# ==============================================================================
# 6. 数据库测试
# ==============================================================================


class TestDatabase:
    """数据库操作"""

    @pytest.mark.db
    def test_save_to_db_creates_table(self, collector, sample_news_list):
        """测试 save_to_db 能否创建表"""
        with patch("quant.data_collector.news_collector.get_db_connection") as mock_conn:
            mock_cursor = MagicMock()
            mock_cursor.rowcount = 1
            mock_conn.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value = mock_cursor

            result = collector.save_to_db(sample_news_list)

            # 验证 CREATE TABLE 被调用
            calls = mock_cursor.execute.call_args_list
            create_table_called = any("CREATE TABLE" in str(call) for call in calls)
            assert create_table_called, "CREATE TABLE 未被调用"

    @pytest.mark.db
    def test_save_to_db_inserts_data(self, collector, sample_news_list):
        """测试 save_to_db 能否正常写入"""
        with patch("quant.data_collector.news_collector.get_db_connection") as mock_conn:
            mock_cursor = MagicMock()
            mock_cursor.rowcount = 1
            mock_conn.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value = mock_cursor

            result = collector.save_to_db(sample_news_list)

            # 验证 INSERT 被调用
            calls = mock_cursor.execute.call_args_list
            insert_called = any("INSERT INTO" in str(call) for call in calls)
            assert insert_called, "INSERT 未被调用"
            assert result == len(sample_news_list)

    @pytest.mark.db
    def test_save_to_db_deduplication(self, collector, sample_news_list):
        """测试去重逻辑是否生效（相同 source+title+datetime 不重复插入）"""
        with patch("quant.data_collector.news_collector.get_db_connection") as mock_conn:
            mock_cursor = MagicMock()
            # 第一次插入成功，第二次因为 ON CONFLICT 返回 0
            mock_cursor.rowcount = 0
            mock_conn.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value = mock_cursor

            # 插入重复数据
            result = collector.save_to_db(sample_news_list)

            # 验证 ON CONFLICT 子句存在
            calls = mock_cursor.execute.call_args_list
            conflict_handled = any("ON CONFLICT" in str(call) for call in calls)
            assert conflict_handled, "ON CONFLICT 未被使用"

    @pytest.mark.db
    def test_save_to_db_returns_inserted_count(self, collector, sample_news_list):
        """测试返回值是否为实际插入条数"""
        with patch("quant.data_collector.news_collector.get_db_connection") as mock_conn:
            mock_cursor = MagicMock()
            # 模拟只插入了 1 条（另一条重复）
            mock_cursor.rowcount = 1
            mock_conn.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value = mock_cursor

            result = collector.save_to_db(sample_news_list)

            assert isinstance(result, int)
            assert result >= 0

    @pytest.mark.db
    def test_save_to_db_empty_list(self, collector):
        """测试空列表输入"""
        result = collector.save_to_db([])
        assert result == 0

    @pytest.mark.db
    def test_save_to_db_handles_invalid_datetime(self, collector):
        """测试处理无效的 datetime"""
        invalid_news = [
            {
                "datetime": "invalid-date",
                "source": "test",
                "title": "测试",
                "content": "内容",
                "url": "http://test.com",
                "category": "general",
            }
        ]
        with patch("quant.data_collector.news_collector.get_db_connection") as mock_conn:
            mock_cursor = MagicMock()
            mock_cursor.rowcount = 1
            mock_conn.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value = mock_cursor

            # 应该不抛出异常，使用当前时间
            result = collector.save_to_db(invalid_news)
            assert result >= 0


# ==============================================================================
# 7. 异常处理测试
# ==============================================================================


class TestErrorHandling:
    """异常处理"""

    @pytest.mark.network
    def test_fetch_all_continues_on_single_source_failure(self, collector):
        """测试单个数据源失败时 fetch_all 是否继续运行其他源"""
        with patch.object(collector, "fetch_jin10", side_effect=Exception("金十数据失败")):
            # 即使金十数据失败，其他源应该继续
            news = collector.fetch_all()
            assert isinstance(news, list)
            # 至少应该有其他源的数据（如果网络正常）

    def test_fetch_jin10_handles_network_timeout(self, collector):
        """测试网络超时是否优雅降级"""
        with patch.object(collector.session, "get", side_effect=requests.exceptions.Timeout("Network timeout")):
            news = collector.fetch_jin10()
            assert news == []  # 应该返回空列表而不是抛出异常

    def test_fetch_sina_handles_invalid_json(self, collector):
        """测试处理无效 JSON 响应"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "Invalid JSON"  # 必须是字符串，不是 Mock 对象
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_response.raise_for_status.return_value = None

        with patch.object(collector.session, "get", return_value=mock_response):
            news = collector.fetch_sina_finance()
            assert isinstance(news, list)

    def test_fetch_rss_handles_missing_feedparser(self, collector):
        """测试 feedparser 未安装时的处理"""
        with patch("quant.data_collector.news_collector.HAS_FEEDPARSER", False):
            news = collector.fetch_rss()
            assert news == []

    def test_fetch_eastmoney_handles_api_failure(self, collector):
        """测试东方财富 API 失败时的降级处理"""
        with patch.object(collector.session, "get", side_effect=requests.exceptions.RequestException("API Error")):
            news = collector.fetch_eastmoney()
            assert isinstance(news, list)

    @pytest.mark.db
    def test_save_to_db_handles_db_error(self, collector, sample_news_list):
        """测试数据库错误处理"""
        with patch("quant.data_collector.news_collector.get_db_connection") as mock_conn:
            mock_conn.return_value.__enter__.side_effect = Exception("DB Connection Error")

            # 应该不抛出异常
            result = collector.save_to_db(sample_news_list)
            assert result == 0

    def test_clean_html_handles_malformed_html(self):
        """测试处理格式错误的 HTML"""
        malformed = "<p>未闭合标签<div>嵌套错误</p>"
        cleaned = NewsCollector._clean_html(malformed)
        # BeautifulSoup 会尽力解析
        assert isinstance(cleaned, str)
        assert "<" not in cleaned or ">" not in cleaned


# ==============================================================================
# 运行测试
# ==============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
