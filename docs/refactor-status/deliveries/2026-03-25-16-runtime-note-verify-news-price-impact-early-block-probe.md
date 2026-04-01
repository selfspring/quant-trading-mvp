# Runtime Note - verify_news_price_impact early block probe

## 摘要
本轮执行“启动早期阻塞定位探针”，目标是定位 `scripts/verify_news_price_impact.py` 在 dry-run 模式下的首个阻塞阶段。

结论先行：
- **未在启动早期阶段复现阻塞**。
- 题设要求覆盖的 7 个探针点均已到达，且都在单步超时边界内快速完成。
- 因此，当前可证据化的结论是：**首个阻塞阶段不在“模块 import → 配置加载 → DB 连接 → SELECT 1 → news_analysis 最小样本查询 → 进入主循环前”这条启动早期链路内。**
- 若与前序“150 秒无 stdout/stderr”现象同时成立，则更可能是：**阻塞发生在进入主循环之后的逐条处理阶段，且 stdout 在该环境下未及时可见/未被刷新。**

## 战前回忆 / 已遵守的踩坑记录
已先回看并遵守以下已知记录：
- `docs/refactor-status/deliveries/2026-03-25-15-runtime-note-verify-news-price-impact-full-log-capture.md`
  - 已知：此前真实 dry-run 观察 150 秒以上无 stdout/stderr，更像早期阻塞。
  - 已知：PowerShell 不支持 `&&`，需用 PowerShell 语法。
  - 已知：需显式设置 `PYTHONPATH=E:\quant-trading-mvp`。
- `docs/refactor-status/deliveries/2026-03-24-21-backend-verification-layering-minimal-implementation.md`
  - 已知：之前曾记录运行环境缺少 `news_analysis.effective_time` 列。
- 本次实际探针结果显示：当前 DB 中最小样本查询已可成功引用 `na.effective_time`，说明运行环境与此前记录相比已有变化，至少不再卡在该列缺失处。

## 探针策略
为了避免扩大 scope，没有改 `scripts/verify_news_price_impact.py` 业务脚本本体，而是新增了一个**独立临时探针脚本**：
- `scripts/verify_news_price_impact_early_probe.py`

策略特点：
- 每个阶段单独写日志到独立 probe 日志文件
- 每行日志即时 flush + `os.fsync()` 落盘
- DB 查询显式设置 `statement_timeout`
- 只覆盖启动早期链路，不进入逐条业务处理深水区
- 一旦确认首个阻塞阶段不在启动早期，即停止继续深挖

## 实际探针日志文件
- `E:\quant-trading-mvp\logs\verify_news_price_impact_early_probe_20260325-161822.log`

## 临时探针改动
### 修改文件清单
- `E:\quant-trading-mvp\scripts\verify_news_price_impact_early_probe.py`

### 改动目的
- 以最小侵入方式复用 `scripts.verify_news_price_impact` 的配置与连接逻辑
- 对启动早期链路做分阶段、带边界的探针验证
- 避免直接修改业务脚本，防止将“定位阻塞”扩成“顺手大修”

## 探针阶段与结果
本次至少覆盖了任务要求中的 7 个阶段：

1. **模块 import 完成**
   - 阶段名：`import_module_complete`
   - 结果：已到达，成功
   - 耗时：`0.312s`

2. **配置 / 环境加载完成**
   - 阶段名：`config_env_loaded`
   - 结果：已到达，成功
   - 耗时：`0.047s`
   - 额外信息：`host=localhost port=5432 dbname=quant_trading user=postgres`

3. **DB 连接前**
   - 阶段名：`db_connect_before`
   - 结果：已到达，成功
   - 耗时：`0.016s`

4. **DB 连接后**
   - 阶段名：`db_connect_after`
   - 结果：已到达，成功
   - 耗时：`0.203s`

5. **最小查询（SELECT 1）前后**
   - 阶段名：`select_1_before`
   - 结果：已到达，成功
   - 耗时：`0.031s`
   - 阶段名：`select_1_after`
   - 结果：已到达，成功
   - 耗时：`0.047s`
   - 查询结果：`(1,)`

