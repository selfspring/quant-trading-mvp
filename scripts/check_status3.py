import psycopg2

conn = psycopg2.connect(host='localhost', dbname='quant_trading', user='postgres', password='@Cmx1454697261')
cur = conn.cursor()

# kline_data breakdown
cur.execute("SELECT instrument_id, COUNT(*), MIN(datetime), MAX(datetime) FROM kline_data GROUP BY instrument_id")
print("=== kline_data ===")
for r in cur.fetchall():
    print(r)

# today's kline_data
cur.execute("SELECT COUNT(*) FROM kline_data WHERE datetime::date = CURRENT_DATE")
print("\nToday kline_data:", cur.fetchone()[0])

# recent kline_data
cur.execute("SELECT datetime, open, high, low, close, volume FROM kline_data WHERE datetime::date = CURRENT_DATE ORDER BY datetime DESC LIMIT 5")
print("\nLatest klines today:")
for r in cur.fetchall():
    print(r)

# news_raw today
cur.execute("SELECT COUNT(*) FROM news_raw WHERE created_at::date = CURRENT_DATE")
print("\nToday news:", cur.fetchone()[0])

# strategy_state.json
print("\n=== strategy_state.json ===")
import json
with open('data/strategy_state.json', 'r') as f:
    state = json.load(f)
    print(json.dumps(state, indent=2, default=str))

conn.close()
