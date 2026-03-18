import psycopg2
from datetime import datetime

conn = psycopg2.connect(
    host='localhost',
    port=5432,
    database='quant_trading',
    user='postgres',
    password='@Cmx1454697261'
)
cur = conn.cursor()

# 检查各表的数据量和时间范围
tables = ['market_data', 'kline_1min', 'signals', 'trades', 'positions']

for table in tables:
    try:
        cur.execute(f'SELECT COUNT(*) FROM {table}')
        count = cur.fetchone()[0]
        print(f'\n{table}: {count} 条记录')
        
        if count > 0:
            # 获取时间范围
            if table == 'market_data':
                cur.execute(f'SELECT MIN(update_time), MAX(update_time) FROM {table}')
            elif table in ['kline_1min', 'signals']:
                cur.execute(f'SELECT MIN(timestamp), MAX(timestamp) FROM {table}')
            elif table == 'trades':
                cur.execute(f'SELECT MIN(trade_time), MAX(trade_time) FROM {table}')
            elif table == 'positions':
                cur.execute(f'SELECT MIN(update_time), MAX(update_time) FROM {table}')
            
            time_range = cur.fetchone()
            if time_range[0]:
                print(f'  时间范围: {time_range[0]} ~ {time_range[1]}')
            
            # 显示最新几条记录
            if table == 'kline_1min':
                cur.execute(f'SELECT timestamp, symbol, close, volume FROM {table} ORDER BY timestamp DESC LIMIT 3')
                print('  最新 3 条:')
                for row in cur.fetchall():
                    print(f'    {row}')
            elif table == 'signals':
                cur.execute(f'SELECT timestamp, symbol, signal_type, confidence FROM {table} ORDER BY timestamp DESC LIMIT 3')
                print('  最新 3 条:')
                for row in cur.fetchall():
                    print(f'    {row}')
    except Exception as e:
        print(f'{table}: 查询失败 - {e}')

cur.close()
conn.close()
