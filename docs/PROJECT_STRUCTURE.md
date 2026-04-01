# 项目文件结构说明文档

**项目位置**: `E:\quant-trading-mvp`

---

## 1. 概述

本项目采用模块化目录组织原则，按功能职责清晰分离：

- **核心代码** → `quant/` 目录，按功能模块划分
- **脚本工具** → `scripts/` 目录，存放独立运行的工具脚本
- **文档** → `docs/` 目录，分类存放各类文档
- **资源文件** → `models/`, `logs/`, `temp/` 等目录
- **测试** → `tests/` 目录（待实现）
- **版本归档** → `versions/` 目录

---

## 2. 根目录文件

| 文件 | 说明 |
|------|------|
| `.env` | 环境变量配置（数据库连接、CTP 账号等敏感信息） |
| `.gitignore` | Git 忽略规则 |
| `README.md` | 项目说明文档 |
| `requirements.txt` | Python 依赖包列表 |
| `PRD.md` | 产品需求文档（初版） |
| `PRD-v2.md` | 产品需求文档（v2 版） |
| `PRD-v3.md` | 产品需求文档（v3 版，最新） |
| `架构设计文档.md` | 架构设计文档（v1） |
| `架构设计文档-v2.md` | 架构设计文档（v2） |
| `架构设计文档-v3.md` | 架构设计文档（v3，最新） |

---

## 3. 核心目录

### 3.1 `quant/` — 核心代码

```
quant/
├── common/              # 公共模块
│   ├── config.py        # 配置管理（基于 Pydantic）
│   ├── db_pool.py       # 数据库连接池
│   ├── tq_factory.py    # 天勤 API 工厂（TqApi/TqKq 创建与管理）⭐ 新增
│   └── tracer.py        # 消息追踪
│
├── data_collector/      # 数据采集
│   ├── ctp_market.py    # CTP 行情接口（备用，已加断线重连）
│   ├── ctp_trade.py     # CTP 交易接口（已弃用，保留备用）
│   ├── tq_trade.py      # 天勤交易接口（TqKq 快期模拟盘）⭐ 新增
│   └── backup_data_source.py  # 备用数据源（AkShare）
│
├── signal_generator/    # 信号生成
│   ├── technical_indicators.py  # 技术指标计算
│   ├── technical_signals.py     # 技术分析信号
│   ├── feature_engineer.py      # ML 特征工程（47 个特征）
│   ├── ml_predictor.py          # ML 预测器
│   ├── model_trainer.py         # 模型训练
│   └── signal_fusion.py         # 多信号融合
│
├── risk_executor/       # 风控执行
│   ├── signal_processor.py      # 信号处理器（含三种平仓逻辑）
│   ├── risk_manager.py          # 风控管理器（含止损止盈）
│   ├── position_manager.py      # 持仓管理器
│   ├── trade_executor.py        # 交易执行器（已切换到天勤交易）
│   └── execute_trade.py         # 交易执行入口（已切换到天勤交易）
│
├── monitor/             # 监控告警（待实现）
└── web_server/          # Web 服务（待实现）
```

### 3.2 `scripts/` — 脚本工具

| 脚本 | 说明 |
|------|------|
| `init_db.py` | 初始化数据库表结构 |
| `test_ctp_connection.py` | 测试 CTP 行情连接 |
| `test_ctp_trade.py` | 测试 CTP 交易下单 |
| `test_ml_config.py` | 测试 ML 配置加载 |
| `train_ml_model.py` | 训练 ML 模型（模拟数据） |
| `test_ml_prediction.py` | 测试 ML 预测 |
| `run_single_cycle.py` | 单次策略执行（cron 触发，已切换到天勤交易） |
| `run_tq_collector.py` | 天勤长驻采集进程（替代 CTP 采集，交易时段运行）⭐ |
| `run_ctp_collector.py` | CTP 长驻采集进程（备用，已加断线重连） |
| `emergency_close5.py` | 紧急平仓脚本（限价单，分昨仓/今仓）⭐ 2026-03-18 新增 |
| `train_final_clean.py` | 用真实数据训练模型（47 特征） |
| `tune_hyperparams.py` | LightGBM 超参数调优 |
| `evaluate_model.py` | ML 模型质量评估 |
| `monitor_ml.py` | 实时查看 ML 预测和置信度 |
| `fetch_tq_data.py` | 从天勤获取历史数据 |
| `fetch_akshare_data.py` | 从 AkShare 获取历史数据 |
| `import_to_db.py` | 将历史数据导入数据库 |

### 3.3 `docs/` — 文档

```
docs/
├── CTP_MARKET_GUIDE.md           # CTP 行情接口使用指南
├── CTP_DEPLOYMENT.md             # CTP 部署说明
├── ML_MODULE_GUIDE.md            # ML 模块使用指南
├── PostgreSQL 配置指南.md         # 数据库配置说明
├── CTP_IMPLEMENTATION_SUMMARY.md # CTP 实现总结
├── 项目总结文档.md               # 项目总结
├── 项目进度文档.md               # 项目进度记录
├── PROJECT_STRUCTURE.md          # 项目文件结构说明（本文档）
│
├── reviews/                      # 审查报告
│   ├── COMPREHENSIVE_REVIEW_REPORT.md  # 综合审查报告
│   ├── PM_REVIEW_REPORT.md             # 产品审查报告
│   ├── QA_REVIEW_REPORT.md             # 质量审查报告
│   └── ...
│
└── ml/                           # ML 开发记录
    ├── ml_step1_summary.md       # ML 开发步骤 1 总结
    ├── ml_step2_summary.md       # ML 开发步骤 2 总结
    └── ml_step3a_summary.md      # ML 开发步骤 3a 总结
```

