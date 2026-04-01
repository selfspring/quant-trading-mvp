path = r'E:\quant-trading-mvp\scripts\run_single_cycle.py'
content = open(path, encoding='utf-8').read()

# 1. Replace import
content = content.replace(
    'from quant.common.ctp_factory import ctp_trade_session',
    'from quant.common.tq_factory import tq_trade_session'
)

# 2. Replace all usages
content = content.replace('ctp_trade_session(', 'tq_trade_session(')

# 3. Replace log messages (CTP -> 天勤)
content = content.replace('CTP \u65e0\u6301\u4ed3\u4f46 state \u6709\u8bb0\u5f55', '\u5929\u52e4\u65e0\u6301\u4ed3\u4f46 state \u6709\u8bb0\u5f55')
content = content.replace('CTP \u540c\u6b65\u5931\u8d25', '\u5929\u52e4\u540c\u6b65\u5931\u8d25')

open(path, 'w', encoding='utf-8').write(content)
print('Done')

# Verify
count_ctp = content.count('ctp_trade_session')
count_tq = content.count('tq_trade_session')
print(f'ctp_trade_session: {count_ctp} (should be 0)')
print(f'tq_trade_session: {count_tq} (should be >0)')
