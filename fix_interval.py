import psycopg2
conn = psycopg2.connect('dbname=quant_trading user=postgres password=@Cmx1454697261 host=localhost')
cur = conn.cursor()
cur.execute("UPDATE kline_data SET interval = '1m' WHERE interval = '1min'")
print(f"Updated {cur.rowcount} rows")
conn.commit()
conn.close()
