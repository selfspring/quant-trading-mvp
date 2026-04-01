# LLM 新闻链路 P0 执行清单

**日期**: 2026-03-23  
**阶段**: P0（定义统一与主链路收敛）  
**目标**: 先消除双入口、双语义、双时间口径问题，为后续基线实验建立可信基础。

---

## 1. P0 范围边界

## 做什么

P0 只做以下四类工作：

1. **统一主入口**
   - 明确 `scripts/batch_llm_analysis.py` 作为唯一主分析入口
   - 停用 `scripts/run_llm_analysis.py`

2. **统一时间语义**
   - 不再使用含混的 `time` 作为新闻分析主时间字段
   - 明确拆分：
     - `published_time`
     - `analyzed_at`
     - `effective_time`

3. **重构筛选层语义**
   - 不再沿用 `is_gold_related` 作为核心业务语义
   - 将 `filter_news.py` 重构为“候选新闻筛选（candidate screening）”脚本

4. **清除高风险硬编码**
   - 移除代码中的 API Key / 数据库密码硬编码
   - 统一改为 `.env` / config 读取

## 不做什么

P0 明确**不做**以下内容：

1. 不做 RAG 增强
2. 不做向量库 schema 大改
3. 不做 signal fusion 逻辑重构
4. 不做收益回测优化
5. 不做 UI / 监控层调整
6. 不做大规模历史数据重跑（除非 P0 改动要求最小必要回填）

---

## 2. 文件级改动清单

## A. 直接保留并改造

### 1) `scripts/batch_llm_analysis.py`
**动作**: 保留 + 主改造

**原因**:
- 当前最接近批量、可控、可作为主入口的脚本
- 比 `run_llm_analysis.py` 更适合作为后续基线实验入口

**改造要求**:
- 数据来源统一改为候选新闻来源（P0 可先兼容旧表，但语义必须改清）
- 写入 `news_analysis` 时增加：
  - `published_time`
  - `analyzed_at`
  - `effective_time`
- 移除硬编码 API Key / DB_CONFIG
- 增加失败记录与 checkpoint 能力（若改动太大，可先留 TODO，但至少留接口）

---

### 2) `scripts/verify_news_price_impact.py`
**动作**: 保留 + 小改造

**原因**:
- 当前已是相对独立的验证脚本
- 可作为后续 `effective_time` 验证链路的基础

**改造要求**:
- 默认使用 `effective_time` 作为验证锚点
- 明确保留扩展点：未来支持 `published_time` 对照组
- P0 阶段可以暂时继续写回 `news_analysis`，但要在注释/字段命名中明确这是过渡态
- 若数据库 schema 允许，优先新建独立验证表；若 P0 控制范围过紧，则先在文档中写清下一步迁移

---

### 3) `quant/signal_generator/news_vector_store.py`
**动作**: 保留，P0 只做最小兼容修改

**原因**:
- 不是 P0 核心阻断点
- 但必须避免继续依赖混乱字段语义

**改造要求**:
- 如果读取 `news_analysis.time`，改为兼容 `published_time` / `effective_time`
- 不在 P0 推进“把未来价格标签喂回实时分析”的逻辑
- 保持向量存储能力，但不扩大职责

---

## B. 暂停 / 废弃

### 4) `scripts/run_llm_analysis.py`
**动作**: 停用 / 废弃

**原因**:
- 与 `batch_llm_analysis.py` 形成双入口
- 依赖 `llm_news_analyzer.py` 的旧流程
- 会继续制造双口径样本和双时间语义

**处理方式**:
- 保留文件，但在文件头部加入显式废弃说明
- 执行时直接报错并提示改用 `batch_llm_analysis.py`

---

## C. 拆分 / 降权

### 5) `quant/signal_generator/llm_news_analyzer.py`
**动作**: 不再作为主流程入口；降为“旧实现 / 待拆分模块”

**原因**:
- 当前职责过重：
  - prompt 构建
  - 历史检索
  - API 调用
  - DB 保存
  - 价格验证
- 这种“全都管”的写法会继续放大语义混乱

**P0 处理方式**:
- 不要求一次性完全拆分
- 先停止 `run_llm_analysis.py` 对它的主路径依赖
- 标记为后续 P1/P2 拆分对象

---

## D. 需要重写

### 6) `scripts/filter_news.py`
**动作**: 重写

**原因**:
- `is_gold_related` 语义过重且误导
- Guardian 与非 Guardian 采用两套完全不同标准
- 无法作为可信样本筛选层

**P0 新目标**:
- 将此脚本改造成 `candidate screening`
- 输出“候选新闻”而不是“已确认黄金相关新闻”

**最低要求**:
- 不再使用“非 guardian 全部 TRUE”策略
- 对所有来源使用同一层级的候选规则
- 保留筛选原因字段/日志

**可接受的 P0 过渡方案**:
- 若暂时不新建 `news_candidates` 表，则至少：
  - 新建 `is_candidate`
  - 新建 `candidate_reason`
  - 新建 `screened_at`
- 禁止继续使用 `is_gold_related` 作为主业务判断字段

---

## E. 暂不纳入 P0 主改动，但后续必须跟进

### 7) `scripts/store_news_vectors.py`
**动作**: 暂不作为 P0 核心改动

### 8) `scripts/backtest_signal_fusion.py`
**动作**: 暂停研究结论使用，不作为 P0 修复重点

**原因**:
- 在时间语义和样本定义没统一前，回测结果不可信
- P0 不应把精力放在优化回测代码上

---

## 3. 数据表 / 字段变更建议

## 最低必要字段统一（P0）

