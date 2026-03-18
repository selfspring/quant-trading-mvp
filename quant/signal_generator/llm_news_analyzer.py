"""
LLM 新闻解读模块
使用 Claude Opus 4 分析新闻对黄金期货的影响

核心功能:
- 从 news_raw 表读取未分析的新闻
- 调用 Claude API 进行结构化分析
- 将分析结果存入 news_signals 表
- 支持单条和批量分析
"""

import json
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional

import requests

from quant.common.config import config
from quant.common.db_pool import get_db_connection

logger = logging.getLogger(__name__)


class LLMNewsAnalyzer:
    """LLM 新闻分析器
    
    使用 Claude Opus 4 分析新闻对黄金期货价格的影响，
    返回结构化的分析结果（重要性、方向、时间框架、置信度）。
    """

    # Claude API 配置
    ANTHROPIC_VERSION = "2023-06-01"
    
    # 分析 Prompt 模板
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

    def __init__(self, api_key: Optional[str] = None, model: str = "claude-opus-4"):
        """初始化 LLM 新闻分析器
        
        Parameters
        ----------
        api_key : str, optional
            Claude API Key，如果为 None 则从 config 读取
        model : str
            Claude 模型名称，默认 claude-opus-4
        """
        self.api_key = api_key or config.claude.api_key.get_secret_value()
        self.model = model
        self.base_url = config.claude.base_url
        self.timeout = config.claude.timeout
        self.max_retries = config.claude.max_retries
        
        self.session = requests.Session()
        self.session.headers.update({
            "x-api-key": self.api_key,
            "anthropic-version": self.ANTHROPIC_VERSION,
            "content-type": "application/json",
        })
        
        logger.info(
            "LLMNewsAnalyzer 初始化完成, model=%s, base_url=%s, timeout=%ds",
            self.model,
            self.base_url,
            self.timeout,
        )

    def analyze_news(self, news: Dict) -> Dict:
        """分析单条新闻
        
        Parameters
        ----------
        news : dict
            新闻数据，格式:
            {
                "datetime": "2026-03-12 14:35:00",
                "source": "Reuters",
                "title": "Fed signals rate cut in Q2",
                "content": "The Federal Reserve...",
                "url": "https://..."
            }
        
        Returns
        -------
        dict
            分析结果，格式:
            {
                "importance": "high|medium|low|irrelevant",
                "direction": "bullish|bearish|neutral",
                "timeframe": "immediate|short-term|long-term",
                "confidence": 0.0-1.0,
                "reasoning": "简短解释"
            }
        """
        # 构建 prompt
        prompt = self.ANALYSIS_PROMPT.format(
            title=news.get("title", ""),
            content=news.get("content", ""),
            source=news.get("source", ""),
            datetime=news.get("datetime", ""),
        )
        
        # 调用 Claude API
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
            # 返回默认值（irrelevant）
            return {
                "importance": "irrelevant",
                "direction": "neutral",
                "timeframe": "immediate",
                "confidence": 0.0,
                "reasoning": f"分析失败: {str(e)[:50]}",
            }

    def analyze_batch(self, news_list: List[Dict]) -> List[Dict]:
        """批量分析新闻
        
        Parameters
        ----------
        news_list : list of dict
            新闻列表
        
        Returns
        -------
        list of dict
            分析结果列表，顺序与输入一致
        """
        if not news_list:
            logger.warning("analyze_batch: 输入为空列表")
            return []
        
        logger.info("开始批量分析 %d 条新闻", len(news_list))
        results = []
        
        for i, news in enumerate(news_list, 1):
            try:
                result = self.analyze_news(news)
                results.append(result)
                
                # 避免 API rate limit，每条新闻之间间隔
                if i < len(news_list):
                    time.sleep(1.0)
            except Exception as e:
                logger.error("批量分析第 %d 条新闻失败: %s", i, e)
                results.append({
                    "importance": "irrelevant",
                    "direction": "neutral",
                    "timeframe": "immediate",
                    "confidence": 0.0,
                    "reasoning": f"批量分析失败: {str(e)[:50]}",
                })
        
        logger.info("批量分析完成, 共 %d 条", len(results))
        return results

    def fetch_and_analyze_latest(self, limit: int = 10) -> List[Dict]:
        """从数据库读取最新未分析的新闻并分析
        
        Parameters
        ----------
        limit : int
            最多读取的新闻条数，默认 10
        
        Returns
        -------
        list of dict
            分析结果列表，每个元素包含:
            {
                "news_id": 12345,
                "datetime": "2026-03-12 14:35:00",
                "analysis": {...}  # analyze_news 的返回值
            }
        """
        logger.info("开始读取最新未分析的新闻, limit=%d", limit)
        
        # 查询未分析的新闻（不在 news_signals 表中的）
        query_sql = """
        SELECT id, datetime, source, title, content, url
        FROM news_raw
        WHERE id NOT IN (SELECT news_id FROM news_signals WHERE news_id IS NOT NULL)
        ORDER BY datetime DESC
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
                    
                    logger.info("读取到 %d 条未分析的新闻", len(rows))
                    
                    # 转换为字典列表
                    news_list = []
                    for row in rows:
                        news_list.append({
                            "id": row[0],
                            "datetime": row[1].strftime("%Y-%m-%d %H:%M:%S") if row[1] else "",
                            "source": row[2] or "",
                            "title": row[3] or "",
                            "content": row[4] or "",
                            "url": row[5] or "",
                        })
        except Exception as e:
            logger.error("读取未分析新闻失败: %s", e, exc_info=True)
            return []
        
        # 批量分析
        results = []
        for news in news_list:
            analysis = self.analyze_news(news)
            results.append({
                "news_id": news["id"],
                "datetime": news["datetime"],
                "analysis": analysis,
            })
            
            # 立即保存到数据库
            try:
                self.save_to_db(news["id"], analysis)
            except Exception as e:
                logger.error("保存分析结果失败 (news_id=%d): %s", news["id"], e)
            
            # 避免 API rate limit
            time.sleep(1.0)
        
        logger.info("fetch_and_analyze_latest 完成, 共分析 %d 条", len(results))
        return results

    def save_to_db(self, news_id: int, analysis: Dict):
        """保存分析结果到 news_signals 表
        
        Parameters
        ----------
        news_id : int
            新闻 ID（news_raw 表的主键）
        analysis : dict
            分析结果，格式见 analyze_news 返回值
        """
        # 自动建表
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS news_signals (
            id SERIAL PRIMARY KEY,
            news_id INT REFERENCES news_raw(id),
            datetime TIMESTAMP NOT NULL,
            importance VARCHAR(20),
            direction VARCHAR(20),
            timeframe VARCHAR(20),
            confidence FLOAT,
            reasoning TEXT,
            created_at TIMESTAMP DEFAULT NOW(),
            UNIQUE(news_id)
        );
        """
        
        # 插入数据（冲突时更新）
        upsert_sql = """
        INSERT INTO news_signals (news_id, datetime, importance, direction, timeframe, confidence, reasoning)
        VALUES (%s, NOW(), %s, %s, %s, %s, %s)
        ON CONFLICT (news_id) DO UPDATE SET
            importance = EXCLUDED.importance,
            direction = EXCLUDED.direction,
            timeframe = EXCLUDED.timeframe,
            confidence = EXCLUDED.confidence,
            reasoning = EXCLUDED.reasoning,
            created_at = NOW();
        """
        
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    # 确保表存在
                    cursor.execute(create_table_sql)
                    conn.commit()
                    
                    # 插入/更新数据
                    cursor.execute(
                        upsert_sql,
                        (
                            news_id,
                            analysis.get("importance", "irrelevant"),
                            analysis.get("direction", "neutral"),
                            analysis.get("timeframe", "immediate"),
                            analysis.get("confidence", 0.0),
                            analysis.get("reasoning", ""),
                        ),
                    )
                    conn.commit()
                    
                    logger.debug("分析结果已保存: news_id=%d", news_id)
        except Exception as e:
            logger.error("保存分析结果失败 (news_id=%d): %s", news_id, e, exc_info=True)
            raise

    def _call_claude_api(self, prompt: str, retry_count: int = 0) -> Dict:
        """调用 Claude API 进行分析
        
        Parameters
        ----------
        prompt : str
            分析 prompt
        retry_count : int
            当前重试次数
        
        Returns
        -------
        dict
            解析后的 JSON 结果
        
        Raises
        ------
        Exception
            API 调用失败或 JSON 解析失败
        """
        api_url = f"{self.base_url}/v1/messages"
        
        payload = {
            "model": self.model,
            "max_tokens": 1024,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
        }
        
        try:
            response = self.session.post(
                api_url,
                json=payload,
                timeout=self.timeout,
            )
            
            # 处理 rate limit (429)
            if response.status_code == 429:
                if retry_count < self.max_retries:
                    wait_time = 2 ** retry_count  # 指数退避
                    logger.warning(
                        "遇到 rate limit (429), 等待 %d 秒后重试 (第 %d/%d 次)",
                        wait_time,
                        retry_count + 1,
                        self.max_retries,
                    )
                    time.sleep(wait_time)
                    return self._call_claude_api(prompt, retry_count + 1)
                else:
                    raise Exception(f"达到最大重试次数 ({self.max_retries}), 仍然遇到 rate limit")
            
            # 其他错误
            response.raise_for_status()
            
            # 解析响应
            data = response.json()
            content = data.get("content", [])
            
            if not content or not isinstance(content, list):
                raise Exception(f"API 响应格式异常: {data}")
            
            # 提取文本内容
            text = content[0].get("text", "")
            
            if not text:
                raise Exception("API 返回空文本")
            
            # 解析 JSON
            try:
                result = json.loads(text)
            except json.JSONDecodeError as e:
                # JSON 解析失败，尝试提取 JSON 片段
                logger.warning("JSON 解析失败，尝试提取 JSON 片段: %s", e)
                result = self._extract_json_from_text(text)
            
            # 验证必需字段
            required_fields = ["importance", "direction", "timeframe", "confidence", "reasoning"]
            for field in required_fields:
                if field not in result:
                    raise Exception(f"分析结果缺少必需字段: {field}")
            
            # 验证字段值
            if result["importance"] not in ["high", "medium", "low", "irrelevant"]:
                logger.warning("importance 值异常: %s, 设为 irrelevant", result["importance"])
                result["importance"] = "irrelevant"
            
            if result["direction"] not in ["bullish", "bearish", "neutral"]:
                logger.warning("direction 值异常: %s, 设为 neutral", result["direction"])
                result["direction"] = "neutral"
            
            if result["timeframe"] not in ["immediate", "short-term", "long-term"]:
                logger.warning("timeframe 值异常: %s, 设为 immediate", result["timeframe"])
                result["timeframe"] = "immediate"
            
            # 确保 confidence 在 0-1 之间
            try:
                confidence = float(result["confidence"])
                result["confidence"] = max(0.0, min(1.0, confidence))
            except (ValueError, TypeError):
                logger.warning("confidence 值异常: %s, 设为 0.0", result["confidence"])
                result["confidence"] = 0.0
            
            return result
            
        except requests.RequestException as e:
            if retry_count < self.max_retries:
                wait_time = 2 ** retry_count
                logger.warning(
                    "API 请求失败: %s, 等待 %d 秒后重试 (第 %d/%d 次)",
                    e,
                    wait_time,
                    retry_count + 1,
                    self.max_retries,
                )
                time.sleep(wait_time)
                return self._call_claude_api(prompt, retry_count + 1)
            else:
                raise Exception(f"API 请求失败 (已重试 {self.max_retries} 次): {e}")

    @staticmethod
    def _extract_json_from_text(text: str) -> Dict:
        """从文本中提取 JSON 片段
        
        当 Claude 返回的文本包含额外说明时，尝试提取 JSON 部分。
        
        Parameters
        ----------
        text : str
            包含 JSON 的文本
        
        Returns
        -------
        dict
            解析后的 JSON
        
        Raises
        ------
        Exception
            无法提取或解析 JSON
        """
        import re
        
        # 尝试匹配 JSON 对象
        match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', text, re.DOTALL)
        
        if match:
            json_str = match.group(0)
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                pass
        
        # 如果无法提取，返回默认值
        logger.error("无法从文本中提取 JSON: %s", text[:200])
        raise Exception(f"无法解析 JSON: {text[:200]}")


# ------------------------------------------------------------------
# 独立测试入口
# ------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    )
    
    # 测试单条新闻分析
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
    
    # 测试从数据库读取并分析
    print("\n=== 测试从数据库读取并分析 ===")
    results = analyzer.fetch_and_analyze_latest(limit=5)
    print(f"共分析 {len(results)} 条新闻")
    for r in results:
        print(f"  news_id={r['news_id']}, importance={r['analysis']['importance']}, direction={r['analysis']['direction']}")
