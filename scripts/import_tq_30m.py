"""从天勤下载 au2606 30m 数据并导入数据库"""
from tqsdk import TqApi, TqAuth
import pandas as pd
import psycopg2

auth = TqAuth("17340696348", "@Cmx1454697261")

print("连接天勤...")
api = TqApi(auth=auth)

print("下载 au2606 30m 数据...")
klines = api.get_kline_serial("SHFE.au2606", 30 * 60, data_length=10000)
klines['dt'] = pd.to_datetime(klines['datetime'], unit='ns', utc=True).dt.tz_convert('Asia/Shanghai')

print(f"获取 {len(klines)} 根")
print(f"范围: {klines['dt'].iloc[0]} ~ {klines['dt'].iloc[-1]}")

api.close()

# 导入数据库
print("\n导入数据库...")
conn = psycopg2.connect(host='localhost', port=5432, dbname='quant_trading', user='postgres', password='@Cmx1454697261')
cur = conn.cursor()

count = 0
for _, row in klines.iterrows():
    if row['open'] == 0 or pd.isna(row['open']):
        continue
    cur.execute("""
        INSERT INTO kline_data (time, symbol, interval, open, high, low, close, volume, open_interest)
        VALUES (%s, 'au2606', '30m', %s, %s, %s, %s, %s, %s)
        ON CONFLICT (time, symbol, interval) DO UPDATE SET
            open=EXCLUDED.open, high=EXCLUDED.high, low=EXCLUDED.low,
            close=EXCLUDED.close, volume=EXCLUDED.volume, open_interest=EXCLUDED.open_interest
    """, (row['dt'], float(row['open']), float(row['high']), float(row['low']),
          float(row['close']), int(row['volume']), float(row.get('close_oi', 0))))
    count += 1

conn.commit()
cur.close()
conn.close()
print(f"导入完成: {count} 根 au2606 30m K线")
