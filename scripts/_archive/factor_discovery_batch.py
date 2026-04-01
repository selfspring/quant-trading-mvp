import sys
sys.path.insert(0, 'E:/quant-trading-mvp')
import numpy as np
import pandas as pd
from quant.common.config import config
from quant.common.db import db_engine
from quant.factors.factor_evaluator import evaluate_factor
import json
from datetime import datetime

with db_engine(config) as engine:
    df = pd.read_sql("""
        SELECT time as timestamp, open, high, low, close, volume, open_interest
        FROM kline_data WHERE symbol='au_main' AND interval='30m'
        ORDER BY time
    """, engine)
df['timestamp'] = pd.to_datetime(df['timestamp'])
print(f"Data loaded: {len(df)} rows")

def test_and_log(name, desc, source, factor_values):
    results = {}
    for h in [4, 8, 16]:
        fwd = np.log(df['close'].shift(-h) / df['close'])
        r = evaluate_factor(factor_values, fwd, name=name)
        label = f"{h*30//60}h"
        results[label] = r
    avg_ic = np.mean([abs(results[k].get('rank_ic', 0)) for k in results])
    effective = avg_ic > 0.02
    def to_native(obj):
        if isinstance(obj, (np.integer,)): return int(obj)
        if isinstance(obj, (np.floating,)): return float(obj)
        if isinstance(obj, (np.bool_,)): return bool(obj)
        if isinstance(obj, dict): return {k: to_native(v) for k, v in obj.items()}
        return obj
    record = {
        'timestamp': datetime.now().isoformat(),
        'name': name,
        'description': desc,
        'source': source,
        'avg_abs_ic': round(float(avg_ic), 4),
        'results': {k: to_native({kk: vv for kk, vv in v.items() if kk != 'valid'}) for k, v in results.items()},
        'effective': bool(effective),
    }
    with open('E:/quant-trading-mvp/data/factor_discovery_log.jsonl', 'a', encoding='utf-8') as f:
        f.write(json.dumps(record, ensure_ascii=False, default=lambda o: float(o) if isinstance(o, (np.floating, np.integer)) else str(o)) + '\n')
    status = '** EFFECTIVE **' if effective else ''
    for label in ['2h', '4h', '8h']:
        r = results[label]
        ric = r.get('rank_ic', 0)
        ir = r.get('ir', 0)
        da = r.get('direction_acc', 0)
        ls = r.get('long_short_return', 0)
        print(f"  {label}: IC={ric:.4f}, IR={ir:.4f}, Dir={da:.4f}, LS={ls:.6f}")
    print(f"  Avg|IC|={avg_ic:.4f} {status}")
    return effective

tested = 0
effective_count = 0

# === Factor 1: OI绝对变化强度与价格方向交互 ===
print("\n=== Factor 1: oi_abs_change_dir ===")
oi_chg = df['open_interest'].pct_change()
oi_abs = oi_chg.abs()
oi_abs_z = (oi_abs - oi_abs.rolling(20).mean()) / (oi_abs.rolling(20).std() + 1e-10)
price_dir = np.sign(df['close'] - df['close'].shift(5))
factor1 = oi_abs_z * price_dir
factor1 = factor1.rolling(5).mean()
tested += 1
if test_and_log('oi_abs_change_dir', 'OI绝对变化强度与价格方向交互：OI变化幅度z乘以价格方向', 'OI absolute change direction', factor1):
    effective_count += 1

# === Factor 2: 成交量加权VWAP位置 ===
print("\n=== Factor 2: vwap_position_vol_weight ===")
vwap = (df['close'] * df['volume']).rolling(20).sum() / (df['volume'].rolling(20).sum() + 1e-10)
price_pos = (df['close'] - vwap) / (df['close'].rolling(20).std() + 1e-10)
vol_ratio = df['volume'] / (df['volume'].rolling(20).mean() + 1e-10)
factor2 = price_pos * np.log1p(vol_ratio)
tested += 1
if test_and_log('vwap_position_vol_weight', '成交量加权VWAP位置：价格偏离VWAP的z乘以对数相对成交量', 'VWAP position volume weighted', factor2):
    effective_count += 1

