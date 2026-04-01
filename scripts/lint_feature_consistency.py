"""
特征一致性 Linter
检查模型期望的特征与 FeatureEngineer 实际生成的特征是否一致。

运行方式: python scripts/lint_feature_consistency.py
退出码: 0=通过, 1=失败
"""
import sys
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

ERRORS = []


def add_error(rule, desc, fix):
    ERRORS.append({"rule": rule, "desc": desc, "fix": fix})


def get_model_features():
    """从 lgbm_model.txt 加载模型期望的特征列表"""
    model_path = PROJECT_ROOT / "models" / "lgbm_model.txt"
    if not model_path.exists():
        add_error("model-exists", f"模型文件不存在: {model_path}",
                  "运行 python scripts/train_final_clean.py 重新训练模型")
        return None
    try:
        import lightgbm as lgb
        model = lgb.Booster(model_file=str(model_path))
        return model.feature_name()
    except Exception as e:
        add_error("model-load", f"加载模型失败: {e}",
                  "确保 lightgbm 已安装: pip install lightgbm")
        return None


def get_feature_engineer_features():
    """用 FeatureEngineer 生成测试特征，获取实际特征列表"""
    try:
        import pandas as pd
        import numpy as np

        # 构造 100 行 OHLCV + open_interest 假数据
        np.random.seed(42)
        n = 100
        base_price = 600.0
        close = base_price + np.cumsum(np.random.randn(n) * 0.5)
        high = close + np.abs(np.random.randn(n) * 0.3)
        low = close - np.abs(np.random.randn(n) * 0.3)
        open_price = close + np.random.randn(n) * 0.2

        # 生成时间戳（带小时信息，以便时间特征生效）
        timestamps = pd.date_range("2025-01-01 09:00", periods=n, freq="30min")

        df = pd.DataFrame({
            "timestamp": timestamps,
            "open": open_price,
            "high": high,
            "low": low,
            "close": close,
            "volume": np.random.randint(100, 10000, n).astype(float),
            "open_interest": np.random.randint(1000, 50000, n).astype(float),
        })

        from quant.signal_generator.feature_engineer import FeatureEngineer
        fe = FeatureEngineer()
        X, y = fe.prepare_training_data(df)
        return list(X.columns)
    except Exception as e:
        add_error("feature-engineer", f"FeatureEngineer 生成特征失败: {e}",
                  "检查 quant/signal_generator/feature_engineer.py 是否正常工作")
        return None


def check_feature_consistency(model_features, actual_features):
    """对比模型特征和实际特征"""
    model_set = set(model_features)
    actual_set = set(actual_features)

    missing = model_set - actual_set
    extra = actual_set - model_set

    if missing:
        add_error("feature-missing",
                  f"FeatureEngineer 缺少模型需要的特征 ({len(missing)} 个): {sorted(missing)}",
                  "在 FeatureEngineer.generate_features() 中添加缺少的特征计算")

    if extra:
        add_error("feature-extra",
                  f"FeatureEngineer 生成了模型不需要的额外特征 ({len(extra)} 个): {sorted(extra)}",
                  "在 prepare_training_data() 中过滤掉多余特征，或重新训练模型")


def check_doc_feature_count(model_features):
    """检查 ML_MODULE_GUIDE.md 中记录的特征数量是否与模型一致"""
    doc_path = PROJECT_ROOT / "docs" / "ML_MODULE_GUIDE.md"
    if not doc_path.exists():
        add_error("doc-exists", f"文档不存在: {doc_path}",
                  "创建 docs/ML_MODULE_GUIDE.md 并记录特征信息")
        return

    content = doc_path.read_text(encoding="utf-8")
    import re
    # 查找类似 "特征数量: 47" 或 "47 个" 的模式
    matches = re.findall(r'(\d+)\s*个', content)
    # 也查找 "特征数量**: 47"
    matches2 = re.findall(r'[Tt]otal.*?(\d+)', content)

    actual_count = len(model_features)
    doc_counts = [int(m) for m in matches if int(m) == actual_count or (30 <= int(m) <= 100)]

    if not doc_counts:
        add_error("doc-count",
                  f"ML_MODULE_GUIDE.md 中未找到与模型特征数量 ({actual_count}) 匹配的记录",
                  f"更新文档中的特征数量为 {actual_count}")
    else:
        # 检查是否有匹配的
        if actual_count not in doc_counts:
            add_error("doc-count-mismatch",
                      f"文档记录的特征数量 {doc_counts} 与模型实际特征数量 {actual_count} 不一致",
                      f"更新 ML_MODULE_GUIDE.md 中的特征数量为 {actual_count}")


def main():
    print("=" * 60)
    print("特征一致性 Linter")
    print("=" * 60)

    # 1. 获取模型特征
    print("\n[1/4] 加载模型特征...")
    model_features = get_model_features()
    if model_features:
        print(f"  模型期望 {len(model_features)} 个特征")

    # 2. 获取 FeatureEngineer 特征
    print("[2/4] 生成 FeatureEngineer 特征...")
    actual_features = get_feature_engineer_features()
    if actual_features:
        print(f"  FeatureEngineer 生成 {len(actual_features)} 个特征")

    # 3. 对比
    if model_features and actual_features:
        print("[3/4] 对比特征一致性...")
        check_feature_consistency(model_features, actual_features)

    # 4. 检查文档
    if model_features:
        print("[4/4] 检查文档特征数量...")
        check_doc_feature_count(model_features)

    # 输出结果
    if ERRORS:
        print(f"\n发现 {len(ERRORS)} 个问题:\n")
        for err in ERRORS:
            print(f"X [{err['rule']}]")
            print(f"  {err['desc']}")
            print(f"  修复方法: {err['fix']}")
            print()
        sys.exit(1)
    else:
        print("\n[PASS] 特征一致性检查通过")
        sys.exit(0)


if __name__ == "__main__":
    main()
