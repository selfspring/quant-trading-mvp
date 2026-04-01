# LLM 新闻链路重构方案

**日期**: 2026-03-23  
**状态**: 拟执行  
**目的**: 将当前“实验脚本堆叠”的新闻分析流程，重构为**定义清晰、时间语义稳定、验证目标单一**的可信链路。

---

## 一、当前核心结论

当前 LLM 新闻分析相关代码存在的最大问题，不是单点 bug，而是**系统定义不统一**：

1. **样本定义不统一**
   - 有的入口从 `news_raw` 读
   - 有的入口从 `news_filtered` 读
   - `news_filtered` 本身又混合了“Guardian 标题关键词过滤”和“非 Guardian 全放行”两种标准

2. **时间语义不统一**
   - 有的逻辑把 `news_analysis.time` 当新闻发布时间
   - 有的逻辑把它当分析写入时间
   - 回测/验证脚本又在混用 `news_raw.time` 与 `news_analysis.time`

3. **验证目标不统一**
   - 有的脚本在验证“方向判断是否正确”
   - 有的脚本在验证“加均线过滤后收益是否好看”
   - 有的脚本在做带历史案例提示的分析，但没有明确它是预测系统还是研究辅助系统

**结论**: 当前链路不能直接用来支撑“LLM 新闻策略有效”的结论，必须先重构定义，再讨论优化。

---

## 二、重构目标

重构后的链路必须满足：

1. **单一入口**：同一类任务只保留一套主流程
2. **字段语义明确**：每个时间字段和结果字段有唯一含义
3. **实验可重复**：同样输入可得到同样口径的输出
4. **验证可解释**：知道自己在验证哪一层能力
5. **避免信息泄漏**：不能把未来结果混入实时分析流程

---

## 三、推荐的新链路

```text
news_raw
  -> news_candidates
  -> news_analysis
  -> news_verification
  -> strategy_backtest
```

### 1. news_raw
原始新闻表，只存采集结果。

**职责**:
- 保存新闻原文
- 不做业务判断
- 不做 gold_related 标注

**建议字段**:
- `id`
- `published_time`
- `source`
- `title`
- `content`
- `url`
- `collected_at`
- `source_type`（guardian / reuters / jin10 / twitter ...）

---

### 2. news_candidates
候选新闻表，用于表达“这条新闻是否值得交给 LLM 分析”。

**职责**:
- 只做候选筛选
- 与最终方向判断分离
- 保留筛选原因，便于审计

**建议字段**:
- `news_id`
- `candidate_reason`（keyword / source_rule / manual / model）
- `candidate_score`
- `is_candidate`
- `screened_at`
- `screening_version`

**注意**:
- 不要再用 `is_gold_related` 这种语义过重的字段
- 候选 ≠ 已确认相关，只表示“值得进下一步”

---

### 3. news_analysis
LLM 分析结果表。

**职责**:
- 存 LLM 对候选新闻的方向判断
- 明确区分发布时间、分析时间、可交易时间

**建议字段**:
- `id`
- `news_id`
- `published_time`（冗余存储，便于分析）
- `analyzed_at`（LLM 返回结果的时间）
- `effective_time`（允许进入策略/验证的时间）
- `importance`
- `direction`
- `timeframe`
- `confidence`
- `reasoning`
- `model_version`
- `prompt_version`
- `analysis_mode`（plain / rag / offline_research）

**关键规则**:
- `published_time` = 新闻发布时间
- `analyzed_at` = LLM 完成时间
- `effective_time` = 真实可用于交易/验证的起点时间
- 不允许再把 `time` 一个字段混用所有语义

---

### 4. news_verification
价格验证结果表。

**职责**:
- 单独存价格验证结果
- 不把验证标签直接塞回 analysis 主表，避免语义污染

**建议字段**:
- `analysis_id`
- `verification_anchor_time`（必须明确：通常应为 `effective_time`）
- `symbol`
- `base_price`
- `price_30m`
- `price_4h`
- `price_1d`
- `price_change_30m`
- `price_change_4h`
- `price_change_1d`
- `correct_30m`
- `correct_4h`
- `correct_1d`
- `verification_version`
- `verified_at`

**关键规则**:
- 验证锚点默认使用 `effective_time`，不是 `published_time`
- 若要研究“理想条件下的事件反应”，可额外做 `published_time` 口径，但必须与真实交易口径分开

---

## 四、必须统一的研究问题

### 问题 A：LLM 是否能判断方向？
这是**方向分类任务**。

输入：候选新闻  
输出：`bullish / bearish / neutral`  
验证：`effective_time` 之后的价格变化方向

### 问题 B：LLM 是否能筛出值得交易的新闻？
这是**事件筛选任务**。

输入：全部新闻或候选新闻  
输出：`importance/confidence`  
验证：高 importance/high confidence 的新闻是否带来更大绝对波动或更高方向准确率

### 问题 C：完整策略是否赚钱？
这是**交易策略任务**。

输入：LLM 信号 + 技术/ML 过滤 + 交易规则  
输出：交易记录  
验证：收益、回撤、夏普、胜率

