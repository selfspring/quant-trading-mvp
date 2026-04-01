"""Run verify_news_price_impact dry-run and capture output."""
import sys
import os
import traceback

# Encoding fix for Windows
os.environ['PYTHONIOENCODING'] = 'utf-8'
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from scripts.verify_news_price_impact import process_all_records
    stats = process_all_records(dry_run=True, anchor_time='effective_time')
    print("\n=== COMPLETED SUCCESSFULLY ===")
    print(f"Stats: {stats}")
except Exception as e:
    print(f"\n=== ERROR ===")
    print(f"Exception: {e}")
    traceback.print_exc()
