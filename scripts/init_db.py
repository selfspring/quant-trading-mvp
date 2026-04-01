"""
数据库初始化脚本
创建所有必需的表（14 张表）
"""
import sys
import os

# Windows 编码修复
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from quant.common.config import config


def create_database():
    """创建数据库（如果不存在）"""
    from quant.common.db import db_connection as _unused_trigger  # noqa: F401
    # 需要连接 postgres 库（目标库可能还不存在），不能用 db_connection
    from quant.common.db import get_db_dsn
    import importlib
    _psycopg2 = importlib.import_module('psycopg2')
    _autocommit = importlib.import_module('psycopg2.extensions').ISOLATION_LEVEL_AUTOCOMMIT
    conn = None
    cursor = None
    try:
        dsn = f"host={config.database.host} port={config.database.port} dbname=postgres user={config.database.user} password={config.database.password.get_secret_value()}"
        conn = getattr(_psycopg2, 'connect')(dsn)
        conn.set_isolation_level(_autocommit)
        cursor = conn.cursor()
        
        # 检查数据库是否存在
        cursor.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s",
            (config.database.database,)
        )
        exists = cursor.fetchone()
        
        if not exists:
            cursor.execute(
                f"CREATE DATABASE {config.database.database}"
            )
            print(f"✅ 数据库 {config.database.database} 创建成功")
        else:
            print(f"ℹ️  数据库 {config.database.database} 已存在")
    
    except Exception as e:
        print(f"❌ 创建数据库失败：{e}")
        raise
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def enable_timescaledb():
    """启用 TimescaleDB 扩展"""
    from quant.common.db import db_connection
    try:
        with db_connection(config) as conn:
            cursor = conn.cursor()
            cursor.execute("CREATE EXTENSION IF NOT EXISTS timescaledb")
            conn.commit()
            cursor.close()
        print("✅ TimescaleDB 扩展已启用")
    
    except Exception as e:
        print(f"⚠️ TimescaleDB 扩展启用失败（可能已安装）: {e}")


