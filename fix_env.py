import sys
data = open('.env', 'rb').read()

# Try different decodings
for enc in ['utf-8', 'utf-16-le', 'utf-16', 'gbk', 'latin-1']:
    try:
        text = data.decode(enc)
        text = text.replace('\ufeff', '')  # remove BOM
        if 'BROKER' in text or 'CTP' in text:
            print(f"Decoded with: {enc}")
            # Fix symbol
            text = text.replace('au2604', 'au2606')
            # Write back as UTF-8
            with open('.env', 'w', encoding='utf-8', newline='\n') as f:
                f.write(text)
            print("Fixed and saved.")
            # Verify
            with open('.env', 'r', encoding='utf-8') as f:
                content = f.read()
            for line in content.strip().split('\n'):
                print(f"  {line}")
            break
    except:
        continue