**要求**:
- 三个问题必须分开验证
- 不允许还没把 A、B 搞清楚，就直接拿 C 的回测结果下结论

---

## 五、RAG / 历史案例使用原则

当前 `llm_news_analyzer.py` 会把历史相似新闻注入 prompt。这个设计不是不能用，但必须分模式：

### 模式 1：plain
- 不使用历史案例
- 用于建立纯基线能力

### 模式 2：rag
- 可以使用历史新闻文本、历史 reasoning
- **禁止**把未来真实价格变化、correct 标签直接喂给模型

### 模式 3：offline_research
- 允许给完整历史标签
- 仅用于离线研究，不可用于声称“实时预测能力”

**建议**:
- 第一阶段只保留 `plain`
- 等基线建立后，再增加 `rag`
- 暂停当前“半研究半预测”的混合用法

---

## 六、脚本层面的去留建议

### 保留并改造

#### 1. `scripts/batch_llm_analysis.py`
**定位**: 主入口（保留）

**改造方向**:
- 只从 `news_candidates` 读取待分析新闻
- 写入 `news_analysis`
- 记录 `published_time / analyzed_at / effective_time`
- 删除硬编码密钥和硬编码数据库密码
- 支持 checkpoint / failed queue

#### 2. `scripts/verify_news_price_impact.py`
**定位**: 主验证脚本（保留）

**改造方向**:
- 以 `effective_time` 为默认验证锚点
- 写入 `news_verification`
- 不再把验证结果混进 `news_analysis` 主语义中
- 同时支持 `published_time` 口径，作为研究对照组

#### 3. `quant/signal_generator/news_vector_store.py`
**定位**: 辅助模块（保留）

**改造方向**:
- 只存允许用于检索的字段
- 将“预测增强”和“研究增强”分 collection 或分 metadata 标签

---

### 暂停 / 废弃 / 合并

#### 4. `scripts/run_llm_analysis.py`
**建议**: 废弃

原因：
- 与 `batch_llm_analysis.py` 重复
- 调用路径不同
- 容易继续制造双入口和双口径

#### 5. `quant/signal_generator/llm_news_analyzer.py`
**建议**: 拆分职责，不再直接承担全流程

建议拆成：
- `news_llm_client.py`：只负责 LLM 调用与结果解析
- `news_prompt_builder.py`：只负责 prompt 构建
- `news_analysis_service.py`：负责业务编排

#### 6. `scripts/filter_news.py`
**建议**: 重写，不要继续沿用现有语义

原因：
- `is_gold_related` 语义过重
- “非 guardian 全量放行”假设不可接受
- 现逻辑更适合原型探索，不适合生产/研究基线

---

## 七、最小可信实验路径（推荐执行顺序）

### 阶段 1：建立纯基线
目标：先验证“LLM 对候选新闻判断方向是否有信息量”

执行：
1. 重建 `news_candidates`
2. 统一只走 `batch_llm_analysis.py`
3. `analysis_mode = plain`
4. 验证锚点统一用 `effective_time`
5. 输出方向准确率 / 分 importance 分组统计

**这一阶段不做**:
- RAG
- 均线过滤
- signal fusion
- 收益回测

### 阶段 2：验证筛选价值
目标：高 importance / 高 confidence 是否真的更有信息量

执行：
1. 对不同 confidence 阈值分桶
2. 对不同 importance 分桶
3. 比较方向准确率与绝对价格波动

### 阶段 3：加入 RAG 对照实验
目标：比较 plain vs rag 是否真的提升

要求：
- 同一批样本
- 同一验证口径
- 严禁泄漏未来标签

### 阶段 4：最后才做策略回测
目标：把 LLM 作为一个子信号源接入 signal fusion

要求：
- 只有在阶段 1~3 结论清楚后才进入
- 回测必须使用 `effective_time`
- 明确交易执行规则和滑点假设

---

## 八、需要优先落实的工程任务

### P0（必须先做）
1. 统一主入口，停用 `run_llm_analysis.py`
2. 重命名/重构时间字段，禁止继续使用含混的 `time`
3. 重写 `filter_news.py`，改成 `candidate screening`
4. 从代码中移除硬编码密钥/密码

### P1（紧接着做）
5. 新建 `news_verification` 表
6. 改造验证脚本为双口径（published_time / effective_time）
7. 停止把验证标签回灌到 LLM 实时分析 prompt

### P2（基线跑通后）
8. 重新设计向量库 schema
9. 做 plain vs rag 对照实验
10. 最后再接回 signal fusion / backtest

---

## 九、最终判断

当前系统不适合继续以“修几个小问题”的方式推进。

正确路径是：

**先统一定义 → 再建立基线实验 → 再做增强 → 最后才谈策略收益。**

否则继续修补现有脚本，只会得到更多“看起来能跑”的结果，而不是“值得信”的结果。

---

## 十、建议的下一步行动

建议立刻启动一个小型重构迭代，只做以下三件事：

1. **确定唯一主链路**：`news_raw -> news_candidates -> news_analysis -> news_verification`
2. **停用双入口和双语义字段**
3. **跑第一版纯基线实验（plain, effective_time 口径）**

完成这三步之后，再决定是否继续做 RAG 和 signal fusion。
