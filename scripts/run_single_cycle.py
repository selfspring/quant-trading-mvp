"""
单次执行策略脚本 - 执行一轮后退出
用于 cron 定时触发（每 5 分钟）
"""
import sys
import os
import json
import logging
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from quant.common.config import config
from quant.common.ctp_factory import ctp_trade_session
from quant.common.db import db_engine
from quant.signal_generator.ml_predictor import MLPredictor
from quant.risk_executor.position_manager import PositionManager
from quant.risk_executor.signal_processor import SignalProcessor
from quant.risk_executor.risk_manager import RiskManager
from quant.risk_executor.trade_executor import TradeExecutor

# 状态文件路径
STATE_FILE = Path(__file__).parent.parent / "data" / "strategy_state.json"
STATE_FILE.parent.mkdir(parents=True, exist_ok=True)

# 日志配置
log_dir = Path(__file__).parent.parent / "logs"
log_dir.mkdir(exist_ok=True)
log_file = log_dir / f"strategy_{datetime.now().strftime('%Y-%m-%d')}.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()
    ],
    force=True  # 强制重新配置，覆盖之前的 logging 设置
)
logger = logging.getLogger(__name__)


def load_state():
    """加载持久化状态"""
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, 'r', encoding='utf-8-sig') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"加载状态失败: {e}")
    return {"consecutive_losses": 0, "last_trade_time": None, "open_positions": []}


def save_state(state):
    """保存持久化状态（原子写入，防止进程崩溃导致文件损坏）"""
    try:
        tmp_file = STATE_FILE.with_suffix('.tmp')
        with open(tmp_file, 'w', encoding='utf-8') as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_file, STATE_FILE)  # 原子替换，不会出现中途截断
    except Exception as e:
        logger.error(f"保存状态失败: {e}")
        if tmp_file.exists():
            tmp_file.unlink(missing_ok=True)


def get_kline_data():
    """从数据库获取 K 线数据，不足时回退到 AkShare"""
    import pandas as pd
    symbol = config.strategy.symbol
    
    # 1. 优先从数据库读取
    try:
        with db_engine(config) as conn:
            # 优先读 30 分钟线（与模型训练一致）
            df = pd.read_sql("""
                SELECT time as timestamp, open, high, low, close, volume, COALESCE(open_interest, 0) as open_interest
                FROM kline_data
                WHERE symbol = %s AND interval = '30m'
                ORDER BY time DESC LIMIT 100
            """, conn, params=(symbol,))
            
            # au2606 没有 30m 时，回退到 au_main 的 30m
            if df is None or len(df) < 60:
                logger.warning(f"{symbol} 30分钟线不足: {len(df) if df is not None else 0}，尝试 au_main")
                df = pd.read_sql("""
                    SELECT time as timestamp, open, high, low, close, volume, COALESCE(open_interest, 0) as open_interest
                    FROM kline_data
                    WHERE symbol = 'au_main' AND interval = '30m'
                    ORDER BY time DESC LIMIT 100
                """, conn)
            
            # 30 分钟线不足时，尝试从 1 分钟线聚合
            if df is None or len(df) < 60:
                logger.warning(f"30 分钟线不足: {len(df) if df is not None else 0}，尝试从 1 分钟线聚合")
                df_1m = pd.read_sql("""
                    SELECT time as timestamp, open, high, low, close, volume, COALESCE(open_interest, 0) as open_interest
                    FROM kline_data
                    WHERE symbol = %s AND interval = '1m'
                    ORDER BY time DESC LIMIT 3000
                """, conn, params=(symbol,))
                
                if df_1m is not None and len(df_1m) >= 30:
                    df_1m = df_1m.sort_values('timestamp').reset_index(drop=True)
                    df_1m['timestamp'] = pd.to_datetime(df_1m['timestamp'])
                    df_1m = df_1m.set_index('timestamp')
                    df = df_1m.resample('30min').agg({
                        'open': 'first', 'high': 'max', 'low': 'min',
                        'close': 'last', 'volume': 'sum', 'open_interest': 'last'
                    }).dropna().reset_index()
                    df = df.rename(columns={'timestamp': 'timestamp'})
                    logger.info(f"从 1 分钟线聚合 30 分钟线: {len(df)} 根")
        
        if df is not None and len(df) >= 60:
            df = df.sort_values('timestamp').reset_index(drop=True)
            logger.info(f"获取 K 线（数据库）: {len(df)} 根")
            return df
        else:
            logger.warning(f"数据库 K 线不足: {len(df) if df is not None else 0}，回退到 AkShare")
    except Exception as e:
        logger.warning(f"数据库读取失败: {e}，回退到 AkShare", exc_info=True)
    
    # 2. 回退到 AkShare
    try:
        import akshare as ak
        df = ak.futures_zh_minute_sina(symbol=symbol, period="1")
        
        if df is None or len(df) < 60:
            logger.error(f"AkShare K 线不足: {len(df) if df is not None else 0}")
            return None
        
        kline_data = df.tail(100).copy()
        kline_data.columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume', 'hold']
        kline_data = kline_data.rename(columns={'hold': 'open_interest'})
        kline_data = kline_data[['timestamp', 'open', 'high', 'low', 'close', 'volume', 'open_interest']]
        for col in ['open', 'high', 'low', 'close', 'volume', 'open_interest']:
            kline_data[col] = pd.to_numeric(kline_data[col], errors='coerce')
        kline_data.reset_index(drop=True, inplace=True)
        logger.info(f"获取 K 线（AkShare）: {len(kline_data)} 根")
        return kline_data
    except Exception as e:
        logger.error(f"获取 K 线失败: {e}")
        return None


