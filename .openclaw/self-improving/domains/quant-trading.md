# Self-Improving Memory - 量化交易领域

## 任务分配模式 ✅

### 成功的 Agent 协作流程
1. **PM/Architect 审查** → 发现隐患和缺失
2. **Backend 修复** → 实现具体功能
3. **QA 测试** → 验证功能正确性
4. **总结文档** → 记录完成状态

### 关键原则
- **TDD**: QA 先写测试，Backend 照着实现
- **小步快跑**: 每个任务控制在 5-7 分钟内完成
- **及时总结**: 每个阶段生成 Markdown 报告

## 量化交易特定经验

### 模块解耦
- **技术指标** (`technical_indicators.py`): 纯函数，可复用
- **特征工程** (`feature_engineer.py`): 统一管理特征生成
- **ML 预测** (`ml_predictor.py`): 只负责推理，不重复计算指标
- **信号处理** (`signal_processor.py`): 置信度过滤
- **风控管理** (`risk_manager.py`): 持仓冲突检查
- **交易执行** (`trade_executor.py`): CTP 参数转换

**教训**: MLPredictor 曾经绕过 FeatureEngineer 直接计算指标，导致训练/推理特征不一致。必须强制通过统一入口。

### 风控优先级
1. **持仓安全第一**: 反向信号必须先平仓
2. **置信度过滤**: 低置信度信号直接丢弃
3. **真实持仓同步**: 定期从 CTP 同步，不信任内存状态

### CTP 接口注意事项
- 订阅合约：大写 + bytes 编码
- 发单：小写字符串
- 交易时段：避开午休 (12:15-13:30)
- 必须处理断线重连

### 测试策略
- **Mock 测试**: 用假对象验证逻辑
- **集成测试**: 真实类串联验证
- **Dry-run 模式**: 不发真实订单，验证全流程

## Windows 开发坑
- PowerShell 管道编码问题：用 `Select-Object` 代替 `| head`
- 日志 emoji 在 GBK 终端报错：用 UTF-8 编码或避免 emoji
- 文件路径：用 `Select-String` 代替 `grep`
