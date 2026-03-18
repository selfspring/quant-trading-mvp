# ML 模块 Step 2 完成总结

## 完成内容
- 在 config.py 中添加了 MLConfig 类
- 在主 Config 类中添加了 ml 字段
- 创建了 test_ml_config.py 测试脚本
- 测试通过，配置加载正常

## 配置参数
- model_path: models/lgbm_model.txt
- feature_window: 60 分钟
- prediction_horizon: 60 分钟
- confidence_threshold: 0.65
- LightGBM 参数：learning_rate=0.05, num_leaves=31, max_depth=6

## 下一步需要
- 实现 feature_engineer.py 的特征计算逻辑
- 从数据库读取 K 线数据
- 计算技术指标（MA、MACD、RSI 等）
