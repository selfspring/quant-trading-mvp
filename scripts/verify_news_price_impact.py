#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/verify_news_price_impact.py

For each news_analysis record:
1. Choose a verification anchor time
2. Find nearest kline price as base_price (using consistent symbol)
3. Get +30m, +4h, +1d prices from the SAME symbol
4. Calculate price_change_30m/4h/1d (percentage)
5. Compare LLM direction prediction with actual price changes
6. Write verification results to `news_verification`
7. During transition, also double-write legacy verification fields on `news_analysis`
8. Print accuracy statistics

Key design:
- Default verification anchor is `effective_time`
- Explicit research contrast anchor `published_time` is still supported
- `news_analysis.time` is treated as legacy ambiguous field and is not used as a new default anchor
- Default write path is `news_verification`; legacy `news_analysis` fields are short-term compatibility only
- Uses a consistent symbol per record to avoid cross-contract price jumps
- Prioritizes symbols by time coverage overlap with the anchor time
- For +1d, falls back to kline_daily if minute data unavailable

Usage:
    python scripts/verify_news_price_impact.py [--dry-run] [--anchor-time effective_time|published_time]
"""
import argparse
import sys
from datetime import timedelta
from decimal import Decimal

import psycopg2
import psycopg2.extras

from quant.common.config import config

DB_CONFIG = dict(
    host=config.database.host,
    port=config.database.port,
    dbname=config.database.database,
    user=config.database.user,
    password=config.database.password.get_secret_value(),
)


def get_connection():
    return psycopg2.connect(**DB_CONFIG)


def find_best_symbol(cur, news_time):
    """
    Find the best kline_data symbol to use for this news time.
    We pick the symbol that has the most data around the news time window
    (from -1 day to +2 days).

    Priority order if counts are equal: au_continuous > au9999 > au2606 > au_main
    """
    window_start = news_time - timedelta(days=1)
    window_end = news_time + timedelta(days=2)

    preferred_order = ['au_continuous', 'au9999', 'au2606', 'au_main']

    # 优先找有 30m 数据的 symbol（避免只有 1m 数据的 symbol 造成精度问题）
    cur.execute("""
        SELECT symbol, COUNT(*) as cnt
        FROM kline_data
        WHERE time >= %s AND time <= %s
          AND symbol IN ('au_continuous', 'au9999', 'au2606', 'au_main')
          AND interval = '30m'
        GROUP BY symbol
        ORDER BY cnt DESC
    """, (window_start, window_end))

    results = cur.fetchall()

    # 如果没有 30m 数据，降级到所有 interval
    if not results:
        cur.execute("""
            SELECT symbol, COUNT(*) as cnt
            FROM kline_data
            WHERE time >= %s AND time <= %s
              AND symbol IN ('au_continuous', 'au9999', 'au2606', 'au_main')
            GROUP BY symbol
            ORDER BY cnt DESC
        """, (window_start, window_end))
        results = cur.fetchall()

    if not results:
        return None

    best_count = results[0][1]

    # 按优先级选择：优先 au_main（30m 数据最完整覆盖近期）
    preferred_order = ['au_main', 'au_continuous', 'au2606', 'au9999']
    for sym in preferred_order:
        for row in results:
            if row[0] == sym and row[1] >= best_count * 0.3:
                return sym

    return results[0][0]


def find_price(cur, symbol, target_time, direction='nearest'):
    """
    Find closest kline close price for a given symbol and target time.
    Tries intervals in priority order: 30m -> 1m -> 15m -> any

    direction: 'nearest', 'before' (<=), 'after' (>=)
    Returns: (price, actual_time) or (None, None)
    """
    # 优先使用粒度合适的 interval，避免 1m 数据噪音或 interval 混用
    interval_priority = ['30m', '1m', '15m', None]  # None = 不过滤

    for interval in interval_priority:
        row_before = None
        row_after = None

        if direction in ('before', 'nearest'):
            if interval:
                cur.execute("""
                    SELECT close, time FROM kline_data
                    WHERE symbol = %s AND time <= %s AND interval = %s
                    ORDER BY time DESC LIMIT 1
                """, (symbol, target_time, interval))
            else:
                cur.execute("""
                    SELECT close, time FROM kline_data
                    WHERE symbol = %s AND time <= %s
                    ORDER BY time DESC LIMIT 1
                """, (symbol, target_time))
            row_before = cur.fetchone()

        if direction in ('after', 'nearest'):
            if interval:
                cur.execute("""
                    SELECT close, time FROM kline_data
                    WHERE symbol = %s AND time >= %s AND interval = %s
                    ORDER BY time ASC LIMIT 1
                """, (symbol, target_time, interval))
            else:
                cur.execute("""
                    SELECT close, time FROM kline_data
                    WHERE symbol = %s AND time >= %s
                    ORDER BY time ASC LIMIT 1
                """, (symbol, target_time))
            row_after = cur.fetchone()

        if direction == 'nearest':
            if row_before and row_after:
                diff_b = abs((target_time - row_before[1]).total_seconds())
                diff_a = abs((row_after[1] - target_time).total_seconds())
                row = row_before if diff_b <= diff_a else row_after
            elif row_before:
                row = row_before
            elif row_after:
                row = row_after
            else:
                row = None
        elif direction == 'before':
            row = row_before
        else:
            row = row_after

        if row is None:
            continue

        # Sanity: reject if more than 5 days away
        gap = abs((row[1] - target_time).total_seconds())
        if gap > 5 * 24 * 3600:
            continue

        return float(row[0]), row[1]

    return None, None


def find_daily_price_1d(cur, news_time):
    """
    Find next trading day's close price from kline_daily.
    Returns: (price, date) or (None, None)
    """
    news_date = news_time.date()
    cur.execute("""
        SELECT close, time FROM kline_daily
        WHERE symbol = 'au_continuous' AND time > %s
        ORDER BY time ASC LIMIT 1
    """, (news_date,))
    row = cur.fetchone()
    if row:
        return float(row[0]), row[1]
    return None, None


def find_daily_base_price(cur, news_time):
    """
    Find the daily close price on or before the news date.
    Used when minute data is unavailable for base price.
    Returns: (price, date) or (None, None)
    """
    news_date = news_time.date()
    cur.execute("""
        SELECT close, time FROM kline_daily
        WHERE symbol = 'au_continuous' AND time <= %s
        ORDER BY time DESC LIMIT 1
    """, (news_date,))
    row = cur.fetchone()
    if row:
        return float(row[0]), row[1]
    return None, None


def compute_correctness(direction, price_change):
    """
    Determine if the LLM prediction direction matches actual price change.
    - bullish + price up -> 1
    - bearish + price down -> 1
    - neutral -> None
    - otherwise -> 0
    """
    if direction is None or price_change is None:
        return None

    d = direction.lower().strip()

    if d == 'neutral':
        return None

    if d == 'bullish':
        return 1 if price_change > 0 else 0
    elif d == 'bearish':
        return 1 if price_change < 0 else 0

    return None


ALLOWED_ANCHOR_TIMES = {'effective_time', 'published_time'}
VERIFICATION_VERSION = 'verification_layering_v1'


def ensure_verification_schema():
    """Create minimal news_verification table and legacy verification columns if needed."""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            ALTER TABLE news_analysis
            ADD COLUMN IF NOT EXISTS base_price DECIMAL(18, 6),
            ADD COLUMN IF NOT EXISTS price_change_30m DECIMAL(18, 6),
            ADD COLUMN IF NOT EXISTS price_change_4h DECIMAL(18, 6),
            ADD COLUMN IF NOT EXISTS price_change_1d DECIMAL(18, 6),
            ADD COLUMN IF NOT EXISTS correct_30m INTEGER,
            ADD COLUMN IF NOT EXISTS correct_4h INTEGER,
            ADD COLUMN IF NOT EXISTS correct_1d INTEGER,
            ADD COLUMN IF NOT EXISTS direction_correct INTEGER;
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS news_verification (
                id SERIAL PRIMARY KEY,
                analysis_id INTEGER NOT NULL REFERENCES news_analysis(id) ON DELETE CASCADE,
                verification_scope VARCHAR(32) NOT NULL,
                verification_anchor_time TIMESTAMPTZ NOT NULL,
                symbol VARCHAR(32),
                base_price DECIMAL(18, 6),
                price_change_30m DECIMAL(18, 6),
                price_change_4h DECIMAL(18, 6),
                price_change_1d DECIMAL(18, 6),
                correct_30m INTEGER,
                correct_4h INTEGER,
                correct_1d INTEGER,
                direction_correct INTEGER,
                verification_version VARCHAR(64) NOT NULL,
                verified_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                CONSTRAINT uq_news_verification_analysis_scope UNIQUE (analysis_id, verification_scope),
                CONSTRAINT ck_news_verification_scope CHECK (
                    verification_scope IN ('effective_time', 'published_time')
                ),
                CONSTRAINT ck_news_verification_correct_30m CHECK (correct_30m IN (0, 1) OR correct_30m IS NULL),
                CONSTRAINT ck_news_verification_correct_4h CHECK (correct_4h IN (0, 1) OR correct_4h IS NULL),
                CONSTRAINT ck_news_verification_correct_1d CHECK (correct_1d IN (0, 1) OR correct_1d IS NULL),
                CONSTRAINT ck_news_verification_direction_correct CHECK (direction_correct IN (0, 1) OR direction_correct IS NULL)
            );
        """)

        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_news_verification_anchor_time
            ON news_verification (verification_anchor_time DESC);
        """)

        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_news_verification_verified_at
            ON news_verification (verified_at DESC);
        """)

        conn.commit()
    finally:
        cur.close()
        conn.close()


