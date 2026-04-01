"""
完整流程测试 - 包含实际交易（SimNow 模拟盘）
行情 -> ML预测 -> 信号处理 -> 风控 -> 实际发单
"""
import sys, os, time, logging
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

def run_full_pipeline_with_trade():
    logger.info("=" * 60)
    logger.info("完整流程测试（包含实际交易）")
    logger.info("=" * 60)
    
    # ========== 1. 行情数据采集 ==========
    logger.info("\n[1/6] 行情数据采集...")
    from quant.data_collector.ctp_market import start_collector, get_recent_klines
    
    # 启动行情采集
    api = start_collector(
        broker_id="9999",
        user_id="256693",
        password="@Cmx1454697261",
        md_address="tcp://182.254.243.31:30011",
        symbols=["au2606"]
    )
    
    logger.info("✅ CTP 连接成功，等待 Tick（10秒）...")
    time.sleep(10)
    
    # 获取 K 线
    kline_data = get_recent_klines(symbol='au2606', count=100, period='1min')
    logger.info(f"   K 线数据: {len(kline_data)} 根")
    
    if len(kline_data) < 60:
        logger.warning(f"⚠️ K 线不足 60 根（{len(kline_data)}），尝试备用数据...")
        try:
            import akshare as ak
            import pandas as pd
            df = ak.futures_zh_minute_sina(symbol="au2606", period="1")
            if df is not None and len(df) >= 60:
                kline_data = df.tail(100).copy()
                kline_data.columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume', 'hold']
                kline_data = kline_data[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
                for col in ['open', 'high', 'low', 'close', 'volume']:
                    kline_data[col] = pd.to_numeric(kline_data[col], errors='coerce')
                kline_data.reset_index(drop=True, inplace=True)
                logger.info(f"   AkShare 获取到 {len(kline_data)} 根 K 线")
        except Exception as e:
            logger.error(f"   AkShare 获取失败: {e}")
    
    if kline_data is None or len(kline_data) < 60:
        logger.error("❌ 无法获取足够的 K 线数据，流程终止")
        api.Release()
        return
    
    logger.info(f"✅ K 线数据就绪: {len(kline_data)} 根")
    logger.info(f"   最新价格: {kline_data['close'].iloc[-1]}")
    
    # ========== 2. ML 预测 ==========
    logger.info("\n[2/6] ML 预测...")
    from quant.signal_generator.ml_predictor import MLPredictor
    
    predictor = MLPredictor()
    ml_signal = predictor.predict(kline_data)
    
    if ml_signal is None:
        logger.error("❌ ML 预测返回 None")
        api.Release()
        return
    
    logger.info(f"✅ ML 预测结果:")
    logger.info(f"   方向: {ml_signal.get('direction', 'N/A')}")
    logger.info(f"   置信度: {ml_signal.get('confidence', 'N/A')}")
    logger.info(f"   预测值: {ml_signal.get('prediction', 'N/A')}")
    
    # ========== 3. 信号处理 ==========
    logger.info("\n[3/6] 信号处理...")
    from quant.common.config import config
    from quant.risk_executor.signal_processor import SignalProcessor
    
    processor = SignalProcessor(config)
    trade_intent = processor.process_signal(ml_signal)
    
    if trade_intent is None:
        logger.info("⚠️ 置信度不足，信号被过滤")
        logger.info("✅ 流程到此结束（无交易信号）")
        api.Release()
        return
    
    logger.info(f"✅ 交易意图:")
    logger.info(f"   方向: {trade_intent.direction}")
    logger.info(f"   动作: {trade_intent.action}")
    logger.info(f"   置信度: {trade_intent.confidence}")
    logger.info(f"   数量: {trade_intent.volume}")
    
    # ========== 4. 风控检查 ==========
    logger.info("\n[4/6] 风控检查...")
    from quant.risk_executor.position_manager import PositionManager
    from quant.risk_executor.risk_manager import RiskManager
    
    position_mgr = PositionManager()
    risk_mgr = RiskManager(position_mgr, config)
    
    final_order = risk_mgr.check_and_adjust(trade_intent)
    
    if final_order is None:
        logger.info("⚠️ 风控拦截")
        logger.info("✅ 流程到此结束（风控拦截）")
        api.Release()
        return
    
    logger.info(f"✅ 风控通过:")
    logger.info(f"   {final_order}")
    
    # ========== 5. 连接交易接口 ==========
    logger.info("\n[5/6] 连接 CTP 交易接口...")
    from quant.data_collector.ctp_trade import CTPTradeApi
    
    trade_api = CTPTradeApi(
        broker_id="9999",
        account_id="256693",
        password="@Cmx1454697261",
        td_address="tcp://182.254.243.31:30001",
        app_id="simnow_client_test",
        auth_code="0000000000000000"
    )
    
    try:
        trade_api.connect()
        logger.info("✅ 交易接口连接成功")
        time.sleep(2)  # 等待连接稳定
    except Exception as e:
        logger.error(f"❌ 交易接口连接失败: {e}")
        api.Release()
        return
    
    # ========== 6. 实际发单 ==========
    logger.info("\n[6/6] 实际发单（SimNow 模拟盘）...")
    from quant.risk_executor.trade_executor import TradeExecutor
    
    executor = TradeExecutor(config, trade_api)
    
    # 获取当前价格
    current_price = float(kline_data['close'].iloc[-1])
    logger.info(f"   当前价格: {current_price}")
    
    try:
        order = executor.execute_order(final_order, price=current_price)
        
        if order:
            logger.info(f"✅ 订单已发送:")
            logger.info(f"   订单ID: {order.order_id if hasattr(order, 'order_id') else 'N/A'}")
            logger.info(f"   方向: {order.direction}")
            logger.info(f"   动作: {order.action}")
            logger.info(f"   数量: {order.volume}")
            logger.info(f"   价格: {order.entry_price}")
            
            # 等待成交回报
            logger.info("\n等待成交回报（10秒）...")
            time.sleep(10)
            
        else:
            logger.warning("⚠️ 订单被冷却机制拦截")
    
    except Exception as e:
        logger.error(f"❌ 发单失败: {e}", exc_info=True)
    
    # ========== 总结 ==========
    logger.info("\n" + "=" * 60)
    logger.info("完整流程测试结束")
    logger.info("=" * 60)
    logger.info(f"  K 线数据: {len(kline_data)} 根")
    logger.info(f"  ML 预测: {ml_signal.get('direction')} (置信度 {ml_signal.get('confidence', 0):.2f})")
    logger.info(f"  信号处理: {'通过' if trade_intent else '过滤'}")
    logger.info(f"  风控检查: {'通过' if final_order else '拦截'}")
    logger.info(f"  交易执行: {'已发单' if order else '未发单'}")
    
    # 清理
    api.Release()
    logger.info("\n✅ 流程完成，资源已释放")

if __name__ == "__main__":
    run_full_pipeline_with_trade()
