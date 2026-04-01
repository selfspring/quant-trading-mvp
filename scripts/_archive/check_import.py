import psycopg2
conn = psycopg2.connect(host='localhost', port=5432, dbname='quant_trading', user='postgres', password='@Cmx1454697261')
cur = conn.cursor()

# Count by year for 1m
cur.execute("SELECT EXTRACT(year FROM time)::int as yr, COUNT(*) FROM kline_data WHERE symbol='au9999' AND interval='1m' GROUP BY yr ORDER BY yr")
rows = cur.fetchall()
print('=== 1m K lines by year ===')
for r in rows:
    print(f'  {r[0]}: {r[1]:,} rows')

cur.execute("SELECT COUNT(*) FROM kline_data WHERE symbol='au9999' AND interval='1m'")
print(f'Total 1m: {cur.fetchone()[0]:,}')

cur.execute("SELECT COUNT(*) FROM kline_data WHERE symbol='au9999' AND interval='15m'")
print(f'Total 15m: {cur.fetchone()[0]:,}')

cur.execute("SELECT COUNT(*) FROM kline_data WHERE symbol='au9999' AND interval='30m'")
print(f'Total 30m: {cur.fetchone()[0]:,}')

conn.close()
