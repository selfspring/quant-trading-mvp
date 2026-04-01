# 文档索引

> Agent 入口：先看这个文件，按需跳转到具体文档。不要一次性读所有文档。

## ⚠️ 写代码前必读（强制）

**任何涉及 CTP 连接、数据库操作、配置读取、常量定义的代码，动手前必须先读：**

```
quant/common/README.md
```

里面有现成的公共模块。用已有的，不要重新造。违反此规则 = 引入重复代码 = code-artisan 会打回。

## 架构与设计

| 文档 | 用途 | 状态 | 更新时间 |
|------|------|------|----------|
| [../quant/common/README.md](../quant/common/README.md) | **公共模块目录（CTP/DB/常量）— 写代码前必读** | ✅ 当前 | 2026-03-18 |
| [SCAFFOLDING.md](SCAFFOLDING.md) | 工程支架、Linter 规则、约束检查 | ✅ 当前 | 2026-03-18 |
| [CODING_STANDARDS.md](CODING_STANDARDS.md) | 编码规范速查（禁止事项 + 公共模块用法）| ✅ 当前 | 2026-03-18 |
| [DATA_FLOW_ARCHITECTURE.md](DATA_FLOW_ARCHITECTURE.md) | 六层数据流架构、模块实现状态 | ✅ 当前 | 2026-03-16 |
| [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) | 目录结构、文件清单 | ✅ 当前 | 2026-03-19 |
| [SIGNAL_FUSION_IMPLEMENTATION.md](SIGNAL_FUSION_IMPLEMENTATION.md) | 信号融合模块实现细节 | ✅ 当前 | 2026-03-12 |

## ML 模型

| 文档 | 用途 | 状态 | 更新时间 |
|------|------|------|----------|
| [ML_MODULE_GUIDE.md](ML_MODULE_GUIDE.md) | ML 模型参数、47 个特征、平仓逻辑、使用方式 | ✅ 当前 | 2026-03-19 |
| [ml/ml_step1_summary.md](ml/ml_step1_summary.md) | ML 开发步骤 1 总结 | 📦 归档 | 2026-03-11 |
| [ml/ml_step2_summary.md](ml/ml_step2_summary.md) | ML 开发步骤 2 总结 | 📦 归档 | 2026-03-11 |
| [ml/ml_step3a_summary.md](ml/ml_step3a_summary.md) | ML 开发步骤 3a 总结 | 📦 归档 | 2026-03-11 |

## CTP 与数据采集

| 文档 | 用途 | 状态 | 更新时间 |
|------|------|------|----------|
| [SOLUTION_TICK_TO_KLINE.md](SOLUTION_TICK_TO_KLINE.md) | SimNow Tick 问题诊断与解决、天勤全面接入 | ✅ 当前 | 2026-03-19 |
| [CTP_MARKET_GUIDE.md](CTP_MARKET_GUIDE.md) | CTP 行情接口使用指南 | 📦 归档 | 2026-03-11 |
| [CTP_DEPLOYMENT.md](CTP_DEPLOYMENT.md) | CTP 安装部署步骤 | 📦 归档 | 2026-03-09 |
| [CTP_IMPLEMENTATION_SUMMARY.md](CTP_IMPLEMENTATION_SUMMARY.md) | CTP 实现总结 | 📦 归档 | 2026-03-09 |
| [CTP账号配置.md](CTP账号配置.md) | SimNow 账号信息 | ✅ 当前 | 2026-03-10 |
| [MACRO_COLLECTOR.md](MACRO_COLLECTOR.md) | 宏观数据采集说明 | ✅ 当前 | 2026-03-12 |

## 信号与交易

| 文档 | 用途 | 状态 | 更新时间 |
|------|------|------|----------|
| [SIGNAL_DATABASE_STATUS.md](SIGNAL_DATABASE_STATUS.md) | 14 张数据库表状态分析 | ⚠️ 部分过时 | 2026-03-12 |
| [SIGNAL_OUTPUT_ANALYSIS.md](SIGNAL_OUTPUT_ANALYSIS.md) | ML/技术/融合信号输出格式分析 | ⚠️ 部分过时 | 2026-03-12 |

## 数据库

| 文档 | 用途 | 状态 | 更新时间 |
|------|------|------|----------|
| [PostgreSQL配置指南.md](PostgreSQL配置指南.md) | 数据库安装配置 | ✅ 当前 | 2026-03-09 |

## 审查报告

| 文档 | 用途 | 状态 | 更新时间 |
|------|------|------|----------|
| [reviews/COMPREHENSIVE_REVIEW_REPORT.md](reviews/COMPREHENSIVE_REVIEW_REPORT.md) | 综合审查报告 | 📦 归档 | 2026-03-11 |
| [reviews/PM_REVIEW_REPORT.md](reviews/PM_REVIEW_REPORT.md) | 产品审查 | 📦 归档 | 2026-03-11 |
| [reviews/QA_REVIEW_REPORT.md](reviews/QA_REVIEW_REPORT.md) | 质量审查 | 📦 归档 | 2026-03-11 |
| [reviews/ARCHITECTURE_REVIEW_REPORT.md](reviews/ARCHITECTURE_REVIEW_REPORT.md) | 架构审查 | 📦 归档 | 2026-03-11 |
| [reviews/CODE_REVIEW_REPORT.md](reviews/CODE_REVIEW_REPORT.md) | 代码审查 | 📦 归档 | 2026-03-11 |

## 综合

| 文档 | 用途 | 状态 | 更新时间 |
|------|------|------|----------|
| [项目总结文档.md](项目总结文档.md) | 项目整体总结 | ⚠️ 部分过时 | 2026-03-08 |

## 状态说明

- ✅ **当前** — 内容与代码一致，可信赖
- ⚠️ **部分过时** — 核心内容仍有参考价值，但部分细节可能与最新代码不符
- 📦 **归档** — 历史记录，不再维护，仅供追溯

## 根目录关键文档

| 文档 | 用途 |
|------|------|
| `PRD-v3.md` | 产品需求文档（最新版） |
| `架构设计文档-v3.md` | 架构设计文档（最新版） |
| `.env` | 环境变量（CTP 账号、数据库密码） |

---

**维护规则**: 新增或修改文档后，必须同步更新本索引。
