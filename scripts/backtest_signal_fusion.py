"""
Signal Fusion Backtest - 信号融合回测
对比: A组(纯LLM信号) vs B组(LLM+均线过滤)
使用所有可用时间框架 (30m, 4h, 1d)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from collections import defaultdict
from datetime import datetime

import psycopg2
import psycopg2.extras

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "quant_trading",
    "user": "postgres",
    "password": "@Cmx1454697261",
}


def get_connection():
    return psycopg2.connect(**DB_CONFIG)


def load_news_signals(conn):
    """Load all news_analysis records that have price data in any timeframe."""
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute("""
        SELECT
            na.id, na.news_id, na.direction, na.confidence, na.importance,
            na.price_change_30m, na.price_change_4h, na.price_change_1d,
            na.correct_30m, na.correct_4h, na.correct_1d,
            na.base_price,
            nr.time as published_at, nr.title,
            na.time as news_time
        FROM news_analysis na
        JOIN news_raw nr ON na.news_id = nr.id
        WHERE (na.price_change_30m IS NOT NULL
            OR na.price_change_4h IS NOT NULL
            OR na.price_change_1d IS NOT NULL)
        ORDER BY nr.time
    """)
    rows = cur.fetchall()
    cur.close()
    return rows


def load_daily_prices(conn):
    """Load kline_daily for MA20 calculation."""
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute("""
        SELECT time, close
        FROM kline_daily
        ORDER BY time
    """)
    rows = cur.fetchall()
    cur.close()
    return {row["time"]: float(row["close"]) for row in rows}


def compute_ma(daily_prices, date, period=20):
    """Compute MA for a given date using the last `period` days of data."""
    from datetime import date as date_type
    if isinstance(date, datetime):
        d = date.date()
    elif isinstance(date, date_type):
        d = date
    else:
        d = date

    # Collect the last `period` trading days up to and including `d`
    all_dates = sorted(daily_prices.keys())
    relevant = [dt for dt in all_dates if dt <= d]
    if len(relevant) < period:
        return None
    window = relevant[-period:]
    return sum(daily_prices[dt] for dt in window) / period


def direction_to_signal(direction):
    """Convert LLM direction to trading signal: 1=long, -1=short, 0=skip."""
    if direction is None:
        return 0
    d = direction.lower().strip()
    if d in ("bullish", "positive", "up"):
        return 1
    elif d in ("bearish", "negative", "down"):
        return -1
    else:
        return 0


def run_backtest(trades, group_name):
    """Run backtest on a list of trades and return stats dict."""
    if not trades:
        return {
            "group": group_name,
            "total_trades": 0,
            "wins": 0,
            "losses": 0,
            "win_rate": 0,
            "avg_pnl": 0,
            "avg_win": 0,
            "avg_loss": 0,
            "profit_factor": 0,
            "max_consecutive_losses": 0,
            "cumulative_return": 0,
            "best_trade": 0,
            "worst_trade": 0,
        }

    wins = [t for t in trades if t["pnl"] > 0]
    losses = [t for t in trades if t["pnl"] <= 0]
    pnls = [t["pnl"] for t in trades]

    # Max consecutive losses
    max_consec_loss = 0
    current_consec = 0
    for t in trades:
        if t["pnl"] <= 0:
            current_consec += 1
            max_consec_loss = max(max_consec_loss, current_consec)
        else:
            current_consec = 0

    total_win = sum(t["pnl"] for t in wins) if wins else 0
    total_loss = abs(sum(t["pnl"] for t in losses)) if losses else 0

    return {
        "group": group_name,
        "total_trades": len(trades),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": len(wins) / len(trades) * 100 if trades else 0,
        "avg_pnl": sum(pnls) / len(pnls) if pnls else 0,
        "avg_win": total_win / len(wins) if wins else 0,
        "avg_loss": -total_loss / len(losses) if losses else 0,
        "profit_factor": total_win / total_loss if total_loss > 0 else float("inf"),
        "max_consecutive_losses": max_consec_loss,
        "cumulative_return": sum(pnls),
        "best_trade": max(pnls) if pnls else 0,
        "worst_trade": min(pnls) if pnls else 0,
    }


def print_report(stats, timeframe, sample_count):
    """Print formatted backtest report."""
    print(f"\n{'='*60}")
    print(f"  {stats['group']} | 时间框架: {timeframe}")
    print(f"{'='*60}")
    print(f"  样本量:           {sample_count} 条新闻信号")
    print(f"  总交易次数:       {stats['total_trades']}")
    print(f"  胜:               {stats['wins']}")
    print(f"  负:               {stats['losses']}")
    print(f"  胜率:             {stats['win_rate']:.1f}%")
    print(f"  平均盈亏:         {stats['avg_pnl']:.4f}%")
    print(f"  平均盈利:         {stats['avg_win']:.4f}%")
    print(f"  平均亏损:         {stats['avg_loss']:.4f}%")
    print(f"  盈亏比:           {stats['profit_factor']:.2f}")
    print(f"  最大连续亏损:     {stats['max_consecutive_losses']}")
    print(f"  累计收益:         {stats['cumulative_return']:.4f}%")
    print(f"  最佳交易:         {stats['best_trade']:.4f}%")
    print(f"  最差交易:         {stats['worst_trade']:.4f}%")
    print(f"{'='*60}")


def main():
    conn = get_connection()
    try:
        signals = load_news_signals(conn)
        daily_prices = load_daily_prices(conn)
        print(f"已加载 {len(signals)} 条有价格数据的新闻信号")
        print(f"已加载 {len(daily_prices)} 个交易日的日线数据")

        # Define timeframes to backtest
        timeframes = {
            "30m": "price_change_30m",
            "4h": "price_change_4h",
            "1d": "price_change_1d",
        }

        all_results = []

        for tf_name, price_col in timeframes.items():
            # Filter signals that have data for this timeframe
            tf_signals = [s for s in signals if s[price_col] is not None]
            if not tf_signals:
                print(f"\n[!] 时间框架 {tf_name}: 无可用数据，跳过")
                continue

            print(f"\n--- 时间框架 {tf_name}: {len(tf_signals)} 条信号 ---")

            # A组: 纯LLM信号
            trades_a = []
            # B组: LLM + MA20过滤
            trades_b = []

            for sig in tf_signals:
                signal = direction_to_signal(sig["direction"])
                if signal == 0:
                    continue  # neutral → skip

                price_change = float(sig[price_col])

                # Determine P&L: long profits from positive change, short from negative
                pnl = price_change * signal  # signal=1 → pnl=price_change; signal=-1 → pnl=-price_change

                trade_info = {
                    "news_id": sig["news_id"],
                    "title": sig["title"][:50] if sig["title"] else "N/A",
                    "direction": sig["direction"],
                    "signal": signal,
                    "price_change": price_change,
                    "pnl": pnl,
                    "date": sig["published_at"],
                }

                # A组: 纯LLM (所有非neutral信号都交易)
                trades_a.append(trade_info)

                # B组: LLM + MA20过滤
                # 需要判断当前价格相对于MA20的位置
                trade_date = sig["published_at"]
                if trade_date is None:
                    continue
                if isinstance(trade_date, datetime):
                    d = trade_date.date()
                else:
                    d = trade_date

                base_price = float(sig["base_price"]) if sig["base_price"] else None
                ma20 = compute_ma(daily_prices, d, period=20)

                if ma20 is not None and base_price is not None:
                    # 过滤规则:
                    # - long 只在价格 > MA20 时进场（趋势确认）
                    # - short 只在价格 < MA20 时进场（趋势确认）
                    if signal == 1 and base_price > ma20:
                        trades_b.append(trade_info)
                    elif signal == -1 and base_price < ma20:
                        trades_b.append(trade_info)
                    # else: MA过滤掉，不交易
                else:
                    # 无MA数据时退回到纯LLM
                    trades_b.append(trade_info)

            stats_a = run_backtest(trades_a, "A组 (纯LLM信号)")
            stats_b = run_backtest(trades_b, "B组 (LLM+MA20过滤)")

            print_report(stats_a, tf_name, len(tf_signals))
            print_report(stats_b, tf_name, len(tf_signals))

            all_results.append((tf_name, stats_a, stats_b, len(tf_signals)))

        # Summary comparison
        print(f"\n\n{'#'*60}")
        print("  综合对比报告")
        print(f"{'#'*60}")
        print(f"\n{'时间框架':<8} | {'组别':<20} | {'交易数':>6} | {'胜率':>8} | {'盈亏比':>8} | {'累计收益':>10}")
        print(f"{'-'*8}-+-{'-'*20}-+-{'-'*6}-+-{'-'*8}-+-{'-'*8}-+-{'-'*10}")
        for tf_name, stats_a, stats_b, sample_count in all_results:
            for stats in [stats_a, stats_b]:
                print(
                    f"{tf_name:<8} | {stats['group']:<20} | {stats['total_trades']:>6} | "
                    f"{stats['win_rate']:>7.1f}% | {stats['profit_factor']:>8.2f} | "
                    f"{stats['cumulative_return']:>9.4f}%"
                )

        # Direction distribution
        print("\n\n--- 信号方向分布 ---")
        dir_counts = defaultdict(int)
        for s in signals:
            d = s["direction"] or "NULL"
            dir_counts[d] += 1
        for d, c in sorted(dir_counts.items(), key=lambda x: -x[1]):
            print(f"  {d:<12}: {c:>4} 条")

        # Caveats
        print(f"\n{'*'*60}")
        print("  [!] 重要说明")
        print(f"{'*'*60}")
        print(f"  1. 样本量有限（总共 {len(signals)} 条有价格数据的新闻）")
        print("  2. 数据集中在特定时间段，可能存在时间偏差")
        print("  3. 未考虑交易成本（手续费、滑点）")
        print("  4. 回测结果不代表未来表现")
        print("  5. MA20过滤依赖日线数据可用性")
        print("  6. 1d 时间框架数据最少（约20条），统计意义有限")
        print(f"{'*'*60}")

    finally:
        conn.close()


if __name__ == "__main__":
    main()
