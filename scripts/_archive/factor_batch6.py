import sys
sys.path.insert(0, 'E:/quant-trading-mvp')
import numpy as np
import pandas as pd
from quant.common.config import config
from quant.common.db import db_engine
from quant.factors.factor_evaluator import evaluate_factor
import json
from datetime import datetime

class NpEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (np.integer,)): return int(obj)
        if isinstance(obj, (np.floating,)): return float(obj)
        if isinstance(obj, (np.bool_,)): return bool(obj)
        if isinstance(obj, np.ndarray): return obj.tolist()
        return super().default(obj)

with db_engine(config) as engine:
    df = pd.read_sql("""
        SELECT time as timestamp, open, high, low, close, volume, open_interest
        FROM kline_data WHERE symbol='au_main' AND interval='30m'
        ORDER BY time
    """, engine)
df['timestamp'] = pd.to_datetime(df['timestamp'])
print(f"Data loaded: {len(df)} rows")

def test_factor(name, desc, source, factor_values):
    results = {}
    for h in [4, 8, 16]:
        fwd = np.log(df['close'].shift(-h) / df['close'])
        r = evaluate_factor(factor_values, fwd, name=name)
        label = f"{h*30//60}h"
        results[label] = r
        ric = r.get('rank_ic', 0)
        ir = r.get('ir', 0)
        da = r.get('direction_acc', 0)
        print(f"  {label}: IC={ric:.4f}, IR={ir:.4f}, Dir={da:.4f}")
    avg_ic = np.mean([abs(results[k].get('rank_ic', 0)) for k in results])
    eff = avg_ic > 0.02
    record = {
        'timestamp': datetime.now().isoformat(),
        'name': name, 'description': desc, 'source': source,
        'avg_abs_ic': round(float(avg_ic), 4),
        'results': {k: {kk: vv for kk, vv in v.items() if kk != 'valid'} for k, v in results.items()},
        'effective': bool(eff),
    }
    with open('E:/quant-trading-mvp/data/factor_discovery_log.jsonl', 'a', encoding='utf-8') as f:
        f.write(json.dumps(record, ensure_ascii=False, cls=NpEncoder) + '\n')
    tag = "** EFFECTIVE **" if eff else ""
    print(f"  => {name}: Avg |IC|={avg_ic:.4f} {tag}\n")
    return avg_ic, eff

total = 0
effective = 0

# === Factor 41: OI Triple Screen ===
# Inspired by Elder's triple screen: OI trend on 3 timeframes must agree
print("=== Factor 41: oi_triple_screen ===")
oi = df['open_interest']
oi_trend_short = np.sign(oi.rolling(5).mean() - oi.rolling(10).mean())
oi_trend_mid = np.sign(oi.rolling(10).mean() - oi.rolling(30).mean())
oi_trend_long = np.sign(oi.rolling(30).mean() - oi.rolling(60).mean())
# All 3 agree = strong signal
triple = (oi_trend_short + oi_trend_mid + oi_trend_long)
# Weight by OI change magnitude
oi_mag = oi.pct_change(10).abs().rolling(5).mean()
oi_mag_z = (oi_mag - oi_mag.rolling(40).mean()) / oi_mag.rolling(40).std().clip(lower=1e-10)
factor_raw = triple * (1 + oi_mag_z.clip(0, 3))
z = (factor_raw - factor_raw.rolling(40).mean()) / factor_raw.rolling(40).std().clip(lower=1e-10)
fv = z.clip(-3, 3)
ic, eff = test_factor('oi_triple_screen',
    'OI三重滤网：三个时间尺度OI趋势一致性乘以OI变化幅度',
    'Elder triple screen for OI', fv)
total += 1; effective += int(eff)

# === Factor 42: Volume-OI Momentum Spread ===
# Spread between volume momentum and OI momentum
print("=== Factor 42: vol_oi_mom_spread ===")
vol_mom = (df['volume'].rolling(5).mean() / df['volume'].rolling(20).mean().clip(lower=1)) - 1
oi_mom = (df['open_interest'].rolling(5).mean() / df['open_interest'].rolling(20).mean().clip(lower=1)) - 1
spread = vol_mom - oi_mom
# When volume rises faster than OI = speculative; OI rises faster = positioning
z = (spread - spread.rolling(40).mean()) / spread.rolling(40).std().clip(lower=1e-10)
price_dir = np.sign(df['close'].pct_change(5))
fv = (z * price_dir).clip(-3, 3)
ic, eff = test_factor('vol_oi_mom_spread',
    '量仓动量价差：成交量动量与OI动量之差z乘以价格方向',
    'volume OI momentum spread', fv)
total += 1; effective += int(eff)

# === Factor 43: OI Acceleration Regime ===
# OI acceleration (2nd derivative) in different volatility regimes
print("=== Factor 43: oi_accel_regime ===")
oi = df['open_interest']
oi_vel = oi.pct_change(5)
oi_accel = oi_vel - oi_vel.shift(5)
# Volatility regime
atr = (df['high'] - df['low']).rolling(14).mean()
atr_pct = atr / df['close'].clip(lower=1)
atr_z = (atr_pct - atr_pct.rolling(60).mean()) / atr_pct.rolling(60).std().clip(lower=1e-10)
# In low vol: OI accel matters more (buildup before breakout)
# In high vol: OI accel matters less (noise)
vol_weight = np.exp(-atr_z.clip(-2, 2))  # higher weight in low vol
factor_raw = oi_accel * vol_weight
z = (factor_raw - factor_raw.rolling(40).mean()) / factor_raw.rolling(40).std().clip(lower=1e-10)
fv = z.clip(-3, 3)
ic, eff = test_factor('oi_accel_regime',
    'OI加速度regime：低波动率时OI加速度权重更高的z-score',
    'OI acceleration volatility regime', fv)
