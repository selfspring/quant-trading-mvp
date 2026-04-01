"""
经典量化因子库
每个因子是一个函数：输入 DataFrame(open/high/low/close/volume/open_interest)，输出 Series
"""
import numpy as np
import pandas as pd


# ============================================================
# 1. 趋势因子
# ============================================================

def ma_cross_5_20(df):
    """均线交叉：MA5/MA20 比值"""
    return df['close'].rolling(5).mean() / df['close'].rolling(20).mean() - 1

def ma_cross_10_60(df):
    """均线交叉：MA10/MA60 比值"""
    return df['close'].rolling(10).mean() / df['close'].rolling(60).mean() - 1

def ma_slope_20(df):
    """MA20 斜率（20周期线性回归斜率）"""
    ma = df['close'].rolling(20).mean()
    return ma.diff(5) / ma.shift(5)

def macd_hist(df):
    """MACD 柱状图"""
    ema12 = df['close'].ewm(span=12).mean()
    ema26 = df['close'].ewm(span=26).mean()
    dif = ema12 - ema26
    dea = dif.ewm(span=9).mean()
    return (dif - dea) * 2

def macd_cross(df):
    """MACD 金叉/死叉信号（DIF-DEA 的符号变化）"""
    ema12 = df['close'].ewm(span=12).mean()
    ema26 = df['close'].ewm(span=26).mean()
    dif = ema12 - ema26
    dea = dif.ewm(span=9).mean()
    diff = dif - dea
    return np.sign(diff) - np.sign(diff.shift(1))

def price_position(df):
    """价格在N日高低点中的位置 (0~1)"""
    h20 = df['high'].rolling(20).max()
    l20 = df['low'].rolling(20).min()
    rng = h20 - l20
    return (df['close'] - l20) / rng.replace(0, np.nan)

def trend_strength(df):
    """趋势强度：ADX 近似（用方向运动计算）"""
    high = df['high']
    low = df['low']
    close = df['close']
    plus_dm = high.diff().clip(lower=0)
    minus_dm = (-low.diff()).clip(lower=0)
    tr = pd.concat([high - low, (high - close.shift(1)).abs(), (low - close.shift(1)).abs()], axis=1).max(axis=1)
    atr14 = tr.rolling(14).mean()
    plus_di = 100 * plus_dm.rolling(14).mean() / atr14.replace(0, np.nan)
    minus_di = 100 * minus_dm.rolling(14).mean() / atr14.replace(0, np.nan)
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    return dx.rolling(14).mean()


# ============================================================
# 2. 动量因子
# ============================================================

def momentum_5(df):
    """5周期动量（收益率）"""
    return df['close'].pct_change(5)

def momentum_20(df):
    """20周期动量"""
    return df['close'].pct_change(20)

def momentum_60(df):
    """60周期动量"""
    return df['close'].pct_change(60)

def rsi_14(df):
    """RSI(14) 归一化到 -1~1"""
    delta = df['close'].diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi = 100 - 100 / (1 + rs)
    return (rsi - 50) / 50  # 归一化

def rsi_divergence(df):
    """RSI 背离：价格创新高但 RSI 没有"""
    delta = df['close'].diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi = 100 - 100 / (1 + rs)
    price_high = df['close'].rolling(20).max() == df['close']
    rsi_high = rsi.rolling(20).max() == rsi
    return (price_high.astype(int) - rsi_high.astype(int)).astype(float)

def rate_of_change(df):
    """ROC(10)"""
    return (df['close'] - df['close'].shift(10)) / df['close'].shift(10)

def williams_r(df):
    """威廉指标 %R(14)"""
    h14 = df['high'].rolling(14).max()
    l14 = df['low'].rolling(14).min()
    return (h14 - df['close']) / (h14 - l14).replace(0, np.nan)


# ============================================================
# 3. 波动率因子
# ============================================================