### news_raw
建议至少确认以下字段语义：
- `id`
- `time` → **实际语义应视为 `published_time`**
- `source`
- `title`
- `content`
- `url`

**P0 要求**:
- 文档和代码中统一把 `news_raw.time` 当作 `published_time`
- 不要再把它称为 generic `time`

---

### news_analysis
当前问题：语义混乱。

**P0 目标字段**:
- `news_id`
- `published_time`
- `analyzed_at`
- `effective_time`
- `importance`
- `direction`
- `timeframe`
- `confidence`
- `reasoning`
- `model_version`

**P0 最低实现策略**:
若当前数据库不方便大改，可先采用以下过渡方案：

1. 新增列：
   - `published_time TIMESTAMP`
   - `analyzed_at TIMESTAMP`
   - `effective_time TIMESTAMP`
2. 历史兼容：
   - 将旧 `time` 视为待废弃字段
3. 新写入逻辑：
   - `published_time = news_raw.time`
   - `analyzed_at = NOW()`
   - `effective_time = analyzed_at`（P0 先这么定，后续可升级为“对齐到下一可交易 bar”）

---

### 候选筛选层（P0 过渡）
优先级从高到低：

#### 方案 A（更好）
新建 `news_candidates` 表：
- `news_id`
- `is_candidate`
- `candidate_reason`
- `candidate_score`
- `screened_at`
- `screening_version`

#### 方案 B（P0 可接受）
在 `news_raw` 上临时新增：
- `is_candidate`
- `candidate_reason`
- `screened_at`

**禁止事项**:
- 不允许继续把 `is_gold_related` 当最终业务真值

---

## 4. 推荐执行顺序

### Step 1. 先停双入口
- 修改 `scripts/run_llm_analysis.py`
- 增加废弃提示，阻止继续使用旧入口

### Step 2. 统一配置读取
- 从 `.env` / config 读取 API Key 和数据库配置
- 修改 `batch_llm_analysis.py`
- 修改 `verify_news_price_impact.py`
- 修改 `filter_news.py`
- 必要时修改 `news_vector_store.py`

### Step 3. 重构 `news_analysis` 时间字段
- 加新列
- 调整 `batch_llm_analysis.py` 的写入逻辑
- 调整 `verify_news_price_impact.py` 的读取逻辑

### Step 4. 重写筛选层
- 重写 `filter_news.py`
- 输出 candidate 语义，而不是 gold_related 真值语义

### Step 5. 做一次最小链路验证
- 跑 candidate screening
- 跑 batch analysis
- 跑 price verification
- 只检查链路是否通、字段是否正确，不看收益率

---

## 5. 风险点与回滚策略

## 风险 1：数据库 schema 改动影响旧脚本
**风险**:
- 旧脚本依赖 `news_analysis.time`

**缓解**:
- P0 先新增列，不立即删旧列
- 代码逐步迁移

**回滚**:
- 保留旧列与旧查询兼容路径
- 新逻辑失败时回退到旧读法（仅临时）

---

## 风险 2：筛选规则一改，样本量骤变
**风险**:
- `filter_news.py` 重写后候选数可能大幅变化

**缓解**:
- P0 先保守筛选
- 输出日志统计（总数、按来源分布、按关键词分布）

**回滚**:
- 保留旧脚本备份
- 候选筛选版本号写入日志/字段

---

## 风险 3：历史数据与新字段不兼容
**风险**:
- 历史 `news_analysis` 记录没有 `published_time/effective_time`

**缓解**:
- 写一次 backfill：`published_time = news_raw.time`
- `analyzed_at` 缺失时可回填旧 `time`
- `effective_time` 缺失时暂取 `analyzed_at`

**回滚**:
- 回填脚本单独执行，可回滚事务

---

## 风险 4：开发过程中又走回旧入口
**风险**:
- 团队成员继续运行 `run_llm_analysis.py`

**缓解**:
- 在文件开头直接报错退出
- 在文档中明确只允许 `batch_llm_analysis.py`

---

## 6. 给 backend agent 的实施说明

你要做的是 **P0 最小可信重构**，不是大重写。

### 必做项
1. 将 `scripts/run_llm_analysis.py` 改为废弃入口，运行即提示使用 `batch_llm_analysis.py`
2. 将 `scripts/batch_llm_analysis.py` 改为唯一主入口
3. 移除代码中的硬编码 API Key / 数据库密码，改为配置读取
4. 为 `news_analysis` 增加并使用：
   - `published_time`
   - `analyzed_at`
   - `effective_time`
5. 修改 `scripts/verify_news_price_impact.py`，默认使用 `effective_time`
6. 重写 `scripts/filter_news.py`，输出 candidate 语义，而不是 gold_related 语义

### 不要做的事
1. 不要引入新的复杂框架
2. 不要顺手重写向量库和回测系统
3. 不要在 P0 阶段加入 RAG 强化
4. 不要删除旧字段，先兼容迁移

### 验收标准
1. 代码中不再有硬编码密钥/数据库密码
2. 运行旧入口会明确失败并提示新入口
3. `news_analysis` 新写入记录含：`published_time / analyzed_at / effective_time`
4. 验证脚本使用 `effective_time`
5. 候选筛选脚本不再使用“非 guardian 全 TRUE”逻辑
6. 完成后提供：
   - 修改文件列表
   - 数据库迁移说明
   - 最小验证步骤
   - 剩余未做项

---

## 7. 结论

P0 的目标不是把系统变“更强”，而是先把系统变“可信”。

在 P0 完成前：
- 不再解读回测收益
- 不再扩大 RAG 方案
- 不再基于当前链路做策略结论

P0 完成后，才进入基线实验阶段。
