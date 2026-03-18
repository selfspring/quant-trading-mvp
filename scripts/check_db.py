import sys
sys.path.insert(0, 'E:/quant-trading-mvp')
from quant.common.config import config
from quant.common.db import db_connection

with db_connection(config) as conn:
    cur = conn.cursor()

    cur.execute('SELECT symbol, interval, COUNT(*) FROM kline_data GROUP BY symbol, interval ORDER BY symbol, interval')
    for row in cur.fetchall():
        print(f'  {row[0]} {row[1]}: {row[2]} rows')

    cur.execute("SELECT MIN(time), MAX(time) FROM kline_data WHERE symbol='au2606' AND interval='30m'")
    r = cur.fetchone()
    print(f'\nau2606 30m range: {r[0]} ~ {r[1]}')
