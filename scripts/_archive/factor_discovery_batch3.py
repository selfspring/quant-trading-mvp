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

def to_native(obj):
    if isinstance(obj, (np.integer,)): return int(obj)
    if isinstance(obj, (np.floating,)): return float(obj)
    if isinstance(obj, (np.bool_,)): return bool(obj)
    if isinstance(obj, dict): return {k: to_native(v) for k, v in obj.items()}
    return obj

def test_and_log(name, desc, source, factor_values):
    results = {}
    for h in [4, 8, 16]:
        fwd = np.log(df['close'].shift(-h) / df['close'])
        r = evaluate_factor(factor_values, fwd, name=name)
        label = f"{h*30//60}h"
        results[label] = r
    avg_ic = np.mean([abs(results[k].get('rank_ic', 0)) for k in results])
    effective = avg_ic > 0.02
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
        print(f"  {label}: IC={r.get('rank_ic',0):.4f}, IR={r.get('ir',0):.4f}, Dir={r.get('direction_acc',0):.4f}, LS={r.get('long_short_return',0):.6f}")
    print(f"  Avg|IC|={avg_ic:.4f} {status}")
    return effective

tested = 0
effective_count = 0

# === Factor 17: OI净流入速率变化 ===
print("\n=== Factor 17: oi_net_inflow_accel ===")
oi_diff = df['open_interest'].diff()
oi_inflow_rate = oi_diff.rolling(5).mean()
oi_inflow_accel = oi_inflow_rate.diff(5)
oi_inflow_accel_z = (oi_inflow_accel - oi_inflow_accel.rolling(30).mean()) / (oi_inflow_accel.rolling(30).std() + 1e-10)
price_trend = np.sign(df['close'].rolling(10).mean() - df['close'].rolling(30).mean())
factor17 = oi_inflow_accel_z * price_trend
tested += 1
if test_and_log('oi_net_inflow_accel', 'OI净流入加速度：OI流入速率变化z乘以价格趋势方向', 'OI net inflow acceleration', factor17):
    effective_count += 1

# === Factor 18: 成交量加权收盘价偏离度 ===
print("\n=== Factor 18: vol_weighted_close_dev ===")
vwap20 = (df['close'] * df['volume']).rolling(20).sum() / (df['volume'].rolling(20).sum() + 1e-10)
vwap5 = (df['close'] * df['volume']).rolling(5).sum() / (df['volume'].rolling(5).sum() + 1e-10)
dev = (vwap5 - vwap20) / (df['close'].rolling(20).std() + 1e-10)
factor18 = dev
tested += 1
if test_and_log('vol_weighted_close_dev', '短长期VWAP偏离：5期VWAP减20期VWAP归一化', 'short long VWAP deviation', factor18):
    effective_count += 1

# === Factor 19: OI变化的条件波动率 ===
print("\n=== Factor 19: oi_cond_vol ===")
oi_chg = df['open_interest'].pct_change()
ret = df['close'].pct_change()
up_ret = (ret > 0).astype(float)
down_ret = (ret <= 0).astype(float)
oi_up_vol = (oi_chg * up_ret).rolling(20).std()
oi_down_vol = (oi_chg * down_ret).rolling(20).std()
factor19 = (oi_up_vol - oi_down_vol) / (oi_up_vol + oi_down_vol + 1e-10)
factor19_z = (factor19 - factor19.rolling(30).mean()) / (factor19.rolling(30).std() + 1e-10)
tested += 1
if test_and_log('oi_cond_vol', 'OI条件波动率不对称：上涨时OI波动减下跌时OI波动归一化z', 'OI conditional volatility asymmetry', factor19_z):
    effective_count += 1