total += 1; effective += int(eff)

# === Factor 44: Directional Volume Ratio ===
# Ratio of up-volume to down-volume over rolling window
print("=== Factor 44: dir_vol_ratio ===")
ret = df['close'].pct_change()
up_vol = np.where(ret > 0, df['volume'], 0)
down_vol = np.where(ret < 0, df['volume'], 0)
up_sum = pd.Series(up_vol, index=df.index).rolling(15).sum()
down_sum = pd.Series(down_vol, index=df.index).rolling(15).sum().clip(lower=1)
ratio = np.log(up_sum / down_sum)
z = (ratio - ratio.rolling(40).mean()) / ratio.rolling(40).std().clip(lower=1e-10)
fv = z.clip(-3, 3)
ic, eff = test_factor('dir_vol_ratio',
    '方向成交量比：上涨/下跌成交量对数比的z-score',
    'directional volume ratio', fv)
total += 1; effective += int(eff)

# === Factor 45: OI Momentum Divergence Index ===
# Composite: OI momentum vs price momentum across 3 windows
print("=== Factor 45: oi_mom_div_index ===")
divs = []
for w in [5, 10, 20]:
    p_mom = df['close'].pct_change(w)
    p_z = (p_mom - p_mom.rolling(40).mean()) / p_mom.rolling(40).std().clip(lower=1e-10)
    o_mom = df['open_interest'].pct_change(w)
    o_z = (o_mom - o_mom.rolling(40).mean()) / o_mom.rolling(40).std().clip(lower=1e-10)
    divs.append(o_z - p_z)
composite = pd.concat(divs, axis=1).mean(axis=1)
z = (composite - composite.rolling(40).mean()) / composite.rolling(40).std().clip(lower=1e-10)
fv = z.clip(-3, 3)
ic, eff = test_factor('oi_mom_div_index',
    'OI动量背离指数：多窗口OI与价格动量背离的综合z-score',
    'OI momentum divergence index', fv)
total += 1; effective += int(eff)

# === Factor 46: Smart OI ===
# OI changes during high-volume low-volatility periods (smart money)
print("=== Factor 46: smart_oi ===")
vol_z = (df['volume'] - df['volume'].rolling(20).mean()) / df['volume'].rolling(20).std().clip(lower=1e-10)
ret_abs = df['close'].pct_change().abs()
ret_z = (ret_abs - ret_abs.rolling(20).mean()) / ret_abs.rolling(20).std().clip(lower=1e-10)
# Smart money: high volume but low price impact
smart_mask = ((vol_z > 0.5) & (ret_z < 0)).astype(float)
oi_chg = df['open_interest'].pct_change()
smart_oi = (oi_chg * smart_mask).rolling(15).sum()
z = (smart_oi - smart_oi.rolling(40).mean()) / smart_oi.rolling(40).std().clip(lower=1e-10)
fv = z.clip(-3, 3)
ic, eff = test_factor('smart_oi',
    '聪明OI：高成交量低波动时OI变化的累积z-score',
    'smart money OI', fv)
total += 1; effective += int(eff)

# === Factor 47: OI Trend Exhaustion ===
# When OI trend has been going too long, expect reversal
print("=== Factor 47: oi_trend_exhaustion ===")
oi_ma = df['open_interest'].rolling(10).mean()
oi_trend = oi_ma - oi_ma.shift(10)
oi_trend_dir = np.sign(oi_trend)
# Count consecutive same-direction trend
consec = pd.Series(0.0, index=df.index)
cnt = 0
prev = 0
for i in range(len(df)):
    cur = oi_trend_dir.iloc[i]
    if cur == prev and not np.isnan(cur):
        cnt += 1
    else:
        cnt = 1
    prev = cur
    consec.iloc[i] = cnt
# Exhaustion: long trend + decelerating OI change
oi_decel = oi_trend.abs() - oi_trend.abs().shift(5)
exhaustion = consec * np.sign(oi_decel.clip(upper=0))  # negative decel = exhaustion
z = (exhaustion - exhaustion.rolling(40).mean()) / exhaustion.rolling(40).std().clip(lower=1e-10)
fv = (-z * oi_trend_dir).clip(-3, 3)  # reversal signal
ic, eff = test_factor('oi_trend_exhaustion',
    'OI趋势耗竭：OI趋势持续时间与减速的交互反转信号',
    'OI trend exhaustion reversal', fv)
total += 1; effective += int(eff)

# === Factor 48: Price-Volume Correlation Shift ===
# Shift in price-volume correlation regime
print("=== Factor 48: pv_corr_shift ===")
ret = df['close'].pct_change()
vol = df['volume']
corr_short = ret.rolling(10).corr(vol)
corr_long = ret.rolling(40).corr(vol)
shift = corr_short - corr_long
z = (shift - shift.rolling(40).mean()) / shift.rolling(40).std().clip(lower=1e-10)
# Positive shift = volume now more correlated with price = trending
mom_dir = np.sign(df['close'].pct_change(10))
fv = (z * mom_dir).clip(-3, 3)
ic, eff = test_factor('pv_corr_shift',
    '量价相关性迁移：短长期量价相关性差z乘以动量方向',
    'price volume correlation shift', fv)
total += 1; effective += int(eff)

print(f"\n=== BATCH 6 COMPLETE: Tested {total}, Effective {effective} ===")
