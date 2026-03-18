"""将天勤历史数据导入数据库"""
import pandas as pd
import psycopg2
from psycopg2.extras import execute_batch

print("=== 连接数据库 ===")
conn = psycopg2.connect(
    host='localhost', port=5432,
    dbname='quant_trading', user='postgres',
    password='@Cmx1454697261'
)
cur = conn.cursor()

# 1. 导入 30 分钟线
print("\n=== 导入 30 分钟线 ===")
df_30m = pd.read_csv('E:/quant-trading-mvp/data/tq_au_30m_10000.csv')
df_30m['datetime'] = pd.to_datetime(df_30m['datetime'])

# 准备数据
rows = []
for _, row in df_30m.iterrows():
    rows.append((
        row['datetime'],
        'au_main',  # 主力合约
        '30m',
        float(row['open']),
        float(row['high']),
        float(row['low']),
        float(row['close']),
        int(row['volume']),
        int(row.get('open_oi', 0))
    ))

print(f"准备导入 {len(rows)} 根 30 分钟线...")

# 批量插入（使用 ON CONFLICT 避免重复）
execute_batch(cur, """
    INSERT INTO kline_data (time, symbol, interval, open, high, low, close, volume, open_interest)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    ON CONFLICT (time, symbol, interval) DO UPDATE SET
        open=EXCLUDED.open, high=EXCLUDED.high, low=EXCLUDED.low,
        close=EXCLUDED.close, volume=EXCLUDED.volume, open_interest=EXCLUDED.open_interest
""", rows, page_size=1000)

conn.commit()
print(f"[OK] 已导入 30 分钟线")

# 2. 导入日线
print("\n=== 导入日线 ===")
df_daily = pd.read_csv('E:/quant-trading-mvp/data/tq_au_daily_5000.csv')
df_daily['datetime'] = pd.to_datetime(df_daily['datetime'])

# 过滤掉 1970 年的异常数据
df_daily = df_daily[df_daily['datetime'] > '2000-01-01']

rows_daily = []
for _, row in df_daily.iterrows():
    rows_daily.append((
        row['datetime'],
        'au_main',
        '1d',
        float(row['open']),
        float(row['high']),
        float(row['low']),
        float(row['close']),
        int(row['volume']),
        int(row.get('open_oi', 0))
    ))

print(f"准备导入 {len(rows_daily)} 根日线...")

execute_batch(cur, """
    INSERT INTO kline_data (time, symbol, interval, open, high, low, close, volume, open_interest)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    ON CONFLICT (time, symbol, interval) DO UPDATE SET
        open=EXCLUDED.open, high=EXCLUDED.high, low=EXCLUDED.low,
        close=EXCLUDED.close, volume=EXCLUDED.volume, open_interest=EXCLUDED.open_interest
""", rows_daily, page_size=1000)

conn.commit()
print(f"[OK] 已导入日线")

# 3. 查看导入结果
print("\n=== 导入结果 ===")
cur.execute("SELECT interval, COUNT(*) FROM kline_data WHERE symbol='au_main' GROUP BY interval")
for row in cur.fetchall():
    print(f"  {row[0]}: {row[1]} 根")

cur.execute("SELECT MIN(time), MAX(time) FROM kline_data WHERE symbol='au_main' AND interval='30m'")
min_time, max_time = cur.fetchone()
print(f"\n30 分钟线时间范围: {min_time} ~ {max_time}")

cur.close()
conn.close()
print("\n[OK] 数据库导入完成")
