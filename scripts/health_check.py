import json
from pathlib import Path

raw = Path('E:/quant-trading-mvp/data/strategy_state.json').read_text(encoding='utf-8-sig')
state = json.loads(raw)
pos = state.get('open_positions', [])
print(f'positions: {len(pos)}')
print(f'consecutive_losses: {state.get("consecutive_losses", 0)}')
for p in pos:
    print(f'  {p["direction"]} {p["volume"]} lots @ {p["entry_price"]}')
