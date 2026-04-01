# -*- coding: utf-8 -*-
import psycopg2

conn = psycopg2.connect(
    host='localhost',
    port=5432,
    dbname='quant_trading',
    user='postgres',
    password='@Cmx1454697261'
)

cur = conn.cursor()

# 检查 au_main 有哪些 interval 和数据量
cur.execute("SELECT DISTINCT interval FROM kline_data WHERE symbol='au_main' ORDER BY interval")
intervals = cur.fetchall()
print('au_main intervals:', [i[0] for i in intervals])

for interval in intervals:
    cur.execute("SELECT COUNT(*) FROM kline_data WHERE symbol='au_main' AND interval=%s", (interval[0],))
    count = cur.fetchone()[0]
    cur.execute("SELECT MIN(time), MAX(time) FROM kline_data WHERE symbol='au_main' AND interval=%s", (interval[0],))
    time_range = cur.fetchone()
    print(f'  {interval[0]}: {count} rows, {time_range}')

conn.close()
