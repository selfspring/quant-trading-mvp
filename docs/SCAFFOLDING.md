# 工程支架设计

## 概述

工程支架是让 agent 能够可靠、快速工作的基础设施。包括自动化检查、约束强制、反馈循环。

## 1. Linter（代码规则）

### 1.1 通用 Linter（已有）
- **Ruff**: Python 代码风格、导入排序、未使用变量
- **mypy**: 类型检查

### 1.2 自定义 Linter（需要创建）

#### 风控规则 Linter
**文件**: `scripts/lint_risk_rules.py`

检查项：
- [ ] 所有交易指令必须经过 RiskManager.check_and_adjust()
- [ ] 持仓量不超过 config.risk.max_position_ratio
- [ ] 止损止盈价格必须在开仓时设定
- [ ] 连败计数必须持久化到 strategy_state.json

错误信息示例：
```
❌ risk_executor/trade_executor.py:45
   交易指令未经过风控检查
   
   修复方法：
   final_intent = risk_manager.check_and_adjust(intent)
   if final_intent is None:
       logger.warning("风控拦截")
       return False
```

#### 数据库操作 Linter
**文件**: `scripts/lint_db_operations.py` ✅ 已实现

检查项：
- [x] 所有数据库操作必须使用 db_engine/db_connection（不直接 psycopg2.connect）— **已实现**: `quant/common/db.py`
- [x] 禁止硬编码数据库密码 — **DB-002 规则**
- [x] 禁止硬编码连接参数 — **DB-003 规则**
- [x] 禁止直接 import psycopg2 — **DB-004 规则**
- [x] 禁止直接 create_engine — **DB-005 规则**
- [ ] SQL 查询必须使用参数化（防 SQL 注入）
- [ ] 必须有异常处理和日志记录

#### 特征一致性 Linter
**文件**: `scripts/lint_feature_consistency.py`

检查项：
- [ ] FeatureEngineer.generate_features() 输出的列必须与模型训练时一致
- [ ] 不允许在 MLPredictor 中绕过 FeatureEngineer 直接计算特征
- [ ] 训练脚本和预测脚本必须使用相同的 FeatureEngineer

#### 日志规范 Linter
**文件**: `scripts/lint_logging.py`

检查项：
- [ ] 所有模块必须使用 structlog（不用 print）
- [ ] 关键操作必须记录日志（开仓、平仓、风控拦截）
- [ ] 日志必须包含 symbol、timestamp、direction 等关键字段

## 2. 架构约束

### 2.1 分层依赖检查
**文件**: `scripts/check_architecture.py`

规则：
```
data_collector/  → 只能依赖 common/
signal_generator/ → 可依赖 data_collector/, common/
risk_executor/   → 可依赖 signal_generator/, data_collector/, common/
monitor/         → 可依赖所有层
```

禁止：
- ❌ data_collector 依赖 signal_generator
- ❌ signal_generator 依赖 risk_executor
- ❌ 循环依赖

### 2.2 配置集中化
**文件**: `scripts/check_config_usage.py`

检查项：
- [ ] 所有配置必须从 config.py 读取（不硬编码）
- [ ] 不允许直接读 .env（通过 config.py 统一管理）
- [ ] 敏感信息（密码、API key）必须用 SecretStr

## 3. 测试框架

### 3.1 单元测试
**目录**: `tests/unit/`

覆盖：
- FeatureEngineer 特征生成
- SignalProcessor 信号处理
- RiskManager 风控规则
- PositionManager 持仓管理

### 3.2 集成测试
**目录**: `tests/integration/`

覆盖：
- 完整策略流程（K线 → ML → 风控 → 发单）
- 数据库读写
- CTP 连接（mock）

### 3.3 回测测试
**文件**: `tests/backtest/test_strategy.py`

用历史数据验证策略逻辑。

## 4. 文档验证

### 4.1 文档新鲜度检查
**文件**: `scripts/check_doc_freshness.py`

检查项：
- [ ] docs/INDEX.md 中的所有文档都存在
- [ ] 标注为"当前"的文档最后更新时间 < 7 天
- [ ] 代码中引用的文档路径都有效

### 4.2 代码-文档一致性
**文件**: `scripts/check_code_doc_consistency.py`

检查项：
- [ ] ML_MODULE_GUIDE.md 中的特征数量与 FeatureEngineer 一致
- [ ] PROJECT_STRUCTURE.md 中的文件列表与实际目录一致
- [ ] 配置文档与 config.py 的字段一致

## 5. 类型检查

**工具**: mypy

配置文件 `pyproject.toml`:
```toml
[tool.mypy]
python_version = "3.12"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = false  # 全局宽松
check_untyped_defs = true
ignore_missing_imports = true

# 核心模块严格检查
[[tool.mypy.overrides]]
module = "quant.common.*"
disallow_untyped_defs = true

[[tool.mypy.overrides]]
module = "quant.risk_executor.*"
disallow_untyped_defs = true
```

**当前状态**: ⚠️ 部分实现
- [x] pyproject.toml 配置完成
- [ ] quant/common/ 有 64 个类型错误待修复
- [ ] quant/risk_executor/ 未检查

检查项：
- [ ] 所有函数必须有类型注解
- [ ] 返回值类型必须明确
- [ ] 不允许 Any 类型（除非显式标注）

## 6. 格式化

**工具**: Ruff

配置文件 `.ruff.toml`:
```toml
line-length = 120
target-version = "py312"

[lint]
select = ["E", "F", "I", "N", "W"]
ignore = ["E501"]  # 行长度由 formatter 处理
```

自动修复：
```bash
ruff check --fix .
ruff format .
```

## 7. CI/CD 管道

### 7.1 Pre-commit Hook
**文件**: `.pre-commit-config.yaml`

运行：
- Ruff 格式化
- mypy 类型检查
- 自定义 linter

### 7.2 GitHub Actions（可选）
**文件**: `.github/workflows/ci.yml`

触发：每次 push 或 PR

步骤：
1. 运行所有 linter
2. 运行单元测试
3. 运行集成测试
4. 检查文档新鲜度

## 8. 可观测性

### 8.1 结构化日志
**已实现**: 使用 structlog

标准字段：
- timestamp
- level
- event（操作名称）
- symbol
- direction
- price
- volume

### 8.2 指标收集（待实现）
**文件**: `quant/monitor/metrics.py`

指标：
- 策略执行次数
- ML 预测置信度分布
- 风控拦截次数
- 平仓原因分布（止损/止盈/反向信号/ML反转）

### 8.3 追踪链路（待实现）
**工具**: OpenTelemetry

追踪：
- 完整策略执行链路
- 数据库查询耗时
- ML 预测耗时
- CTP 下单耗时

## 实施优先级

### P0（立即实施）
1. 风控规则 Linter
2. 特征一致性 Linter
3. 单元测试框架

### P1（本周）
4. 架构约束检查
5. 文档新鲜度检查
6. Pre-commit Hook

### P2（下周）
7. 集成测试
8. 类型检查（mypy）
9. 指标收集

### P3（未来）
10. CI/CD 管道
11. 追踪链路

## 使用方式

### 开发时
```bash
# 运行所有检查
python scripts/run_all_checks.py

# 只运行 linter
python scripts/lint_risk_rules.py
python scripts/lint_feature_consistency.py

# 自动修复格式
ruff check --fix .
ruff format .
```

### Agent 工作流
1. Agent 修改代码
2. 自动运行 linter
3. 如果失败，错误信息直接注入 agent 上下文
4. Agent 根据错误信息修复
5. 循环直到通过

---

**维护**: 每次添加新的风控规则或架构约束，同步更新对应的 linter。
