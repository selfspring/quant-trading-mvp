import psycopg2

conn = psycopg2.connect(
    host='localhost', port=5432,
    dbname='quant_trading', user='postgres',
    password='@Cmx1454697261'
)
cur = conn.cursor()
cur.execute("""
    SELECT COUNT(*), MIN(time), MAX(time)
    FROM kline_data
    WHERE symbol='au2606' AND interval='1m' AND time::date='2026-03-16'
""")
print('今日1分钟K线:', cur.fetchone())
conn.close()
