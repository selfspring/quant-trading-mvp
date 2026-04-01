import sys, os
sys.path.insert(0, r"E:\quant-trading-mvp")
os.chdir(r"E:\quant-trading-mvp")

# Force UTF-8
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8')

import traceback

print("Step 1: importing module...")
sys.stdout.flush()

try:
    import psycopg2
    import psycopg2.extras
    from quant.common.config import config
    print("Step 2: config loaded")
    sys.stdout.flush()
    
    DB_CONFIG = dict(
        host=config.database.host,
        port=config.database.port,
        dbname=config.database.database,
        user=config.database.user,
        password=config.database.password.get_secret_value(),
    )
    
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    print("Step 3: connected to DB")
    sys.stdout.flush()
    
    # Test the actual query that process_all_records uses
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
        LIMIT 5
    """
    
    print("Step 4: executing query...")
    sys.stdout.flush()
    
    cur.execute(query)
    records = cur.fetchall()
    print(f"Step 5: got {len(records)} records")
    sys.stdout.flush()
    
    for rec in records:
        print(f"  id={rec['id']}, anchor_time={rec['anchor_time']}, dir={rec['direction']}")
        sys.stdout.flush()
    
    cur.close()
    conn.close()
    print("Step 6: done - query works!")
    sys.stdout.flush()
    
except Exception as e:
    print(f"EXCEPTION: {type(e).__name__}: {e}")
    traceback.print_exc()
    sys.stdout.flush()
