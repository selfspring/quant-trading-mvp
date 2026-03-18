"""用 AkShare 获取黄金期货主力合约历史数据"""
import akshare as ak
import pandas as pd
import os

print("=== 从 AkShare 获取黄金期货数据 ===\n")

# 1. 主力合约日线（2年+）
print("1. 主力合约日线（AU0）...")
df_main = ak.futures_main_sina(symbol="AU0", start_date="20200101", end_date="20260316")
print(f"   行数: {len(df_main)}")
print(f"   时间范围: {df_main.iloc[0]['日期']} ~ {df_main.iloc[-1]['日期']}")
print(f"   列名: {list(df_main.columns)}")
print("\n   最近 5 天:")
print(df_main[['日期', '开盘价', '最高价', '最低价', '收盘价', '成交量']].tail(5))

# 2. au2606 合约日线
print("\n2. au2606 合约日线...")
df_2606 = ak.futures_zh_daily_sina(symbol="au2606")
print(f"   行数: {len(df_2606)}")
print(f"   时间范围: {df_2606.iloc[0]['date']} ~ {df_2606.iloc[-1]['date']}")
print("\n   最近 5 天:")
print(df_2606[['date', 'open', 'high', 'low', 'close', 'volume']].tail(5))

# 3. 保存数据
print("\n3. 保存数据...")
os.makedirs('E:/quant-trading-mvp/data', exist_ok=True)

# 主力合约数据（用于训练）
df_main_clean = df_main.rename(columns={
    '日期': 'date',
    '开盘价': 'open',
    '最高价': 'high',
    '最低价': 'low',
    '收盘价': 'close',
    '成交量': 'volume',
    '持仓量': 'open_interest'
})
df_main_clean.to_csv('E:/quant-trading-mvp/data/au_main_daily.csv', index=False)
print(f"   主力合约日线已保存: data/au_main_daily.csv ({len(df_main_clean)} 行)")

# au2606 数据
df_2606.to_csv('E:/quant-trading-mvp/data/au2606_daily.csv', index=False)
print(f"   au2606 日线已保存: data/au2606_daily.csv ({len(df_2606)} 行)")

print("\n=== 数据获取完成 ===")
print(f"可用于训练的数据: {len(df_main_clean)} 天日线")
print("建议：用主力合约数据训练模型，覆盖时间更长，数据更连续")
