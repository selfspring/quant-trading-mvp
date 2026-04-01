"""
基本面数据采集模块测试脚本
测试 FundamentalCollector 的各数据源是否可用

测试项:
  1. 美元指数 (Dollar Index) - fetch_dollar_index
  2. 10年期美债收益率       - fetch_treasury_yield
  3. 美联储基准利率         - fetch_fed_rate
  4. 非农就业数据           - fetch_non_farm
  5. CPI通胀数据            - fetch_cpi
  6. 综合采集               - fetch_all
"""
import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
os.environ['PYTHONIOENCODING'] = 'utf-8'

import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

from quant.data_collector.fundamental_collector import FundamentalCollector


def _section(title: str):
    """打印分隔栏"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def test_all():
    collector = FundamentalCollector()
    results = {}
    timings = {}

    # ------------------------------------------------------------------
    # 测试1: 美元指数
    # ------------------------------------------------------------------
    _section("测试1: 美元指数 (Dollar Index)")
    try:
        t0 = time.time()
        df = collector.fetch_dollar_index(start_date="2025-01-01", end_date="2025-12-31")
        elapsed = time.time() - t0
        timings['dollar_index'] = elapsed
        ok = len(df) > 0
        print(f"  状态: {'成功' if ok else '空数据'}")
        print(f"  记录数: {len(df)}")
        print(f"  耗时: {elapsed:.2f}s")
        if ok:
            print(f"  列名: {list(df.columns)}")
            print(f"  日期范围: {df['date'].min()} ~ {df['date'].max()}")
            print(f"  最新值: {df['dollar_index'].iloc[-1]:.2f}")
        results['dollar_index'] = '✅' if ok else '❌'
    except Exception as e:
        print(f"  失败: {e}")
        results['dollar_index'] = '❌'

    # ------------------------------------------------------------------
    # 测试2: 美债收益率
    # ------------------------------------------------------------------
    _section("测试2: 10年期美债收益率")
    try:
        t0 = time.time()
        df = collector.fetch_treasury_yield(start_date="2025-01-01", end_date="2025-12-31")
        elapsed = time.time() - t0
        timings['treasury_yield'] = elapsed
        ok = len(df) > 0
        print(f"  状态: {'成功' if ok else '空数据'}")
        print(f"  记录数: {len(df)}")
        print(f"  耗时: {elapsed:.2f}s")
        if ok:
            print(f"  列名: {list(df.columns)}")
            print(f"  日期范围: {df['date'].min()} ~ {df['date'].max()}")
            print(f"  最新值: {df['treasury_yield_10y'].iloc[-1]:.2f}%")
        results['treasury_yield'] = '✅' if ok else '❌'
    except Exception as e:
        print(f"  失败: {e}")
        results['treasury_yield'] = '❌'

    # ------------------------------------------------------------------
    # 测试3: 美联储利率
    # ------------------------------------------------------------------
    _section("测试3: 美联储基准利率")
    try:
        t0 = time.time()
        df = collector.fetch_fed_rate()
        elapsed = time.time() - t0
        timings['fed_rate'] = elapsed
        ok = len(df) > 0
        print(f"  状态: {'成功' if ok else '空数据'}")
        print(f"  记录数: {len(df)}")
        print(f"  耗时: {elapsed:.2f}s")
        if ok:
            print(f"  列名: {list(df.columns)}")
            print(f"  日期范围: {df['date'].min()} ~ {df['date'].max()}")
            print(f"  最新值: {df['fed_rate'].iloc[-1]:.2f}%")
        results['fed_rate'] = '✅' if ok else '❌'
    except Exception as e:
        print(f"  失败: {e}")
        results['fed_rate'] = '❌'

    # ------------------------------------------------------------------
    # 测试4: 非农
    # ------------------------------------------------------------------
    _section("测试4: 非农就业数据")
    try:
        t0 = time.time()
        df = collector.fetch_non_farm()
        elapsed = time.time() - t0
        timings['non_farm'] = elapsed
        ok = len(df) > 0
        print(f"  状态: {'成功' if ok else '空数据'}")
        print(f"  记录数: {len(df)}")
        print(f"  耗时: {elapsed:.2f}s")
        if ok:
            print(f"  列名: {list(df.columns)}")
            print(f"  日期范围: {df['date'].min()} ~ {df['date'].max()}")
            print(f"  最新值: {df['non_farm'].iloc[-1]:.0f}")
        results['non_farm'] = '✅' if ok else '❌'
    except Exception as e:
        print(f"  失败: {e}")
        results['non_farm'] = '❌'

    # ------------------------------------------------------------------
    # 测试5: CPI
    # ------------------------------------------------------------------
    _section("测试5: CPI通胀数据")
    try:
        t0 = time.time()
        df = collector.fetch_cpi()
        elapsed = time.time() - t0
        timings['cpi'] = elapsed
        ok = len(df) > 0
        print(f"  状态: {'成功' if ok else '空数据'}")
        print(f"  记录数: {len(df)}")
        print(f"  耗时: {elapsed:.2f}s")
        if ok:
            print(f"  列名: {list(df.columns)}")
            print(f"  日期范围: {df['date'].min()} ~ {df['date'].max()}")
            print(f"  最新值: {df['cpi'].iloc[-1]:.2f}")
        results['cpi'] = '✅' if ok else '❌'
    except Exception as e:
        print(f"  失败: {e}")
        results['cpi'] = '❌'

    # ------------------------------------------------------------------
    # 测试6: fetch_all 综合采集
    # ------------------------------------------------------------------
    _section("测试6: fetch_all 综合采集")
    try:
        t0 = time.time()
        all_data = collector.fetch_all()
        elapsed = time.time() - t0
        timings['fetch_all'] = elapsed
        print(f"  耗时: {elapsed:.2f}s")
        print(f"  返回类型: {type(all_data).__name__}")
        print(f"  包含的 key: {list(all_data.keys())}")
        all_ok = True
        for key, df in all_data.items():
            count = len(df) if df is not None else 0
            status = '✅' if count > 0 else '❌'
            print(f"    {key}: {count} 条 {status}")
            if count == 0:
                all_ok = False
        results['fetch_all'] = '✅' if all_ok else '⚠️'
    except Exception as e:
        print(f"  失败: {e}")
        results['fetch_all'] = '❌'

    # ------------------------------------------------------------------
    # 汇总
    # ------------------------------------------------------------------
    _section("测试结果汇总")
    for name, status in results.items():
        timing_str = f" ({timings.get(name, 0):.1f}s)" if name in timings else ""
        print(f"  {name}: {status}{timing_str}")

    passed = sum(1 for v in results.values() if v == '✅')
    total = len(results)
    print(f"\n  通过: {passed}/{total}")
    total_time = sum(timings.values())
    print(f"  总耗时: {total_time:.1f}s")

    if passed == total:
        print("\n  🎉 全部测试通过！所有数据源可用。")
    elif passed > 0:
        print(f"\n  ⚠️ 部分测试通过 ({passed}/{total})，请检查失败项。")
    else:
        print("\n  ❌ 全部测试失败，请检查网络连接和依赖库安装。")

    return results


if __name__ == '__main__':
    test_all()
