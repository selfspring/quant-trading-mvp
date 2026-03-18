import json

with open('data/strategy_state.json', 'rb') as f:
    raw = f.read()

has_bom = raw[:3] == b'\xef\xbb\xbf'
print(f'BOM: {has_bom}')

text = raw.decode('utf-8-sig')
data = json.loads(text)

with open('data/strategy_state.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print('Fixed')
