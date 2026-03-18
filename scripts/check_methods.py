import sys
sys.path.insert(0, 'E:\\quant-trading-mvp')
from quant.data_collector.ctp_trade import CTPTradeApi
print("CTPTradeApi methods:")
for m in sorted([x for x in dir(CTPTradeApi) if not x.startswith('_')]):
    print(f"  {m}")