def atr_14(df):
    """ATR(14) 归一化"""
    high = df['high']
    low = df['low']
    close = df['close']
    tr = pd.concat([high - low, (high - close.shift(1)).abs(), (low - close.shift(1)).abs()], axis=1).max(axis=1)
    atr = tr.rolling(14).mean()
    return atr / close

def volatility_ratio(df):
    """波动率比：短期/长期"""
    vol5 = df['close'].pct_change().rolling(5).std()
    vol20 = df['close'].pct_change().rolling(20).std()
    return vol5 / vol20.replace(0, np.nan)

def bb_width(df):
    """布林带宽度"""
    ma = df['close'].rolling(20).mean()
    std = df['close'].rolling(20).std()
    return 2 * std / ma.replace(0, np.nan)

def bb_position(df):
    """布林带位置 (0~1)"""
    ma = df['close'].rolling(20).mean()
    std = df['close'].rolling(20).std()
    upper = ma + 2 * std
    lower = ma - 2 * std
    return (df['close'] - lower) / (upper - lower).replace(0, np.nan)

def keltner_position(df):
    """Keltner 通道位置"""
    ma = df['close'].ewm(span=20).mean()
    high = df['high']
    low = df['low']
    close = df['close']
    tr = pd.concat([high - low, (high - close.shift(1)).abs(), (low - close.shift(1)).abs()], axis=1).max(axis=1)
    atr = tr.rolling(20).mean()
    upper = ma + 2 * atr
    lower = ma - 2 * atr
    return (close - lower) / (upper - lower).replace(0, np.nan)

def realized_vol_20(df):
    """20周期已实现波动率"""
    return df['close'].pct_change().rolling(20).std()

def high_low_range(df):
    """高低点振幅比"""
    return (df['high'] - df['low']) / df['close']


# ============================================================
# 4. 成交量因子
# ============================================================

def volume_ratio_5_20(df):
    """量比：5周期均量/20周期均量"""
    v5 = df['volume'].rolling(5).mean()
    v20 = df['volume'].rolling(20).mean()
    return v5 / v20.replace(0, np.nan)

def volume_price_corr(df):
    """量价相关性（20周期）"""
    return df['close'].rolling(20).corr(df['volume'])

def obv_slope(df):
    """OBV 斜率（能量潮趋势）"""
    direction = np.sign(df['close'].diff())
    obv = (direction * df['volume']).cumsum()
    return obv.diff(10) / obv.rolling(10).mean().replace(0, np.nan)

def volume_spike(df):
    """成交量突变（当前量/20周期均量）"""
    return df['volume'] / df['volume'].rolling(20).mean().replace(0, np.nan)

def vwap_deviation(df):
    """VWAP 偏离度"""
    vwap = (df['close'] * df['volume']).rolling(20).sum() / df['volume'].rolling(20).sum().replace(0, np.nan)
    return (df['close'] - vwap) / vwap.replace(0, np.nan)

def money_flow(df):
    """资金流向（MFI 简化版）"""
    tp = (df['high'] + df['low'] + df['close']) / 3
    mf = tp * df['volume']
    pos_mf = mf.where(tp > tp.shift(1), 0).rolling(14).sum()
    neg_mf = mf.where(tp < tp.shift(1), 0).rolling(14).sum()
    return pos_mf / neg_mf.replace(0, np.nan)


# ============================================================
# 5. 持仓量因子
# ============================================================

def oi_change_rate(df):
    """持仓量变化率"""
    return df['open_interest'].pct_change(5)

def oi_price_divergence(df):
    """持仓量-价格背离：价格涨但持仓量降"""
    price_up = df['close'].diff(5) > 0
    oi_down = df['open_interest'].diff(5) < 0
    return (price_up & oi_down).astype(float) - (~price_up & ~oi_down).astype(float)

def oi_volume_ratio(df):
    """持仓量/成交量比"""
    return df['open_interest'] / df['volume'].replace(0, np.nan)

def oi_concentration(df):
    """持仓量集中度变化"""
    oi_ma = df['open_interest'].rolling(20).mean()
    return df['open_interest'] / oi_ma.replace(0, np.nan) - 1


