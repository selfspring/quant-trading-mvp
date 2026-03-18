import psycopg2
conn = psycopg2.connect('dbname=quant_trading user=postgres password=@Cmx1454697261 host=localhost')
cur = conn.cursor()

# 检查数据
cur.execute("SELECT COUNT(*), symbol, interval FROM kline_data GROUP BY symbol, interval")
print("数据库中的 K 线数据:")
for row in cur.fetchall():
    print(f"  {row[1]} {row[2]}: {row[0]} 根")

# 检查 symbol 大小写
cur.execute("SELECT DISTINCT symbol FROM kline_data")
print("\n所有 symbol:")
for row in cur.fetchall():
    print(f"  '{row[0]}'")

# 查看策略查询用的参数
symbol = 'au2604'
print(f"\n策略查询参数: symbol='{symbol.upper()}', interval='1min'")

cur.execute("SELECT COUNT(*) FROM kline_data WHERE symbol = %s AND interval = %s", (symbol.upper(), '1min'))
print(f"大写查询结果: {cur.fetchone()[0]}")

cur.execute("SELECT COUNT(*) FROM kline_data WHERE symbol = %s AND interval = %s", (symbol, '1min'))
print(f"小写查询结果: {cur.fetchone()[0]}")

conn.close()
