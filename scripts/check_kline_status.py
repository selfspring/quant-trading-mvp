import psycopg2

conn = psycopg2.connect(
    host='localhost', port=5432, database='quant_trading',
    user='postgres', password='@Cmx1454697261'
)
cur = conn.cursor()

cur.execute('SELECT COUNT(*) FROM kline_daily')
print('kline_daily count:', cur.fetchone()[0])

cur.execute("SELECT COUNT(*) FROM kline_data WHERE symbol='au_continuous'")
print('kline_data au_continuous count:', cur.fetchone()[0])

cur.execute("SELECT MIN(time), MAX(time) FROM kline_data WHERE symbol='au_continuous'")
row = cur.fetchone()
print('au_continuous time range:', row[0], 'to', row[1])

# Check columns of kline_data
cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name='kline_data' ORDER BY ordinal_position")
print('\nkline_data columns:')
for r in cur.fetchall():
    print(f'  {r[0]}: {r[1]}')

# Check columns of kline_daily
cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name='kline_daily' ORDER BY ordinal_position")
print('\nkline_daily columns:')
for r in cur.fetchall():
    print(f'  {r[0]}: {r[1]}')

# Sample from kline_data
cur.execute("SELECT * FROM kline_data WHERE symbol='au_continuous' ORDER BY time LIMIT 3")
print('\nSample kline_data rows:')
for r in cur.fetchall():
    print(f'  {r}')

conn.close()
