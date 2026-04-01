-- 1. tick_data（Tick 数据表）
CREATE TABLE IF NOT EXISTS tick_data (
    time TIMESTAMPTZ NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    exchange VARCHAR(10),
    last_price DOUBLE PRECISION,
    volume BIGINT,
    open_interest BIGINT,
    bid_price_1 DOUBLE PRECISION,
    bid_volume_1 INT,
    ask_price_1 DOUBLE PRECISION,
    ask_volume_1 INT,
    open_price DOUBLE PRECISION,
    high_price DOUBLE PRECISION,
    low_price DOUBLE PRECISION,
    pre_close DOUBLE PRECISION
);

-- 创建 TimescaleDB 超表
SELECT create_hypertable('tick_data', 'time', if_not_exists => TRUE);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_tick_symbol_time ON tick_data (symbol, time DESC);

-- 2. kline_daily（日线数据表）
CREATE TABLE IF NOT EXISTS kline_daily (
    time DATE NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    open DOUBLE PRECISION,
    high DOUBLE PRECISION,
    low DOUBLE PRECISION,
    close DOUBLE PRECISION,
    volume BIGINT,
    open_interest BIGINT,
    PRIMARY KEY (time, symbol)
);

CREATE INDEX IF NOT EXISTS idx_kline_daily_symbol ON kline_daily (symbol, time DESC);

-- 3. kline_1h（小时线数据表）
CREATE TABLE IF NOT EXISTS kline_1h (
    time TIMESTAMPTZ NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    open DOUBLE PRECISION,
    high DOUBLE PRECISION,
    low DOUBLE PRECISION,
    close DOUBLE PRECISION,
    volume BIGINT,
    open_interest BIGINT,
    PRIMARY KEY (time, symbol)
);

CREATE INDEX IF NOT EXISTS idx_kline_1h_symbol ON kline_1h (symbol, time DESC);

-- 4. macro_data（宏观数据表）
CREATE TABLE IF NOT EXISTS macro_data (
    time DATE NOT NULL,
    indicator VARCHAR(50) NOT NULL,
    value DOUBLE PRECISION,
    unit VARCHAR(20),
    source VARCHAR(50),
    PRIMARY KEY (time, indicator)
);

CREATE INDEX IF NOT EXISTS idx_macro_indicator ON macro_data (indicator, time DESC);

-- 5. news_data（新闻数据表）
CREATE TABLE IF NOT EXISTS news_data (
    id SERIAL PRIMARY KEY,
    time TIMESTAMPTZ NOT NULL,
    title TEXT NOT NULL,
    content TEXT,
    source VARCHAR(100),
    url TEXT,
    keywords TEXT[],
    sentiment DOUBLE PRECISION,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_news_time ON news_data (time DESC);
CREATE INDEX IF NOT EXISTS idx_news_keywords ON news_data USING GIN (keywords);
