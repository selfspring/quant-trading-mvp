"""清除指定表的数据"""
import psycopg2

conn = psycopg2.connect(
    host='localhost', port=5432,
    dbname='quant_trading', user='postgres',
    password='@Cmx1454697261'
)
cur = conn.cursor()

tables = ['kline_daily', 'kline_data', 'macro_data', 'message_trace', 'news_raw']

for name in tables:
    cur.execute(f'DELETE FROM "{name}"')
    print(f'{name}: deleted {cur.rowcount} rows')

conn.commit()
conn.close()
print('Done.')
