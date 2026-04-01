# Historical News Data Sources — Research Report

> Last updated: 2026-03-22

## Purpose

Evaluate free/low-cost sources of historical financial news (2013–2025) for the gold quantitative trading system. Target topics: gold/precious metals, Federal Reserve, inflation, geopolitics.

---

## 1. The Guardian Open Platform ✅ **SELECTED — PRIMARY SOURCE**

| Attribute | Detail |
|---|---|
| URL | https://open-platform.theguardian.com/ |
| Cost | **Free** (test key: `test`, or register for higher limits) |
| Coverage | 1999–present |
| Rate Limits | 720 req/min, 50,000 req/day (test key) |
| Historical Depth | Full access to all historical articles |
| Filtering | Section (business, world), keyword search, date range |
| Body Text | Yes, via `show-fields=bodyText,headline,trailText` |
| Language | English |
| Max Page Size | 200 results per page |

**Estimated yield for 2013–2025:**
- Gold-related business: ~2,000 articles
- Federal Reserve / monetary policy: ~5,700 articles
- Inflation: ~11,400 articles
- Precious metals: ~1,500 articles
- Geopolitics (world): ~300 articles
- Dollar / commodities: many thousands
- **Total with dedup: ~15,000–25,000 unique articles**

**Pros:**
- Completely free, generous limits
- Full article text available
- Excellent financial/business coverage
- Good API documentation
- Reliable, well-maintained

**Cons:**
- UK/EU perspective (not US-centric)
- No direct "gold price" tag — relies on keyword search
- Some irrelevant results mixed in

---

## 2. GDELT Project ⚠️ **SECONDARY — LIMITED VALUE**

| Attribute | Detail |
|---|---|
| URL | https://api.gdeltproject.org/ |
| Cost | **Free** |
| Coverage | 2015–present (v2 API), 1979–present (raw data files) |
| Rate Limits | 1 request per 5 seconds (strict 429) |
| Filtering | Keyword, date, country, language |
| Body Text | **No** — URLs and metadata only |
| Language | Multi-language (global) |

**Pros:**
- Massive global coverage
- Free, no API key needed
- Includes tone/sentiment metadata

**Cons:**
- Very aggressive rate limiting
- No article body text — only titles and URLs
- Returns many non-English results
- Results are often low-quality (Indonesian, Indian local news)
- API documentation is poor
- Historical coverage via API limited (v2 starts ~2015)

**Verdict:** Not practical for our use case. Would need a separate scraping step to get actual article content from each URL.

---

## 3. New York Times APIs ❌ **REQUIRES API KEY**

| Attribute | Detail |
|---|---|
| URL | https://developer.nytimes.com/ |
| Cost | **Free** (requires registration for API key) |
| Coverage | 1851–present (Archive API) |
| Rate Limits | 5 req/min (Archive), 10 req/min (Article Search) |
| Body Text | Abstracts only; full text requires paid subscription |

**Pros:**
- Incredibly deep historical archive
- High-quality financial journalism
- Article Search API supports keyword + date filtering

**Cons:**
- Must register for free API key (no test key)
- Very low rate limits (5/min for archive)
- No full body text — only headlines, abstracts, URLs
- Requires scraping NYT website for full content (TOS issue)

**Verdict:** Good for headline-level data if you register for a key. Could complement Guardian data but adds complexity.

---

## 4. NewsAPI ❌ **HISTORICAL DATA REQUIRES PAID PLAN**

| Attribute | Detail |
|---|---|
| URL | https://newsapi.org/ |
| Cost | Free tier: last 30 days only. Paid: $449/mo+ for historical |
| Coverage | 2019–present |
| Rate Limits | 100 req/day (free), 250-500 req/day (paid) |
| Body Text | Partial (first ~200 chars) |

**Pros:**
- Easy API, good documentation
- Many sources (80,000+)

**Cons:**
- Free tier only covers last 30 days
- Historical data requires expensive paid plan ($449+/month)
- Only goes back to ~2019
- Truncated body text

**Verdict:** Not viable for historical data collection.

---

## 5. Event Registry ⚠️ **FREEMIUM**

