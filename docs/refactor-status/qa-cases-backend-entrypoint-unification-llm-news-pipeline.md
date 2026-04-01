# QA 测试用例：主入口收敛（LLM 新闻链路）

## 1. 本轮测试范围
本轮只验证 backend 第一轮任务：

> 统一 LLM 新闻分析主入口，停用重复入口

本轮测试目标来自以下输入：
- `docs/LLM_NEWS_PIPELINE_REFACTOR_PLAN.md`
- architect 第一轮审计结论
- `docs/refactor-status/llm-news-pipeline-constraints.md`
- `docs/refactor-status/task-card-backend-entrypoint-unification-llm-news-pipeline.md`

---

## 2. 本轮验收目标
本轮 QA 需要确认：

1. `batch_llm_analysis.py` 已被明确为 baseline 唯一分析入口
2. `run_llm_analysis.py` 已不再作为主链路入口执行
3. 代码说明和调用语义不再制造“双入口都可作为主流程”的歧义
4. 本轮实现未越界扩展到 verification / RAG / backtest / schema 大改
5. backend 汇报与实际文件状态一致

---

## 3. 本轮明确不测
本轮 **不** 验证以下内容：

- 时间字段语义是否已彻底修复
- `news_verification` 是否已建立
- analysis / verification 是否已完全解耦
- future-label leakage 是否已治理完成
- candidate screening 是否已完成正式重构
- secrets 是否已全部移除
- 策略收益、RAG 效果、回测结果

说明：
- 以上内容仍重要，但不属于本轮 backend 任务范围。
- 若 QA 发现 backend 擅自改动这些区域，可记录为 scope 风险；但不能因“这些还没做”直接驳回本轮。

---

## 4. 测试用例

### Case 1：baseline 唯一入口声明存在
**目标**：确认 `batch_llm_analysis.py` 已被明确标识为 baseline 唯一主入口。  
**检查方法**：读回 `scripts/batch_llm_analysis.py`。  
**通过标准**：文件头部说明、注释或等价表达中，明确其为 baseline 唯一主入口，并说明旧入口已停用。  
**失败条件**：仍保留模糊表述，使人无法判断它是否为唯一主入口。

---

### Case 2：旧入口被真实停用，而非名义停用
**目标**：确认 `run_llm_analysis.py` 不再执行旧分析逻辑。  
**检查方法**：
1. 读回 `scripts/run_llm_analysis.py`
2. 实际运行 `python scripts/run_llm_analysis.py`

**通过标准**：
- 该脚本不再调用旧分析主链路
- 执行时输出停用/弃用提示
- 明确提示新的唯一入口
- 返回非 0 或等效失败状态，防止被继续当成主流程运行

**失败条件**：
- 仍然能跑旧分析流程
- 只是注释说弃用，但实际代码照常执行
- 没有清晰迁移提示

---

### Case 3：`LLMNewsAnalyzer` 不再被表达为 baseline 主链路
**目标**：确认 `llm_news_analyzer.py` 当前被明确定位为非 baseline 主链路。  
**检查方法**：读回 `quant/signal_generator/llm_news_analyzer.py`，重点检查模块说明和 `fetch_and_analyze_latest()` 的说明。  
**通过标准**：
- 明确写出其非 baseline 主链路地位，或至少清楚声明其为旧路径/兼容路径/底层能力
- 不再暗示它与 `run_llm_analysis.py` 组合是主流程

**失败条件**：
- 仍保留明显“它是默认主入口”的表达
- 没有任何降级说明

---

### Case 4：相关说明不再制造双入口歧义
**目标**：确认本轮改动后的代码说明层面不再让维护者误以为双入口并列。  
**检查方法**：交叉阅读 3 个关键文件：
- `scripts/batch_llm_analysis.py`
- `scripts/run_llm_analysis.py`
- `quant/signal_generator/llm_news_analyzer.py`

**通过标准**：
- 三者表达一致
- 只有一个 baseline 主入口
- 旧入口明确为停用/非主链路

**失败条件**：
- 文件间表述互相矛盾
- 任一文件仍留下“双入口都能当主流程”的暗示

---

### Case 5：本轮未越界扩 scope
**目标**：确认 backend 没有在本轮顺手改到不属于任务范围的核心层面。  
**检查方法**：对照 backend 任务卡与修改文件范围。  
**通过标准**：
- 修改聚焦在入口统一
- 未把任务扩展为 verification / RAG / backtest / schema 大改

**失败条件**：
- 顺手引入本轮未授权的大范围重构
- 修改范围明显超出任务卡

---

### Case 6：backend 汇报与实际文件一致
**目标**：确认 backend 的结果说明与代码现实一致。  
**检查方法**：逐条对照 backend 汇报与关键文件读回结果。  
**通过标准**：
- 汇报中的关键结论都能在文件或执行结果中找到证据

**失败条件**：
- 汇报与实际修改不一致
- 声称停用但文件未体现
- 声称唯一入口但代码说明未体现

---

## 5. QA 输出要求
执行 QA 时，至少输出：

1. 每个 case 的 pass/fail
2. 证据来自哪些文件/命令
3. 最终结论：通过 / 有条件通过 / 驳回
4. 如果驳回，必须指出具体返工项
5. 如果通过，也要明确遗留风险

---

## 6. 备注
本测试用例文档的目标是：
- 让 QA 基于 plan + architect 审计 + backend 任务边界来验收
- 避免 QA 过度自由发挥
- 避免把“未来轮次的问题”混进本轮结论
