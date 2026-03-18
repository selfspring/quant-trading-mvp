import sys
sys.path.insert(0, 'E:/quant-trading-mvp')
from quant.common.config import config
from quant.common.db import db_connection

with db_connection(config) as conn:
    cur = conn.cursor()

    # Check what symbols and intervals exist
    cur.execute("SELECT symbol, interval, COUNT(*), MIN(time), MAX(time) FROM kline_data GROUP BY symbol, interval ORDER BY symbol, interval")
    rows = cur.fetchall()
    for r in rows:
        print(f"symbol={r[0]} interval={r[1]} count={r[2]} from={r[3]} to={r[4]}")

    if not rows:
        print("NO_DATA_IN_TABLE")
        # Check if table exists and has any rows
        cur.execute("SELECT COUNT(*) FROM kline_data")
        print("Total rows:", cur.fetchone()[0])
