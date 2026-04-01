"""
验证 TradeExecutor -> CTPTradeApi 全链路集成
使用 Mock td_api 验证：
  1. 强多头信号 -> SignalProcessor -> RiskManager 放行 -> TradeExecutor 发单
  2. 参数映射（direction / offset_flag / instrument_id / volume / price）正确
  3. 反向信号 -> RiskManager 拦截并转为平仓 -> TradeExecutor 发出正确平仓单
"""
import sys
import os
import io
import logging

# 解决 Windows 终端编码问题
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
from unittest.mock import MagicMock, call
from types import SimpleNamespace

# 确保项目根目录在 sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from quant.risk_executor.signal_processor import SignalProcessor, TradeIntent
from quant.risk_executor.risk_manager import RiskManager
from quant.risk_executor.position_manager import PositionManager
from quant.risk_executor.trade_executor import TradeExecutor, Order
from quant.risk_executor.trade_executor import (
    THOST_FTDC_D_Buy,
    THOST_FTDC_D_Sell,
    THOST_FTDC_OF_Open,
    THOST_FTDC_OF_Close,
)

# 配置日志
logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(name)s | %(message)s")
logger = logging.getLogger("verify_trade_flow")


def make_config(**overrides):
    """构造一个轻量级 config 仿真对象"""
    strategy = SimpleNamespace(
        symbol=overrides.get("symbol", "au2606"),
        max_position_ratio=overrides.get("max_position_ratio", 0.7),
    )
    ml = SimpleNamespace(
        confidence_threshold=overrides.get("confidence_threshold", 0.65),
    )
    return SimpleNamespace(strategy=strategy, ml=ml)


def make_mock_td_api():
    """创建 Mock 版的 td_api，模拟 CTPTradeApi"""
    td_api = MagicMock()
    td_api.send_order.return_value = "mock-ref-001"
    return td_api


# ==============================================================
# 测试 1: 强多头信号 → 买入开仓
# ==============================================================
def test_strong_bull_signal_opens_long():
    print("\n" + "=" * 60)
    print("测试 1: 强多头信号 → 买入开仓")
    print("=" * 60)

    config = make_config()
    td_api = make_mock_td_api()

    # 组装流水线
    signal_processor = SignalProcessor(config)
    position_manager = PositionManager()
    risk_manager = RiskManager(position_manager, config)
    executor = TradeExecutor(config, td_api=td_api)

    # 模拟 ML 输出：强多头
    ml_output = {"prediction": 0.03, "confidence": 0.85, "signal": 1}
    intent = signal_processor.process_signal(ml_output)
    assert intent is not None, "信号处理器应该生成交易意图"
    print(f"  信号处理器输出: {intent}")

    # 风控审核
    approved = risk_manager.check_and_adjust(intent)
    assert approved is not None, "风控应放行（无持仓时首次开仓）"
    print(f"  风控审核结果: {approved}")

    # 执行发单
    order = executor.execute_order(approved, price=680.0)
    print(f"  生成订单: {order}")

    # 校验 td_api.send_order 被正确调用
    td_api.send_order.assert_called_once()
    call_kwargs = td_api.send_order.call_args
    actual = call_kwargs.kwargs if call_kwargs.kwargs else dict(zip(
        ['instrument_id', 'direction', 'offset_flag', 'volume', 'price'],
        call_kwargs.args
    ))

    print(f"  send_order 实际参数: {actual}")

    assert actual['instrument_id'] == 'au2606', f"合约代码错误: {actual['instrument_id']}"
    assert actual['direction'] == THOST_FTDC_D_Buy, f"方向错误: {actual['direction']}"
    assert actual['offset_flag'] == THOST_FTDC_OF_Open, f"开平标志��误: {actual['offset_flag']}"
    assert actual['volume'] == 1, f"手数错误: {actual['volume']}"
    assert actual['price'] == 680.0, f"价格错误: {actual['price']}"
    assert order.order_ref == "mock-ref-001", f"OrderRef 错误: {order.order_ref}"

    print("  ✅ 测试 1 通过!")
    return True


# ==============================================================
# 测试 2: 已有多头 + 看空信号 → 平仓
# ==============================================================
def test_bear_signal_with_long_position_closes():
    print("\n" + "=" * 60)
    print("测试 2: 已有多头 + 看空信号 → RiskManager 转为平仓")
    print("=" * 60)

    config = make_config()
    td_api = make_mock_td_api()
    td_api.send_order.return_value = "mock-ref-002"

    signal_processor = SignalProcessor(config)
    position_manager = PositionManager()
    position_manager.update_position('long', 2)  # 假设已有 2 手多头
    risk_manager = RiskManager(position_manager, config)
    executor = TradeExecutor(config, td_api=td_api)

    # 模拟看空信号
    ml_output = {"prediction": -0.02, "confidence": 0.78, "signal": -1}
    intent = signal_processor.process_signal(ml_output)
    assert intent is not None
    print(f"  信号处理器输出: {intent}")
    assert intent.direction == 'sell' and intent.action == 'open'

    # 风控审核 → 拦截开空，转平多
    approved = risk_manager.check_and_adjust(intent)
    assert approved is not None
    assert approved.action == 'close', "风控应将动作改为 close"
    assert approved.direction == 'sell', "方向应保持 sell"
    assert approved.volume == 2, "应平掉全部多头（2手）"
    print(f"  风控调整后: {approved}")

    # 执行
    order = executor.execute_order(approved, price=675.0)
    print(f"  生成订单: {order}")

    actual = td_api.send_order.call_args.kwargs if td_api.send_order.call_args.kwargs else dict(zip(
        ['instrument_id', 'direction', 'offset_flag', 'volume', 'price'],
        td_api.send_order.call_args.args
    ))
    print(f"  send_order 实际参数: {actual}")

    assert actual['direction'] == THOST_FTDC_D_Sell, "方向应为卖"
    assert actual['offset_flag'] == THOST_FTDC_OF_Close, "应为平仓"
    assert actual['volume'] == 2, "应平 2 手"

    print("  ✅ 测试 2 通过!")
    return True


