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
    SELECT DISTINCT symbol, interval, COUNT(*) as count
    FROM kline_data 
    GROUP BY symbol, interval
    ORDER BY symbol, interval
""")
symbols = cursor.fetchall()
print("Available symbols and intervals:")
for s in symbols:
    print(f"  {s[0]} - {s[1]} - {s[2]} records")

conn.close()
