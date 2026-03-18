import sys
sys.stdout.reconfigure(encoding='utf-8')
import psycopg2

conn = psycopg2.connect(host='localhost', port=5432, dbname='quant_trading', user='postgres', password='@Cmx1454697261')
cur = conn.cursor()
cur.execute("SELECT symbol, interval, COUNT(*), MAX(time) FROM kline_data GROUP BY symbol, interval ORDER BY symbol, interval")
rows = cur.fetchall()
for r in rows:
    print(r)
conn.close()
