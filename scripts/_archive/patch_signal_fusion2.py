path = r'E:\quant-trading-mvp\quant\signal_generator\signal_fusion.py'
content = open(path, encoding='utf-8').read()

# 1. _normalize_signals 中 ML direction 判断 (line ~161)
content = content.replace(
    '''            if prediction > 0.005:
                ml_dir = "buy"
            elif prediction < -0.005:
                ml_dir = "sell"''',
    '''            if prediction > 0.0008:
                ml_dir = "buy"
            elif prediction < -0.0008:
                ml_dir = "sell"'''
)

# 2. _normalize_signals 注释 (line ~143)
content = content.replace(
    'ml: prediction > 0.005',
    'ml: prediction > 0.0008'
)
content = content.replace(
    '< -0.005',
    '< -0.0008'
)

open(path, 'w', encoding='utf-8').write(content)
print('Done')

# Verify all 0.005 are gone
count = content.count('0.005')
print(f'Remaining 0.005 occurrences: {count}')
for i, l in enumerate(open(path, encoding='utf-8')):
    if '0.005' in l:
        print(f'  {i+1}: {l.rstrip()}')
