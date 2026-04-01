import sys, io, requests, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import psycopg2
import hashlib
from datetime import date

FRED_KEY = '4a2f776eaba16b7aa835947dbc060a99'
FRED_BASE = 'https://api.stlouisfed.org/fred'

# 分段拉取 VIX 完整历史
print('获取 VIX (VIXCLS) 2013-2026...')
all_obs = []
for start_y, end_y in [('2013-01-01','2017-12-31'),('2018-01-01','2021-12-31'),('2022-01-01','2026-03-21')]:
    url = (f"{FRED_BASE}/series/observations"
           f"?series_id=VIXCLS"
           f"&observation_start={start_y}"
           f"&observation_end={end_y}"
           f"&api_key={FRED_KEY}"
           f"&file_type=json"
           f"&limit=2000")
    r = requests.get(url, timeout=15, proxies={'http': None, 'https': None})
    r.raise_for_status()
    all_obs.extend(r.json().get('observations', []))
    time.sleep(0.3)

# 过滤有效值
vix_data = [(o['date'], float(o['value'])) for o in all_obs if o.get('value') not in ('.', '', None)]
print(f'VIX数据: {len(vix_data)} 条 ({vix_data[0][0]} ~ {vix_data[-1][0]})')

# 找 VIX 阈值突破事件
# 策略: 找每次从<20突破到>=30、从<30突破到>=40的第一天
VIX_THRESHOLDS = [
    (30, 'VIX_30', 'VIX spike above 30 - elevated market fear'),
    (40, 'VIX_40', 'VIX spike above 40 - extreme market panic'),
]

events = []
prev_vix = None

for d_str, vix in vix_data:
    for threshold, event_type, base_desc in VIX_THRESHOLDS:
        lower = threshold - 10
        if prev_vix is not None and prev_vix < threshold <= vix:
            # 突破阈值的第一天
            desc = f"{base_desc}: {prev_vix:.1f} -> {vix:.1f}"
            events.append({
                'event_type': event_type,
                'event_date': d_str,
                'event_time_utc': f"{d_str}T21:00:00Z",  # 收盘时
                'year': int(d_str[:4]),
                'month': int(d_str[5:7]),
                'importance': 'high',
                'description': desc,
                'source': 'fred.stlouisfed.org',
                'source_url': 'https://fred.stlouisfed.org/series/VIXCLS',
                'vix_value': vix,
            })
    prev_vix = vix

print(f'\nVIX阈值突破事件: {len(events)} 条')
for e in events:
    print(f"  {e['event_date']} | {e['event_type']} | {e['description']}")

# 入库 macro_events
conn = psycopg2.connect(host='localhost', port=5432, database='quant_trading', user='postgres', password='@Cmx1454697261')
cur = conn.cursor()

# 先确认表有 event_type UNIQUE 约束
inserted_macro = 0
for e in events:
    try:
        cur.execute("""
            INSERT INTO macro_events (event_type, event_date, event_time_utc, year, month, importance, description, source, source_url)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (event_type, event_date) DO NOTHING
        """, (e['event_type'], e['event_date'], e['event_time_utc'], e['year'], e['month'],
               e['importance'], e['description'], e['source'], e['source_url']))
        if cur.rowcount > 0:
            inserted_macro += 1
    except Exception as ex:
        print(f"  macro_events error: {ex}")

# 同时写入 news_raw
inserted_news = 0
for e in events:
    title = f"Market Fear Spike: {e['event_type']} - {e['description']}"
    content = f"{e['description']}\nVIX Index measures implied volatility of S&P500 options. High VIX indicates market fear and uncertainty, typically bullish for gold as safe haven.\nSource: CBOE VIX via FRED"
    content_hash = hashlib.md5(f"VIX:{e['event_date']}:{e['event_type']}".encode()).hexdigest()
    try:
        cur.execute("""
            INSERT INTO news_raw (time, source, title, content, url, content_hash)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (content_hash) DO NOTHING
        """, (e['event_time_utc'], f"macro_{e['event_type'].lower()}", title, content,
               e['source_url'], content_hash))
        if cur.rowcount > 0:
            inserted_news += 1
    except Exception as ex:
        print(f"  news_raw error: {ex}")

conn.commit()
print(f'\nmacro_events 新增: {inserted_macro} 条')
print(f'news_raw 新增: {inserted_news} 条')

# 验证
cur.execute("SELECT event_type, COUNT(*) FROM macro_events WHERE event_type LIKE 'VIX%' GROUP BY event_type")
for row in cur.fetchall():
    print(f'  DB: {row[0]}: {row[1]} 条')
conn.close()
