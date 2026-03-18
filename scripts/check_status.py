import sys
sys.path.insert(0, 'E:/quant-trading-mvp')
from datetime import date
from quant.common.config import config
from quant.common.db import db_connection

with db_connection(config) as conn:
    cur = conn.cursor()

    # 1m klines total
    cur.execute("SELECT COUNT(*), MIN(datetime), MAX(datetime) FROM kline_1m WHERE instrument_id LIKE '%au%'")
    print("1m klines:", cur.fetchone())

    # 30m klines total
    cur.execute("SELECT COUNT(*), MIN(datetime), MAX(datetime) FROM kline_30m WHERE instrument_id LIKE '%au%'")
    print("30m klines:", cur.fetchone())

    # today's 1m klines
    cur.execute("SELECT COUNT(*) FROM kline_1m WHERE datetime::date = CURRENT_DATE")
    print("Today 1m:", cur.fetchone())

    # today's 30m klines
    cur.execute("SELECT COUNT(*) FROM kline_30m WHERE datetime::date = CURRENT_DATE")
    print("Today 30m:", cur.fetchone())

    # recent trades
    cur.execute("SELECT * FROM trades ORDER BY trade_time DESC LIMIT 5")
    cols = [d[0] for d in cur.description] if cur.description else []
    rows = cur.fetchall()
    print("\nRecent trades:", cols)
    for r in rows:
        print(r)

    # list all tables
    cur.execute("SELECT tablename FROM pg_tables WHERE schemaname='public'")
    print("\nTables:", [r[0] for r in cur.fetchall()])
