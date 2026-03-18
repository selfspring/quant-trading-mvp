import psycopg2

conn = psycopg2.connect(
    dbname='quant_trading',
    user='postgres',
    password='@Cmx1454697261',
    host='localhost'
)
cur = conn.cursor()

# 检查 tick 数据
cur.execute("SELECT COUNT(*), MIN(time), MAX(time) FROM tick_data WHERE symbol='au2606'")
tick_count, tick_min, tick_max = cur.fetchone()
print(f"Tick数据总数: {tick_count}")
print(f"Tick时间范围: {tick_min} ~ {tick_max}")

if tick_count > 0:
    cur.execute("""
        SELECT time, last_price, volume 
        FROM tick_data 
        WHERE symbol='au2606' 
        ORDER BY time DESC 
        LIMIT 5
    """)
    print("\n最新5条Tick:")
    for row in cur.fetchall():
        print(f"  {row[0]} | 价格:{row[1]} 成交量:{row[2]}")

conn.close()
