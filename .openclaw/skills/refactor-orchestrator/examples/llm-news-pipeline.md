# Example: LLM 新闻链路重构

> 这是 `refactor-orchestrator` 的一个领域实例，展示如何把通用重构编排方法应用到
> `LLM_NEWS_PIPELINE_REFACTOR_PLAN.md` 这类新闻分析链路重构任务上。

## 1. Governing Doc
- `docs/LLM_NEWS_PIPELINE_REFACTOR_PLAN.md`

## 2. 目标链路

```text
news_raw
  -> news_candidates
  -> news_analysis
  -> news_verification
  -> strategy_backtest
```

## 3. 领域约束示例

### 关键语义约束
- `news_raw` 只存原始新闻
- `news_candidates` 只表达候选筛选
- `news_analysis` 只表达 LLM 分析结果
- `news_verification` 只表达价格验证结果
- 不混用 `published_time / analyzed_at / effective_time`

### 一票否决风险
- 未来标签或验证结果回灌到实时分析 prompt
- 含混 `time` 字段承担多重核心语义
- 验证与分析职责混层
- baseline 未建立前直接进入增强/回测结论

### 推荐推进顺序
1. 统一主入口
2. 时间语义去歧义
3. candidate screening 重写
4. verification 独立建模
5. 最后再做增强实验

## 4. 建议检查对象
- `scripts/batch_llm_analysis.py`
- `scripts/run_llm_analysis.py`
- `scripts/filter_news.py`
- `scripts/verify_news_price_impact.py`
- `quant/signal_generator/llm_news_analyzer.py`
- `quant/signal_generator/news_vector_store.py`

## 5. 示例状态文件命名
- `docs/refactor-status/llm-news-pipeline-status.md`

## 6. 说明
本 example 只提供领域映射，不替代 `refactor-orchestrator` 的通用流程规则。
真正执行时：
- 通用流程看 `SKILL.md`
- 通用模板看 `references/`
- 领域细节看本 example
