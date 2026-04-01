import sys, os
sys.path.insert(0, r"E:\quant-trading-mvp")
os.chdir(r"E:\quant-trading-mvp")

if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8')

import traceback

try:
    print("Loading verify_news_price_impact...")
    sys.stdout.flush()
    
    # Check for init_db dependency issue
    # The verify script imports from quant.common.config, let's check it loads
    from quant.common.config import config
    print(f"Config loaded: {config.database.database}")
    sys.stdout.flush()
    
    # Check if there's a kline_30m_availability table reference issue in init_db
    # The init_db.py has CREATE_TABLE_SQL / CREATE_INDEX_SQL references
    print("Checking init_db for issues...")
    sys.stdout.flush()
    
    # Now try to import the verify module
    import importlib.util
    spec = importlib.util.spec_from_file_location("verify", r"E:\quant-trading-mvp\scripts\verify_news_price_impact.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    print("Module loaded!")
    sys.stdout.flush()
    
    print("\nStarting dry-run...")
    sys.stdout.flush()
    stats = mod.process_all_records(dry_run=True, anchor_time='effective_time')
    print("\nDry-run completed!")
    sys.stdout.flush()
    
except Exception as e:
    print(f"\nEXCEPTION: {type(e).__name__}: {e}")
    traceback.print_exc()
    sys.stdout.flush()
