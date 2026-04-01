import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import psycopg2
import hashlib

# 精确地缘政治+市场重大事件清单（有明确日期，对黄金有重大影响）
GEO_EVENTS = [
    # 俄乌战争
    ('GEO', '2022-02-24', '2022-02-24T02:00:00Z', 'Russia invades Ukraine - Full-scale military invasion begins, major geopolitical shock bullish for gold'),
    ('GEO', '2022-03-16', '2022-03-16T00:00:00Z', 'Ukraine war escalation - NATO warns of prolonged conflict, gold safe haven demand surges'),
    ('GEO', '2023-06-06', '2023-06-06T00:00:00Z', 'Ukraine Kakhovka dam destroyed - Escalation of infrastructure attacks in Russia-Ukraine war'),
    ('GEO', '2024-02-17', '2024-02-17T00:00:00Z', 'Avdiivka falls to Russia - Significant Ukrainian military setback, geopolitical risk elevated'),

    # 中东冲突
    ('GEO', '2023-10-07', '2023-10-07T06:00:00Z', 'Hamas attacks Israel - October 7 attack triggers Israel-Gaza war, massive safe haven gold demand'),
    ('GEO', '2023-10-17', '2023-10-17T00:00:00Z', 'Israel ground invasion Gaza begins - Middle East war escalation, gold spikes'),
    ('GEO', '2024-04-13', '2024-04-13T22:00:00Z', 'Iran attacks Israel directly - First direct Iran-Israel military exchange, extreme gold rally'),
    ('GEO', '2024-04-19', '2024-04-19T00:00:00Z', 'Israel retaliates against Iran - Risk of broader Middle East war, gold hits record'),
    ('GEO', '2025-03-15', '2025-03-15T00:00:00Z', 'US strikes Iran-backed Houthis in Yemen - Escalation of Middle East conflict'),

    # 新冠疫情
    ('GEO', '2020-01-20', '2020-01-20T00:00:00Z', 'WHO confirms human-to-human COVID-19 transmission - Pandemic risk begins affecting markets'),
    ('GEO', '2020-03-11', '2020-03-11T00:00:00Z', 'WHO declares COVID-19 pandemic - Global lockdowns begin, extreme market volatility'),
    ('GEO', '2020-03-23', '2020-03-23T00:00:00Z', 'Fed emergency QE unlimited - Fed announces unlimited asset purchases, gold surges'),

    # 美国政治/制裁
    ('GEO', '2018-08-07', '2018-08-07T00:00:00Z', 'US reimposed Iran sanctions - Trump reinstates Iran oil sanctions, geopolitical premium in gold'),
    ('GEO', '2019-05-10', '2019-05-10T00:00:00Z', 'US-China trade war escalation - Trump raises tariffs to 25% on $200B Chinese goods'),
    ('GEO', '2020-01-03', '2020-01-03T00:00:00Z', 'US kills Iranian general Soleimani - Drone strike kills top Iranian commander, gold spikes sharply'),
    ('GEO', '2022-02-26', '2022-02-26T00:00:00Z', 'Russia SWIFT sanctions - West cuts Russia from SWIFT banking system, ruble collapses'),
    ('GEO', '2025-04-02', '2025-04-02T00:00:00Z', "Trump Liberation Day tariffs - Sweeping global tariffs announced, market panic, gold safe haven surge"),

    # 全球金融危机/事件
    ('GEO', '2013-04-12', '2013-04-12T00:00:00Z', 'Gold flash crash - Gold drops $200 in two days, largest single-day drop in 30 years'),
    ('GEO', '2015-08-11', '2015-08-11T00:00:00Z', 'China yuan devaluation - PBOC devalues yuan 1.9%, triggers global risk-off'),
    ('GEO', '2016-06-24', '2016-06-24T00:00:00Z', 'Brexit vote shock - UK votes to leave EU, gold surges $60 in one day'),
    ('GEO', '2016-11-09', '2016-11-09T00:00:00Z', 'Trump elected US president - Unexpected election result, initial gold spike then reversal'),
    ('GEO', '2019-08-05', '2019-08-05T00:00:00Z', 'China labels US currency manipulator - Trade war peak, gold breaks above $1500'),
    ('GEO', '2023-03-10', '2023-03-10T00:00:00Z', 'Silicon Valley Bank collapse - US banking crisis begins, flight to gold safety'),
    ('GEO', '2023-05-01', '2023-05-01T00:00:00Z', 'First Republic Bank seized - Regional banking crisis continues, gold near all-time high'),
    ('GEO', '2024-08-05', '2024-08-05T00:00:00Z', 'Global markets crash - Yen carry trade unwind + recession fears, VIX hits 65, gold volatile'),
]

conn = psycopg2.connect(host='localhost', port=5432, database='quant_trading', user='postgres', password='@Cmx1454697261')
cur = conn.cursor()

inserted_macro = 0
inserted_news = 0

for event_type, event_date, event_time_utc, description in GEO_EVENTS:
    year = int(event_date[:4])
    month = int(event_date[5:7])

    # macro_events
    try:
        cur.execute("""
            INSERT INTO macro_events (event_type, event_date, event_time_utc, year, month, importance, description, source, source_url)
            VALUES (%s, %s, %s, %s, %s, 'high', %s, 'curated', 'https://en.wikipedia.org/wiki/Timeline_of_the_21st_century')
            ON CONFLICT (event_type, event_date) DO UPDATE SET description=EXCLUDED.description
        """, (event_type, event_date, event_time_utc, year, month, description))
        if cur.rowcount > 0:
            inserted_macro += 1
    except Exception as e:
        print(f'  macro error {event_date}: {e}')

    # news_raw
    title = f"Geopolitical Event: {description[:100]}"
    content = f"{description}\n\nThis is a major geopolitical event with significant impact on gold prices as a safe haven asset.\nEvent Date: {event_date}\nSource: Curated historical events database"
    content_hash = hashlib.md5(f"GEO:{event_date}:{description[:50]}".encode()).hexdigest()
    try:
        cur.execute("""
            INSERT INTO news_raw (time, source, title, content, url, content_hash)
            VALUES (%s, 'macro_geo', %s, %s, '', %s)
            ON CONFLICT (content_hash) DO NOTHING
        """, (event_time_utc, title, content, content_hash))
        if cur.rowcount > 0:
            inserted_news += 1
    except Exception as e:
        print(f'  news error {event_date}: {e}')

conn.commit()
print(f'macro_events 新增/更新: {inserted_macro} 条')
print(f'news_raw 新增: {inserted_news} 条')

# 验证
print('\n=== 地缘政治事件样本 ===')
cur.execute("SELECT event_date, LEFT(description, 80) FROM macro_events WHERE event_type='GEO' ORDER BY event_date")
for row in cur.fetchall():
    print(f'  {row[0]} | {row[1]}')

conn.close()
