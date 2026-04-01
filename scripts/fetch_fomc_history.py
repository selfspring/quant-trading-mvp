"""
FOMC 历史会议数据采集脚本

数据源：
- 2021-2027: https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm
- 2013-2020: https://www.federalreserve.gov/monetarypolicy/fomchistorical{year}.htm

产出：
- data/fomc_events.json (结构化JSON)
- 可选入库到 PostgreSQL macro_events 表
"""
import sys
import io
import json
import re
from datetime import datetime, date
from pathlib import Path

if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import requests
from bs4 import BeautifulSoup


def fetch_page(url: str) -> BeautifulSoup:
    """抓取页面并返回BeautifulSoup对象"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    resp = requests.get(url, headers=headers, timeout=30, proxies={"http": None, "https": None})
    resp.raise_for_status()
    return BeautifulSoup(resp.text, "html.parser")


def parse_calendars_page(soup: BeautifulSoup) -> list:
    """解析 fomccalendars.htm (2021-2027)
    
    页面结构：纯文本中按 "YYYY FOMC Meetings" 分段，
    每段内 "Month\n  day1-day2[*]" 交替出现。
    直接用全文文本正则匹配更可靠。
    """
    events = []
    full_text = soup.get_text("\n", strip=False)
    
    months = {
        'January': 1, 'February': 2, 'March': 3, 'April': 4,
        'May': 5, 'June': 6, 'July': 7, 'August': 8,
        'September': 9, 'October': 10, 'November': 11, 'December': 12,
    }
    
    # 按年份分段
    year_sections = re.split(r'(\d{4})\s+FOMC\s+Meetings', full_text)
    # year_sections: [preamble, "2026", section_text, "2025", section_text, ...]
    
    for i in range(1, len(year_sections) - 1, 2):
        year = int(year_sections[i])
        section = year_sections[i + 1]
        
        # 匹配: 月份名 后面跟着 数字-数字 可能有*
        # 页面格式是月份和日期分开在不同行
        current_month = None
        for line in section.split('\n'):
            line = line.strip()
            # 检查是否是月份行
            for mname, mnum in months.items():
                if line == mname or line.startswith(mname + '/'):
                    current_month = mnum
                    # 处理 "Apr/May" 这种跨月格式
                    if '/' in line:
                        parts = line.split('/')
                        current_month = months.get(parts[0].strip(), mnum)
                    break
            
            # 检查是否是日期行: "27-28" 或 "17-18*" 或 "30-1"
            if current_month is not None:
                date_match = re.match(r'^(\d{1,2})[-–](\d{1,2})(\*?)$', line)
                if date_match:
                    day_start = int(date_match.group(1))
                    day_end = int(date_match.group(2))
                    has_sep = date_match.group(3) == '*'
                    
                    end_month = current_month
                    if day_end < day_start:
                        end_month = current_month + 1
                    
                    try:
                        meeting_date = date(year, end_month, day_end)
                        event = {
                            "event_type": "FOMC",
                            "event_date": meeting_date.isoformat(),
                            "event_time_utc": f"{meeting_date.isoformat()}T18:00:00Z",
                            "year": year,
                            "month": current_month,
                            "day_range": f"{day_start}-{day_end}",
                            "has_sep": has_sep,
                            "importance": "high",
                            "source": "federalreserve.gov",
                            "source_url": "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm",
                        }
                        events.append(event)
                    except ValueError:
                        pass
    
    return events


def parse_historical_page(soup: BeautifulSoup, year: int) -> list:
    """解析 fomchistoricalYYYY.htm (2013-2020)"""
    events = []
    
    months = {
        'January': 1, 'February': 2, 'March': 3, 'April': 4,
        'May': 5, 'June': 6, 'July': 7, 'August': 8,
        'September': 9, 'October': 10, 'November': 11, 'December': 12,
    }
    
    # 找 panel-heading 里的会议日期
    panels = soup.find_all(class_="panel-heading")
    
    for panel in panels:
        text = panel.get_text(" ", strip=True)
        
        # 匹配格式: "Meeting - January 27-28, 2015" 或 "January 27-28, 2015"
        date_pattern = re.compile(
            r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+'
            r'(\d{1,2})[-–](\d{1,2}),?\s*(\d{4})?'
        )
        
        m = date_pattern.search(text)
        if not m:
            continue
        
        month_name = m.group(1)
        day_start = int(m.group(2))
        day_end = int(m.group(3))
        event_year = int(m.group(4)) if m.group(4) else year
        month = months.get(month_name, 0)
        if month == 0:
            continue
        
        end_month = month
        if day_end < day_start:
            end_month = month + 1
        
        # 检查是否有 SEP (Summary of Economic Projections)
        panel_body = panel.find_next_sibling(class_="panel-body")
        has_sep = False
        if panel_body:
            body_text = panel_body.get_text()
            has_sep = "Summary of Economic Projections" in body_text or "SEP" in body_text
        
        try:
            meeting_date = date(event_year, end_month, day_end)
            event = {
                "event_type": "FOMC",
                "event_date": meeting_date.isoformat(),
                "event_time_utc": f"{meeting_date.isoformat()}T18:00:00Z",
                "year": event_year,
                "month": month,
                "day_range": f"{day_start}-{day_end}",
                "has_sep": has_sep,
                "importance": "high",
                "source": "federalreserve.gov",
                "source_url": f"https://www.federalreserve.gov/monetarypolicy/fomchistorical{event_year}.htm",
            }
            events.append(event)
        except ValueError:
            pass
    
    return events


def save_to_db(events: list):
    """保存到 PostgreSQL macro_events 表"""
    import psycopg2
    
    conn = psycopg2.connect(
        host='localhost', port=5432, database='quant_trading',
        user='postgres', password='@Cmx1454697261'
    )
    cur = conn.cursor()
    
    # 建表
    cur.execute("""
        CREATE TABLE IF NOT EXISTS macro_events (
            id SERIAL PRIMARY KEY,
            event_type VARCHAR(50) NOT NULL,
            event_date DATE NOT NULL,
            event_time_utc TIMESTAMP WITH TIME ZONE,
            year INT,
            month INT,
            day_range VARCHAR(20),
            has_sep BOOLEAN DEFAULT FALSE,
            importance VARCHAR(20) DEFAULT 'high',
            description TEXT,
            decision TEXT,
            rate_before NUMERIC,
            rate_after NUMERIC,
            source VARCHAR(100),
            source_url TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            UNIQUE(event_type, event_date)
        );
    """)
    conn.commit()
    
    inserted = 0
    for e in events:
        try:
            cur.execute("""
                INSERT INTO macro_events (event_type, event_date, event_time_utc, year, month,
                    day_range, has_sep, importance, source, source_url)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (event_type, event_date) DO NOTHING
            """, (
                e["event_type"], e["event_date"], e["event_time_utc"],
                e["year"], e["month"], e["day_range"], e["has_sep"],
                e["importance"], e["source"], e["source_url"],
            ))
            if cur.rowcount > 0:
                inserted += 1
        except Exception as ex:
            print(f"  Skip {e['event_date']}: {ex}")
    
    conn.commit()
    conn.close()
    return inserted


def main():
    all_events = []
    
    # 1. 抓取 2021-2027 (fomccalendars.htm)
    print("=== 抓取 fomccalendars.htm (2021-2027) ===")
    url = "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"
    soup = fetch_page(url)
    events = parse_calendars_page(soup)
    print(f"  找到 {len(events)} 条 FOMC 事件")
    all_events.extend(events)
    
    # 2. 抓取 2013-2020 (fomchistoricalYYYY.htm)
    for year in range(2013, 2021):
        url = f"https://www.federalreserve.gov/monetarypolicy/fomchistorical{year}.htm"
        print(f"=== 抓取 {url} ===")
        try:
            soup = fetch_page(url)
            events = parse_historical_page(soup, year)
            print(f"  找到 {len(events)} 条 FOMC 事件")
            all_events.extend(events)
        except Exception as e:
            print(f"  抓取失败: {e}")
    
    # 3. 按日期排序
    all_events.sort(key=lambda x: x["event_date"])
    
    # 4. 保存 JSON
    output_dir = Path(__file__).parent.parent / "data"
    output_dir.mkdir(exist_ok=True)
    json_path = output_dir / "fomc_events.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(all_events, f, indent=2, ensure_ascii=False)
    print(f"\n已保存 {len(all_events)} 条到 {json_path}")
    
    # 5. 入库
    print("\n=== 入库到 macro_events 表 ===")
    inserted = save_to_db(all_events)
    print(f"  新增 {inserted} 条（跳过已存在的）")
    
    # 6. 打印样本
    print(f"\n=== 样本（前5条 + 后5条） ===")
    for e in all_events[:5]:
        print(f"  {e['event_date']} | FOMC | SEP={e['has_sep']} | {e['day_range']}")
    print("  ...")
    for e in all_events[-5:]:
        print(f"  {e['event_date']} | FOMC | SEP={e['has_sep']} | {e['day_range']}")
    
    print(f"\n总计: {len(all_events)} 条 FOMC 事件 ({all_events[0]['year']}-{all_events[-1]['year']})")


if __name__ == "__main__":
    main()