| Attribute | Detail |
|---|---|
| URL | https://eventregistry.org/ |
| Cost | Free: 5,000 articles/month. Paid: from €500/mo |
| Coverage | 2014–present |
| Filtering | Advanced concept/topic filtering |
| Body Text | Yes |

**Pros:**
- Good concept-based filtering (can search "gold" as a concept)
- Full article body text
- Event clustering (groups related articles)

**Cons:**
- Free tier very limited (5,000/month)
- Would take 3-5 months to collect full dataset at free tier
- Paid tier expensive

**Verdict:** Possible but slow at free tier. Could supplement Guardian data over time.

---

## 6. Internet Archive / Wayback Machine ❌ **NOT PRACTICAL**

| Attribute | Detail |
|---|---|
| URL | https://archive.org/ |
| Cost | Free |
| Coverage | 1996–present |

**Pros:**
- Massive historical web archive
- Free

**Cons:**
- No structured search by topic/keyword
- Must know exact URLs to retrieve
- No API for "find me gold news articles"
- Would require building URL lists first, then scraping archived pages
- Extremely slow for bulk collection

**Verdict:** Only useful if you already have specific article URLs.

---

## 7. Common Crawl ❌ **TOO RAW**

| Attribute | Detail |
|---|---|
| URL | https://commoncrawl.org/ |
| Cost | Free |
| Coverage | 2008–present |

**Pros:**
- Petabytes of web crawl data
- Free, downloadable

**Cons:**
- Raw web crawl — no news filtering
- Requires massive data processing (AWS/BigQuery)
- Finding gold-related financial news = needle in haystack
- No pre-built search API

**Verdict:** Only for large-scale research projects with significant compute.

---

## 8. Reuters / Bloomberg ❌ **EXPENSIVE**

| Attribute | Detail |
|---|---|
| Cost | Bloomberg Terminal: ~$2,000/mo. Reuters Eikon: ~$1,200/mo |
| Coverage | Decades of history |
| Body Text | Full text |

**Pros:**
- Highest quality financial news
- Comprehensive gold/commodities coverage
- Full article text + metadata

**Cons:**
- Very expensive
- Designed for financial institutions
- Complex licensing

**Verdict:** Best quality but prohibitively expensive for this project.

---

## 9. 金十数据 (Jin10) ⚠️ **NO HISTORICAL API**

| Attribute | Detail |
|---|---|
| URL | https://www.jin10.com/ |
| Cost | Free (web), paid for some data |
| Coverage | Recent years |

**Pros:**
- Chinese financial news, good gold coverage
- Already integrated in real-time pipeline

**Cons:**
- No public historical data API
- Website requires JS rendering (Selenium/Playwright)
- Anti-scraping measures
- Terms of service may prohibit bulk scraping

**Verdict:** Already collecting real-time; historical would require complex web scraping.

---

## Recommendation

### Immediate (Implemented)
1. **The Guardian Open Platform** — Primary source, collecting ~15,000–25,000 articles (2013–2025)
   - Script: `scripts/fetch_historical_news.py`
   - Free, reliable, good quality

### Future Enhancements (If More Data Needed)
2. **NYT Article Search API** — Register for free key, collect headlines/abstracts
   - Would add ~5,000–10,000 headline-level entries
   - Rate limit: slow but free

3. **Event Registry** — Use free tier (5,000/month) for targeted gold news
   - 3–5 months to build meaningful dataset
   - Higher relevance through concept-based filtering

4. **GDELT + Article Scraping** — Use GDELT for URL discovery, then scrape article text
   - Complex but powerful pipeline
   - Legal/TOS concerns with scraping

### If Budget Available
5. **Alpha Vantage News API** ($49.99/mo) — Financial news with sentiment
6. **Polygon.io** ($29/mo) — Market-focused news
7. **Event Registry paid** (€500/mo) — Best structured news data

---

## Data Quality Notes

- Guardian articles are general news with financial focus — not pure financial wire service
- Keywords overlap: "gold" matches Olympics stories, "inflation" matches non-financial usage
- Post-collection filtering/scoring may be needed to rank relevance to gold trading
- Consider using NLP/LLM to score relevance after collection
