import psycopg2

conn = psycopg2.connect(
    host='localhost', port=5432, database='quant_trading',
    user='postgres', password='@Cmx1454697261'
)
cur = conn.cursor()

# 检查所有可能有价格数据的表
tables = ['kline_data', 'kline_1h', 'kline_daily', 'tick_data', 'macro_daily']
for t in tables:
    try:
        cur.execute(f"SELECT COUNT(*) FROM {t}")
        cnt = cur.fetchone()[0]
        if cnt > 0:
            # 找时间列
            cur.execute(f"""
                SELECT column_name FROM information_schema.columns
                WHERE table_name = '{t}' AND data_type LIKE '%time%' OR (table_name = '{t}' AND data_type = 'date')
                ORDER BY ordinal_position LIMIT 3
            """)
            time_cols = [r[0] for r in cur.fetchall()]
            
            for tc in time_cols:
                try:
                    cur.execute(f"SELECT MIN({tc}), MAX({tc}) FROM {t}")
                    r = cur.fetchone()
                    print(f"{t} ({cnt} rows) [{tc}]: {r[0]} ~ {r[1]}")
                except:
                    conn.rollback()
            
            # 看看有哪些 symbol
            cur.execute(f"""
                SELECT column_name FROM information_schema.columns
                WHERE table_name = '{t}' AND column_name IN ('symbol', 'pair', 'instrument')
            """)
            sym_cols = [r[0] for r in cur.fetchall()]
            for sc in sym_cols:
                cur.execute(f"SELECT DISTINCT {sc} FROM {t} LIMIT 10")
                syms = [r[0] for r in cur.fetchall()]
                print(f"  {sc}: {syms}")
        else:
            print(f"{t}: empty")
    except Exception as e:
        conn.rollback()
        print(f"{t}: error - {e}")

# 也查一下 fundamental_data
print("\n=== fundamental_data ===")
cur.execute("SELECT COUNT(*) FROM fundamental_data")
cnt = cur.fetchone()[0]
print(f"  rows: {cnt}")
if cnt > 0:
    cur.execute("""
        SELECT column_name, data_type FROM information_schema.columns
        WHERE table_name = 'fundamental_data' ORDER BY ordinal_position
    """)
    for r in cur.fetchall():
        print(f"  {r[0]:25s} {r[1]}")

# macro_daily
print("\n=== macro_daily ===")
cur.execute("SELECT COUNT(*) FROM macro_daily")
cnt = cur.fetchone()[0]
print(f"  rows: {cnt}")
if cnt > 0:
    cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'macro_daily' ORDER BY ordinal_position")
    for r in cur.fetchall():
        print(f"  {r[0]:25s} {r[1]}")
    cur.execute("SELECT MIN(date), MAX(date) FROM macro_daily")
    r = cur.fetchone()
    print(f"  range: {r[0]} ~ {r[1]}")

conn.close()
