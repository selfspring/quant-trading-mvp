"""
市场状态识别测试脚本
从数据库读取 au_main 30m 数据，运行状态识别，打印最近 10 根的状态结果
"""
import sys
import pandas as pd

# 添加项目路径
sys.path.insert(0, 'E:/quant-trading-mvp')

from quant.common.config import config
from quant.common.db import db_engine
from quant.signal_generator.market_regime import MarketRegimeDetector


def main():
    print("=" * 60)
    print("市场状态识别测试")
    print("=" * 60)
    
    # 1. 从数据库读取数据
    print("\n[1] 从数据库读取 au_main 30m 数据...")
    
    # 读取最近 200 根 K 线（足够计算指标和训练 HMM）
    # 注意：表名是 kline_data，字段是 time 和 interval
    query = """
    SELECT time as timestamp, open, high, low, close, volume, open_interest
    FROM kline_data
    WHERE symbol = 'au_main' AND interval = '30m'
    ORDER BY time DESC
    LIMIT 200
    """
    
    with db_engine(config) as engine:
        df = pd.read_sql_query(query, engine)
    
    if df.empty:
        print("错误：无法从数据库读取数据")
        return
    
    # 按时间正序排列
    df = df.sort_values('timestamp').reset_index(drop=True)
    
    print(f"读取到 {len(df)} 根 K 线")
    print(f"时间范围：{df['timestamp'].iloc[0]} 至 {df['timestamp'].iloc[-1]}")
    
    # 2. 生成技术指标
    print("\n[2] 生成技术指标...")
    from quant.signal_generator.feature_engineer import FeatureEngineer
    
    fe = FeatureEngineer()
    df_features = fe.generate_features(df)
    
    print(f"生成特征后数据行数：{len(df_features)}")
    print(f"可用指标：ATR={df_features['atr'].iloc[-1]:.4f}, "
          f"ATR Ratio={df_features['atr_ratio'].iloc[-1]:.5f}")
    
    # 3. 创建市场状态检测器
    print("\n[3] 初始化市场状态检测器...")
    detector = MarketRegimeDetector()
    
    # 4. 对最近 10 根 K 线进行状态识别
    print("\n[4] 运行状态识别（最近 10 根 K 线）...")
    print("-" * 60)
    
    results = []
    for i in range(-10, 0):
        # 取到当前行为止的所有数据用于检测
        df_slice = df_features.iloc[:len(df_features)+i+1].copy()
        
        if len(df_slice) < 60:
            # 数据不足，跳过
            continue
        
        result = detector.detect(df_slice)
        result['timestamp'] = df_features.iloc[i]['timestamp']
        result['close'] = df_features.iloc[i]['close']
        results.append(result)
    
    # 5. 打印结果
    print(f"\n{'时间':<20} {'状态':<10} {'规则':<10} {'HMM':<10} {'置信度':<8} {'ADX':<8} {'ATR%':<8}")
    print("-" * 60)
    
    for r in results:
        timestamp = str(r['timestamp'])[:19]  # 截取日期部分
        print(f"{timestamp:<20} "
              f"{r['regime']:<10} "
              f"{r['regime_rule']:<10} "
              f"{r['regime_hmm']:<10} "
              f"{r['confidence']:<8.3f} "
              f"{r['adx']:<8.3f} "
              f"{r['atr_ratio']*100:<8.3f}%")
    
    print("-" * 60)
    
    # 6. 打印最新状态的建议参数
    latest = results[-1]
    print(f"\n最新市场状态：{latest['regime'].upper()}")
    print(f"\n策略参数建议:")
    params = latest['params']
    print(f"  - 置信度提升：{params.get('confidence_boost', 0):.1%}")
    print(f"  - 止损倍率：{params.get('stop_loss_multiplier', 1):.1f}x")
    print(f"  - 开仓置信度阈值：{params.get('confidence_threshold', 0.7):.1%}")
    print(f"  - 暂停交易：{'是' if params.get('pause_trading', False) else '否'}")
    print(f"  - 原因：{params.get('reason', 'N/A')}")
    
    # 7. 统计最近 10 根的状态分布
    print(f"\n状态分布统计:")
    regime_counts = {}
    for r in results:
        regime = r['regime']
        regime_counts[regime] = regime_counts.get(regime, 0) + 1
    
    for regime, count in regime_counts.items():
        print(f"  - {regime}: {count} 根 ({count/len(results)*100:.1f}%)")
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == '__main__':
    main()
