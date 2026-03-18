"""测试天勤最大数据量"""
from tqsdk import TqApi, TqAuth
import pandas as pd

print("=== 连接天勤 ===")
api = TqApi(auth=TqAuth("17340696348", "@Cmx1454697261"))

try:
    # 测试不同数量
    for count in [20000, 15000, 12000, 10000, 9000]:
        print(f"\n尝试拉取 {count} 根 30 分钟线...")
        try:
            klines = api.get_kline_serial("KQ.m@SHFE.au", duration_seconds=1800, data_length=count)
            df = klines.copy()
            df['datetime'] = pd.to_datetime(df['datetime'], unit='ns')
            print(f"  [OK] 获取 {len(df)} 根")
            print(f"  时间: {df.iloc[0]['datetime']} ~ {df.iloc[-1]['datetime']}")
            
            if len(df) > 8000:
                df.to_csv(f'E:/quant-trading-mvp/data/tq_au_30m_{len(df)}.csv', index=False)
                print(f"  已保存: data/tq_au_30m_{len(df)}.csv")
            break
        except Exception as e:
            print(f"  [FAIL] {str(e)[:100]}")
    
    # 测试日线
    print("\n尝试拉取日线...")
    for count in [5000, 3000, 2000]:
        try:
            klines_daily = api.get_kline_serial("KQ.m@SHFE.au", duration_seconds=86400, data_length=count)
            df_daily = klines_daily.copy()
            df_daily['datetime'] = pd.to_datetime(df_daily['datetime'], unit='ns')
            print(f"  [OK] 获取 {len(df_daily)} 根日线")
            print(f"  时间: {df_daily.iloc[0]['datetime']} ~ {df_daily.iloc[-1]['datetime']}")
            
            if len(df_daily) > 800:
                df_daily.to_csv(f'E:/quant-trading-mvp/data/tq_au_daily_{len(df_daily)}.csv', index=False)
                print(f"  已保存: data/tq_au_daily_{len(df_daily)}.csv")
            break
        except Exception as e:
            print(f"  [FAIL] {str(e)[:100]}")

finally:
    api.close()
    print("\n=== 连接已关闭 ===")
