"""
建表并导入宏观数据 CSV 到 PostgreSQL
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pandas as pd
from quant.common.config import config
from quant.common.db import db_connection, db_engine

DDL = """
CREATE TABLE IF NOT EXISTS macro_daily (
    date DATE NOT NULL,
    indicator VARCHAR(50) NOT NULL,
    value DECIMAL(20, 6),
    PRIMARY KEY (date, indicator)
);

CREATE TABLE IF NOT EXISTS fut_holding (
    trade_date DATE NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    broker VARCHAR(50) NOT NULL,
    vol BIGINT,
    vol_chg BIGINT,
    long_hld BIGINT,
    long_chg BIGINT,
    short_hld BIGINT,
    short_chg BIGINT,
    PRIMARY KEY (trade_date, symbol, broker)
);

CREATE TABLE IF NOT EXISTS macro_monthly (
    month VARCHAR(10) NOT NULL,
    indicator VARCHAR(50) NOT NULL,
    value DECIMAL(20, 6),
    PRIMARY KEY (month, indicator)
);

CREATE TABLE IF NOT EXISTS eco_calendar (
    date DATE,
    time VARCHAR(20),
    country VARCHAR(20),
    event VARCHAR(200),
    value VARCHAR(50),
    previous VARCHAR(50),
    forecast VARCHAR(50),
    PRIMARY KEY (date, event)
);

