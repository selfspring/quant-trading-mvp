import psycopg2

conn = psycopg2.connect(
    host='localhost', port=5432, database='quant_trading',
    user='postgres', password='@Cmx1454697261'
)
cur = conn.cursor()

# 查看所有事件类型
cur.execute("""
    SELECT event_type, COUNT(*), MIN(event_date), MAX(event_date)
    FROM macro_events
    GROUP BY event_type
    ORDER BY event_type
""")
print("=== macro_events 所有事件类型 ===")
for r in cur.fetchall():
    print(f"  {r[0]:20s}: {r[1]:4d} rows  ({r[2]} ~ {r[3]})")

# 查看表结构
cur.execute("""
    SELECT column_name, data_type, is_nullable
    FROM information_schema.columns
    WHERE table_name = 'macro_events'
    ORDER BY ordinal_position
""")
print("\n=== 表结构 ===")
for r in cur.fetchall():
    print(f"  {r[0]:25s} {r[1]:20s} nullable={r[2]}")

# 检查是否有 news/geopolitical 类型的表
cur.execute("""
    SELECT table_name FROM information_schema.tables
    WHERE table_schema = 'public'
    ORDER BY table_name
""")
print("\n=== 所有表 ===")
for r in cur.fetchall():
    print(f"  {r[0]}")

conn.close()