def process_all_records(dry_run=False, anchor_time='effective_time'):
    """Process all news_analysis records."""
    if anchor_time not in ALLOWED_ANCHOR_TIMES:
        raise ValueError(f'Unsupported anchor_time: {anchor_time}')

    if not dry_run:
        ensure_verification_schema()

    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    update_cur = conn.cursor()

    anchor_expr = """
        COALESCE(na.effective_time, na.analyzed_at, na.published_time, nr.time)
    """ if anchor_time == 'effective_time' else """
        COALESCE(na.published_time, nr.time)
    """

    cur.execute(f"""
        SELECT na.id, na.news_id,
               {anchor_expr} AS anchor_time,
               na.published_time,
               na.analyzed_at,
               na.effective_time,
               nr.time as news_time,
               na.direction, na.importance,
               na.confidence, nr.title
        FROM news_analysis na
        JOIN news_raw nr ON na.news_id = nr.id
        ORDER BY {anchor_expr}
    """)
    records = cur.fetchall()
    print(f"Processing {len(records)} news_analysis records...")
    print(f"Verification anchor: {anchor_time}")
    print()

    stats = {
        'total': len(records),
        'base_price_found': 0,
        'price_30m_found': 0,
        'price_4h_found': 0,
        'price_1d_found': 0,
        'correct_30m': {'total': 0, 'correct': 0},
        'correct_4h': {'total': 0, 'correct': 0},
        'correct_1d': {'total': 0, 'correct': 0},
    }

    for i, rec in enumerate(records):
        na_id = rec['id']
        anchor_ts = rec['anchor_time']
        direction = rec['direction']

        if anchor_ts is None:
            print(f"  [{na_id}] anchor_time is NULL. Skipping.")
            continue

        # 1. Find best symbol for this anchor time
        symbol = find_best_symbol(cur, anchor_ts)

        # 2. Find base_price using minute data from the chosen symbol
        base_price = None
        base_time = None

        if symbol:
            base_price, base_time = find_price(cur, symbol, anchor_ts, direction='nearest')

        # Fallback: use kline_daily if minute data not available
        if base_price is None:
            base_price, base_time = find_daily_base_price(cur, anchor_ts)
            symbol = None  # mark that we're using daily data

        if base_price is None:
            print(f"  [{na_id}] {anchor_ts} - No base price found. Skipping.")
            continue

        stats['base_price_found'] += 1

        # 3. Find +30m price (same symbol if available)
        price_change_30m = None
        if symbol:
            price_30m, _ = find_price(cur, symbol, anchor_ts + timedelta(minutes=30), direction='after')
            if price_30m and base_price > 0:
                price_change_30m = ((price_30m - base_price) / base_price) * 100
                stats['price_30m_found'] += 1

        # 4. Find +4h price (same symbol if available)
        price_change_4h = None
        if symbol:
            price_4h, _ = find_price(cur, symbol, anchor_ts + timedelta(hours=4), direction='after')
            if price_4h and base_price > 0:
                price_change_4h = ((price_4h - base_price) / base_price) * 100
                stats['price_4h_found'] += 1

        # 5. Find +1d price
        #    Try kline_daily next trading day close first
        #    If base_price is from daily data, use daily-to-daily for consistency
        price_change_1d = None
        price_1d, date_1d = find_daily_price_1d(cur, anchor_ts)
        if price_1d is not None and base_price > 0:
            price_change_1d = ((price_1d - base_price) / base_price) * 100
            stats['price_1d_found'] += 1

        # 6. Compute correctness
        correct_30m = compute_correctness(direction, price_change_30m)
        correct_4h = compute_correctness(direction, price_change_4h)
        correct_1d = compute_correctness(direction, price_change_1d)
        direction_correct = correct_1d

        # Track accuracy stats
        if correct_30m is not None:
            stats['correct_30m']['total'] += 1
            stats['correct_30m']['correct'] += correct_30m
        if correct_4h is not None:
            stats['correct_4h']['total'] += 1
            stats['correct_4h']['correct'] += correct_4h
        if correct_1d is not None:
            stats['correct_1d']['total'] += 1
            stats['correct_1d']['correct'] += correct_1d

        # Print progress
        if (i + 1) % 20 == 0 or i == 0:
            sym_str = symbol or 'daily'
            print(f"  [{i+1}/{len(records)}] id={na_id}, anchor={anchor_time}, sym={sym_str}, base={base_price:.2f}, "
                  f"chg30m={fmt_pct(price_change_30m)}, chg4h={fmt_pct(price_change_4h)}, "
                  f"chg1d={fmt_pct(price_change_1d)}, dir={direction}")

        # 7. Update database
        if not dry_run:
            base_price_db = Decimal(str(base_price))
            price_change_30m_db = Decimal(str(round(price_change_30m, 6))) if price_change_30m is not None else None
            price_change_4h_db = Decimal(str(round(price_change_4h, 6))) if price_change_4h is not None else None
            price_change_1d_db = Decimal(str(round(price_change_1d, 6))) if price_change_1d is not None else None

            # New default truth path: news_verification
            update_cur.execute("""
                INSERT INTO news_verification (
                    analysis_id,
                    verification_scope,
                    verification_anchor_time,
                    symbol,
                    base_price,
                    price_change_30m,
                    price_change_4h,
                    price_change_1d,
                    correct_30m,
                    correct_4h,
                    correct_1d,
                    direction_correct,
                    verification_version,
                    verified_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                ON CONFLICT (analysis_id, verification_scope) DO UPDATE SET
                    verification_anchor_time = EXCLUDED.verification_anchor_time,
                    symbol = EXCLUDED.symbol,
                    base_price = EXCLUDED.base_price,
                    price_change_30m = EXCLUDED.price_change_30m,
                    price_change_4h = EXCLUDED.price_change_4h,
                    price_change_1d = EXCLUDED.price_change_1d,
                    correct_30m = EXCLUDED.correct_30m,
                    correct_4h = EXCLUDED.correct_4h,
                    correct_1d = EXCLUDED.correct_1d,
                    direction_correct = EXCLUDED.direction_correct,
                    verification_version = EXCLUDED.verification_version,
                    verified_at = NOW()
            """, (
                na_id,
                anchor_time,
                anchor_ts,
                symbol,
                base_price_db,
                price_change_30m_db,
                price_change_4h_db,
                price_change_1d_db,
                correct_30m,
                correct_4h,
                correct_1d,
                direction_correct,
                VERIFICATION_VERSION,
            ))

            # Short-term compatibility: double-write legacy verification fields on news_analysis
            update_cur.execute("""
                UPDATE news_analysis
                SET base_price = %s,
                    price_change_30m = %s,
                    price_change_4h = %s,
                    price_change_1d = %s,
                    correct_30m = %s,
                    correct_4h = %s,
                    correct_1d = %s,
                    direction_correct = %s
                WHERE id = %s
            """, (
                base_price_db,
                price_change_30m_db,
                price_change_4h_db,
                price_change_1d_db,
                correct_30m,
                correct_4h,
                correct_1d,
                direction_correct,
                na_id,
            ))

    if not dry_run:
        conn.commit()
        print("\n[OK] Database updated successfully.")
    else:
        print("\n[DRY RUN] No changes made.")

    # Print statistics
    print(f"\n{'='*60}")
    print("STATISTICS")
    print(f"{'='*60}")
    print(f"Total records: {stats['total']}")
    print(f"Base price found: {stats['base_price_found']}")
    print(f"+30m price found: {stats['price_30m_found']}")
    print(f"+4h price found:  {stats['price_4h_found']}")
    print(f"+1d price found:  {stats['price_1d_found']}")
    print()
    print("LLM Direction Accuracy (excluding neutral predictions):")
    for dim_key, dim_label in [('correct_30m', '30 min'), ('correct_4h', '4 hour'), ('correct_1d', '1 day')]:
        s = stats[dim_key]
        if s['total'] > 0:
            acc = s['correct'] / s['total'] * 100
            print(f"  {dim_label:>8}: {s['correct']}/{s['total']} = {acc:.1f}%")
        else:
            print(f"  {dim_label:>8}: N/A (no evaluable predictions)")
    print(f"{'='*60}")

    cur.close()
    update_cur.close()
    conn.close()

    return stats


def fmt_pct(v):
    """Format percentage or return N/A."""
    if v is None:
        return "N/A"
    return f"{v:+.4f}%"


def main():
    parser = argparse.ArgumentParser(description='Verify news price impact')
    parser.add_argument('--dry-run', action='store_true',
                        help='Run without updating database')
    parser.add_argument('--anchor-time', choices=sorted(ALLOWED_ANCHOR_TIMES), default='effective_time',
                        help='Verification anchor time. Default uses effective_time; published_time is for explicit research contrast.')
    args = parser.parse_args()

    process_all_records(dry_run=args.dry_run, anchor_time=args.anchor_time)
    return 0


if __name__ == '__main__':
    sys.exit(main())
