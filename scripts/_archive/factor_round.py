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

# Factor 1: OI Stiffness
def oi_stiffness(df, w=20):
    price_vol = df['close'].pct_change().abs().rolling(w).std()
    oi_vol = df['open_interest'].pct_change().abs().rolling(w).std()
    ratio = price_vol / (oi_vol + 1e-10)
    oi_dir = np.sign(df['open_interest'].diff(w))
    raw = ratio * oi_dir
    z = (raw - raw.rolling(60).mean()) / (raw.rolling(60).std() + 1e-10)
    return z

print('=== Factor 1: oi_stiffness ===')
test_factor('oi_stiffness', 'OI刚性：价格波动率/OI波动率比乘以OI方向z-score',
            'OI stiffness price impact resistance', oi_stiffness(df))

# Factor 2: OI Price Momentum Divergence V2
def oi_price_mom_div_v2(df):
    scores = pd.Series(0.0, index=df.index)
    for w in [5, 10, 20, 40]:
        oi_mom = df['open_interest'].pct_change(w)
        price_mom = df['close'].pct_change(w)
        oi_z = (oi_mom - oi_mom.rolling(60).mean()) / (oi_mom.rolling(60).std() + 1e-10)
        price_z = (price_mom - price_mom.rolling(60).mean()) / (price_mom.rolling(60).std() + 1e-10)
        scores += (oi_z - price_z) / 4
    z = (scores - scores.rolling(40).mean()) / (scores.rolling(40).std() + 1e-10)
    return z

print('=== Factor 2: oi_price_mom_div_v2 ===')
test_factor('oi_price_mom_div_v2', '多尺度OI价格动量背离V2：多窗口OI-价格动量z差综合',
            'multi-scale OI price momentum divergence v2', oi_price_mom_div_v2(df))

# Factor 3: OI Compression Breakout
def oi_compression_breakout(df, w=20, lookback=60):
    oi_std = df['open_interest'].pct_change().rolling(w).std()
    oi_std_pct = oi_std.rolling(lookback).rank(pct=True)
    compressed = (oi_std_pct < 0.2).astype(float)
    oi_dir = np.sign(df['open_interest'].diff(5))
    signal = compressed.rolling(10).sum() * oi_dir
    z = (signal - signal.rolling(60).mean()) / (signal.rolling(60).std() + 1e-10)
    return z

print('=== Factor 3: oi_compression_breakout ===')
test_factor('oi_compression_breakout', 'OI压缩突破：OI波动率低位时方向信号z-score',
            'OI volatility compression breakout', oi_compression_breakout(df))

# Factor 4: Volume Weighted OI Acceleration
def vol_weighted_oi_accel_v2(df, w=10):
    oi_accel = df['open_interest'].diff().diff()
    rel_vol = df['volume'] / df['volume'].rolling(20).mean()
    raw = oi_accel * rel_vol
    ema = raw.ewm(span=w).mean()
    z = (ema - ema.rolling(60).mean()) / (ema.rolling(60).std() + 1e-10)
    return z

print('=== Factor 4: vol_weighted_oi_accel_v2 ===')
test_factor('vol_weighted_oi_accel_v2', '成交量加权OI加速度V2：OI二阶导乘以相对成交量EMA z',
            'volume weighted OI acceleration v2', vol_weighted_oi_accel_v2(df))

# Factor 5: OI Trend Quality Index
def oi_trend_quality_idx(df, w=20):
    oi_ret = df['open_interest'].pct_change()
    net_move = df['open_interest'].diff(w)
    total_move = oi_ret.abs().rolling(w).sum() * df['open_interest'].shift(w)
    efficiency = net_move / (total_move + 1e-10)
    sharpe = oi_ret.rolling(w).mean() / (oi_ret.rolling(w).std() + 1e-10)
    raw = efficiency * sharpe.abs()
    z = (raw - raw.rolling(60).mean()) / (raw.rolling(60).std() + 1e-10)
    return z

print('=== Factor 5: oi_trend_quality_idx ===')
test_factor('oi_trend_quality_idx', 'OI趋势质量指数：效率比乘以夏普绝对值z-score',
            'OI trend quality efficiency times Sharpe', oi_trend_quality_idx(df))

# Factor 6: Price Range OI Normalized V2
def price_range_oi_norm_v2(df, w=10):
    hl_range = (df['high'] - df['low']) / df['close']
    oi_change = df['open_interest'].pct_change().abs()
    ratio = hl_range / (oi_change + 1e-10)
    ratio_z = (ratio - ratio.rolling(60).mean()) / (ratio.rolling(60).std() + 1e-10)
    oi_dir = np.sign(df['open_interest'].diff(w))
    raw = ratio_z * oi_dir * (-1)  # low ratio = OI absorbing = continuation
    z = (raw - raw.rolling(40).mean()) / (raw.rolling(40).std() + 1e-10)
    return z

print('=== Factor 6: price_range_oi_norm_v2 ===')
test_factor('price_range_oi_norm_v2', '振幅OI归一化V2：振幅/OI变化比取反乘以OI方向z',
            'price range OI normalized v2', price_range_oi_norm_v2(df))

# Factor 7: OI Relative Strength Oscillator
def oi_rso(df, w=14):
    oi_diff = df['open_interest'].diff()
    gain = oi_diff.clip(lower=0).rolling(w).mean()
    loss = (-oi_diff.clip(upper=0)).rolling(w).mean()
    rs = gain / (loss + 1e-10)
    rsi = 100 - 100 / (1 + rs)
    centered = rsi - 50
    z = (centered - centered.rolling(60).mean()) / (centered.rolling(60).std() + 1e-10)
    return z

print('=== Factor 7: oi_rso ===')
test_factor('oi_rso', 'OI相对强度振荡器：OI RSI居中z-score',
            'OI relative strength oscillator', oi_rso(df))

# Factor 8: OI Accumulation Distribution Line
def oi_ad_line(df, w=20):
    clv = ((df['close'] - df['low']) - (df['high'] - df['close'])) / (df['high'] - df['low'] + 1e-10)
    oi_flow = clv * df['open_interest'].diff().abs()
    ad = oi_flow.cumsum()
    ad_detrend = ad - ad.rolling(w).mean()
    z = (ad_detrend - ad_detrend.rolling(60).mean()) / (ad_detrend.rolling(60).std() + 1e-10)
    return z

print('=== Factor 8: oi_ad_line ===')
test_factor('oi_ad_line', 'OI AD线：K线位置加权OI流量累积去趋势z-score',
            'OI accumulation distribution line', oi_ad_line(df))

print('\n=== Round complete ===')
