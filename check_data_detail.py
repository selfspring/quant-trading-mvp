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
print("1. kline_data (200 条 - 1分钟K线)")
print("=" * 60)
cur.execute("""
    SELECT time, symbol, interval, open, high, low, close, volume 
    FROM kline_data 
    ORDER BY time DESC 
    LIMIT 5
""")
for row in cur.fetchall():
    print(f"  {row[0]} | {row[1]} | {row[2]} | O:{row[3]:.2f} H:{row[4]:.2f} L:{row[5]:.2f} C:{row[6]:.2f} V:{row[7]}")

cur.execute("SELECT MIN(time), MAX(time) FROM kline_data")
time_range = cur.fetchone()
print(f"\n  时间范围: {time_range[0]} ~ {time_range[1]}")

cur.execute("SELECT symbol, COUNT(*) FROM kline_data GROUP BY symbol")
print("\n  各品种数据量:")
for row in cur.fetchall():
    print(f"    {row[0]}: {row[1]} 条")

print("\n" + "=" * 60)
print("2. kline_daily (2235 条 - 日K线)")
print("=" * 60)
cur.execute("""
    SELECT time, symbol, open, high, low, close, volume 
    FROM kline_daily 
    ORDER BY time DESC 
    LIMIT 5
""")
for row in cur.fetchall():
    print(f"  {row[0]} | {row[1]} | O:{row[2]:.2f} H:{row[3]:.2f} L:{row[4]:.2f} C:{row[5]:.2f} V:{row[6]}")

cur.execute("SELECT MIN(time), MAX(time) FROM kline_daily")
time_range = cur.fetchone()
print(f"\n  时间范围: {time_range[0]} ~ {time_range[1]}")

cur.execute("SELECT symbol, COUNT(*) FROM kline_daily GROUP BY symbol")
print("\n  各品种数据量:")
for row in cur.fetchall():
    print(f"    {row[0]}: {row[1]} 条")

print("\n" + "=" * 60)
print("3. macro_data (48 条 - 宏观数据)")
print("=" * 60)
cur.execute("""
    SELECT time, indicator, value, unit, source 
    FROM macro_data 
    ORDER BY time DESC 
    LIMIT 10
""")
for row in cur.fetchall():
    print(f"  {row[0]} | {row[1]} | {row[2]} {row[3]} | {row[4]}")

print("\n" + "=" * 60)
print("4. message_trace (34 条 - 消息追踪)")
print("=" * 60)
cur.execute("""
    SELECT timestamp, process_name, event_type, status 
    FROM message_trace 
    ORDER BY timestamp DESC 
    LIMIT 10
""")
for row in cur.fetchall():
    print(f"  {row[0]} | {row[1]} | {row[2]} | {row[3]}")

cur.close()
conn.close()
