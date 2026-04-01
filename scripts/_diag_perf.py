import sys, os, time as _time
sys.path.insert(0, r"E:\quant-trading-mvp")
os.chdir(r"E:\quant-trading-mvp")

if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8')

import traceback
import psycopg2
import psycopg2.extras
from datetime import timedelta
from quant.common.config import config

DB_CONFIG = dict(
    host=config.database.host,
    port=config.database.port,
    dbname=config.database.database,
    user=config.database.user,
    password=config.database.password.get_secret_value(),
)

try:
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    # Check kline_data size
    cur.execute("SELECT COUNT(*) FROM kline_data")
    kline_count = cur.fetchone()[0]
    print(f"kline_data rows: {kline_count}")
    sys.stdout.flush()

    # Check index on kline_data
    cur.execute("""SELECT indexname, indexdef FROM pg_indexes WHERE tablename = 'kline_data'""")
    print("\nkline_data indexes:")
    for row in cur.fetchall():
        print(f"  {row[0]}: {row[1][:100]}")
    sys.stdout.flush()

    # Time a typical find_best_symbol query
    test_time = "2024-01-15 10:00:00+08:00"
    window_start = "2024-01-14 10:00:00+08:00"
    window_end = "2024-01-17 10:00:00+08:00"
    
    t0 = _time.time()
    cur.execute("""
        SELECT symbol, COUNT(*) as cnt
        FROM kline_data
        WHERE time >= %s AND time <= %s
          AND symbol IN ('au_continuous', 'au9999', 'au2606', 'au_main')
          AND interval = '30m'
        GROUP BY symbol
        ORDER BY cnt DESC
    """, (window_start, window_end))
    rows = cur.fetchall()
    t1 = _time.time()
    print(f"\nfind_best_symbol query took: {(t1-t0)*1000:.0f}ms, results: {len(rows)}")
    for r in rows:
        print(f"  {r[0]}: {r[1]}")
    sys.stdout.flush()

    # Time a typical find_price query 
    t0 = _time.time()
    cur.execute("""
        SELECT close, time FROM kline_data
        WHERE symbol = 'au_main' AND time <= %s AND interval = '30m'
        ORDER BY time DESC LIMIT 1
    """, (test_time,))
    row = cur.fetchone()
    t1 = _time.time()
    print(f"\nfind_price query took: {(t1-t0)*1000:.0f}ms, result: {row}")
    sys.stdout.flush()

    # Check if kline_data is a hypertable 
    cur.execute("""SELECT * FROM timescaledb_information.hypertables WHERE hypertable_name = 'kline_data'""")
    ht = cur.fetchone()
    print(f"\nkline_data is hypertable: {ht is not None}")
    sys.stdout.flush()

    # Count kline_data by year
    cur.execute("""SELECT date_trunc('year', time) as y, COUNT(*) FROM kline_data GROUP BY y ORDER BY y""")
    print("\nkline_data by year:")
    for row in cur.fetchall():
        print(f"  {row[0]}: {row[1]}")
    sys.stdout.flush()

    cur.close()
    conn.close()
    print("\n[diagnostic done]")

except Exception as e:
    print(f"EXCEPTION: {type(e).__name__}: {e}")
    traceback.print_exc()
    sys.stdout.flush()
