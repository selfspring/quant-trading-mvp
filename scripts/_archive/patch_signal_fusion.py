path = r'E:\quant-trading-mvp\quant\signal_generator\signal_fusion.py'
content = open(path, encoding='utf-8').read()

# Replace 0.005 thresholds in _calculate_strength for ML signal
old = """            if prediction > 0.005 and final_direction == "buy":
                weighted_sum += ml_confidence * self.ml_weight
                weight_sum += self.ml_weight
            elif prediction < -0.005 and final_direction == "sell":
                weighted_sum += ml_confidence * self.ml_weight
                weight_sum += self.ml_weight
            elif abs(prediction) <= 0.005 and final_direction == "hold":
                weighted_sum += ml_confidence * self.ml_weight
                weight_sum += self.ml_weight"""

new = """            if prediction > 0.0008 and final_direction == "buy":
                weighted_sum += ml_confidence * self.ml_weight
                weight_sum += self.ml_weight
            elif prediction < -0.0008 and final_direction == "sell":
                weighted_sum += ml_confidence * self.ml_weight
                weight_sum += self.ml_weight
            elif abs(prediction) <= 0.0008 and final_direction == "hold":
                weighted_sum += ml_confidence * self.ml_weight
                weight_sum += self.ml_weight"""

if old in content:
    content = content.replace(old, new)
    open(path, 'w', encoding='utf-8').write(content)
    print('Patched signal_fusion.py: 0.005 -> 0.0008')
else:
    print('ERROR: old text not found')
    # Debug: find the lines
    for i, l in enumerate(open(path, encoding='utf-8')):
        if '0.005' in l:
            print(f'{i+1}: {l.rstrip()}')
