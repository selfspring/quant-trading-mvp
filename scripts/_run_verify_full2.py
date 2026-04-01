import sys, os, time as _time
sys.path.insert(0, r"E:\quant-trading-mvp")
os.chdir(r"E:\quant-trading-mvp")

if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8')

import traceback
import psycopg2
import psycopg2.extras
from datetime import timedelta
from decimal import Decimal
from quant.common.config import config

DB_CONFIG = dict(
    host=config.database.host,
    port=config.database.port,
    dbname=config.database.database,
    user=config.database.user,
    password=config.database.password.get_secret_value(),
)

# Replicate process_all_records logic but with progress tracking
try:
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    import importlib.util
    spec = importlib.util.spec_from_file_location("verify", r"E:\quant-trading-mvp\scripts\verify_news_price_impact.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    anchor_time = 'effective_time'
    anchor_expr = "COALESCE(na.effective_time, na.analyzed_at, na.published_time, nr.time)"

    cur.execute(f"""
        SELECT na.id, na.news_id,
               {anchor_expr} AS anchor_time,
               na.published_time, na.analyzed_at, na.effective_time,
               nr.time as news_time,
               na.direction, na.importance, na.confidence, nr.title
        FROM news_analysis na
        JOIN news_raw nr ON na.news_id = nr.id
        ORDER BY {anchor_expr}
    """)
    records = cur.fetchall()
    total = len(records)
    print(f"Total records: {total}")
    sys.stdout.flush()

    stats = {
        'total': total, 'base_price_found': 0,
        'price_30m_found': 0, 'price_4h_found': 0, 'price_1d_found': 0,
        'correct_30m': {'total': 0, 'correct': 0},
        'correct_4h': {'total': 0, 'correct': 0},
        'correct_1d': {'total': 0, 'correct': 0},
    }

    start = _time.time()
    for i, rec in enumerate(records):
        na_id = rec['id']
        anchor_ts = rec['anchor_time']
        direction = rec['direction']

        if anchor_ts is None:
            continue

        symbol = mod.find_best_symbol(cur, anchor_ts)
        base_price, base_time = None, None
        if symbol:
            base_price, base_time = mod.find_price(cur, symbol, anchor_ts, direction='nearest')
        if base_price is None:
            base_price, base_time = mod.find_daily_base_price(cur, anchor_ts)
            symbol = None
        if base_price is None:
            continue

        stats['base_price_found'] += 1

        price_change_30m = None
        if symbol:
            p, _ = mod.find_price(cur, symbol, anchor_ts + timedelta(minutes=30), direction='after')
            if p and base_price > 0:
                price_change_30m = ((p - base_price) / base_price) * 100
                stats['price_30m_found'] += 1

        price_change_4h = None
        if symbol:
            p, _ = mod.find_price(cur, symbol, anchor_ts + timedelta(hours=4), direction='after')
            if p and base_price > 0:
                price_change_4h = ((p - base_price) / base_price) * 100
                stats['price_4h_found'] += 1

        price_change_1d = None
        p, _ = mod.find_daily_price_1d(cur, anchor_ts)
        if p is not None and base_price > 0:
            price_change_1d = ((p - base_price) / base_price) * 100
            stats['price_1d_found'] += 1

        c30 = mod.compute_correctness(direction, price_change_30m)
        c4h = mod.compute_correctness(direction, price_change_4h)
        c1d = mod.compute_correctness(direction, price_change_1d)

        if c30 is not None:
            stats['correct_30m']['total'] += 1
            stats['correct_30m']['correct'] += c30
        if c4h is not None:
            stats['correct_4h']['total'] += 1
            stats['correct_4h']['correct'] += c4h
        if c1d is not None:
            stats['correct_1d']['total'] += 1
            stats['correct_1d']['correct'] += c1d

        if (i + 1) % 100 == 0:
            elapsed = _time.time() - start
            print(f"  [{i+1}/{total}] {elapsed:.1f}s elapsed")
            sys.stdout.flush()

    elapsed = _time.time() - start
    print(f"\nCompleted {total} records in {elapsed:.1f}s")
    print(f"Base price found: {stats['base_price_found']}")
    print(f"+30m found: {stats['price_30m_found']}")
    print(f"+4h found: {stats['price_4h_found']}")
    print(f"+1d found: {stats['price_1d_found']}")

    for k, label in [('correct_30m', '30min'), ('correct_4h', '4h'), ('correct_1d', '1d')]:
        s = stats[k]
        if s['total'] > 0:
            acc = s['correct'] / s['total'] * 100
            print(f"  {label}: {s['correct']}/{s['total']} = {acc:.1f}%")
        else:
            print(f"  {label}: N/A")

    print("\n[DRY-RUN FULL PASSED]")
    sys.stdout.flush()

    cur.close()
    conn.close()

except Exception as e:
    print(f"\nEXCEPTION: {type(e).__name__}: {e}")
    traceback.print_exc()
    sys.stdout.flush()
