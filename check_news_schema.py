import psycopg2
conn = psycopg2.connect(host='localhost', port=5432, database='quant_trading', user='postgres', password='@Cmx1454697261')
cur = conn.cursor()
cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'news_raw' ORDER BY ordinal_position")
print("news_raw 表结构:")
for row in cur.fetchall():
    print(f"  {row[0]}: {row[1]}")

cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'news_data' ORDER BY ordinal_position")
print("\nnews_data 表结构:")
for row in cur.fetchall():
    print(f"  {row[0]}: {row[1]}")
cur.close()
conn.close()