CREATE TABLE IF NOT EXISTS shfe_monthly (
    month VARCHAR(10) NOT NULL,
    inc_month DECIMAL(20, 6),
    inc_cumval DECIMAL(20, 6),
    stk_endval DECIMAL(20, 6),
    PRIMARY KEY (month)
);
"""


def create_tables(conn):
    cur = conn.cursor()
    cur.execute(DDL)
    conn.commit()
    print("Tables created.")


def parse_date(val):
    """Parse date string like '20260318' to date."""
    s = str(int(val))
    return pd.to_datetime(s, format='%Y%m%d').date()


def import_shibor(conn):
    df = pd.read_csv('data/shibor.csv')
    col_map = {
        'on': 'shibor_on', '1w': 'shibor_1w', '2w': 'shibor_2w',
        '1m': 'shibor_1m', '3m': 'shibor_3m', '6m': 'shibor_6m',
        '9m': 'shibor_9m', '1y': 'shibor_1y'
    }
    cur = conn.cursor()
    sql = "INSERT INTO macro_daily (date, indicator, value) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING"
    count = 0
    for _, row in df.iterrows():
        d = parse_date(row['date'])
        for col, ind in col_map.items():
            v = row[col]
            if pd.notna(v):
                cur.execute(sql, (d, ind, float(v)))
                count += 1
    conn.commit()
    print(f"shibor: {count} rows inserted")


def import_us_treasury(conn):
    df = pd.read_csv('data/us_treasury.csv')
    col_map = {
        'm1': 'us_1m', 'm2': 'us_2m', 'm3': 'us_3m', 'm6': 'us_6m',
        'y1': 'us_1y', 'y2': 'us_2y', 'y3': 'us_3y', 'y5': 'us_5y',
        'y7': 'us_7y', 'y10': 'us_10y', 'y20': 'us_20y', 'y30': 'us_30y'
    }
    cur = conn.cursor()
    sql = "INSERT INTO macro_daily (date, indicator, value) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING"
    count = 0
    for _, row in df.iterrows():
        d = parse_date(row['date'])
        for col, ind in col_map.items():
            v = row[col]
            if pd.notna(v):
                cur.execute(sql, (d, ind, float(v)))
                count += 1
    conn.commit()
    print(f"us_treasury: {count} rows inserted")


def import_fut_holding(conn):
    df = pd.read_csv('data/fut_holding_au.csv')
    cur = conn.cursor()
    sql = """INSERT INTO fut_holding (trade_date, symbol, broker, vol, vol_chg, long_hld, long_chg, short_hld, short_chg)
             VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING"""
    count = 0
    for _, row in df.iterrows():
        d = parse_date(row['trade_date'])
        cur.execute(sql, (
            d, row['symbol'], row['broker'],
            int(row['vol']) if pd.notna(row['vol']) else None,
            int(row['vol_chg']) if pd.notna(row['vol_chg']) else None,
            int(row['long_hld']) if pd.notna(row['long_hld']) else None,
            int(row['long_chg']) if pd.notna(row['long_chg']) else None,
            int(row['short_hld']) if pd.notna(row['short_hld']) else None,
            int(row['short_chg']) if pd.notna(row['short_chg']) else None,
        ))
        count += 1
    conn.commit()
    print(f"fut_holding: {count} rows inserted")


def import_cn_cpi(conn):
    df = pd.read_csv('data/cn_cpi.csv')
    cur = conn.cursor()
    sql = "INSERT INTO macro_monthly (month, indicator, value) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING"
    col_map = {
        'nt_val': 'cpi_nt_val', 'nt_yoy': 'cpi_nt_yoy', 'nt_mom': 'cpi_nt_mom', 'nt_accu': 'cpi_nt_accu',
        'town_val': 'cpi_town_val', 'town_yoy': 'cpi_town_yoy', 'town_mom': 'cpi_town_mom', 'town_accu': 'cpi_town_accu',
        'cnt_val': 'cpi_cnt_val', 'cnt_yoy': 'cpi_cnt_yoy', 'cnt_mom': 'cpi_cnt_mom', 'cnt_accu': 'cpi_cnt_accu',
    }
    count = 0
    for _, row in df.iterrows():
        m = str(row['month'])
        for col, ind in col_map.items():
            v = row.get(col)
            if pd.notna(v):
                cur.execute(sql, (m, ind, float(v)))
                count += 1
    conn.commit()
    print(f"cn_cpi: {count} rows inserted")


def import_cn_ppi(conn):
    df = pd.read_csv('data/cn_ppi.csv')
    cur = conn.cursor()
    sql = "INSERT INTO macro_monthly (month, indicator, value) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING"
    # Import key PPI columns
    key_cols = ['ppi_yoy', 'ppi_mom', 'ppi_accu', 'ppi_mp_yoy', 'ppi_cg_yoy']
    count = 0
    for _, row in df.iterrows():
        m = str(row['month'])
        for col in key_cols:
            v = row.get(col)
            if pd.notna(v):
                cur.execute(sql, (m, col, float(v)))
                count += 1
    conn.commit()
    print(f"cn_ppi: {count} rows inserted")


def import_cn_money_supply(conn):
    df = pd.read_csv('data/cn_money_supply.csv')
    cur = conn.cursor()
    sql = "INSERT INTO macro_monthly (month, indicator, value) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING"
    col_map = {
        'm0': 'm0', 'm0_yoy': 'm0_yoy', 'm0_mom': 'm0_mom',
        'm1': 'm1', 'm1_yoy': 'm1_yoy', 'm1_mom': 'm1_mom',
        'm2': 'm2', 'm2_yoy': 'm2_yoy', 'm2_mom': 'm2_mom',
    }
    count = 0
    for _, row in df.iterrows():
        m = str(row['month'])
        for col, ind in col_map.items():
            v = row.get(col)
            if pd.notna(v):
                cur.execute(sql, (m, ind, float(v)))
                count += 1
    conn.commit()
    print(f"cn_money_supply: {count} rows inserted")


def import_cn_gdp(conn):
    df = pd.read_csv('data/cn_gdp.csv')
    cur = conn.cursor()
    sql = "INSERT INTO macro_monthly (month, indicator, value) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING"
    col_map = {
        'gdp': 'gdp', 'gdp_yoy': 'gdp_yoy',
        'pi': 'gdp_pi', 'pi_yoy': 'gdp_pi_yoy',
        'si': 'gdp_si', 'si_yoy': 'gdp_si_yoy',
        'ti': 'gdp_ti', 'ti_yoy': 'gdp_ti_yoy',
    }
    count = 0
    for _, row in df.iterrows():
        m = str(row['quarter'])
        for col, ind in col_map.items():
            v = row.get(col)
            if pd.notna(v):
                cur.execute(sql, (m, ind, float(v)))
                count += 1
    conn.commit()
    print(f"cn_gdp: {count} rows inserted")


def import_eco_calendar(conn):
    df = pd.read_csv('data/eco_calendar.csv')
    cur = conn.cursor()
    sql = """INSERT INTO eco_calendar (date, time, country, event, value, previous, forecast)
             VALUES (%s, %s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING"""
    count = 0
    for _, row in df.iterrows():
        d = parse_date(row['date'])
        cur.execute(sql, (
            d,
            str(row['time']) if pd.notna(row['time']) else None,
            str(row['country']) if pd.notna(row['country']) else None,
            str(row['event']) if pd.notna(row['event']) else None,
            str(row['value']) if pd.notna(row['value']) else None,
            str(row['pre_value']) if pd.notna(row['pre_value']) else None,
            str(row['fore_value']) if pd.notna(row['fore_value']) else None,
        ))
        count += 1
    conn.commit()
    print(f"eco_calendar: {count} rows inserted")


def import_shfe_monthly(conn):
    df = pd.read_csv('data/shfe_monthly.csv')
    cur = conn.cursor()
    sql = """INSERT INTO shfe_monthly (month, inc_month, inc_cumval, stk_endval)
             VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING"""
    count = 0
    for _, row in df.iterrows():
        cur.execute(sql, (
            str(row['month']),
            float(row['inc_month']) if pd.notna(row['inc_month']) else None,
            float(row['inc_cumval']) if pd.notna(row['inc_cumval']) else None,
            float(row['stk_endval']) if pd.notna(row['stk_endval']) else None,
        ))
        count += 1
    conn.commit()
    print(f"shfe_monthly: {count} rows inserted")


def print_counts(conn):
    cur = conn.cursor()
    tables = ['macro_daily', 'fut_holding', 'macro_monthly', 'eco_calendar', 'shfe_monthly']
    print("\n=== Table row counts ===")
    for t in tables:
        cur.execute(f"SELECT COUNT(*) FROM {t}")
        print(f"  {t}: {cur.fetchone()[0]}")


if __name__ == '__main__':
    os.chdir(os.path.join(os.path.dirname(__file__), '..'))
    with db_connection(config) as conn:
        create_tables(conn)
        import_shibor(conn)
        import_us_treasury(conn)
        import_fut_holding(conn)
        import_cn_cpi(conn)
        import_cn_ppi(conn)
        import_cn_money_supply(conn)
        import_cn_gdp(conn)
        import_eco_calendar(conn)
        import_shfe_monthly(conn)
        print_counts(conn)
    print("\nDone.")
