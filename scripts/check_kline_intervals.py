"""查看数据库中不同周期的 K 线"""
import psycopg2

conn = psycopg2.connect(
    host='localhost', port=5432,
    dbname='quant_trading', user='postgres',
    password='@Cmx1454697261'
)
cur = conn.cursor()

cur.execute("""
    SELECT symbol, interval, COUNT(*), MIN(time), MAX(time)
    FROM kline_data
    GROUP BY symbol, interval
    ORDER BY symbol, interval
""")

print("Symbol       Interval  Count   Time Range")
print("-" * 90)
for row in cur.fetchall():
    symbol, interval, count, min_t, max_t = row
    print(f"{symbol:12} {interval:8} {count:6}  {min_t} ~ {max_t}")

conn.close()
