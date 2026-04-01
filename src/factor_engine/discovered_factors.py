"""
Discovered Factors - Auto-generated from factor discovery loop
Generated: 2026-03-19
Total effective factors in this session: 19
"""
import numpy as np
import pandas as pd


def oi_keltner_signal(df):
    """OI 肯特纳通道位置*价格动量方向确认"""
    oi = df['open_interest']
    oi_ma = oi.rolling(20, min_periods=5).mean()
    oi_std = oi.rolling(20, min_periods=5).std()
    oi_position = (oi - oi_ma) / (oi_std * 2 + 1e-8)
    oi_position = oi_position.clip(-1, 1)
    price_mom = df['close'].pct_change(10)
    signal = oi_position * np.sign(price_mom)
    return signal.rolling(5, min_periods=2).mean()


def volume_weighted_oi_roc(df):
    """成交量加权 OI 变化率"""
    vol = df['volume']
    vol_ma = vol.rolling(20, min_periods=5).mean()
    vol_weight = (vol / (vol_ma + 1e-8)).clip(0, 3)
    oi_roc = df['open_interest'].pct_change(5).fillna(0)
    return (vol_weight * oi_roc).rolling(10, min_periods=3).mean()


def price_position_oi_confirm(df):
    """价格位置*OI 方向确认"""
    hl_range = df['high'] - df['low']
    price_pos = (df['close'] - df['low']) / (hl_range + 1e-8)
    oi_dir = np.sign(df['open_interest'].diff())
    fv = (price_pos * oi_dir).rolling(15, min_periods=5).mean()
    return (fv - fv.rolling(40, min_periods=10).mean()) / (fv.rolling(40, min_periods=10).std() + 1e-8)


def oi_vol_cone_breakout(df):
    """OI 波动率锥突破信号"""
    oi_vol = df['open_interest'].pct_change(10).rolling(20, min_periods=5).std()
    oi_vol_ma = oi_vol.rolling(40, min_periods=10).mean()
    oi_vol_z = (oi_vol - oi_vol_ma) / (oi_vol.rolling(40, min_periods=10).std() + 1e-8)
    price_mom = df['close'].pct_change(10)
    return oi_vol_z * np.sign(price_mom)


def vol_oi_ratio_momentum(df):
    """量仓比动量*价格方向"""
    vol_oi_ratio = df['volume'] / (df['open_interest'] + 1e-8)
    ratio_ma = vol_oi_ratio.rolling(20, min_periods=5).mean()
    ratio_mom = vol_oi_ratio / (ratio_ma + 1e-8) - 1
    price_dir = np.sign(df['close'].diff(5))
    fv = ratio_mom * price_dir
    return (fv - fv.rolling(30, min_periods=10).mean()) / (fv.rolling(30, min_periods=10).std() + 1e-8)


def oi_triple_ma(df):
    """OI 三重均线排列*价格动量"""
    oi = df['open_interest']
    oi_ma5 = oi.rolling(5, min_periods=2).mean()
    oi_ma10 = oi.rolling(10, min_periods=3).mean()
    oi_ma20 = oi.rolling(20, min_periods=5).mean()
    alignment = np.sign(oi_ma5 - oi_ma10) + np.sign(oi_ma10 - oi_ma20)
    price_mom = df['close'].pct_change(10)
    fv = alignment * np.sign(price_mom)
    return fv.rolling(5, min_periods=2).mean()


def oi_momentum_decay(df):
    """OI 动量衰减率*价格方向"""
    oi = df['open_interest']
    oi_mom_short = oi.pct_change(5)
    oi_mom_long = oi.pct_change(20)
    decay = oi_mom_short / (oi_mom_long.abs() + 1e-8)
    decay = decay.clip(-5, 5)
    price_mom = df['close'].pct_change(10)
    fv = decay * np.sign(price_mom)
    return (fv - fv.rolling(40, min_periods=10).mean()) / (fv.rolling(40, min_periods=10).std() + 1e-8)


def oi_rsi_divergence(df):
    """OI RSI 与价格动量背离"""
    oi = df['open_interest']
    oi_diff = oi.diff()
    gain = oi_diff.clip(lower=0).rolling(14, min_periods=5).mean()
    loss = (-oi_diff.clip(upper=0)).rolling(14, min_periods=5).mean()
    rs = gain / (loss + 1e-8)
    oi_rsi = 100 - 100 / (1 + rs)
    oi_rsi_norm = (oi_rsi - 50) / 50
    price_mom = df['close'].pct_change(10)
    return oi_rsi_norm - np.sign(price_mom) * oi_rsi_norm.abs()


def vol_price_oi_resonance(df):
    """量价 OI 三元共振"""
    vol_z = (df['volume'] - df['volume'].rolling(20).mean()) / (df['volume'].rolling(20).std() + 1e-8)
    price_z = (df['close'].pct_change(5) - df['close'].pct_change(5).rolling(20).mean()) / (df['close'].pct_change(5).rolling(20).std() + 1e-8)
    oi_z = (df['open_interest'].diff() - df['open_interest'].diff().rolling(20).mean()) / (df['open_interest'].diff().rolling(20).std() + 1e-8)
    fv = vol_z * price_z * oi_z
    fv = fv.rolling(10, min_periods=3).mean()
    return (fv - fv.rolling(40).mean()) / (fv.rolling(40).std() + 1e-8)


