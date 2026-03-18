"""从天勤获取 au2606 1分钟数据，测试不同参数"""
from tqsdk import TqApi, TqAuth
import time

auth = TqAuth("17340696348", "@Cmx1454697261")

try:
    api = TqApi(auth=auth)
    
    # 尝试不同数量
    for count in [500, 1000, 3000, 5000, 8000, 10000]:
        try:
            klines = api.get_kline_serial("SHFE.au2606", 60, data_length=count)
            actual = len(klines)
            first = klines.iloc[0]['datetime'] if actual > 0 else 'N/A'
            last = klines.iloc[-1]['datetime'] if actual > 0 else 'N/A'
            print(f"请求 {count:>6} 根 1m -> 实际 {actual:>6} 根 | {first} ~ {last}")
        except Exception as e:
            print(f"请求 {count:>6} 根 1m -> 错误: {e}")
    
    # 也试试 au_main
    print("\n=== au_main ===")
    for count in [5000, 10000]:
        try:
            klines = api.get_kline_serial("KQ.m@SHFE.au", 60, data_length=count)
            actual = len(klines)
            first = klines.iloc[0]['datetime'] if actual > 0 else 'N/A'
            last = klines.iloc[-1]['datetime'] if actual > 0 else 'N/A'
            print(f"请求 {count:>6} 根 1m -> 实际 {actual:>6} 根 | {first} ~ {last}")
        except Exception as e:
            print(f"请求 {count:>6} 根 1m -> 错误: {e}")
    
    api.close()
except Exception as e:
    print(f"连接失败: {e}")
