import sys
sys.path.insert(0, 'E:/quant-trading-mvp')
sys.stdout.reconfigure(encoding='utf-8')
import numpy as np, pandas as pd, json
from datetime import datetime
from quant.common.config import config
from quant.common.db import db_engine
from quant.factors.factor_evaluator import evaluate_factor

with db_engine(config) as engine:
    df = pd.read_sql(
        "SELECT time as timestamp, open, high, low, close, volume, open_interest "
        "FROM kline_data WHERE symbol='au_main' AND interval='30m' ORDER BY time",
        engine
    )
df['timestamp'] = pd.to_datetime(df['timestamp'])

def test_factor(name, desc, source, factor_values):
    results = {}
    for h in [4, 8, 16]:
        fwd = np.log(df['close'].shift(-h) / df['close'])
        r = evaluate_factor(factor_values, fwd, name=name)
        results[f'{h*30//60}h'] = r
        print(f'  {h*30//60}h: IC={r.get("rank_ic",0):.4f}, IR={r.get("ir",0):.4f}, Dir={r.get("direction_acc",0):.4f}')
    avg_ic = np.mean([abs(results[k].get('rank_ic', 0)) for k in results if results[k].get('valid')])
    eff = avg_ic > 0.02
    record = {
        'timestamp': datetime.now().isoformat(), 'name': name,
        'description': desc, 'source': source,
        'avg_abs_ic': round(avg_ic, 4),
        'results': {k: {kk: vv for kk, vv in v.items() if kk != 'valid'} for k, v in results.items()},
        'effective': str(eff),
    }
    with open('E:/quant-trading-mvp/data/factor_discovery_log.jsonl', 'a', encoding='utf-8') as f:
        f.write(json.dumps(record, ensure_ascii=False) + '\n')
    tag = '** EFFECTIVE **' if eff else ''
    print(f'{name}: Avg |IC|={avg_ic:.4f} {tag}')
    print('---')
    return eff

# Factor 1: OI Connors RSI - 三重RSI复合
def oi_connors_rsi(df):
    oi = df['open_interest']
    # RSI of OI
    delta = oi.diff()
    gain = delta.clip(lower=0).rolling(3).mean()
    loss = (-delta.clip(upper=0)).rolling(3).mean()
    rsi3 = 100 - 100/(1+gain/(loss+1e-10))
    # RSI of streak
    streak = pd.Series(0.0, index=df.index)
    for i in range(1, len(oi)):
        if delta.iloc[i] > 0: streak.iloc[i] = max(streak.iloc[i-1], 0) + 1
        elif delta.iloc[i] < 0: streak.iloc[i] = min(streak.iloc[i-1], 0) - 1
        else: streak.iloc[i] = 0
    streak_g = streak.clip(lower=0).rolling(2).mean()
    streak_l = (-streak.clip(upper=0)).rolling(2).mean()
    rsi_streak = 100 - 100/(1+streak_g/(streak_l+1e-10))
    # Percentile rank
    pct_rank = delta.rolling(100).rank(pct=True) * 100
    composite = (rsi3 + rsi_streak + pct_rank) / 3 - 50
    z = (composite - composite.rolling(60).mean()) / (composite.rolling(60).std() + 1e-10)
    return z

print('=== Factor 1: oi_connors_rsi ===')
test_factor('oi_connors_rsi', 'OI Connors RSI：三重RSI复合z-score',
            'Connors RSI applied to OI', oi_connors_rsi(df))

# Factor 2: OI Heikin Ashi Trend
def oi_heikin_ashi(df, w=10):
    oi = df['open_interest']
    ha_close = (oi.rolling(4).mean())
    ha_open = pd.Series(np.nan, index=df.index)
    ha_open.iloc[0] = oi.iloc[0]
    for i in range(1, len(oi)):
        ha_open.iloc[i] = (ha_open.iloc[i-1] + ha_close.iloc[i-1]) / 2 if not np.isnan(ha_close.iloc[i-1]) else ha_open.iloc[i-1]
    trend = ha_close - ha_open
    ema = trend.ewm(span=w).mean()
    z = (ema - ema.rolling(60).mean()) / (ema.rolling(60).std() + 1e-10)
    return z

print('=== Factor 2: oi_heikin_ashi ===')
test_factor('oi_heikin_ashi', 'OI Heikin Ashi趋势：HA蜡烛体方向EMA z-score',
            'Heikin Ashi trend applied to OI', oi_heikin_ashi(df))

# Factor 3: OI Momentum Persistence Ratio
def oi_mom_persist_ratio(df, w=20):
    oi_diff = df['open_interest'].diff()
    pos_count = (oi_diff > 0).rolling(w).sum()
    neg_count = (oi_diff < 0).rolling(w).sum()
    ratio = (pos_count - neg_count) / w
    z = (ratio - ratio.rolling(60).mean()) / (ratio.rolling(60).std() + 1e-10)
    return z

