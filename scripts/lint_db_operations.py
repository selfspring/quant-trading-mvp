"""
数据库操作 Linter
检查项目中是否存在绕过公共模块直接操作数据库的代码

检查规则：
1. 禁止直接 psycopg2.connect() — 应使用 db_engine/db_connection/get_db_connection
2. 禁止硬编码数据库密码
3. 禁止硬编码数据库连接参数（host/port/dbname）
"""
import os
import re
import sys
from pathlib import Path
from dataclasses import dataclass, field
from typing import List

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent

# 扫描目录（只扫描业务代码和脚本）
SCAN_DIRS = ['quant', 'scripts']

# 排除的文件（公共模块本身）
EXCLUDE_FILES = {
    'quant/common/db.py',
    'quant/common/db_pool.py',
    'quant/common/tracer.py',  # tracer 内部用 db_pool
    'scripts/lint_db_operations.py',  # 自身
}

# 排除的目录
EXCLUDE_DIRS = {'__pycache__', '.git', 'venv', '.venv'}


@dataclass
class Violation:
    file: str
    line: int
    rule: str
    severity: str  # Critical / High / Medium
    message: str
    suggestion: str


def check_file(filepath: Path, rel_path: str) -> List[Violation]:
    """检查单个文件"""
    violations = []

    try:
        content = filepath.read_text(encoding='utf-8')
    except (UnicodeDecodeError, PermissionError):
        return violations

    lines = content.splitlines()

    for i, line in enumerate(lines, 1):
        stripped = line.strip()

        # 跳过注释
        if stripped.startswith('#'):
            continue

        # 规则 1: 禁止直接 psycopg2.connect()
        if re.search(r'psycopg2\.connect\s*\(', line):
            violations.append(Violation(
                file=rel_path, line=i, rule='DB-001',
                severity='Critical',
                message=f'直接调用 psycopg2.connect()',
                suggestion='使用 from quant.common.db import db_engine, db_connection'
            ))

        # 规则 2: 禁止硬编码数据库密码
        if re.search(r"password\s*=\s*['\"](?!%)[^'\"]+['\"]", line) and 'connect' in content[max(0, content.find(line)-200):content.find(line)+len(line)]:
            # 排除 SecretStr 和 config 引用
            if 'SecretStr' not in line and 'config.' not in line and 'get_secret_value' not in line:
                violations.append(Violation(
                    file=rel_path, line=i, rule='DB-002',
                    severity='Critical',
                    message='疑似硬编码数据库密码',
                    suggestion='密码应通过 config.database.password (SecretStr) 管理'
                ))

        # 规则 3: 禁止硬编码连接参数
        if re.search(r"(host|dbname|database)\s*=\s*['\"]localhost['\"]", line):
            if 'config' not in line and 'default' not in line.lower():
                violations.append(Violation(
                    file=rel_path, line=i, rule='DB-003',
                    severity='High',
                    message='硬编码数据库连接参数',
                    suggestion='使用 from quant.common.config import config; config.database.host'
                ))

        # 规则 4: 禁止直接 import psycopg2（在非公共模块中）
        if re.search(r'^import psycopg2$', stripped) or re.search(r'^from psycopg2 import', stripped):
            # 允许在 db.py/db_pool.py 中 import
            violations.append(Violation(
                file=rel_path, line=i, rule='DB-004',
                severity='Medium',
                message='直接 import psycopg2（应通过公共模块间接使用）',
                suggestion='使用 from quant.common.db import db_engine 或 from quant.common.db_pool import get_db_connection'
            ))

        # 规则 5: 禁止 create_engine 直接调用（应通过 db.py）
        if re.search(r'create_engine\s*\(', line):
            violations.append(Violation(
                file=rel_path, line=i, rule='DB-005',
                severity='High',
                message='直接调用 create_engine()（应通过 db_engine 上下文管理器）',
                suggestion='使用 from quant.common.db import db_engine'
            ))

    return violations


def scan_project() -> List[Violation]:
    """扫描整个项目"""
    all_violations = []

    for scan_dir in SCAN_DIRS:
        dir_path = PROJECT_ROOT / scan_dir
        if not dir_path.exists():
            continue

        for filepath in dir_path.rglob('*.py'):
            rel_path = str(filepath.relative_to(PROJECT_ROOT)).replace('\\', '/')

            # 排除
            if rel_path in EXCLUDE_FILES:
                continue
            if any(d in filepath.parts for d in EXCLUDE_DIRS):
                continue

            violations = check_file(filepath, rel_path)
            all_violations.extend(violations)

    return all_violations


def print_report(violations: List[Violation]):
    """打印报告"""
    if not violations:
        print("✅ 数据库操作 Lint 检查通过，未发现违规")
        return

    # 按严重程度分组
    by_severity = {}
    for v in violations:
        by_severity.setdefault(v.severity, []).append(v)

    print(f"❌ 发现 {len(violations)} 个违规\n")

    for severity in ['Critical', 'High', 'Medium']:
        items = by_severity.get(severity, [])
        if not items:
            continue
        print(f"### {severity} ({len(items)})")
        for v in items:
            print(f"  [{v.rule}] {v.file}:{v.line}")
            print(f"    问题: {v.message}")
            print(f"    修复: {v.suggestion}")
            print()


def main():
    violations = scan_project()
    print_report(violations)
    # 有 Critical 时返回非零退出码
    critical = [v for v in violations if v.severity == 'Critical']
    return 1 if critical else 0


if __name__ == '__main__':
    sys.exit(main())
