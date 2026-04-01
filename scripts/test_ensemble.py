"""测试集成预测器"""
import sys
sys.path.insert(0, 'E:/quant-trading-mvp')

import pandas as pd
from quant.common.config import config
from quant.common.db import db_engine
from quant.signal_generator.ensemble_predictor import EnsemblePredictor

print("=" * 60)
print("测试 EnsemblePredictor")
print("=" * 60)

# 初始化预测器
ep = EnsemblePredictor()
print("\nEnsemblePredictor 初始化成功")

# 加载测试数据
with db_engine(config) as engine:
    df = pd.read_sql("""
        SELECT time as timestamp, open, high, low, close, volume, open_interest
        FROM kline_data
        WHERE symbol='au_main' AND interval='30m'
        ORDER BY time DESC
        LIMIT 100
    """, engine)

df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.iloc[::-1].reset_index(drop=True)

print(f"加载 {len(df)} 根 K 线数据")

# 测试预测
result = ep.predict(df)
print(f"\n预测结果:")
print(f"  signal: {result['signal']}")
print(f"  confidence: {result['confidence']:.4f}")
print(f"  predicted_return: {result['predicted_return']:.8f}")

print("\n" + "=" * 60)
print("测试通过!")
print("=" * 60)
