"""Temporary script to audit news_analysis schema."""
import psycopg2

conn = psycopg2.connect(
    host='localhost', port=5432,
    dbname='quant_trading', user='postgres', password='@Cmx1454697261'
)
cur = conn.cursor()

print("=== news_analysis columns ===")
cur.execute("""
    SELECT column_name, data_type, is_nullable, column_default
    FROM information_schema.columns
    WHERE table_name='news_analysis'
    ORDER BY ordinal_position
""")
for r in cur.fetchall():
    print(r)

print("\n=== news_verification table exists? ===")
cur.execute("""
    SELECT EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_name='news_verification'
    )
""")
print(cur.fetchone()[0])

print("\n=== news_verification columns (if exists) ===")
cur.execute("""
    SELECT column_name, data_type, is_nullable, column_default
    FROM information_schema.columns
    WHERE table_name='news_verification'
    ORDER BY ordinal_position
""")
rows = cur.fetchall()
if rows:
    for r in rows:
        print(r)
else:
    print("(table does not exist or has no columns)")

conn.close()
