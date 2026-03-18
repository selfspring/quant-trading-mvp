"""验证天勤 8000 根 30 分钟线数据真实性"""
import pandas as pd

df = pd.read_csv('E:/quant-trading-mvp/data/tq_au_30m_8000.csv')
df['datetime'] = pd.to_datetime(df['datetime'])
df = df.sort_values('datetime').reset_index(drop=True)

print(f"总行数: {len(df)}")
print(f"时间范围: {df.iloc[0]['datetime']} ~ {df.iloc[-1]['datetime']}")
print(f"覆盖天数: {df['datetime'].dt.date.nunique()}")

# 时间间隔分析
diffs = df['datetime'].diff().dropna()
print(f"\n时间间隔统计:")
print(f"  最小: {diffs.min()}")
print(f"  最大: {diffs.max()}")
print(f"  中位数: {diffs.median()}")

# 价格范围
print(f"\n价格范围: {df['close'].min():.2f} ~ {df['close'].max():.2f}")
print(f"成交量范围: {df['volume'].min():.0f} ~ {df['volume'].max():.0f}")

# 前 5 根
print(f"\n前 5 根:")
print(df[['datetime','open','high','low','close','volume']].head(5).to_string())

# 后 5 根
print(f"\n后 5 根:")
print(df[['datetime','open','high','low','close','volume']].tail(5).to_string())

# 检查是否有重复
dup = df.duplicated(subset=['datetime']).sum()
print(f"\n重复行: {dup}")

# 检查 NaN
nan_count = df[['open','high','low','close','volume']].isna().sum().sum()
print(f"NaN 值: {nan_count}")

# 每月数据量
print(f"\n每月数据量:")
monthly = df.groupby(df['datetime'].dt.to_period('M')).size()
for period, count in monthly.items():
    print(f"  {period}: {count} 根")
