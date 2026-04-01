"""调试脚本：模拟策略执行流程，检查日志和下单"""
import sys, os, json, logging
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 先配置日志，确保能看到所有输出
log_dir = Path(r"E:\quant-trading-mvp\logs")
log_dir.mkdir(exist_ok=True)
log_file = log_dir / f"debug_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log"

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8', mode='w'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

logger.info("=" * 60)
logger.info(f"调试脚本启动，日志文件：{log_file}")
logger.info("=" * 60)

from quant.common.config import config
from quant.signal_generator.ml_predictor import MLPredictor
from quant.risk_executor.position_manager import PositionManager
from quant.risk_executor.signal_processor import SignalProcessor
from quant.risk_executor.risk_manager import RiskManager
from quant.risk_executor.trade_executor import TradeExecutor
from quant.data_collector.ctp_trade import CTPTradeApi
import pandas as pd
from quant.common.db import db_connection, db_engine

STATE_FILE = Path(r"E:\quant-trading-mvp\data\strategy_state.json")

try:
    # 1. 加载 state
    logger.info("步骤 1: 加载 state")
    if STATE_FILE.exists():
        with open(STATE_FILE, 'r', encoding='utf-8-sig') as f:
            state = json.load(f)
        logger.info(f"加载 state: {json.dumps(state, indent=2, default=str)}")
    else:
        state = {"consecutive_losses": 0, "last_trade_time": None, "open_positions": []}
        logger.info("state 文件不存在，使用空 state")
    
    # 2. 获取 K 线
    logger.info("步骤 2: 获取 K 线数据")
    with db_engine(config) as engine:
        df = pd.read_sql("""
            SELECT time as timestamp, open, high, low, close, volume, COALESCE(open_interest, 0) as open_interest
            FROM kline_data
            WHERE symbol = %s AND interval = '1m'
            ORDER BY time DESC LIMIT 300
        """, engine, params=(config.strategy.symbol,))
    
    if len(df) >= 60:
        df = df.sort_values('timestamp').reset_index(drop=True)
        logger.info(f"获取 K 线：{len(df)} 根")
        current_price = float(df.iloc[-1]['close'])
        logger.info(f"当前价格：{current_price:.2f}")
    else:
        logger.error(f"K 线不足：{len(df)}")
        sys.exit(1)
    
    # 3. 初始化组件
    logger.info("步骤 3: 初始化组件")
    position_manager = PositionManager()
    
    # 恢复 state 持仓到 position_manager
    for pos in state.get('open_positions', []):
        if pos.get('direction') == 'buy':
            position_manager.update_position('long', pos.get('volume', 1))
        elif pos.get('direction') == 'sell':
            position_manager.update_position('short', pos.get('volume', 1))
    
    logger.info(f"恢复持仓后：多头={position_manager.long_volume}, 空头={position_manager.short_volume}")
    
    # 同步 CTP 持仓
    logger.info("步骤 4: 连接 CTP 并同步持仓")
    trade_api = CTPTradeApi(
        broker_id=config.ctp.broker_id,
        account_id=config.ctp.account_id,
        password=config.ctp.password.get_secret_value(),
        td_address=config.ctp.td_address,
        app_id=config.ctp.app_id,
        auth_code=config.ctp.auth_code
    )
    trade_api.connect()
    import time
    time.sleep(2)  # 等待 CTP 回调
    
    position_manager.sync_from_ctp(trade_api)
    logger.info(f"CTP 同步后：多头={position_manager.long_volume}, 空头={position_manager.short_volume}")
    
    # 检查 state 和 CTP 是否一致
    ctp_long = position_manager.long_volume
    ctp_short = position_manager.short_volume
    state_long = sum(1 for p in state.get('open_positions', []) if p.get('direction') == 'buy')
    state_short = sum(1 for p in state.get('open_positions', []) if p.get('direction') == 'sell')
    
    if ctp_long != state_long or ctp_short != state_short:
        logger.warning(f"持仓不一致! CTP: 多{ctp_long}/空{ctp_short}, State: 多{state_long}/空{state_short}")
        if ctp_long == 0 and ctp_short == 0 and len(state.get('open_positions', [])) > 0:
            logger.warning("CTP 无持仓但 state 有记录，清空 state")
            state['open_positions'] = []
            with open(STATE_FILE, 'w', encoding='utf-8') as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
            logger.info("state 已清空")
    
    # 5. ML 预测
    logger.info("步骤 5: ML 预测")
    ml_predictor = MLPredictor()
    ml_signal = ml_predictor.predict(df)
    
    if ml_signal is None:
        logger.info("ML 预测无信号，退出")
        sys.exit(0)
    
    logger.info(f"ML 信号：signal={ml_signal.get('signal')}, confidence={ml_signal.get('confidence', 0):.2f}, prediction={ml_signal.get('prediction', 0):.4f}")
    
    # 置信度过滤
    confidence = ml_signal.get('confidence', 0)
    has_position = len(state.get('open_positions', [])) > 0
    if confidence < 0.40 and not has_position:
        logger.info(f"置信度 {confidence:.2f} < 0.40 且无持仓，跳过")
        sys.exit(0)
    
    # 6. 信号处理
    logger.info("步骤 6: 信号处理")
    signal_processor = SignalProcessor(config)
    trade_intents = signal_processor.process_signal(ml_signal, position_manager)
    
    if not trade_intents:
        logger.info("无交易意图，退出")
        sys.exit(0)
    
    logger.info(f"生成 {len(trade_intents)} 个交易意图：{trade_intents}")
    
    # 7. 执行交易
    logger.info("步骤 7: 执行交易")
    risk_manager = RiskManager(position_manager, config)
    trade_executor = TradeExecutor(config, trade_api)
    
    for i, intent in enumerate(trade_intents):
        logger.info(f"处理意图 {i+1}/{len(trade_intents)}: {intent}")
        
        # 风控检查
        final_intent = risk_manager.check_and_adjust(intent)
        if final_intent is None:
            logger.warning(f"风控拦截：{intent}")
            continue
        
        logger.info(f"风控通过：{final_intent}")
        
        # 执行订单
        result = trade_executor.execute_order(final_intent)
        logger.info(f"execute_order 返回：{result}")
        
        if result:
            logger.info(f"✅ 交易指令已发送：{result}")
            
            # 更新 state
            if final_intent.action == 'open':
                predicted_return = abs(ml_signal.get('prediction', 0.01))
                sl_tp = risk_manager.calc_stop_loss_take_profit(final_intent.direction, current_price, predicted_return)
                state['open_positions'].append({
                    'direction': final_intent.direction,
                    'entry_price': current_price,
                    'entry_time': datetime.now().isoformat(),
                    'predicted_return': predicted_return,
                    'stop_loss': sl_tp['stop_loss'],
                    'take_profit': sl_tp['take_profit'],
                    'volume': final_intent.volume
                })
                logger.info(f"记录开仓：方向={final_intent.direction}, 开仓价={current_price:.2f}, 止损={sl_tp['stop_loss']:.2f}, 止盈={sl_tp['take_profit']:.2f}")
            elif final_intent.action == 'close':
                pos_direction = 'buy' if final_intent.direction == 'sell' else 'sell'
                state['open_positions'] = [p for p in state['open_positions'] if p.get('direction') != pos_direction]
                logger.info(f"清除持仓记录：持仓方向={pos_direction}")
    
    # 8. 保存 state
    logger.info("步骤 8: 保存 state")
    state['consecutive_losses'] = risk_manager.consecutive_losses
    state['last_trade_time'] = datetime.now().isoformat()
    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    logger.info(f"state 已保存：{json.dumps(state, indent=2, default=str)}")
    
    logger.info("=" * 60)
    logger.info("调试脚本执行完成")
    logger.info("=" * 60)
    
except Exception as e:
    logger.error(f"异常：{e}", exc_info=True)
    import traceback
    logger.error(traceback.format_exc())
    sys.exit(1)
