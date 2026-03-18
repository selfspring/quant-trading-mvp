"""
CTP 行情数据采集模块 - 简化版
移除复杂依赖，专注于 Tick 接收和 K 线聚合
"""
import os
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, Optional
from collections import defaultdict, deque

import pandas as pd
from openctp_ctp import mdapi

# 全局引用，防止 GC
_global_api = None
_global_spi = None


class BarData:
    """K线数据"""
    def __init__(self, symbol, datetime, open_price, high_price, low_price, close_price, volume, open_interest):
        self.symbol = symbol
        self.datetime = datetime
        self.open_price = open_price
        self.high_price = high_price
        self.low_price = low_price
        self.close_price = close_price
        self.volume = volume
        self.open_interest = open_interest


class MdSpi(mdapi.CThostFtdcMdSpi):
    """行情回调接口"""
    
    def __init__(self, api, collector):
        super().__init__()
        self.api = api
        self.collector = collector
        self.tick_count = 0
    
    def OnFrontConnected(self):
        """连接成功"""
        print(f"[{datetime.now()}] CTP 连接成功")
        
        # 登录请求
        req = mdapi.CThostFtdcReqUserLoginField()
        req.BrokerID = self.collector.broker_id
        req.UserID = self.collector.user_id
        req.Password = self.collector.password
        
        self.api.ReqUserLogin(req, 0)
    
    def OnRspUserLogin(self, pRspUserLogin, pRspInfo, nRequestID, bIsLast):
        """登录响应"""
        if pRspInfo and pRspInfo.ErrorID != 0:
            print(f"[{datetime.now()}] 登录失败: {pRspInfo.ErrorMsg}")
            return
        
        print(f"[{datetime.now()}] 登录成功")
        self.collector.connected = True
        
        # 订阅合约
        for symbol in self.collector.symbols:
            instrument_id = symbol.upper().encode('utf-8')
            ret = self.api.SubscribeMarketData([instrument_id], 1)
            print(f"[{datetime.now()}] 订阅 {symbol} -> ret={ret}")
    
    def OnRspSubMarketData(self, pSpecificInstrument, pRspInfo, nRequestID, bIsLast):
        """订阅行情响应"""
        if pRspInfo and pRspInfo.ErrorID != 0:
            symbol = pSpecificInstrument.InstrumentID if pSpecificInstrument else "未知"
            print(f"[{datetime.now()}] 订阅失败 {symbol}: {pRspInfo.ErrorMsg}")
        else:
            symbol = pSpecificInstrument.InstrumentID if pSpecificInstrument else "未知"
            print(f"[{datetime.now()}] 订阅确认: {symbol}")
    
    def OnRtnDepthMarketData(self, pDepthMarketData):
        """行情数据回调 - 核心逻辑"""
        if not pDepthMarketData:
            return
        
        self.tick_count += 1
        
        # 构造 tick 数据
        tick_data = {
            'symbol': pDepthMarketData.InstrumentID,
            'last_price': pDepthMarketData.LastPrice,
            'volume': pDepthMarketData.Volume,
            'open_interest': pDepthMarketData.OpenInterest,
            'datetime': datetime.now()
        }
        
        # 打印每个 tick
        print(f"[{datetime.now()}] Tick #{self.tick_count}: {tick_data['symbol']} {tick_data['last_price']:.2f}")
        
        # 缓存 tick
        self.collector.cache_tick(tick_data)
        
        # 聚合 K 线
        try:
            self.collector.aggregate_klines(tick_data)
        except Exception as e:
            print(f"[{datetime.now()}] K线聚合失败: {e}")


