# RALPH_PLAN.md - LLM分析补全与回测验证

## Config
- project: E:\quant-trading-mvp
- max_iterations: 15
- backpressure: none
- retry_limit: 2

## 背景
news_filtered 有 11213 条新闻，news_analysis 只有 151 条（覆盖率 1.4%）。
需要批量跑 LLM 分析，然后重跑价格验证，再做有意义的回测。

## Tasks

- [ ] 1. 批量 LLM 分析：对 news_filtered 中所有未分析的新闻跑 batch_llm_analysis.py
  - AC:
    - news_analysis 表记录数显著增加（目标 > 5000 条）
    - 运行命令：`python scripts/batch_llm_analysis.py`
    - 检查：`SELECT COUNT(*) FROM news_analysis` 结果 > 5000
    - 检查：无大量报错（success rate > 80%）
    - 注意：API 有速率限制，脚本内已有 BATCH_DELAY 和 ITEM_DELAY，不要修改这些参数

- [ ] 2. 重跑价格验证：对所有新分析的新闻填充 price_change
  - AC:
    - 运行：`python scripts/verify_news_price_impact.py`
    - price_change_30m 填充率 > 80%
    - price_change_4h 填充率 > 80%
    - 打印最终 STATISTICS 并汇报

- [ ] 3. 重跑回测并分析结果
  - AC:
    - 运行：`python scripts/backtest_signal_fusion.py`
    - 打印完整回测报告
    - 汇报各时间框架的胜率、盈亏比
    - 指出样本量是否足够（>100条非neutral信号）
    - 给出结论：LLM 信号是否有预测能力
