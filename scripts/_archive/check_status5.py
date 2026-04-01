import os
from pathlib import Path
from datetime import datetime

log_dir = Path(r"E:\quant-trading-mvp\logs")

# Check strategy log for today
strategy_log = log_dir / "strategy_2026-03-18.log"
print(f"=== {strategy_log.name} ===")
print(f"Size: {strategy_log.stat().st_size} bytes")
print(f"Modified: {datetime.fromtimestamp(strategy_log.stat().st_mtime)}")
content = strategy_log.read_text(encoding='utf-8')
if content.strip():
    print(content)
else:
    print("(EMPTY)")

# Check if there's a separate output log from Windows Task Scheduler
print("\n=== Looking for other output files ===")
for f in sorted(log_dir.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True)[:10]:
    st = f.stat()
    print(f"  {f.name:40s} {st.st_size:>10} bytes  {datetime.fromtimestamp(st.st_mtime)}")

# Check data directory for recent files
data_dir = Path(r"E:\quant-trading-mvp\data")
if data_dir.exists():
    print("\n=== data/ directory ===")
    for f in sorted(data_dir.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True)[:10]:
        st = f.stat()
        print(f"  {f.name:40s} {st.st_size:>10} bytes  {datetime.fromtimestamp(st.st_mtime)}")

# Check strategy_state.json modification time
state_file = data_dir / "strategy_state.json"
if state_file.exists():
    print(f"\n=== strategy_state.json ===")
    print(f"Modified: {datetime.fromtimestamp(state_file.stat().st_mtime)}")
    print(state_file.read_text(encoding='utf-8'))
