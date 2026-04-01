# Backend Delivery - P0 补丁轮（secrets + legacy guard）

## 任务名称
- 清理 baseline 入口硬编码 secrets，并收紧旧一体化旁路风险

## 任务范围
本轮只处理：
- `scripts/batch_llm_analysis.py` 中与本轮直接相关的硬编码 API key / DB password
- `LLMNewsAnalyzer.fetch_and_analyze_latest()` 的 legacy 旁路风险

本轮明确不做：
- 时间字段治理
- verification 分层
- candidate screening 重构
- RAG / backtest / signal fusion 改造
- 全仓库 secrets 大扫除
- `LLMNewsAnalyzer` 整体架构重构

---

## 结果摘要
- 已将 `scripts/batch_llm_analysis.py` 中与本轮直接相关的硬编码 API key / DB password 改为通过现有 `quant.common.config` 配置加载。
- 已收紧 `LLMNewsAnalyzer.fetch_and_analyze_latest()`：默认拒绝执行，只有显式设置环境变量 `LLM_NEWS_ANALYZER_ENABLE_LEGACY_FETCH_AND_ANALYZE=1` 时才允许临时兼容调用，并输出高可见度 warning。
- baseline 唯一主入口结论未变，仍是 `scripts/batch_llm_analysis.py`。
- 本轮未扩展到时间字段治理 / verification 分层 / candidate screening / RAG / backtest。

---

## 修改文件

### 1. `scripts/batch_llm_analysis.py`
- 修改内容：
  - 新增 `from quant.common.config import config`
  - 将 API key、DB host/port/db/user/password 从硬编码改为读取 `config`
  - 清理文件尾部损坏内容，恢复可编译状态
- 修改目的：
  - 去掉本轮直接相关的明文 API key / DB password
  - 保持 baseline 主入口可运行、可验证

### 2. `quant/signal_generator/llm_news_analyzer.py`
- 修改内容：
  - 增加 legacy env guard 常量：`LLM_NEWS_ANALYZER_ENABLE_LEGACY_FETCH_AND_ANALYZE`
  - 将 `fetch_and_analyze_latest()` 改为：默认抛 `RuntimeError`
  - 只有显式环境变量为 `1` 时才放行，并记录 warning
  - 清理文件尾部损坏内容，恢复可编译状态
- 修改目的：
  - 收紧旧一体化路径旁路风险
  - 防止维护者继续把它当作事实主链路

### 3. `tmp_verify_legacy_guard.py`
- 修改内容：
  - 添加最小验证脚本，用于验证旧入口默认会被 guard 拦住
- 修改目的：
  - 做本轮必要验证
- 备注：
  - 属于临时验证文件，不建议长期保留

---

## 与计划对齐
对应：
- `LLM_NEWS_PIPELINE_REFACTOR_PLAN.md` 中 P0 的“移除硬编码密钥/密码”
- 以及前一轮 QA 标出的“旧一体化方法旁路风险”

本轮落实：
- baseline 入口 secrets 清理
- 旧方法旁路风险收紧

---

## secrets 新读取方式
当前 `scripts/batch_llm_analysis.py` 改为通过 `quant.common.config.config` 读取：

- API key：
  - `config.claude.api_key.get_secret_value()`
  - 环境变量：`CLAUDE_API_KEY`
- API base URL：
  - `config.claude.base_url`
  - 环境变量：`CLAUDE_BASE_URL`
- model：
  - `config.claude.model`
  - 环境变量：`CLAUDE_MODEL`
- DB 连接：
  - `config.database.host` → `DB_HOST`
  - `config.database.port` → `DB_PORT`
  - `config.database.database` → `DB_DATABASE`
  - `config.database.user` → `DB_USER`
  - `config.database.password.get_secret_value()` → `DB_PASSWORD`

配置来源：
- 优先仓库根目录 `.env`
- 否则环境变量

---

## 旧方法旁路风险收紧说明
目标方法：
- `LLMNewsAnalyzer.fetch_and_analyze_latest()`

当前保护方式：
1. 默认禁止执行
2. 错误信息明确声明该路径已降级为受保护旧接口
3. 明确 baseline 唯一主入口：`scripts/batch_llm_analysis.py`
4. 仅当显式设置 `LLM_NEWS_ANALYZER_ENABLE_LEGACY_FETCH_AND_ANALYZE=1` 时放行
5. 放行时输出 warning，强调“仅供临时兼容，不得作为 baseline 主链路”

---

## 验证过程
- 读回关键文件：
  - `scripts/batch_llm_analysis.py`
  - `quant/signal_generator/llm_news_analyzer.py`
- 语法编译检查：
  - `python -m py_compile scripts/batch_llm_analysis.py quant/signal_generator/llm_news_analyzer.py`
  - 结果：通过
- guard 验证：
  - `python tmp_verify_legacy_guard.py`
  - 结果：`GUARD_OK`
  - 错误信息明确指出旧接口默认禁止执行，baseline 唯一主入口为 `scripts/batch_llm_analysis.py`

结论：
- 本轮补丁目标已达成

---

## 风险与遗留
- `batch_llm_analysis.py` 现改用 `config.claude.*`，但脚本内部仍保留原有 Provider/协议历史包袱，后续需再理顺
- `LLMNewsAnalyzer` 旧兼容路径仍保留 `save_to_db()` / `verify_price_impact()` 语义，analysis / verification 混层未在本轮治理
- 本轮未做全仓库 secrets 大扫除，仅处理任务卡指定范围
- 时间字段混义、verification 分层、candidate screening、future-label leakage 全量治理仍未处理

---

## git 情况
- 已尝试：
  - `git add scripts/batch_llm_analysis.py quant/signal_generator/llm_news_analyzer.py tmp_verify_legacy_guard.py`
  - `git commit -m "fix(llm-news): remove hardcoded baseline secrets and guard legacy entry"`
- commit 未成功
- 原因：pre-commit 被仓库既有问题阻断，包括：
  - `ruff check`（含 `scripts/run_llm_analysis.py` 既有问题、临时验证脚本 import block）
  - `mypy`（`llm_news_analyzer.py` 的历史类型问题）
  - DB lint advisory

---

## 下一步建议
1. 决定是否删除临时验证文件 `tmp_verify_legacy_guard.py`，或将其转成正式测试
2. 若要争取 commit 成功，可单开一轮做最小 hook 清障
3. 在本轮补丁已完成前提下，下一大项可进入：
   - 时间字段语义治理
   - analysis / verification 分层
