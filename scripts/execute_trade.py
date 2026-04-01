"""
交易执行脚本 - 纯机械执行，不做任何决策
由协调者在 analyst 分析 + risk-manager 审核通过后调用

用法:
  python scripts/execute_trade.py <action> <direction> <volume>
  
  action: open / close
  direction: buy / sell
  volume: 整数（手数）

示例:
  python scripts/execute_trade.py open buy 1      # 开多 1 手
  python scripts/execute_trade.py close sell 1     # 平多 1 手
  python scripts/execute_trade.py open sell 1      # 开空 1 手
  python scripts/execute_trade.py close buy 1      # 平空 1 手

输出：JSON 格式执行结果
"""
import sys
import os
import json
import logging
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from quant.common.config import config
from quant.data_collector.tq_trade import TqTradeApi

STATE_FILE = Path(__file__).parent.parent / "data" / "strategy_state.json"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)


def load_state():
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding='utf-8'))
        except:
            pass
    return {"consecutive_losses": 0, "last_trade_time": None, "open_positions": []}


def save_state(state):
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding='utf-8')


def execute(action, direction, volume):
    result = {
        "timestamp": datetime.now().isoformat(),
        "action": action,
        "direction": direction,
        "volume": volume,
        "symbol": config.strategy.symbol,
        "status": "pending"
    }

    try:
        # 1. 连接天勤快期模拟盘
        api = TqTradeApi(
            account_id=config.ctp.account_id,  # 用天勤账号
            password=config.ctp.password.get_secret_value()
        )
        api.connect()
        if not api.login():
            raise Exception("天勤登录失败")
        logger.info("天勤快期模拟盘连接成功")

        # 2. 同步持仓（下单前）
        pos = api.get_position(config.strategy.symbol)
        pre_long = pos.get('long', 0)
        pre_short = pos.get('short', 0)
        logger.info(f"下单前持仓：多={pre_long}, 空={pre_short}")

        # 3. 下单
        # 天勤方向：open/close -> OPEN/CLOSE
        offset = 'OPEN' if action == 'open' else 'CLOSE'
        # 天勤方向：buy/sell -> BUY/SELL
        tq_direction = 'BUY' if direction == 'buy' else 'SELL'
        
        order_ref = api.send_order(
            config.strategy.symbol, tq_direction, offset, volume, 0  # 0= 市价
        )
        logger.info(f"订单已提交：order_ref={order_ref}")
        result["order_ref"] = str(order_ref) if order_ref else None

        # 4. 等待成交（天勤不需要 wait_for_order）
        import time
        time.sleep(5)  # 天勤快期模拟盘持仓同步需要更多时间

        # 5. 同步持仓（下单后）
        pos = api.get_position(config.strategy.symbol)
        post_long = pos.get('long', 0)
        post_short = pos.get('short', 0)
        logger.info(f"下单后持仓：多={post_long}, 空={post_short}")

        # 6. 用天勤真实持仓更新 state 文件
        state = load_state()
        
        # 重建 open_positions（基于天勤真实持仓）
        new_positions = []
        if post_long > 0:
            # 保留已有的多头记录，或创建新的
            existing_longs = [p for p in state.get('open_positions', []) if p.get('direction') == 'buy']
            if existing_longs:
                new_positions.extend(existing_longs[:post_long])
            else:
                for _ in range(post_long):
                    new_positions.append({
                        "direction": "buy",
                        "entry_price": 0,
                        "entry_time": datetime.now().isoformat(),
                        "volume": 1
                    })
        if post_short > 0:
            existing_shorts = [p for p in state.get('open_positions', []) if p.get('direction') == 'sell']
            if existing_shorts:
                new_positions.extend(existing_shorts[:post_short])
            else:
                for _ in range(post_short):
                    new_positions.append({
                        "direction": "sell",
                        "entry_price": 0,
                        "entry_time": datetime.now().isoformat(),
                        "volume": 1
                    })

        state['open_positions'] = new_positions
        state['last_trade_time'] = datetime.now().isoformat()
        save_state(state)

        result["status"] = "success"
        result["pre_position"] = {"long": pre_long, "short": pre_short}
        result["post_position"] = {"long": post_long, "short": post_short}
        result["state_synced"] = True

    except Exception as e:
        logger.error(f"执行失败：{e}")
        result["status"] = "failed"
        result["error"] = str(e)

    return result


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("用法：python execute_trade.py <action> <direction> <volume>")
        print("  action: open/close")
        print("  direction: buy/sell")
        print("  volume: 整数")
        sys.exit(1)

    action = sys.argv[1]
    direction = sys.argv[2]
    volume = int(sys.argv[3])

    if action not in ('open', 'close'):
        print(f"无效 action: {action}")
        sys.exit(1)
    if direction not in ('buy', 'sell'):
        print(f"无效 direction: {direction}")
        sys.exit(1)

    result = execute(action, direction, volume)
    print(json.dumps(result, ensure_ascii=False, indent=2))
