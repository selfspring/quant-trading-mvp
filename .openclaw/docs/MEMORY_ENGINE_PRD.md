# 本地双轨记忆系统 (Memory Engine V2) PRD

## 1. 背景与问题
当前 OpenClaw 原生记忆系统基于纯文本和简单的 BM25 匹配，存在以下痛点：
- **缺乏结构化分层**：长篇大论全部塞入上下文，容易撑爆 Token 上限并引发大模型幻觉。
- **孤岛效应**：各子 Agent 之间无法有效共享历史踩坑记录和关键策略。
- **检索效率低**：纯文本无法进行语义相似度搜索和图谱逻辑推理。
- **无一致性保障**：多进程并发写入时容易丢失数据。

## 2. 目标与非目标

### 2.1 目标
- 构建一个 **L0/L1/L2 三层渐进式** 的记忆架构。
- 采用 **SQLite主库 + ChromaDB从库** 的双轨机制，既保证数据事务一致性，又获得强大的 AI 检索生态。
- 实现跨 Agent 的记忆共享，提供标准化的 `store_memory` 和 `recall_memory` 接口。
- 为现有的量化交易项目（`news_embeddings`）提供底层向量存储支持。

### 2.2 非目标
- **不** 依赖任何云端数据库或闭源收费服务，全量数据落盘在本地。
- **暂不** 在第一期实现全自动的“隐形 Hook”（如 beforeTurn/afterTurn），先通过显式工具调用验证流程。
- **不** 用 DuckDB 替代一切，坚持主从分离架构以兼顾安全和生态。

## 3. 核心设计：L0/L1/L2 认知与物理对齐

| 逻辑层级 | 物理存储 | 存储内容 | 作用与时机 |
| :--- | :--- | :--- | :--- |
| **L0 (摘要)** | ChromaDB | ~50 Token的一句话摘要 + 768维Embedding向量 | 用于做毫秒级的模糊语义召回，仅返回 UUID。 |
| **L1 (要点)** | SQLite (主库) | ~500 Token的核心要点 + Graph(节点与边) | 根据 UUID 查出结构化数据，注入 Agent 上下文。 |
| **L2 (原文)** | 硬盘 Markdown | 完整的报错日志、长篇代码、原始对话记录 | 平时静默，仅在 Agent 明确要求深度排查时读取。 |

## 4. 架构方案概述

- **主库（Source of Truth）**：`SQLite`（开启 WAL 模式）
  - 承载所有的并发写入、图谱关系（Nodes/Edges）、L2文件路径。
  - 保证 ACID 事务，解决多 Agent 并发写入造成的死锁或脑裂。
- **从库（Search Index）**：`ChromaDB` (嵌入模式)
  - 仅作为搜索引擎存在，负责提供 HNSW 向量索引能力。
  - 通过异步/队列机制与 SQLite 保持同步。
- **工具封装**：
  - 封装为 OpenClaw 的 `skill`。

## 5. 阶段实施计划 (Phases)

### Phase 1: MVP（最小可用版本）
- 目标：跑通底层双引擎并提供基础 API，证明无并发锁表问题。
- 功能：
  - 初始化 SQLite 表结构（memories, edges, sync_jobs）。
  - 实现 `store_memory`（写 SQLite -> 标为 pending -> 异步查 LLM 生成 embedding -> 写入 Chroma）。
  - 实现 `recall_memory`（Chroma 找 UUID -> SQLite 查 L1）。
- 约束：全手动调用。

### Phase 2: 自动化与跨 Agent 共享
- 目标：将工具暴露给所有子 Agent，并引入工作流自动化。
- 功能：
  - 更新 `task-template.md`，强制 Agent 在任务开始前调用 `recall_memory`。
  - 引入简单的 Hook 脚本，对话结束时自动提取 L0/L1。

### Phase 3: 量化系统并网
- 目标：复用底层 ChromaDB，支撑业务需求。
- 功能：
  - 在 ChromaDB 中开辟 `news_embeddings` Collection，接入量化项目的新闻向量分析流。

---
*Status: Approved*
*Owner: User / Main Agent*