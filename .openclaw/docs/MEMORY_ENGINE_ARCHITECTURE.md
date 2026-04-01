# Memory Engine V2 架构设计文档

## 1. 架构目标
- **零网络依赖**：完全跑在本地（除了调用 LLM 做 Embedding 外）。
- **无并发锁表**：解决多 Agent 架构下多个进程同时写 ChromaDB 导致的 SQLite `database is locked` 报错。
- **防止脑裂**：保证记忆写入的原子性，绝不出现“向量搜到了但找不到原文”或者“图谱关联错乱”的问题。

## 2. 核心架构拓扑

```text
[OpenClaw Agent] ---调用---> [Skill Tool: store_memory / recall_memory]
                                |
                                | (主流程 - 同步)
                                v
                      +-------------------+
                      |   SQLite (主库)    |  <--- 真相源 (Source of Truth)
                      |  - memories表     |  <--- 存 L1 要点与 L2 文件路径
                      |  - memory_edges表 |  <--- 存 图谱关系
                      |  - sync_jobs表    |  <--- 存 待同步的 Chroma 任务
                      +-------------------+
                                |
                                | (异步队列 - 避免长耗时锁死)
                                v
                      +-------------------+
                      |     ChromaDB      |  <--- 搜索引擎 (Search Index)
                      |   (本地嵌入模式)  |  <--- 只存 L0 摘要 与 768维 Embedding
                      +-------------------+
                                | (基于 UUID)
                                v
                      +-------------------+
                      |   Markdown 文件层 |  <--- L2 物理原文层
                      +-------------------+
```

## 3. 组件职责与选型

1. **主库 (SQLite3)**
   - 必须开启 `WAL` 模式（Write-Ahead Logging），支持极高并发读写。
   - 所有数据的写入口，负责分配 UUID，执行 `BEGIN ... COMMIT` 事务。
   - 充当图数据库：通过 SQL CTE 递归查询实现多跳节点关系查询。

2. **从库 (ChromaDB)**
   - 负责接受 Embedding 并在后台维护 HNSW 索引。
   - **绝对不能用它存长文本**，只负责在输入 Query 时，算余弦距离并吐出 Top-K 的 `UUID`。

3. **物理层 (文件系统)**
   - 目录：`~/workspace/data/memory_engine/markdowns/`
   - 文件命名：`{UUID}.md`

## 4. 关键数据流 (Data Flow)

### 4.1 写入流程 (`store_memory`)
1. 接收输入内容，为其生成唯一的 `memory_id` (UUID)。
2. 将完整内容写入硬盘，路径为 `markdowns/{memory_id}.md`。
3. 开启 SQLite 事务：
   - `INSERT INTO memories` (写入 L0 摘要, L1 要点, path)。
   - `INSERT INTO memory_edges` (写入与现有节点的关联边)。
   - `INSERT INTO sync_jobs` (插入一条类型为 `EMBEDDING_SYNC` 的任务)。
4. `COMMIT` 事务（毫秒级）。
5. *主流程结束，释放 Agent。*

### 4.2 异步同步流程 (`sync_embeddings`)
1. 后台 Daemon 或 Cron 脚本定期扫 `sync_jobs` 表。
2. 捞出待同步的记录，调用外部 API（如 OpenAI / 智谱 / Ollama）生成 768 维向量。
3. 获取到 Embedding 后，写入 ChromaDB。
4. 将 SQLite 中的 `sync_jobs` 状态标为 `completed`。

### 4.3 召回流程 (`recall_memory`)
1. 拦截用户的 Query，通过模型转为 Vector。
2. 请求 ChromaDB 查找最相似的 Top 3 `memory_id`。
3. 拿这 3 个 ID，去 SQLite 查询 `memories` 获取 L1 文本。
4. 用这 3 个 ID 在 `memory_edges` 做 1 度外扩，附加上下文关联节点。
5. 将组装好的 JSON 注入给 Agent。

## 5. 失败补偿机制
- 如果同步到 ChromaDB 失败（如 API 超时）：保留 `sync_jobs` 的 `pending` 状态，下次重试。
- 如果 ChromaDB 文件损坏：直接清空 Chroma 目录，写一个 `rebuild_index.py` 遍历 SQLite，重新灌入所有 Embedding，这是主从架构最大的优势。
