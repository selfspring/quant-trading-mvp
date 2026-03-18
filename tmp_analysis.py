from quant.signal_generator.ml_predictor import MLPredictor
import pandas as pd
import psycopg2

# 连接数据库
conn = psycopg2.connect(
    host='localhost',
    port=5432,
    dbname='quant_trading',
    user='postgres',
    password='@Cmx1454697261'
)

# au2606 只有 1m 数据，获取最多数据
df = pd.read_sql("""
    SELECT time as timestamp, open, high, low, close, volume, 
           COALESCE(open_interest, 0) as open_interest 
    FROM kline_data 
    WHERE symbol='au2606' AND interval='1m' 
    ORDER BY time DESC 
    LIMIT 200
""", conn)
conn.close()

if len(df) == 0:
    print("No data found for au2606")
else:
    # 排序
    df = df.sort_values('timestamp').reset_index(drop=True)
    
    print(f"Data rows: {len(df)}")
    print(f"Latest time: {df.iloc[-1]['timestamp']}")
    print(f"Latest price: {df.iloc[-1]['close']}")
    print(f"Last 5 closes: {df['close'].tail(5).tolist()}")
    
    # 尝试预测（如果数据足够）
    if len(df) >= 60:
        predictor = MLPredictor()
        result = predictor.predict(df)
        print('\nML Prediction:', result)
    else:
        print(f"\nNot enough data for ML prediction (need 60, have {len(df)})")
