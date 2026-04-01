"""Run verify dry-run with per-record error catching."""
import sys, os, traceback
os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.path.insert(0, r'E:\quant-trading-mvp')
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

import psycopg2
import psycopg2.extras
from quant.common.config import config
from scripts.verify_news_price_impact import (
    find_best_symbol, find_price, find_daily_base_price, find_daily_price_1d,
    compute_correctness, fmt_pct
)
from datetime import timedelta

DB_CONFIG = dict(
    host=config.database.host,
    port=config.database.port,
    dbname=config.database.database,
    user=config.database.user,
    password=config.database.password.get_secret_value(),
)

conn = psycopg2.connect(**DB_CONFIG)
cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

anchor_expr = "COALESCE(na.effective_time, na.analyzed_at, na.published_time, nr.time)"

cur.execute(f"""
    SELECT na.id, na.news_id,
           {anchor_expr} AS anchor_time,
           na.direction, na.importance
    FROM news_analysis na
    JOIN news_raw nr ON na.news_id = nr.id
    ORDER BY {anchor_expr}
""")
records = cur.fetchall()
print(f"Total records: {len(records)}", flush=True)

error_count = 0
success_count = 0

for i, rec in enumerate(records):
    try:
        na_id = rec['id']
        anchor_ts = rec['anchor_time']
        if anchor_ts is None:
            continue
        symbol = find_best_symbol(cur, anchor_ts)
        base_price = None
        if symbol:
            base_price, base_time = find_price(cur, symbol, anchor_ts, direction='nearest')
        if base_price is None:
            base_price, base_time = find_daily_base_price(cur, anchor_ts)
            symbol = None
        if base_price is None:
            continue
        success_count += 1
    except Exception as e:
        error_count += 1
        if error_count <= 5:
            print(f"Error at record {i} (id={rec['id']}): {e}", flush=True)

    if (i+1) % 100 == 0:
        print(f"  processed {i+1}/{len(records)}, ok={success_count}, err={error_count}", flush=True)

print(f"\nDone: {len(records)} total, {success_count} with price, {error_count} errors", flush=True)
cur.close()
conn.close()
