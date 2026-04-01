"""
交易团队协作主控脚本
替代 run_single_cycle.py，使用 agent 团队协作决策

工作流程：
1. Monitor 健康检查
2. Analyst 市场分析
3. Risk-Manager 风控审核
4. Executor 执行交易
5. Monitor 执行后检查
"""
import sys
import os
import json
import logging
from datetime import datetime
from pathlib import Path

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 日志配置
log_dir = Path(__file__).parent.parent / "logs"
log_dir.mkdir(exist_ok=True)
log_file = log_dir / f"team_trading_{datetime.now().strftime('%Y-%m-%d')}.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 工作目录
WORK_DIR = Path(__file__).parent.parent
STATE_FILE = WORK_DIR / "data" / "strategy_state.json"
REPORTS_DIR = WORK_DIR / "data" / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


def call_agent(agent_id: str, task: str, context: dict = None) -> dict:
    """
    调用 agent 执行任务（通过 OpenClaw sessions_spawn）
    
    这里是占位实现，实际需要通过 OpenClaw API 调用
    你需要在 OpenClaw 中运行这个脚本，让它能访问 sessions_spawn
    """
    logger.info(f"调用 {agent_id}: {task}")
    
    # TODO: 实际实现需要调用 OpenClaw sessions_spawn
    # 现在返回模拟结果
    return {
        "agent": agent_id,
        "task": task,
        "status": "pending",
        "message": "需要在 OpenClaw 环境中运行"
    }


def step1_health_check() -> dict:
    """步骤 1: 健康检查"""
    logger.info("=" * 60)
    logger.info("步骤 1: 系统健康检查")
    logger.info("=" * 60)
    
    task = f"""
你是系统监控 agent。请执行健康检查：

1. 检查 state 文件: {STATE_FILE}
2. 运行以下命令同步 CTP 持仓:
   cd {WORK_DIR}
   python -c "from quant.data_collector.ctp_trade import CTPTradeApi; from quant.common.config import config; api = CTPTradeApi(config.ctp.broker_id, config.ctp.account_id, config.ctp.password.get_secret_value(), config.ctp.td_address, config.ctp.app_id, config.ctp.auth_code); api.connect(); print('Long:', api.get_position('long')); print('Short:', api.get_position('short'))"

3. 对比 state 文件中的持仓数量与 CTP 实际持仓
4. 检查是否有异常（持仓不一致、无限开仓迹象）

输出 JSON 格式报告到: {REPORTS_DIR / 'health-check.json'}
格式: {{"status": "ok/warning/error", "issues": [], "ctp_position": {{"long": 0, "short": 0}}, "state_position": {{"long": 0, "short": 0}}}}
"""
    
    result = call_agent("trading-monitor", task)
    
    # 读取报告
    report_file = REPORTS_DIR / "health-check.json"
    if report_file.exists():
        with open(report_file, 'r', encoding='utf-8') as f:
            report = json.load(f)
        logger.info(f"健康检查结果: {report['status']}")
        return report
    else:
        logger.warning("健康检查报告未生成，使用默认值")
        return {"status": "unknown", "issues": ["报告未生成"]}


def step2_market_analysis() -> dict:
    """步骤 2: 市场分析"""
    logger.info("=" * 60)
    logger.info("步骤 2: 市场分析")
    logger.info("=" * 60)
    
    task = f"""
你是市场分析 agent。请执行市场分析：

1. 运行以下命令获取最新 K 线数据:
   cd {WORK_DIR}
   python -c "from scripts.run_single_cycle import get_kline_data; df = get_kline_data(); print(df.tail(10))"

2. 运行 ML 模型预测:
   python -c "from quant.signal_generator.ml_predictor import MLPredictor; from scripts.run_single_cycle import get_kline_data; predictor = MLPredictor(); df = get_kline_data(); result = predictor.predict(df); print(result)"

3. 分析技术指标和预测结果
4. 生成交易建议（buy/sell/hold）

输出 JSON 格式报告到: {REPORTS_DIR / 'analysis-report.json'}
格式: {{"signal": "buy/sell/hold", "confidence": 0.0-1.0, "prediction": 0.0, "current_price": 0.0, "reason": "..."}}
"""
    
    result = call_agent("analyst", task)
    
    # 读取报告
    report_file = REPORTS_DIR / "analysis-report.json"
    if report_file.exists():
        with open(report_file, 'r', encoding='utf-8') as f:
            report = json.load(f)
        logger.info(f"分析结果: signal={report.get('signal')}, confidence={report.get('confidence')}")
        return report
    else:
        logger.warning("分析报告未生成")
        return {"signal": "hold", "confidence": 0.0, "reason": "报告未生成"}


