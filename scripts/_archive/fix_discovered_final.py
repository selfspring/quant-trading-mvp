"""
Fix discovered_factors.py: all function bodies over-indented by 4 spaces (8 -> 4)
Starting from line 1815 (big_order_flow_imbalance function)
"""
path = r'E:\quant-trading-mvp\quant\factors\discovered_factors.py'
lines = open(path, encoding='utf-8').readlines()

# Find the line where over-indentation starts (should be around 1815: '        import numpy as np')
start_line = None
for i, l in enumerate(lines):
    # Look for the pattern: 8 spaces followed by 'import' in function body
    if i > 1800 and l.startswith('        import numpy as np'):
        start_line = i
        print(f'Found over-indentation start at line {i+1}')
        break

if start_line is None:
    print('ERROR: could not find over-indentation start')
    exit(1)

# From start_line to end, reduce indentation by 4 spaces for all lines
# But only for lines that are indented (not blank, not DISCOVERED_FACTORS assignment)
fixed_count = 0
for i in range(start_line, len(lines)):
    l = lines[i]
    # Skip blank lines and DISCOVERED_FACTORS[...] = ... lines
    if l.strip() == '' or l.startswith("DISCOVERED_FACTORS["):
        continue
    # Check if line has extra indentation (starts with 8+ spaces)
    if l.startswith('        '):
        # Reduce by 4 spaces
        lines[i] = l[4:]
        fixed_count += 1
    elif l.startswith('    '):
        # Already at 4 spaces, this is correct for function body
        pass

# Write back
open(path, 'w', encoding='utf-8').writelines(lines)
print(f'Fixed {fixed_count} lines from line {start_line+1} to end')

# Verify the fix
print('\nVerification:')
for i in range(start_line, min(start_line + 10, len(lines))):
    l = lines[i].replace(' ', '·')
    print(f'{i+1}: {l[:50]}')
