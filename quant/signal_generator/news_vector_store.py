"""
新闻向量存储模块 — 基于 ChromaDB 的新闻分析向量化检索

提供:
  - store_news_vectors(): 将 news_analysis 数据批量写入向量库
  - search_similar_news(text, n=5): 检索相似历史新闻
  - get_collection(): 获取底层 ChromaDB collection
"""

import logging
import os
from typing import Any, Dict, List, Optional

import chromadb

logger = logging.getLogger(__name__)

# 持久化目录 & collection 名称
DEFAULT_PERSIST_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), os.pardir, os.pardir,
    "data", "news_vectors"
)
COLLECTION_NAME = "news_analysis_vectors"


def _get_client(persist_dir: Optional[str] = None):
    """获取 ChromaDB 持久化客户端"""
    path = persist_dir or os.path.normpath(DEFAULT_PERSIST_DIR)
    os.makedirs(path, exist_ok=True)
    return chromadb.PersistentClient(path=path)


def get_collection(persist_dir: Optional[str] = None):
    """获取或创建 news_analysis_vectors collection"""
    client = _get_client(persist_dir)
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"description": "Gold news analysis vectors with price impact data"},
    )


def _build_document(title: str, content: str, reasoning: str) -> str:
    """
    构建向量化文本:
      新闻标题 + 内容摘要(前500字) + LLM推理
    """
    content_preview = (content or "")[:500]
    parts = []
    if title:
        parts.append(f"Title: {title}")
    if content_preview:
        parts.append(f"Content: {content_preview}")
    if reasoning:
        parts.append(f"Analysis: {reasoning}")
    return "\n".join(parts)


def store_from_db(
    db_config: Optional[Dict[str, Any]] = None,
    persist_dir: Optional[str] = None,
    batch_size: int = 100,
) -> int:
    """
    从 PostgreSQL 的 news_analysis + news_raw 表中读取数据，
    向量化后存入 ChromaDB。支持增量更新（按 news_id 去重）。

    Returns: 新增记录数
    """
    import psycopg2

    cfg = db_config or {
        "host": "localhost",
        "port": 5432,
        "dbname": "quant_trading",
        "user": "postgres",
        "password": "@Cmx1454697261",
    }

    collection = get_collection(persist_dir)

    # 查询已有 ids 以支持增量
    existing_ids = set()
    try:
        # ChromaDB 1.x: get() 返回 GetResult
        result = collection.get()
        existing_ids = set(result["ids"]) if result["ids"] else set()
    except Exception:
        pass

    conn = psycopg2.connect(**cfg)
    cur = conn.cursor()
    cur.execute("""
        SELECT
            na.news_id,
            nr.title,
            nr.content,
            na.reasoning,
            na.time,
            na.importance,
            na.direction,
            na.confidence,
            na.price_change_30m,
            na.price_change_4h,
            na.price_change_1d,
            na.correct_30m,
            na.correct_4h,
            na.correct_1d,
            na.base_price
        FROM news_analysis na
        JOIN news_raw nr ON na.news_id = nr.id
        WHERE na.reasoning IS NOT NULL
        ORDER BY na.news_id
    """)
    rows = cur.fetchall()
    conn.close()

    # 过滤已存在的
    new_rows = [r for r in rows if f"news_{r[0]}" not in existing_ids]
    if not new_rows:
        logger.info("No new records to store (all %d already in vector store)", len(rows))
        return 0

    # 分批写入
    added = 0
    for i in range(0, len(new_rows), batch_size):
        batch = new_rows[i : i + batch_size]
        ids = []
        documents = []
        metadatas = []

        for row in batch:
            (news_id, title, content, reasoning, time_val,
             importance, direction, confidence,
             pc_30m, pc_4h, pc_1d,
             c_30m, c_4h, c_1d,
             base_price) = row

            doc_id = f"news_{news_id}"
            doc_text = _build_document(title or "", content or "", reasoning or "")
            if not doc_text.strip():
                continue

            meta = {
                "news_id": int(news_id),
                "time": str(time_val) if time_val else "",
                "importance": str(importance or ""),
                "direction": str(direction or ""),
                "confidence": float(confidence) if confidence is not None else 0.0,
                "base_price": float(base_price) if base_price is not None else 0.0,
            }
            # 仅在有值时添加价格变化字段
            if pc_30m is not None:
                meta["price_change_30m"] = float(pc_30m)
            if pc_4h is not None:
                meta["price_change_4h"] = float(pc_4h)
            if pc_1d is not None:
                meta["price_change_1d"] = float(pc_1d)
            if c_30m is not None:
                meta["correct_30m"] = int(c_30m)
            if c_4h is not None:
                meta["correct_4h"] = int(c_4h)
            if c_1d is not None:
                meta["correct_1d"] = int(c_1d)

            ids.append(doc_id)
            documents.append(doc_text)
            metadatas.append(meta)

        if ids:
            collection.add(ids=ids, documents=documents, metadatas=metadatas)
            added += len(ids)
            logger.info("Stored batch %d-%d (%d docs)", i, i + len(batch), len(ids))

    logger.info("Total new records stored: %d (existing: %d)", added, len(existing_ids))
    return added


def search_similar_news(
    query_text: str,
    n_results: int = 5,
    persist_dir: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    检索与输入文本最相似的历史新闻分析。

    Args:
        query_text: 待检索的新闻文本
        n_results: 返回结果数量

    Returns:
        列表，每个元素包含:
          - document: 原始向量化文本
          - metadata: 元数据 (news_id, direction, confidence, price_change_1d 等)
          - distance: 相似度距离 (越小越相似)
    """
    collection = get_collection(persist_dir)

    count = collection.count()
    if count == 0:
        logger.warning("Vector store is empty — run store_from_db() first")
        return []

    # 确保不超过实际数量
    actual_n = min(n_results, count)

    results = collection.query(
        query_texts=[query_text],
        n_results=actual_n,
    )

    output = []
    for i in range(len(results["ids"][0])):
        output.append({
            "id": results["ids"][0][i],
            "document": results["documents"][0][i],
            "metadata": results["metadatas"][0][i],
            "distance": results["distances"][0][i] if results.get("distances") else None,
        })
    return output


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    import argparse

    parser = argparse.ArgumentParser(description="News vector store CLI")
    parser.add_argument("--store", action="store_true", help="Store news from DB")
    parser.add_argument("--search", type=str, help="Search query text")
    parser.add_argument("--top", type=int, default=5, help="Number of results")
    args = parser.parse_args()

    if args.store:
        n = store_from_db()
        print(f"Stored {n} new records")
    elif args.search:
        results = search_similar_news(args.search, n_results=args.top)
        for i, r in enumerate(results, 1):
            print(f"\n--- Result {i} (distance={r['distance']:.4f}) ---")
            meta = r["metadata"]
            print(f"  news_id: {meta.get('news_id')}")
            print(f"  time: {meta.get('time')}")
            print(f"  direction: {meta.get('direction')}, confidence: {meta.get('confidence')}")
            print(f"  importance: {meta.get('importance')}")
            if "price_change_1d" in meta:
                print(f"  price_change_1d: {meta['price_change_1d']:.4f}%")
            if "correct_1d" in meta:
                print(f"  correct_1d: {meta['correct_1d']}")
            print(f"  document preview: {r['document'][:200]}...")
    else:
        parser.print_help()
