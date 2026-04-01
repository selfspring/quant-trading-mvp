# Patch feature_engineer.py: normalize absolute price features before return
import re

path = r'E:\quant-trading-mvp\quant\signal_generator\feature_engineer.py'
lines = open(path, encoding='utf-8').readlines()

# Find the line with 'return df_features' in generate_features (not in other methods)
# It should be around line 199
target_line = None
for i, l in enumerate(lines):
    if 'return df_features' in l and i < 210:
        target_line = i
        print(f'Found return at line {i+1}: {l.rstrip()}')
        break

if target_line is None:
    print('ERROR: could not find return df_features')
    exit(1)

# Build normalization block to insert before return
norm_block = '''
        # === 归一化绝对价格特征 (使跨合约/跨时期可用) ===
        close_ref = df_features['close'].replace(0, float('nan'))
        for col in ['ma_5', 'ma_10', 'ma_20', 'ma_60']:
            if col in df_features.columns:
                df_features[col] = df_features[col] / close_ref - 1.0
        for col in ['macd', 'macd_signal', 'macd_hist']:
            if col in df_features.columns:
                df_features[col] = df_features[col] / close_ref
        for col in ['bb_upper', 'bb_lower', 'bb_middle']:
            if col in df_features.columns:
                df_features[col] = df_features[col] / close_ref - 1.0
        for col in ['atr']:
            if col in df_features.columns:
                df_features[col] = df_features[col] / close_ref
'''

new_lines = lines[:target_line] + [norm_block + '\n'] + lines[target_line:]
open(path, 'w', encoding='utf-8').writelines(new_lines)
print(f'Patched: inserted normalization block before line {target_line+1}')
