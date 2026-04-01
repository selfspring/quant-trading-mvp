import sys, os, signal, time as _time
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
    import importlib.util
    spec = importlib.util.spec_from_file_location("verify", r"E:\quant-trading-mvp\scripts\verify_news_price_impact.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    
    print(f"Starting dry-run at {_time.strftime('%H:%M:%S')}")
    sys.stdout.flush()
    
    start = _time.time()
    stats = mod.process_all_records(dry_run=True, anchor_time='effective_time')
    elapsed = _time.time() - start
    
    print(f"\nDry-run completed in {elapsed:.1f}s")
    print(f"Stats: {stats}")
    sys.stdout.flush()

except Exception as e:
    print(f"\nEXCEPTION at {_time.strftime('%H:%M:%S')}: {type(e).__name__}: {e}")
    traceback.print_exc()
    sys.stdout.flush()