def step3_risk_approval(analysis: dict, health: dict) -> dict:
    """步骤 3: 风控审核"""
    logger.info("=" * 60)
    logger.info("步骤 3: 风控审核")
    logger.info("=" * 60)
    
    task = f"""
你是风险管理 agent。请审核交易计划：

市场分析结果:
{json.dumps(analysis, indent=2, ensure_ascii=False)}

系统健康状态:
{json.dumps(health, indent=2, ensure_ascii=False)}

审核规则:
1. 置信度 < 0.65 → 拒绝
2. 持仓不一致 → 拒绝
3. 当前持仓 >= 3 手 → 拒绝新开仓
4. 连败 >= 3 次 → 拒绝

输出 JSON 格式报告到: {REPORTS_DIR / 'risk-approval.json'}
格式: {{"approved": true/false, "reason": "...", "adjusted_volume": 1, "stop_loss": 0.0, "take_profit": 0.0}}
"""
    
    result = call_agent("risk-manager", task)
    
    # 读取报告
    report_file = REPORTS_DIR / "risk-approval.json"
    if report_file.exists():
        with open(report_file, 'r', encoding='utf-8') as f:
            report = json.load(f)
        logger.info(f"风控审核: approved={report.get('approved')}, reason={report.get('reason')}")
        return report
    else:
        logger.warning("风控报告未生成，默认拒绝")
        return {"approved": False, "reason": "报告未生成"}


def step4_execute_trade(approval: dict, analysis: dict) -> dict:
    """步骤 4: 执行交易"""
    logger.info("=" * 60)
    logger.info("步骤 4: 执行交易")
    logger.info("=" * 60)
    
    if not approval.get("approved"):
        logger.info("风控拒绝，跳过交易")
        return {"status": "skipped", "reason": approval.get("reason")}
    
    task = f"""
你是交易执行 agent。请执行交易指令：

交易信号:
{json.dumps(analysis, indent=2, ensure_ascii=False)}

风控批准:
{json.dumps(approval, indent=2, ensure_ascii=False)}

执行步骤:
1. 连接 CTP 交易接口
2. 提交订单（方向={analysis.get('signal')}, 数量={approval.get('adjusted_volume', 1)}）
3. 等待订单成交
4. 更新 state 文件: {STATE_FILE}

输出 JSON 格式报告到: {REPORTS_DIR / 'execution-result.json'}
格式: {{"status": "success/failed", "order_id": "...", "filled_price": 0.0, "reason": "..."}}
"""
    
    result = call_agent("executor", task)
    
    # 读取报告
    report_file = REPORTS_DIR / "execution-result.json"
    if report_file.exists():
        with open(report_file, 'r', encoding='utf-8') as f:
            report = json.load(f)
        logger.info(f"执行结果: status={report.get('status')}")
        return report
    else:
        logger.warning("执行报告未生成")
        return {"status": "unknown", "reason": "报告未生成"}


def step5_post_check() -> dict:
    """步骤 5: 执行后检查"""
    logger.info("=" * 60)
    logger.info("步骤 5: 执行后检查")
    logger.info("=" * 60)
    
    task = f"""
你是系统监控 agent。请执行执行后检查：

1. 重新同步 CTP 持仓
2. 验证 state 文件是否正确更新
3. 检查是否有异常

输出 JSON 格式报告到: {REPORTS_DIR / 'post-check.json'}
格式: {{"status": "ok/warning/error", "issues": []}}
"""
    
    result = call_agent("trading-monitor", task)
    
    # 读取报告
    report_file = REPORTS_DIR / "post-check.json"
    if report_file.exists():
        with open(report_file, 'r', encoding='utf-8') as f:
            report = json.load(f)
        logger.info(f"执行后检查: {report['status']}")
        return report
    else:
        return {"status": "unknown"}


def main():
    """主流程"""
    logger.info("=" * 60)
    logger.info("交易团队协作流程开始")
    logger.info("=" * 60)
    
    try:
        # 步骤 1: 健康检查
        health = step1_health_check()
        if health.get("status") == "error":
            logger.error(f"健康检查失败: {health.get('issues')}")
            return 1
        
        # 步骤 2: 市场分析
        analysis = step2_market_analysis()
        if analysis.get("signal") == "hold":
            logger.info("无交易信号，结束")
            return 0
        
        # 步骤 3: 风控审核
        approval = step3_risk_approval(analysis, health)
        
        # 步骤 4: 执行交易
        execution = step4_execute_trade(approval, analysis)
        
        # 步骤 5: 执行后检查
        post_check = step5_post_check()
        
        logger.info("=" * 60)
        logger.info("交易团队协作流程完成")
        logger.info("=" * 60)
        return 0
        
    except Exception as e:
        logger.error(f"流程异常: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
