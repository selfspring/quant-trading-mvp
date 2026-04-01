import sys
sys.path.insert(0, 'E:/quant-trading-mvp')
import numpy as np
import pandas as pd
from quant.common.config import config
from quant.common.db import db_engine
from quant.factors.factor_evaluator import evaluate_factor
import json
from datetime import datetime

# Load data once
with db_engine(config) as engine:
    df = pd.read_sql("""
        SELECT time as timestamp, open, high, low, close, volume, open_interest
        FROM kline_data WHERE symbol='au_main' AND interval='30m'
        ORDER BY time
    """, engine)
df['timestamp'] = pd.to_datetime(df['timestamp'])
print(f"Data loaded: {len(df)} rows")

def test_factor(name, description, source, factor_values):
    results = {}
    for h in [4, 8, 16]:
        fwd = np.log(df['close'].shift(-h) / df['close'])
        r = evaluate_factor(factor_values, fwd, name=name)
        label = f"{h*30//60}h"
        results[label] = r
        ic = r.get('rank_ic', 0)
        ir = r.get('ir', 0)
        da = r.get('direction_acc', 0)
        print(f"  {label}: IC={ic:.4f}, IR={ir:.4f}, Dir={da:.4f}")

    avg_ic = np.mean([abs(results[k].get('rank_ic', 0)) for k in results])
    effective = avg_ic > 0.02
    def jsonify(obj):
        if isinstance(obj, (np.bool_, np.generic)):
            return obj.item()
        if isinstance(obj, float) and (np.isnan(obj) or np.isinf(obj)):
            return None
        return obj

    record = {
        'timestamp': datetime.now().isoformat(),
        'name': name,
        'description': description,
        'source': source,
        'avg_abs_ic': round(float(avg_ic), 4),
        'results': {k: {kk: round(float(vv), 4) if isinstance(vv, (float, np.floating)) else jsonify(vv) for kk, vv in v.items() if kk != 'valid'} for k, v in results.items()},
        'effective': bool(effective),
    }
    with open('E:/quant-trading-mvp/data/factor_discovery_log.jsonl', 'a', encoding='utf-8') as f:
        f.write(json.dumps(record, ensure_ascii=False) + '\n')
    tag = "** EFFECTIVE **" if effective else ""
    print(f"  Avg |IC|: {avg_ic:.4f} {tag}")
    print("---")
    return effective, avg_ic

effective_count = 0
total_count = 0

# ============================================================
# Factor 1: OI回归残差因子
# ============================================================
print("\n[Factor 1] oi_regression_residual")
total_count += 1
window = 40
oi = df['open_interest']
price = df['close']
oi_z = (oi - oi.rolling(window).mean()) / (oi.rolling(window).std() + 1e-8)
p_z = (price - price.rolling(window).mean()) / (price.rolling(window).std() + 1e-8)
cov = (oi_z * p_z).rolling(window).mean()
var_p = (p_z ** 2).rolling(window).mean()
beta = cov / (var_p + 1e-8)
residual = oi_z - beta * p_z
eff, _ = test_factor('oi_regression_residual',
    'OI回���残差：OI对价格滚动回归的残差z-score',
    'OI-price cointegration residual', residual)
if eff: effective_count += 1

# ============================================================
# Factor 2: 成交量加权价格偏度
# ============================================================
print("\n[Factor 2] volume_weighted_price_skew")
total_count += 1
ret = df['close'].pct_change()
vol_w = df['volume'] / df['volume'].rolling(20).mean()
weighted_ret = ret * vol_w
skew_val = weighted_ret.rolling(30).apply(lambda x: pd.Series(x).skew(), raw=False)
f2 = (skew_val - skew_val.rolling(60).mean()) / (skew_val.rolling(60).std() + 1e-8)
eff, _ = test_factor('volume_weighted_price_skew',
    '成交量加权价格偏度：量加权收益的30期偏度z-score',
    'volume weighted return skewness', f2)
if eff: effective_count += 1

# ============================================================
# Factor 3: 高低价不对称动量
# ============================================================
print("\n[Factor 3] hl_asymmetric_momentum")
total_count += 1
high_mom = np.log(df['high'] / df['high'].shift(10))
low_mom = np.log(df['low'] / df['low'].shift(10))
asym = high_mom - low_mom
f3 = (asym - asym.rolling(40).mean()) / (asym.rolling(40).std() + 1e-8)
eff, _ = test_factor('hl_asymmetric_momentum',
    '高低价不对称动量：高价动量与低价动量之差的z-score',
    'high-low asymmetric momentum', f3)
if eff: effective_count += 1

