"""
新闻数据采集模块测试脚本
测试 NewsCollector 的各数据源是否可用

测试项:
  1. 金十数据快讯     - fetch_jin10
  2. 新浪财经新闻     - fetch_sina_finance
  3. RSS 聚合新闻     - fetch_rss
  4. 东方财富新闻     - fetch_eastmoney
  5. 综合采集         - fetch_all
"""
import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
os.environ['PYTHONIOENCODING'] = 'utf-8'

import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

from quant.data_collector.news_collector import NewsCollector


def _section(title: str):
    """打印分隔栏"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def _preview_news(news_list, max_items=3):
    """预览前 N 条新闻标题"""
    if not news_list:
        print("  (无数据)")
        return
    for i, n in enumerate(news_list[:max_items]):
        title = n.get('title') or n.get('content', '')[:60]
        dt = n.get('datetime', '')
        source = n.get('source', '')
        print(f"    [{i+1}] [{dt}] {title[:70]}")


def test_all():
    collector = NewsCollector(request_interval=2.0)
    results = {}
    timings = {}
    counts = {}

    # ------------------------------------------------------------------
    # 测试1: 金十数据
    # ------------------------------------------------------------------
    _section("测试1: 金十数据快讯 (jin10)")
    try:
        t0 = time.time()
        news = collector.fetch_jin10()
        elapsed = time.time() - t0
        timings['jin10'] = elapsed
        count = len(news)
        counts['jin10'] = count
        ok = count > 0
        print(f"  状态: {'✅ 成功' if ok else '⚠️ 空数据'}")
        print(f"  新闻数量: {count}")
        print(f"  耗时: {elapsed:.2f}s")
        if ok:
            print(f"  前3条预览:")
            _preview_news(news)
            # 显示分类分布
            categories = {}
            for n in news:
                cat = n.get('category', 'unknown')
                categories[cat] = categories.get(cat, 0) + 1
            print(f"  分类分布: {categories}")
        results['jin10'] = '✅' if ok else '❌'
    except Exception as e:
        print(f"  ❌ 失败: {e}")
        results['jin10'] = '❌'
        counts['jin10'] = 0

    # ------------------------------------------------------------------
    # 测试2: 新浪财经
    # ------------------------------------------------------------------
    _section("测试2: 新浪财经新闻 (sina)")
    try:
        t0 = time.time()
        news = collector.fetch_sina_finance()
        elapsed = time.time() - t0
        timings['sina'] = elapsed
        count = len(news)
        counts['sina'] = count
        ok = count > 0
        print(f"  状态: {'✅ 成功' if ok else '⚠️ 空数据'}")
        print(f"  新闻数量: {count} (关键词过滤后)")
        print(f"  耗时: {elapsed:.2f}s")
        if ok:
            print(f"  前3条预览:")
            _preview_news(news)
        results['sina'] = '✅' if ok else '❌'
    except Exception as e:
        print(f"  ❌ 失败: {e}")
        results['sina'] = '❌'
        counts['sina'] = 0

    # ------------------------------------------------------------------
    # 测试3: RSS 聚合
    # ------------------------------------------------------------------
    _section("测试3: RSS 聚合新闻 (Google News / Investing.com)")
    try:
        t0 = time.time()
        news = collector.fetch_rss()
        elapsed = time.time() - t0
        timings['rss'] = elapsed
        count = len(news)
        counts['rss'] = count
        ok = count > 0
        print(f"  状态: {'✅ 成功' if ok else '⚠️ 空数据'}")
        print(f"  新闻数量: {count}")
        print(f"  耗时: {elapsed:.2f}s")
        if ok:
            print(f"  前3条预览:")
            _preview_news(news)
            # 显示各 feed 来源分布
            feeds = {}
            for n in news:
                fname = n.get('feed_name', 'unknown')
                feeds[fname] = feeds.get(fname, 0) + 1
            print(f"  Feed 分布: {feeds}")
        results['rss'] = '✅' if ok else '❌'
    except Exception as e:
        print(f"  ❌ 失败: {e}")
        results['rss'] = '❌'
        counts['rss'] = 0

    # ------------------------------------------------------------------
    # 测试4: 东方财富
    # ------------------------------------------------------------------
    _section("测试4: 东方财富新闻 (eastmoney)")
    try:
        t0 = time.time()
        news = collector.fetch_eastmoney()
        elapsed = time.time() - t0
        timings['eastmoney'] = elapsed
        count = len(news)
        counts['eastmoney'] = count
        ok = count > 0
        print(f"  状态: {'✅ 成功' if ok else '⚠️ 空数据'}")
        print(f"  新闻数量: {count} (关键词过滤后)")
        print(f"  耗时: {elapsed:.2f}s")
        if ok:
            print(f"  前3条预览:")
            _preview_news(news)
        results['eastmoney'] = '✅' if ok else '❌'
    except Exception as e:
        print(f"  ❌ 失败: {e}")
        results['eastmoney'] = '❌'
        counts['eastmoney'] = 0

    # ------------------------------------------------------------------
    # 测试5: fetch_all 综合采集
    # ------------------------------------------------------------------
    _section("测试5: fetch_all 综合采集")
    try:
        t0 = time.time()
        all_news = collector.fetch_all()
        elapsed = time.time() - t0
        timings['fetch_all'] = elapsed
        count = len(all_news)
        counts['fetch_all'] = count
        ok = count > 0
        print(f"  状态: {'✅ 成功' if ok else '⚠️ 空数据'}")
        print(f"  总新闻数量: {count}")
        print(f"  耗时: {elapsed:.2f}s")
        if ok:
            # 按来源分组统计
            by_source = {}
            for n in all_news:
                src = n.get('source', 'unknown')
                by_source[src] = by_source.get(src, 0) + 1
            print(f"  各来源分布:")
            for src, cnt in sorted(by_source.items()):
                print(f"    {src}: {cnt} 条")
            print(f"  前3条预览:")
            _preview_news(all_news)
        results['fetch_all'] = '✅' if ok else '❌'
    except Exception as e:
        print(f"  ❌ 失败: {e}")
        results['fetch_all'] = '❌'
        counts['fetch_all'] = 0

    # ------------------------------------------------------------------
    # 汇总
    # ------------------------------------------------------------------
    _section("测试结果汇总")
    print(f"  {'数据源':<15} {'状态':<6} {'数量':>6}  {'耗时':>8}")
    print(f"  {'-'*15} {'-'*6} {'-'*6}  {'-'*8}")
    for name in ['jin10', 'sina', 'rss', 'eastmoney', 'fetch_all']:
        status = results.get(name, '❌')
        cnt = counts.get(name, 0)
        timing_str = f"{timings.get(name, 0):.1f}s" if name in timings else "-"
        print(f"  {name:<15} {status:<6} {cnt:>6}  {timing_str:>8}")

    passed = sum(1 for v in results.values() if v == '✅')
    total = len(results)
    total_news = sum(counts.get(k, 0) for k in ['jin10', 'sina', 'rss', 'eastmoney'])
    total_time = sum(timings.values())

    print(f"\n  通过: {passed}/{total}")
    print(f"  总采集新闻数 (不含 fetch_all): {total_news}")
    print(f"  总耗时: {total_time:.1f}s")

    if passed == total:
        print("\n  🎉 全部测试通过！所有新闻数据源可用。")
    elif passed > 0:
        print(f"\n  ⚠️ 部分测试通过 ({passed}/{total})，请检查失败项。")
        print("  提示: RSS 需要安装 feedparser (pip install feedparser)")
        print("  提示: 部分数据源可能需要网络代理")
    else:
        print("\n  ❌ 全部测试失败，请检查网络连接和依赖库安装。")

    return results


if __name__ == '__main__':
    test_all()
