# Delivery - backend - 最小时间语义落地（analysis 写入三字段 + verification 默认锚点切换）

## 时间
- 2026-03-24 20:27 GMT+8

## 任务卡
- `docs/refactor-status/task-card-backend-time-semantics-minimal-implementation-llm-news-pipeline.md`

## 本轮完成内容
1. 在 `scripts/batch_llm_analysis.py` 的 baseline analysis 写入链路补齐 `published_time / analyzed_at / effective_time`
2. 明确并落实当前默认规则：`effective_time = analyzed_at`
3. 在 `scripts/verify_news_price_impact.py` 中把默认验证锚点切到 `effective_time`
4. 保留显式研究对照口径：`--anchor-time published_time`
5. 在关键代码注释/告警中冻结 `news_analysis.time` 的新依赖，明确其为 legacy ambiguous field

## 修改文件
- `scripts/batch_llm_analysis.py`
- `scripts/verify_news_price_impact.py`
- `quant/signal_generator/llm_news_analyzer.py`

## 三个正式时间字段说明
- `published_time`
  - 来源：`news_filtered.time`
  - 写入位置：`batch_llm_analysis.py -> save_analysis(..., published_time=...)`
  - 语义：新闻发布时间（当前 baseline 通过 news_filtered 继承上游时间）
- `analyzed_at`
  - 来源：LLM 返回后、落库前由脚本生成的 `datetime.utcnow()`
  - 写入位置：`batch_llm_analysis.py -> save_analysis(..., analyzed_at=...)`
  - 语义：本次分析结果完成/写入时间
- `effective_time`
  - 来源：当前最小规则下直接等于 `analyzed_at`
  - 写入位置：`save_analysis()` 内 `effective_time = analyzed_at`
  - 语义：当前真实可进入 verification / 策略口径的默认生效时间

## verification 锚点说明
- 默认锚点：`effective_time`
  - CLI 默认：`--anchor-time effective_time`
  - SQL 取值：`COALESCE(na.effective_time, na.analyzed_at, na.published_time, nr.time)`
- 研究对照锚点：`published_time`
  - CLI 显式：`--anchor-time published_time`
  - SQL 取值：`COALESCE(na.published_time, nr.time)`

## `news_analysis.time` 冻结说明
- baseline 新写入逻辑不再把 `time` 当正式业务时间语义字段设计，而是同步写入三正式字段
- 为兼容历史表结构，`batch_llm_analysis.py` 仍会写 `time = analyzed_at`
- `verify_news_price_impact.py` 的新默认锚点不再使用 `news_analysis.time`
- `quant/signal_generator/llm_news_analyzer.py` 明确增加 legacy 警告，限制后续继续把 `time` 当正式字段扩用

## 验证
- 读回修改后的关键文件
- 运行语法检查：
  - `python -m py_compile scripts/batch_llm_analysis.py scripts/verify_news_price_impact.py quant/signal_generator/llm_news_analyzer.py`
- 如环境允许，建议后续在带数据库配置的环境执行：
  - `python scripts/verify_news_price_impact.py --dry-run`
  - `python scripts/verify_news_price_impact.py --dry-run --anchor-time published_time`

## 风险与遗留
1. 本轮未做全历史数据回填，历史旧记录可能没有三正式字段
2. `news_analysis.time` 仍保留写入，仅用于 legacy 兼容；彻底移除需后续迁移
3. `verify_news_price_impact.py` 仍沿用 analysis 表回写 verification 结果，本轮未展开分层改造

## 结论
- 已按任务卡完成“最小时间语义落地”，未扩展到 verification 分层或大规模下游清理
