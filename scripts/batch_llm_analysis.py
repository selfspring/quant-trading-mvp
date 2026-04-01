"""
批量 LLM 新闻分析脚本（baseline 唯一主入口）。

使用 Provider 5 (OpenAI Chat Completions 格式) 批量分析 news_filtered 中的新闻，
结果写入 news_analysis 表，支持断点续传和 --limit 参数。

P0 入口约束：
- `scripts/batch_llm_analysis.py` 是当前 baseline 唯一分析入口
- `scripts/run_llm_analysis.py` 已停用，不再作为主链路入口
- 本脚本负责 baseline analysis 写入链路中的最小时间语义落地：写入 `published_time / analyzed_at / effective_time`
- 当前默认规则：`effective_time = analyzed_at`
- `news_analysis.time` 仅保留 legacy ambiguous 兼容语义，不得新增业务依赖
- 本脚本不在本轮顺手处理 verification 分层 / RAG / 全量历史回填

用法:
    python scripts/batch_llm_analysis.py --limit 20
"""

import argparse
import json
import logging
import re
import time
from datetime import datetime

import psycopg2
import requests

from quant.common.config import config

# ── 配置 ──────────────────────────────────────────────────────────

PROVIDER5_BASE_URL = config.claude.base_url.rstrip("/")
PROVIDER5_API_KEY = config.claude.api_key.get_secret_value()
PROVIDER5_MODEL = config.claude.model

DB_CONFIG = dict(
    host=config.database.host,
    port=config.database.port,
    dbname=config.database.database,
    user=config.database.user,
    password=config.database.password.get_secret_value(),
)

BATCH_SIZE = 10       # 每批条数
BATCH_DELAY = 2.0     # 批间间隔 (秒)
ITEM_DELAY = 0.5      # 条间间隔 (秒)
REQUEST_TIMEOUT = 120  # 单次请求超时 (秒)
MAX_RETRIES = 3       # 单条最大重试次数

# ── Prompt (复用 LLMNewsAnalyzer.ANALYSIS_PROMPT) ─────────────────

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

# ── Logging ───────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("batch_llm")


# ── DB helpers ────────────────────────────────────────────────────

def get_conn():
    return psycopg2.connect(**DB_CONFIG)


def fetch_pending_news(limit: int):
    """从 news_filtered 读取尚未分析的新闻, 返回 list[dict]."""
    sql = """
        SELECT nf.id, nf.time, nf.source, nf.title, nf.content
        FROM news_filtered nf
        WHERE nf.id NOT IN (
            SELECT news_id FROM news_analysis WHERE news_id IS NOT NULL
        )
        ORDER BY nf.time ASC
        LIMIT %s;
    """
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(sql, (limit,))
        rows = cur.fetchall()
        return [
            {
                "id": r[0],
                "time": r[1],
                "source": r[2] or "",
                "title": r[3] or "",
                "content": r[4] or "",
            }
            for r in rows
        ]
    finally:
        conn.close()


def ensure_time_semantics_columns():
    """为 news_analysis 补齐最小时间语义字段。"""
    alter_sql = """
        ALTER TABLE news_analysis
        ADD COLUMN IF NOT EXISTS published_time TIMESTAMPTZ,
        ADD COLUMN IF NOT EXISTS analyzed_at TIMESTAMPTZ,
        ADD COLUMN IF NOT EXISTS effective_time TIMESTAMPTZ;
    """
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(alter_sql)
        conn.commit()
    finally:
        conn.close()


def save_analysis(news_id: int, published_time, analysis: dict, model_version: str, analyzed_at=None):
    """Upsert 单条分析结果到 news_analysis，并补齐正式时间字段。"""
    analyzed_at = analyzed_at or datetime.utcnow()
    effective_time = analyzed_at
    upsert_sql = """
        INSERT INTO news_analysis
            (
                news_id,
                time,
                published_time,
                analyzed_at,
                effective_time,
                importance,
                direction,
                timeframe,
                confidence,
                reasoning,
                model_version
            )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (news_id) DO UPDATE SET
            time = EXCLUDED.time,
            published_time = EXCLUDED.published_time,
            analyzed_at = EXCLUDED.analyzed_at,
            effective_time = EXCLUDED.effective_time,
            importance = EXCLUDED.importance,
            direction = EXCLUDED.direction,
            timeframe = EXCLUDED.timeframe,
            confidence = EXCLUDED.confidence,
            reasoning = EXCLUDED.reasoning,
            model_version = EXCLUDED.model_version,
            created_at = NOW();
    """
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(upsert_sql, (
            news_id,
            analyzed_at,
            published_time,
            analyzed_at,
            effective_time,
            analysis.get("importance", "irrelevant"),
            analysis.get("direction", "neutral"),
            analysis.get("timeframe", "immediate"),
            analysis.get("confidence", 0.0),
            analysis.get("reasoning", ""),
            model_version,
        ))
        conn.commit()
    finally:
        conn.close()


# ── LLM call (OpenAI Chat Completions format) ────────────────────

