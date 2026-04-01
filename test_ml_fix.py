"""测试 ML 预测修复"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from quant.signal_generator.ml_predictor import MLPredictor
from quant.risk_executor.signal_processor import SignalProcessor
from quant.common.config import config
import pandas as pd
import numpy as np

# 生成测试数据
np.random.seed(42)
dates = pd.date_range('2024-01-01', periods=100, freq='1min')
df = pd.DataFrame({
    'timestamp': dates,
    'open': 500 + np.random.randn(100).cumsum(),
    'high': 502 + np.random.randn(100).cumsum(),
    'low': 498 + np.random.randn(100).cumsum(),
    'close': 500 + np.random.randn(100).cumsum(),
    'volume': np.random.randint(100, 1000, 100)
})

print("=" * 60)
print("测试 ML 预测修复")
print("=" * 60)

try:
    # 测试预测
    predictor = MLPredictor()
    result = predictor.predict(df)
    
    print(f"\n预测结果:")
    print(f"  prediction: {result['prediction']:.6f}")
    print(f"  confidence: {result['confidence']:.4f}")
    print(f"  signal: {result['signal']}")
    print(f"  direction: {result['direction']}")
    
    # 测试信号处理
    processor = SignalProcessor(config)
    intent = processor.process_signal(result)
    
    print(f"\n信号处理:")
    if intent:
        print(f"  ✅ 生成交易意图: {intent}")
    else:
        print(f"  ❌ 无交易意图（置信度不足或 signal=0）")
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)
    
except Exception as e:
    print(f"\n❌ 错误: {e}")
    import traceback
    traceback.print_exc()
