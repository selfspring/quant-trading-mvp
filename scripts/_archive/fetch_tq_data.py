"""从天勤获取黄金期货历史数据"""
from tqsdk import TqApi, TqAuth
import pandas as pd

print("=== 连接天勤 ===")
api = TqApi(auth=TqAuth("17340696348", "@Cmx1454697261"))

try:
    # 1. 获取黄金主力合约日线（最近 2 年）
    print("\n=== 黄金主力合约日线 ===")
    klines_daily = api.get_kline_serial("KQ.m@SHFE.au", duration_seconds=86400, data_length=800)
    df_daily = klines_daily.copy()
    print(f"行数: {len(df_daily)}")
    print(f"列名: {list(df_daily.columns)}")
    print(f"\n最早: {df_daily.iloc[0]['datetime']}")
    print(f"最新: {df_daily.iloc[-1]['datetime']}")
    print("\n最近 5 天:")
    print(df_daily[['datetime', 'open', 'high', 'low', 'close', 'volume']].tail(5))
    
    # 2. 获取 au2606 合约日线
    print("\n=== au2606 合约日线 ===")
    klines_2606 = api.get_kline_serial("SHFE.au2606", duration_seconds=86400, data_length=300)
    df_2606 = klines_2606.copy()
    print(f"行数: {len(df_2606)}")
    print(f"时间范围: {df_2606.iloc[0]['datetime']} ~ {df_2606.iloc[-1]['datetime']}")
    print(df_2606[['datetime', 'open', 'high', 'low', 'close', 'volume']].tail(5))
    
    # 3. 获取 30 分钟线（最近 1 个月）
    print("\n=== 主力合约 30 分钟线 ===")
    klines_30m = api.get_kline_serial("KQ.m@SHFE.au", duration_seconds=1800, data_length=1000)
    df_30m = klines_30m.copy()
    print(f"行数: {len(df_30m)}")
    print(f"时间范围: {df_30m.iloc[0]['datetime']} ~ {df_30m.iloc[-1]['datetime']}")
    print(df_30m[['datetime', 'open', 'high', 'low', 'close', 'volume']].tail(5))
    
    # 4. 保存到 CSV（可选）
    print("\n=== 保存数据 ===")
    df_daily.to_csv('E:/quant-trading-mvp/data/tq_au_daily.csv', index=False)
    print("日线数据已保存: data/tq_au_daily.csv")
    
    df_30m.to_csv('E:/quant-trading-mvp/data/tq_au_30m.csv', index=False)
    print("30分钟线已保存: data/tq_au_30m.csv")
    
finally:
    api.close()
    print("\n=== 连接已关闭 ===")
