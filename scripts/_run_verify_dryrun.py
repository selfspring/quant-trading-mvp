import sys, os
sys.path.insert(0, r"E:\quant-trading-mvp")
os.chdir(r"E:\quant-trading-mvp")

try:
    from scripts.verify_news_price_impact import process_all_records
    print("Module loaded successfully. Starting dry-run...")
    stats = process_all_records(dry_run=True, anchor_time='effective_time')
    print("\nDry-run completed successfully!")
except Exception as e:
    import traceback
    print(f"ERROR: {e}")
    traceback.print_exc()
