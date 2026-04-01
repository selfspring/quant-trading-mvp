import psycopg2

conn = psycopg2.connect(
    host='localhost',
    port=5432,
    dbname='quant_trading',
    user='postgres',
    password='@Cmx1454697261'
)

cursor = conn.cursor()
cursor.execute("""
    SELECT COUNT(*) 
    FROM kline_data 
    WHERE symbol='au2606' AND interval='30m'
""")
count = cursor.fetchone()[0]
print(f"Total records: {count}")

cursor.execute("""
    SELECT time, close 
    FROM kline_data 
    WHERE symbol='au2606' AND interval='30m' 
    ORDER BY time DESC 
    LIMIT 10
""")
recent = cursor.fetchall()
print("\nRecent 10 records:")
for r in recent:
    print(f"  {r[0]} - {r[1]}")

conn.close()
