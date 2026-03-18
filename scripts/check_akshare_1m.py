"""检查 AkShare 能拿到多少 au2606 数据"""
import akshare as ak

# 1. 期货分钟线
print("=== AkShare 期货分钟线 ===")
for period in ["1", "5", "15", "30", "60"]:
    try:
        df = ak.futures_zh_minute_sina(symbol="au2606", period=period)
        if df is not None and len(df) > 0:
            print(f"  {period}m: {len(df)} 根 | {df.iloc[0]['datetime']} ~ {df.iloc[-1]['datetime']}")
        else:
            print(f"  {period}m: 无数据")
    except Exception as e:
        print(f"  {period}m: 错误 - {e}")

# 2. 主力合约
print("\n=== AkShare 主力合约 ===")
for period in ["1", "5", "15", "30", "60"]:
    try:
        df = ak.futures_zh_minute_sina(symbol="au0", period=period)
        if df is not None and len(df) > 0:
            print(f"  {period}m: {len(df)} 根 | {df.iloc[0]['datetime']} ~ {df.iloc[-1]['datetime']}")
        else:
            print(f"  {period}m: 无数据")
    except Exception as e:
        print(f"  {period}m: 错误 - {e}")

# 3. 日线
print("\n=== AkShare 日线 ===")
try:
    df = ak.futures_main_sina(symbol="au0", start_date="20200101", end_date="20260317")
    if df is not None:
        print(f"  日线: {len(df)} 根 | {df.iloc[0]['date']} ~ {df.iloc[-1]['date']}")
except Exception as e:
    print(f"  日线: 错误 - {e}")
