import sys
sys.path.insert(0, 'E:/quant-trading-mvp')
from quant.common.config import config
from quant.common.db import db_connection

with db_connection(config) as conn:
    cur = conn.cursor()

    # list all tables
    cur.execute("SELECT tablename FROM pg_tables WHERE schemaname='public'")
    tables = [r[0] for r in cur.fetchall()]
    print("Tables:", tables)

    # check each table count and date range
    for t in tables:
        try:
            cur.execute(f"SELECT COUNT(*) FROM {t}")
            cnt = cur.fetchone()[0]
            # try to find date column
            cur.execute(f"SELECT column_name FROM information_schema.columns WHERE table_name='{t}' AND column_name IN ('datetime','trade_time','created_at','timestamp') LIMIT 1")
            date_col = cur.fetchone()
            if date_col:
                dc = date_col[0]
                cur.execute(f"SELECT MIN({dc}), MAX({dc}) FROM {t}")
                mn, mx = cur.fetchone()
                print(f"  {t}: {cnt} rows, {mn} ~ {mx}")
                # today count
                cur.execute(f"SELECT COUNT(*) FROM {t} WHERE {dc}::date = CURRENT_DATE")
                today = cur.fetchone()[0]
                print(f"    Today: {today}")
            else:
                print(f"  {t}: {cnt} rows")
        except Exception as e:
            print(f"  {t}: ERROR {e}")
            conn.rollback()
