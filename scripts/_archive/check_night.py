import sys
sys.path.insert(0, 'E:/quant-trading-mvp')
from quant.common.config import config
from quant.common.db import db_connection

with db_connection(config) as conn:
    cur = conn.cursor()

    # 今晚采集的数据
    cur.execute("SELECT COUNT(*) FROM kline_data WHERE symbol='au2606' AND interval='1m' AND time >= '2026-03-17 21:00:00+08'")
    print(f"今晚 1m K线数: {cur.fetchone()[0]}")

    cur.execute("SELECT MIN(time), MAX(time) FROM kline_data WHERE symbol='au2606' AND interval='1m' AND time >= '2026-03-17 21:00:00+08'")
    row = cur.fetchone()
    print(f"时间范围: {row[0]} ~ {row[1]}")

    # 最新5根
    cur.execute("SELECT time, open, high, low, close, volume FROM kline_data WHERE symbol='au2606' AND interval='1m' ORDER BY time DESC LIMIT 5")
    print("\n最新5根 1m K线:")
    for r in cur.fetchall():
        print(f"  {r[0]}  O:{r[1]:.2f} H:{r[2]:.2f} L:{r[3]:.2f} C:{r[4]:.2f} V:{r[5]}")

    # 30m 数据
    cur.execute("SELECT COUNT(*) FROM kline_data WHERE symbol='au2606' AND interval='30m'")
    print(f"\nau2606 30m K线总数: {cur.fetchone()[0]}")

    cur.close()
