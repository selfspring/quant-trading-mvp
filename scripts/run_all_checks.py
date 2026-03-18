"""
统一运行脚本 - 按顺序运行所有检查

运行方式: python scripts/run_all_checks.py
"""
import subprocess
import sys
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent


def run_check(name, cmd):
    """运行单个检查，返回 (name, passed, output)"""
    print(f"\n{'=' * 60}")
    print(f"  {name}")
    print(f"{'=' * 60}")
    try:
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        result = subprocess.run(
            cmd,
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
            env=env,
        )
        output = result.stdout + result.stderr
        print(output)
        return (name, result.returncode == 0, output)
    except subprocess.TimeoutExpired:
        msg = f"  [TIMEOUT] {name} 超时 (120s)"
        print(msg)
        return (name, False, msg)
    except Exception as e:
        msg = f"  [ERROR] {name} 执行失败: {e}"
        print(msg)
        return (name, False, msg)


def main():
    print("=" * 60)
    print("  运行所有检查")
    print("=" * 60)

    python = sys.executable
    results = []

    # 1. 风控规则 Linter
    results.append(run_check(
        "风控规则 Linter",
        [python, str(PROJECT_ROOT / "scripts" / "lint_risk_rules.py")]
    ))

    # 2. 特征一致性 Linter
    results.append(run_check(
        "特征一致性 Linter",
        [python, str(PROJECT_ROOT / "scripts" / "lint_feature_consistency.py")]
    ))

    # 3. pytest 单元测试
    results.append(run_check(
        "单元测试 (pytest)",
        [python, "-m", "pytest", str(PROJECT_ROOT / "tests" / "unit"), "-v", "--tb=short"]
    ))

    # 汇总
    print("\n" + "=" * 60)
    print("  汇总结果")
    print("=" * 60)

    passed = sum(1 for _, ok, _ in results if ok)
    failed = sum(1 for _, ok, _ in results if not ok)
    total = len(results)

    for name, ok, _ in results:
        status = "PASS" if ok else "FAIL"
        print(f"  [{status}] {name}")

    print(f"\n  通过: {passed}/{total}  失败: {failed}/{total}")

    if failed > 0:
        print("\n  有检查未通过，请修复后重试。")
        sys.exit(1)
    else:
        print("\n  所有检查通过!")
        sys.exit(0)


if __name__ == "__main__":
    main()
