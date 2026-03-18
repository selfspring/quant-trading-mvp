import sys
sys.path.insert(0, 'E:\\quant-trading-mvp')

from quant.common.db_pool import get_db_connection

with get_db_connection() as conn:
    cur = conn.cursor()
    
    # 检查 au2606 K线数量
    cur.execute("SELECT COUNT(*) FROM kline_data WHERE symbol='au2606'")
    count = cur.fetchone()[0]
    print(f"au2606 K线总数: {count}")
    
    # 检查最新5条
    cur.execute("SELECT time, interval, open, high, low, close, volume FROM kline_data WHERE symbol='au2606' ORDER BY time DESC LIMIT 5")
    print("\n最新5条K线:")
    for row in cur.fetchall():
        print(row)
    
    # 检查所有合约
    cur.execute("SELECT symbol, COUNT(*) as cnt FROM kline_data GROUP BY symbol")
    print("\n所有合约统计:")
    for row in cur.fetchall():
        print(row)
