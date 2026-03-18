import psycopg2
import json

conn = psycopg2.connect(host='localhost', dbname='quant_trading', user='postgres', password='@Cmx1454697261')
cur = conn.cursor()

# check kline_data columns
cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='kline_data' ORDER BY ordinal_position")
print("kline_data columns:", [r[0] for r in cur.fetchall()])

# kline_data count and range
cur.execute("SELECT COUNT(*) FROM kline_data")
print("kline_data total:", cur.fetchone()[0])

# find date column and get range
cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='kline_data' AND data_type LIKE '%timestamp%' LIMIT 1")
dc = cur.fetchone()
if dc:
    dc = dc[0]
    cur.execute(f"SELECT MIN({dc}), MAX({dc}) FROM kline_data")
    print(f"kline_data range ({dc}):", cur.fetchone())
    cur.execute(f"SELECT COUNT(*) FROM kline_data WHERE {dc}::date = CURRENT_DATE")
    print("kline_data today:", cur.fetchone()[0])
    cur.execute(f"SELECT * FROM kline_data ORDER BY {dc} DESC LIMIT 3")
    cols = [d[0] for d in cur.description]
    print("Columns:", cols)
    for r in cur.fetchall():
        print(r)

# trades and orders
for t in ['trades', 'orders']:
    cur.execute(f"SELECT column_name FROM information_schema.columns WHERE table_name='{t}' ORDER BY ordinal_position")
    print(f"\n{t} columns:", [r[0] for r in cur.fetchall()])
    cur.execute(f"SELECT COUNT(*) FROM {t}")
    print(f"{t} total:", cur.fetchone()[0])

# strategy state
print("\n=== strategy_state.json ===")
with open('data/strategy_state.json', 'r') as f:
    print(json.dumps(json.load(f), indent=2, default=str))

conn.close()
