"""
基本面数据采集模块
采集美元指数、美债收益率、美联储利率、非农、CPI 等宏观经济数据

采用分步实现：
- Step 1: 骨架 + 美元指数（fetch_dollar_index）
- Step 2: 美债收益率 + 美联储利率
- Step 3: 非农 + CPI + 存库 + fetch_all
"""

import logging
import os
from datetime import datetime, timedelta
from typing import Optional

import pandas as pd
from sqlalchemy import create_engine, text, inspect

logger = logging.getLogger(__name__)


class FundamentalCollector:
    """基本面数据采集器"""

    def __init__(self):
        logger.info("FundamentalCollector 初始化")

    # ------------------------------------------------------------------
    # Step 1: 美元指数
    # ------------------------------------------------------------------

    def fetch_dollar_index(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        采集美元指数（DXY）历史数据

        Parameters
        ----------
        start_date : str, optional
            开始日期，格式 'YYYY-MM-DD'，默认 1 年前
        end_date : str, optional
            结束日期，格式 'YYYY-MM-DD'，默认今天

        Returns
        -------
        pd.DataFrame
            columns = ['date', 'dollar_index']
        """
        if end_date is None:
            end_date = datetime.now().strftime("%Y-%m-%d")
        if start_date is None:
            start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")

        logger.info(
            "开始采集美元指数, start_date=%s, end_date=%s",
            start_date,
            end_date,
        )

        # 优先使用 yfinance（DX-Y.NYB = ICE 美元指数期货）
        df = self._fetch_dollar_index_yfinance(start_date, end_date)

        if df is not None and not df.empty:
            logger.info("美元指数采集成功, 共 %d 条记录", len(df))
            return df

        # 备选：通过 AKShare 外汇接口间接获取（目前 AKShare 无直接美元指数接口）
        logger.warning("yfinance 采集失败, 尝试 AKShare 备选方案")
        df = self._fetch_dollar_index_akshare(start_date, end_date)

        if df is not None and not df.empty:
            logger.info("美元指数(AKShare)采集成功, 共 %d 条记录", len(df))
            return df

        logger.error("所有数据源均采集失败, 返回空 DataFrame")
        return pd.DataFrame(columns=["date", "dollar_index"])

    def _fetch_dollar_index_yfinance(
        self, start_date: str, end_date: str
    ) -> Optional[pd.DataFrame]:
        """通过 yfinance 采集 ICE 美元指数（DX-Y.NYB）"""
        try:
            import yfinance as yf

            ticker = yf.Ticker("DX-Y.NYB")
            hist = ticker.history(start=start_date, end=end_date)

            if hist.empty:
                logger.warning("yfinance 返回空数据")
                return None

            df = pd.DataFrame(
                {
                    "date": hist.index.date,
                    "dollar_index": hist["Close"].values,
                }
            )
            df["date"] = pd.to_datetime(df["date"])
            return df

        except ImportError:
            logger.error("yfinance 未安装, 请执行: pip install yfinance")
            return None
        except Exception as e:
            logger.error("yfinance 采集美元指数异常: %s", e, exc_info=True)
            return None

    def _fetch_dollar_index_akshare(
        self, start_date: str, end_date: str
    ) -> Optional[pd.DataFrame]:
        """
        通过 AKShare 外汇历史接口间接获取美元指数

        AKShare 目前没有直接的美元指数接口，此处尝试使用
        forex_hist_em(symbol='美元指数') 东方财富外汇历史数据。
        如果该 symbol 不可用则返回 None。
        """
        try:
            import akshare as ak

            # 东方财富外汇-美元指数代码
            hist = ak.forex_hist_em(symbol="美元指数")

            if hist is None or hist.empty:
                logger.warning("AKShare forex_hist_em 返回空数据")
                return None

            # 标准化列名（东方财富返回的列名可能是中文）
            col_map = {}
            for col in hist.columns:
                col_lower = str(col).lower()
                if "日期" in col_lower or "date" in col_lower or "时间" in col_lower:
                    col_map[col] = "date"
                elif "收盘" in col_lower or "close" in col_lower:
                    col_map[col] = "dollar_index"

            if "date" not in col_map.values() or "dollar_index" not in col_map.values():
                # 退而使用前两列
                cols = hist.columns.tolist()
                col_map = {cols[0]: "date", cols[1]: "dollar_index"}
                logger.warning(
                    "列名无法识别, 使用前两列: %s -> date, %s -> dollar_index",
                    cols[0],
                    cols[1],
                )

            hist = hist.rename(columns=col_map)
            df = hist[["date", "dollar_index"]].copy()
            df["date"] = pd.to_datetime(df["date"])

            # 按日期范围过滤
            mask = (df["date"] >= pd.to_datetime(start_date)) & (
                df["date"] <= pd.to_datetime(end_date)
            )
            df = df.loc[mask].reset_index(drop=True)

            return df if not df.empty else None

        except ImportError:
            logger.error("akshare 未安装, 请执行: pip install akshare")
            return None
        except Exception as e:
            logger.error("AKShare 采集美元指数异常: %s", e, exc_info=True)
            return None

    # ------------------------------------------------------------------
    # Step 2: 美债收益率 / 美联储利率
    # ------------------------------------------------------------------

    def fetch_treasury_yield(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        采集 10 年期美债收益率日数据

        Parameters
        ----------
        start_date : str, optional
            开始日期，格式 'YYYY-MM-DD'，默认 1 年前
        end_date : str, optional
            结束日期，格式 'YYYY-MM-DD'，默认今天

        Returns
        -------
        pd.DataFrame
            columns = ['date', 'treasury_yield_10y']
        """
        if end_date is None:
            end_date = datetime.now().strftime("%Y-%m-%d")
        if start_date is None:
            start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")

        logger.info(
            "开始采集10年期美债收益率, start_date=%s, end_date=%s",
            start_date,
            end_date,
        )

        # 优先使用 yfinance（^TNX = CBOE 10-Year Treasury Note Yield）
        df = self._fetch_treasury_yield_yfinance(start_date, end_date)

        if df is not None and not df.empty:
            logger.info("10年期美债收益率采集成功, 共 %d 条记录", len(df))
            return df

        # 备选：通过 AKShare 获取
        logger.warning("yfinance 采集失败, 尝试 AKShare 备选方案")
        df = self._fetch_treasury_yield_akshare(start_date, end_date)

        if df is not None and not df.empty:
            logger.info("10年期美债收益率(AKShare)采集成功, 共 %d 条记录", len(df))
            return df

        logger.error("所有数据源均采集失败, 返回空 DataFrame")
        return pd.DataFrame(columns=["date", "treasury_yield_10y"])

    def _fetch_treasury_yield_yfinance(
        self, start_date: str, end_date: str
    ) -> Optional[pd.DataFrame]:
        """通过 yfinance 采集 10 年期美债收益率（^TNX）"""
        try:
            import yfinance as yf

            ticker = yf.Ticker("^TNX")
            hist = ticker.history(start=start_date, end=end_date)

            if hist.empty:
                logger.warning("yfinance ^TNX 返回空数据")
                return None

            df = pd.DataFrame(
                {
                    "date": hist.index.date,
                    "treasury_yield_10y": hist["Close"].values,
                }
            )
            df["date"] = pd.to_datetime(df["date"])
            return df

        except ImportError:
            logger.error("yfinance 未安装, 请执行: pip install yfinance")
            return None
        except Exception as e:
            logger.error("yfinance 采集美债收益率异常: %s", e, exc_info=True)
            return None

    def _fetch_treasury_yield_akshare(
        self, start_date: str, end_date: str
    ) -> Optional[pd.DataFrame]:
        """
        通过 AKShare 采集美债收益率

        尝试使用 bond_zh_us_rate(period='10年') 获取中美国债收益率数据，
        从中提取美国 10 年期国债收益率。
        """
        try:
            import akshare as ak

            # AKShare 中美国债收益率接口
            hist = ak.bond_zh_us_rate(period="10年")

            if hist is None or hist.empty:
                logger.warning("AKShare bond_zh_us_rate 返回空数据")
                return None

            # 标准化列名
            col_map = {}
            for col in hist.columns:
                col_lower = str(col).lower()
                if "日期" in col_lower or "date" in col_lower:
                    col_map[col] = "date"
                elif "美国国债收益率" in str(col) or "美债" in str(col):
                    col_map[col] = "treasury_yield_10y"

            if "date" not in col_map.values() or "treasury_yield_10y" not in col_map.values():
                # 退而使用位置：通常第一列是日期，第三列是美国国债收益率
                cols = hist.columns.tolist()
                col_map = {cols[0]: "date"}
                # 尝试找到美国相关列（通常在中国列之后）
                if len(cols) >= 3:
                    col_map[cols[2]] = "treasury_yield_10y"
                else:
                    col_map[cols[1]] = "treasury_yield_10y"
                logger.warning(
                    "列名无法精确识别, 使用位置推断: %s", col_map
                )

            hist = hist.rename(columns=col_map)
            df = hist[["date", "treasury_yield_10y"]].copy()
            df["date"] = pd.to_datetime(df["date"])

            # 去除空值
            df = df.dropna(subset=["treasury_yield_10y"])

            # 按日期范围过滤
            mask = (df["date"] >= pd.to_datetime(start_date)) & (
                df["date"] <= pd.to_datetime(end_date)
            )
            df = df.loc[mask].reset_index(drop=True)

            return df if not df.empty else None

        except ImportError:
            logger.error("akshare 未安装, 请执行: pip install akshare")
            return None
        except Exception as e:
            logger.error("AKShare 采集美债收益率异常: %s", e, exc_info=True)
            return None

    def fetch_fed_rate(self) -> pd.DataFrame:
        """
        采集美联储基准利率（Federal Funds Rate）历史数据

        Returns
        -------
        pd.DataFrame
            columns = ['date', 'fed_rate']
        """
        logger.info("开始采集美联储基准利率")

        # 优先使用 AKShare
        df = self._fetch_fed_rate_akshare()

        if df is not None and not df.empty:
            logger.info("美联储利率采集成功, 共 %d 条记录", len(df))
            return df

        # 备选：通过 yfinance 获取联邦基金利率 ETF 代理
        logger.warning("AKShare 采集失败, 尝试 yfinance 备选方案")
        df = self._fetch_fed_rate_yfinance()

        if df is not None and not df.empty:
            logger.info("美联储利率(yfinance)采集成功, 共 %d 条记录", len(df))
            return df

        # 备选 2：从 FRED 网页抓取
        logger.warning("yfinance 采集失败, 尝试 FRED 网页抓取")
        df = self._fetch_fed_rate_fred()

        if df is not None and not df.empty:
            logger.info("美联储利率(FRED)采集成功, 共 %d 条记录", len(df))
            return df

        logger.error("所有数据源均采集失败, 返回空 DataFrame")
        return pd.DataFrame(columns=["date", "fed_rate"])

    def _fetch_fed_rate_akshare(self) -> Optional[pd.DataFrame]:
        """通过 AKShare 采集美联储利率"""
        try:
            import akshare as ak

            hist = ak.macro_bank_usa_interest_rate()

            if hist is None or hist.empty:
                logger.warning("AKShare macro_bank_usa_interest_rate 返回空数据")
                return None

            # 标准化列名
            col_map = {}
            for col in hist.columns:
                col_str = str(col)
                if "日期" in col_str or "date" in col_str.lower() or "报告日期" in col_str:
                    col_map[col] = "date"
                elif "利率" in col_str or "rate" in col_str.lower() or "今值" in col_str or "现值" in col_str:
                    col_map[col] = "fed_rate"

            if "date" not in col_map.values() or "fed_rate" not in col_map.values():
                cols = hist.columns.tolist()
                col_map = {cols[0]: "date", cols[1]: "fed_rate"}
                logger.warning(
                    "列名无法精确识别, 使用前两列: %s -> date, %s -> fed_rate",
                    cols[0],
                    cols[1],
                )

            hist = hist.rename(columns=col_map)
            df = hist[["date", "fed_rate"]].copy()
            df["date"] = pd.to_datetime(df["date"], errors="coerce")
            df["fed_rate"] = pd.to_numeric(df["fed_rate"], errors="coerce")

            # 去除无效行
            df = df.dropna(subset=["date", "fed_rate"]).reset_index(drop=True)

            # 按日期升序排列
            df = df.sort_values("date").reset_index(drop=True)

            return df if not df.empty else None

        except ImportError:
            logger.error("akshare 未安装, 请执行: pip install akshare")
            return None
        except Exception as e:
            logger.error("AKShare 采集美联储利率异常: %s", e, exc_info=True)
            return None

    def _fetch_fed_rate_yfinance(self) -> Optional[pd.DataFrame]:
        """
        通过 yfinance 采集联邦基金有效利率的代理数据

        使用 ^IRX（13-Week Treasury Bill）作为短期利率的近似参考。
        注意：这不是联邦基金利率本身，而是一个近似代理。
        """
        try:
            import yfinance as yf

            ticker = yf.Ticker("^IRX")
            hist = ticker.history(period="max")

            if hist.empty:
                logger.warning("yfinance ^IRX 返回空数据")
                return None

            df = pd.DataFrame(
                {
                    "date": hist.index.date,
                    "fed_rate": hist["Close"].values,
                }
            )
            df["date"] = pd.to_datetime(df["date"])

            logger.info("注意: yfinance 数据来自 ^IRX (13周国债利率), 为近似值")
            return df

        except ImportError:
            logger.error("yfinance 未安装, 请执行: pip install yfinance")
            return None
        except Exception as e:
            logger.error("yfinance 采集联邦基金利率代理异常: %s", e, exc_info=True)
            return None

    def _fetch_fed_rate_fred(self) -> Optional[pd.DataFrame]:
        """
        从 FRED 网页抓取联邦基金有效利率（FEDFUNDS）

        通过 FRED 提供的 CSV 下载接口获取数据。
        """
        try:
            url = (
                "https://fred.stlouisfed.org/graph/fredgraph.csv"
                "?id=FEDFUNDS"
                "&cosd=1954-07-01"
                "&coed=9999-12-31"
            )
            df = pd.read_csv(url)

            if df.empty:
                logger.warning("FRED CSV 返回空数据")
                return None

            # FRED CSV 通常列名为 DATE 和 FEDFUNDS
            col_map = {}
            for col in df.columns:
                col_upper = str(col).upper()
                if "DATE" in col_upper:
                    col_map[col] = "date"
                elif "FEDFUNDS" in col_upper or "VALUE" in col_upper:
                    col_map[col] = "fed_rate"

            if "date" not in col_map.values() or "fed_rate" not in col_map.values():
                cols = df.columns.tolist()
                col_map = {cols[0]: "date", cols[1]: "fed_rate"}
                logger.warning(
                    "FRED CSV 列名无法识别, 使用前两列: %s -> date, %s -> fed_rate",
                    cols[0],
                    cols[1],
                )

            df = df.rename(columns=col_map)
            df = df[["date", "fed_rate"]].copy()
            df["date"] = pd.to_datetime(df["date"], errors="coerce")
            df["fed_rate"] = pd.to_numeric(df["fed_rate"], errors="coerce")

            # 去除无效行（FRED 有时用 '.' 表示缺失值）
            df = df.dropna(subset=["date", "fed_rate"]).reset_index(drop=True)

            return df if not df.empty else None

        except Exception as e:
            logger.error("FRED 网页抓取联邦基金利率异常: %s", e, exc_info=True)
            return None

    # ------------------------------------------------------------------
    # Step 3: 非农 / CPI / 存库 / fetch_all（待实现）
    # ------------------------------------------------------------------

    def fetch_non_farm(self) -> pd.DataFrame:
        """采集美国非农就业人数（月度数据）"""
        logger.info("开始采集非农就业数据")
        try:
            # 从 FRED CSV 下载 PAYEMS 数据
            import requests
            url = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=PAYEMS"
            resp = requests.get(url, timeout=30)
            if resp.status_code == 200:
                from io import StringIO
                df = pd.read_csv(StringIO(resp.text))
                df.columns = ['date', 'non_farm']
                df['date'] = pd.to_datetime(df['date'])
                df['non_farm'] = pd.to_numeric(df['non_farm'], errors='coerce')
                df = df.dropna()
                logger.info("非农数据采集成功, 共 %d 条", len(df))
                return df
        except Exception as e:
            logger.error("非农数据采集失败: %s", e, exc_info=True)

        logger.error("非农数据采集失败, 返回空 DataFrame")
        return pd.DataFrame(columns=['date', 'non_farm'])

    def fetch_cpi(self) -> pd.DataFrame:
        """采集美国CPI通胀率（月度数据）"""
        logger.info("开始采集CPI数据")
        try:
            # 从 FRED CSV 下载 CPIAUCSL 数据
            import requests
            url = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=CPIAUCSL"
            resp = requests.get(url, timeout=30)
            if resp.status_code == 200:
                from io import StringIO
                df = pd.read_csv(StringIO(resp.text))
                df.columns = ['date', 'cpi']
                df['date'] = pd.to_datetime(df['date'])
                df['cpi'] = pd.to_numeric(df['cpi'], errors='coerce')
                df = df.dropna()
                logger.info("CPI数据采集成功, 共 %d 条", len(df))
                return df
        except Exception as e:
            logger.error("CPI数据采集失败: %s", e, exc_info=True)

        logger.error("CPI数据采集失败, 返回空 DataFrame")
        return pd.DataFrame(columns=['date', 'cpi'])

    def save_to_db(self, data: pd.DataFrame, table_name: str = "fundamentals"):
        """
        将基本面数据存入 PostgreSQL

        Parameters
        ----------
        data : pd.DataFrame
            包含基本面数据的 DataFrame
        table_name : str
            表名（默认 fundamentals）
        """
        if data is None or data.empty:
            logger.warning("save_to_db: 数据为空, 跳过")
            return

        from ..common.db_pool import get_db_connection

        create_table_sql = """
        CREATE TABLE IF NOT EXISTS fundamentals (
            id SERIAL PRIMARY KEY,
            date DATE NOT NULL,
            dollar_index FLOAT,
            treasury_yield_10y FLOAT,
            fed_rate FLOAT,
            non_farm FLOAT,
            cpi FLOAT,
            created_at TIMESTAMP DEFAULT NOW(),
            UNIQUE(date)
        );
        """

        upsert_sql = """
        INSERT INTO fundamentals (date, dollar_index, treasury_yield_10y, fed_rate, non_farm, cpi)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (date) DO UPDATE SET
            dollar_index = COALESCE(EXCLUDED.dollar_index, fundamentals.dollar_index),
            treasury_yield_10y = COALESCE(EXCLUDED.treasury_yield_10y, fundamentals.treasury_yield_10y),
            fed_rate = COALESCE(EXCLUDED.fed_rate, fundamentals.fed_rate),
            non_farm = COALESCE(EXCLUDED.non_farm, fundamentals.non_farm),
            cpi = COALESCE(EXCLUDED.cpi, fundamentals.cpi);
        """

        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    # 自动建表
                    cursor.execute(create_table_sql)
                    conn.commit()

                    # 遍历 DataFrame 逐行 UPSERT
                    count = 0
                    for _, row in data.iterrows():
                        cursor.execute(upsert_sql, (
                            row.get('date'),
                            row.get('dollar_index'),
                            row.get('treasury_yield_10y'),
                            row.get('fed_rate'),
                            row.get('non_farm'),
                            row.get('cpi'),
                        ))
                        count += 1
                    conn.commit()
                    logger.info("save_to_db: 成功写入/更新 %d 条记录到表 %s", count, table_name)
        except Exception as e:
            logger.error("save_to_db 失败: %s", e, exc_info=True)
            raise

    def fetch_all(self) -> dict:
        """
        采集所有基本面数据

        依次调用 5 个 fetch 方法，每个独立 try-except，一个失败不影响其他。

        Returns
        -------
        dict
            {"dollar_index": df1, "treasury_yield": df2, "fed_rate": df3,
             "non_farm": df4, "cpi": df5}
        """
        logger.info("========== 开始采集所有基本面数据 ==========")
        results = {}

        # 1. 美元指数
        try:
            df = self.fetch_dollar_index()
            results["dollar_index"] = df
        except Exception as e:
            logger.error("美元指数采集异常: %s", e, exc_info=True)
            results["dollar_index"] = pd.DataFrame()

        # 2. 美债收益率
        try:
            df = self.fetch_treasury_yield()
            results["treasury_yield"] = df
        except Exception as e:
            logger.error("美债收益率采集异常: %s", e, exc_info=True)
            results["treasury_yield"] = pd.DataFrame()

        # 3. 美联储利率
        try:
            df = self.fetch_fed_rate()
            results["fed_rate"] = df
        except Exception as e:
            logger.error("美联储利率采集异常: %s", e, exc_info=True)
            results["fed_rate"] = pd.DataFrame()

        # 4. 非农就业
        try:
            df = self.fetch_non_farm()
            results["non_farm"] = df
        except Exception as e:
            logger.error("非农数据采集异常: %s", e, exc_info=True)
            results["non_farm"] = pd.DataFrame()

        # 5. CPI
        try:
            df = self.fetch_cpi()
            results["cpi"] = df
        except Exception as e:
            logger.error("CPI数据采集异常: %s", e, exc_info=True)
            results["cpi"] = pd.DataFrame()

        # 汇总日志
        summary = {k: len(v) for k, v in results.items()}
        logger.info("基本面数据采集完成, 汇总: %s", summary)
        total = sum(summary.values())
        logger.info("========== 采集结束, 共 %d 条数据 ==========", total)

        return results