# === Factor 20: 价格跳跃后OI持续性 ===
print("\n=== Factor 20: jump_oi_persist ===")
ret = df['close'].pct_change()
ret_std = ret.rolling(20).std()
is_jump = (ret.abs() > 2 * ret_std).astype(float)
jump_dir = np.sign(ret) * is_jump
oi_after = df['open_interest'].pct_change().shift(-1)
jump_oi = jump_dir * oi_after
factor20 = jump_oi.rolling(20).sum()
factor20_z = (factor20 - factor20.rolling(30).mean()) / (factor20.rolling(30).std() + 1e-10)
tested += 1
if test_and_log('jump_oi_persist', '价格跳跃后OI持续性：大幅波动后OI反应方向的累积z', 'jump OI persistence', factor20_z):
    effective_count += 1

# === Factor 21: 多周期OI动量一致性得分 ===
print("\n=== Factor 21: multi_period_oi_mom_score ===")
oi = df['open_interest']
oi_mom3 = np.sign(oi.diff(3))
oi_mom5 = np.sign(oi.diff(5))
oi_mom10 = np.sign(oi.diff(10))
oi_mom20 = np.sign(oi.diff(20))
consistency = (oi_mom3 + oi_mom5 + oi_mom10 + oi_mom20) / 4
price_mom = df['close'].pct_change(5)
price_mom_z = (price_mom - price_mom.rolling(20).mean()) / (price_mom.rolling(20).std() + 1e-10)
factor21 = consistency * price_mom_z
tested += 1
if test_and_log('multi_period_oi_mom_score', '多周期OI动量一致性：多窗口OI方向一致性乘以价格动量z', 'multi period OI momentum consistency', factor21):
    effective_count += 1

# === Factor 22: 成交量分布的变异系数趋势 ===
print("\n=== Factor 22: vol_cv_trend ===")
vol_mean = df['volume'].rolling(20).mean()
vol_std = df['volume'].rolling(20).std()
vol_cv = vol_std / (vol_mean + 1e-10)
vol_cv_ma5 = vol_cv.rolling(5).mean()
vol_cv_ma20 = vol_cv.rolling(20).mean()
cv_trend = vol_cv_ma5 - vol_cv_ma20
cv_trend_z = (cv_trend - cv_trend.rolling(30).mean()) / (cv_trend.rolling(30).std() + 1e-10)
mom_dir = np.sign(df['close'].pct_change(10))
factor22 = cv_trend_z * mom_dir
tested += 1
if test_and_log('vol_cv_trend', '成交量变异系数趋势：CV短长均线差z乘以价格方向', 'volume CV trend directional', factor22):
    effective_count += 1

# === Factor 23: OI与价格的非线性相关 ===
print("\n=== Factor 23: oi_price_nonlinear ===")
ret = df['close'].pct_change(5)
oi_chg = df['open_interest'].pct_change(5)
ret_sq = ret ** 2 * np.sign(ret)
oi_sq = oi_chg ** 2 * np.sign(oi_chg)
nonlin_corr = ret_sq.rolling(20).corr(oi_sq)
nonlin_z = (nonlin_corr - nonlin_corr.rolling(30).mean()) / (nonlin_corr.rolling(30).std() + 1e-10)
factor23 = nonlin_z
tested += 1
if test_and_log('oi_price_nonlinear_corr', 'OI与价格非线性相关：有符号平方收益与有符号平方OI变化的相关z', 'OI price nonlinear correlation', factor23):
    effective_count += 1

# === Factor 24: 价格位置与OI位置的背离 ===
print("\n=== Factor 24: price_oi_position_div ===")
price_pct = (df['close'] - df['close'].rolling(60).min()) / (df['close'].rolling(60).max() - df['close'].rolling(60).min() + 1e-10)
oi_pct = (df['open_interest'] - df['open_interest'].rolling(60).min()) / (df['open_interest'].rolling(60).max() - df['open_interest'].rolling(60).min() + 1e-10)
divergence = oi_pct - price_pct
div_z = (divergence - divergence.rolling(20).mean()) / (divergence.rolling(20).std() + 1e-10)
factor24 = div_z
tested += 1
if test_and_log('price_oi_position_div', '价格与OI位置背离：OI在60期区间位置减价格在60期区间位置z', 'price OI position divergence', factor24):
    effective_count += 1

print(f"\n=== Batch 3 Summary: tested={tested}, effective={effective_count} ===")
