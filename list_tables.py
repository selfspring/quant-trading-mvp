import psycopg2

conn = psycopg2.connect(
    host='localhost',
    port=5432,
    database='quant_trading',
    user='postgres',
    password='@Cmx1454697261'
)
cur = conn.cursor()

# 查看所有表
cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")
tables = [row[0] for row in cur.fetchall()]
print(f"数据库中的表 ({len(tables)} 个):")
for table in tables:
    print(f"  - {table}")

# 检查每个表的数据量
print("\n各表数据量:")
for table in tables:
    try:
        cur.execute(f'SELECT COUNT(*) FROM "{table}"')
        count = cur.fetchone()[0]
        print(f"  {table}: {count} 条")
    except Exception as e:
        print(f"  {table}: 查询失败 - {e}")

cur.close()
conn.close()
