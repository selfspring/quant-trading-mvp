"""
交易执行脚本 - 纯机械执行，不做任何决策
由协调者在 analyst 分析 + risk-manager 审核通过后调用

用法:
  python scripts/execute_trade.py <action> <direction> <volume>
  
  action: open / close
  direction: buy / sell
  volume: 整数（手数）

示例:
  python scripts/execute_trade.py open buy 1      # 开多1手
  python scripts/execute_trade.py close sell 1     # 平多1手
  python scripts/execute_trade.py open sell 1      # 开空1手
  python scripts/execute_trade.py close buy 1      # 平空1手

输出: JSON 格式执行结果
"""
import sys
import os
import json
import logging
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from quant.common.config import config
from quant.data_collector.ctp_trade import CTPTradeApi

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
        # 1. 连接 CTP
        api = CTPTradeApi(
            broker_id=config.ctp.broker_id,
            account_id=config.ctp.account_id,
            password=config.ctp.password.get_secret_value(),
            td_address=config.ctp.td_address,
            app_id=config.ctp.app_id,
            auth_code=config.ctp.auth_code
        )
        api.connect()
        logger.info("CTP 连接成功")

        # 2. 同步持仓（下单前）
        pre_long = api.get_position('long') or 0
        pre_short = api.get_position('short') or 0
        logger.info(f"下单前持仓: 多={pre_long}, 空={pre_short}")

        # 3. 下单
        offset = action  # open / close
        order_ref = api.send_order(
            config.strategy.symbol, direction, offset, volume, 0  # 0=市价
        )
        logger.info(f"订单已提交: ref={order_ref}")
        result["order_ref"] = str(order_ref)

        # 4. 等待成交（简单等待）
        import time
        time.sleep(3)

        # 5. 同步持仓（下单后）
        post_long = api.get_position('long') or 0
        post_short = api.get_position('short') or 0
        logger.info(f"下单后持仓: 多={post_long}, 空={post_short}")

        # 6. 用 CTP 真实持仓更新 state 文件
        state = load_state()
        
        # 重建 open_positions（基于 CTP 真实持仓）
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
        logger.error(f"执行失败: {e}")
        result["status"] = "failed"
        result["error"] = str(e)

    return result


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("用法: python execute_trade.py <action> <direction> <volume>")
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
