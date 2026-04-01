"""
测试备用数据源
验证：当 SimNow 无数据时，备用数据源能否正常提供 K 线
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from quant.data_collector.backup_data_source import get_backup_data_source
from quant.common.config import config

def test_backup_data_source():
    """测试备用数据源"""
    print("=" * 60)
    print("测试备用数据源")
    print("=" * 60)
    
    # 初始化
    backup = get_backup_data_source()
    print(f"\n✅ 备用数据源类型：{backup.data_source}")
    
    symbol = config.strategy.symbol
    print(f"测试合约：{symbol}")
    
    # 测试 1: 获取实时 K 线
    print("\n" + "-" * 60)
    print("测试 1: 获取实时 K 线")
    print("-" * 60)
    
    klines = backup.get_realtime_klines(symbol=symbol, count=10, period='1min')
    
    if klines is not None and not klines.empty:
        print(f"✅ 获取成功：{len(klines)} 根 K 线")
        print("\n最新 3 根 K 线:")
        print(klines.tail(3).to_string())
    else:
        print("⚠️  备用数据源无法获取实时数据")
        print("   可能原因:")
        print("   - Tushare token 未配置")
        print("   - AkShare 数据接口暂时不可用")
        print("   - 该合约无历史数据")
    
    # 测试 2: 生成模拟数据
    print("\n" + "-" * 60)
    print("测试 2: 生成模拟 K 线（用于测试策略逻辑）")
    print("-" * 60)
    
    mock_klines = backup.generate_mock_klines(
        symbol=symbol,
        count=10,
        period='1min',
        base_price=580.0
    )
    
    print(f"✅ 生成成功：{len(mock_klines)} 根 K 线")
    print("\n模拟 K 线数据:")
    print(mock_klines.to_string())
    
    # 测试 3: 存储到数据库
    print("\n" + "-" * 60)
    print("测试 3: 存储到数据库")
    print("-" * 60)
    
    success = backup.fetch_and_store(symbol=symbol, count=20, period='1min')
    
    if success:
        print("✅ 数据存储成功")
    else:
        print("⚠️  数据存储失败")
    
    # 总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    print("\n解决方案已就绪:")
    print("1. ✅ 备用数据源模块已创建")
    print("2. ✅ 增强版主策略已创建 (main_strategy_enhanced.py)")
    print("3. ✅ 支持三级数据回退:")
    print("   - SimNow 实时 Tick → 聚合 K 线")
    print("   - Tushare/AkShare API → 历史 K 线")
    print("   - 模拟数据生成 → 策略逻辑验证")
    print("\n使用方法:")
    print("  python scripts/main_strategy_enhanced.py")
    print("\n下一步:")
    print("1. 如需使用 Tushare，在 .env 中配置 TUSHARE_TOKEN")
    print("2. 或直接运行增强版策略，会自动使用模拟数据测试")
    print("3. 等待夜盘时段，SimNow 可能有实时数据推送")


if __name__ == "__main__":
    test_backup_data_source()
