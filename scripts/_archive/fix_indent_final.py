"""
最终修复脚本 - 基于精确分析的缩进修复
"""
import re

INPUT = r'E:\quant-trading-mvp\quant\factors\discovered_factors.py'

with open(INPUT, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Convert to list of strings (strip \r\n for processing)
processed = [l.rstrip('\r\n') for l in lines]

def get_indent(line):
    if not line.strip():
        return -1
    return len(line) - len(line.lstrip())

# ===== Pass 1: Fix over-indented function bodies =====
# Functions where body is at 8 spaces instead of 4
# These are in the latter part of the file
fixes = 0
i = 0
output = []
while i < len(processed):
    line = processed[i]
    
    # Top-level def
    if re.match(r'^def \w+', line):
        output.append(line)
        i += 1
        
        # Check if body starts at 8 spaces (over-indented)
        # First skip docstring
        while i < len(processed):
            curr = processed[i]
            if curr.strip() == '' or curr.strip().startswith('"""') or curr.strip().startswith("'''"):
                output.append(curr)
                i += 1
                # If multi-line docstring, skip to end
                if (curr.strip().startswith('"""') or curr.strip().startswith("'''")):
                    quote = '"""' if '"""' in curr else "'''"
                    if curr.strip().count(quote) < 2:
                        while i < len(processed):
                            output.append(processed[i])
                            if quote in processed[i]:
                                i += 1
                                break
                            i += 1
                continue
            else:
                break
        
        if i >= len(processed):
            continue
        
        # Check first body line indent
        first_body = processed[i]
        first_indent = get_indent(first_body)
        
        if first_indent == 8:
            # Over-indented: shift all body lines by -4
            while i < len(processed):
                curr = processed[i]
                if re.match(r'^(def |DISCOVERED_FACTORS\[|class )', curr) and curr.strip():
                    break
                if curr.strip() == '':
                    output.append(curr)
                    i += 1
                    continue
                ind = get_indent(curr)
                if ind >= 4:
                    output.append(' ' * (ind - 4) + curr.lstrip())
                    fixes += 1
                else:
                    output.append(curr)
                i += 1
        else:
            continue  # Normal indent, don't consume lines
        continue
    
    output.append(line)
    i += 1

print(f"Pass 1: Fixed {fixes} over-indented lines")
processed = output

# ===== Pass 2: Fix for/while/if/try/def blocks where body is at same indent =====
# Use iterative approach: fix one at a time, re-check
for iteration in range(20):
    content = '\n'.join(processed)
    try:
        compile(content, 'test.py', 'exec')
        print(f"Pass 2 iteration {iteration}: ALL GOOD!")
        break
    except SyntaxError as e:
        msg = e.msg
        ln = e.lineno  # 1-based
        
        if not ln or ln > len(processed):
            print(f"Pass 2 iteration {iteration}: Cannot fix line {ln}: {msg}")
            break
        
        fixed = False
        
        if "expected 'except' or 'finally'" in msg:
            # Find the try: statement
            for j in range(ln - 2, max(0, ln - 30), -1):
                s = processed[j].strip()
                if s.startswith('try:'):
                    try_indent = get_indent(processed[j])
                    expected = try_indent + 4
                    # Fix lines between try and except
                    k = j + 1
                    while k < len(processed):
                        cs = processed[k].strip()
                        ci = get_indent(processed[k])
                        if ci == try_indent and (cs.startswith('except') or cs.startswith('finally:')):
                            break
                        if ci == try_indent and cs:
                            processed[k] = ' ' * expected + cs
                            print(f"  FIX try body: L{k+1} {try_indent}->{expected}")
                        k += 1
                    fixed = True
                    break
        
        elif "expected an indented block" in msg:
            # Find the block statement above
            for j in range(ln - 2, max(0, ln - 10), -1):
                s = processed[j].rstrip()
                if s.rstrip().endswith(':') and processed[j].strip():
                    block_indent = get_indent(processed[j])
                    expected = block_indent + 4
                    # Fix lines that should be in this block
                    k = j + 1
                    while k < len(processed):
                        cs = processed[k].strip()
                        ci = get_indent(processed[k])
                        if ci == -1:
                            k += 1
                            continue
                        if ci < block_indent:
                            break
                        if ci == block_indent and cs:
                            # Check if it's a companion keyword
                            if re.match(r'(else:|elif |except|finally:)', cs):
                                break
                            # Check if it's a DISCOVERED_FACTORS or new def
                            if cs.startswith('DISCOVERED_FACTORS[') or cs.startswith('def '):
                                break
                            processed[k] = ' ' * expected + cs
                            print(f"  FIX block body: L{k+1} {block_indent}->{expected}")
                        elif ci > block_indent:
                            # Already deeper, also shift
                            new_indent = ci + (expected - block_indent)
                            processed[k] = ' ' * new_indent + cs
                            print(f"  FIX nested: L{k+1} {ci}->{new_indent}")
                        k += 1
                    fixed = True
                    break
        
        elif "'continue' not properly in loop" in msg or "'break' outside loop" in msg:
            # This continue/break is at function level but should be in a for loop
            # Find the for loop above, then indent everything from for body start to current line
            error_indent = get_indent(processed[ln - 1])
            for j in range(ln - 2, max(0, ln - 50), -1):
                s = processed[j].strip()
                ji = get_indent(processed[j])
                if ji < error_indent and (s.startswith('for ') or s.startswith('while ')) and s.endswith(':'):
                    # Found the for/while loop
                    block_indent = ji
                    expected = block_indent + 4
                    # Lines from j+1 that are at block_indent level should be expected
                    # But some are already at expected (correct for-body lines)
                    # We need to indent lines from after the last correct for-body line
                    # Actually: find where for-body "breaks" back to block_indent
                    k = j + 1
                    while k < len(processed):
                        cs = processed[k].strip()
                        ci = get_indent(processed[k])
                        if ci == -1:
                            k += 1
                            continue
                        if ci < block_indent:
                            break
                        if ci == block_indent and cs:
                            # This should be for-body but is at wrong level
                            if cs.startswith('DISCOVERED_FACTORS[') or re.match(r'^def \w+', cs):
                                break
                            processed[k] = ' ' * expected + cs
                            print(f"  FIX for-body: L{k+1} {block_indent}->{expected}")
                        elif ci > block_indent and ci < expected:
                            new_indent = ci + (expected - block_indent)
                            processed[k] = ' ' * new_indent + cs
                            print(f"  FIX for-nested: L{k+1} {ci}->{new_indent}")
                        k += 1
                    fixed = True
                    break
        
        elif "unexpected indent" in msg:
            # Line has too much indent
            error_indent = get_indent(processed[ln - 1])
            # Look at previous non-empty line
            for j in range(ln - 2, max(0, ln - 5), -1):
                if processed[j].strip():
                    prev_indent = get_indent(processed[j])
                    prev_line = processed[j].rstrip()
                    if prev_line.endswith(':'):
                        target = prev_indent + 4
                    else:
                        target = prev_indent
                    processed[ln - 1] = ' ' * target + processed[ln - 1].lstrip()
                    print(f"  FIX unexpected indent: L{ln} {error_indent}->{target}")
                    fixed = True
                    break
        
        if not fixed:
            print(f"Pass 2 iteration {iteration}: Cannot auto-fix L{ln}: {msg}")
            # Show context
            start = max(0, ln - 4)
            end = min(len(processed), ln + 3)
            for j in range(start, end):
                marker = ">>>" if j == ln - 1 else "   "
                ind = get_indent(processed[j])
                print(f"  {marker} {j+1}: [{ind:2d}] {processed[j][:80]}")
            break

# Write output
content = '\n'.join(processed)
with open(INPUT, 'w', encoding='utf-8', newline='\n') as f:
    f.write(content)
print(f"Written to {INPUT}")
