"""拼接多合约1m数据为连续序列，并聚合30m"""
import sys
sys.path.insert(0, 'E:/quant-trading-mvp')

import pandas as pd
import numpy as np
from quant.common.config import config
from quant.common.db import db_engine, db_connection


def main():
    # 1. 读取所有1m数据
    with db_engine(config) as engine:
        df = pd.read_sql("""
            SELECT time as timestamp, symbol, open, high, low, close, volume, open_interest
            FROM kline_data
            WHERE interval = '1m'
              AND symbol IN ('au2504','au2506','au2508','au2510','au2512','au_main')
            ORDER BY time
        """, engine)

    print(f"Total 1m rows: {len(df)}")

    # 2. 去重：同一时间戳保留 au_main 优先，否则取第一个
    df['priority'] = df['symbol'].apply(lambda x: 0 if x == 'au_main' else 1)
    df = df.sort_values(['timestamp', 'priority']).drop_duplicates(subset='timestamp', keep='first')
    df = df.drop(columns=['priority']).sort_values('timestamp').reset_index(drop=True)
    print(f"After dedup: {len(df)} rows, {df.timestamp.min()} ~ {df.timestamp.max()}")

    # 3. 换月价差调整（简单加法调整）
    symbols = df['symbol'].values
    closes = df['close'].values.copy()

    adjustment = 0.0
    for i in range(1, len(df)):
        if symbols[i] != symbols[i-1]:
            gap = closes[i] - closes[i-1]
            adjustment += gap
            print(f"  Switch {symbols[i-1]} -> {symbols[i]} at {df.iloc[i]['timestamp']}, gap={gap:.2f}, cumulative adj={adjustment:.2f}")

    # 应用调整：从后往前，每个合约段加上后续的累计调整
    adj_values = np.zeros(len(df))
    current_adj = 0.0
    current_symbol = symbols[-1]
    for i in range(len(df)-1, -1, -1):
        if symbols[i] != current_symbol:
            gap = closes[i+1] - closes[i]
            current_adj -= gap
            current_symbol = symbols[i]
        adj_values[i] = current_adj

    df['open'] = df['open'] + adj_values
    df['high'] = df['high'] + adj_values
    df['low'] = df['low'] + adj_values
    df['close'] = df['close'] + adj_values
    print(f"Price adjusted. Final range: {df['close'].min():.2f} ~ {df['close'].max():.2f}")

    # 4. 保存1m到数据库
    with db_connection(config) as conn:
        cur = conn.cursor()
        inserted = 0
        for _, row in df.iterrows():
            cur.execute("""
                INSERT INTO kline_data (time, symbol, interval, open, high, low, close, volume, open_interest)
                VALUES (%s, 'au_continuous', '1m', %s, %s, %s, %s, %s, %s)
                ON CONFLICT (time, symbol, interval) DO NOTHING
            """, (row['timestamp'], float(row['open']), float(row['high']),
                  float(row['low']), float(row['close']),
                  float(row['volume']), float(row['open_interest'])))
            inserted += cur.rowcount
        conn.commit()
    print(f"1m inserted: {inserted}")

    # 5. 聚合30m
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.set_index('timestamp')
    df_30m = df.resample('30min').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum',
        'open_interest': 'last'
    }).dropna().reset_index()

    print(f"30m aggregated: {len(df_30m)} rows")

    with db_connection(config) as conn:
        cur = conn.cursor()
        inserted = 0
        for _, row in df_30m.iterrows():
            cur.execute("""
                INSERT INTO kline_data (time, symbol, interval, open, high, low, close, volume, open_interest)
                VALUES (%s, 'au_continuous', '30m', %s, %s, %s, %s, %s, %s)
                ON CONFLICT (time, symbol, interval) DO NOTHING
            """, (row['timestamp'], float(row['open']), float(row['high']),
                  float(row['low']), float(row['close']),
                  float(row['volume']), float(row['open_interest'])))
            inserted += cur.rowcount
        conn.commit()
    print(f"30m inserted: {inserted}")


if __name__ == '__main__':
    main()
