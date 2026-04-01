import psycopg2
import pandas as pd

conn = psycopg2.connect(host='localhost', port=5432, dbname='quant_trading', user='postgres', password='@Cmx1454697261')
cur = conn.cursor()

print('=== kline_data 数据总览 ===')
cur.execute("""
    SELECT symbol, interval, 
           COUNT(*) as cnt,
           MIN(time) as first_time,
           MAX(time) as last_time
    FROM kline_data
    GROUP BY symbol, interval
    ORDER BY symbol, interval
""")
for r in cur.fetchall():
    print(f'  {r[0]} {r[1]}: {r[2]:,} rows | {r[3]} ~ {r[4]}')

print()
print('=== au9999 1m 按年统计 ===')
cur.execute("""
    SELECT EXTRACT(year FROM time)::int as yr, COUNT(*) as cnt
    FROM kline_data WHERE symbol='au9999' AND interval='1m'
    GROUP BY yr ORDER BY yr
""")
for r in cur.fetchall():
    print(f'  {r[0]}: {r[1]:,}')

print()
print('=== au9999 15m 按年统计 ===')
cur.execute("""
    SELECT EXTRACT(year FROM time)::int as yr, COUNT(*) as cnt
    FROM kline_data WHERE symbol='au9999' AND interval='15m'
    GROUP BY yr ORDER BY yr
""")
for r in cur.fetchall():
    print(f'  {r[0]}: {r[1]:,}')

print()
print('=== au2606 数据 ===')
cur.execute("""
    SELECT symbol, interval, COUNT(*) as cnt, MIN(time), MAX(time)
    FROM kline_data WHERE symbol='au2606'
    GROUP BY symbol, interval ORDER BY interval
""")
for r in cur.fetchall():
    print(f'  {r[0]} {r[1]}: {r[2]:,} rows | {r[3]} ~ {r[4]}')

print()
print('=== 所有 1m 数据缺口检测（au9999，按月） ===')
cur.execute("""
    SELECT 
        EXTRACT(year FROM time)::int as yr,
        EXTRACT(month FROM time)::int as mo,
        COUNT(*) as cnt
    FROM kline_data 
    WHERE symbol='au9999' AND interval='1m'
    GROUP BY yr, mo
    ORDER BY yr, mo
""")
rows = cur.fetchall()
for r in rows:
    # 黄金期货每月交易日约20天，每天约270分钟（含夜盘）
    status = '  OK' if r[2] > 3000 else ' LOW'
    print(f'  {status} {r[0]}-{r[1]:02d}: {r[2]:,}')

conn.close()
