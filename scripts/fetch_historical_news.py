#!/usr/bin/env python3
"""
Fetch historical financial news (2013-2025) from The Guardian Open Platform API.

Target: news_raw table in quant_trading database.
Topics: gold, precious metals, Federal Reserve, inflation, geopolitics.

Guardian API (test key):
  - 720 requests/min, 50,000/day
  - page-size up to 200
  - Full body text via show-fields=bodyText,headline,trailText
  - Free, no signup required with 'test' key

Usage:
  python scripts/fetch_historical_news.py [--year YEAR] [--dry-run]
"""

import argparse
import hashlib
import json
import logging
import sys
import time
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime, timezone, timedelta

import psycopg2
import psycopg2.extras

# ── Config ──────────────────────────────────────────────────────────────
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'quant_trading',
    'user': 'postgres',
    'password': '@Cmx1454697261',
}

GUARDIAN_API_KEY = 'test'  # Free developer key
GUARDIAN_BASE_URL = 'https://content.guardianapis.com/search'
PAGE_SIZE = 200  # Max allowed

# Queries to run — each covers a different topic area.
# We use section filters to keep results relevant.
QUERIES = [
    # Gold & precious metals in business
    {
        'q': 'gold price OR gold market OR gold rally OR gold slump',
        'section': 'business',
        'label': 'gold_business',
    },
    {
        'q': 'precious metals OR silver price OR platinum price',
        'section': 'business',
        'label': 'precious_metals',
    },
    # Federal Reserve & monetary policy
    {
        'q': 'federal reserve OR interest rate OR quantitative easing OR taper',
        'section': 'business',
        'label': 'fed_policy',
    },
    # Inflation & economic indicators
    {
        'q': 'inflation OR consumer prices OR CPI',
        'section': 'business',
        'label': 'inflation',
    },
    # Geopolitics that affect gold
    {
        'q': 'geopolitics OR sanctions OR trade war OR military conflict',
        'section': 'world',
        'label': 'geopolitics',
    },
    # Dollar and commodities
    {
        'q': 'dollar OR safe haven OR commodity prices',
        'section': 'business',
        'label': 'dollar_commodities',
    },
]

# Rate limiting: 720/min = 12/sec, but let's be polite
REQUEST_DELAY = 0.15  # seconds between requests

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
log = logging.getLogger(__name__)


def content_hash(title, url, pub_date):
    """Generate a deterministic hash for dedup."""
    raw = f"{title}|{url}|{pub_date}"
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()[:32]


def fetch_guardian_page(query, section, from_date, to_date, page=1):
    """Fetch one page from Guardian API."""
    params = {
        'q': query,
        'section': section,
        'from-date': from_date,
        'to-date': to_date,
        'api-key': GUARDIAN_API_KEY,
        'page-size': PAGE_SIZE,
        'page': page,
        'order-by': 'newest',
        'show-fields': 'headline,trailText,bodyText',
    }
    url = GUARDIAN_BASE_URL + '?' + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={
        'User-Agent': 'quant-trading-mvp/1.0 (historical news collector)',
    })

    for attempt in range(3):
        try:
            resp = urllib.request.urlopen(req, timeout=15)
            data = json.loads(resp.read().decode('utf-8'))
            return data['response']
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = 5 * (attempt + 1)
                log.warning(f"Rate limited (429), waiting {wait}s...")
                time.sleep(wait)
            else:
                log.error(f"HTTP {e.code} for page {page}: {e}")
                raise
        except Exception as e:
            log.error(f"Request error (attempt {attempt+1}): {e}")
            if attempt < 2:
                time.sleep(2)
            else:
                raise

    return None


def process_article(result):
    """Convert a Guardian API result to a news_raw row dict."""
    fields = result.get('fields', {})

    title = fields.get('headline', result.get('webTitle', ''))
    trail = fields.get('trailText', '')
    body = fields.get('bodyText', '')

    # Combine trail + body for content
    content = trail
    if body:
        if content:
            content += '\n\n'
        content += body

    pub_date = result.get('webPublicationDate', '')
    web_url = result.get('webUrl', '')

    # Parse the ISO date
    try:
        dt = datetime.fromisoformat(pub_date.replace('Z', '+00:00'))
    except (ValueError, AttributeError):
        dt = None

    if not title or not dt:
        return None

    return {
        'time': dt,
        'source': 'guardian',
        'title': title,
        'content': content[:50000] if content else None,  # Limit size
        'url': web_url,
        'author': None,
        'content_hash': content_hash(title, web_url, pub_date),
    }


def get_existing_hashes(conn):
    """Load all existing content_hash values from news_raw for dedup."""
    cur = conn.cursor()
    cur.execute("SELECT content_hash FROM news_raw WHERE content_hash IS NOT NULL")
    hashes = set(row[0] for row in cur.fetchall())
    cur.close()
    return hashes


