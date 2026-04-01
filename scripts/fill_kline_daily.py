"""
Fill kline_daily from kline_data by aggregating minute-level data to daily OHLCV.

Strategy:
- au9999 1m data covers 2008-01 to 2025-04 → aggregate to daily
- au_continuous 1m data covers 2025-03 to 2026-03 → aggregate to daily
- Combine both, using au_continuous data where dates overlap
- Store all rows with symbol='au_continuous' in kline_daily
"""
import psycopg2
import sys
import io

# Encoding safety for Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

DB_PARAMS = dict(
    host='localhost', port=5432, database='quant_trading',
    user='postgres', password='@Cmx1454697261'
)

def main():
    conn = psycopg2.connect(**DB_PARAMS)
    conn.autocommit = False
    cur = conn.cursor()

    # Step 1: Clear existing data (idempotent)
    cur.execute("DELETE FROM kline_daily")
    print(f"Cleared kline_daily: {cur.rowcount} rows deleted")

    # Step 2: Aggregate au9999 1m data into daily bars
    # For OHLCV daily aggregation from 1m candles:
    #   open = first candle's open (by time)
    #   high = max high
    #   low = min low
    #   close = last candle's close (by time)
    #   volume = sum volume
    #   open_interest = last candle's open_interest
    # Shanghai gold futures trade: day session 9:00-15:00, night session 21:00-02:30
    # A trading day includes the previous night session + current day session.
    # For simplicity, we use calendar date (in Asia/Shanghai timezone) to group.

    print("\nAggregating au9999 1m data (2008-2025)...")
    cur.execute("""
        INSERT INTO kline_daily (time, symbol, open, high, low, close, volume, open_interest)
        SELECT
            (time AT TIME ZONE 'Asia/Shanghai')::date AS trade_date,
            'au_continuous' AS symbol,
            (array_agg(open ORDER BY time))[1]::float8 AS open,
            MAX(high)::float8 AS high,
            MIN(low)::float8 AS low,
            (array_agg(close ORDER BY time DESC))[1]::float8 AS close,
            SUM(volume) AS volume,
            (array_agg(open_interest ORDER BY time DESC))[1] AS open_interest
        FROM kline_data
        WHERE symbol = 'au9999' AND interval = '1m'
        GROUP BY trade_date
        ORDER BY trade_date
    """)
    au9999_count = cur.rowcount
    print(f"  Inserted {au9999_count} daily rows from au9999")

    # Step 3: Aggregate au_continuous 1m data into daily bars
    print("\nAggregating au_continuous 1m data (2025-2026)...")
    # Use ON CONFLICT to overwrite au9999 data where au_continuous has data
    # First need a unique constraint or use a temp approach
    # Since kline_daily may not have a unique constraint, let's delete overlapping dates first

    cur.execute("""
        SELECT MIN((time AT TIME ZONE 'Asia/Shanghai')::date),
               MAX((time AT TIME ZONE 'Asia/Shanghai')::date)
        FROM kline_data
        WHERE symbol = 'au_continuous' AND interval = '1m'
    """)
    cont_min, cont_max = cur.fetchone()
    print(f"  au_continuous date range: {cont_min} to {cont_max}")

    # Delete overlapping dates from au9999 aggregation
    cur.execute("""
        DELETE FROM kline_daily
        WHERE time >= %s AND time <= %s
    """, (cont_min, cont_max))
    print(f"  Deleted {cur.rowcount} overlapping rows")

    # Insert au_continuous daily bars
    cur.execute("""
        INSERT INTO kline_daily (time, symbol, open, high, low, close, volume, open_interest)
        SELECT
            (time AT TIME ZONE 'Asia/Shanghai')::date AS trade_date,
            'au_continuous' AS symbol,
            (array_agg(open ORDER BY time))[1]::float8 AS open,
            MAX(high)::float8 AS high,
            MIN(low)::float8 AS low,
            (array_agg(close ORDER BY time DESC))[1]::float8 AS close,
            SUM(volume) AS volume,
            (array_agg(open_interest ORDER BY time DESC))[1] AS open_interest
        FROM kline_data
        WHERE symbol = 'au_continuous' AND interval = '1m'
        GROUP BY trade_date
        ORDER BY trade_date
    """)
    cont_count = cur.rowcount
    print(f"  Inserted {cont_count} daily rows from au_continuous")

    conn.commit()

    # Step 4: Verify
    print("\n=== Verification ===")
    cur.execute("SELECT COUNT(*), MIN(time), MAX(time) FROM kline_daily")
    count, min_t, max_t = cur.fetchone()
    print(f"Total rows: {count}")
    print(f"Date range: {min_t} to {max_t}")

    # Check for large gaps (>5 calendar days excluding weekends/holidays)
    cur.execute("""
        SELECT time, next_time, (next_time - time) AS gap_days
        FROM (
            SELECT time, LEAD(time) OVER (ORDER BY time) AS next_time
            FROM kline_daily
        ) t
        WHERE (next_time - time) > 7
        ORDER BY gap_days DESC
        LIMIT 10
    """)
    gaps = cur.fetchall()
    if gaps:
        print(f"\nLargest gaps (> 7 days):")
        for g in gaps:
            print(f"  {g[0]} -> {g[1]} ({g[2]} days)")
    else:
        print("\nNo gaps > 7 days found")

    # Sample rows
    cur.execute("SELECT * FROM kline_daily ORDER BY time LIMIT 3")
    print("\nFirst 3 rows:")
    for r in cur.fetchall():
        print(f"  {r}")

    cur.execute("SELECT * FROM kline_daily ORDER BY time DESC LIMIT 3")
    print("\nLast 3 rows:")
    for r in cur.fetchall():
        print(f"  {r}")

    # Yearly distribution
    cur.execute("""
        SELECT EXTRACT(YEAR FROM time)::int AS yr, COUNT(*)
        FROM kline_daily
        GROUP BY yr
        ORDER BY yr
    """)
    print("\nYearly distribution:")
    for r in cur.fetchall():
        print(f"  {r[0]}: {r[1]} days")

    conn.close()
    print("\nDone!")

if __name__ == '__main__':
    main()
