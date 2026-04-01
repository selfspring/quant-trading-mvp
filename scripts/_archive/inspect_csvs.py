import pandas as pd

files = [
    'data/shibor.csv',
    'data/us_treasury.csv',
    'data/fut_holding_au.csv',
    'data/cn_cpi.csv',
    'data/cn_ppi.csv',
    'data/cn_money_supply.csv',
    'data/cn_gdp.csv',
    'data/eco_calendar.csv',
    'data/shfe_monthly.csv',
]

for f in files:
    print(f'=== {f} ===')
    df = pd.read_csv(f, nrows=3)
    print(df.columns.tolist())
    print(df.head())
    print()
