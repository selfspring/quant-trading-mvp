# QA 测试用例：P0 补丁轮（secrets + 旁路风险收紧）

## 1. 本轮测试范围
本轮只验证 backend P0 补丁任务：

> 清理 baseline 入口硬编码 secrets，并收紧旧一体化旁路风险

本轮测试目标来自以下输入：
- `docs/LLM_NEWS_PIPELINE_REFACTOR_PLAN.md`
- `docs/refactor-status/llm-news-pipeline-constraints.md`
- `docs/refactor-status/task-card-backend-p0-patch-secrets-and-bypass-risk-llm-news-pipeline.md`
- 上一轮 QA 与工作日志结论

---

## 2. 本轮验收目标
本轮 QA 需要确认：

1. `batch_llm_analysis.py` 中已不再硬编码本轮目标中的 API key / DB password
2. baseline 主入口的 secrets 已改为从现有配置体系安全读取，而不是换位置硬编码
3. `LLMNewsAnalyzer.fetch_and_analyze_latest()` 默认已被 guard 限制，不能再被无感当作事实主链路调用
4. 只有显式环境变量开启时，旧兼容路径才允许旁路调用
5. baseline 唯一主入口结论仍保持为 `batch_llm_analysis.py`
6. 本轮未越界扩展到时间字段治理 / verification 分层 / RAG / backtest / schema 大改
7. backend 汇报与实际文件状态一致

---

## 3. 本轮明确不测
本轮 **不** 验证以下内容：

- 时间字段语义是否已治理
- `news_verification` 是否已建立
- analysis / verification 是否已解耦
- candidate screening 是否已正式重构
- future-label leakage 是否已全量治理
- 全仓库 hardcoded secrets 是否已全部清理
- `LLMNewsAnalyzer` 是否已完成完整架构拆分
- pre-commit / ruff / mypy / DB lint 是否已全部通过

说明：
- 本轮关注的是“baseline 主入口 secrets”与“legacy guard”。
- 若 backend 顺手修了必要的可编译性问题，可以记录，但不应因此扩大验收主题。

---

## 4. 测试用例

### Case 1：baseline 主入口不再硬编码 API key / DB password
**目标**：确认 `scripts/batch_llm_analysis.py` 已移除本轮目标中的明文 secrets。  
**检查方法**：读回 `scripts/batch_llm_analysis.py`。  
**通过标准**：看不到本轮目标中的明文 API key / DB password 硬编码；关键配置改由配置体系读取。  
**失败条件**：只是把 secrets 挪到另一个硬编码常量，或仍保留敏感值在脚本中。

---

### Case 2：secrets 改为从现有配置体系读取
**目标**：确认 secrets 新读取方式是项目现有安全配置路径，而不是临时拼接。  
**检查方法**：
1. 读回 `scripts/batch_llm_analysis.py`
2. 如有必要，读回 `quant.common.config` 相关定义

**通过标准**：
- 使用现有配置模块/配置对象读取 secrets
- API key / DB password 的来源路径可解释
- 读取方式与项目现有配置机制一致

**失败条件**：
- 通过另一个脚本内常量或隐蔽硬编码读取
- 配置来源不清晰

---

### Case 3：`fetch_and_analyze_latest()` 默认被 guard 阻断
**目标**：确认旧一体化入口默认已不可直接执行。  
**检查方法**：
1. 读回 `quant/signal_generator/llm_news_analyzer.py`
2. 按 backend 提供方式执行验证（或等价验证）

**通过标准**：
- 未设置显式旁路环境变量时，调用会被阻断
- 报错/提示能清楚说明：该路径不是 baseline 主链路

**失败条件**：
- 旧方法默认仍可直接运行
- guard 只写注释，没有实际限制

---

### Case 4：只有显式环境变量才允许旧兼容路径放行
**目标**：确认旧路径放行条件是显式的、可追踪的。  
**检查方法**：读回 `llm_news_analyzer.py` 中 guard 逻辑；必要时验证环境变量控制路径。  
**通过标准**：
- 只有设置指定环境变量时才允许继续
- 代码中能清楚看到开关条件
- 放行时有显式 warning 或等价高可见度提示

**失败条件**：
- guard 条件模糊
- 默认放行
- 没有清晰 warning

---

### Case 5：baseline 唯一主入口结论保持不变
**目标**：确认本轮补丁没有动摇上一轮已经收口的 baseline 唯一入口结论。  
**检查方法**：交叉检查：
- `scripts/batch_llm_analysis.py`
- `scripts/run_llm_analysis.py`
- `quant/signal_generator/llm_news_analyzer.py`

**通过标准**：
- `batch_llm_analysis.py` 仍是 baseline 唯一主入口
- `run_llm_analysis.py` 仍是停用旧入口
- `LLMNewsAnalyzer` 仍非 baseline 主链路

**失败条件**：
- 本轮补丁意外恢复了旧路径地位
- 表述重新变模糊

---

### Case 6：本轮未越界扩 scope
**目标**：确认 backend 没有把本轮补丁扩大成其他层面的重构。  
**检查方法**：对照任务卡与实际改动文件/改动内容。  
**通过标准**：
- 改动聚焦在 secrets 与 legacy guard
- 未展开到时间字段、verification、RAG、schema 大改等主题

**失败条件**：
- 出现明显越界的大范围重构

---

### Case 7：backend 汇报与实际文件一致
**目标**：确认 backend 本轮汇报内容真实反映代码现实。  
**检查方法**：逐条对照 backend 汇报与实际文件/命令结果。  
**通过标准**：
- “secrets 改从 config 读取”能在代码中证实
- “legacy guard 默认拒绝执行”能在代码/验证中证实
- 关键结论可被文件与命令支撑

**失败条件**：
- 汇报与文件不符
- 关键结论找不到证据

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
- 让 QA 基于本轮边界验收
- 避免把“下一阶段的大问题”混进当前结论
- 把“条件通过项”真正转化为可执行测试点
