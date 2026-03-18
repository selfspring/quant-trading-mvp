"""
生成模拟的历史 K 线数据并导入数据库
用于测试策略逻辑
"""
import psycopg2
from datetime import datetime, timedelta
import random
import numpy as np

# 数据库连接
conn = psycopg2.connect(
    dbname='quant_trading',
    user='postgres',
    password='@Cmx1454697261',
    host='localhost'
)
cur = conn.cursor()

# 生成 100 根 1 分钟 K 线（从现在往前推）
symbol = 'au2604'
interval = '1min'
base_price = 520.0  # 黄金期货基准价格
volatility = 0.5    # 波动率

print(f"生成 {symbol} 的历史 K 线数据...")

end_time = datetime.now()
start_time = end_time - timedelta(minutes=100)

klines = []
current_price = base_price

for i in range(100):
    timestamp = start_time + timedelta(minutes=i)
    
    # 模拟价格波动
    change = random.gauss(0, volatility)
    current_price += change
    
    open_price = current_price
    high_price = current_price + abs(random.gauss(0, volatility/2))
    low_price = current_price - abs(random.gauss(0, volatility/2))
    close_price = current_price + random.gauss(0, volatility/2)
    
    volume = random.randint(100, 1000)
    open_interest = random.randint(10000, 50000)
    
    klines.append((
        timestamp,
        symbol,
        interval,
        round(open_price, 2),
        round(high_price, 2),
        round(low_price, 2),
        round(close_price, 2),
        volume,
        open_interest
    ))
    
    current_price = close_price

# 插入数据库
print(f"插入 {len(klines)} 根 K 线到数据库...")

for kline in klines:
    cur.execute("""
        INSERT INTO kline_data (time, symbol, interval, open, high, low, close, volume, open_interest)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (time, symbol, interval) DO NOTHING
    """, kline)

conn.commit()

# 验证插入
cur.execute("""
    SELECT COUNT(*), MIN(time), MAX(time), AVG(close)
    FROM kline_data 
    WHERE symbol = %s AND interval = %s
""", (symbol, interval))

count, min_time, max_time, avg_close = cur.fetchone()

print(f"\n✓ 成功插入 {count} 根 K 线")
print(f"  时间范围: {min_time} ~ {max_time}")
print(f"  平均收盘价: {avg_close:.2f}")

# 显示最新 5 根
print(f"\n最新 5 根 K 线:")
cur.execute("""
    SELECT time, open, high, low, close, volume
    FROM kline_data
    WHERE symbol = %s AND interval = %s
    ORDER BY time DESC
    LIMIT 5
""", (symbol, interval))

for row in cur.fetchall():
    print(f"  {row[0]} | O:{row[1]} H:{row[2]} L:{row[3]} C:{row[4]} V:{row[5]}")

conn.close()
print("\n数据准备完成！现在可以运行策略了。")
