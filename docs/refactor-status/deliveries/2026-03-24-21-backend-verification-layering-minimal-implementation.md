# Backend Delivery - 最小 verification 分层实施

## A. 结果摘要
- 已按任务卡完成最小 verification 分层实施，且未扩 scope。
- 已落地 `news_verification` 最小表 schema（同时补到 `scripts/init_db.py` 与运行时 `ensure_verification_schema()`）。
- 已将 `scripts/verify_news_price_impact.py` 的默认写入路径切到 `news_verification`。
- 默认 verification 口径继续保持 `effective_time`；显式研究对照口径继续支持 `published_time`。
- 已保留过渡期短期双写：verification 结果在写入 `news_verification` 的同时，继续回写 `news_analysis` 上的 legacy verification 字段，避免旧下游立即断裂。
- 已完成修改文件读回与语法编译校验。
- 运行级 dry-run 尝试已执行，但被现网/本地数据库 schema 现状挡住：当前 DB 中缺失 `news_analysis.effective_time` 列，导致脚本在查询阶段失败；这属于运行环境未跟上前序时间语义变更，不是本轮代码语法错误。

## B. 修改文件
- `scripts/verify_news_price_impact.py`
  - 修改内容：
    - 新增 `VERIFICATION_VERSION = 'verification_layering_v1'`
    - 新增 `ensure_verification_schema()`：
      - 为 `news_analysis` 补 legacy verification 字段（若不存在）
      - 创建 `news_verification` 最小表、唯一约束、check 约束、索引
    - `process_all_records()` 在非 dry-run 时先确保 schema
    - 默认写入路径改为：先 `INSERT ... ON CONFLICT` 到 `news_verification`
    - 保留过渡期双写：继续 `UPDATE news_analysis` legacy verification 字段
    - 文档字符串更新，明确默认写新表、legacy 仅短期兼容
  - 修改目的：
    - 建立 verification 新真源
    - 保持默认锚点为 `effective_time`
    - 保留 `published_time` 研究对照口径
    - 避免旧消费方立即断裂

- `scripts/init_db.py`
  - 修改内容：
    - 新增 `news_verification` 建表 SQL
    - 新增唯一约束、check 约束、索引
  - 修改目的：
    - 让初始化路径也具备最小 verification 分层落地能力
    - 避免只有脚本运行时动态建表而 init 路径缺失

## C. `news_verification` 最小表说明
- 表名：`news_verification`
- 关键字段：
  - `id SERIAL PRIMARY KEY`
  - `analysis_id INTEGER NOT NULL REFERENCES news_analysis(id) ON DELETE CASCADE`
  - `verification_scope VARCHAR(32) NOT NULL`
  - `verification_anchor_time TIMESTAMPTZ NOT NULL`
  - `symbol VARCHAR(32)`
  - `base_price DECIMAL(18, 6)`
  - `price_change_30m DECIMAL(18, 6)`
  - `price_change_4h DECIMAL(18, 6)`
  - `price_change_1d DECIMAL(18, 6)`
  - `correct_30m INTEGER`
  - `correct_4h INTEGER`
  - `correct_1d INTEGER`
  - `direction_correct INTEGER`
  - `verification_version VARCHAR(64) NOT NULL`
  - `verified_at TIMESTAMPTZ NOT NULL DEFAULT NOW()`
- 关键约束：
  - 关联对象为 `analysis_id`，不是 `news_id`
  - 唯一键：`UNIQUE (analysis_id, verification_scope)`
    - 含义：同一条 analysis 在同一 verification 口径下只保留一条当前真值记录，支持幂等 upsert
  - `verification_scope` check：仅允许 `effective_time` / `published_time`
  - `correct_30m` / `correct_4h` / `correct_1d` / `direction_correct` check：只允许 `0 / 1 / NULL`
- 索引：
  - `idx_news_verification_anchor_time (verification_anchor_time DESC)`
  - `idx_news_verification_verified_at (verified_at DESC)`

## D. 默认 verification 写入路径说明
- 默认入口仍是 `scripts/verify_news_price_impact.py`
- 默认口径仍是 `--anchor-time effective_time`
- 当前默认写入顺序：
  1. 计算锚点时间、symbol、base_price、价格变化、correct 结果
  2. 先写入 `news_verification`（`INSERT ... ON CONFLICT (analysis_id, verification_scope) DO UPDATE`）
  3. 再双写 legacy 字段到 `news_analysis`
- 结论：默认写入路径已切到新表；`news_analysis` 上的 verification 字段仅作为短期兼容副本继续保留

## E. 双写兼容策略说明
- 兼容目标：避免 `news_vector_store.py`、`llm_news_analyzer.py`、`backtest_signal_fusion.py` 等旧下游立刻断裂
- 实现方式：
  - 同一轮 verification 结果先写 `news_verification`
  - 再把 `base_price / price_change_30m / price_change_4h / price_change_1d / correct_30m / correct_4h / correct_1d / direction_correct` 回写到 `news_analysis`
- 策略定位：
  - `news_verification` 是新真源
  - `news_analysis` legacy verification 字段是过渡期兼容副本
- 本轮未做：
  - 不迁移旧下游读取逻辑
  - 不做双读切换治理
  - 不做历史全量回填

## F. 验证过程
- 做了哪些验证：
  1. 读入并对齐 governing doc / status / constraints / work logs / task card
  2. 检查现有 `verify_news_price_impact.py`、`init_db.py`、相关旧下游引用
  3. 修改代码后重新读回关键文件
  4. 运行 `python -m py_compile scripts/verify_news_price_impact.py scripts/init_db.py`
  5. 尝试运行：
     - `python scripts/verify_news_price_impact.py --dry-run --anchor-time effective_time`
     - 因模块导入路径问题，补 `PYTHONPATH`
     - 再次运行 dry-run
- 验证结果：
  - 语法编译：通过
  - 修改文件读回：通过
  - 运行级 dry-run：未完全通过
    - 卡点：数据库当前缺少 `news_analysis.effective_time` 列
    - 报错：`psycopg2.errors.UndefinedColumn: column na.effective_time does not exist`
- 是否通过：
  - 代码改造目标：通过
  - 运行环境验证：受当前数据库 schema 未同步前序时间语义变更影响，未完全通过

## G. 风险与遗留
- 当前 DB schema 很可能尚未执行前序时间语义列补齐；若不先补 `published_time / analyzed_at / effective_time`，本脚本无法在运行环境完成 dry-run / 实跑。
- `news_vector_store.py`、`llm_news_analyzer.py`、`backtest_signal_fusion.py` 仍直接依赖 `news_analysis` legacy verification 字段；本轮靠双写维持兼容，但未治理其读取源。
- `ensure_verification_schema()` 仅在非 dry-run 时执行，因此 dry-run 对“空库/旧库”不会主动补表；这符合 dry-run 不写库原则，但也意味着旧库 dry-run 仍受现状 schema 影响。

## H. 下一步建议
- 先在目标 DB 执行前序时间语义 schema 补齐（至少确保 `news_analysis` 存在 `published_time / analyzed_at / effective_time`）。
- 之后重新执行：
  - `PYTHONPATH=E:\quant-trading-mvp python scripts/verify_news_price_impact.py --dry-run --anchor-time effective_time`
  - 如通过，再做非 dry-run 建表与默认写入验证。
- 下一轮再按计划逐步推动旧下游从 `news_analysis` legacy verification 字段迁移到 `news_verification`，但不应在本轮扩 scope。
