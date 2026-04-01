# 量化交易系统 MVP

基于AI的多元市场量化交易系统，聚焦上期所黄金期货（AU）30分钟K线波段交易。

## 项目状态

🚧 **开发中** - Milestone 1: 基础架构 + 数据采集

## 技术栈

- Python 3.10+
- TimescaleDB 2.x（时序数据）
- Chroma 0.4+（向量数据库）
- Redis 7.x（消息队列）
- vnpy-ctp 6.6.9+（交易接口）
- LightGBM 4.x（机器学习）
- VectorBT 0.26+（回测）
- Claude Opus 4（新闻解读）
- Vue 3 + FastAPI（Web界面）

## 快速开始

### 1. 环境准备

```bash
# 安装 Python 依赖
pip install -r requirements.txt

# 安装 PostgreSQL + TimescaleDB
# Windows: 下载 TimescaleDB 安装包
# macOS: brew install timescaledb
# Linux: apt-get install timescaledb-postgresql-14

# 安装 Redis
# Windows: 下载 Redis for Windows
# macOS: brew install redis
# Linux: apt-get install redis-server
```

### 2. 配置

复制配置文件并修改：

```bash
cp config.example.yaml config.yaml
# 编辑 config.yaml，填入数据库密码、CTP账号等
```

或使用环境变量（推荐）：

```bash
# 创建 .env 文件
DATABASE__PASSWORD=your_db_password
CTP__ACCOUNT_ID=your_ctp_account
CTP__PASSWORD=your_ctp_password
CLAUDE__API_KEY=your_claude_api_key
```

### 3. 初始化数据库

```bash
python scripts/init_db.py
```

### 4. 启动系统

**方式A：本地启动（推荐用于开发）**

```bash
python start_local.py
```

**方式B：Docker 启动**

```bash
docker-compose up -d
```

### 5. 访问 Web 界面

打开浏览器访问：http://localhost:8080

## 项目结构

```
quant-trading-mvp/
├── quant/                      # 主代码目录
│   ├── common/                 # 公共模块
│   │   ├── config.py          # 配置管理
│   │   └── tracer.py          # 消息追踪
│   ├── data_collector/        # 数据采集模块
│   ├── signal_generator/      # 信号生成模块
│   ├── risk_executor/         # 风控+交易执行
│   ├── web_server/            # Web服务
│   └── monitor/               # 监控告警
├── scripts/                   # 脚本
│   └── init_db.py            # 数据库初始化
├── tests/                     # 测试
├── logs/                      # 日志
├── config/                    # 配置文件
├── versions/                  # 文档历史版本
├── requirements.txt           # Python依赖
├── config.example.yaml        # 配置示例
├── PRD-v3.md                 # 产品需求文档
├── 架构设计文档-v3.md         # 架构设计文档
└── README.md                 # 本文件
```

## 开发进度

### Milestone 1: 基础架构 + 数据采集（2周）

**第1周（已完成）**：
- ✅ 环境搭建
- ✅ 数据库表创建（14张表）
- ✅ 配置管理模块
- ✅ 消息追踪模块

**第2周（进行中）**：
- ⏳ CTP 行情接入
- ⏳ 新闻爬虫
- ⏳ 数据质量监控
- ⏳ 基本面数据采集

### Milestone 2: 信号生成 + 回测（2周）
- ⏳ 技术指标计算
- ⏳ 市场状态识别
- ⏳ ML 模型训练
- ⏳ LLM 新闻解读
- ⏳ 信号融合
- ⏳ VectorBT 回测

### Milestone 3: 交易执行 + 监控（2周）
- ⏳ 风控模块
- ⏳ CTP 下单
- ⏳ Web 监控界面
- ⏳ 邮件告警

## 文档

- [产品需求文档 v3.0](PRD-v3.md)
- [架构设计文档 v3.0](架构设计文档-v3.md)
- [数据源调研](数据源调研列表.md)
- [项目总结](项目总结文档.md)

## 关键特性

- ✅ **多进程架构**：5个独立进程，避免GIL瓶颈
- ✅ **消息流追踪**：全链路可观测，trace_id追踪
- ✅ **LLM缓存**：Chroma相似度检索 + Redis缓存，节省60% API成本
- ✅ **动态权重**：根据市场状态自适应调整信号融合权重
- ✅ **数据去重**：基于content_hash避免重复处理
- ✅ **质量监控**：data_quality_log表追踪数据源健康状态
- ✅ **故障降级**：多数据源备份 + 自动切换

## SimNow 服务器地址

### ✅ 第一套环境（仿真环境，与实盘同步）- 已测试可用

适合测试实盘交易策略，交易时段与实盘一致。**推荐使用第一组服务器（已测试连接成功）**。

- **第一组（推荐）**：
  - 交易前置：`tcp://182.254.243.31:30001`
  - 行情前置：`tcp://182.254.243.31:30011` ✅ 已测试可用
- **第二组**：
  - 交易前置：`tcp://182.254.243.31:30002`
  - 行情前置：`tcp://182.254.243.31:30012`
- **第三组**：
  - 交易前置：`tcp://182.254.243.31:30003`
  - 行情前置：`tcp://182.254.243.31:30013`

### ❌ 第二套环境（7x24 环境）- 当前不可用

全天候运行，适合开发和测试。**注意：此环境当前无法连接，请使用第一套环境。**

- 交易前置：`tcp://182.254.243.31:40001` ❌ 无法连接
- 行情前置：`tcp://182.254.243.31:40011` ❌ 无法连接

### 认证信息

- **BrokerID**：`9999`
- **AppID**：`simnow_client_test`
- **AuthCode**：`0000000000000000`（16个0）

### 使用方法

在代码中使用便捷方法创建配置：

```python
from quant.common.config import CTPConfig

# 使用仿真环境（推荐，已测试可用）
config = CTPConfig.simnow_7x24(
    account_id="your_account",
    password="your_password"
)

# 使用交易时段环境（推荐用于实盘前测试）
config = CTPConfig.simnow_trading(
    account_id="your_account",
    password="your_password",
    group=1  # 可选 1, 2, 3，默认第一组
)
```

或通过环境变量配置：

```bash
# .env 文件
CTP__ACCOUNT_ID=your_account
CTP__PASSWORD=your_password
CTP__MD_ADDRESS=tcp://182.254.243.31:30011  # 使用仿真环境端口（已测试可用）
CTP__TD_ADDRESS=tcp://182.254.243.31:30001
```

## 注意事项

1. **CTP账号**：需要自行注册 SimNow 模拟账号（https://www.simnow.com.cn/）
2. **服务器地址**：旧地址（180.168.146.187）已不可用，请使用新地址（182.254.243.31）
3. **Claude API**：需要有效的 API Key
4. **模拟盘先行**：真实交易前必须通过模拟盘验证（至少1个月）
5. **成本控制**：LLM API 建议设置每日调用上限（500次）

## 许可证

MIT License

## 联系方式

如有问题，请提交 Issue。
