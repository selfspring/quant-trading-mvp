path = r'E:\quant-trading-mvp\scripts\run_single_cycle.py'
content = open(path, encoding='utf-8').read()

# 1. 替换 import
content = content.replace(
    'from quant.common.ctp_factory import ctp_trade_session',
    'from quant.common.tq_factory import tq_trade_session'
)

# 2. 替换所有 with ctp_trade_session 调用
content = content.replace('with ctp_trade_session(config)', 'with tq_trade_session(config)')

open(path, 'w', encoding='utf-8').write(content)
print('Done')

# Verify
for i, l in enumerate(open(path, encoding='utf-8')):
    if 'ctp_trade_session' in l or 'tq_trade_session' in l:
        print(f'{i+1}: {l.rstrip()}')
