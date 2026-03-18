"""
风控规则 Linter
用 AST 分析代码，检查风控相关规则是否被正确遵守。

运行方式: python scripts/lint_risk_rules.py
退出码: 0=通过, 1=失败
"""
import ast
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
ERRORS = []


def add_error(file, line, rule, desc, fix):
    ERRORS.append({
        "file": file,
        "line": line,
        "rule": rule,
        "desc": desc,
        "fix": fix,
    })


# ── Rule 1: run_single_cycle.py 中主交易循环的 execute_order() 前必须有 check_and_adjust() ──

def check_rule1_execute_order_guarded():
    """检查 run_single_cycle.py 中 trade_executor.execute_order() 调用前
    是否有 risk_manager.check_and_adjust() 调用。

    注意：止损止盈块中的 execute_order 由 risk_manager 生成意图，不需要 check_and_adjust。
    只检查主交易循环（遍历 trade_intents 的 for 循环）。
    """
    target = PROJECT_ROOT / "scripts" / "run_single_cycle.py"
    if not target.exists():
        add_error(str(target), 0, "risk-guard",
                  "run_single_cycle.py 不存在",
                  "创建 scripts/run_single_cycle.py")
        return

    source = target.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(target))

    # 找到 main() 函数
    main_func = None
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "main":
            main_func = node
            break

    if main_func is None:
        return

    # 在 main 函数中找到遍历 trade_intents 的 for 循环
    for node in ast.walk(main_func):
        if not isinstance(node, ast.For):
            continue
        # 检查是否是 "for intent in trade_intents"
        iter_node = node.iter
        if isinstance(iter_node, ast.Name) and iter_node.id == "trade_intents":
            _check_for_loop_guarded(node, str(target))


def _check_for_loop_guarded(for_node, filename):
    """在 for 循环体中，检查 execute_order 前是否有 check_and_adjust"""
    body = for_node.body
    execute_lines = set()
    guard_lines = set()

    for stmt in body:
        for child in ast.walk(stmt):
            if isinstance(child, ast.Call) and isinstance(child.func, ast.Attribute):
                if child.func.attr == "execute_order":
                    execute_lines.add(child.lineno)
                if child.func.attr == "check_and_adjust":
                    guard_lines.add(child.lineno)

    if execute_lines and not guard_lines:
        for line in sorted(execute_lines):
            add_error(
                filename, line, "risk-guard",
                "trade_executor.execute_order() 调用前缺少 risk_manager.check_and_adjust()",
                "修复方法:\n"
                "  final_intent = risk_manager.check_and_adjust(intent)\n"
                "  if final_intent is None:\n"
                "      continue\n"
                "  result = trade_executor.execute_order(final_intent)"
            )


# ── Rule 2: signal_processor.py 中 TradeIntent(action='open') 必须有置信度检查 ──

def check_rule2_confidence_check():
    """检查 signal_processor.py 中开仓意图是否有置信度过滤"""
    target = PROJECT_ROOT / "quant" / "risk_executor" / "signal_processor.py"
    if not target.exists():
        add_error(str(target), 0, "confidence-check",
                  "signal_processor.py 不存在",
                  "创建 quant/risk_executor/signal_processor.py")
        return

    source = target.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(target))

    # 查找 process_signal 方法
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "process_signal":
            _check_confidence_in_process_signal(node, str(target))
            return

    add_error(str(target), 0, "confidence-check",
              "未找到 process_signal 方法",
              "在 SignalProcessor 类中实现 process_signal 方法")


def _check_confidence_in_process_signal(func_node, filename):
    """检查 process_signal 中是否有置信度阈值比较"""
    has_threshold_check = False
    for node in ast.walk(func_node):
        if isinstance(node, ast.Attribute) and node.attr == "confidence_threshold":
            has_threshold_check = True
            break

    if not has_threshold_check:
        add_error(filename, func_node.lineno, "confidence-check",
                  "process_signal() 中缺少置信度阈值检查",
                  "修复方法:\n"
                  "  if confidence < self.confidence_threshold:\n"
                  "      return None")


# ── Rule 3: risk_manager.py 中必须存在 check_stop_loss_take_profit 方法 ──

def check_rule3_stop_loss_method():
    """检查 risk_manager.py 中是否存在 check_stop_loss_take_profit 方法"""
    target = PROJECT_ROOT / "quant" / "risk_executor" / "risk_manager.py"
    if not target.exists():
        add_error(str(target), 0, "stop-loss-method",
                  "risk_manager.py 不存在",
                  "创建 quant/risk_executor/risk_manager.py")
        return

    source = target.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(target))

    found = False
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "check_stop_loss_take_profit":
            found = True
            break

    if not found:
        add_error(str(target), 0, "stop-loss-method",
                  "RiskManager 缺少 check_stop_loss_take_profit 方法",
                  "修复方法:\n"
                  "  def check_stop_loss_take_profit(self, current_price, open_positions):\n"
                  "      # 遍历持仓，检查是否触发止损/止盈\n"
                  "      ...")


# ── Rule 4: strategy_state.json schema 必须包含 consecutive_losses, open_positions ──

def check_rule4_state_schema():
    """检查 strategy_state.json 的 schema"""
    state_file = PROJECT_ROOT / "data" / "strategy_state.json"
    if not state_file.exists():
        # 检查 load_state 默认值是否包含必要字段
        target = PROJECT_ROOT / "scripts" / "run_single_cycle.py"
        if not target.exists():
            return
        source = target.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(target))

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "load_state":
                return_nodes = [n for n in ast.walk(node) if isinstance(n, ast.Return)]
                for ret in return_nodes:
                    if isinstance(ret.value, ast.Dict):
                        keys = []
                        for k in ret.value.keys:
                            if isinstance(k, ast.Constant):
                                keys.append(k.value)
                        required = {"consecutive_losses", "open_positions"}
                        missing = required - set(keys)
                        if missing:
                            add_error(str(target), ret.lineno, "state-schema",
                                      f"load_state 默认值缺少字段: {missing}",
                                      "修复方法:\n"
                                      '  return {"consecutive_losses": 0, "last_trade_time": None, "open_positions": []}')
        return

    # 如果文件存在，检查实际内容
    try:
        with open(state_file, "r", encoding="utf-8") as f:
            state = json.load(f)
    except (json.JSONDecodeError, Exception) as e:
        add_error(str(state_file), 0, "state-schema",
                  f"strategy_state.json 解析失败: {e}",
                  "修复方法: 确保文件是合法 JSON")
        return

    required_fields = {"consecutive_losses", "open_positions"}
    missing = required_fields - set(state.keys())
    if missing:
        add_error(str(state_file), 0, "state-schema",
                  f"strategy_state.json 缺少字段: {missing}",
                  "修复方法: 添加缺少的字段到 JSON 文件中\n"
                  '  {"consecutive_losses": 0, "open_positions": []}')


def main():
    print("=" * 60)
    print("风控规则 Linter")
    print("=" * 60)

    check_rule1_execute_order_guarded()
    check_rule2_confidence_check()
    check_rule3_stop_loss_method()
    check_rule4_state_schema()

    if ERRORS:
        print(f"\n发现 {len(ERRORS)} 个问题:\n")
        for err in ERRORS:
            line_info = f":{err['line']}" if err['line'] else ""
            print(f"X [{err['file']}{line_info}] {err['rule']}")
            print(f"  {err['desc']}")
            print(f"  {err['fix']}")
            print()
        sys.exit(1)
    else:
        print("\n[PASS] 所有风控规则检查通过")
        sys.exit(0)


if __name__ == "__main__":
    main()
