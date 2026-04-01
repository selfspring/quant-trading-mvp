"""验证信号类型修复：字符串 vs 整数"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from quant.risk_executor.signal_processor import SignalProcessor
from quant.common.config import config

sp = SignalProcessor(config)

# 修复前：字符串 'buy'
r1 = sp.process_signal({'signal': 'buy', 'confidence': 0.65, 'prediction': 0.0023}, None)
print(f'[BUG] signal="buy"(str) -> result={r1}')

# 修复后：整数 1
r2 = sp.process_signal({'signal': 1, 'confidence': 0.65, 'prediction': 0.0023}, None)
print(f'[FIX] signal=1(int)   -> result={r2}')

# 修复后：整数 -1
r3 = sp.process_signal({'signal': -1, 'confidence': 0.65, 'prediction': -0.0023}, None)
print(f'[FIX] signal=-1(int)  -> result={r3}')

# 验证
assert r1 is None, "BUG confirmed: string signal returns None"
assert r2 is not None and len(r2) > 0, "FIX works: int signal returns intent"
assert r3 is not None and len(r3) > 0, "FIX works: int signal returns intent"
print("\nAll assertions passed! Bug confirmed and fix verified.")
