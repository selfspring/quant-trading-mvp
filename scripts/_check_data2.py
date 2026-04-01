"""Get all backtest-eligible rows."""
import psycopg2

conn = psycopg2.connect(
    host='localhost', port=5432, database='quant_trading',
    user='postgres', password='@Cmx1454697261'
)
cur = conn.cursor()

cur.execute("""
    SELECT na.id, na.news_id, na.time, na.direction, na.confidence, na.importance,
           na.base_price, na.price_change_1d, na.correct_1d
    FROM news_analysis na
    WHERE na.base_price IS NOT NULL AND na.price_change_1d IS NOT NULL
    ORDER BY na.time
""")
rows = cur.fetchall()
print(f"Total backtest-eligible rows: {len(rows)}")
for r in rows:
    print(f"  id={r[0]}, nid={r[1]}, time={r[2]}, dir={r[3]}, conf={r[4]:.2f}, imp={r[5]}, base={r[6]:.2f}, pct_1d={r[7]:.4f}%, correct={r[8]}")

# Direction distribution
cur.execute("""
    SELECT direction, COUNT(*) FROM news_analysis 
    WHERE base_price IS NOT NULL AND price_change_1d IS NOT NULL
    GROUP BY direction
""")
print(f"\nDirection distribution (backtest set): {dict(cur.fetchall())}")

# Also check rows with price_change_30m and price_change_4h
cur.execute("SELECT COUNT(*) FROM news_analysis WHERE base_price IS NOT NULL AND price_change_30m IS NOT NULL")
print(f"\nRows with 30m price: {cur.fetchone()[0]}")
cur.execute("SELECT COUNT(*) FROM news_analysis WHERE base_price IS NOT NULL AND price_change_4h IS NOT NULL")
print(f"Rows with 4h price: {cur.fetchone()[0]}")

# Get the time range of news with price data so we know what daily data we need
cur.execute("""
    SELECT MIN(time), MAX(time) FROM news_analysis
    WHERE base_price IS NOT NULL AND price_change_1d IS NOT NULL
""")
r = cur.fetchone()
print(f"\nTime range of backtest data: {r[0]} to {r[1]}")

conn.close()
