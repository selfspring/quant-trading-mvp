import sys
sys.path.insert(0, 'E:/quant-trading-mvp')
from quant.common.config import config
from quant.common.db import db_connection

with db_connection(config) as conn:
    cur = conn.cursor()
    cur.execute("""
        SELECT COUNT(*), MIN(time), MAX(time)
        FROM kline_data
        WHERE symbol='au2606' AND interval='1m' AND time::date='2026-03-16'
    """)
    print('今日1分钟K线:', cur.fetchone())