def oi_momentum_conditional(df):
    """OI 动量一致性*价格方向"""
    oi = df['open_interest']
    oi_mom = oi.pct_change(5)
    oi_mom_sign = np.sign(oi_mom)
    consistency = (oi_mom_sign == oi_mom_sign.shift(1)).astype(float)
    consistency = consistency.rolling(10, min_periods=5).mean()
    price_mom = df['close'].pct_change(10)
    fv = consistency * np.sign(oi_mom) * np.sign(price_mom)
    return (fv - fv.rolling(40).mean()) / (fv.rolling(40).std() + 1e-8)


def vol_adjusted_oi_flow(df):
    """波动率调整 OI 流"""
    oi_change = df['open_interest'].diff()
    returns = df['close'].pct_change()
    realized_vol = returns.rolling(20, min_periods=5).std()
    oi_flow_adj = oi_change / (realized_vol + 1e-8)
    fv = oi_flow_adj.rolling(10, min_periods=3).sum()
    return (fv - fv.rolling(40).mean()) / (fv.rolling(40).std() + 1e-8)


def vol_dist_weighted_oi(df):
    """成交量分布加权 OI 变化"""
    vol = df['volume']
    vol_rank = vol.rolling(40, min_periods=10).rank(pct=True)
    vol_weight = vol_rank ** 2
    oi_change = df['open_interest'].diff()
    weighted_oi = (vol_weight * oi_change).rolling(15, min_periods=5).sum()
    return (weighted_oi - weighted_oi.rolling(40).mean()) / (weighted_oi.rolling(40).std() + 1e-8)


def oi_extreme_reversal_v2(df):
    """OI 极值反转*价格确认"""
    oi = df['open_interest']
    oi_z = (oi - oi.rolling(40).mean()) / (oi.rolling(40).std() + 1e-8)
    extreme = (oi_z.abs() > 2).astype(float)
    reversal_signal = -extreme * np.sign(oi_z)
    price_mom = df['close'].pct_change(10)
    fv = reversal_signal * np.sign(price_mom)
    fv = fv.rolling(10, min_periods=3).mean()
    return (fv - fv.rolling(40).mean()) / (fv.rolling(40).std() + 1e-8)


def oi_roc_conditional_pct(df):
    """OI 变化率条件分位"""
    oi = df['open_interest']
    oi_roc = oi.pct_change(5)
    oi_roc_rank = oi_roc.rolling(100, min_periods=20).rank(pct=True)
    condition = (oi_roc.abs() > oi_roc.rolling(40).std()).astype(float)
    fv = condition * (oi_roc_rank - 0.5) * 2
    price_mom = df['close'].pct_change(10)
    fv = fv * np.sign(price_mom)
    return (fv - fv.rolling(40).mean()) / (fv.rolling(40).std() + 1e-8)


def oi_weighted_price_mom(df):
    """OI 加权价格动量"""
    oi = df['open_interest']
    oi_z = (oi - oi.rolling(40).mean()) / (oi.rolling(40).std() + 1e-8)
    oi_weight = (oi_z.abs() + 1).clip(1, 3)
    price_mom = df['close'].pct_change(10)
    fv = price_mom * oi_weight
    return (fv - fv.rolling(40).mean()) / (fv.rolling(40).std() + 1e-8)


def oi_ma_deviation(df):
    """OI 均线乖离率*价格方向"""
    oi = df['open_interest']
    oi_ma = oi.rolling(20).mean()
    deviation = (oi - oi_ma) / oi_ma
    price_mom = df['close'].pct_change(10)
    fv = deviation * np.sign(price_mom)
    return (fv - fv.rolling(40).mean()) / (fv.rolling(40).std() + 1e-8)


def oi_vol_weighted_mom(df):
    """OI 波动率加权动量"""
    oi = df['open_interest']
    oi_mom = oi.pct_change(5)
    oi_vol = oi_mom.rolling(20).std()
    oi_vol_inv = 1 / (oi_vol + 1e-8)
    fv = oi_mom * oi_vol_inv
    return (fv - fv.rolling(40).mean()) / (fv.rolling(40).std() + 1e-8)


def price_mom_oi_boost(df):
    """价格动量 OI 确认增强"""
    price_mom = df['close'].pct_change(10)
    oi_dir = np.sign(df['open_interest'].diff(5))
    boost = 1 + 0.5 * (np.sign(price_mom) == oi_dir).astype(float)
    fv = price_mom * boost
    return (fv - fv.rolling(40).mean()) / (fv.rolling(40).std() + 1e-8)


def price_range_oi_flow(df):
    """价格区间*OI 流"""
    hl_range = (df['high'] - df['low']) / df['close']
    range_exp = hl_range / hl_range.rolling(20).mean()
    oi_change = df['open_interest'].diff()
    oi_flow = oi_change.rolling(5).sum()
    fv = range_exp * oi_flow
    return (fv - fv.rolling(40).mean()) / (fv.rolling(40).std() + 1e-8)


# List of all discovered factor functions
DISCOVERED_FACTORS = [
    oi_keltner_signal,
    volume_weighted_oi_roc,
    price_position_oi_confirm,
    oi_vol_cone_breakout,
    vol_oi_ratio_momentum,
    oi_triple_ma,
    oi_momentum_decay,
    oi_rsi_divergence,
    vol_price_oi_resonance,
    oi_momentum_conditional,
    vol_adjusted_oi_flow,
    vol_dist_weighted_oi,
    oi_extreme_reversal_v2,
    oi_roc_conditional_pct,
    oi_weighted_price_mom,
    oi_ma_deviation,
    oi_vol_weighted_mom,
    price_mom_oi_boost,
    price_range_oi_flow,
]
