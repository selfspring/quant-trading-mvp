# 量化交易系统 - 共享知识库

## 项目信息
- **项目路径**: `E:\quant-trading-mvp`
- **合约**: au2606 (黄金期货 2026年6月)
- **仿真环境**: SimNow (账户 256693)
- **数据库**: PostgreSQL localhost:5432 / quant_trading

## 系统架构
- **数据层**: CTP 行情采集 → 1分钟K线 → 数据库
- **信号层**: MLPredictor (LightGBM) → 预测未来60分钟收益率
- **风控层**: SignalProcessor + RiskManager + PositionManager
- **执行层**: TradeExecutor → CTP API
- **状态持久化**: `data/strategy_state.json`

## 关键文件
- `scripts/run_single_cycle.py` - 单次策略执行脚本
- `scripts/run_ctp_collector.py` - CTP 数据采集脚本
- `quant/signal_generator/ml_predictor.py` - ML 预测器
- `quant/risk_executor/signal_processor.py` - 信号处理
- `quant/risk_executor/risk_manager.py` - 风控管理
- `quant/risk_executor/position_manager.py` - 持仓管理
- `quant/risk_executor/trade_executor.py` - 交易执行
- `quant/data_collector/ctp_trade.py` - CTP 交易接口
- `quant/data_collector/ctp_market.py` - CTP 行情接口
- `quant/common/config.py` - 配置
- `models/lgbm_model.txt` - LightGBM 模型文件
- `data/strategy_state.json` - 策略状态（持仓、连败等）

## 数据库表
- `kline_data` - K线数据 (symbol, interval, time, open, high, low, close, volume, open_interest)

## 已知 BUG 和踩过的坑
1. **无限开仓 BUG**: risk_manager.check_and_adjust() 没有最大持仓限制，已有多头时收到买入信号直接放行
2. **持仓不同步**: CTP 真实持仓为 0，但 state 文件记录了 34 手。CTP sync 结果没有反馈回 state
3. **置信度过滤失效**: ML 预测置信度 0.36-0.37 远低于阈值 0.65，但策略仍在发单
4. **合约代码大小写**: SimNow 订阅用大写 AU2606，发单用小写 au2606
5. **CTP 回调线程敏感**: 复杂依赖会干扰回调，保持简单
6. **SimNow 限制**: 12:15-13:30 午休不接单；市价单处理有限制

## 风控规则（应遵守）
- 最大持仓: 3 手
- 置信度阈值: 0.65（低于此值不交易）
- 连败 >= 3 次暂停交易
- 反向信号: 先平仓再考虑反向开仓
- 盈亏比: 2:1（止盈 = predicted_return * 1.25, 止损 = predicted_return * 0.5）

## CTP 连接信息
- 行情前置: tcp://182.254.243.31:30011
- 交易前置: tcp://182.254.243.31:30001
- BrokerID/账号/密码: 见 .env 文件和 config

## 交易时段
- 早盘: 09:00-11:30 (10:15-10:30 小休)
- 午盘: 13:30-15:00
- 夜盘: 21:00-次日02:30
- 午休: 12:15-13:30 (不接单)
