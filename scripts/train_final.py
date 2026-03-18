"""
Final training script with enhanced features
Train LightGBM model on 10000 bars of 30m data
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
import numpy as np
import lightgbm as lgb
from sklearn.metrics import mean_squared_error
from quant.signal_generator.feature_engineer import FeatureEngineer


def main():
    print("=" * 60)
    print("Final Model Training with Enhanced Features")
    print("=" * 60)
    
    # 1. Load data
    data_path = r'E:\quant-trading-mvp\data\tq_au_30m_10000.csv'
    print(f"\n[1/6] Loading data from: {data_path}")
    df = pd.read_csv(data_path)
    print(f"Loaded {len(df)} rows")
    print(f"Columns: {list(df.columns)}")
    print(f"Date range: {df['datetime'].iloc[0]} to {df['datetime'].iloc[-1]}")
    
    # 2. Generate features
    print("\n[2/6] Generating features...")
    engineer = FeatureEngineer()
    X, y = engineer.prepare_training_data(df)
    
    # Remove NaN
    print(f"Before dropna: X shape = {X.shape}")
    mask = ~(X.isna().any(axis=1) | y.isna())
    X = X[mask]
    y = y[mask]
    print(f"After dropna: X shape = {X.shape}, y shape = {y.shape}")
    print(f"Number of features: {X.shape[1]}")
    
    # 3. Train/test split (80/20)
    print("\n[3/6] Splitting data (80% train, 20% test)...")
    split_idx = int(len(X) * 0.8)
    X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
    y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]
    print(f"Train: {len(X_train)} samples")
    print(f"Test: {len(X_test)} samples")
    
    # 4. Train LightGBM model
    print("\n[4/6] Training LightGBM model...")
    train_data = lgb.Dataset(X_train, label=y_train)
    test_data = lgb.Dataset(X_test, label=y_test, reference=train_data)
    
    params = {
        'objective': 'regression',
        'metric': 'rmse',
        'boosting_type': 'gbdt',
        'num_leaves': 31,
        'learning_rate': 0.05,
        'feature_fraction': 0.9,
        'bagging_fraction': 0.8,
        'bagging_freq': 5,
        'verbose': -1
    }
    
    model = lgb.train(
        params,
        train_data,
        num_boost_round=200,
        valid_sets=[test_data],
        callbacks=[lgb.early_stopping(stopping_rounds=20), lgb.log_evaluation(period=50)]
    )
    
    # 5. Evaluate
    print("\n[5/6] Evaluating model...")
    y_pred_train = model.predict(X_train, num_iteration=model.best_iteration)
    y_pred_test = model.predict(X_test, num_iteration=model.best_iteration)
    
    # MSE and RMSE
    mse_train = mean_squared_error(y_train, y_pred_train)
    mse_test = mean_squared_error(y_test, y_pred_test)
    rmse_train = np.sqrt(mse_train)
    rmse_test = np.sqrt(mse_test)
    
    # Direction accuracy
    def direction_accuracy(y_true, y_pred):
        return np.mean((y_true > 0) == (y_pred > 0))
    
    dir_acc_train = direction_accuracy(y_train, y_pred_train)
    dir_acc_test = direction_accuracy(y_test, y_pred_test)
    
    # Correlation
    corr_train = np.corrcoef(y_train, y_pred_train)[0, 1]
    corr_test = np.corrcoef(y_test, y_pred_test)[0, 1]
    
    print("\n" + "=" * 60)
    print("EVALUATION RESULTS")
    print("=" * 60)
    print(f"Number of features: {X.shape[1]}")
    print(f"\nTrain Set:")
    print(f"  MSE:  {mse_train:.6f}")
    print(f"  RMSE: {rmse_train:.6f}")
    print(f"  Direction Accuracy: {dir_acc_train:.2%}")
    print(f"  Correlation: {corr_train:.4f}")
    print(f"\nTest Set:")
    print(f"  MSE:  {mse_test:.6f}")
    print(f"  RMSE: {rmse_test:.6f}")
    print(f"  Direction Accuracy: {dir_acc_test:.2%}")
    print(f"  Correlation: {corr_test:.4f}")
    
    # 6. Save model
    print("\n[6/6] Saving model...")
    model_path = r'E:\quant-trading-mvp\models\lgbm_model.txt'
    model.save_model(model_path)
    print(f"Model saved to: {model_path}")
    
    # Feature importance
    print("\n" + "=" * 60)
    print("TOP 20 IMPORTANT FEATURES")
    print("=" * 60)
    feature_importance = pd.DataFrame({
        'feature': X.columns,
        'importance': model.feature_importance(importance_type='gain')
    }).sort_values('importance', ascending=False)
    
    for idx, row in feature_importance.head(20).iterrows():
        print(f"{row['feature']:30s} {row['importance']:10.2f}")
    
    print("\n" + "=" * 60)
    print("Training completed successfully!")
    print("=" * 60)


if __name__ == '__main__':
    main()
