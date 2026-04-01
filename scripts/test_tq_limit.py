"""测试天勤极限数据量"""
from tqsdk import TqApi, TqAuth
import pandas as pd

print("=== 连接天勤 ===")
api = TqApi(auth=TqAuth("17340696348", "@Cmx1454697261"))

try:
    # 测试更大的数量
    for count in [50000, 30000, 25000, 20000, 15000]:
        print(f"\n尝试拉取 {count} 根 30 分钟线...")
        try:
            klines = api.get_kline_serial("KQ.m@SHFE.au", duration_seconds=1800, data_length=count)
            df = klines.copy()
            df['datetime'] = pd.to_datetime(df['datetime'], unit='ns')
            actual_count = len(df)
            print(f"  [OK] 实际获取 {actual_count} 根")
            print(f"  时间: {df.iloc[0]['datetime']} ~ {df.iloc[-1]['datetime']}")
            
            # 保存
            df.to_csv(f'E:/quant-trading-mvp/data/tq_au_30m_{actual_count}.csv', index=False)
            print(f"  已保存: data/tq_au_30m_{actual_count}.csv")
            
            # 如果实际数量小于请求数量，说明到极限了
            if actual_count < count:
                print(f"  [INFO] 已达到数据极限（请求 {count}，实际 {actual_count}）")
                break
        except Exception as e:
            print(f"  [FAIL] {str(e)[:150]}")
    
    # 测试 1 分钟线极限
    print("\n尝试拉取更多 1 分钟线...")
    for count in [20000, 15000, 12000, 10000]:
        try:
            klines_1m = api.get_kline_serial("KQ.m@SHFE.au", duration_seconds=60, data_length=count)
            df_1m = klines_1m.copy()
            df_1m['datetime'] = pd.to_datetime(df_1m['datetime'], unit='ns')
            actual_count = len(df_1m)
            print(f"  [OK] 实际获取 {actual_count} 根 1 分钟线")
            print(f"  时间: {df_1m.iloc[0]['datetime']} ~ {df_1m.iloc[-1]['datetime']}")
            
            if actual_count > 8000:
                df_1m.to_csv(f'E:/quant-trading-mvp/data/tq_au_1m_{actual_count}.csv', index=False)
                print(f"  已保存: data/tq_au_1m_{actual_count}.csv")
            
            if actual_count < count:
                print(f"  [INFO] 已达到数据极限（请求 {count}，实际 {actual_count}）")
                break
        except Exception as e:
            print(f"  [FAIL] {str(e)[:150]}")

finally:
    api.close()
    print("\n=== 连接已关闭 ===")