print('=== Factor 3: oi_mom_persist_ratio ===')
test_factor('oi_mom_persist_ratio', 'OI动量持续比：正负变化频率差z-score',
            'OI momentum persistence up down ratio', oi_mom_persist_ratio(df))

# Factor 4: OI Weighted Realized Correlation
def oi_weighted_realized_corr(df, w=20):
    price_ret = df['close'].pct_change()
    oi_ret = df['open_interest'].pct_change()
    oi_weight = oi_ret.abs() / (oi_ret.abs().rolling(w).mean() + 1e-10)
    weighted_product = price_ret * oi_ret * oi_weight
    raw = weighted_product.rolling(w).mean()
    z = (raw - raw.rolling(60).mean()) / (raw.rolling(60).std() + 1e-10)
    return z

print('=== Factor 4: oi_weighted_realized_corr ===')
test_factor('oi_weighted_realized_corr', 'OI加权已实现相关：OI幅度加权的价格OI协动z',
            'OI weighted realized correlation', oi_weighted_realized_corr(df))

# Factor 5: OI Trend Reversal Probability
def oi_trend_rev_prob(df, w=20):
    oi = df['open_interest']
    oi_dir = np.sign(oi.diff())
    reversals = (oi_dir != oi_dir.shift(1)).astype(float)
    rev_freq = reversals.rolling(w).mean()
    # low reversal = strong trend, use direction
    trend_dir = np.sign(oi.diff(w))
    raw = (1 - rev_freq) * trend_dir
    z = (raw - raw.rolling(60).mean()) / (raw.rolling(60).std() + 1e-10)
    return z

print('=== Factor 5: oi_trend_rev_prob ===')
test_factor('oi_trend_rev_prob', 'OI趋势反转概率：低反转频率乘以方向z-score',
            'OI trend reversal probability', oi_trend_rev_prob(df))

# Factor 6: OI Acceleration Persistence
def oi_accel_persist(df, w=10):
    oi_accel = df['open_interest'].diff().diff()
    accel_dir = np.sign(oi_accel)
    persist = accel_dir.rolling(w).sum() / w
    oi_dir = np.sign(df['open_interest'].diff(w))
    raw = persist * oi_dir
    z = (raw - raw.rolling(60).mean()) / (raw.rolling(60).std() + 1e-10)
    return z

print('=== Factor 6: oi_accel_persist ===')
test_factor('oi_accel_persist', 'OI加速度持续性：加速度方向一致性乘以OI方向z',
            'OI acceleration direction persistence', oi_accel_persist(df))

# Factor 7: Price Volatility OI Momentum Interaction
def price_vol_oi_mom_interact(df, w=20):
    price_vol = df['close'].pct_change().rolling(w).std()
    vol_z = (price_vol - price_vol.rolling(60).mean()) / (price_vol.rolling(60).std() + 1e-10)
    oi_mom = df['open_interest'].pct_change(w)
    oi_mom_z = (oi_mom - oi_mom.rolling(60).mean()) / (oi_mom.rolling(60).std() + 1e-10)
    # low vol + high OI momentum = accumulation
    raw = oi_mom_z * (1 / (1 + vol_z.abs()))
    z = (raw - raw.rolling(40).mean()) / (raw.rolling(40).std() + 1e-10)
    return z

print('=== Factor 7: price_vol_oi_mom_interact ===')
test_factor('price_vol_oi_mom_interact', '价格波动率OI动量交互：低波动时OI动量增强z',
            'price volatility OI momentum interaction', price_vol_oi_mom_interact(df))

# Factor 8: OI Exponential Trend Strength
def oi_exp_trend_strength(df):
    oi = df['open_interest']
    ema5 = oi.ewm(span=5).mean()
    ema20 = oi.ewm(span=20).mean()
    ema60 = oi.ewm(span=60).mean()
    # all aligned = strong trend
    align = np.sign(ema5 - ema20) + np.sign(ema20 - ema60) + np.sign(ema5 - ema60)
    raw = align / 3 * (ema5 - ema60).abs() / (ema60 + 1e-10)
    z = (raw - raw.rolling(60).mean()) / (raw.rolling(60).std() + 1e-10)
    return z

print('=== Factor 8: oi_exp_trend_strength ===')
test_factor('oi_exp_trend_strength', 'OI指数趋势强度：三EMA对齐乘以偏离幅度z-score',
            'OI exponential trend strength triple EMA alignment', oi_exp_trend_strength(df))

print('\n=== Round 5 complete ===')
