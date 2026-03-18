"""查看数据库所有表和数据量"""
import psycopg2

conn = psycopg2.connect(
    host='localhost', port=5432,
    dbname='quant_trading', user='postgres',
    password='@Cmx1454697261'
)
cur = conn.cursor()

cur.execute("""
    SELECT table_name FROM information_schema.tables 
    WHERE table_schema = 'public' ORDER BY table_name
""")
tables = cur.fetchall()

for t in tables:
    name = t[0]
    cur.execute(f'SELECT COUNT(*) FROM "{name}"')
    count = cur.fetchone()[0]
    print(f'{name}: {count} rows')

conn.close()
