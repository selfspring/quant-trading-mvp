"""Run verify dry-run with proper error capture."""
import sys
import os
import traceback

os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.path.insert(0, r'E:\quant-trading-mvp')

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

try:
    from scripts.verify_news_price_impact import process_all_records
    stats = process_all_records(dry_run=True, anchor_time='effective_time')
    print("\n=== COMPLETED SUCCESSFULLY ===")
except Exception as e:
    print(f"\n=== EXCEPTION ===", flush=True)
    traceback.print_exc()
    sys.exit(1)
