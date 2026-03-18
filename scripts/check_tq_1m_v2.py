"""从天勤获取 au2606 1分钟数据，显示可读时间"""
from tqsdk import TqApi, TqAuth
import pandas as pd

auth = TqAuth("17340696348", "@Cmx1454697261")

try:
    api = TqApi(auth=auth)
    
    klines = api.get_kline_serial("SHFE.au2606", 60, data_length=10000)
    actual = len(klines)
    
    # 转换时间
    klines['dt'] = pd.to_datetime(klines['datetime'], unit='ns', utc=True).dt.tz_convert('Asia/Shanghai')
    
    print(f"au2606 1m: {actual} 根")
    print(f"起始: {klines['dt'].iloc[0]}")
    print(f"结束: {klines['dt'].iloc[-1]}")
    print(f"\n最新5根:")
    for _, row in klines.tail(5).iterrows():
        print(f"  {row['dt']}  O:{row['open']:.2f} H:{row['high']:.2f} L:{row['low']:.2f} C:{row['close']:.2f} V:{int(row['volume'])}")
    
    # au_main
    klines2 = api.get_kline_serial("KQ.m@SHFE.au", 60, data_length=10000)
    klines2['dt'] = pd.to_datetime(klines2['datetime'], unit='ns', utc=True).dt.tz_convert('Asia/Shanghai')
    print(f"\nau_main 1m: {len(klines2)} 根")
    print(f"起始: {klines2['dt'].iloc[0]}")
    print(f"结束: {klines2['dt'].iloc[-1]}")
    
    api.close()
except Exception as e:
    print(f"错误: {e}")
