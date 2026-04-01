import sys
sys.path.insert(0, 'E:/quant-trading-mvp')
import numpy as np
import pandas as pd
from quant.common.config import config
from quant.common.db import db_engine
from quant.factors.factor_evaluator import evaluate_factor
import json
from datetime import datetime

# Load data
with db_engine(config) as engine:
    df = pd.read_sql("""
        SELECT time as timestamp, open, high, low, close, volume, open_interest
        FROM kline_data WHERE symbol='au_main' AND interval='30m'
        ORDER BY time
    """, engine)
df['timestamp'] = pd.to_datetime(df['timestamp'])
print(f"Data loaded: {len(df)} rows, from {df.timestamp.min()} to {df.timestamp.max()}")

def test_and_log(name, description, source, factor_func):
    """Test a factor and log results"""
    factor_values = factor_func(df)
    nan_ratio = factor_values.isna().mean()
    print(f"\n=== {name} ===")
    print(f"NaN ratio: {nan_ratio:.2%}")
    
    results = {}
    for h in [4, 8, 16]:
        fwd = np.log(df['close'].shift(-h) / df['close'])
        r = evaluate_factor(factor_values, fwd, name=name)
        results[f"{h*30//60}h"] = r
        ic = r.get('rank_ic', 0)
        ir = r.get('ir', 0)
        da = r.get('direction_acc', 0)
        print(f"  {h*30//60}h: IC={ic:.4f}, IR={ir:.4f}, Dir={da:.4f}")
    
    avg_ic = np.mean([abs(results[k].get('rank_ic', 0)) for k in results if results[k].get('valid')])
    effective = avg_ic > 0.02
    
    def to_native(obj):
        if isinstance(obj, (np.integer,)): return int(obj)
        if isinstance(obj, (np.floating,)): return float(obj)
        if isinstance(obj, (np.bool_,)): return bool(obj)
        return obj

    record = {
        'timestamp': datetime.now().isoformat(),
        'name': name,
        'description': description,
        'source': source,
        'avg_abs_ic': round(float(avg_ic), 4),
        'results': {k: {kk: to_native(round(float(vv), 4)) if isinstance(vv, (float, np.floating)) else to_native(vv) 
                        for kk, vv in v.items() if kk != 'valid'} 
                   for k, v in results.items()},
        'effective': bool(effective),
    }
    with open('E:/quant-trading-mvp/data/factor_discovery_log.jsonl', 'a', encoding='utf-8') as f:
        f.write(json.dumps(record, ensure_ascii=False) + '\n')
    
    print(f"Avg |IC|: {avg_ic:.4f} {'** EFFECTIVE **' if effective else ''}")
    return avg_ic, effective, factor_func

# ============================================================
# Factor 1: Volume Shock (成交量冲击因子)
# ============================================================
def volume_shock(df):
    vol_ma = df['volume'].rolling(20).mean()
    vol_std = df['volume'].rolling(20).std()
    shock = (df['volume'] - vol_ma) / (vol_std + 1e-8)
    price_dir = df['close'] - df['open']
    return shock * np.sign(price_dir)

test_and_log('volume_shock', '成交量冲击因子：成交量z-score乘以价格方向', 
             'quant knowledge - volume anomaly', volume_shock)

# ============================================================
# Factor 2: OI Acceleration (持仓量加速度)
# ============================================================
def oi_acceleration(df):
    oi_change = df['open_interest'].diff()
    oi_accel = oi_change.diff()
    # normalize
    return oi_accel / (df['open_interest'].rolling(20).std() + 1e-8)

test_and_log('oi_acceleration', '持仓量加速度：持仓量变化的变化率，归一化',
             'quant knowledge - OI derivative', oi_acceleration)

# ============================================================
# Factor 3: Price Range Ratio (价格区间比)
# ============================================================
def price_range_ratio(df):
    # 当前K线实体占整个振幅的比例
    body = abs(df['close'] - df['open'])
    shadow = df['high'] - df['low']
    ratio = body / (shadow + 1e-8)
    # 结合方向
    direction = np.sign(df['close'] - df['open'])
    return ratio * direction

test_and_log('price_range_ratio', '价格区间比：K线实体/振幅，带方向',
             'quant knowledge - candlestick pattern', price_range_ratio)

# ============================================================
# Factor 4: Volume-OI Divergence (量仓背离)
# ============================================================
def volume_oi_divergence(df):
    vol_z = (df['volume'] - df['volume'].rolling(20).mean()) / (df['volume'].rolling(20).std() + 1e-8)
    oi_z = (df['open_interest'].diff() - df['open_interest'].diff().rolling(20).mean()) / (df['open_interest'].diff().rolling(20).std() + 1e-8)
    # 量增仓减或量减仓增 = 背离
    return vol_z - oi_z

test_and_log('volume_oi_divergence', '量仓背离：成交量z-score与持仓量变化z-score的差',
             'quant knowledge - volume OI divergence', volume_oi_divergence)

# ============================================================
# Factor 5: Intraday Momentum (日内动量)
# ============================================================
def intraday_momentum(df):
    # 开盘到收盘的动量，相对于振幅归一化
    move = (df['close'] - df['open']) / (df['high'] - df['low'] + 1e-8)
    # 用EMA平滑
    return move.ewm(span=10).mean()

test_and_log('intraday_momentum', '日内动量：(close-open)/(high-low)的EMA平滑',
             'quant knowledge - intraday momentum', intraday_momentum)

# ============================================================
# Factor 6: High-Low Breakout (高低点突破)
# ============================================================
def high_low_breakout(df):
    rolling_high = df['high'].rolling(40).max()
    rolling_low = df['low'].rolling(40).min()
    range_size = rolling_high - rolling_low + 1e-8
    position = (df['close'] - rolling_low) / range_size
    # 转换为 -1 到 1
    return position * 2 - 1

test_and_log('high_low_breakout', '高低点突破：收盘价在近40期高低点区间中的位置',
             'quant knowledge - channel breakout', high_low_breakout)

# ============================================================
# Factor 7: Volume Weighted Price Momentum (量价加权动量)
# ============================================================
def vwap_momentum(df):
    vwap = (df['close'] * df['volume']).rolling(20).sum() / (df['volume'].rolling(20).sum() + 1e-8)
    deviation = (df['close'] - vwap) / (df['close'].rolling(20).std() + 1e-8)
    return deviation

test_and_log('vwap_momentum', 'VWAP偏离因子：收盘价相对于20期VWAP的标准化偏离',
             'quant knowledge - VWAP deviation', vwap_momentum)

# ============================================================
# Factor 8: OI-Price Momentum (持仓价格联动)
# ============================================================
def oi_price_momentum(df):
    price_ret = df['close'].pct_change(5)
    oi_ret = df['open_interest'].pct_change(5)
    # 同向增强，反向减弱
    return price_ret * oi_ret * 1000

test_and_log('oi_price_momentum', '持仓价格联动：5期价格收益率与持仓量变化率的乘积',
             'quant knowledge - OI price co-movement', oi_price_momentum)

print("\n" + "="*60)
print("ROUND 1 COMPLETE")
print("="*60)
