import psycopg2

conn = psycopg2.connect(host='localhost', port=5432, dbname='quant_trading', user='postgres', password='@Cmx1454697261')
cur = conn.cursor()
cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name='kline_data' ORDER BY ordinal_position")
for r in cur.fetchall():
    print(r)

# Check unique constraint
cur.execute("""
    SELECT conname, pg_get_constraintdef(c.oid) 
    FROM pg_constraint c 
    JOIN pg_class t ON c.conrelid = t.oid 
    WHERE t.relname = 'kline_data'
""")
print("\nConstraints:")
for r in cur.fetchall():
    print(r)

# Check existing data count
cur.execute("SELECT symbol, interval, COUNT(*) FROM kline_data GROUP BY symbol, interval ORDER BY symbol, interval")
print("\nExisting data:")
for r in cur.fetchall():
    print(r)

conn.close()
