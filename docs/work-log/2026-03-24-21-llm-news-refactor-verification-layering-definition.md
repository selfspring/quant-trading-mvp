# LLM 新闻链路重构工作日志

## 时间
- 2026-03-24 21:01 GMT+8

## 本轮完成内容
1. architect 完成 verification 分层设计
2. 明确了 `news_verification` 的最小职责：
   - 针对某一条 analysis 结果，在明确锚点与口径下记录价格验证快照与方向判定结果
3. 明确了必须从 `news_analysis` 迁出的 verification 字段：
   - `base_price`
   - `price_change_30m`
   - `price_change_4h`
   - `price_change_1d`
   - `correct_30m`
   - `correct_4h`
   - `correct_1d`
   - `direction_correct`
4. 明确了过渡期兼容策略：
   - 先新表落地
   - 默认写新表
   - 短期双写 legacy verification 字段
5. 明确了高风险下游消费点：
   - `news_vector_store.py`
   - `llm_news_analyzer.py`
   - `backtest_signal_fusion.py`

## 当前关键决策
- `news_verification` 关联对象应为 `analysis_id`，不是 `news_id`
- 默认 verification 口径继续维持 `effective_time`
- 当前最稳兼容策略是短期双写，而不是一步切断 legacy 字段

## 下一步
- backend 最小实施：
  1. 建 `news_verification` 最小表
  2. 改 `verify_news_price_impact.py` 默认写新表
  3. 短期双写 legacy 字段