### 3.4 `models/` — 模型文件

存放训练好的机器学习模型文件（LightGBM 格式）。
- `lgbm_model.txt` — 当前生产模型（47 特征，10000 根 30 分钟线训练，regularized 参数）

### 3.5 `data/` — 数据文件

| 文件 | 说明 |
|------|------|
| `tq_au_30m_10000.csv` | 天勤黄金主力合约 30 分钟线（10000 根，2023-12 ~ 2026-03） |
| `tq_au_1m_10000.csv` | 天勤黄金主力合约 1 分钟线（10000 根） |
| `tq_au_daily_5000.csv` | 天勤黄金主力合约日线（5000 根） |
| `au_main_daily.csv` | AkShare 黄金主力合约日线（1499 天） |
| `au2606_daily.csv` | AkShare au2606 合约日线（201 天） |
| `strategy_state.json` | 策略状态持久化（连败计数、持仓信息、止损止盈、开仓价格） |
| `collector.pid` | 采集进程 PID 文件（JSON 格式，防僵尸进程）|

### 3.6 `logs/` — 日志文件

| 文件 | 说明 |
|------|------|
| `strategy_YYYY-MM-DD.log` | 策略执行日志（按天分文件） |
| `collector_YYYY-MM-DD.log` | CTP 采集进程日志（按天分文件） |

### 3.6 `temp/` — 临时文件

存放 CTP 接口生成的临时文件（如 `.con` 文件）。

### 3.7 `tests/` — 测试代码

单元测试和集成测试（待实现）。

### 3.8 `versions/` — 历史版本

存放文档的历史版本备份。

---

## 4. 配置文件

### 4.1 `.env` 环境变量

```bash
# 数据库配置
DB_HOST=localhost
DB_PORT=5432
DB_NAME=quant_trading
DB_USER=your_user
DB_PASSWORD=your_password

# CTP 账号配置（备用）
CTP_BROKER_ID=your_broker_id
CTP_USER_ID=your_user_id
CTP_PASSWORD=your_password
CTP_FRONT_ADDR=tcp://your_front_address

# 天勤账号配置（主用）
CTP__ACCOUNT_ID=your_tq_account_id
```

### 4.2 `requirements.txt` Python 依赖

项目所需的 Python 包依赖列表。

---

## 5. 文档查找指南

| 想了解... | 查看文档 |
|-----------|----------|
| **CTP 接口使用** | [`docs/CTP_MARKET_GUIDE.md`](docs/CTP_MARKET_GUIDE.md) |
| **ML 模块使用** | [`docs/ML_MODULE_GUIDE.md`](docs/ML_MODULE_GUIDE.md) |
| **数据库配置** | [`docs/PostgreSQL 配置指南.md`](docs/PostgreSQL 配置指南.md) |
| **项目审查结果** | [`docs/reviews/COMPREHENSIVE_REVIEW_REPORT.md`](docs/reviews/COMPREHENSIVE_REVIEW_REPORT.md) |
| **产品需求** | [`PRD-v3.md`](PRD-v3.md)（最新版本） |
| **架构设计** | [`架构设计文档-v3.md`](架构设计文档-v3.md)（最新版本） |

---

## 6. 开发指南

### 6.1 添加新功能

1. **代码** → 放在 `quant/` 对应模块目录下
2. **测试脚本** → 放在 `scripts/` 目录下
3. **文档** → 放在 `docs/` 目录下
4. **更新** → 更新 `README.md` 和本文档

### 6.2 运行测试

```bash
# CTP 行情测试
python scripts/test_ctp_connection.py

# CTP 交易测试
python scripts/test_ctp_trade.py

# ML 配置测试
python scripts/test_ml_config.py

# ML 预测测试
python scripts/test_ml_prediction.py

# 训练 ML 模型
python scripts/train_ml_model.py
```

### 6.3 代码规范

- 使用 Python 3.x
- 遵循 PEP 8 代码风格
- 关键函数添加文档字符串
- 配置管理使用 Pydantic

---

## 7. 目录结构总览

```
quant-trading-mvp/
├── .env                          # 环境变量配置
├── .gitignore                    # Git 忽略规则
├── README.md                     # 项目说明
├── requirements.txt              # Python 依赖
├── PRD.md                        # 产品需求文档 v1
├── PRD-v2.md                     # 产品需求文档 v2
├── PRD-v3.md                     # 产品需求文档 v3（最新）
├── 架构设计文档.md                # 架构设计 v1
├── 架构设计文档-v2.md            # 架构设计 v2
├── 架构设计文档-v3.md            # 架构设计 v3（最新）
│
├── quant/                        # 核心代码
│   ├── common/                   # 公共模块（含 tq_factory.py）
│   ├── data_collector/           # 数据采集（含 tq_trade.py）
│   ├── signal_generator/         # 信号生成
│   ├── risk_executor/            # 风控执行（已切换到天勤交易）
│   ├── monitor/                  # 监控告警（待实现）
│   └── web_server/               # Web 服务（待实现）
│
├── scripts/                      # 脚本工具
├── docs/                         # 文档
├── models/                       # 模型文件
├── logs/                         # 日志文件
├── temp/                         # 临时文件
├── tests/                        # 测试代码（待实现）
└── versions/                     # 历史版本
```

---

**文档版本**: 2.0  
**最后更新**: 2026-03-19
