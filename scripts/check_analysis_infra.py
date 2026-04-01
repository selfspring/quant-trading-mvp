import psycopg2

conn = psycopg2.connect(
    host='localhost', port=5432, database='quant_trading',
    user='postgres', password='@Cmx1454697261'
)
cur = conn.cursor()

# news_analysis 表结构
print("=== news_analysis ===")
cur.execute("""
    SELECT column_name, data_type
    FROM information_schema.columns
    WHERE table_name = 'news_analysis'
    ORDER BY ordinal_position
""")
for r in cur.fetchall():
    print(f"  {r[0]:25s} {r[1]}")
cur.execute("SELECT COUNT(*) FROM news_analysis")
print(f"  rows: {cur.fetchone()[0]}")

# news_data 表
print("\n=== news_data ===")
cur.execute("""
    SELECT column_name, data_type
    FROM information_schema.columns
    WHERE table_name = 'news_data'
    ORDER BY ordinal_position
""")
for r in cur.fetchall():
    print(f"  {r[0]:25s} {r[1]}")
cur.execute("SELECT COUNT(*) FROM news_data")
print(f"  rows: {cur.fetchone()[0]}")

# kline_daily 看看有什么数据
print("\n=== kline_daily ===")
cur.execute("""
    SELECT column_name, data_type
    FROM information_schema.columns
    WHERE table_name = 'kline_daily'
    ORDER BY ordinal_position
""")
for r in cur.fetchall():
    print(f"  {r[0]:25s} {r[1]}")
cur.execute("SELECT COUNT(*), MIN(open_time), MAX(open_time) FROM kline_daily")
r = cur.fetchone()
print(f"  rows: {r[0]}, range: {r[1]} ~ {r[2]}")

# trading_signals
print("\n=== trading_signals ===")
cur.execute("""
    SELECT column_name, data_type
    FROM information_schema.columns
    WHERE table_name = 'trading_signals'
    ORDER BY ordinal_position
""")
for r in cur.fetchall():
    print(f"  {r[0]:25s} {r[1]}")
cur.execute("SELECT COUNT(*) FROM trading_signals")
print(f"  rows: {cur.fetchone()[0]}")

# fused_signals
print("\n=== fused_signals ===")
cur.execute("""
    SELECT column_name, data_type
    FROM information_schema.columns
    WHERE table_name = 'fused_signals'
    ORDER BY ordinal_position
""")
for r in cur.fetchall():
    print(f"  {r[0]:25s} {r[1]}")
cur.execute("SELECT COUNT(*) FROM fused_signals")
print(f"  rows: {cur.fetchone()[0]}")

conn.close()
