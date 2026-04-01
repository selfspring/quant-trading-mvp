"""查看交易记录和K线数据"""
import sys
sys.path.insert(0, 'E:/quant-trading-mvp')
from quant.common.config import config
from quant.common.db import db_connection

with db_connection(config) as conn:
    cur = conn.cursor()

    # 查看 kline_data
    cur.execute("SELECT COUNT(*) FROM kline_data")
    print(f"kline_data: {cur.fetchone()[0]} rows")

    cur.execute("SELECT time, symbol, open, high, low, close, volume FROM kline_data ORDER BY time DESC LIMIT 5")
    rows = cur.fetchall()
    if rows:
        print("\n最近5根K线:")
        for r in rows:
            print(f"  {r[0]} | {r[1]} | O:{r[2]} H:{r[3]} L:{r[4]} C:{r[5]} V:{r[6]}")

    # 查看 orders
    cur.execute("SELECT COUNT(*) FROM orders")
    print(f"\norders: {cur.fetchone()[0]} rows")

    cur.execute("SELECT * FROM orders ORDER BY 1 DESC LIMIT 5")
    rows = cur.fetchall()
    if rows:
        print("\n最近5笔订单:")
        for r in rows:
            print(f"  {r}")

    # 查看 trades
    cur.execute("SELECT COUNT(*) FROM trades")
    print(f"\ntrades: {cur.fetchone()[0]} rows")

    cur.execute("SELECT * FROM trades ORDER BY 1 DESC LIMIT 5")
    rows = cur.fetchall()
    if rows:
        print("\n最近5笔成交:")
        for r in rows:
            print(f"  {r}")

    # 查看 trading_signals
    cur.execute("SELECT COUNT(*) FROM trading_signals")
    print(f"\ntrading_signals: {cur.fetchone()[0]} rows")

    # 查看 ml_predictions
    cur.execute("SELECT COUNT(*) FROM ml_predictions")
    print(f"ml_predictions: {cur.fetchone()[0]} rows")
