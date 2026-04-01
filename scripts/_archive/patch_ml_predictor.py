import sys
sys.path.insert(0, r'E:\quant-trading-mvp')

path = r'E:\quant-trading-mvp\quant\signal_generator\ml_predictor.py'
content = open(path, encoding='utf-8').read()

new_block = '''        # 4. 生成开仓/方向信号，判断方向
        # 新模型预测1小时收益率，std~0.0035，threshold调低
        threshold = 0.0015
        if pred_value > threshold:
            direction = "buy"
            signal = 1
        elif pred_value < -threshold:
            direction = "sell"
            signal = -1
        else:
            direction = None
            signal = 0

        # 5. 计算置信度（只对有方向信号计算）
        # 映射：0.0015->0.35, 0.003->0.6, 0.008+->0.9
        if signal == 0:
            confidence = 0.0
        else:
            abs_pred = abs(pred_value)
            if abs_pred <= threshold:
                confidence = 0.0
            elif abs_pred <= 0.003:
                # 低区间 [0.0015, 0.003] -> [0.35, 0.6]
                confidence = 0.35 + (abs_pred - threshold) / (0.003 - threshold) * 0.25
            elif abs_pred <= 0.008:
                # 中区间 [0.003, 0.008] -> [0.6, 0.9]
                confidence = 0.6 + (abs_pred - 0.003) / (0.008 - 0.003) * 0.3
            else:
                # 高区间 >0.8%，满分
                confidence = 0.9'''

# Find the block from line 56 to 85 and replace it
lines = content.split('\n')

# Find start (threshold = 0.005) and end (confidence = max(...))
start_idx = None
end_idx = None
for i, line in enumerate(lines):
    if 'threshold = 0.005' in line:
        start_idx = i
    if start_idx and 'confidence = max' in line:
        end_idx = i
        break

if start_idx is None or end_idx is None:
    print(f'Could not find block: start={start_idx}, end={end_idx}')
    # print context
    for i, l in enumerate(lines[50:90], 51):
        print(f'{i}: {l}')
else:
    print(f'Replacing lines {start_idx+1} to {end_idx+1}')
    new_lines = lines[:start_idx] + new_block.split('\n') + lines[end_idx+1:]
    open(path, 'w', encoding='utf-8').write('\n'.join(new_lines))
    print('Done')
