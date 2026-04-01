"""
将 news_analysis 中的分析结果向量化存储到 ChromaDB。

用法:
    python scripts/store_news_vectors.py          # 存储所有新闻
    python scripts/store_news_vectors.py --test    # 存储后运行检索测试
"""

import io
import os
import sys

# Windows GBK 编码兜底
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# 确保项目根目录在 sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), os.pardir))

import logging  # noqa: E402

from quant.signal_generator.news_vector_store import (  # noqa: E402
    get_collection,
    search_similar_news,
    store_from_db,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

PERSIST_DIR = os.path.normpath(
    os.path.join(os.path.dirname(__file__), os.pardir, "data", "news_vectors")
)


def main():
    import argparse  # noqa: E402

    parser = argparse.ArgumentParser()
    parser.add_argument("--test", action="store_true", help="Run search tests after storing")
    args = parser.parse_args()

    print(f"=== Storing news vectors to {PERSIST_DIR} ===")
    n = store_from_db(persist_dir=PERSIST_DIR)
    print(f"New records stored: {n}")

    col = get_collection(persist_dir=PERSIST_DIR)
    print(f"Total documents in collection: {col.count()}")

    if args.test or True:  # 始终运行测试
        run_search_tests()


def run_search_tests():
    print("\n" + "=" * 60)
    print("=== Search Test 1: Federal Reserve raises interest rates ===")
    print("=" * 60)
    results = search_similar_news(
        "Federal Reserve raises interest rates",
        n_results=5,
        persist_dir=PERSIST_DIR,
    )
    for i, r in enumerate(results, 1):
        meta = r["metadata"]
        print(f"\n  [{i}] distance={r['distance']:.4f}")
        print(f"      news_id={meta.get('news_id')}, direction={meta.get('direction')}, "
              f"confidence={meta.get('confidence')}")
        if "price_change_1d" in meta:
            print(f"      price_change_1d={meta['price_change_1d']:.4f}%")
        doc_lines = r["document"].split("\n")
        title_line = doc_lines[0] if doc_lines else ""
        print(f"      {title_line[:100]}")

    print("\n" + "=" * 60)
    print("=== Search Test 2: Russia Ukraine war escalation ===")
    print("=" * 60)
    results = search_similar_news(
        "Russia Ukraine war escalation",
        n_results=5,
        persist_dir=PERSIST_DIR,
    )
    for i, r in enumerate(results, 1):
        meta = r["metadata"]
        print(f"\n  [{i}] distance={r['distance']:.4f}")
        print(f"      news_id={meta.get('news_id')}, direction={meta.get('direction')}, "
              f"confidence={meta.get('confidence')}")
        if "price_change_1d" in meta:
            print(f"      price_change_1d={meta['price_change_1d']:.4f}%")
        doc_lines = r["document"].split("\n")
        title_line = doc_lines[0] if doc_lines else ""
        print(f"      {title_line[:100]}")


if __name__ == "__main__":
    main()