# ==============================================================
# 测试 3: 低置信度信号 → 不交易
# ==============================================================
def test_low_confidence_signal_rejected():
    print("\n" + "=" * 60)
    print("测试 3: 低置信度信号 → 不交易")
    print("=" * 60)

    config = make_config(confidence_threshold=0.65)
    td_api = make_mock_td_api()

    signal_processor = SignalProcessor(config)
    position_manager = PositionManager()
    risk_manager = RiskManager(position_manager, config)
    executor = TradeExecutor(config, td_api=td_api)

    ml_output = {"prediction": 0.01, "confidence": 0.50, "signal": 1}
    intent = signal_processor.process_signal(ml_output)
    assert intent is None, "低置信度应被过滤"
    print("  信号处理器: 置信度不足，已过滤")

    approved = risk_manager.check_and_adjust(intent)
    assert approved is None
    print("  风控审核: 无意图，跳过")

    td_api.send_order.assert_not_called()
    print("  send_order 未被调用 ✓")

    print("  ✅ 测试 3 通过!")
    return True


# ==============================================================
# 测试 4: dry-run 模式（无 td_api）
# ==============================================================
def test_dry_run_mode():
    print("\n" + "=" * 60)
    print("测试 4: dry-run 模式（td_api=None）")
    print("=" * 60)

    config = make_config()
    executor = TradeExecutor(config, td_api=None)

    intent = TradeIntent(direction='buy', action='open', confidence=0.9, volume=1)
    order = executor.execute_order(intent, price=680.0)

    assert order is not None, "应该生成订单对象"
    assert order.order_ref is None, "dry-run 不应有 order_ref"
    print(f"  生成订单: {order}")
    print(f"  CTP 参数: {order.to_ctp_params()}")

    print("  ✅ 测试 4 通过!")
    return True


# ==============================================================
# 测试 5: Order.to_ctp_params() 参数名匹配验证
# ==============================================================
def test_order_param_mapping():
    print("\n" + "=" * 60)
    print("测试 5: Order.to_ctp_params() 参数名与 send_order() 签名匹配")
    print("=" * 60)

    order = Order(
        symbol="au2606",
        direction=THOST_FTDC_D_Buy,
        offset_flag=THOST_FTDC_OF_Open,
        volume=3,
        price=688.5,
    )
    params = order.to_ctp_params()
    print(f"  to_ctp_params() = {params}")

    # send_order 签名: instrument_id, direction, offset_flag, volume, price
    expected_keys = {'instrument_id', 'direction', 'offset_flag', 'volume', 'price'}
    actual_keys = set(params.keys())
    assert actual_keys == expected_keys, (
        f"参数名不匹配! 期望 {expected_keys}, 实际 {actual_keys}"
    )
    print(f"  参数名完全匹配: {expected_keys}")

    # 值校验
    assert params['instrument_id'] == 'au2606'
    assert params['direction'] == THOST_FTDC_D_Buy
    assert params['offset_flag'] == THOST_FTDC_OF_Open
    assert params['volume'] == 3
    assert params['price'] == 688.5

    print("  ✅ 测试 5 通过!")
    return True


# ==============================================================
# 主入口
# ==============================================================
def main():
    print("=" * 60)
    print("TradeExecutor <-> CTPTradeApi 集成验证")
    print("=" * 60)

    results = []
    tests = [
        test_strong_bull_signal_opens_long,
        test_bear_signal_with_long_position_closes,
        test_low_confidence_signal_rejected,
        test_dry_run_mode,
        test_order_param_mapping,
    ]

    for test_fn in tests:
        try:
            passed = test_fn()
            results.append((test_fn.__name__, passed))
        except Exception as e:
            logger.error(f"测试 {test_fn.__name__} 异常: {e}", exc_info=True)
            results.append((test_fn.__name__, False))

    # 汇总
    print("\n" + "=" * 60)
    print("测试汇总")
    print("=" * 60)
    all_passed = True
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status}  {name}")
        if not passed:
            all_passed = False

    print()
    if all_passed:
        print("🎉 所有测试通过!")
    else:
        print("⚠️  存在失败的测试")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
