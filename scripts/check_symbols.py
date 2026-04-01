import psycopg2

conn = psycopg2.connect(
    host='localhost', port=5432, database='quant_trading',
    user='postgres', password='@Cmx1454697261'
)
cur = conn.cursor()

# Check all symbols and their counts/ranges
cur.execute("""
    SELECT symbol, interval, COUNT(*), MIN(time), MAX(time)
    FROM kline_data
    GROUP BY symbol, interval
    ORDER BY symbol, interval
""")
print('Symbol/Interval breakdown:')
for r in cur.fetchall():
    print(f'  {r[0]:25s} | {r[1]:5s} | count={r[2]:>8d} | {r[3]} to {r[4]}')

# Total
cur.execute("SELECT COUNT(*) FROM kline_data")
print(f'\nTotal kline_data rows: {cur.fetchone()[0]}')

conn.close()
