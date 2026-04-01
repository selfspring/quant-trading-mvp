import psycopg2

conn = psycopg2.connect(
    host='localhost', port=5432, database='quant_trading',
    user='postgres', password='@Cmx1454697261'
)
cur = conn.cursor()

# news_raw 覆盖情况
cur.execute("SELECT MIN(time), MAX(time), COUNT(*) FROM news_raw")
r = cur.fetchone()
print(f"=== news_raw ===")
print(f"  Total: {r[2]} rows")
print(f"  Range: {r[0]} ~ {r[1]}")

cur.execute("""
    SELECT source, COUNT(*), MIN(time), MAX(time)
    FROM news_raw
    GROUP BY source
    ORDER BY COUNT(*) DESC
""")
print(f"\n  By source:")
for r in cur.fetchall():
    print(f"    {r[0]:20s}: {r[1]:5d} rows  ({r[2]} ~ {r[3]})")

# 看几条样例
cur.execute("SELECT time, source, title FROM news_raw ORDER BY time DESC LIMIT 5")
print(f"\n  Latest 5:")
for r in cur.fetchall():
    print(f"    [{r[0]}] [{r[1]}] {r[2]}")

cur.execute("SELECT time, source, title FROM news_raw ORDER BY time LIMIT 5")
print(f"\n  Earliest 5:")
for r in cur.fetchall():
    print(f"    [{r[0]}] [{r[1]}] {r[2]}")

conn.close()
