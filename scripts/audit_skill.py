"""Skill 安全审查脚本 - 扫描 skill 目录中的可疑模式"""
import os
import sys
import re
from pathlib import Path

# 可疑模式定义
PATTERNS = {
    'env_access': {
        'desc': '读取环境变量/密码',
        'patterns': [r'os\.environ', r'dotenv', r'getenv', r'\.env', r'SECRET', r'PASSWORD', r'API_KEY', r'TOKEN'],
        'severity': 'HIGH'
    },
    'network': {
        'desc': '网络外发请求',
        'patterns': [r'requests\.', r'urllib', r'http\.client', r'httpx', r'aiohttp', r'socket\.', r'curl', r'wget'],
        'severity': 'HIGH'
    },
    'dynamic_exec': {
        'desc': '动态代码执行',
        'patterns': [r'\beval\s*\(', r'\bexec\s*\(', r'\bcompile\s*\(', r'__import__'],
        'severity': 'CRITICAL'
    },
    'subprocess': {
        'desc': '系统命令执行',
        'patterns': [r'subprocess', r'os\.system', r'Popen', r'os\.popen'],
        'severity': 'HIGH'
    },
    'file_ops': {
        'desc': '文件操作',
        'patterns': [r'shutil\.', r'os\.remove', r'os\.rename', r'os\.unlink', r'rmtree'],
        'severity': 'MEDIUM'
    },
    'encoding': {
        'desc': '编码/混淆',
        'patterns': [r'base64\.', r'codecs\.', r'rot13', r'zlib\.decompress'],
        'severity': 'HIGH'
    },
    'core_files': {
        'desc': '修改核心配置',
        'patterns': [r'AGENTS\.md', r'SOUL\.md', r'openclaw\.json', r'\.openclaw', r'config\.yaml'],
        'severity': 'CRITICAL'
    },
    'crypto': {
        'desc': '加密/钱包相关',
        'patterns': [r'private.?key', r'wallet', r'mnemonic', r'seed.?phrase', r'0x[a-fA-F0-9]{40}'],
        'severity': 'CRITICAL'
    }
}

# 扫描的文件扩展名
SCAN_EXTENSIONS = {'.py', '.sh', '.js', '.ts', '.md', '.yaml', '.yml', '.json', '.toml'}


def scan_file(filepath):
    """扫描单个文件"""
    findings = []
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
    except Exception as e:
        return [{'line': 0, 'category': 'error', 'desc': f'Cannot read: {e}', 'severity': 'UNKNOWN', 'text': ''}]

    for line_num, line in enumerate(lines, 1):
        for category, info in PATTERNS.items():
            for pattern in info['patterns']:
                if re.search(pattern, line, re.IGNORECASE):
                    findings.append({
                        'line': line_num,
                        'category': category,
                        'desc': info['desc'],
                        'severity': info['severity'],
                        'text': line.strip()[:120]
                    })
    return findings


def scan_directory(skill_dir):
    """扫描整个 skill 目录"""
    skill_path = Path(skill_dir)
    if not skill_path.exists():
        print(f"[ERROR] Directory not found: {skill_dir}")
        return 1

    print(f"=== Skill Security Audit ===")
    print(f"Target: {skill_path.resolve()}")
    print()

    all_findings = {}
    file_count = 0
    total_lines = 0

    for root, dirs, files in os.walk(skill_path):
        # 跳过隐藏目录和 node_modules
        dirs[:] = [d for d in dirs if not d.startswith('.') and d != 'node_modules']
        for fname in files:
            ext = Path(fname).suffix.lower()
            if ext not in SCAN_EXTENSIONS:
                continue
            filepath = os.path.join(root, fname)
            rel_path = os.path.relpath(filepath, skill_path)
            file_count += 1

            findings = scan_file(filepath)
            if findings:
                all_findings[rel_path] = findings

            try:
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    total_lines += sum(1 for _ in f)
            except:
                pass

    # 统计
    print(f"Scanned: {file_count} files, {total_lines} lines")
    print()

    if not all_findings:
        print("[PASS] No suspicious patterns found")
        return 0

    # 按严重程度排序输出
    severity_order = {'CRITICAL': 0, 'HIGH': 1, 'MEDIUM': 2, 'UNKNOWN': 3}
    critical_count = 0
    high_count = 0
    medium_count = 0

    for filepath, findings in sorted(all_findings.items()):
        print(f"--- {filepath} ---")
        for f in sorted(findings, key=lambda x: severity_order.get(x['severity'], 99)):
            icon = {'CRITICAL': '!!!', 'HIGH': '!! ', 'MEDIUM': '!  '}.get(f['severity'], '?  ')
            print(f"  [{icon}] L{f['line']:>4} [{f['severity']:<8}] {f['desc']}")
            print(f"         {f['text']}")

            if f['severity'] == 'CRITICAL':
                critical_count += 1
            elif f['severity'] == 'HIGH':
                high_count += 1
            elif f['severity'] == 'MEDIUM':
                medium_count += 1
        print()

    # 总结
    print("=== Summary ===")
    print(f"  CRITICAL: {critical_count}")
    print(f"  HIGH:     {high_count}")
    print(f"  MEDIUM:   {medium_count}")
    print()

    if critical_count > 0:
        print("[FAIL] CRITICAL issues found - DO NOT INSTALL without manual review")
        return 2
    elif high_count > 0:
        print("[WARN] HIGH risk patterns found - review before installing")
        return 1
    else:
        print("[INFO] Only MEDIUM findings - likely safe but verify")
        return 0


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(f"Usage: python {sys.argv[0]} <skill_directory>")
        print(f"Example: python {sys.argv[0]} ./temp_skills/quant-trading-cn")
        sys.exit(1)

    exit_code = scan_directory(sys.argv[1])
    sys.exit(exit_code)
