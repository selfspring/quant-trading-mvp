"""
Backtest Engine
基于 VectorBT 的回测引擎，使用 ML 预测信号驱动交易
"""
import logging
import pandas as pd
import numpy as np
import vectorbt as vbt

from quant.common.db import db_engine
from quant.common.config import AppConfig
from quant.signal_generator.feature_engineer import FeatureEngineer
from quant.signal_generator.ml_predictor import MLPredictor

logger = logging.getLogger(__name__)


class BacktestEngine:
    """回测引擎"""

    def __init__(self, config: AppConfig):
        self.config = config
        self.feature_engineer = FeatureEngineer()
        self.ml_predictor = MLPredictor()

    def load_data(self, symbol: str, interval: str,
                  start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """从数据库读取 K 线数据"""
        conditions = ["symbol = %(symbol)s", "interval = %(interval)s"]
        params = {"symbol": symbol, "interval": interval}

        if start_date:
            conditions.append("time >= %(start_date)s")
            params["start_date"] = start_date
        if end_date:
            conditions.append("time <= %(end_date)s")
            params["end_date"] = end_date

        where = " AND ".join(conditions)
        sql = f"""
            SELECT time AS timestamp, open, high, low, close, volume,
                   open_interest
            FROM kline_data
            WHERE {where}
            ORDER BY time
        """

        with db_engine(self.config) as engine:
            df = pd.read_sql(sql, engine, params=params)

        logger.info("Loaded %d rows for %s %s", len(df), symbol, interval)
        return df

    def generate_signals(self, df: pd.DataFrame) -> tuple:
        """
        对每根 K 线生成 ML 预测信号

        Returns:
            (entries, exits) -- bool Series, True 表示开仓/平仓
        """
        # 1. 批量生成特征
        features_df = self.feature_engineer.generate_features(df.copy())

        # 2. 准备模型输入（移除非数值列）
        predict_cols = features_df.columns.tolist()
        for col in ["timestamp", "datetime", "symbol", "id", "duration"]:
            if col in predict_cols:
                predict_cols.remove(col)
        X = features_df[predict_cols]

        # 3. 用 LightGBM 模型批量预测
        predictions = self.ml_predictor.model.predict(X)

        # 4. 计算置信度（复用 MLPredictor 的映射逻辑）
        threshold = 0.005
        abs_pred = np.abs(predictions)

        confidence = np.where(
            abs_pred <= threshold, 0.0,
            np.where(
                abs_pred <= 0.02,
                0.4 + (abs_pred - threshold) / (0.02 - threshold) * 0.5,
                np.where(
                    abs_pred <= 0.05,
                    0.9 - (abs_pred - 0.02) / 0.03 * 0.4,
                    np.maximum(0.3 - (abs_pred - 0.05) * 2, 0.1)
                )
            )
        )

        # 5. 信号过滤：置信度 >= 0.35 才生成交易信号
        conf_threshold = self.config.ml.confidence_threshold
        buy_signal = (predictions > threshold) & (confidence >= conf_threshold)
        sell_signal = (predictions < -threshold) & (confidence >= conf_threshold)

        # 6. 对齐到原始 df 的 index（特征生成可能不改变行数，但以防万一）
        entries = pd.Series(False, index=df.index)
        exits = pd.Series(False, index=df.index)
        entries.iloc[features_df.index] = buy_signal
        exits.iloc[features_df.index] = sell_signal

        n_entries = entries.sum()
        n_exits = exits.sum()
        logger.info("Signals: %d entries, %d exits (conf >= %.2f)",
                     n_entries, n_exits, conf_threshold)
        return entries, exits

    def run(self, symbol: str = "au_main", interval: str = "30m",
            start_date: str = None, end_date: str = None):
        """
        完整回测流程

        Returns:
            vbt.Portfolio 对象
        """
        # 1. 加载数据
        df = self.load_data(symbol, interval, start_date, end_date)
        if df.empty:
            raise ValueError(f"No data for {symbol} {interval}")

        # 2. 生成信号
        entries, exits = self.generate_signals(df)

        # 3. 构建 VectorBT Portfolio
        close = df["close"]
        avg_price = close.mean()
        fees = 10.0 / avg_price  # 单边 10 元手续费，转为比例

        portfolio = vbt.Portfolio.from_signals(
            close,
            entries=entries,
            exits=exits,
            fees=fees,
            freq="30min",
            init_cash=100000,
        )

        logger.info("Backtest complete: %s %s, %d bars", symbol, interval, len(df))
        return portfolio

    def report(self, portfolio) -> None:
        """打印回测��告"""
        stats = portfolio.stats()

        total_return = stats.get("Total Return [%]", 0)
        sharpe = stats.get("Sharpe Ratio", 0)
        max_dd = stats.get("Max Drawdown [%]", 0)
        win_rate = stats.get("Win Rate [%]", 0)

        # 盈亏比：平均盈利 / 平均亏损
        trades = portfolio.trades.records_readable
        if len(trades) > 0:
            profits = trades.loc[trades["PnL"] > 0, "PnL"]
            losses = trades.loc[trades["PnL"] < 0, "PnL"]
            avg_profit = profits.mean() if len(profits) > 0 else 0
            avg_loss = abs(losses.mean()) if len(losses) > 0 else 1
            profit_loss_ratio = avg_profit / avg_loss if avg_loss > 0 else float("inf")
        else:
            profit_loss_ratio = 0

        print("=" * 50)
        print("  BACKTEST REPORT")
        print("=" * 50)
        print(f"  Total Return:       {total_return:.2f}%")
        print(f"  Sharpe Ratio:       {sharpe:.4f}")
        print(f"  Max Drawdown:       {max_dd:.2f}%")
        print(f"  Win Rate:           {win_rate:.2f}%")
        print(f"  Profit/Loss Ratio:  {profit_loss_ratio:.2f}")
        print(f"  Total Trades:       {len(trades)}")
        print("=" * 50)
