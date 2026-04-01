import json
lines = open('E:/quant-trading-mvp/data/factor_discovery_log.jsonl', 'r', encoding='utf-8').readlines()
total = len([l for l in lines if l.strip()])
effective = len([l for l in lines if l.strip() and json.loads(l).get('effective')])
print(f'Total tested: {total}, Effective: {effective}')
print('\nThis session new factors:')
for l in lines[-26:]:
    if not l.strip(): continue
    d = json.loads(l)
    tag = 'OK' if d.get('effective') else '--'
    print(f"  [{tag}] {d['name']}: IC={d['avg_abs_ic']:.4f}")
