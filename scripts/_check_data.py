"""Quick check of available data for backtest."""
import psycopg2

conn = psycopg2.connect(
    host='localhost', port=5432, database='quant_trading',
    user='postgres', password='@Cmx1454697261'
)
cur = conn.cursor()

# news_analysis with 1d price data
cur.execute("SELECT COUNT(*) FROM news_analysis WHERE base_price IS NOT NULL AND price_change_1d IS NOT NULL")
print(f"news_analysis with 1d price: {cur.fetchone()[0]}")

cur.execute("SELECT COUNT(*) FROM news_analysis")
print(f"total news_analysis: {cur.fetchone()[0]}")

# columns
cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='news_analysis' ORDER BY ordinal_position")
print(f"news_analysis columns: {[r[0] for r in cur.fetchall()]}")

# sample rows
cur.execute("""
    SELECT id, news_id, direction, confidence, importance, base_price, 
           price_change_1d, correct_1d, created_at
    FROM news_analysis 
    WHERE base_price IS NOT NULL AND price_change_1d IS NOT NULL
    LIMIT 5
""")
rows = cur.fetchall()
print(f"\nSample rows with price data:")
for r in rows:
    print(f"  id={r[0]}, news_id={r[1]}, dir={r[2]}, conf={r[3]}, imp={r[4]}, base={r[5]}, pchange1d={r[6]}, correct={r[7]}, analyzed_at={r[8]}")

# kline_daily stats
cur.execute("SELECT COUNT(*), MIN(time), MAX(time) FROM kline_daily")
row = cur.fetchone()
print(f"\nkline_daily: count={row[0]}, min={row[1]}, max={row[2]}")

# technical_indicators
cur.execute("SELECT COUNT(*) FROM technical_indicators")
print(f"technical_indicators: {cur.fetchone()[0]}")

# Check technical_indicators columns
cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='technical_indicators' ORDER BY ordinal_position")
cols = [r[0] for r in cur.fetchall()]
print(f"technical_indicators columns: {cols}")

# Check if we have MA data in kline_daily or technical_indicators
if 'sma_20' in cols or 'ma_20' in cols:
    cur.execute("SELECT COUNT(*) FROM technical_indicators WHERE sma_20 IS NOT NULL OR ma_20 IS NOT NULL")
    print(f"tech indicators with MA: {cur.fetchone()[0]}")

# Sample technical indicator
cur.execute("SELECT * FROM technical_indicators LIMIT 3")
rows = cur.fetchall()
print(f"\nSample technical_indicators:")
for r in rows:
    print(f"  {r}")

# Check distinct directions in news_analysis
cur.execute("SELECT direction, COUNT(*) FROM news_analysis GROUP BY direction")
print(f"\nDirection distribution: {dict(cur.fetchall())}")

# Check confidence range
cur.execute("SELECT MIN(confidence), MAX(confidence), AVG(confidence) FROM news_analysis WHERE confidence IS NOT NULL")
r = cur.fetchone()
print(f"Confidence range: min={r[0]}, max={r[1]}, avg={r[2]:.3f}")

conn.close()
