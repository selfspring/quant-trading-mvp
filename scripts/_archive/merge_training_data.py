"""合并多个数据源，增加训练数据量"""
import pandas as pd
import numpy as np

print("=== 合并训练数据 ===\n")

# 1. 天勤 30 分钟线（1000 根）
print("1. 天勤 30 分钟线...")
df_tq = pd.read_csv('E:/quant-trading-mvp/data/tq_au_30m.csv')
df_tq['datetime'] = pd.to_datetime(df_tq['datetime'], unit='ns')
df_tq = df_tq.rename(columns={'datetime': 'timestamp'})
df_tq = df_tq[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
print(f"   行数: {len(df_tq)}")
print(f"   时间: {df_tq.iloc[0]['timestamp']} ~ {df_tq.iloc[-1]['timestamp']}")

# 2. AkShare 日线转 30 分钟（模拟）
print("\n2. AkShare 日线数据（转换为 30 分钟）...")
df_daily = pd.read_csv('E:/quant-trading-mvp/data/au_main_daily.csv')
df_daily['timestamp'] = pd.to_datetime(df_daily['date'])
df_daily = df_daily[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
print(f"   原始日线: {len(df_daily)} 天")

# 将日线拆分为 8 根 30 分钟线（模拟日内走势）
# 简化处理：每天生成 8 根 K 线，价格在 OHLC 之间线性插值
expanded_rows = []
for _, row in df_daily.iterrows():
    base_time = row['timestamp']
    o, h, l, c = row['open'], row['high'], row['low'], row['close']
    v = row['volume'] / 8  # 成交量平均分配
    
    # 生成 8 根 30 分钟线（简化：线性插值）
    for i in range(8):
        t = base_time + pd.Timedelta(minutes=30*i)
        # 简单插值：从 open 到 close
        price = o + (c - o) * (i / 7)
        expanded_rows.append({
            'timestamp': t,
            'open': price,
            'high': max(price, h * (1 - i/8) + c * (i/8)),
            'low': min(price, l * (1 - i/8) + c * (i/8)),
            'close': o + (c - o) * ((i+1) / 7) if i < 7 else c,
            'volume': v
        })

df_expanded = pd.DataFrame(expanded_rows)
print(f"   扩展后: {len(df_expanded)} 根 30 分钟线")

# 3. 合并数据
print("\n3. 合并数据...")
df_combined = pd.concat([df_expanded, df_tq], ignore_index=True)
df_combined = df_combined.sort_values('timestamp').drop_duplicates(subset=['timestamp']).reset_index(drop=True)
print(f"   合并后: {len(df_combined)} 根")
print(f"   时间范围: {df_combined.iloc[0]['timestamp']} ~ {df_combined.iloc[-1]['timestamp']}")

# 4. 保存
df_combined.to_csv('E:/quant-trading-mvp/data/au_30m_combined.csv', index=False)
print(f"\n已保存: data/au_30m_combined.csv ({len(df_combined)} 行)")
