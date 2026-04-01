"""
LLM 新闻分析底层模块。
使用 Claude Opus 4 分析新闻对黄金期货的影响。

当前定位：
- 提供单条/批量分析能力与历史实现兼容方法
- 不再作为 baseline 主链路入口
- baseline 唯一主入口已统一为 `scripts/batch_llm_analysis.py`

注意：
- 本模块仍保留旧的 fetch/save/verify 组合能力，主要用于历史兼容与后续拆分参考
- `news_analysis.time` 在本模块内也视为 legacy ambiguous field，不得作为新的正式时间语义依赖
- P0 本轮不继续扩展 verification / RAG / 全链路重构
"""

import json
import logging
import os
import re
import time
from typing import Dict, List, Optional

import requests

from quant.common.config import config
from quant.common.db_pool import get_db_connection
from quant.signal_generator import news_vector_store

logger = logging.getLogger(__name__)

LEGACY_FETCH_AND_ANALYZE_LATEST_ENV = "LLM_NEWS_ANALYZER_ENABLE_LEGACY_FETCH_AND_ANALYZE"


class LLMNewsAnalyzer:
    """LLM 新闻分析器。"""

    ANTHROPIC_VERSION = "2023-06-01"

    ANALYSIS_PROMPT = """你是一个专业的金融分析师，专注于黄金期货市场。
请分析以下新闻对黄金期货价格的影响：

标题: {title}
内容: {content}
来源: {source}
时间: {datetime}

请返回 JSON 格式的分析结果：
{{
  "importance": "high|medium|low|irrelevant",
  "direction": "bullish|bearish|neutral",
  "timeframe": "immediate|short-term|long-term",
  "confidence": 0.0-1.0,
  "reasoning": "简短解释（50字以内）"
}}

判断标准：
- importance: high=重大事件(美联储决议/非农/战争), medium=一般财经新闻, low=相关性弱, irrelevant=无关
- direction: bullish=利好黄金, bearish=利空黄金, neutral=中性
- timeframe: immediate=立即影响, short-term=1-7天, long-term=1个月以上
- confidence: 你对判断的确信程度

只返回 JSON，不要其他文字。"""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or config.claude.api_key.get_secret_value()
        self.model = model or config.claude.model
        self.base_url = config.claude.base_url.rstrip("/")
        self.timeout = config.claude.timeout
        self.max_retries = config.claude.max_retries

        self.session = requests.Session()
        self.session.headers.update(
            {
                "x-api-key": self.api_key,
                "anthropic-version": self.ANTHROPIC_VERSION,
                "content-type": "application/json",
            }
        )

    def analyze_news(self, news: Dict) -> Dict:
        historical_context = self._retrieve_historical_cases(news)
        prompt = self.ANALYSIS_PROMPT.format(
            title=news.get("title", ""),
            content=news.get("content", ""),
            source=news.get("source", ""),
            datetime=news.get("datetime", ""),
        )

        if historical_context:
            prompt = self._inject_historical_context(prompt, historical_context)

        try:
            result = self._call_claude_api(prompt)
            logger.info(
                "新闻分析完成: [%s] %s -> %s/%s (confidence=%.2f)",
                news.get("source", "unknown"),
                news.get("title", "")[:50],
                result.get("importance", "unknown"),
                result.get("direction", "unknown"),
                result.get("confidence", 0.0),
            )
            return result
        except Exception as e:
            logger.error(
                "新闻分析失败: [%s] %s, 错误: %s",
                news.get("source", "unknown"),
                news.get("title", "")[:50],
                e,
                exc_info=True,
            )
            return {
                "importance": "irrelevant",
                "direction": "neutral",
                "timeframe": "immediate",
                "confidence": 0.0,
                "reasoning": f"分析失败: {str(e)[:50]}",
            }

    def _retrieve_historical_cases(self, news: Dict) -> str:
        try:
            query_text = news.get("title", "")
            content = news.get("content", "")
            if content:
                query_text += " " + content[:300]

            if not query_text.strip():
                logger.debug("新闻标题和内容为空，跳过历史检索")
                return ""

            similar_news = news_vector_store.search_similar_news(query_text=query_text, n_results=3)
            if not similar_news:
                logger.info("向量库中未找到相似历史新闻")
                return ""

            lines = ["", "## 历史参考案例", "以下是历史上与当前新闻相似的事件及其实际市场影响：", ""]
            for idx, item in enumerate(similar_news, 1):
                meta = item.get("metadata", {})
                doc = item.get("document", "")
                title = ""
                for line in doc.split("\n"):
                    if line.startswith("Title: "):
                        title = line[len("Title: "):]
                        break
                if not title:
                    title = doc[:80]

                time_str = meta.get("time", "未知时间")
                direction = meta.get("direction", "unknown")
                confidence = meta.get("confidence", 0.0)
                price_change_1d = meta.get("price_change_1d")
                correct_1d = meta.get("correct_1d")

                lines.append(f"案例{idx}: {title} ({time_str})")
                lines.append(f"- LLM当时判断: {direction}, confidence={confidence}")
                if price_change_1d is not None:
                    change_str = f"{price_change_1d:+.4f}%"
                    correct_str = "判断正确" if correct_1d == 1 else ("判断错误" if correct_1d == 0 else "未验证")
                    lines.append(f"- 实际价格变化: {change_str} (1日), {correct_str}")
                else:
                    lines.append("- 实际价格变化: 暂无数据")
                lines.append("")

            return "\n".join(lines)
        except Exception as e:
            logger.warning("检索历史相似新闻失败（优雅降级）: %s", e)
            return ""

    @staticmethod
    def _inject_historical_context(prompt: str, historical_context: str) -> str:
        marker = "只返回 JSON，不要其他文字。"
        if marker in prompt:
            return prompt.replace(
                marker,
                historical_context + "\n请参考以上历史案例辅助判断，但以当前新闻的实际内容为主。\n\n" + marker,
            )
        return prompt + "\n" + historical_context + "\n请参考以上历史案例辅助判断，但以当前新闻的实际内容为主。"

    def analyze_batch(self, news_list: List[Dict]) -> List[Dict]:
        if not news_list:
            logger.warning("analyze_batch: 输入为空列表")
            return []

        results = []
        for i, news in enumerate(news_list, 1):
            try:
                results.append(self.analyze_news(news))
                if i < len(news_list):
                    time.sleep(1.0)
            except Exception as e:
                logger.error("批量分析第 %d 条新闻失败: %s", i, e)
                results.append(
                    {
                        "importance": "irrelevant",
                        "direction": "neutral",
                        "timeframe": "immediate",
                        "confidence": 0.0,
                        "reasoning": f"批量分析失败: {str(e)[:50]}",
                    }
                )
        return results

    def fetch_and_analyze_latest(self, limit: int = 10) -> List[Dict]:
        """受保护旧接口：默认禁止执行，避免继续被当成 baseline 主链路。"""
        if os.getenv(LEGACY_FETCH_AND_ANALYZE_LATEST_ENV) != "1":
            raise RuntimeError(
                "LLMNewsAnalyzer.fetch_and_analyze_latest() 已降级为受保护旧接口，默认禁止执行；"
                "baseline 唯一主入口为 scripts/batch_llm_analysis.py。"
                f"如需临时兼容调用，请显式设置环境变量 {LEGACY_FETCH_AND_ANALYZE_LATEST_ENV}=1。"
            )

        logger.warning(
            "正在执行受保护旧接口 fetch_and_analyze_latest()；该路径仅供临时兼容，不得作为 baseline 主链路。env=%s",
            LEGACY_FETCH_AND_ANALYZE_LATEST_ENV,
        )

        query_sql = """
        SELECT id, time, source, title, content, url
        FROM news_raw
        WHERE id NOT IN (SELECT news_id FROM news_analysis WHERE news_id IS NOT NULL)
        ORDER BY time DESC
        LIMIT %s;
        """

        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query_sql, (limit,))
                    rows = cursor.fetchall()
                    if not rows:
                        logger.info("没有未分析的新闻")
                        return []
                    news_list = [
                        {
                            "id": row[0],
                            "time_raw": row[1],
                            "datetime": row[1].strftime("%Y-%m-%d %H:%M:%S") if row[1] else "",
                            "source": row[2] or "",
                            "title": row[3] or "",
                            "content": row[4] or "",
                            "url": row[5] or "",
                        }
                        for row in rows
                    ]
        except Exception as e:
            logger.error("读取未分析新闻失败: %s", e, exc_info=True)
            return []

        results = []
        for news in news_list:
            analysis = self.analyze_news(news)
            results.append({"news_id": news["id"], "datetime": news["datetime"], "analysis": analysis})
            try:
                self.save_to_db(news["id"], analysis)
            except Exception as e:
                logger.error("保存分析结果失败 (news_id=%d): %s", news["id"], e)
            if news.get("time_raw"):
                self.verify_price_impact(news["id"], news["time_raw"])
            time.sleep(1.0)

        logger.info("fetch_and_analyze_latest 完成, 共分析 %d 条", len(results))
        return results

    def save_to_db(self, news_id: int, analysis: Dict):
        logger.warning(
            "LLMNewsAnalyzer.save_to_db() 仍属于 legacy 兼容路径；"
            "news_analysis.time 在该路径中仅保留旧兼容用途，不得作为新逻辑正式时间字段依赖。"
        )
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS news_analysis (
            id SERIAL PRIMARY KEY,
            news_id INT REFERENCES news_raw(id),
            time TIMESTAMP NOT NULL,
            importance VARCHAR(20),
            direction VARCHAR(20),
            timeframe VARCHAR(20),
            confidence FLOAT,
            reasoning TEXT,
            model_version VARCHAR(50),
            created_at TIMESTAMP DEFAULT NOW(),
            UNIQUE(news_id)
        );
        """
        upsert_sql = """
        INSERT INTO news_analysis (news_id, time, importance, direction, timeframe, confidence, reasoning, model_version)
        VALUES (%s, NOW(), %s, %s, %s, %s, %s, %s)
        ON CONFLICT (news_id) DO UPDATE SET
            importance = EXCLUDED.importance,
            direction = EXCLUDED.direction,
            timeframe = EXCLUDED.timeframe,
            confidence = EXCLUDED.confidence,
            reasoning = EXCLUDED.reasoning,
            model_version = EXCLUDED.model_version,
            created_at = NOW();
        """
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(create_table_sql)
                conn.commit()
                cursor.execute(
                    upsert_sql,
                    (
                        news_id,
                        analysis.get("importance", "irrelevant"),
                        analysis.get("direction", "neutral"),
                        analysis.get("timeframe", "immediate"),
                        analysis.get("confidence", 0.0),
                        analysis.get("reasoning", ""),
                        self.model,
                    ),
                )
                conn.commit()

    def verify_price_impact(self, news_id: int, news_time) -> None:
        logger.warning(
            "verify_price_impact() 仍属于旧一体化兼容路径，会更新 news_analysis 并混入 verification 语义；"
            "本轮未改造，仅因 legacy 兼容而保留。news_id=%d",
            news_id,
        )

    def _call_claude_api(self, prompt: str, retry_count: int = 0) -> Dict:
        api_url = f"{self.base_url}/v1/messages"
        payload = {
            "model": self.model,
            "max_tokens": 1024,
            "messages": [{"role": "user", "content": prompt}],
        }

        try:
            response = self.session.post(
                api_url,
                json=payload,
                timeout=self.timeout,
                proxies={"http": None, "https": None},
            )

            if response.status_code == 429:
                if retry_count < self.max_retries:
                    wait_time = 2 ** retry_count
                    logger.warning("遇到 rate limit (429), 等待 %d 秒后重试", wait_time)
                    time.sleep(wait_time)
                    return self._call_claude_api(prompt, retry_count + 1)
                raise Exception(f"达到最大重试次数 ({self.max_retries}), 仍然遇到 rate limit")

            response.raise_for_status()
            data = response.json()
            content = data.get("content", [])
            if not content or not isinstance(content, list):
                return {
                    "importance": "low",
                    "direction": "neutral",
                    "timeframe": "short-term",
                    "confidence": 0.0,
                    "reasoning": "API error",
                }

            text = content[0].get("text", "")
            if not text:
                raise Exception("API 返回空文本")

            try:
                result = json.loads(text)
            except json.JSONDecodeError:
                result = self._extract_json_from_text(text)

            required_fields = ["importance", "direction", "timeframe", "confidence", "reasoning"]
            for field in required_fields:
                if field not in result:
                    raise Exception(f"分析结果缺少必需字段: {field}")

            if result["importance"] not in ["high", "medium", "low", "irrelevant"]:
                result["importance"] = "irrelevant"
            if result["direction"] not in ["bullish", "bearish", "neutral"]:
                result["direction"] = "neutral"
            if result["timeframe"] not in ["immediate", "short-term", "long-term"]:
                result["timeframe"] = "immediate"

            try:
                result["confidence"] = max(0.0, min(1.0, float(result["confidence"])))
            except (ValueError, TypeError):
                result["confidence"] = 0.0

            return result

        except requests.RequestException as e:
            if retry_count < self.max_retries:
                wait_time = 2 ** retry_count
                logger.warning("API 请求失败: %s, 等待 %d 秒后重试", e, wait_time)
                time.sleep(wait_time)
                return self._call_claude_api(prompt, retry_count + 1)
            return {
                "importance": "low",
                "direction": "neutral",
                "timeframe": "short-term",
                "confidence": 0.0,
                "reasoning": "API error",
            }

    @staticmethod
    def _extract_json_from_text(text: str) -> Dict:
        match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', text, re.DOTALL)
        if match:
            json_str = match.group(0)
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                pass
        logger.error("无法从文本中提取 JSON: %s", text[:200])
        raise Exception(f"无法解析 JSON: {text[:200]}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s - %(message)s")
    analyzer = LLMNewsAnalyzer()
    test_news = {
        "datetime": "2026-03-12 14:35:00",
        "source": "Reuters",
        "title": "Fed signals rate cut in Q2 2026",
        "content": "The Federal Reserve indicated today that it may cut interest rates in the second quarter of 2026 due to slowing inflation. This move is expected to weaken the US dollar and boost gold prices.",
        "url": "https://example.com/news/123",
    }
    print("\n=== 测试单条新闻分析 ===")
    result = analyzer.analyze_news(test_news)
    print(json.dumps(result, indent=2, ensure_ascii=False))

    print("\n=== 测试从数据库读取并分析（默认受保护）===")
    try:
        results = analyzer.fetch_and_analyze_latest(limit=5)
        print(f"共分析 {len(results)} 条新闻")
    except RuntimeError as e:
        print(f"已按预期阻止旧入口执行: {e}")
