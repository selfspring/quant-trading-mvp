"""
备用数据源模块 - 当 SimNow 无实时数据时使用
支持：
1. Tushare 专业版（需 token）
2. AkShare 免费数据（无需 token）
3. 本地 CSV 历史数据回测
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import logging
from quant.common.config import config
from quant.common.db_pool import get_db_connection

logger = logging.getLogger(__name__)


class BackupDataSource:
    """备用数据源管理器"""
    
    def __init__(self):
        self.redis_client = redis.Redis(
            host=config.redis.host,
            port=config.redis.port,
            db=config.redis.db,
            password=config.redis.password.get_secret_value() if config.redis.password else None,
            decode_responses=False
        )
        self.data_source = None  # 'tushare' | 'akshare' | 'csv' | None
        self._initialize_data_source()
    
    def _initialize_data_source(self):
        """初始化数据源（按优先级尝试）"""
        # 1. 尝试 Tushare
        try:
            ts_token = config.get('tushare_token', None)
            if ts_token:
                import tushare as ts
                ts.set_token(ts_token)
                self.pro = ts.pro_api()
                self.data_source = 'tushare'
                logger.info(f"backup_data_source_initialized source='tushare'")
                return
        except Exception as e:
            logger.warning(f"tushare_init_failed error=str(e)")
        
        # 2. 尝试 AkShare（无需 token）
        try:
            import akshare as ak
            self.ak = ak
            self.data_source = 'akshare'
            logger.info(f"backup_data_source_initialized source='akshare'")
            return
        except Exception as e:
            logger.warning(f"akshare_init_failed error=str(e)")
        
        # 3. 回退到 CSV 模式
        logger.info(f"backup_data_source_fallback source='csv'")
        self.data_source = 'csv'
    
    def get_realtime_klines(
        self,
        symbol: str,
        count: int = 100,
        period: str = '1min'
    ) -> Optional[pd.DataFrame]:
        """
        获取实时 K 线数据（从备用数据源）
        
        Args:
            symbol: 合约代码（如 'au2606'）
            count: 需要的 K 线数量
            period: 周期（'1min', '5min', '15min', '1h'）
        
        Returns:
            DataFrame with columns: timestamp, open, high, low, close, volume
            或 None（如果获取失败）
        """
        if self.data_source == 'tushare':
            return self._get_tushare_klines(symbol, count, period)
        elif self.data_source == 'akshare':
            return self._get_akshare_klines(symbol, count, period)
        elif self.data_source == 'csv':
            return self._get_csv_klines(symbol, count, period)
        else:
            logger.error("no_data_source_available")
            return None
    
    def _get_tushare_klines(
        self,
        symbol: str,
        count: int,
        period: str
    ) -> Optional[pd.DataFrame]:
        """从 Tushare 获取期货 K 线"""
        try:
            # 映射周期到 Tushare 格式
            period_map = {
                '1min': '1',
                '5min': '5',
                '15min': '15',
                '30min': '30',
                '1h': '60',
            }
            ts_period = period_map.get(period, '1')
            
            # Tushare 期货合约代码格式（如 AU2606.CFX）
            ts_symbol = symbol.upper() + '.CFX'
            
            # 计算时间范围（向前推 count * period）
            end_date = datetime.now().strftime('%Y%m%d')
            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y%m%d')
            
            df = self.pro.fut_daily(
                ts_code=ts_symbol,
                start_date=start_date,
                end_date=end_date
            )
            
            if df.empty:
                logger.warning(f"tushare_no_data symbol=ts_symbol")
                return None
            
            # 转换为标准格式
            df = df.rename(columns={
                'trade_date': 'timestamp',
                'open': 'open',
                'high': 'high',
                'low': 'low',
                'close': 'close',
                'vol': 'volume'
            })
            
            # 时间格式转换
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            # 取最近 count 根
            df = df.tail(count).reset_index(drop=True)
            
            logger.info(f"tushare_klines_fetched symbol=symbol, count=len(df)")
            return df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
            
        except Exception as e:
            logger.error(f"tushare_fetch_failed error=str(e)")
            return None
    
    def _get_akshare_klines(
        self,
        symbol: str,
        count: int,
        period: str
    ) -> Optional[pd.DataFrame]:
        """从 AkShare 获取期货 K 线"""
        try:
            # AkShare 期货代码格式（如 "au2606"）
            ak_symbol = symbol.lower()
            
            # 获取实时行情（AkShare 的期货数据）
            # 注意：AkShare 免费数据主要是日线，分钟线可能需要特定接口
            df = self.ak.futures_zh_daily_sina(symbol=ak_symbol)
            
            if df.empty:
                logger.warning(f"akshare_no_data symbol=ak_symbol")
                return None
            
            # 转换为标准格式
            df = df.rename(columns={
                'date': 'timestamp',
                'open': 'open',
                'high': 'high',
                'low': 'low',
                'close': 'close',
                'volume': 'volume'
            })
            
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.tail(count).reset_index(drop=True)
            
            logger.info(f"akshare_klines_fetched symbol=symbol, count=len(df)")
            return df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
            
        except Exception as e:
            logger.error(f"akshare_fetch_failed error=str(e)")
            return None
    
    def _get_csv_klines(
        self,
        symbol: str,
        count: int,
        period: str
    ) -> Optional[pd.DataFrame]:
        """
        从本地 CSV 文件读取历史数据（用于回测）
        文件路径：data/{symbol}_{period}.csv
        """
        import os
        csv_path = os.path.join('data', f'{symbol}_{period}.csv')
        
        if not os.path.exists(csv_path):
            logger.warning(f"csv_file_not_found path=csv_path")
            return None
        
        try:
            df = pd.read_csv(csv_path)
            
            # 确保列名正确
            required_cols = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
            for col in required_cols:
                if col not in df.columns:
                    logger.error(f"csv_missing_column column=col, path=csv_path")
                    return None
            
            # 时间转换
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            # 取最近 count 根
            df = df.tail(count).reset_index(drop=True)
            
            logger.info(f"csv_klines_loaded symbol=symbol, count=len(df), path=csv_path")
            return df[required_cols]
            
        except Exception as e:
            logger.error(f"csv_load_failed error=str(e)")
            return None
    
    def generate_mock_klines(
        self,
        symbol: str,
        count: int = 100,
        period: str = '1min',
        base_price: float = 580.0
    ) -> pd.DataFrame:
        """
        生成模拟 K 线数据（用于测试策略逻辑）
        
        Args:
            symbol: 合约代码
            count: K 线数量
            period: 周期
            base_price: 基准价格
        
        Returns:
            模拟的 K 线 DataFrame
        """
        np.random.seed(42)  # 固定随机种子，便于复现
        
        # 生成时间序列
        now = datetime.now()
        if period.endswith('min'):
            delta_minutes = int(period.replace('min', ''))
            timestamps = [now - timedelta(minutes=(count - i) * delta_minutes) for i in range(count)]
        elif period.endswith('h'):
            delta_hours = int(period.replace('h', ''))
            timestamps = [now - timedelta(hours=(count - i) * delta_hours) for i in range(count)]
        else:
            timestamps = [now - timedelta(minutes=(count - i)) for i in range(count)]
        
        # 生成价格序列（随机游走）
        returns = np.random.normal(0, 0.001, count)  # 日收益率 ~ N(0, 0.1%)
        price_multiplier = np.cumprod(1 + returns)
        close_prices = base_price * price_multiplier
        
        # 生成 OHLC
        open_prices = np.roll(close_prices, 1)
        open_prices[0] = base_price
        
        high_prices = np.maximum(open_prices, close_prices) * (1 + np.random.uniform(0, 0.002, count))
        low_prices = np.minimum(open_prices, close_prices) * (1 - np.random.uniform(0, 0.002, count))
        
        # 生成成交量
        volumes = np.random.randint(100, 10000, count)
        
        df = pd.DataFrame({
            'timestamp': timestamps,
            'open': open_prices,
            'high': high_prices,
            'low': low_prices,
            'close': close_prices,
            'volume': volumes
        })
        
        logger.info(f"mock_klines_generated symbol=symbol, count=count, base_price=base_price")
        return df
    
    def fetch_and_store(
        self,
        symbol: str,
        count: int = 100,
        period: str = '1min'
    ) -> bool:
        """
        从备用数据源获取 K 线并存储到数据库
        
        Args:
            symbol: 合约代码
            count: K 线数量
            period: 周期
        
        Returns:
            True if successful, False otherwise
        """
        df = self.get_realtime_klines(symbol, count, period)
        
        if df is None:
            logger.warning(f"no_data_to_store symbol=symbol")
            return False
        
        # 存储到数据库
        try:
            interval_map = {
                '1min': '1m',
                '5min': '5m',
                '15min': '15m',
                '30min': '30m',
                '1h': '1h',
            }
            db_interval = interval_map.get(period, period)
            
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    for _, row in df.iterrows():
                        query = """
                            INSERT INTO kline_data 
                            (time, symbol, interval, open, high, low, close, volume, open_interest)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (time, symbol, interval) 
                            DO UPDATE SET
                                open = EXCLUDED.open,
                                high = EXCLUDED.high,
                                low = EXCLUDED.low,
                                close = EXCLUDED.close,
                                volume = EXCLUDED.volume,
                                open_interest = EXCLUDED.open_interest
                        """
                        cursor.execute(query, (
                            row['timestamp'],
                            symbol,
                            db_interval,
                            row['open'],
                            row['high'],
                            row['low'],
                            row['close'],
                            row['volume'],
                            0  # open_interest
                        ))
                    conn.commit()
            
            logger.info(f"klines_stored_to_db symbol=symbol, count=len(df), period=period")
            return True
            
        except Exception as e:
            logger.error(f"db_store_failed error=str(e)")
            return False


# 单例模式
_backup_data_source: Optional[BackupDataSource] = None


def get_backup_data_source() -> BackupDataSource:
    """获取备用数据源单例"""
    global _backup_data_source
    if _backup_data_source is None:
        _backup_data_source = BackupDataSource()
    return _backup_data_source