# === Factor 3: 多层波动率斜率 ===
print("\n=== Factor 3: vol_slope_multi ===")
ret = np.log(df['close'] / df['close'].shift(1))
vol10 = ret.rolling(10).std()
vol20 = ret.rolling(20).std()
vol40 = ret.rolling(40).std()
vol60 = ret.rolling(60).std()
slope1 = (vol10 - vol20) / (vol20 + 1e-10)
slope2 = (vol20 - vol40) / (vol40 + 1e-10)
slope3 = (vol40 - vol60) / (vol60 + 1e-10)
factor3 = (slope1 + slope2 + slope3) / 3
mom_dir = np.sign(df['close'] - df['close'].shift(10))
factor3 = factor3 * mom_dir
tested += 1
if test_and_log('vol_slope_multi', '多层波动率斜率：多窗口波动���梯度均值乘以动量方向', 'multi-scale volatility slope', factor3):
    effective_count += 1

# === Factor 4: OI变化率偏度 ===
print("\n=== Factor 4: oi_change_skew ===")
oi_chg = df['open_interest'].pct_change()
oi_skew = oi_chg.rolling(30).skew()
oi_skew_z = (oi_skew - oi_skew.rolling(40).mean()) / (oi_skew.rolling(40).std() + 1e-10)
factor4 = oi_skew_z
tested += 1
if test_and_log('oi_change_skew', 'OI变化率偏度：OI pct_change的30期偏度z-score', 'OI change skewness', factor4):
    effective_count += 1

# === Factor 5: 价格与OI加速度协同 ===
print("\n=== Factor 5: price_oi_accel_sync ===")
price_mom5 = df['close'].pct_change(5)
price_mom20 = df['close'].pct_change(20)
price_accel = price_mom5 - price_mom20 / 4
oi_mom5 = df['open_interest'].pct_change(5)
oi_mom20 = df['open_interest'].pct_change(20)
oi_accel = oi_mom5 - oi_mom20 / 4
pa_z = (price_accel - price_accel.rolling(30).mean()) / (price_accel.rolling(30).std() + 1e-10)
oa_z = (oi_accel - oi_accel.rolling(30).mean()) / (oi_accel.rolling(30).std() + 1e-10)
factor5 = pa_z * oa_z
factor5 = factor5.rolling(3).mean()
tested += 1
if test_and_log('price_oi_accel_sync', '价格与OI加速度协同：价格加速度z与OI加速度z的乘积', 'price OI acceleration sync', factor5):
    effective_count += 1

# === Factor 6: 成交量冲击持续性 ===
print("\n=== Factor 6: vol_impulse_persist ===")
vol_z = (df['volume'] - df['volume'].rolling(20).mean()) / (df['volume'].rolling(20).std() + 1e-10)
vol_impulse = (vol_z > 1.5).astype(float)
ret_sign = np.sign(df['close'] - df['open'])
impulse_dir = vol_impulse * ret_sign
factor6 = impulse_dir.rolling(15).sum()
factor6 = (factor6 - factor6.rolling(40).mean()) / (factor6.rolling(40).std() + 1e-10)
tested += 1
if test_and_log('vol_impulse_persist', '成交量冲击持续性：放量K线方向的15期累积z-score', 'volume impulse persistence', factor6):
    effective_count += 1

# === Factor 7: OI与价格滞后交叉相关 ===
print("\n=== Factor 7: oi_price_lag_corr ===")
ret5 = df['close'].pct_change(5)
oi_chg5 = df['open_interest'].pct_change(5).shift(3)
corr_lag = ret5.rolling(20).corr(oi_chg5)
corr_lag_z = (corr_lag - corr_lag.rolling(40).mean()) / (corr_lag.rolling(40).std() + 1e-10)
factor7 = corr_lag_z
tested += 1
if test_and_log('oi_price_lag_corr', 'OI与价格滞后交叉相关：OI变化领先3期与价格收益的滚动相关z', 'OI price lagged cross-correlation', factor7):
    effective_count += 1

# === Factor 8: 涨跌K线OI反应不对称 ===
print("\n=== Factor 8: hl_asym_oi_reaction ===")
up_bar = (df['close'] > df['open']).astype(float)
down_bar = (df['close'] <= df['open']).astype(float)
oi_chg_diff = df['open_interest'].diff()
up_oi = (oi_chg_diff * up_bar).rolling(15).mean()
down_oi = (oi_chg_diff * down_bar).rolling(15).mean()
factor8 = up_oi - down_oi
factor8 = (factor8 - factor8.rolling(30).mean()) / (factor8.rolling(30).std() + 1e-10)
tested += 1
if test_and_log('hl_asym_oi_reaction', '涨跌K线OI反应不对称：上涨K线OI变化均值减下跌K线OI变化均值z', 'up down bar OI asymmetry', factor8):
    effective_count += 1

print(f"\n=== Batch 1 Summary: tested={tested}, effective={effective_count} ===")
