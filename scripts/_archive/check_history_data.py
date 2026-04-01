"""拉取真实历史数据并查看可用量"""
import akshare as ak
import pandas as pd

# 1. 日线数据
print("=== 日线数据 ===")
try:
    df_daily = ak.futures_zh_daily_sina(symbol="au2606")
    if df_daily is not None:
        print(f"行数: {len(df_daily)}")
        print(f"时间范围: {df_daily.iloc[0]['date']} ~ {df_daily.iloc[-1]['date']}")
        print(df_daily.tail(5))
    else:
        print("无数据")
except Exception as e:
    print(f"失败: {e}")

# 2. 分钟线数据
print("\n=== 1分钟线数据 ===")
try:
    df_1m = ak.futures_zh_minute_sina(symbol="au2606", period="1")
    if df_1m is not None:
        print(f"行数: {len(df_1m)}")
        print(f"列名: {list(df_1m.columns)}")
        print(df_1m.head(3))
        print("...")
        print(df_1m.tail(3))
    else:
        print("无数据")
except Exception as e:
    print(f"失败: {e}")

# 3. 30分钟线
print("\n=== 30分钟线数据 ===")
try:
    df_30m = ak.futures_zh_minute_sina(symbol="au2606", period="30")
    if df_30m is not None:
        print(f"行数: {len(df_30m)}")
        print(df_30m.tail(5))
    else:
        print("无数据")
except Exception as e:
    print(f"失败: {e}")

# 4. 尝试主力合约
print("\n=== 主力合约日线 ===")
try:
    df_main = ak.futures_main_sina(symbol="AU0", start_date="20240101", end_date="20260316")
    if df_main is not None:
        print(f"行数: {len(df_main)}")
        print(f"时间范围: {df_main.iloc[0]['日期']} ~ {df_main.iloc[-1]['日期']}")
    else:
        print("无数据")
except Exception as e:
    print(f"失败: {e}")
