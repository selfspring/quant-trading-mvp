import sys, os
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

try:
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    anchor_expr = "COALESCE(na.effective_time, na.analyzed_at, na.published_time, nr.time)"
    
    query = f"""
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
    """
    
    print("Executing main query...")
    sys.stdout.flush()
    cur.execute(query)
    records = cur.fetchall()
    print(f"Got {len(records)} records")
    sys.stdout.flush()
    
    # Import find_best_symbol from the module
    import importlib.util
    spec = importlib.util.spec_from_file_location("verify", r"E:\quant-trading-mvp\scripts\verify_news_price_impact.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    
    # Process just the first 3 records
    for i, rec in enumerate(records[:3]):
        na_id = rec['id']
        anchor_ts = rec['anchor_time']
        direction = rec['direction']
        
        print(f"\n--- Record {i+1}: id={na_id}, anchor={anchor_ts}, dir={direction}")
        sys.stdout.flush()
        
        if anchor_ts is None:
            print("  anchor_time is NULL, skip")
            continue
        
        symbol = mod.find_best_symbol(cur, anchor_ts)
        print(f"  best symbol: {symbol}")
        sys.stdout.flush()
        
        base_price = None
        base_time = None
        if symbol:
            base_price, base_time = mod.find_price(cur, symbol, anchor_ts, direction='nearest')
            print(f"  base_price from minute: {base_price}, time={base_time}")
            sys.stdout.flush()
        
        if base_price is None:
            base_price, base_time = mod.find_daily_base_price(cur, anchor_ts)
            symbol = None
            print(f"  base_price from daily: {base_price}, time={base_time}")
            sys.stdout.flush()
        
        if base_price is None:
            print("  No base price found - skip")
            continue
        
        # 30m
        price_change_30m = None
        if symbol:
            price_30m, _ = mod.find_price(cur, symbol, anchor_ts + timedelta(minutes=30), direction='after')
            if price_30m and base_price > 0:
                price_change_30m = ((price_30m - base_price) / base_price) * 100
        
        # 4h
        price_change_4h = None
        if symbol:
            price_4h, _ = mod.find_price(cur, symbol, anchor_ts + timedelta(hours=4), direction='after')
            if price_4h and base_price > 0:
                price_change_4h = ((price_4h - base_price) / base_price) * 100
        
        # 1d
        price_change_1d = None
        price_1d, date_1d = mod.find_daily_price_1d(cur, anchor_ts)
        if price_1d is not None and base_price > 0:
            price_change_1d = ((price_1d - base_price) / base_price) * 100
        
        correct_30m = mod.compute_correctness(direction, price_change_30m)
        correct_4h = mod.compute_correctness(direction, price_change_4h)
        correct_1d = mod.compute_correctness(direction, price_change_1d)
        
        print(f"  chg30m={price_change_30m}, chg4h={price_change_4h}, chg1d={price_change_1d}")
        print(f"  correct: 30m={correct_30m}, 4h={correct_4h}, 1d={correct_1d}")
        sys.stdout.flush()
    
    cur.close()
    conn.close()
    print("\n[DRY-RUN partial test PASSED]")
    sys.stdout.flush()

except Exception as e:
    print(f"\nEXCEPTION: {type(e).__name__}: {e}")
    traceback.print_exc()
    sys.stdout.flush()
