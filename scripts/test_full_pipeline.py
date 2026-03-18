"""
完整流程测试：行情 -> ML预测 -> 信号处理 -> 风控 -> 发单
单次循环，检查每个环节
"""
import sys, os, time, logging
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

def run_full_pipeline():
    logger.info("=" * 60)
    logger.info("完整流程测试")
    logger.info("=" * 60)
    
    # ========== 1. 行情数据采集 ==========
    logger.info("\n[1/5] 行情数据采集...")
    from quant.data_collector.ctp_market import run_collector, get_recent_klines, _tick_cache, _connected, MdSpi
    from openctp_ctp import mdapi
    import threading
    
    # 启动行情采集（后台线程）
    flow_path = "./ctp_flow/"
    os.makedirs(flow_path, exist_ok=True)
    
    api = mdapi.CThostFtdcMdApi.CreateFtdcMdApi(flow_path)
    spi = MdSpi(api, "9999", "256693", "@Cmx1454697261", ["au2606"])
    api.RegisterSpi(spi)
    api.RegisterFront("tcp://182.254.243.31:30011")
    api.Init()
    
    # 等待连接
    import quant.data_collector.ctp_market as ctp_mod
    for i in range(10):
        time.sleep(1)
        if ctp_mod._connected:
            break
    
    if not ctp_mod._connected:
        logger.error("❌ CTP 连接失败")
        return
    
    logger.info("✅ CTP 连接成功，等待 Tick（15秒）...")
    time.sleep(15)
    
    tick_count = ctp_mod._tick_count
    logger.info(f"   收到 {tick_count} 个 Tick")
    
    if tick_count == 0:
        logger.warning("⚠️ 没有收到 Tick，尝试从数据库获取 K 线...")
    
    # 获取 K 线
    kline_data = get_recent_klines(symbol='au2606', count=100, period='1m')
    logger.info(f"   K 线数据: {len(kline_data)} 根")
    
    if len(kline_data) < 60:
        logger.warning(f"⚠️ K 线不足 60 根（{len(kline_data)}），尝试备用数据...")
        # 用 AkShare 获取（不导入 backup_data_source，因为它用了 structlog）
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
    logger.info("\n[2/5] ML 预测...")
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
    logger.info("\n[3/5] 信号处理...")
    from quant.common.config import config
    from quant.risk_executor.signal_processor import SignalProcessor
    
    processor = SignalProcessor(config)
    trade_intent = processor.process_signal(ml_signal)
    
    if trade_intent is None:
        logger.info("⚠️ 置信度不足，信号被过滤（这是正常的风控行为）")
        logger.info("✅ 流程到此结束（无交易信号）")
        api.Release()
        return
    
    logger.info(f"✅ 交易意图:")
    logger.info(f"   方向: {trade_intent.direction}")
    logger.info(f"   动作: {trade_intent.action}")
    logger.info(f"   置信度: {trade_intent.confidence}")
    logger.info(f"   数量: {trade_intent.volume}")
    
    # ========== 4. 风控检查 ==========
    logger.info("\n[4/5] 风控检查...")
    from quant.risk_executor.position_manager import PositionManager
    from quant.risk_executor.risk_manager import RiskManager
    
    position_mgr = PositionManager()
    risk_mgr = RiskManager(position_mgr, config)
    
    final_order = risk_mgr.check_and_adjust(trade_intent)
    
    if final_order is None:
        logger.info("⚠️ 风控拦截（这是正常的风控行为）")
        logger.info("✅ 流程到此结束（风控拦截）")
        api.Release()
        return
    
    logger.info(f"✅ 风控通过:")
    logger.info(f"   {final_order}")
    
    # ========== 5. 交易执行（dry-run） ==========
    logger.info("\n[5/5] 交易执行（dry-run，不实际发单）...")
    logger.info(f"   如果实际执行，将会:")
    logger.info(f"   - 方向: {final_order.direction}")
    logger.info(f"   - 动作: {final_order.action}")
    logger.info(f"   - 数量: {final_order.volume}")
    logger.info(f"   - 合约: au2606")
    logger.info("✅ dry-run 完成，未实际发单")
    
    # ========== 总结 ==========
    logger.info("\n" + "=" * 60)
    logger.info("完整流程测试结束")
    logger.info("=" * 60)
    logger.info(f"  Tick 接收: {tick_count} 个")
    logger.info(f"  K 线数据: {len(kline_data)} 根")
    logger.info(f"  ML 预测: {ml_signal.get('direction')} (置信度 {ml_signal.get('confidence', 0):.2f})")
    logger.info(f"  信号处理: {'通过' if trade_intent else '过滤'}")
    logger.info(f"  风控检���: {'通过' if final_order else '拦截'}")
    logger.info(f"  交易执行: dry-run")
    
    api.Release()

if __name__ == "__main__":
    run_full_pipeline()
