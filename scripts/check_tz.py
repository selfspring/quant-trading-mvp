import psycopg2
conn = psycopg2.connect(host='localhost', port=5432, dbname='quant_trading', user='postgres', password='@Cmx1454697261')
cur = conn.cursor()
cur.execute("SELECT time, pg_typeof(time) FROM kline_data WHERE symbol='au2606' AND interval='1m' ORDER BY time DESC LIMIT 3")
for row in cur.fetchall():
    print(f'DB time: {row[0]}  type: {row[1]}')

# 测试聚合查询
from datetime import datetime, timedelta
now = datetime.now()
bar_30m_start = now.replace(minute=(now.minute // 30) * 30, second=0, microsecond=0)
bar_30m_end = bar_30m_start + timedelta(minutes=30)
print(f'\nQuery range: {bar_30m_start} ~ {bar_30m_end}')

cur.execute("""
    SELECT COUNT(*) FROM kline_data 
    WHERE symbol='au2606' AND interval='1m' AND time >= %s AND time < %s
""", (bar_30m_start, bar_30m_end))
print(f'Matching rows: {cur.fetchone()[0]}')

cur.close()
conn.close()
