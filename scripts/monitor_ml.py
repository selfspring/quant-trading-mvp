"""实时查看 ML 预测和置信度"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from quant.signal_generator.ml_predictor import MLPredictor
from quant.common.config import config
from quant.common.db import db_engine

def get_latest_prediction():
    # 从数据库读取最新 K 线
    with db_engine(config) as engine:
        df = pd.read_sql("SELECT time as timestamp, open, high, low, close, volume FROM kline_data WHERE symbol='au2606' AND interval='1m' ORDER BY time DESC LIMIT 100", engine)
    
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
    
    # ML 预测
    predictor = MLPredictor()
    result = predictor.predict(df)
    
    return result

if __name__ == "__main__":
    result = get_latest_prediction()
    
    print("=" * 50)
    print("ML 预测实时监控")
    print("=" * 50)
    print(f"预测收益率: {result['prediction']*100:+.2f}%")
    print(f"置信度:     {result['confidence']:.2f}")
    print(f"方向:       {result['direction']}")
    print(f"信号:       {result['signal']}")
    print("-" * 50)
    
    # 判断是否会交易
    threshold = 0.65
    if result['confidence'] >= threshold:
        print(f"✓ 置信度 >= {threshold}，会发单")
    else:
        print(f"✗ 置信度 < {threshold}，不会发单")
    
    print("=" * 50)