def call_llm(prompt: str, retry: int = 0) -> dict:
    """调用 Provider 5 API, 返回解析后的 JSON dict."""
    url = f"{PROVIDER5_BASE_URL}/chat/completions"
    headers = {
        "Authorization": f"Bearer {PROVIDER5_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": PROVIDER5_MODEL,
        "max_tokens": 512,
        "messages": [
            {"role": "user", "content": prompt},
        ],
    }

    try:
        resp = requests.post(
            url,
            json=payload,
            headers=headers,
            timeout=REQUEST_TIMEOUT,
            proxies={"http": None, "https": None},
        )

        if resp.status_code == 429:
            if retry < MAX_RETRIES:
                wait = 2 ** (retry + 1)
                log.warning("Rate limited (429), waiting %ds (retry %d/%d)", wait, retry + 1, MAX_RETRIES)
                time.sleep(wait)
                return call_llm(prompt, retry + 1)
            raise RuntimeError("Rate limit exceeded after max retries")

        resp.raise_for_status()
        data = resp.json()
        content_text = data["choices"][0]["message"]["content"]
        return parse_json_response(content_text)

    except requests.RequestException as e:
        if retry < MAX_RETRIES:
            wait = 2 ** (retry + 1)
            log.warning("Request failed: %s, retrying in %ds (%d/%d)", e, wait, retry + 1, MAX_RETRIES)
            time.sleep(wait)
            return call_llm(prompt, retry + 1)
        raise


def parse_json_response(text: str) -> dict:
    """从 LLM 响应中解析 JSON, 带容错."""
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass

    match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    log.error("Cannot parse JSON from response: %s", text[:200])
    return {
        "importance": "irrelevant",
        "direction": "neutral",
        "timeframe": "immediate",
        "confidence": 0.0,
        "reasoning": "JSON parse failed",
    }


def validate_analysis(result: dict) -> dict:
    """校验并规范化分析结果字段."""
    valid_importance = {"high", "medium", "low", "irrelevant"}
    valid_direction = {"bullish", "bearish", "neutral"}
    valid_timeframe = {"immediate", "short-term", "long-term"}

    if result.get("importance") not in valid_importance:
        result["importance"] = "irrelevant"
    if result.get("direction") not in valid_direction:
        result["direction"] = "neutral"
    if result.get("timeframe") not in valid_timeframe:
        result["timeframe"] = "immediate"

    try:
        result["confidence"] = max(0.0, min(1.0, float(result.get("confidence", 0))))
    except (ValueError, TypeError):
        result["confidence"] = 0.0

    if "reasoning" not in result:
        result["reasoning"] = ""

    return result


# ── Main ──────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Batch LLM news analysis")
    parser.add_argument("--limit", type=int, default=20, help="Max news to analyze this run")
    args = parser.parse_args()

    log.info("=== Batch LLM Analysis Start (limit=%d) ===", args.limit)
    ensure_time_semantics_columns()

    pending = fetch_pending_news(args.limit)
    if not pending:
        log.info("No pending news to analyze. Done.")
        return

    log.info("Found %d pending news to analyze", len(pending))

    success_count = 0
    fail_count = 0

    for batch_start in range(0, len(pending), BATCH_SIZE):
        batch = pending[batch_start: batch_start + BATCH_SIZE]
        batch_num = batch_start // BATCH_SIZE + 1
        total_batches = (len(pending) + BATCH_SIZE - 1) // BATCH_SIZE
        log.info("--- Batch %d/%d (%d items) ---", batch_num, total_batches, len(batch))

        for i, news in enumerate(batch):
            news_id = news["id"]
            title_short = (news["title"] or "")[:60]
            dt_str = news["time"].strftime("%Y-%m-%d %H:%M:%S") if news["time"] else ""

            log.info("[%d/%d] id=%d: %s", batch_start + i + 1, len(pending), news_id, title_short)

            content_truncated = (news["content"] or "")[:1500]
            prompt = ANALYSIS_PROMPT.format(
                title=news["title"],
                content=content_truncated,
                source=news["source"],
                datetime=dt_str,
            )

            try:
                result = call_llm(prompt)
                result = validate_analysis(result)
                analyzed_at = datetime.utcnow()
                save_analysis(news_id, news["time"], result, PROVIDER5_MODEL, analyzed_at=analyzed_at)
                log.info(
                    "  -> %s / %s / conf=%.2f / %s",
                    result["importance"],
                    result["direction"],
                    result["confidence"],
                    result["reasoning"][:40],
                )
                success_count += 1
            except Exception as e:
                log.error("  -> FAILED: %s", e)
                fail_count += 1

            if i < len(batch) - 1:
                time.sleep(ITEM_DELAY)

        if batch_start + BATCH_SIZE < len(pending):
            log.info("Batch done. Waiting %.1fs...", BATCH_DELAY)
            time.sleep(BATCH_DELAY)

    log.info("=== Batch LLM Analysis Complete ===")
    log.info("Success: %d, Failed: %d, Total: %d", success_count, fail_count, len(pending))

    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM news_analysis")
        total = cur.fetchone()[0]
        log.info("Total records in news_analysis: %d", total)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