def create_tables():
    """创建所有表（带事务回滚机制）"""
    from quant.common.db import db_connection
    try:
        with db_connection(config) as conn:
            cursor = conn.cursor()
        
        # 表 1：K 线数据
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS kline_data (
                time TIMESTAMPTZ NOT NULL,
                symbol VARCHAR(20) NOT NULL,
                interval VARCHAR(10) NOT NULL,
                open DECIMAL(18, 4) NOT NULL,
                high DECIMAL(18, 4) NOT NULL,
                low DECIMAL(18, 4) NOT NULL,
                close DECIMAL(18, 4) NOT NULL,
                volume BIGINT NOT NULL,
                open_interest BIGINT,
                PRIMARY KEY (time, symbol, interval)
            )
        """)
        
        # 转换为 hypertable
        cursor.execute("""
            SELECT create_hypertable('kline_data', 'time', if_not_exists => TRUE)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_kline_symbol_time 
            ON kline_data (symbol, time DESC)
        """)
        print("✅ 表 kline_data 创建成功")
        
        # 表 2：基本面数据
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fundamental_data (
                time TIMESTAMPTZ NOT NULL,
                indicator VARCHAR(50) NOT NULL,
                value DECIMAL(18, 6) NOT NULL,
                source VARCHAR(100),
                PRIMARY KEY (time, indicator)
            )
        """)
        
        cursor.execute("""
            SELECT create_hypertable('fundamental_data', 'time', if_not_exists => TRUE)
        """)
        print("✅ 表 fundamental_data 创建成功")
        
        # 表 3：新闻原文（含去重）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS news_raw (
                id SERIAL PRIMARY KEY,
                time TIMESTAMPTZ NOT NULL,
                source VARCHAR(100) NOT NULL,
                title TEXT NOT NULL,
                content TEXT,
                url TEXT,
                author VARCHAR(100),
                content_hash VARCHAR(64) NOT NULL,
                embedding_id VARCHAR(100),
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        
        cursor.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_news_hash 
            ON news_raw (content_hash)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_news_time 
            ON news_raw (time DESC)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_news_source 
            ON news_raw (source, time DESC)
        """)
        print("✅ 表 news_raw 创建成功（含去重索引）")
        
        # 表 4：AI 新闻解读结果
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS news_analysis (
                id SERIAL PRIMARY KEY,
                news_id INTEGER REFERENCES news_raw(id),
                time TIMESTAMPTZ NOT NULL,
                published_time TIMESTAMPTZ,
                analyzed_at TIMESTAMPTZ,
                effective_time TIMESTAMPTZ,
                importance VARCHAR(20) NOT NULL,
                direction VARCHAR(20) NOT NULL,
                timeframe VARCHAR(20) NOT NULL,
                confidence DECIMAL(3, 2) NOT NULL,
                reasoning TEXT,
                model_version VARCHAR(50),
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_analysis_time 
            ON news_analysis (time DESC)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_analysis_importance 
            ON news_analysis (importance, time DESC)
        """)
        print("✅ 表 news_analysis 创建成功")

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS news_verification (
                id SERIAL PRIMARY KEY,
                analysis_id INTEGER NOT NULL REFERENCES news_analysis(id) ON DELETE CASCADE,
                verification_scope VARCHAR(32) NOT NULL,
                verification_anchor_time TIMESTAMPTZ NOT NULL,
                symbol VARCHAR(32),
                base_price DECIMAL(18, 6),
                price_change_30m DECIMAL(18, 6),
                price_change_4h DECIMAL(18, 6),
                price_change_1d DECIMAL(18, 6),
                correct_30m INTEGER,
                correct_4h INTEGER,
                correct_1d INTEGER,
                direction_correct INTEGER,
                verification_version VARCHAR(64) NOT NULL,
                verified_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                CONSTRAINT uq_news_verification_analysis_scope UNIQUE (analysis_id, verification_scope),
                CONSTRAINT ck_news_verification_scope CHECK (
                    verification_scope IN ('effective_time', 'published_time')
                ),
                CONSTRAINT ck_news_verification_correct_30m CHECK (correct_30m IN (0, 1) OR correct_30m IS NULL),
                CONSTRAINT ck_news_verification_correct_4h CHECK (correct_4h IN (0, 1) OR correct_4h IS NULL),
                CONSTRAINT ck_news_verification_correct_1d CHECK (correct_1d IN (0, 1) OR correct_1d IS NULL),
                CONSTRAINT ck_news_verification_direction_correct CHECK (direction_correct IN (0, 1) OR direction_correct IS NULL)
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_news_verification_anchor_time
            ON news_verification (verification_anchor_time DESC)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_news_verification_verified_at
            ON news_verification (verified_at DESC)
        """)
        print("✅ 表 news_verification 创建成功")

        cursor.execute(CREATE_TABLE_SQL)
        cursor.execute(CREATE_INDEX_SQL)
        print(f"✅ 表 kline_30m_availability 创建成功（rule_version={RULE_VERSION}）")
        
        # 表 5：技术指标（含扩展字段）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS technical_indicators (
                time TIMESTAMPTZ NOT NULL,
                symbol VARCHAR(20) NOT NULL,
                ma_5 DECIMAL(18, 4),
                ma_10 DECIMAL(18, 4),
                ma_20 DECIMAL(18, 4),
                macd DECIMAL(18, 6),
                macd_signal DECIMAL(18, 6),
                macd_hist DECIMAL(18, 6),
                rsi_14 DECIMAL(5, 2),
                bb_upper DECIMAL(18, 4),
                bb_middle DECIMAL(18, 4),
                bb_lower DECIMAL(18, 4),
                atr_14 DECIMAL(18, 4),
                extra_indicators JSONB,
                PRIMARY KEY (time, symbol)
            )
        """)
        
        cursor.execute("""
            SELECT create_hypertable('technical_indicators', 'time', if_not_exists => TRUE)
        """)
        print("✅ 表 technical_indicators 创建成功（含扩展字段）")
        
        # 表 6：ML 模型预测
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ml_predictions (
                time TIMESTAMPTZ NOT NULL,
                symbol VARCHAR(20) NOT NULL,
                predicted_return DECIMAL(8, 6) NOT NULL,
                confidence DECIMAL(3, 2) NOT NULL,
                model_version VARCHAR(50) NOT NULL,
                features JSONB,
                PRIMARY KEY (time, symbol)
            )
        """)
        
        cursor.execute("""
            SELECT create_hypertable('ml_predictions', 'time', if_not_exists => TRUE)
        """)
        print("✅ 表 ml_predictions 创建成功")
        
        # 表 7：交易信号
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trading_signals (
                id SERIAL PRIMARY KEY,
                time TIMESTAMPTZ NOT NULL,
                symbol VARCHAR(20) NOT NULL,
                signal_type VARCHAR(20) NOT NULL,
                signal_strength DECIMAL(3, 2) NOT NULL,
                technical_score DECIMAL(3, 2),
                ml_score DECIMAL(3, 2),
                news_score DECIMAL(3, 2),
                reasoning JSONB,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_signals_time 
            ON trading_signals (time DESC)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_signals_symbol 
            ON trading_signals (symbol, time DESC)
        """)
        print("✅ 表 trading_signals 创建成功")
        
        # 表 8：订单记录
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id SERIAL PRIMARY KEY,
                order_id VARCHAR(50) UNIQUE NOT NULL,
                symbol VARCHAR(20) NOT NULL,
                direction VARCHAR(10) NOT NULL,
                offset_flag VARCHAR(10) NOT NULL,
                price DECIMAL(18, 4) NOT NULL,
                volume INTEGER NOT NULL,
                status VARCHAR(20) NOT NULL,
                signal_id INTEGER REFERENCES trading_signals(id),
                submitted_at TIMESTAMPTZ,
                filled_at TIMESTAMPTZ,
                cancelled_at TIMESTAMPTZ,
                error_msg TEXT,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_orders_status 
            ON orders (status, created_at DESC)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_orders_symbol 
            ON orders (symbol, created_at DESC)
        """)
        print("✅ 表 orders 创建成功")
        
        # 表 9：成交记录
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                id SERIAL PRIMARY KEY,
                trade_id VARCHAR(50) UNIQUE NOT NULL,
                order_id VARCHAR(50) REFERENCES orders(order_id),
                symbol VARCHAR(20) NOT NULL,
                direction VARCHAR(10) NOT NULL,
                price DECIMAL(18, 4) NOT NULL,
                volume INTEGER NOT NULL,
                commission DECIMAL(18, 4),
                traded_at TIMESTAMPTZ NOT NULL,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_trades_time 
            ON trades (traded_at DESC)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_trades_symbol 
            ON trades (symbol, traded_at DESC)
        """)
        print("✅ 表 trades 创建成功")
        
        # 表 10：持仓记录
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS positions (
                id SERIAL PRIMARY KEY,
                symbol VARCHAR(20) NOT NULL,
                direction VARCHAR(10) NOT NULL,
                volume INTEGER NOT NULL,
                avg_price DECIMAL(18, 4) NOT NULL,
                current_price DECIMAL(18, 4),
                unrealized_pnl DECIMAL(18, 4),
                realized_pnl DECIMAL(18, 4) DEFAULT 0,
                opened_at TIMESTAMPTZ NOT NULL,
                closed_at TIMESTAMPTZ,
                status VARCHAR(20) NOT NULL,
                updated_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_positions_status 
            ON positions (status, symbol)
        """)
        print("✅ 表 positions 创建成功")
        
        # 表 11：账户快照
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS account_snapshot (
                time TIMESTAMPTZ NOT NULL PRIMARY KEY,
                balance DECIMAL(18, 4) NOT NULL,
                available DECIMAL(18, 4) NOT NULL,
                margin DECIMAL(18, 4) NOT NULL,
                total_pnl DECIMAL(18, 4) NOT NULL,
                daily_pnl DECIMAL(18, 4),
                weekly_pnl DECIMAL(18, 4),
                max_drawdown DECIMAL(5, 2),
                position_count INTEGER
            )
        """)
        
        cursor.execute("""
            SELECT create_hypertable('account_snapshot', 'time', if_not_exists => TRUE)
        """)
        print("✅ 表 account_snapshot 创建成功")
        
        # 表 12：数据质量监控
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS data_quality_log (
                time TIMESTAMPTZ NOT NULL,
                data_type VARCHAR(50) NOT NULL,
                source VARCHAR(100) NOT NULL,
                status VARCHAR(20) NOT NULL,
                records_count INTEGER,
                error_msg TEXT,
                latency_ms INTEGER,
                PRIMARY KEY (time, data_type, source)
            )
        """)
        
        cursor.execute("""
            SELECT create_hypertable('data_quality_log', 'time', if_not_exists => TRUE)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_quality_status 
            ON data_quality_log (status, time DESC)
        """)
        print("✅ 表 data_quality_log 创建成功")
        
        # 表 13：信号回溯分析
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS signal_performance (
                signal_id INTEGER REFERENCES trading_signals(id),
                time TIMESTAMPTZ NOT NULL,
                actual_return_1h DECIMAL(8, 6),
                actual_return_2h DECIMAL(8, 6),
                actual_return_4h DECIMAL(8, 6),
                max_favorable_excursion DECIMAL(8, 6),
                max_adverse_excursion DECIMAL(8, 6),
                PRIMARY KEY (signal_id)
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_signal_perf_time 
            ON signal_performance (time DESC)
        """)
        print("✅ 表 signal_performance 创建成功")
        
        # 表 14：消息流追踪
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS message_trace (
                trace_id VARCHAR(64) NOT NULL,
                timestamp TIMESTAMPTZ NOT NULL,
                process_name VARCHAR(50) NOT NULL,
                event_type VARCHAR(50) NOT NULL,
                event_data JSONB,
                parent_trace_id VARCHAR(64),
                latency_ms INTEGER,
                status VARCHAR(20) NOT NULL,
                error_msg TEXT,
                PRIMARY KEY (trace_id, timestamp)
            )
        """)
        
        cursor.execute("""
            SELECT create_hypertable('message_trace', 'timestamp', if_not_exists => TRUE)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_trace_id 
            ON message_trace (trace_id, timestamp DESC)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_parent_trace 
            ON message_trace (parent_trace_id, timestamp DESC)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_process_event 
            ON message_trace (process_name, event_type, timestamp DESC)
        """)
        print("✅ 表 message_trace 创建成功")
        
        conn.commit()
        print("\n🎉 所有表创建完成！共 14 张表")
    
    except Exception as e:
        print(f"\n❌ 创建表失败，已回滚：{e}")
        raise


if __name__ == '__main__':
    print("开始初始化数据库...\n")
    
    try:
        create_database()
        enable_timescaledb()
        create_tables()
        
        print("\n✅ 数据库初始化完成！")
        print(f"数据库：{config.database.database}")
        print(f"主机：{config.database.host}:{config.database.port}")
        
    except Exception as e:
        print(f"\n❌ 初始化失败：{e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
