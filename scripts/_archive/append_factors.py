import sys
sys.path.insert(0, 'E:/quant-trading-mvp')

new_code = """

def support_resistance_oi(df):
    \"\"\"支撑阻力位OI交互：价格在极端位置时OI变化的EMA z-score
    avg |IC| = 0.0540, 4h IC=0.0665, 8h IC=0.0667
    \"\"\"
    import numpy as np
    rolling_high = df['high'].rolling(40, min_periods=10).max()
    rolling_low = df['low'].rolling(40, min_periods=10).min()
    pos = (df['close'] - rolling_low) / (rolling_high - rolling_low + 1e-10)
    oi_chg = df['open_interest'].pct_change()
    extreme = (pos > 0.8).astype(float) - (pos < 0.2).astype(float)
    signal = extreme * oi_chg
    cum_signal = signal.ewm(span=10, min_periods=5).mean()
    return (cum_signal - cum_signal.rolling(60, min_periods=20).mean()) / (cum_signal.rolling(60, min_periods=20).std() + 1e-10)

DISCOVERED_FACTORS['support_resistance_oi'] = support_resistance_oi


def hour_of_day_momentum(df):
    \"\"\"日内时段效应：各小时历史收益均值z-score
    avg |IC| = 0.0253, 2h IC=-0.0400
    \"\"\"
    import pandas as pd
    import numpy as np
    hour = df['timestamp'].dt.hour
    ret = df['close'].pct_change()
    result = pd.Series(0.0, index=df.index)
    for h_val in range(24):
        mask = hour == h_val
        if mask.sum() > 20:
            rolling_mean = ret[mask].expanding(min_periods=10).mean()
            result[mask] = rolling_mean
    return (result - result.rolling(100, min_periods=20).mean()) / (result.rolling(100, min_periods=20).std() + 1e-10)

DISCOVERED_FACTORS['hour_of_day_momentum'] = hour_of_day_momentum


def kurtosis_oi_signal(df):
    \"\"\"峰度OI信号：收益峰度乘以OI方向z-score
    avg |IC| = 0.0227, 8h IC=0.0400
    \"\"\"
    import numpy as np
    ret = df['close'].pct_change()
    kurt = ret.rolling(30, min_periods=15).apply(lambda x: x.kurtosis(), raw=False)
    oi_dir = np.sign(df['open_interest'].diff(5))
    signal = kurt * oi_dir
    return (signal - signal.rolling(60, min_periods=20).mean()) / (signal.rolling(60, min_periods=20).std() + 1e-10)

DISCOVERED_FACTORS['kurtosis_oi_signal'] = kurtosis_oi_signal


def amihud_oi_weighted(df):
    \"\"\"Amihud非流动性OI加权：非流动性取反乘以OI动量方向z-score
    avg |IC| = 0.0252, 8h IC=0.0393
    \"\"\"
    import numpy as np
    ret = df['close'].pct_change().abs()
    illiq = ret / (df['volume'] + 1)
    illiq_z = (illiq - illiq.rolling(60, min_periods=20).mean()) / (illiq.rolling(60, min_periods=20).std() + 1e-10)
    oi_mom = df['open_interest'].pct_change(5)
    signal = -illiq_z * np.sign(oi_mom)
    return (signal - signal.rolling(60, min_periods=20).mean()) / (signal.rolling(60, min_periods=20).std() + 1e-10)

DISCOVERED_FACTORS['amihud_oi_weighted'] = amihud_oi_weighted


def doji_reversal_oi(df):
    \"\"\"十字星反转OI确认：十字星时OI方向取反的EMA z-score
    avg |IC| = 0.0279, 8h IC=-0.0462
    \"\"\"
    import numpy as np
    body = abs(df['close'] - df['open'])
    total_range = df['high'] - df['low'] + 1e-10
    body_ratio = body / total_range
    is_doji = (body_ratio < 0.15).astype(float)
    oi_dir = np.sign(df['open_interest'].diff())
    signal = -is_doji * oi_dir
    cum_signal = signal.ewm(span=10, min_periods=5).mean()
    return (cum_signal - cum_signal.rolling(60, min_periods=20).mean()) / (cum_signal.rolling(60, min_periods=20).std() + 1e-10)

DISCOVERED_FACTORS['doji_reversal_oi'] = doji_reversal_oi


def parkinson_vol_oi(df):
    \"\"\"Parkinson波动率收缩OI积累：低波动率时OI方向z-score
    avg |IC| = 0.0482, 4h IC=0.0590, 8h IC=0.0603
    \"\"\"
    import numpy as np
    hl = np.log(df['high'] / df['low'])
    park_vol = np.sqrt(hl**2 / (4 * np.log(2)))
    park_short = park_vol.rolling(5, min_periods=3).mean()
    park_long = park_vol.rolling(30, min_periods=10).mean()
    vol_ratio = park_short / (park_long + 1e-10)
    oi_mom = df['open_interest'].pct_change(10)
    signal = (1 / (vol_ratio + 0.1)) * np.sign(oi_mom)
    return (signal - signal.rolling(60, min_periods=20).mean()) / (signal.rolling(60, min_periods=20).std() + 1e-10)

DISCOVERED_FACTORS['parkinson_vol_oi'] = parkinson_vol_oi


def garman_klass_oi(df):
    \"\"\"Garman-Klass波动率变化OI交互：GK波动率变化乘以OI方向z-score
    avg |IC| = 0.0224, 2h IC=0.0363
    \"\"\"
    import numpy as np
    log_hl = np.log(df['high'] / df['low'])
    log_co = np.log(df['close'] / df['open'])
    gk = 0.5 * log_hl**2 - (2*np.log(2) - 1) * log_co**2
    gk_vol = np.sqrt(gk.rolling(20, min_periods=10).mean().clip(lower=0))
    gk_short = np.sqrt(gk.rolling(5, min_periods=3).mean().clip(lower=0))
    vol_change = (gk_short - gk_vol) / (gk_vol + 1e-10)
    oi_dir = np.sign(df['open_interest'].diff(5))
    signal = vol_change * oi_dir
    return (signal - signal.rolling(60, min_periods=20).mean()) / (signal.rolling(60, min_periods=20).std() + 1e-10)

DISCOVERED_FACTORS['garman_klass_oi'] = garman_klass_oi
"""

with open('E:/quant-trading-mvp/quant/factors/discovered_factors.py', 'a', encoding='utf-8') as f:
    f.write(new_code)
print('Appended 7 new effective factors to discovered_factors.py')
