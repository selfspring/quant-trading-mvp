"""
检查数据库中的数据状态
"""
import psycopg2
from datetime import datetime

conn = psycopg2.connect(
    host='localhost',
    port=5432,
    database='quant_trading',
    user='postgres',
    password='@Cmx1454697261'
)
cur = conn.cursor()

print("=" * 60)
print("数据库状态检查")
print("=" * 60)

# 检查 Tick 数据
cur.execute("""
    SELECT COUNT(*) as tick_count, 
           MIN(update_time) as earliest, 
           MAX(update_time) as latest 
    FROM market_data 
    WHERE instrument_id = 'au2606'
""")
result = cur.fetchone()
print(f'\n📊 Tick 数据统计:')
print(f'  数量: {result[0]:,} 条')
print(f'  最早: {result[1]}')
print(f'  最新: {result[2]}')

# 检查最近的数据
cur.execute("""
    SELECT update_time, last_price, volume
    FROM market_data 
    WHERE instrument_id = 'au2606'
    ORDER BY update_time DESC
    LIMIT 5
""")
recent = cur.fetchall()
print(f'\n📈 最近 5 条 Tick:')
for row in recent:
    print(f'  {row[0]} | 价格: {row[1]} | 成交量: {row[2]}')

# 检查是否有 K 线表
cur.execute("""
    SELECT table_name 
    FROM information_schema.tables 
    WHERE table_schema = 'public' 
    AND table_name LIKE '%kline%'
""")
kline_tables = cur.fetchall()
print(f'\n📊 K线表:')
if kline_tables:
    for table in kline_tables:
        print(f'  - {table[0]}')
else:
    print('  ❌ 未找到 K 线表')

cur.close()
conn.close()

print("\n" + "=" * 60)
