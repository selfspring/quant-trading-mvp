# -*- coding: utf-8 -*-
import pandas as pd
import psycopg2

# 连接数据库
conn = psycopg2.connect(
    host='localhost',
    port=5432,
    dbname='quant_trading',
    user='postgres',
    password='@Cmx1454697261'
)

# 获取完整数据进行深度分析
query = """
SELECT time as timestamp, open, high, low, close, volume, COALESCE(open_interest, 0) as open_interest
FROM kline_data
WHERE symbol='au2606' AND interval='1m'
ORDER BY time ASC
"""

df = pd.read_sql(query, conn)
conn.close()

print("=== 深度市场分析 ===\n")

# 1. 价格趋势分析
recent_20 = df['close'].tail(20).tolist()
recent_10 = df['close'].tail(10).tolist()
recent_5 = df['close'].tail(5).tolist()

current_price = recent_5[-1]
ma5 = sum(recent_5) / len(recent_5)
ma10 = sum(recent_10) / len(recent_10)
ma20 = sum(recent_20) / len(recent_20)

print(f"当前价格: {current_price:.2f}")
print(f"MA5: {ma5:.2f}")
print(f"MA10: {ma10:.2f}")
print(f"MA20: {ma20:.2f}")

# 2. 价格动量
momentum_5 = ((recent_5[-1] - recent_5[0]) / recent_5[0]) * 100
momentum_10 = ((recent_10[-1] - recent_10[0]) / recent_10[0]) * 100
momentum_20 = ((recent_20[-1] - recent_20[0]) / recent_20[0]) * 100

print(f"\n动量分析:")
print(f"5周期动量: {momentum_5:.3f}%")
print(f"10周期动量: {momentum_10:.3f}%")
print(f"20周期动量: {momentum_20:.3f}%")

# 3. 波动性分析
volatility = pd.Series(recent_20).std()
print(f"\n波动性(20周期标准差): {volatility:.2f}")

# 4. 成交量分析
recent_vol_5 = df['volume'].tail(5).mean()
recent_vol_20 = df['volume'].tail(20).mean()
vol_ratio = recent_vol_5 / recent_vol_20 if recent_vol_20 > 0 else 1

print(f"\n成交量分析:")
print(f"近5周期平均成交量: {recent_vol_5:.0f}")
print(f"近20周期平均成交量: {recent_vol_20:.0f}")
print(f"成交量比率: {vol_ratio:.2f}")

# 5. 支撑阻力
high_20 = df['high'].tail(20).max()
low_20 = df['low'].tail(20).min()

print(f"\n支撑阻力(20周期):")
print(f"阻力位: {high_20:.2f}")
print(f"支撑位: {low_20:.2f}")
print(f"当前位置: {((current_price - low_20) / (high_20 - low_20) * 100):.1f}%")

# 6. 趋势判断
trend_signal = "上升" if ma5 > ma10 > ma20 else "下降" if ma5 < ma10 < ma20 else "震荡"
print(f"\n趋势判断: {trend_signal}")
