"""分析 ML 预测值的合理性"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
from quant.signal_generator.ml_predictor import MLPredictor

# 1. 从数据库读取最新 K 线
import psycopg2
conn = psycopg2.connect(host='localhost', port=5432, dbname='quant_trading', user='postgres', password='@Cmx1454697261')
df = pd.read_sql("SELECT time as timestamp, open, high, low, close, volume FROM kline_data WHERE symbol='au2606' AND interval='1m' ORDER BY time DESC LIMIT 100", conn)
conn.close()

if len(df) < 60:
    print("数据库 K 线不足，使用 AkShare")
    import akshare as ak
    df = ak.futures_zh_minute_sina(symbol='au2606', period="1")
    df = df.tail(100).copy()
    df.columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume', 'hold']
    df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
    for col in ['open', 'high', 'low', 'close', 'volume']:
        df[col] = pd.to_numeric(df[col], errors='coerce')

df = df.sort_values('timestamp').reset_index(drop=True)

# 2. ML 预测
predictor = MLPredictor()
result = predictor.predict(df)

print("=== ML 预测结果 ===")
print(f"预测值: {result['prediction']:.6f} ({result['prediction']*100:.2f}%)")
print(f"置信度: {result['confidence']:.6f}")
print(f"方向: {result['direction']}")

# 3. 计算实际历史波动
print("\n=== 历史波动分析 ===")
df['returns'] = df['close'].pct_change()
print(f"最近 100 根 K 线收益率统计:")
print(f"  均值: {df['returns'].mean():.6f} ({df['returns'].mean()*100:.2f}%)")
print(f"  标准差: {df['returns'].std():.6f} ({df['returns'].std()*100:.2f}%)")
print(f"  最小值: {df['returns'].min():.6f} ({df['returns'].min()*100:.2f}%)")
print(f"  最大值: {df['returns'].max():.6f} ({df['returns'].max()*100:.2f}%)")

# 4. 计算未来 N 根 K 线的累计收益率（模拟预测目标）
print("\n=== 未来 N 根 K 线累计收益率 ===")
for n in [2, 5, 10, 30, 60]:
    if len(df) > n:
        future_returns = []
        for i in range(len(df) - n):
            ret = (df.iloc[i+n]['close'] - df.iloc[i]['close']) / df.iloc[i]['close']
            future_returns.append(ret)
        future_returns = np.array(future_returns)
        print(f"未来 {n} 根 K 线:")
        print(f"  均值: {future_returns.mean():.6f} ({future_returns.mean()*100:.2f}%)")
        print(f"  标准差: {future_returns.std():.6f} ({future_returns.std()*100:.2f}%)")
        print(f"  最大值: {future_returns.max():.6f} ({future_returns.max()*100:.2f}%)")

# 5. 判断合理性
print("\n=== 合理性分析 ===")
pred_pct = result['prediction'] * 100
if pred_pct > 5:
    print(f"⚠️ 预测值 {pred_pct:.2f}% 偏高")
    print(f"   1 分钟 K 线单根涨跌通常在 ±0.5% 以内")
    print(f"   预测 13% 相当于连续大涨，不太现实")
elif pred_pct > 2:
    print(f"⚠️ 预测值 {pred_pct:.2f}% 偏高但可能")
    print(f"   如果是预测未来 60 分钟累计收益，勉强合理")
elif pred_pct > 0.5:
    print(f"✓ 预测值 {pred_pct:.2f}% 合理")
else:
    print(f"✓ 预测值 {pred_pct:.2f}% 偏保守")

print(f"\n当前置信度 {result['confidence']:.2f}，阈值 0.65")
if result['confidence'] < 0.65:
    print("✓ 风控会拦截，不会发单")
else:
    print("⚠️ 风控会通过，会发单")
