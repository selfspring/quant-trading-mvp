# 架构审查 Part 2 - 技术栈评估

## 设计要求 vs 实际使用

| 组件 | 设计要求 | 实际使用 | 符合度 | 备注 |
|------|---------|---------|--------|------|
| **语言** | Python 3.10+ | Python 3.10+ | ✅ | 符合 |
| **数据库** | TimescaleDB 2.x | PostgreSQL + TimescaleDB | ✅ | 已配置 hypertable |
| **向量DB** | Chroma 0.4+ | chromadb==0.4.22 | ✅ | 已在 requirements.txt |
| **缓存/消息队列** | Redis 7.x | redis==5.0.1 | ✅ | 已配置 |
| **CTP接口** | vnpy-ctp 6.6.9+ | openctp-ctp>=6.7.0 | ⚠️ | **技术选型变更** |
| **ML框架** | LightGBM 4.x | lightgbm==4.3.0 | ⚠️ | 已声明但未实现 |
| **回测框架** | VectorBT 0.26+ | vectorbt==0.26.1 | ⚠️ | 已声明但未实现 |
| **LLM** | Claude Opus 4 | anthropic==0.18.1 | ⚠️ | 已声明但未实现 |
| **前端** | Vue 3 + Vite | - | ❌ | 未实现 |
| **Web框架** | FastAPI | fastapi==0.109.0 | ⚠️ | 已声明但未实现 |
| **进程管理** | Supervisor 4.x | supervisor==4.2.5 | ⚠️ | 已声明但未配置 |

## 技术选型变更

### 1. vnpy-ctp → openctp-ctp
- **原因**：openctp-ctp 是 vnpy-ctp 的开源替代版本，API 兼容
- **影响**：
  - ✅ 代码已适配（`quant/data_collector/ctp_market.py` 使用 `openctp_ctp.mdapi`）
  - ✅ 功能完整（行情订阅、登录、回调处理已实现）
  - ⚠️ PRD 文档未更新（仍标注 vnpy-ctp）
- **建议**：更新 PRD-v3.md 中的技术栈说明，统一为 openctp-ctp

## 实现进度分析

### ✅ 已实现的模块
1. **数据库层**
   - TimescaleDB 表结构完整（14 张表）
   - 包含 hypertable 配置（kline_data, fundamental_data 等）
   - 消息追踪表（message_trace）已创建
   - 连接池配置完善（db_pool.py）

2. **CTP 行情采集**
   - openctp-ctp 集成完成
   - 行情订阅、登录、回调处理已实现
   - 30 分钟 K 线聚合逻辑已实现
   - 消息追踪（trace_id）已集成

3. **配置管理**
   - pydantic-settings 类型安全配置
   - 支持环境变量和 YAML 配置
   - 数据库、Redis、CTP 配置完整

### ⚠️ 已声明但未实现的模块
1. **ML 模型（LightGBM）**
   - requirements.txt 中已声明
   - 代码目录 `quant/signal_generator/` 存在但为空
   - 特征工程、模型训练代码缺失

2. **LLM 新闻解读（Claude）**
   - anthropic SDK 已声明
   - 新闻爬虫代码缺失
   - LLM 调用逻辑缺失
   - Chroma 向量存储未集成

3. **回测框架（VectorBT）**
   - vectorbt 已声明
   - 回测脚本和逻辑缺失

4. **Web 界面**
   - FastAPI 已声明
   - Vue 3 前端代码缺失
   - WebSocket 实时推送未实现

5. **进程管理**
   - Supervisor 已声明
   - supervisord.conf 配置文件缺失
   - 多进程启动脚本缺失

### ❌ 完全缺失的模块
1. **前端代码**（Vue 3 + Vite）
2. **新闻爬虫**（东方财富、新浪财经）
3. **基本面数据采集**（AKShare/TuShare）
4. **技术指标计算**（TA-Lib）
5. **风控模块**（信号过滤、仓位管理）
6. **交易执行模块**（CTP 下单接口）
7. **监控告警**（邮件告警）

## 依赖版本分析

### 核心依赖版本合理性
- ✅ psycopg2-binary==2.9.9（稳定版本）
- ✅ redis==5.0.1（最新稳定版）
- ✅ openctp-ctp>=6.7.0（使用 >= 允许小版本更新）
- ✅ fastapi==0.109.0（2024 年最新版本）
- ⚠️ TA-Lib==0.4.28（需要手动编译，Windows 安装困难）

### 潜在问题
1. **TA-Lib 安装复杂**
   - Windows 需要预编译 wheel 或手动编译
   - 建议提供安装文档或使用 pandas-ta 替代

2. **timescale==0.0.12**
   - 这是 Python 客户端库，不是 TimescaleDB 本身
   - 实际使用的是 psycopg2，timescale 库可能未使用

## 结论

### 符合度评估
- **已实现部分符合度**：85%（数据库、CTP 接口、配置管理）
- **整体项目完成度**：20%（仅完成 Milestone 1 的部分内容）
- **技术栈声明完整度**：95%（requirements.txt 几乎完整）

### 关键发现
1. ✅ **基础架构扎实**：数据库设计完整，消息追踪已实现
2. ⚠️ **技术选型变更未同步**：PRD 文档需更新为 openctp-ctp
3. ⚠️ **依赖已声明但代码缺失**：ML、LLM、回测、Web 模块未实现
4. ❌ **前端完全缺失**：Vue 3 代码和构建配置不存在

### 建议
1. **立即行动**：更新 PRD-v3.md，将 vnpy-ctp 改为 openctp-ctp
2. **优先级调整**：先完成数据采集（新闻、基本面），再做 ML 和 LLM
3. **依赖清理**：移除 timescale==0.0.12（未使用）
4. **文档补充**：添加 TA-Lib Windows 安装指南
5. **进度透明**：在 README.md 中明确标注各模块实现状态

### 风险提示
- 当前进度约为 Milestone 1 的 60%，距离完整 MVP 还有 80% 工作量
- LLM 成本控制机制（缓存、相似度检索）尚未实现，可能导致成本超支
- 多进程架构框架已搭建，但进程间通信（Redis Pub/Sub）未实现
