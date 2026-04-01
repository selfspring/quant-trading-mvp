"""从天勤拉取更多历史 30 分钟线"""
from tqsdk import TqApi, TqAuth
import pandas as pd

print("=== 连接天勤 ===")
api = TqApi(auth=TqAuth("17340696348", "@Cmx1454697261"))

try:
    # 尝试拉取最大量的 30 分钟线
    for count in [8000, 5000, 3000, 2000]:
        print(f"\n尝试拉取 {count} 根 30 分钟线...")
        try:
            klines = api.get_kline_serial("KQ.m@SHFE.au", duration_seconds=1800, data_length=count)
            df = klines.copy()
            df['datetime'] = pd.to_datetime(df['datetime'], unit='ns')
            print(f"  [OK] 获取 {len(df)} 根")
            print(f"  时间: {df.iloc[0]['datetime']} ~ {df.iloc[-1]['datetime']}")
            
            # 保存
            df.to_csv(f'E:/quant-trading-mvp/data/tq_au_30m_{len(df)}.csv', index=False)
            print(f"  已保存: data/tq_au_30m_{len(df)}.csv")
            break
        except Exception as e:
            print(f"  [FAIL] {e}")
    
    # 也拉 1 分钟线看看能拉多少
    print("\n尝试拉取 1 分钟线...")
    for count in [8000, 5000, 3000]:
        try:
            klines_1m = api.get_kline_serial("KQ.m@SHFE.au", duration_seconds=60, data_length=count)
            df_1m = klines_1m.copy()
            df_1m['datetime'] = pd.to_datetime(df_1m['datetime'], unit='ns')
            print(f"  [OK] 获取 {len(df_1m)} 根 1 分钟线")
            print(f"  时间: {df_1m.iloc[0]['datetime']} ~ {df_1m.iloc[-1]['datetime']}")
            df_1m.to_csv(f'E:/quant-trading-mvp/data/tq_au_1m_{len(df_1m)}.csv', index=False)
            print(f"  已保存: data/tq_au_1m_{len(df_1m)}.csv")
            break
        except Exception as e:
            print(f"  [FAIL] {e}")

finally:
    api.close()
    print("\n=== 连接已关闭 ===")
