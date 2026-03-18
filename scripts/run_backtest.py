"""回测执行脚本"""
import argparse
from quant.common.config import config
from quant.backtest.engine import BacktestEngine


def main():
    parser = argparse.ArgumentParser(description="Run backtest")
    parser.add_argument("--symbol", default="au_main")
    parser.add_argument("--interval", default="30m")
    parser.add_argument("--start", default=None)
    parser.add_argument("--end", default=None)
    args = parser.parse_args()

    engine = BacktestEngine(config)
    portfolio = engine.run(args.symbol, args.interval, args.start, args.end)
    engine.report(portfolio)


if __name__ == "__main__":
    main()
