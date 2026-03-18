import psycopg2

conn = psycopg2.connect(host='localhost', port=5432, dbname='quant_trading', user='postgres', password='@Cmx1454697261')
cursor = conn.cursor()

# 检查有哪些 symbol
cursor.execute("SELECT DISTINCT symbol FROM kline_data LIMIT 20")
symbols = cursor.fetchall()
print(f'Symbols available: {[s[0] for s in symbols]}')

# 检查 au2606 有哪些 interval
cursor.execute("SELECT DISTINCT interval FROM kline_data WHERE symbol='au2606'")
intervals = cursor.fetchall()
print(f'\nau2606 intervals: {[i[0] for i in intervals]}')

# 检查 au 开头的合约
cursor.execute("SELECT DISTINCT symbol FROM kline_data WHERE symbol LIKE 'au%' LIMIT 20")
au_symbols = cursor.fetchall()
print(f'\nAU symbols: {[s[0] for s in au_symbols]}')

conn.close()