6. **针对 news_analysis 的最小样本查询前后**
   - 阶段名：`news_analysis_sample_before`
   - 结果：已到达，成功
   - 耗时：`0.031s`
   - 阶段名：`news_analysis_sample_after`
   - 结果：已到达，成功
   - 耗时：`0.079s`
   - 查询结果：`row_found=True`

7. **进入主循环前**
   - 阶段名：`before_main_loop`
   - 结果：已到达，成功
   - 耗时：`0.047s`
   - 额外信息：`total_records=869`

附加：
- `db_connection` 关闭成功
- `probe` 结果：`all_requested_probe_points_reached`

## 最后成功阶段 / 首个阻塞阶段
### 最后成功阶段
- **`before_main_loop`**

### 首个阻塞阶段
- **本轮未在启动早期探针范围内发现阻塞阶段**。
- 更准确的表述应为：
  - **首个阻塞阶段不在本轮已覆盖的启动早期阶段内；阻塞边界应后移到“主循环开始后”的逐条处理路径中继续定位。**

## 为什么能得出这个结论
`scripts/verify_news_price_impact.py` 的主函数路径是：
- 解析参数
- 调用 `process_all_records()`
- 在进入 `for i, rec in enumerate(records):` 主循环前，会先执行：
  - 建立连接
  - 执行主记录查询
  - `records = cur.fetchall()`
  - 打印总记录数
  - 初始化统计对象

本次探针已证明：
- 模块导入没卡住
- 配置读取没卡住
- DB 建连没卡住
- `SELECT 1` 没卡住
- 最小版 `news_analysis JOIN news_raw` 查询没卡住
- 进入主循环前的记录总数统计也没卡住

因此，“启动早期阻塞”这一假设在当前环境下**没有被探针支持**。

## 对前序 full-log capture 现象的最小解释
前序 note 记录到：真实 dry-run 跑 150 秒以上无 stdout/stderr。
结合本次探针，最小解释是：
- 脚本**并非卡死在 import / config / DB connect / 首个轻量查询**；
- 更可能卡在**主循环中的某条记录处理**，例如：
  - `find_best_symbol()` 的窗口查询
  - `find_price()` 在 `kline_data` 上的多轮 before/after 查询
  - 某条记录对应的排序 / 过滤 SQL 在大表上退化
- 同时由于 `print()` 输出缓冲或宿主重定向方式，导致“已进入循环但暂时无可见 stdout”。

## 最小下一步修复建议
只给最小下一步，不扩 scope：
1. **不要回退到 legacy `time`。**
2. 在 `scripts/verify_news_price_impact.py` 内部继续做第二层探针，但仅限主循环首条记录附近：
   - `records fetched` 后立即落盘
   - `loop record picked` 前后落盘
   - `find_best_symbol` 前后落盘
   - `base_price lookup` 前后落盘
   - 每个 SQL 设置 statement timeout
3. 优先只探测 **第 1 条记录**，不要重新无边界跑完整 dry-run。
4. 若需要保留零侵入原则，也可再新增一个“单条 record probe”独立脚本，而不是直接大改业务脚本。

## 本轮执行命令
```powershell
$env:PYTHONPATH='E:\quant-trading-mvp'; python 'E:\quant-trading-mvp\scripts\verify_news_price_impact_early_probe.py'
```

## 关键读回确认
已读回以下关键文件：
- `E:\quant-trading-mvp\logs\verify_news_price_impact_early_probe_20260325-161822.log`
- `E:\quant-trading-mvp\docs\refactor-status\deliveries\2026-03-25-16-runtime-note-verify-news-price-impact-early-block-probe.md`
- `E:\quant-trading-mvp\scripts\verify_news_price_impact_early_probe.py`

## 对照期望输出检查
- Probe 日志文件路径：**已提供**
- 最后成功阶段：**已明确**
- 首个阻塞阶段：**已明确说明“未在启动早期范围内发现；边界后移到主循环后”**
- 每个已执行探针结果摘要：**已逐条列出**
- 临时探针改动：**已列出修改文件与目的**
- 最小下一步修复建议：**已提供**
- delivery / runtime note 文件：**已生成**
