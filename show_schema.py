import psycopg2

conn = psycopg2.connect(
    host='localhost',
    port=5432,
    database='quant_trading',
    user='postgres',
    password='@Cmx1454697261'
)
cur = conn.cursor()

tables = ['kline_data', 'kline_daily', 'macro_data', 'message_trace']

for table in tables:
    print(f"\n{'='*60}")
    print(f"表结构: {table}")
    print('='*60)
    cur.execute(f"""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = '{table}'
        ORDER BY ordinal_position
    """)
    for row in cur.fetchall():
        print(f"  {row[0]}: {row[1]}")

cur.close()
conn.close()
