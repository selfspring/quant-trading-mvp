import psycopg2

conn = psycopg2.connect(
    host='localhost', port=5432, database='quant_trading',
    user='postgres', password='@Cmx1454697261'
)
cur = conn.cursor()

# kline_daily
print("=== kline_daily ===")
cur.execute("SELECT COUNT(*), MIN(time), MAX(time) FROM kline_daily")
r = cur.fetchone()
print(f"  rows: {r[0]}, range: {r[1]} ~ {r[2]}")
cur.execute("SELECT DISTINCT symbol FROM kline_daily")
print(f"  symbols: {[r[0] for r in cur.fetchall()]}")

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

# news_analysis 样例
print("\n=== news_analysis 样例 (latest 3) ===")
cur.execute("""
    SELECT na.time, na.importance, na.direction, na.confidence, na.reasoning,
           nr.title
    FROM news_analysis na
    LEFT JOIN news_raw nr ON na.news_id = nr.id
    ORDER BY na.time DESC LIMIT 3
""")
for r in cur.fetchall():
    print(f"  [{r[0]}] {r[5]}")
    print(f"    importance={r[1]} direction={r[2]} confidence={r[3]}")
    print(f"    reasoning: {str(r[4])[:100]}...")

# 现有项目中的 news 相关脚本
print("\n=== news 相关脚本 ===")

conn.close()
