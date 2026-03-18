import psycopg2
import pandas as pd

conn = psycopg2.connect('dbname=quant_trading user=postgres password=@Cmx1454697261 host=localhost')

symbol = 'au2604'
db_interval = '1min'
count = 100

query = """
    SELECT time AS timestamp,
           open, high, low, close, volume
    FROM kline_data
    WHERE symbol = %s AND interval = %s
    ORDER BY time DESC
    LIMIT %s
"""

print(f"查询参数: symbol='{symbol}', interval='{db_interval}', count={count}")

df = pd.read_sql(query, conn, params=(symbol, db_interval, count))

print(f"\n查询结果: {len(df)} 行")
if not df.empty:
    print("\n前 5 行:")
    print(df.head())
else:
    print("DataFrame 为空！")

conn.close()