# ============================================================
# 6. 形态因子
# ============================================================

def body_ratio(df):
    """实体比（实体/振幅）"""
    body = (df['close'] - df['open']).abs()
    rng = (df['high'] - df['low']).replace(0, np.nan)
    return body / rng

def upper_shadow_ratio(df):
    """上影线比"""
    rng = (df['high'] - df['low']).replace(0, np.nan)
    upper = df['high'] - df[['open', 'close']].max(axis=1)
    return upper / rng

def lower_shadow_ratio(df):
    """下影线比"""
    rng = (df['high'] - df['low']).replace(0, np.nan)
    lower = df[['open', 'close']].min(axis=1) - df['low']
    return lower / rng

def consecutive_direction(df):
    """连续涨跌天数"""
    direction = np.sign(df['close'].diff())
    groups = (direction != direction.shift(1)).cumsum()
    counts = direction.groupby(groups).cumcount() + 1
    return counts * direction

def gap_ratio(df):
    """跳空缺口比"""
    gap = df['open'] - df['close'].shift(1)
    return gap / df['close'].shift(1)


# ============================================================
# 7. 时间因子
# ============================================================

def hour_of_day(df):
    """交易时段（归一化）"""
    ts = pd.to_datetime(df['timestamp']) if 'timestamp' in df.columns else df.index
    return ts.hour / 23.0

def day_of_week(df):
    """星期几（归一化）"""
    ts = pd.to_datetime(df['timestamp']) if 'timestamp' in df.columns else df.index
    return ts.dayofweek / 4.0


# ============================================================
# 因子注册表
# ============================================================

CLASSIC_FACTORS = {
    # 趋势
    'ma_cross_5_20': ma_cross_5_20,
    'ma_cross_10_60': ma_cross_10_60,
    'ma_slope_20': ma_slope_20,
    'macd_hist': macd_hist,
    'macd_cross': macd_cross,
    'price_position': price_position,
    'trend_strength': trend_strength,
    # 动量
    'momentum_5': momentum_5,
    'momentum_20': momentum_20,
    'momentum_60': momentum_60,
    'rsi_14': rsi_14,
    'rsi_divergence': rsi_divergence,
    'rate_of_change': rate_of_change,
    'williams_r': williams_r,
    # 波动率
    'atr_14': atr_14,
    'volatility_ratio': volatility_ratio,
    'bb_width': bb_width,
    'bb_position': bb_position,
    'keltner_position': keltner_position,
    'realized_vol_20': realized_vol_20,
    'high_low_range': high_low_range,
    # 成交量
    'volume_ratio_5_20': volume_ratio_5_20,
    'volume_price_corr': volume_price_corr,
    'obv_slope': obv_slope,
    'volume_spike': volume_spike,
    'vwap_deviation': vwap_deviation,
    'money_flow': money_flow,
    # 持仓量
    'oi_change_rate': oi_change_rate,
    'oi_price_divergence': oi_price_divergence,
    'oi_volume_ratio': oi_volume_ratio,
    'oi_concentration': oi_concentration,
    # 形态
    'body_ratio': body_ratio,
    'upper_shadow_ratio': upper_shadow_ratio,
    'lower_shadow_ratio': lower_shadow_ratio,
    'consecutive_direction': consecutive_direction,
    'gap_ratio': gap_ratio,
    # 时间
    'hour_of_day': hour_of_day,
    'day_of_week': day_of_week,
}


def compute_all_factors(df: pd.DataFrame) -> pd.DataFrame:
    """计算所有经典因子，返回因子值 DataFrame"""
    result = pd.DataFrame(index=df.index)
    failed = []
    for name, func in CLASSIC_FACTORS.items():
        try:
            result[name] = func(df)
        except Exception as e:
            failed.append((name, str(e)))
            result[name] = np.nan
    if failed:
        print(f"  Failed factors: {failed}")
    return result
