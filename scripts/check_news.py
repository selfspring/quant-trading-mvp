import psycopg2

conn = psycopg2.connect(
    host='localhost', port=5432, database='quant_trading',
    user='postgres', password='@Cmx1454697261'
)
cur = conn.cursor()

# 查看 GEO 事件详情
print("=== GEO events (25 rows) ===")
cur.execute("SELECT event_date, importance, description FROM macro_events WHERE event_type='GEO' ORDER BY event_date")
for r in cur.fetchall():
    print(f"  {r[0]}  [{r[1]}]  {r[2]}")

# 查看 news_data 表结构和数量
print("\n=== news_data 表结构 ===")
cur.execute("""
    SELECT column_name, data_type
    FROM information_schema.columns
    WHERE table_name = 'news_data'
    ORDER BY ordinal_position
""")
for r in cur.fetchall():
    print(f"  {r[0]:25s} {r[1]}")

cur.execute("SELECT COUNT(*) FROM news_data")
print(f"\nnews_data rows: {cur.fetchone()[0]}")

# 查看 news_raw
print("\n=== news_raw 表结构 ===")
cur.execute("""
    SELECT column_name, data_type
    FROM information_schema.columns
    WHERE table_name = 'news_raw'
    ORDER BY ordinal_position
""")
for r in cur.fetchall():
    print(f"  {r[0]:25s} {r[1]}")

cur.execute("SELECT COUNT(*) FROM news_raw")
print(f"\nnews_raw rows: {cur.fetchone()[0]}")

conn.close()