def main():
    logger.info("=" * 60)
    logger.info("单次策略执行开始")
    logger.info("=" * 60)
    
    try:
        # 1. 加载状态
        state = load_state()
        logger.info(f"加载状态: 连败={state['consecutive_losses']}, 持仓数={len(state.get('open_positions', []))}")
        
        # 2. 获取 K 线
        logger.info("获取 K 线数据...")
        kline_data = get_kline_data()
        if kline_data is None:
            logger.error("无法获取 K 线，退出")
            return 1
        
        current_price = float(kline_data.iloc[-1]['close'])
        logger.info(f"当前价格: {current_price:.2f}")
        
        # 2.5 K 线时间戳去重：30分钟线每30分钟更新一次，避免重复预测
        latest_kline_time = str(kline_data.iloc[-1]['timestamp'])
        last_kline_time = state.get('last_kline_time')
        if last_kline_time and last_kline_time == latest_kline_time:
            logger.info(f"K 线未更新（时间戳: {latest_kline_time}），跳过本次预测")
            return 0
        logger.info(f"新K线检测到: {latest_kline_time}（上次: {last_kline_time}），执行预测")
        state['last_kline_time'] = latest_kline_time
        
        # 3. 初始化组件
        position_manager = PositionManager()
        risk_manager = RiskManager(position_manager, config)
        signal_processor = SignalProcessor(config)
        
        # 从持久化状态恢复持仓
        for pos in state.get('open_positions', []):
            if pos.get('direction') == 'buy':
                position_manager.update_position('long', pos.get('volume', 1))
            elif pos.get('direction') == 'sell':
                position_manager.update_position('short', pos.get('volume', 1))
        
        if position_manager.has_any_position():
            logger.info(f"恢复持仓: 多头={position_manager.long_volume}, 空头={position_manager.short_volume}")
            # 有持仓时主动同步 CTP，防止 state 脱节
            try:
                with ctp_trade_session(config) as trade_api:
                    position_manager.sync_from_ctp(trade_api)
                    ctp_long = position_manager.long_volume
                    ctp_short = position_manager.short_volume
                    if ctp_long == 0 and ctp_short == 0 and len(state.get('open_positions', [])) > 0:
                        logger.warning("CTP 无持仓但 state 有记录，清空 state")
                        state['open_positions'] = []
                        save_state(state)
            except Exception as e:
                logger.warning(f"启动时 CTP 同步失败: {e}")
        
        # 注入持久化状态
        risk_manager.consecutive_losses = state['consecutive_losses']
        if state['last_trade_time']:
            risk_manager.last_trade_time = datetime.fromisoformat(state['last_trade_time'])
        if state.get('circuit_break_until'):
            risk_manager.circuit_break_until = datetime.fromisoformat(state['circuit_break_until'])
        
        # 4. 检查止损止盈（平仓方式2）
        logger.info("检查止损止盈...")
        stop_intents = risk_manager.check_stop_loss_take_profit(current_price, state.get('open_positions', []))
        
        if stop_intents:
            logger.info(f"触发止损止盈，生成 {len(stop_intents)} 个平仓意图")
            tick_size = config.strategy.tick_size
            slippage_ticks = config.strategy.slippage_ticks
            with ctp_trade_session(config) as trade_api:
                position_manager.sync_from_ctp(trade_api)
                trade_executor = TradeExecutor(config, trade_api)
                for intent in stop_intents:
                    if intent.direction == 'buy':
                        limit_price = round(current_price + tick_size * slippage_ticks, 2)
                    else:
                        limit_price = round(current_price - tick_size * slippage_ticks, 2)
                    result = trade_executor.execute_order(intent, price=limit_price)
                    if result:
                        logger.info(f"✅ 止损止盈平仓已发送: {intent}")
                        pos_direction = 'buy' if intent.direction == 'sell' else 'sell'
                        closed_pos = next((p for p in state['open_positions'] if p.get('direction') == pos_direction), None)
                        if closed_pos:
                            entry = closed_pos.get('entry_price', current_price)
                            pnl = (current_price - entry) if pos_direction == 'buy' else (entry - current_price)
                            logger.info(f"止损止盈盈亏: {pnl:.2f}")
                            risk_manager.record_trade_result(pnl)
                        state['open_positions'] = [p for p in state['open_positions'] if p.get('direction') != pos_direction]
            save_state(state)
            logger.info("止损止盈平仓完成，退出本轮")
            return 0
        
        # 5. ML 预测
        logger.info("ML 预测...")
        ml_predictor = MLPredictor()
        ml_signal = ml_predictor.predict(kline_data)
        
        if ml_signal is None:
            logger.info("ML 预测无信号，退出")
            return 0
        
        logger.info(f"预测: signal={ml_signal.get('signal')}, 置信度={ml_signal.get('confidence', 0):.2f}, 预测收益={ml_signal.get('prediction', 0):.4f}")
        
        # 5.5 置信度过滤（仅拦截开仓，不拦截平仓）
        confidence = ml_signal.get('confidence', 0)
        has_position = len(state.get('open_positions', [])) > 0
        if confidence < 0.40 and not has_position:
            logger.info(f"置信度 {confidence:.2f} < 0.45 且无持仓，跳过本轮")
            return 0
        
        # 6. 信号处理（平仓方式1和3）
        logger.info("信号处理...")
        trade_intents = signal_processor.process_signal(ml_signal, position_manager)
        
        if not trade_intents:
            logger.info("无交易意图，退出")
            return 0
        
        logger.info(f"生成 {len(trade_intents)} 个交易意图")
        
        # 7. 连接 CTP
        logger.info("连接 CTP 交易接口...")
        with ctp_trade_session(config) as trade_api:
            position_manager.sync_from_ctp(trade_api)
            
            # 同步 CTP 持仓到 state
            ctp_long = position_manager.long_volume
            ctp_short = position_manager.short_volume
            state_long = sum(1 for p in state.get('open_positions', []) if p.get('direction') == 'buy')
            state_short = sum(1 for p in state.get('open_positions', []) if p.get('direction') == 'sell')
            if ctp_long != state_long or ctp_short != state_short:
                logger.warning(f"持仓不一致! CTP: 多{ctp_long}/空{ctp_short}, State: 多{state_long}/空{state_short}")
                if ctp_long == 0 and ctp_short == 0 and (state_long > 0 or state_short > 0):
                    last_trade = state.get('last_trade_time')
                    if last_trade:
                        elapsed = (datetime.now() - datetime.fromisoformat(last_trade)).total_seconds()
                        if elapsed < 300:
                            logger.warning(f"上次交易 {elapsed:.0f} 秒前，保留 state 持仓记录等待 CTP 同步")
                        else:
                            state['open_positions'] = []
                            save_state(state)
                            logger.info("CTP 无持仓且持仓记录超过 5 分钟，已清空 state")
                    else:
                        state['open_positions'] = []
                        save_state(state)
                        logger.info("CTP 无持仓，已清空 state")
            
            # 8. 执行交易
            trade_executor = TradeExecutor(config, trade_api)
            tick_size = config.strategy.tick_size
            slippage_ticks = config.strategy.slippage_ticks
            for intent in trade_intents:
                final_intent = risk_manager.check_and_adjust(intent)
                if final_intent is None:
                    logger.warning(f"风控拦截: {intent}")
                    continue
                
                if final_intent.direction == 'buy':
                    limit_price = round(current_price + tick_size * slippage_ticks, 2)
                else:
                    limit_price = round(current_price - tick_size * slippage_ticks, 2)
                logger.info(f"使用限价单: {limit_price}（当前价: {current_price}，方向: {final_intent.direction}）")
                result = trade_executor.execute_order(final_intent, price=limit_price)
                if result:
                    logger.info(f"✅ 交易指令已发送: {final_intent}")
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
                        logger.info(f"记录开仓: 方向={final_intent.direction}, 开仓价={current_price:.2f}, 止损={sl_tp['stop_loss']:.2f}, 止盈={sl_tp['take_profit']:.2f}")
                    elif final_intent.action == 'close':
                        pos_direction = 'buy' if final_intent.direction == 'sell' else 'sell'
                        closed_pos = next((p for p in state['open_positions'] if p.get('direction') == pos_direction), None)
                        if closed_pos:
                            entry = closed_pos.get('entry_price', current_price)
                            pnl = (current_price - entry) if pos_direction == 'buy' else (entry - current_price)
                            logger.info(f"平仓盈亏: {pnl:.2f}（开仓价={entry:.2f}, 当前价={current_price:.2f}）")
                            risk_manager.record_trade_result(pnl)
                        state['open_positions'] = [p for p in state['open_positions'] if p.get('direction') != pos_direction]
                        logger.info(f"清除持仓记录: 持仓方向={pos_direction}")
            
            # 同步 CTP 持仓到 state
            ctp_long = position_manager.long_volume
            ctp_short = position_manager.short_volume
            state_long = sum(1 for p in state.get('open_positions', []) if p.get('direction') == 'buy')
            state_short = sum(1 for p in state.get('open_positions', []) if p.get('direction') == 'sell')
            if ctp_long != state_long or ctp_short != state_short:
                logger.warning(f"持仓不一致! CTP: 多{ctp_long}/空{ctp_short}, State: 多{state_long}/空{state_short}")
                # 以 CTP 真实持仓为准同步 state
                if ctp_long == 0 and ctp_short == 0 and (state_long > 0 or state_short > 0):
                    last_trade = state.get('last_trade_time')
                    if last_trade:
                        elapsed = (datetime.now() - datetime.fromisoformat(last_trade)).total_seconds()
                        if elapsed < 300:
                            logger.warning(f"上次交易 {elapsed:.0f} 秒前，保留 state 持仓记录等待 CTP 同步")
                        else:
                            state['open_positions'] = []
                            save_state(state)
                            logger.info("CTP 无持仓且持仓记录超过 5 分钟，已清空 state")
                    else:
                        state['open_positions'] = []
                        save_state(state)
                        logger.info("CTP 无持仓，已清空 state")
            
            # 8. 执行交易
            trade_executor = TradeExecutor(config, trade_api)
            tick_size = config.strategy.tick_size
            slippage_ticks = config.strategy.slippage_ticks
        
        # 9. 更新状态（无论有无交易都保存，确保 last_kline_time 持久化）
        state['consecutive_losses'] = risk_manager.consecutive_losses
        state['circuit_break_until'] = risk_manager.circuit_break_until.isoformat() if risk_manager.circuit_break_until else None
        if trade_intents:
            state['last_trade_time'] = datetime.now().isoformat()
        save_state(state)
        
        logger.info("=" * 60)
        logger.info("单次策略执行完成")
        logger.info("=" * 60)
        return 0
        
    except Exception as e:
        logger.error(f"执行异常: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
