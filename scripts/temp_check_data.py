import sys
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'E:/quant-trading-mvp')
from quant.common.config import config
from quant.common.db import db_connection

with db_connection(config) as conn:
    cur = conn.cursor()
    cur.execute("SELECT symbol, interval, COUNT(*), MAX(time) FROM kline_data GROUP BY symbol, interval ORDER BY symbol, interval")
    rows = cur.fetchall()
    for r in rows:
        print(r)
