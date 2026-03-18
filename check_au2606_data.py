# -*- coding: utf-8 -*-
import pandas as pd
import psycopg2

# 连接数据库
conn = psycopg2.connect(
    host='localhost',
    port=5432,
    dbname='quant_trading',
    user='postgres',
    password='@Cmx1454697261'
)

# 检查 au2606 数据情况
query = """
SELECT symbol, interval, COUNT(*) as count, MIN(time) as earliest, MAX(time) as latest
FROM kline_data
WHERE symbol='au2606'
GROUP BY symbol, interval
ORDER BY interval
"""

df = pd.read_sql(query, conn)
print("=== au2606 数据统计 ===")
print(df)

# 获取最新的数据
query2 = """
SELECT time as timestamp, open, high, low, close, volume, COALESCE(open_interest, 0) as open_interest
FROM kline_data
WHERE symbol='au2606' AND interval='30m'
ORDER BY time DESC
LIMIT 10
"""

df2 = pd.read_sql(query2, conn)
print("\n=== 最新10条30m数据 ===")
print(df2)

conn.close()
