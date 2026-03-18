"""检查 kline_data 表结构"""
import psycopg2

conn = psycopg2.connect(
    host='localhost', port=5432,
    dbname='quant_trading', user='postgres',
    password='@Cmx1454697261'
)
cur = conn.cursor()

# 查看表结构
cur.execute("""
    SELECT column_name, data_type, is_nullable
    FROM information_schema.columns
    WHERE table_name = 'kline_data'
    ORDER BY ordinal_position
""")
print("kline_data 表结构:")
for row in cur.fetchall():
    print(f"  {row[0]}: {row[1]} (nullable: {row[2]})")

# 查看约束
cur.execute("""
    SELECT conname, contype, pg_get_constraintdef(oid)
    FROM pg_constraint
    WHERE conrelid = 'kline_data'::regclass
""")
print("\n约束:")
for row in cur.fetchall():
    print(f"  {row[0]}: {row[2]}")

# 查看 tick_data 表
cur.execute("""
    SELECT column_name, data_type
    FROM information_schema.columns
    WHERE table_name = 'tick_data'
    ORDER BY ordinal_position
""")
print("\ntick_data 表结构:")
for row in cur.fetchall():
    print(f"  {row[0]}: {row[1]}")

cur.execute("SELECT COUNT(*) FROM tick_data")
print(f"\ntick_data 行数: {cur.fetchone()[0]}")

conn.close()
