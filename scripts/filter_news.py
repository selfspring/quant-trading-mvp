"""
Task #2: Pre-filter historical news — mark gold/macro/geopolitical-related news.
Refined keyword approach: title-only matching with curated keyword list.
Uses Python-side filtering for speed.
"""
import io
import os
import sys
import traceback
from collections import defaultdict

os.environ['PYTHONIOENCODING'] = 'utf-8'
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import psycopg2

DB_CONFIG = dict(host='localhost', port=5432, dbname='quant_trading',
                 user='postgres', password='@Cmx1454697261')

LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'filter_news_log.txt')

def log(msg):
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(str(msg) + '\n')

with open(LOG_FILE, 'w', encoding='utf-8') as f:
    f.write('')

# --- KEYWORDS ---
# Title-only matching. Each keyword mapped to its category.
# Removed overly broad terms, kept gold/macro/finance relevant ones.
KEYWORD_CATEGORIES = {
    'gold_direct': [
        'gold',           # gold price, gold market, goldmine etc
        'precious metal',
        'bullion',
        'xau',
    ],
    'central_bank_policy': [
        'federal reserve',
        'interest rate',
        'rate hike',
        'rate cut',
        'monetary policy',
        'quantitative easing',
        'central bank',
        'fomc',
    ],
    'inflation_macro': [
        'inflation',
        'deflation',
        'stagflation',
        'recession',
        'consumer price',
        'economic growth',
        'economic slowdown',
        'gdp',
    ],
    'currency_bond': [
        'us dollar',
        'dollar index',
        'treasury',
        'bond yield',
        'yield curve',
        'eurozone',
        'yuan',
        'currency',
    ],
    'geopolitical': [
        'sanctions',      # keep - financial sanctions affect gold
        'tariff',
        'trade war',
        'geopolitical',
        'safe haven',
        'middle east',
    ],
    'commodities_energy': [
        'oil price',
        'crude oil',
        'opec',
        'commodity',
        'silver',         # precious metals context
        'mining',         # often about gold/silver mining
    ],
    'fed_ecb': [
        'ecb',
        'bank of england',
    ],
    'employment': [
        'unemployment',
        'jobs report',
        'payroll',
        'nonfarm',
        'non-farm',
    ],
}

# Ukraine: only include if title ALSO mentions a financial keyword
# This avoids pure war/politics articles about Ukraine
UKRAINE_FINANCIAL_COWORDS = [
    'sanction', 'oil', 'gas', 'energy', 'market', 'economy', 'economic',
    'price', 'inflation', 'ruble', 'rouble', 'currency', 'trade',
    'stock', 'shares', 'ftse', 'bond', 'gold', 'commodity',
    'central bank', 'interest', 'recession',
]


def match_article(title_lower):
    """Check if title matches any keyword. Returns (matched: bool, categories: set)."""
    matched_cats = set()
    for cat, keywords in KEYWORD_CATEGORIES.items():
        for kw in keywords:
            if kw in title_lower:
                matched_cats.add(cat)
                break

    # Special Ukraine handling
    if 'ukraine' in title_lower or 'russia' in title_lower:
        for coword in UKRAINE_FINANCIAL_COWORDS:
            if coword in title_lower:
                matched_cats.add('geopolitical_ukraine')
                break

    return len(matched_cats) > 0, matched_cats


