"""
信号融合模块测试脚本
验证 SignalFusion 类的各项功能
"""
from datetime import datetime
from quant.signal_generator.signal_fusion import SignalFusion, fuse_signals


def test_basic_fusion():
    """测试基本融合功能"""
    print("=" * 60)
    print("测试 1: 基本信号融合")
    print("=" * 60)
    
    fusion = SignalFusion()
    
    # 三个信号都是 buy
    technical = {"signal": "buy", "strength": 0.7}
    ml = {"prediction": 0.008, "confidence": 0.8}
    llm = {"direction": "bullish", "confidence": 0.85}
    
    result = fusion.fuse_signals(
        technical_signal=technical,
        ml_signal=ml,
        llm_signal=llm,
        symbol="au2606"
    )
    
    print(f"输入:")
    print(f"  技术信号: {technical}")
    print(f"  ML信号: {ml}")
    print(f"  LLM信号: {llm}")
    print(f"\n输出:")
    print(f"  方向: {result['direction']}")
    print(f"  强度: {result['strength']:.4f}")
    print(f"  预期: buy, 强度约 0.78")
    print()


def test_inconsistent_signals():
    """测试不一致信号"""
    print("=" * 60)
    print("测试 2: 不一致信号（应输出 hold）")
    print("=" * 60)
    
    fusion = SignalFusion()
    
    # 三个信号方向不一致
    technical = {"signal": "buy", "strength": 0.7}
    ml = {"prediction": -0.008, "confidence": 0.8}  # sell
    llm = {"direction": "neutral", "confidence": 0.6}  # hold
    
    result = fusion.fuse_signals(
        technical_signal=technical,
        ml_signal=ml,
        llm_signal=llm,
        symbol="au2606"
    )
    
    print(f"输入:")
    print(f"  技术信号: buy")
    print(f"  ML信号: sell (prediction={ml['prediction']})")
    print(f"  LLM信号: hold (neutral)")
    print(f"\n输出:")
    print(f"  方向: {result['direction']}")
    print(f"  强度: {result['strength']:.4f}")
    print(f"  预期: hold (方向不一致)")
    print()


def test_partial_signals():
    """测试部分信号缺失"""
    print("=" * 60)
    print("测试 3: 部分信号缺失")
    print("=" * 60)
    
    fusion = SignalFusion()
    
    # 只有技术信号和ML信号
    technical = {"signal": "sell", "strength": 0.65}
    ml = {"prediction": -0.012, "confidence": 0.75}
    
    result = fusion.fuse_signals(
        technical_signal=technical,
        ml_signal=ml,
        llm_signal=None,  # LLM信号缺失
        symbol="au2606"
    )
    
    print(f"输入:")
    print(f"  技术信号: {technical}")
    print(f"  ML信号: {ml}")
    print(f"  LLM信号: None")
    print(f"\n输出:")
    print(f"  方向: {result['direction']}")
    print(f"  强度: {result['strength']:.4f}")
    print(f"  预期: sell (2/2 一致)")
    print()


def test_all_signals_missing():
    """测试所有信号缺失"""
    print("=" * 60)
    print("测试 4: 所有信号缺失")
    print("=" * 60)
    
    fusion = SignalFusion()
    
    result = fusion.fuse_signals(
        technical_signal=None,
        ml_signal=None,
        llm_signal=None,
        symbol="au2606"
    )
    
    print(f"输入: 所有信号都为 None")
    print(f"\n输出:")
    print(f"  方向: {result['direction']}")
    print(f"  强度: {result['strength']:.4f}")
    print(f"  原因: {result.get('reason', 'N/A')}")
    print(f"  预期: hold (all_signals_missing)")
    print()


def test_custom_weights():
    """测试自定义权重"""
    print("=" * 60)
    print("测试 5: 自定义权重")
    print("=" * 60)
    
    # ML权重更高
    fusion = SignalFusion(ml_weight=0.7, technical_weight=0.2, llm_weight=0.1)
    
    technical = {"signal": "buy", "strength": 0.6}
    ml = {"prediction": 0.015, "confidence": 0.9}
    llm = {"direction": "bullish", "confidence": 0.7}
    
    result = fusion.fuse_signals(
        technical_signal=technical,
        ml_signal=ml,
        llm_signal=llm,
        symbol="au2606"
    )
    
    print(f"权重: ML=0.7, 技术=0.2, LLM=0.1")
    print(f"输入:")
    print(f"  技术信号: {technical}")
    print(f"  ML信号: {ml}")
    print(f"  LLM信号: {llm}")
    print(f"\n输出:")
    print(f"  方向: {result['direction']}")
    print(f"  强度: {result['strength']:.4f}")
    print(f"  预期: buy, 强度约 0.85 (ML权重高)")
    print()


def test_consistency_check():
    """测试一致性检查逻辑"""
    print("=" * 60)
    print("测试 6: 一致性检查（2/3 规则）")
    print("=" * 60)
    
    fusion = SignalFusion()
    
    # 测试 2 buy + 1 sell
    technical = {"signal": "buy", "strength": 0.7}
    ml = {"prediction": 0.008, "confidence": 0.8}
    llm = {"direction": "bearish", "confidence": 0.6}  # sell
    
    result = fusion.fuse_signals(
        technical_signal=technical,
        ml_signal=ml,
        llm_signal=llm,
        symbol="au2606"
    )
    
    print(f"输入: 2 buy + 1 sell")
    print(f"  技术信号: buy")
    print(f"  ML信号: buy")
    print(f"  LLM信号: sell")
    print(f"\n输出:")
    print(f"  方向: {result['direction']}")
    print(f"  强度: {result['strength']:.4f}")
    print(f"  预期: buy (2/3 一致)")
    print()


def test_ml_threshold():
    """测试 ML 预测阈值"""
    print("=" * 60)
    print("测试 7: ML 预测阈值 (±0.005)")
    print("=" * 60)
    
    fusion = SignalFusion()
    
    # ML 预测接近 0，应判断为 hold
    technical = {"signal": "buy", "strength": 0.7}
    ml = {"prediction": 0.003, "confidence": 0.8}  # 小于 0.005，应为 hold
    llm = {"direction": "bullish", "confidence": 0.6}
    
    result = fusion.fuse_signals(
        technical_signal=technical,
        ml_signal=ml,
        llm_signal=llm,
        symbol="au2606"
    )
    
    print(f"输入:")
    print(f"  技术信号: buy")
    print(f"  ML信号: prediction=0.003 (< 0.005, 应为 hold)")
    print(f"  LLM信号: buy")
    print(f"\n输出:")
    print(f"  方向: {result['direction']}")
    print(f"  预期: buy (2 buy + 1 hold, 2/3 一致)")
    print()


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("信号融合模块测试")
    print("=" * 60 + "\n")
    
    try:
        test_basic_fusion()
        test_inconsistent_signals()
        test_partial_signals()
        test_all_signals_missing()
        test_custom_weights()
        test_consistency_check()
        test_ml_threshold()
        
        print("=" * 60)
        print("所有测试完成！")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