def insert_articles(conn, articles):
    """Bulk insert articles into news_raw."""
    if not articles:
        return 0

    cur = conn.cursor()
    sql = """
        INSERT INTO news_raw (time, source, title, content, url, author, content_hash)
        VALUES (%(time)s, %(source)s, %(title)s, %(content)s, %(url)s, %(author)s, %(content_hash)s)
        ON CONFLICT (content_hash) DO NOTHING
    """
    inserted = 0
    for art in articles:
        try:
            cur.execute(sql, art)
            if cur.rowcount > 0:
                inserted += 1
        except Exception as e:
            log.error(f"Insert error for '{art['title'][:50]}': {e}")
            conn.rollback()
            continue

    conn.commit()
    cur.close()
    return inserted


def fetch_query_for_period(query_config, from_date, to_date, existing_hashes, dry_run=False):
    """Fetch all pages for a single query in a date range."""
    q = query_config['q']
    section = query_config['section']
    label = query_config['label']

    articles = []
    page = 1

    # First request to get total count
    resp = fetch_guardian_page(q, section, from_date, to_date, page=1)
    if not resp:
        return articles

    total = resp.get('total', 0)
    total_pages = resp.get('pages', 0)
    log.info(f"  [{label}] {total} articles, {total_pages} pages")

    # Cap at 50 pages (10,000 articles) per query-period to avoid excessive requests
    max_pages = min(total_pages, 50)

    while page <= max_pages:
        if page > 1:
            time.sleep(REQUEST_DELAY)
            resp = fetch_guardian_page(q, section, from_date, to_date, page=page)
            if not resp:
                break

        results = resp.get('results', [])
        if not results:
            break

        for r in results:
            art = process_article(r)
            if art and art['content_hash'] not in existing_hashes:
                articles.append(art)
                existing_hashes.add(art['content_hash'])

        page += 1

    log.info(f"  [{label}] {len(articles)} new articles (after dedup)")
    return articles


def main():
    parser = argparse.ArgumentParser(description='Fetch historical news from The Guardian')
    parser.add_argument('--year', type=int, help='Fetch only a specific year (2013-2025)')
    parser.add_argument('--dry-run', action='store_true', help='Do not write to DB')
    parser.add_argument('--queries', nargs='+', help='Only run specific query labels')
    args = parser.parse_args()

    # Determine year range
    if args.year:
        years = [args.year]
    else:
        years = list(range(2013, 2026))

    log.info(f"Fetching Guardian news for years: {years[0]}-{years[-1]}")

    # Connect to DB
    conn = psycopg2.connect(**DB_CONFIG)
    log.info("Connected to database")

    # Load existing hashes
    existing_hashes = get_existing_hashes(conn)
    log.info(f"Found {len(existing_hashes)} existing content hashes for dedup")

    # Stats
    total_inserted = 0
    stats_by_year = {}
    stats_by_query = {}

    for year in years:
        from_date = f"{year}-01-01"
        to_date = f"{year}-12-31"
        year_inserted = 0

        log.info(f"\n{'='*60}")
        log.info(f"Processing year {year}")
        log.info(f"{'='*60}")

        for qc in QUERIES:
            if args.queries and qc['label'] not in args.queries:
                continue

            articles = fetch_query_for_period(qc, from_date, to_date, existing_hashes, args.dry_run)

            if articles and not args.dry_run:
                inserted = insert_articles(conn, articles)
                year_inserted += inserted
                stats_by_query[qc['label']] = stats_by_query.get(qc['label'], 0) + inserted
                log.info(f"  [{qc['label']}] Inserted {inserted} articles")
            elif articles and args.dry_run:
                log.info(f"  [{qc['label']}] Would insert {len(articles)} articles (dry run)")
                year_inserted += len(articles)
                stats_by_query[qc['label']] = stats_by_query.get(qc['label'], 0) + len(articles)

            # Small delay between queries
            time.sleep(0.5)

        stats_by_year[year] = year_inserted
        total_inserted += year_inserted
        log.info(f"Year {year}: {year_inserted} articles inserted")

    # Print summary
    log.info(f"\n{'='*60}")
    log.info(f"COLLECTION SUMMARY")
    log.info(f"{'='*60}")
    log.info(f"Total new articles: {total_inserted}")
    log.info(f"\nBy year:")
    for year, count in sorted(stats_by_year.items()):
        log.info(f"  {year}: {count}")
    log.info(f"\nBy query:")
    for label, count in sorted(stats_by_query.items()):
        log.info(f"  {label}: {count}")

    # Show final DB state
    if not args.dry_run:
        cur = conn.cursor()
        cur.execute("""
            SELECT source, COUNT(*), MIN(time), MAX(time)
            FROM news_raw
            WHERE source = 'guardian'
            GROUP BY source
        """)
        row = cur.fetchone()
        if row:
            log.info(f"\nGuardian in DB: {row[1]} articles, {row[2]} to {row[3]}")
        cur.close()

    conn.close()
    log.info("Done!")


if __name__ == '__main__':
    main()