# ============================================================
# Factor 4: OI条件期望偏离
# ============================================================
print("\n[Factor 4] oi_conditional_surprise")
total_count += 1
oi_chg = df['open_interest'].diff()
vol_q = pd.qcut(df['volume'].rolling(20).rank(pct=True), q=3, labels=False, duplicates='drop')
# 按成交量分位计算OI变化的条件均值
oi_cond_mean = oi_chg.copy() * 0
for i in range(3):
    mask = vol_q == i
    oi_cond_mean[mask] = oi_chg[mask].rolling(30, min_periods=10).mean()
f4_raw = oi_chg - oi_cond_mean
f4 = (f4_raw - f4_raw.rolling(20).mean()) / (f4_raw.rolling(20).std() + 1e-8)
eff, _ = test_factor('oi_conditional_surprise',
    'OI条件期望偏离：按成交量分位的OI变化条件均值残差z-score',
    'OI conditional expectation surprise', f4)
if eff: effective_count += 1

# ============================================================
# Factor 5: 价格冲击不对称性
# ============================================================
print("\n[Factor 5] price_impact_asymmetry")
total_count += 1
ret5 = df['close'].pct_change()
vol_norm = df['volume'] / df['volume'].rolling(20).mean()
impact = ret5 / (vol_norm + 1e-8)
up_impact = impact.where(ret5 > 0, 0).rolling(20).mean()
down_impact = impact.where(ret5 < 0, 0).rolling(20).mean().abs()
asym_impact = (up_impact - down_impact) / (up_impact + down_impact + 1e-8)
f5 = (asym_impact - asym_impact.rolling(40).mean()) / (asym_impact.rolling(40).std() + 1e-8)
eff, _ = test_factor('price_impact_asymmetry',
    '价格冲击不对称性：上涨vs下跌时单位成交量价格冲击的差异z-score',
    'price impact asymmetry', f5)
if eff: effective_count += 1

# ============================================================
# Factor 6: OI加权波动率偏斜
# ============================================================
print("\n[Factor 6] oi_weighted_vol_skew")
total_count += 1
ret6 = df['close'].pct_change()
oi_chg6 = df['open_interest'].pct_change()
oi_up = (oi_chg6 > 0).astype(float)
vol_when_oi_up = (ret6.abs() * oi_up).rolling(20).mean()
vol_when_oi_down = (ret6.abs() * (1 - oi_up)).rolling(20).mean()
f6_raw = (vol_when_oi_up - vol_when_oi_down) / (vol_when_oi_up + vol_when_oi_down + 1e-8)
f6 = (f6_raw - f6_raw.rolling(40).mean()) / (f6_raw.rolling(40).std() + 1e-8)
eff, _ = test_factor('oi_weighted_vol_skew',
    'OI加权波动率偏���：OI增加时vs减少时的波动率差异z-score',
    'OI weighted volatility skew', f6)
if eff: effective_count += 1

# ============================================================
# Factor 7: 量价弹性变化率
# ============================================================
print("\n[Factor 7] vp_elasticity_change")
total_count += 1
ret7 = df['close'].pct_change()
vol_pct7 = df['volume'].pct_change()
elasticity = ret7 / (vol_pct7 + 1e-8)
elasticity = elasticity.clip(-10, 10)
e_short = elasticity.rolling(10).mean()
e_long = elasticity.rolling(40).mean()
f7 = (e_short - e_long) / (elasticity.rolling(40).std() + 1e-8)
eff, _ = test_factor('vp_elasticity_change',
    '量价弹性变化率：短长期量价弹性差的z-score',
    'volume-price elasticity regime change', f7)
if eff: effective_count += 1

# ============================================================
# Factor 8: OI梯度加速度与波动率交互
# ============================================================
print("\n[Factor 8] oi_grad_vol_interact")
total_count += 1
oi_d1 = df['open_interest'].diff()
oi_d2 = oi_d1.diff()
oi_d2_z = (oi_d2 - oi_d2.rolling(20).mean()) / (oi_d2.rolling(20).std() + 1e-8)
realized_vol = ret7.abs().rolling(20).mean()
rv_z = (realized_vol - realized_vol.rolling(40).mean()) / (realized_vol.rolling(40).std() + 1e-8)
f8 = oi_d2_z * rv_z
f8 = f8.clip(-5, 5)
eff, _ = test_factor('oi_grad_vol_interact',
    'OI梯度加速度与波动率交互：OI二阶导z乘以波动率z',
    'OI gradient volatility interaction', f8)
if eff: effective_count += 1

print(f"\n========== SUMMARY ==========")
print(f"Tested: {total_count}, Effective: {effective_count}")
