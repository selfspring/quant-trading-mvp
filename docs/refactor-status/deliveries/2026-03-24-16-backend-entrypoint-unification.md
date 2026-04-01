# Backend Delivery - 主入口收敛

## 任务名称
- 统一 LLM 新闻分析主入口，停用重复入口

## 任务范围
本轮只处理：
- baseline 唯一主入口收口
- 旧入口停用/隔离
- 消除双入口并列歧义

本轮明确不做：
- verification 设计
- RAG 改造
- backtest / signal fusion
- candidate schema 正式落地
- 全量时间字段重构

---

## 结果摘要
- 已明确 `scripts/batch_llm_analysis.py` 为 baseline 唯一分析入口。
- 已将 `scripts/run_llm_analysis.py` 改为显式停用的旧入口：执行时直接报错并提示迁移到 `batch_llm_analysis.py`。
- 已在 `quant/signal_generator/llm_news_analyzer.py` 中补充定位说明，明确其不再是 baseline 主链路入口。
- 本轮未扩展到 verification / RAG / backtest / schema 重构。

---

## 修改文件

### 1. `scripts/batch_llm_analysis.py`
- 修改内容：
  - 更新文件头部说明，显式声明这是 baseline 唯一主入口
  - 明确 `run_llm_analysis.py` 已停用
  - 明确本轮只处理主入口收口，不扩展到 verification / RAG / 时间语义重构
- 修改目的：
  - 在代码层消除“双入口都可用”的歧义
  - 让 baseline 入口定义落在实际文件中

### 2. `scripts/run_llm_analysis.py`
- 修改内容：
  - 删除原先执行旧分析逻辑的路径
  - 改为显式输出停用提示并返回非 0
  - 提示唯一替代入口：`python scripts/batch_llm_analysis.py [--limit N]`
- 修改目的：
  - 阻断旧入口继续被当成主链路
  - 防止“名义弃用、实际仍可执行”的伪收口

### 3. `quant/signal_generator/llm_news_analyzer.py`
- 修改内容：
  - 增加模块定位说明，明确其当前是历史兼容 / 底层能力，不再代表 baseline 主链路
  - 为 `fetch_and_analyze_latest()` 增加 deprecated 性质说明
- 修改目的：
  - 清理代码层面的主链路语义误导

---

## 与计划对齐
对应：
- `LLM_NEWS_PIPELINE_REFACTOR_PLAN.md` 的 P0：统一主入口，停用 `run_llm_analysis.py`

本轮落实：
- 主入口收口
- 旧入口停用/隔离
- 主链路地位说明统一

---

## 验证过程
- 读回关键文件：
  - `scripts/batch_llm_analysis.py`
  - `scripts/run_llm_analysis.py`
  - `quant/signal_generator/llm_news_analyzer.py`
- 实际执行：
  - `python scripts/run_llm_analysis.py`
  - `python scripts/batch_llm_analysis.py --help`

### 验证结果
- `run_llm_analysis.py`：
  - 不再运行旧分析逻辑
  - 会输出停用提示
  - 返回码为 1
- `batch_llm_analysis.py --help`：
  - 正常显示帮助信息

结论：
- 本轮“主入口收敛”目标已达成

---

## 风险与遗留
- `LLMNewsAnalyzer` 旧一体化逻辑仍保留，尚未拆分
- 外部调度/脚本若仍调用 `run_llm_analysis.py`，现在会失败，需要后续迁移
- `batch_llm_analysis.py` 仍有硬编码 secrets 与旧时间语义问题（已作为后续任务）

---

## git 情况
- 已尝试 `git add` / `git commit`
- commit 未成功
- 原因：仓库 pre-commit 被既有 lint/type/DB linter 问题阻断，不是 git identity 问题

---

## 下一步建议
1. 清理 `batch_llm_analysis.py` 中的硬编码 secrets
2. 收紧 `LLMNewsAnalyzer.fetch_and_analyze_latest()` 的旁路风险
3. 之后再进入时间字段语义治理与 verification 分层
