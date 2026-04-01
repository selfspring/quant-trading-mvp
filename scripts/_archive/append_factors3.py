"""Append batch 3 effective factors"""

new_code = """

def oi_trend_reversal(df):
    \"\"\"OI趋势反转信号：OI均线交叉时的价格动量累积
    avg |IC| = 0.0510, 4h IC=0.0587, 8h IC=0.0658
    \"\"\"
    import numpy as np
    oi_ma5 = df['open_interest'].rolling(5).mean()
    oi_ma20 = df['open_interest'].rolling(20).mean()
    oi_cross = np.sign(oi_ma5 - oi_ma20)
    oi_cross_change = oi_cross.diff().abs()
    price_at_cross = df['close'].pct_change(5) * oi_cross_change
    return price_at_cross.rolling(10).sum()

DISCOVERED_FACTORS['oi_trend_reversal'] = oi_trend_reversal


def volume_decay_rate(df):
    \"\"\"成交量衰减率：5期成交量对数衰减率z-score
    avg |IC| = 0.0206, 2h IC=-0.0287
    \"\"\"
    import numpy as np
    vol_ratio_5 = df['volume'] / df['volume'].shift(5)
    decay = np.log(vol_ratio_5 + 1e-8) / 5
    return (decay - decay.rolling(30).mean()) / (decay.rolling(30).std() + 1e-8)

DISCOVERED_FACTORS['volume_decay_rate'] = volume_decay_rate


def high_vol_bar_return(df):
    \"\"\"高成交量K线收益：放量K线收益的累积
    avg |IC| = 0.0347, 4h IC=0.0401
    \"\"\"
    import numpy as np
    ret = np.log(df['close'] / df['close'].shift(1))
    vol_threshold = df['volume'].rolling(20).quantile(0.8)
    is_high_vol = (df['volume'] > vol_threshold).astype(float)
    return (ret * is_high_vol).rolling(15).sum()

DISCOVERED_FACTORS['high_vol_bar_return'] = high_vol_bar_return


def oi_momentum_quality(df):
    \"\"\"OI动量质量：OI变化率的夏普比
    avg |IC| = 0.0301, 2h IC=0.0337, 4h IC=0.0377
    \"\"\"
    oi_ret = df['open_interest'].pct_change(5)
    oi_ret_mean = oi_ret.rolling(20).mean()
    oi_ret_std = oi_ret.rolling(20).std()
    return oi_ret_mean / (oi_ret_std + 1e-8)

DISCOVERED_FACTORS['oi_momentum_quality'] = oi_momentum_quality


def price_vol_oi_interact(df):
    \"\"\"价格波动率与OI交互：波动率z乘以OI变化z
    avg |IC| = 0.0257, all horizons ~0.025
    \"\"\"
    import numpy as np
    ret = np.log(df['close'] / df['close'].shift(1))
    price_vol = ret.rolling(20).std()
    price_vol_z = (price_vol - price_vol.rolling(60).mean()) / (price_vol.rolling(60).std() + 1e-8)
    oi_chg = df['open_interest'].diff(5)
    oi_chg_z = (oi_chg - oi_chg.rolling(20).mean()) / (oi_chg.rolling(20).std() + 1e-8)
    return price_vol_z * oi_chg_z

DISCOVERED_FACTORS['price_vol_oi_interact'] = price_vol_oi_interact


def oi_vol_trend_ratio(df):
    \"\"\"OI与成交量趋势比：OI线性趋势/成交量线性趋势z-score
    avg |IC| = 0.0490, 4h IC=0.0579, 8h IC=0.0490
    \"\"\"
    import numpy as np
    oi_trend = df['open_interest'].rolling(20).apply(lambda x: np.polyfit(range(len(x)), x, 1)[0], raw=True)
    vol_trend = df['volume'].rolling(20).apply(lambda x: np.polyfit(range(len(x)), x, 1)[0], raw=True)
    ratio = oi_trend / (vol_trend.abs() + 1e-8)
    return (ratio - ratio.rolling(30).mean()) / (ratio.rolling(30).std() + 1e-8)

DISCOVERED_FACTORS['oi_vol_trend_ratio'] = oi_vol_trend_ratio
"""

with open('E:/quant-trading-mvp/quant/factors/discovered_factors.py', 'a', encoding='utf-8') as f:
    f.write(new_code)
print("6 batch-3 factors appended successfully")
