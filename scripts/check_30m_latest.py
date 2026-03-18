import psycopg2, pandas as pd
conn = psycopg2.connect(host='localhost', port=5432, dbname='quant_trading', user='postgres', password='@Cmx1454697261')

df = pd.read_sql("""
    SELECT time, close FROM kline_data 
    WHERE symbol='au2606' AND interval='30m' 
    ORDER BY time DESC LIMIT 5
""", conn)
print("最新5根 au2606 30m:")
for _, r in df.iterrows():
    print(f"  {r['time']}  close={r['close']}")

# 今晚采集器聚合的 30m
df2 = pd.read_sql("""
    SELECT time, close FROM kline_data 
    WHERE symbol='au2606' AND interval='30m' AND time >= '2026-03-17 21:00+08'
    ORDER BY time
""", conn)
print(f"\n今晚聚合的 30m: {len(df2)} 根")
for _, r in df2.iterrows():
    print(f"  {r['time']}  close={r['close']}")

conn.close()
