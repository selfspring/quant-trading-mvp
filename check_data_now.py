import psycopg2

conn = psycopg2.connect(
    dbname='quant_trading',
    user='postgres',
    password='@Cmx1454697261',
    host='localhost'
)
cur = conn.cursor()

# 检查 au2604
cur.execute("SELECT COUNT(*) FROM tick_data WHERE symbol='au2604'")
tick_count = cur.fetchone()[0]

cur.execute("SELECT COUNT(*) FROM kline_data WHERE symbol='au2604'")
kline_count = cur.fetchone()[0]

print(f"au2604 Tick数据: {tick_count}")
print(f"au2604 K线数据: {kline_count}")

if tick_count > 0:
    cur.execute("""
        SELECT time, last_price, volume 
        FROM tick_data 
        WHERE symbol='au2604' 
        ORDER BY time DESC 
        LIMIT 5
    """)
    print("\n最新5条Tick:")
    for row in cur.fetchall():
        print(f"  {row[0]} | 价格:{row[1]} 成交量:{row[2]}")

if kline_count > 0:
    cur.execute("""
        SELECT time, open, high, low, close, volume 
        FROM kline_data 
        WHERE symbol='au2604' AND interval='1min'
        ORDER BY time DESC 
        LIMIT 5
    """)
    print("\n最新5条K线:")
    for row in cur.fetchall():
        print(f"  {row[0]} | O:{row[1]} H:{row[2]} L:{row[3]} C:{row[4]} V:{row[5]}")

conn.close()