class CtpMarketCollector:
    """CTP 行情采集器 - 简化版"""
    
    def __init__(self, broker_id: str, user_id: str, password: str, md_address: str, symbols: list):
        self.broker_id = broker_id
        self.user_id = user_id
        self.password = password
        self.md_address = md_address
        self.symbols = symbols
        
        # CTP API
        self.api = None
        self.spi = None
        self.connected = False
        
        # Tick 缓存 {symbol: deque}
        self.tick_cache: Dict[str, deque] = defaultdict(lambda: deque(maxlen=12000))
        self.tick_lock = threading.Lock()
        
        # K 线聚合器 {(symbol, period): current_bar}
        self.bars: Dict[tuple, dict] = {}
        self.bar_lock = threading.Lock()
        
        # 运行状态
        self.running = False
        
        print(f"[{datetime.now()}] 采集器初始化完成")
    
    def connect(self):
        """连接 CTP"""
        global _global_api, _global_spi
        
        print(f"[{datetime.now()}] 开始连接 CTP...")
        
        # 创建流文件目录
        flow_path = "./ctp_flow/"
        os.makedirs(flow_path, exist_ok=True)
        
        # 创建 API
        self.api = mdapi.CThostFtdcMdApi.CreateFtdcMdApi(flow_path)
        _global_api = self.api  # 全局引用
        
        # 创建 SPI
        self.spi = MdSpi(self.api, self)
        _global_spi = self.spi  # 全局引用
        
        self.api.RegisterSpi(self.spi)
        
        # 注册前置
        self.api.RegisterFront(self.md_address)
        
        # 初始化
        self.api.Init()
        
        # 等待连接
        max_wait = 10
        for i in range(max_wait):
            time.sleep(1)
            if self.connected:
                break
        
        if not self.connected:
            raise TimeoutError("CTP 连接超时")
        
        print(f"[{datetime.now()}] CTP 连接完成")
    
    def cache_tick(self, tick_data: dict):
        """缓存 tick 数据"""
        symbol = tick_data['symbol']
        with self.tick_lock:
            self.tick_cache[symbol].append(tick_data.copy())
    
    def aggregate_klines(self, tick_data: dict):
        """聚合多周期 K 线"""
        symbol = tick_data['symbol']
        tick_time = tick_data['datetime']
        
        # 支持的周期（分钟）
        periods = {
            '1min': 1,
            '5min': 5,
            '15min': 15,
            '30min': 30,
            '1h': 60
        }
        
        with self.bar_lock:
            for period_name, minutes in periods.items():
                key = (symbol, period_name)
                
                # 计算 bar 起始时间
                bar_start = self._get_bar_start(tick_time, minutes)
                
                # 获取或创建 bar
                if key not in self.bars:
                    self.bars[key] = self._create_bar(tick_data, bar_start)
                    continue
                
                current_bar = self.bars[key]
                
                # 检查是否需要新 bar
                bar_end = current_bar['timestamp'] + timedelta(minutes=minutes)
                if tick_time >= bar_end:
                    # 当前 bar 完成
                    self._on_bar_finished(current_bar, period_name)
                    
                    # 创建新 bar
                    self.bars[key] = self._create_bar(tick_data, bar_start)
                else:
                    # 更新当前 bar
                    current_bar['high'] = max(current_bar['high'], tick_data['last_price'])
                    current_bar['low'] = min(current_bar['low'], tick_data['last_price'])
                    current_bar['close'] = tick_data['last_price']
                    current_bar['volume'] = tick_data['volume']
                    current_bar['open_interest'] = tick_data['open_interest']
    
    def _get_bar_start(self, dt: datetime, minutes: int) -> datetime:
        """计算 bar 起始时间"""
        minute = (dt.minute // minutes) * minutes
        return dt.replace(minute=minute, second=0, microsecond=0)
    
    def _create_bar(self, tick_data: dict, bar_start: datetime) -> dict:
        """创建新 bar"""
        return {
            'timestamp': bar_start,
            'symbol': tick_data['symbol'],
            'open': tick_data['last_price'],
            'high': tick_data['last_price'],
            'low': tick_data['last_price'],
            'close': tick_data['last_price'],
            'volume': tick_data['volume'],
            'open_interest': tick_data['open_interest']
        }
    
    def _on_bar_finished(self, bar: dict, period: str):
        """K 线完成回调"""
        print(f"[{datetime.now()}] K线完成 [{period}] {bar['symbol']} {bar['timestamp']} "
              f"O:{bar['open']:.2f} H:{bar['high']:.2f} L:{bar['low']:.2f} C:{bar['close']:.2f}")
        
        # TODO: 这里可以保存到数据库
    
    def get_recent_klines(self, symbol: str, count: int = 60, period: str = '1min') -> pd.DataFrame:
        """
        获取最近 N 根 K 线
        
        Args:
            symbol: 合约代码
            count: K 线数量
            period: 周期 ('1min', '5min', '15min', '30min', '1h')
        
        Returns:
            DataFrame with columns: timestamp, open, high, low, close, volume
        """
        period_minutes = {
            '1min': 1,
            '5min': 5,
            '15min': 15,
            '30min': 30,
            '1h': 60
        }
        
        minutes = period_minutes.get(period, 1)
        
        # 从 tick 缓存聚合
        with self.tick_lock:
            ticks = list(self.tick_cache.get(symbol, []))
        
        if not ticks:
            return pd.DataFrame(columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        # 按时间分组聚合
        bars = []
        current_bar = None
        
        for tick in ticks:
            tick_time = tick['datetime']
            bar_start = self._get_bar_start(tick_time, minutes)
            
            if current_bar is None or current_bar['timestamp'] != bar_start:
                # 保存上一个 bar
                if current_bar:
                    bars.append(current_bar)
                
                # 创建新 bar
                current_bar = self._create_bar(tick, bar_start)
            else:
                # 更新当前 bar
                current_bar['high'] = max(current_bar['high'], tick['last_price'])
                current_bar['low'] = min(current_bar['low'], tick['last_price'])
                current_bar['close'] = tick['last_price']
                current_bar['volume'] = tick['volume']
        
        # 保存最后一个 bar
        if current_bar:
            bars.append(current_bar)
        
        # 转换为 DataFrame
        if not bars:
            return pd.DataFrame(columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        df = pd.DataFrame(bars)
        df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
        df = df.tail(count).reset_index(drop=True)
        
        return df
    
    def run(self):
        """启动采集器"""
        self.running = True
        
        try:
            # 连接 CTP
            self.connect()
            
            print(f"[{datetime.now()}] 采集器运行中...")
            
            # 保持运行
            while self.running:
                time.sleep(1)
        
        except KeyboardInterrupt:
            print(f"[{datetime.now()}] 收到中断信号")
        except Exception as e:
            print(f"[{datetime.now()}] 采集器错误: {e}")
            raise
        finally:
            self.shutdown()
    
    def shutdown(self):
        """关闭采集器"""
        print(f"[{datetime.now()}] 关闭采集器...")
        
        self.running = False
        
        if self.api:
            self.api.Release()
        
        print(f"[{datetime.now()}] 采集器已关闭")


def main():
    """测试入口"""
    collector = CtpMarketCollector(
        broker_id="9999",
        user_id="256693",
        password="@Cmx1454697261",
        md_address="tcp://182.254.243.31:30011",
        symbols=["au2606"]
    )
    
    collector.run()


if __name__ == "__main__":
    main()
