import psycopg2
from datetime import datetime

conn = psycopg2.connect(
    dbname='quant_trading',
    user='postgres',
    password='@Cmx1454697261',
    host='localhost'
)
cur = conn.cursor()

# 先查看所有表
cur.execute("SELECT tablename FROM pg_tables WHERE schemaname='public'")
tables = cur.fetchall()
print("数据库中的表:")
for table in tables:
    print(f"  - {table[0]}")

# 查看 kline_data 表结构
cur.execute("""
    SELECT column_name, data_type 
    FROM information_schema.columns 
    WHERE table_name='kline_data'
""")
print("\nkline_data 表结构:")
for col in cur.fetchall():
    print(f"  {col[0]}: {col[1]}")

# 总记录数和时间范围
cur.execute("SELECT COUNT(*), MIN(time), MAX(time) FROM kline_data WHERE symbol='au2606'")
count, min_time, max_time = cur.fetchone()
print(f"总记录数: {count}")
print(f"时间范围: {min_time} ~ {max_time}")

# 最新10条
print("\n最新10条K线:")
cur.execute("""
    SELECT time, open, high, low, close, volume 
    FROM kline_data 
    WHERE symbol='au2606' 
    ORDER BY time DESC 
    LIMIT 10
""")
for row in cur.fetchall():
    print(f"{row[0]} | O:{row[1]} H:{row[2]} L:{row[3]} C:{row[4]} V:{row[5]}")

# 检查最近60条
cur.execute("""
    SELECT COUNT(*) 
    FROM kline_data 
    WHERE symbol='au2606' 
    AND time >= NOW() - INTERVAL '60 minutes'
""")
recent_count = cur.fetchone()[0]
print(f"\n最近60分钟内的K线数: {recent_count}")

conn.close()