try:
    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = True
    cur = conn.cursor()
    log("Connected to database.")

    # Ensure clean column
    cur.execute("""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'news_raw' AND column_name = 'is_gold_related'
        )
    """)
    if cur.fetchone()[0]:
        log("Column exists, will update values.")
    else:
        log("Adding is_gold_related column...")
        cur.execute("ALTER TABLE news_raw ADD COLUMN is_gold_related BOOLEAN DEFAULT FALSE")
        log("  Column added.")

    # Fetch all guardian titles
    log("Fetching guardian news titles...")
    cur.execute("SELECT id, title, time FROM news_raw WHERE source = 'guardian'")
    rows = cur.fetchall()
    total_guardian = len(rows)
    log(f"Fetched {total_guardian} guardian rows.")

    # Python-side filtering
    log("Filtering...")
    matched_ids = []
    all_category_counts = defaultdict(int)
    year_counts = defaultdict(int)
    keyword_hit_counts = defaultdict(int)  # per-keyword

    for row_id, title, time_val in rows:
        title_lower = (title or '').lower()
        matched, cats = match_article(title_lower)

        if matched:
            matched_ids.append(row_id)
            for cat in cats:
                all_category_counts[cat] += 1
            if time_val:
                year_counts[time_val.year] += 1
            # Track individual keywords
            for cat, keywords in KEYWORD_CATEGORIES.items():
                for kw in keywords:
                    if kw in title_lower:
                        keyword_hit_counts[kw] += 1

    filtered_count = len(matched_ids)
    log(f"\nFiltered Guardian news: {filtered_count} / {total_guardian}")
    log(f"Filter ratio: {filtered_count/total_guardian*100:.1f}%")

    # Check target range
    if 3000 <= filtered_count <= 10000:
        log("IN TARGET RANGE [3000, 10000]")
    else:
        log("WARNING: Outside target range [3000, 10000]")

    # Batch update - first set all guardian to FALSE, then set matched to TRUE
    log("\nUpdating database...")

    # Set all guardian to FALSE in batches
    cur.execute("SELECT id FROM news_raw WHERE source = 'guardian'")
    all_ids = [r[0] for r in cur.fetchall()]
    batch_size = 2000
    for i in range(0, len(all_ids), batch_size):
        batch = all_ids[i:i+batch_size]
        placeholders = ','.join(['%s'] * len(batch))
        cur.execute(f"UPDATE news_raw SET is_gold_related = FALSE WHERE id IN ({placeholders})", batch)
    log(f"  Set {len(all_ids)} guardian rows to FALSE.")

    # Set matched to TRUE
    for i in range(0, len(matched_ids), batch_size):
        batch = matched_ids[i:i+batch_size]
        placeholders = ','.join(['%s'] * len(batch))
        cur.execute(f"UPDATE news_raw SET is_gold_related = TRUE WHERE id IN ({placeholders})", batch)
    log(f"  Set {len(matched_ids)} matched rows to TRUE.")

    # Mark all non-guardian as gold-related
    cur.execute("UPDATE news_raw SET is_gold_related = TRUE WHERE source != 'guardian'")
    non_guardian = cur.rowcount
    log(f"  Marked {non_guardian} non-guardian rows as TRUE.")

    # Create news_filtered table
    log("\nCreating news_filtered table...")
    cur.execute("DROP TABLE IF EXISTS news_filtered CASCADE")
    cur.execute("""
        CREATE TABLE news_filtered AS
        SELECT * FROM news_raw
        WHERE is_gold_related = TRUE
    """)
    cur.execute("CREATE INDEX idx_news_filtered_time ON news_filtered(time)")
    cur.execute("CREATE INDEX idx_news_filtered_source ON news_filtered(source)")
    cur.execute("CREATE INDEX idx_news_filtered_id ON news_filtered(id)")

    cur.execute("SELECT COUNT(*) FROM news_filtered")
    nf_final = cur.fetchone()[0]
    log(f"news_filtered table created with {nf_final} rows.")

    # === STATISTICS ===
    log("\n" + "="*60)
    log("STATISTICS")
    log("="*60)

    log("\n--- Year Distribution (filtered Guardian) ---")
    for yr in sorted(year_counts.keys()):
        log(f"  {yr}: {year_counts[yr]}")

    log("\n--- Keyword Category Distribution ---")
    for cat in sorted(all_category_counts.keys()):
        log(f"  {cat}: {all_category_counts[cat]}")

    log("\n--- Top 20 Individual Keyword Matches ---")
    sorted_kw = sorted(keyword_hit_counts.items(), key=lambda x: x[1], reverse=True)
    for kw, count in sorted_kw[:20]:
        log(f"  {kw}: {count}")

    # Final summary
    cur.execute("SELECT COUNT(*) FROM news_raw WHERE is_gold_related = TRUE")
    total_related = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM news_raw")
    total_all = cur.fetchone()[0]

    log("\n--- FINAL SUMMARY ---")
    log(f"Total news_raw: {total_all}")
    log(f"Total gold-related: {total_related}")
    log(f"  Guardian filtered: {filtered_count} / {total_guardian}")
    log(f"  Non-guardian (all macro): {non_guardian}")
    log(f"news_filtered table rows: {nf_final}")

    conn.close()
    log("\nDone!")
    print("DONE - see filter_news_log.txt for full output")

except Exception as e:
    log(f"\nERROR: {e}")
    log(traceback.format_exc())
    print(f"ERROR: {e}")
    sys.exit(1)
