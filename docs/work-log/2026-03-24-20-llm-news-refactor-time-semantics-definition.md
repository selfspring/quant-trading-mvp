# LLM 新闻链路重构工作日志

## 时间
- 2026-03-24 20:18 GMT+8

## 本轮完成内容
1. architect 完成时间字段语义治理定义
2. 明确了三类正式时间字段：
   - `published_time`
   - `analyzed_at`
   - `effective_time`
3. 明确了 `news_analysis.time` 的定位：
   - legacy ambiguous field
4. 明确了 verification 默认时间锚点：
   - `effective_time`
5. 形成了 backend 最小改造顺序建议

## 关键决策
- 当前默认定义：
  - `effective_time = analyzed_at`
- 不再允许新逻辑继续把 `news_analysis.time` 当正式业务语义字段
- 下一轮 backend 只做最小时间语义落地，不展开 verification 分层

## 下一步
- backend 实现：
  1. analysis 写入链路补 `published_time / analyzed_at / effective_time`
  2. verification 默认锚点切到 `effective_time`
  3. 冻结 `news_analysis.time` 的新依赖
