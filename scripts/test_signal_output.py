"""
测试脚本：展示信号生成层的完整输出
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from quant.signal_generator.ml_predictor import MLPredictor
from quant.risk_executor.signal_processor import SignalProcessor
from quant.common.config import config

def main():
    print("=" * 80)
    print("信号生成层输出测试")
    print("=" * 80)
    
    # 1. 加载历史数据
    print("\n1. 加载历史 K 线数据...")
    df = pd.read_csv('data/au2604_1min.csv')
    df['datetime'] = pd.to_datetime(df['datetime'])
    print(f"   数据行数: {len(df)}")
    print(f"   时间范围: {df['datetime'].min()} ~ {df['datetime'].max()}")
    
    # 2. ML 预测
    print("\n2. ML 预测器输出:")
    print("-" * 80)
    predictor = MLPredictor()
    ml_signal = predictor.predict(df)
    
    print(f"   原始预测值 (prediction):  {ml_signal['prediction']:.6f}")
    print(f"   置信度 (confidence):       {ml_signal['confidence']:.4f}")
    print(f"   信号方向 (signal):         {ml_signal['signal']} ({'做多' if ml_signal['signal'] == 1 else '做空'})")
    
    # 3. 信号处理器
    print("\n3. 信号处理器输出:")
    print("-" * 80)
    processor = SignalProcessor(config)
    trade_intent = processor.process_signal(ml_signal)
    
    if trade_intent is None:
        print("   ⚠️ 置信度不足，信号被过滤")
        print(f"   原因: confidence={ml_signal['confidence']:.4f} < threshold={config.strategy.confidence_threshold}")
    else:
        print(f"   交易方向 (direction):      {trade_intent['direction']}")
        print(f"   交易数量 (quantity):       {trade_intent['quantity']}")
        print(f"   合约代码 (symbol):         {trade_intent['symbol']}")
        print(f"   置信度 (confidence):       {trade_intent['confidence']:.4f}")
        print(f"   原始预测 (prediction):     {trade_intent['prediction']:.6f}")
    
    # 4. 阈值分析
    print("\n4. 阈值分析:")
    print("-" * 80)
    print(f"   当前置信度阈值: {config.strategy.confidence_threshold}")
    print(f"   ML 预测置信度:  {ml_signal['confidence']:.4f}")
    print(f"   是否通过阈值:   {'✅ 是' if ml_signal['confidence'] >= config.strategy.confidence_threshold else '❌ 否'}")
    
    # 5. 置信度计算公式
    print("\n5. 置信度计算公式:")
    print("-" * 80)
    print(f"   confidence = min(abs(prediction) * 50, 1.0)")
    print(f"   confidence = min(abs({ml_signal['prediction']:.6f}) * 50, 1.0)")
    print(f"   confidence = min({abs(ml_signal['prediction']) * 50:.4f}, 1.0)")
    print(f"   confidence = {ml_signal['confidence']:.4f}")
    
    # 6. 建议
    print("\n6. 建议:")
    print("-" * 80)
    if ml_signal['confidence'] < config.strategy.confidence_threshold:
        gap = config.strategy.confidence_threshold - ml_signal['confidence']
        print(f"   当前置信度不足，差距: {gap:.4f}")
        print(f"   需要预测值至少达到: {config.strategy.confidence_threshold / 50:.6f}")
        print(f"   当前预测值: {ml_signal['prediction']:.6f}")
        print("\n   可能的解决方案:")
        print("   - 降低置信度阈值 (当前 0.65)")
        print("   - 改进模型训练 (增加特征、调整参数)")
        print("   - 使用更长的训练数据")
    else:
        print("   ✅ 置信度充足，信号可以通过")
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    main()
