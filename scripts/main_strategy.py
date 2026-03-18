"""
量化交易主策略执行引擎
行情 -> ML预测 -> 信号处理 -> 风控 -> 发单
"""
import sys
import os
import time
import signal
import logging
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from quant.common.config import config
from quant.data_collector.ctp_market import start_collector, get_recent_klines
from quant.data_collector.ctp_trade import CTPTradeApi
from quant.signal_generator.ml_predictor import MLPredictor
from quant.risk_executor.position_manager import PositionManager
from quant.risk_executor.signal_processor import SignalProcessor
from quant.risk_executor.risk_manager import RiskManager
from quant.risk_executor.trade_executor import TradeExecutor

# 配置日志
os.makedirs('logs', exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('logs/main_strategy.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class QuantTradingEngine:
    """量化交易引擎"""
    
    def __init__(self):
        self.running = False
        self.market_api = None  # CTP md api 对象
        self.trade_api = None
        self.ml_predictor = None
        self.position_manager = None
        self.signal_processor = None
        self.risk_manager = None
        self.trade_executor = None
        self.backup_source = None
        
    def initialize(self):
        """初始化所有组件"""
        logger.info("=" * 60)
        logger.info("量化交易引擎启动中...")
        logger.info("=" * 60)
        
        try:
            # 1. 初始化交易 API
            logger.info("1. 初始化交易 API...")
            self.trade_api = CTPTradeApi(
                broker_id=config.ctp.broker_id,
                account_id=config.ctp.account_id,
                password=config.ctp.password.get_secret_value(),
                td_address=config.ctp.td_address,
                app_id=config.ctp.app_id,
                auth_code=config.ctp.auth_code
            )
            
            # 2. 初始化 ML 预测器
            logger.info("2. 初始化 ML 预测器...")
            self.ml_predictor = MLPredictor()
            
            # 3. 初始化持仓管理器
            logger.info("3. 初始化持仓管理器...")
            self.position_manager = PositionManager()
            
            # 4. 初始化信号处理器
            logger.info("4. 初始化���号处理器...")
            self.signal_processor = SignalProcessor(config)
            
            # 5. 初始化风控管理器
            logger.info("5. 初始化风控管理器...")
            self.risk_manager = RiskManager(self.position_manager, config)
            
            # 6. 初始化交易执行器
            logger.info("6. 初始化交易执行器...")
            self.trade_executor = TradeExecutor(config, self.trade_api)
            
            # 7. 初始化备用数据源（延迟导入，避免 structlog）
            logger.info("7. 初始化备用数据源...")
            try:
                from quant.data_collector.backup_data_source import get_backup_data_source
                self.backup_source = get_backup_data_source()
                logger.info(f"   备用数据源: {self.backup_source.data_source}")
            except Exception as e:
                logger.warning(f"   备用数据源初始化失败: {e}")
            
            logger.info("✅ 所有组件初始化完成")
            return True
            
        except Exception as e:
            logger.error(f"❌ 初始化失败: {e}")
            return False
    
    def connect(self):
        """连接 CTP"""
        logger.info("连接 CTP 服务器...")
        
        try:
            # 连接行情（函数式，返回 api 对象）
            logger.info("连接行情服务器...")
            self.market_api = start_collector(
                broker_id=config.ctp.broker_id,
                user_id=config.ctp.account_id,
                password=config.ctp.password.get_secret_value(),
                md_address=config.ctp.md_address,
                symbols=[config.strategy.symbol]
            )
            
            # 连接交易
            logger.info("连接交易服务器...")
            self.trade_api.connect()
            
            # 同步持仓
            logger.info("同步持仓...")
            try:
                self.position_manager.sync_from_ctp(self.trade_api)
            except Exception as e:
                logger.warning(f"持仓同步失败: {e}")
            
            logger.info("✅ CTP 连接成功")
            return True
            
        except Exception as e:
            logger.error(f"❌ CTP 连接失败: {e}")
            return False
    
    def get_kline_data(self):
        """获取 K 线数据（支持回退）"""
        symbol = config.strategy.symbol
        
        # 1. 从数据库/tick 缓存获取
        kline_data = get_recent_klines(symbol=symbol, count=100, period='1min')
        
        if kline_data is not None and len(kline_data) >= 60:
            logger.info(f"   数据源: 实时/数据库 ({len(kline_data)} 根)")
            return kline_data
        
        # 2. AkShare 备用
        if self.backup_source:
            try:
                kline_data = self.backup_source.get_realtime_klines(
                    symbol=symbol, count=100, period='1min'
                )
                if kline_data is not None and len(kline_data) >= 60:
                    logger.info(f"   数据源: 备用 API ({len(kline_data)} 根)")
                    return kline_data
            except Exception as e:
                logger.warning(f"   备用数据源失败: {e}")
        
        # 3. 直接用 AkShare
        try:
            import akshare as ak
            import pandas as pd
            df = ak.futures_zh_minute_sina(symbol=symbol, period="1")
            if df is not None and len(df) >= 60:
                kline_data = df.tail(100).copy()
                kline_data.columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume', 'hold']
                kline_data = kline_data[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
                for col in ['open', 'high', 'low', 'close', 'volume']:
                    kline_data[col] = pd.to_numeric(kline_data[col], errors='coerce')
                kline_data.reset_index(drop=True, inplace=True)
                logger.info(f"   数据源: AkShare ({len(kline_data)} 根)")
                return kline_data
        except Exception as e:
            logger.warning(f"   AkShare 获取失败: {e}")
        
        logger.warning("   无法获取足够的 K 线数据")
        return None
    
    def run_strategy_cycle(self):
        """执行一次策略循环"""
        try:
            logger.info("-" * 60)
            logger.info(f"策略循环 [{datetime.now().strftime('%H:%M:%S')}]")
            
            # 1. 获取 K 线
            logger.info("1. 获取 K 线数据...")
            kline_data = self.get_kline_data()
            if kline_data is None or len(kline_data) < 60:
                logger.warning(f"   K 线不足，跳过")
                return
            
            # 2. ML 预测
            logger.info("2. ML 预测...")
            ml_signal = self.ml_predictor.predict(kline_data)
            if ml_signal is None:
                logger.warning("   ML 预测返回 None，跳过")
                return
            logger.info(f"   预测: {ml_signal.get('direction')} 置信度={ml_signal.get('confidence', 0):.2f}")
            
            # 3. 信号处理
            logger.info("3. 信号处理...")
            trade_intent = self.signal_processor.process_signal(ml_signal)
            if trade_intent is None:
                logger.info("   置信度不足，忽略")
                return
            logger.info(f"   意图: {trade_intent}")
            
            # 4. 风控
            logger.info("4. 风控检查...")
            final_order = self.risk_manager.check_and_adjust(trade_intent)
            if final_order is None:
                logger.info("   风控拦截")
                return
            logger.info(f"   风控通过: {final_order}")
            
            # 5. 执行
            logger.info("5. 执行交易...")
            result = self.trade_executor.execute_order(final_order)
            if result:
                logger.info("   ✅ 交易指令已发送")
            else:
                logger.warning("   ⚠️ 订单被拦截")
            
        except Exception as e:
            logger.error(f"策略循环异常: {e}", exc_info=True)
    
    def main_loop(self):
        """主事件循环"""
        logger.info("=" * 60)
        logger.info("进入主事件循环（60秒/周期）")
        logger.info("=" * 60)
        
        self.running = True
        cycle_count = 0
        
        try:
            while self.running:
                cycle_count += 1
                logger.info(f"\n第 {cycle_count} 次循环")
                
                self.run_strategy_cycle()
                
                # 每 5 个循环同步持仓
                if cycle_count % 5 == 0:
                    try:
                        self.position_manager.sync_from_ctp(self.trade_api)
                    except Exception as e:
                        logger.warning(f"持仓同步失败: {e}")
                
                logger.info("等待下一个周期...")
                time.sleep(60)
                
        except KeyboardInterrupt:
            logger.info("\n收到中断信号...")
        except Exception as e:
            logger.error(f"主循环异常: {e}", exc_info=True)
        finally:
            self.shutdown()
    
    def shutdown(self):
        """关闭"""
        logger.info("=" * 60)
        logger.info("引擎关闭中...")
        self.running = False
        
        if self.market_api:
            try:
                self.market_api.Release()
            except:
                pass
        
        logger.info("✅ 引擎已关闭")


def main():
    engine = QuantTradingEngine()
    
    def signal_handler(sig, frame):
        logger.info("\n收到退出信号...")
        engine.running = False
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    if not engine.initialize():
        return 1
    
    if not engine.connect():
        return 1
    
    engine.main_loop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
