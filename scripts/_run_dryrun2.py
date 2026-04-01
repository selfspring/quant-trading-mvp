"""Run verify_news_price_impact dry-run and write output to file."""
import sys
import os
import traceback

os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.path.insert(0, r'E:\quant-trading-mvp')

output_path = r'E:\quant-trading-mvp\scripts\_dryrun_output.txt'

with open(output_path, 'w', encoding='utf-8') as f:
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    sys.stdout = f
    sys.stderr = f
    try:
        from scripts.verify_news_price_impact import process_all_records
        stats = process_all_records(dry_run=True, anchor_time='effective_time')
        print("\n=== COMPLETED SUCCESSFULLY ===")
        print(f"Stats: {stats}")
    except Exception as e:
        print(f"\n=== ERROR ===")
        print(f"Exception: {e}")
        traceback.print_exc()
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr

print(f"Output written to {output_path}")
