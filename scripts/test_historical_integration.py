"""
Test script for Task #6: Verify that analyze_news integrates historical cases from vector store.
Uses real config/DB but mocks the LLM API call to only verify prompt construction logic.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
from unittest.mock import patch, MagicMock

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s - %(message)s")

from quant.signal_generator.llm_news_analyzer import LLMNewsAnalyzer
from quant.signal_generator import news_vector_store

# Test news
test_news = {
    "datetime": "2026-03-22 10:00:00",
    "source": "Reuters",
    "title": "Fed raises interest rates by 25 basis points",
    "content": "The Federal Reserve raised interest rates by 25 basis points today, citing persistent inflation.",
    "url": "https://example.com/news/456",
}

print("=" * 60)
print("TEST 1: Verify _retrieve_historical_cases with real vector store")
print("=" * 60)

analyzer = LLMNewsAnalyzer()

# Test retrieval (uses real vector store)
historical_context = analyzer._retrieve_historical_cases(test_news)

if historical_context:
    print("[PASS] Historical cases retrieved successfully!")
    print("--- Historical Context (first 500 chars) ---")
    print(historical_context[:500])
    if len(historical_context) > 500:
        print("...")
    print("-" * 40)

    # Verify format
    assert "历史参考案例" in historical_context, "Missing header"
    assert "案例1:" in historical_context, "Missing case 1"
    assert "LLM当时判断:" in historical_context, "Missing LLM judgment"
    print("[PASS] Historical context format is correct!")
else:
    print("[INFO] No historical cases found (vector store may be empty - this is OK)")
    print("[PASS] Graceful degradation works!")

print()
print("=" * 60)
print("TEST 2: Verify _inject_historical_context")
print("=" * 60)

# Test injection
base_prompt = analyzer.ANALYSIS_PROMPT.format(
    title="Test title",
    content="Test content",
    source="Test source",
    datetime="2026-03-22",
)

fake_context = "\n## 历史参考案例\n以下是历史上与当前新闻相似的事件及其实际市场影响：\n\n案例1: Fed cuts rates (2024-06-15)\n- LLM当时判断: bullish, confidence=0.85\n- 实际价格变化: +1.2000% (1日), 判断正确\n"

injected_prompt = LLMNewsAnalyzer._inject_historical_context(base_prompt, fake_context)

# Verify the injection
assert "历史参考案例" in injected_prompt, "Historical context not injected!"
assert "请参考以上历史案例辅助判断" in injected_prompt, "Missing instruction to reference cases"
assert "只返回 JSON，不要其他文字。" in injected_prompt, "JSON instruction was removed!"

# Verify order: historical cases come BEFORE the JSON instruction
hist_pos = injected_prompt.index("历史参考案例")
json_pos = injected_prompt.index("只返回 JSON，不要其他文字。")
assert hist_pos < json_pos, "Historical context should come before JSON instruction"

print("[PASS] Historical context injected correctly!")
print("[PASS] JSON instruction preserved!")
print("[PASS] Injection order is correct (history before JSON instruction)!")

print()
print("=" * 60)
print("TEST 3: Verify graceful degradation when vector store fails")
print("=" * 60)

# Mock vector store to raise an exception
with patch.object(news_vector_store, "search_similar_news", side_effect=Exception("Connection refused")):
    context = analyzer._retrieve_historical_cases(test_news)
    assert context == "", "Should return empty string on failure"
    print("[PASS] Graceful degradation on exception!")

# Mock vector store to return empty list
with patch.object(news_vector_store, "search_similar_news", return_value=[]):
    context = analyzer._retrieve_historical_cases(test_news)
    assert context == "", "Should return empty string when no results"
    print("[PASS] Graceful degradation on empty results!")

print()
print("=" * 60)
print("TEST 4: Verify full analyze_news prompt includes history (mocked LLM)")
print("=" * 60)

# Mock both vector store and LLM API
mock_similar_news = [
    {
        "id": "news_100",
        "document": "Title: Federal Reserve raises rates\nContent: The Fed raised...\nAnalysis: Rate hike is bearish for gold",
        "metadata": {
            "news_id": 100,
            "time": "2024-03-15",
            "direction": "bearish",
            "confidence": 0.8,
            "price_change_1d": -0.5,
            "correct_1d": 1,
        },
        "distance": 0.3,
    },
    {
        "id": "news_200",
        "document": "Title: Fed signals hawkish stance\nContent: Fed officials...\nAnalysis: Hawkish Fed signals",
        "metadata": {
            "news_id": 200,
            "time": "2024-06-20",
            "direction": "bearish",
            "confidence": 0.7,
            "price_change_1d": -1.2,
            "correct_1d": 1,
        },
        "distance": 0.4,
    },
]

captured_prompt = None

original_call = LLMNewsAnalyzer._call_claude_api

def mock_call_claude(self_ref, prompt, retry_count=0):
    global captured_prompt
    captured_prompt = prompt
    return {
        "importance": "high",
        "direction": "bearish",
        "timeframe": "immediate",
        "confidence": 0.85,
        "reasoning": "Fed rate hike is bearish for gold",
    }

with patch.object(news_vector_store, "search_similar_news", return_value=mock_similar_news):
    with patch.object(LLMNewsAnalyzer, "_call_claude_api", mock_call_claude):
        result = analyzer.analyze_news(test_news)

assert captured_prompt is not None, "Prompt was not captured"
assert "历史参考案例" in captured_prompt, "Prompt missing historical cases"
assert "Federal Reserve raises rates" in captured_prompt, "Prompt missing case 1 title"
assert "Fed signals hawkish stance" in captured_prompt, "Prompt missing case 2 title"
assert "请参考以上历史案例辅助判断" in captured_prompt, "Prompt missing reference instruction"

# Verify result is unchanged format
assert result["importance"] == "high"
assert result["direction"] == "bearish"
assert result["confidence"] == 0.85

print("[PASS] Full analyze_news correctly includes historical cases in prompt!")
print("[PASS] Return value format unchanged!")
print()
print("--- Captured Prompt (showing historical section) ---")
# Show just the historical part
if "历史参考案例" in captured_prompt:
    start = captured_prompt.index("历史参考案例") - 5
    end = captured_prompt.index("只返回 JSON")
    print(captured_prompt[start:end])
print("-" * 40)

print()
print("=" * 60)
print("ALL TESTS PASSED!")
print("=" * 60)
