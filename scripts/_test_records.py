"""Minimal test: can we iterate all 869 records without error?"""
import sys, os
os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.path.insert(0, r'E:\quant-trading-mvp')
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

import psycopg2
import psycopg2.extras
from quant.common.config import config

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
           na.direction
    FROM news_analysis na
    JOIN news_raw nr ON na.news_id = nr.id
    ORDER BY {anchor_expr}
""")
records = cur.fetchall()
print(f"Fetched {len(records)} records", flush=True)

# Simple iteration - just count non-null anchors
nulls = sum(1 for r in records if r['anchor_time'] is None)
print(f"NULL anchors: {nulls}", flush=True)
print(f"Non-NULL anchors: {len(records) - nulls}", flush=True)

# Now try find_best_symbol for just record 100-110
from scripts.verify_news_price_impact import find_best_symbol, find_price
from datetime import timedelta

for r in records[100:105]:
    anchor = r['anchor_time']
    sym = find_best_symbol(cur, anchor)
    if sym:
        bp, bt = find_price(cur, sym, anchor, direction='nearest')
        print(f"  id={r['id']}, anchor={anchor}, sym={sym}, base_price={bp}", flush=True)
    else:
        print(f"  id={r['id']}, anchor={anchor}, no symbol", flush=True)

print("Test complete", flush=True)
cur.close()
conn.close()
