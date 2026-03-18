# 架构审查 Part 1 - 模块结构

## 实际目录结构

```
quant/
├── __init__.py
├── common/
│   ├── config.py
│   ├── db_pool.py
│   ├── tracer.py
│   └── __init__.py
├── data_collector/
│   ├── ctp_market.py
│   └── __init__.py
├── monitor/
├── risk_executor/
├── signal_generator/
└── web_server/
```

## 设计文档要求（架构设计文档-v3.md）

根据文档第三章"系统架构"，要求以下 5 个核心模块：

1. **数据采集模块** (data_collector) - 进程1：CTP行情 + 新闻采集
2. **信号生成模块** (signal_generator) - 进程2：技术指标 + ML + LLM
3. **风控执行模块** (risk_executor) - 进程3：风控 + CTP交易执行
4. **Web服务模块** (web_server) - 进程4：FastAPI 监控界面
5. **监控告警模块** (monitor) - 进程5：邮件告警 + 日志

## 对比分析

| 模块 | 设计要求 | 实际状态 | 评价 |
|------|---------|---------|------|
| common | ✅ 基础设施 | ✅ 已实现 | 良好（config/db_pool/tracer 齐全） |
| data_collector | ✅ P0 核心 | ⚠️ 部分实现 | 仅有 ctp_market.py，缺少新闻采集 |
| signal_generator | ✅ P0 核心 | ❌ 空目录 | 完全缺失 |
| risk_executor | ✅ P0 核心 | ❌ 空目录 | 完全缺失 |
| web_server | ✅ P1 重要 | ❌ 空目录 | 完全缺失 |
| monitor | ✅ P1 重要 | ❌ 空目录 | 完全缺失 |

## 结论

**已实现模块**：1.5 个（common 完整，data_collector 部分）

**缺失模块**：4.5 个
- signal_generator（P0 核心，完全缺失）
- risk_executor（P0 核心，完全缺失）
- web_server（P1 重要，完全缺失）
- monitor（P1 重要，完全缺失）
- data_collector 的新闻采集部分

**目录结构合理性**：✅ 良好
- 模块划分清晰，符合设计文档要求
- common 作为公共基础设施，设计合理
- 各模块独立目录，便于多进程部署

**关键问题**：
1. 4 个核心模块完全空白，项目处于早期阶段
2. data_collector 仅实现行情采集，缺少新闻爬虫
3. 所有 P0 核心功能（信号生成、风控、交易执行）尚未开发

**建议优先级**：
1. 补全 signal_generator（P0）
2. 补全 risk_executor（P0）
3. 补全 data_collector 新闻采集（P0）
4. 补全 web_server（P1）
5. 补全 monitor（P1）
