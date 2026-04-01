import os
import sys
import logging
sys.path.insert(0, "E:/quant-trading-mvp")
os.chdir("E:/quant-trading-mvp")

from quant.signal_generator.signal_fusion import SignalFusion
from scripts.run_single_cycle import fetch_llm_signal

logging.basicConfig(level=logging.INFO)

def test_fetch_and_fuse():
    print("Testing LLM Fetch")
    llm_signal = fetch_llm_signal()
    print(f"Fetched: {llm_signal}")
    
    sf = SignalFusion(technical_weight=0.4, ml_weight=0.5, llm_weight=0.1)
    tech = {"signal": "buy", "strength": 0.65}
    ml = {"prediction": 0.001, "confidence": 0.70}
    
    r1 = sf.fuse_signals(technical_signal=tech, ml_signal=ml, llm_signal=llm_signal)
    print(f"R1: {r1['direction']}")
    
    r2 = sf.fuse_signals(technical_signal=tech, ml_signal=ml, llm_signal={"direction": "neutral", "confidence": 0.0, "importance": "low"})
    print(f"R2: {r2['direction']}")
    
    r3 = sf.fuse_signals(technical_signal=tech, ml_signal=ml, llm_signal={"direction": "bullish", "confidence": 0.9, "importance": "high"})
    print(f"R3: {r3['direction']}")

if __name__ == "__main__":
    test_fetch_and_fuse()