"""
Minimal schema alignment: add time semantic columns to news_analysis
and create news_verification table if needed.

This script is idempotent (IF NOT EXISTS / ADD COLUMN IF NOT EXISTS).
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg2
from quant.common.config import config

DB_CONFIG = dict(
    host=config.database.host,
    port=config.database.port,
    dbname=config.database.database,
    user=config.database.user,
    password=config.database.password.get_secret_value(),
)

def main():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    # 1. Add three time semantic columns to news_analysis
    print("Step 1: Adding time semantic columns to news_analysis...")
    cur.execute("""
        ALTER TABLE news_analysis
        ADD COLUMN IF NOT EXISTS published_time TIMESTAMPTZ,
        ADD COLUMN IF NOT EXISTS analyzed_at TIMESTAMPTZ,
        ADD COLUMN IF NOT EXISTS effective_time TIMESTAMPTZ;
    """)
    print("  -> published_time, analyzed_at, effective_time added (or already exist)")

    # 2. Create news_verification table
    print("Step 2: Creating news_verification table...")
    cur.execute("""
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
        );
    """)
    print("  -> news_verification table created (or already exists)")

    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_news_verification_anchor_time
        ON news_verification (verification_anchor_time DESC);
    """)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_news_verification_verified_at
        ON news_verification (verified_at DESC);
    """)
    print("  -> indexes created")

    conn.commit()
    print("\nSchema alignment complete. Verifying...")

    # Verify
    cur.execute("""
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_name='news_analysis'
          AND column_name IN ('published_time', 'analyzed_at', 'effective_time')
        ORDER BY column_name
    """)
    cols = cur.fetchall()
    print(f"\nnews_analysis time columns: {cols}")

    cur.execute("""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_name='news_verification'
        )
    """)
    exists = cur.fetchone()[0]
    print(f"news_verification exists: {exists}")

    cur.close()
    conn.close()
    print("\nDone.")

if __name__ == '__main__':
    main()
