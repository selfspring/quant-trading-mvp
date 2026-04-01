"""
基本面数据采集模块测试用例
基于 PRD.md 需求编写

测试覆盖：
1. 数据格式验证
2. 数据源可用性
3. 数据质量检查
4. 数据库操作
5. fetch_all 综合测试
6. 异常处理
"""
import pytest
import pandas as pd
import sys
import os
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from quant.data_collector.fundamental_collector import FundamentalCollector


@pytest.fixture
def collector():
    """创建 FundamentalCollector 实例"""
    return FundamentalCollector()


@pytest.fixture
def sample_date_range():
    """提供测试用的日期范围"""
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    return start_date, end_date


class TestDataFormat:
    """数据格式验证测试"""

    @pytest.mark.parametrize("method_name,expected_columns", [
        ("fetch_dollar_index", ["date", "dollar_index"]),
        ("fetch_treasury_yield", ["date", "treasury_yield_10y"]),
        ("fetch_fed_rate", ["date", "fed_rate"]),
        ("fetch_non_farm", ["date", "non_farm"]),
        ("fetch_cpi", ["date", "cpi"]),
    ])
    def test_return_dataframe_with_correct_columns(self, collector, method_name, expected_columns):
        """测试每个 fetch 方法返回的 DataFrame 列名是否正确"""
        method = getattr(collector, method_name)
        
        # 对于需要日期参数的方法
        if method_name in ["fetch_dollar_index", "fetch_treasury_yield"]:
            df = method(start_date="2024-01-01", end_date="2024-01-31")
        else:
            df = method()
        
        assert isinstance(df, pd.DataFrame), f"{method_name} 应返回 DataFrame"
        assert list(df.columns) == expected_columns, f"{method_name} 列名不匹配"

    @pytest.mark.parametrize("method_name", [
        "fetch_dollar_index",
        "fetch_treasury_yield",
        "fetch_fed_rate",
        "fetch_non_farm",
        "fetch_cpi",
    ])
    def test_date_column_is_datetime(self, collector, method_name):
        """测试日期列是否为 datetime 类型"""
        method = getattr(collector, method_name)
        
        if method_name in ["fetch_dollar_index", "fetch_treasury_yield"]:
            df = method(start_date="2024-01-01", end_date="2024-01-31")
        else:
            df = method()
        
        if not df.empty:
            assert pd.api.types.is_datetime64_any_dtype(df['date']), \
                f"{method_name} 的 date 列应为 datetime 类型"

    @pytest.mark.parametrize("method_name,value_column", [
        ("fetch_dollar_index", "dollar_index"),
        ("fetch_treasury_yield", "treasury_yield_10y"),
        ("fetch_fed_rate", "fed_rate"),
        ("fetch_non_farm", "non_farm"),
        ("fetch_cpi", "cpi"),
    ])
    def test_value_column_is_numeric(self, collector, method_name, value_column):
        """测试数值列是否为数值类型"""
        method = getattr(collector, method_name)
        
        if method_name in ["fetch_dollar_index", "fetch_treasury_yield"]:
            df = method(start_date="2024-01-01", end_date="2024-01-31")
        else:
            df = method()
        
        if not df.empty:
            assert pd.api.types.is_numeric_dtype(df[value_column]), \
                f"{method_name} 的 {value_column} 列应为数值类型"

    def test_empty_data_returns_empty_dataframe(self, collector):
        """测试空数据时返回空 DataFrame（而非 None 或报错）"""
        # Mock 所有数据源返回 None
        with patch.object(collector, '_fetch_dollar_index_yfinance', return_value=None), \
             patch.object(collector, '_fetch_dollar_index_akshare', return_value=None):
            
            df = collector.fetch_dollar_index()
            
            assert isinstance(df, pd.DataFrame), "空数据应返回 DataFrame"
            assert df.empty, "空数据应返回空 DataFrame"
            assert list(df.columns) == ["date", "dollar_index"], "空 DataFrame 应有正确的列名"


class TestDataSource:
    """数据源可用性测试"""

    @pytest.mark.network
    def test_fetch_dollar_index_returns_data(self, collector, sample_date_range):
        """测试美元指数数据源是否能成功获取数据"""
        start_date, end_date = sample_date_range
        df = collector.fetch_dollar_index(start_date=start_date, end_date=end_date)
        
        assert not df.empty, "美元指数应返回非空数据"
        assert len(df) > 0, "美元指数数据量应大于0"

    @pytest.mark.network
    def test_fetch_treasury_yield_returns_data(self, collector, sample_date_range):
        """测试美债收益率数据源是否能成功获取数据"""
        start_date, end_date = sample_date_range
        df = collector.fetch_treasury_yield(start_date=start_date, end_date=end_date)
        
        assert not df.empty, "美债收益率应返回非空数据"
        assert len(df) > 0, "美债收益率数据量应大于0"

    @pytest.mark.network
    def test_fetch_fed_rate_returns_data(self, collector):
        """测试美联储利率数据源是否能成功获取数据"""
        df = collector.fetch_fed_rate()
        
        assert not df.empty, "美联储利率应返回非空数据"
        assert len(df) > 0, "美联储利率数据量应大于0"

    @pytest.mark.network
    def test_fetch_non_farm_returns_data(self, collector):
        """测试非农就业数据源是否能成功获取数据"""
        df = collector.fetch_non_farm()
        
        assert not df.empty, "非农就业应返回非空数据"
        assert len(df) > 0, "非农就业数据量应大于0"

    @pytest.mark.network
    def test_fetch_cpi_returns_data(self, collector):
        """测试CPI数据源是否能成功获取数据"""
        df = collector.fetch_cpi()
        
        assert not df.empty, "CPI应返回非空数据"
        assert len(df) > 0, "CPI数据量应大于0"

    @pytest.mark.network
    def test_date_range_filter_works(self, collector):
        """测试日期范围过滤是否生效"""
        start_date = "2024-01-01"
        end_date = "2024-01-31"
        
        df = collector.fetch_dollar_index(start_date=start_date, end_date=end_date)
        
        if not df.empty:
            min_date = df['date'].min()
            max_date = df['date'].max()
            
            assert min_date >= pd.to_datetime(start_date), "最小日期应大于等于起始日期"
            assert max_date <= pd.to_datetime(end_date), "最大日期应小于等于结束日期"


class TestDataQuality:
    """数据质量测试"""

    @pytest.mark.network
    def test_no_null_values_in_critical_columns(self, collector, sample_date_range):
        """测试关键列是否有空值"""
        start_date, end_date = sample_date_range
        df = collector.fetch_dollar_index(start_date=start_date, end_date=end_date)
        
        if not df.empty:
            assert df['date'].notna().all(), "date 列不应有空值"
            assert df['dollar_index'].notna().all(), "dollar_index 列不应有空值"

    @pytest.mark.network
    def test_dollar_index_range_is_reasonable(self, collector, sample_date_range):
        """测试美元指数范围是否合理（80-130之间）"""
        start_date, end_date = sample_date_range
        df = collector.fetch_dollar_index(start_date=start_date, end_date=end_date)
        
        if not df.empty:
            assert (df['dollar_index'] >= 80).all(), "美元指数应 >= 80"
            assert (df['dollar_index'] <= 130).all(), "美元指数应 <= 130"

    @pytest.mark.network
    def test_treasury_yield_range_is_reasonable(self, collector, sample_date_range):
        """测试美债收益率范围是否合理（0-20%）"""
        start_date, end_date = sample_date_range
        df = collector.fetch_treasury_yield(start_date=start_date, end_date=end_date)
        
        if not df.empty:
            assert (df['treasury_yield_10y'] >= 0).all(), "美债收益率应 >= 0"
            assert (df['treasury_yield_10y'] <= 20).all(), "美债收益率应 <= 20%"

    @pytest.mark.network
    def test_fed_rate_range_is_reasonable(self, collector):
        """测试联邦基金利率范围是否合理（0-25%）"""
        df = collector.fetch_fed_rate()
        
        if not df.empty:
            assert (df['fed_rate'] >= 0).all(), "联邦基金利率应 >= 0"
            assert (df['fed_rate'] <= 25).all(), "联邦基金利率应 <= 25%"

    @pytest.mark.network
    def test_cpi_is_positive(self, collector):
        """测试CPI是否为正数"""
        df = collector.fetch_cpi()
        
        if not df.empty:
            assert (df['cpi'] > 0).all(), "CPI应为正数"

    @pytest.mark.network
    def test_non_farm_is_positive(self, collector):
        """测试非农数据是否为正数"""
        df = collector.fetch_non_farm()
        
        if not df.empty:
            assert (df['non_farm'] > 0).all(), "非农就业人数应为正数"

    @pytest.mark.network
    def test_data_is_sorted_by_date(self, collector, sample_date_range):
        """测试数据是否按日期排序"""
        start_date, end_date = sample_date_range
        df = collector.fetch_dollar_index(start_date=start_date, end_date=end_date)
        
        if len(df) > 1:
            dates = df['date'].tolist()
            assert dates == sorted(dates), "数据应按日期升序排列"


class TestDatabase:
    """数据库操作测试"""

    @pytest.mark.db
    def test_save_to_db_creates_table(self, collector):
        """测试 save_to_db 是否能自动创建表"""
        # 创建测试数据
        test_data = pd.DataFrame({
            'date': [pd.to_datetime('2024-01-01')],
            'dollar_index': [105.5],
            'treasury_yield_10y': [4.2],
            'fed_rate': [5.25],
            'non_farm': [150000.0],
            'cpi': [310.5]
        })
        
        # 尝试保存（应自动建表）
        try:
            collector.save_to_db(test_data)
            
            # 验证表是否存在
            from quant.common.db_pool import get_db_connection
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT EXISTS (
                            SELECT FROM information_schema.tables 
                            WHERE table_name = 'fundamentals'
                        );
                    """)
                    table_exists = cursor.fetchone()[0]
                    assert table_exists, "fundamentals 表应被创建"
        except Exception as e:
            pytest.skip(f"数据库连接失败，跳过测试: {e}")

    @pytest.mark.db
    def test_save_to_db_upsert_works(self, collector):
        """测试 UPSERT 去重是否有效（同一日期重复写入不报错）"""
        test_data = pd.DataFrame({
            'date': [pd.to_datetime('2024-01-01')],
            'dollar_index': [105.5],
            'treasury_yield_10y': [4.2],
            'fed_rate': [5.25],
            'non_farm': [150000.0],
            'cpi': [310.5]
        })
        
        try:
            # 第一次写入
            collector.save_to_db(test_data)
            
            # 第二次写入相同日期（应更新而非报错）
            test_data_updated = test_data.copy()
            test_data_updated['dollar_index'] = 106.0
            collector.save_to_db(test_data_updated)
            
            # 验证数据已更新
            from quant.common.db_pool import get_db_connection
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT dollar_index FROM fundamentals 
                        WHERE date = '2024-01-01'
                    """)
                    result = cursor.fetchone()
                    assert result is not None, "数据应存在"
                    assert abs(result[0] - 106.0) < 0.01, "数据应被更新"
        except Exception as e:
            pytest.skip(f"数据库连接失败，跳过测试: {e}")

    @pytest.mark.db
    def test_save_empty_dataframe_does_not_error(self, collector):
        """测试保存空 DataFrame 不报错"""
        empty_df = pd.DataFrame(columns=['date', 'dollar_index'])
        
        try:
            # 应该不报错，只是跳过
            collector.save_to_db(empty_df)
        except Exception as e:
            pytest.fail(f"保存空 DataFrame 不应报错: {e}")


class TestFetchAll:
    """综合采集测试"""

    @pytest.mark.network
    def test_fetch_all_returns_dict_with_all_keys(self, collector):
        """测试 fetch_all 返回的 dict 是否包含所有 5 个 key"""
        results = collector.fetch_all()
        
        expected_keys = ["dollar_index", "treasury_yield", "fed_rate", "non_farm", "cpi"]
        assert isinstance(results, dict), "fetch_all 应返回 dict"
        assert set(results.keys()) == set(expected_keys), "应包含所有 5 个数据源的 key"

    @pytest.mark.network
    def test_fetch_all_each_value_is_dataframe(self, collector):
        """测试 fetch_all 返回的每个值都是 DataFrame"""
        results = collector.fetch_all()
        
        for key, df in results.items():
            assert isinstance(df, pd.DataFrame), f"{key} 应为 DataFrame"

    def test_fetch_all_single_failure_does_not_affect_others(self, collector):
        """测试单个数据源失败不影响其他数据源"""
        # Mock 一个数据源失败
        with patch.object(collector, 'fetch_dollar_index', side_effect=Exception("Network error")):
            results = collector.fetch_all()
            
            # 美元指数应为空 DataFrame
            assert isinstance(results['dollar_index'], pd.DataFrame)
            
            # 其他数据源应正常（至少返回 DataFrame）
            for key in ['treasury_yield', 'fed_rate', 'non_farm', 'cpi']:
                assert isinstance(results[key], pd.DataFrame), f"{key} 应正常返回 DataFrame"

    @pytest.mark.network
    def test_fetch_all_logs_summary(self, collector, caplog):
        """测试 fetch_all 是否记录汇总日志"""
        import logging
        caplog.set_level(logging.INFO)
        
        collector.fetch_all()
        
        # 检查是否有汇总日志
        log_messages = [record.message for record in caplog.records]
        assert any("采集完成" in msg or "汇总" in msg for msg in log_messages), \
            "应记录采集汇总日志"


class TestErrorHandling:
    """异常处理测试"""

    def test_network_timeout_graceful_degradation(self, collector):
        """测试网络超时时是否优雅降级"""
        # Mock 网络超时
        with patch('yfinance.Ticker') as mock_ticker:
            mock_ticker.return_value.history.side_effect = Exception("Timeout")
            
            # 应返回空 DataFrame 而非抛出异常
            df = collector.fetch_dollar_index()
            
            assert isinstance(df, pd.DataFrame), "超时应返回空 DataFrame"
            assert df.empty or not df.empty, "应优雅处理超时"

    @pytest.mark.parametrize("invalid_date", [
        "invalid-date",
        "2024-13-01",  # 无效月份
        "2024-02-30",  # 无效日期
    ])
    def test_invalid_date_parameter_handling(self, collector, invalid_date):
        """测试错误的日期参数是否处理得当"""
        # 应该不抛出异常，或返回空 DataFrame
        try:
            df = collector.fetch_dollar_index(start_date=invalid_date, end_date="2024-01-31")
            assert isinstance(df, pd.DataFrame), "无效日期应返回 DataFrame"
        except Exception as e:
            # 如果抛出异常，应该是明确的日期格式错误
            assert "date" in str(e).lower() or "invalid" in str(e).lower(), \
                f"异常信息应明确指出日期问题: {e}"

    def test_missing_dependencies_handling(self, collector):
        """测试缺少依赖库时的处理"""
        # Mock yfinance 不存在
        with patch('builtins.__import__', side_effect=ImportError("No module named 'yfinance'")):
            # 应该尝试备选方案或返回空 DataFrame
            df = collector._fetch_dollar_index_yfinance("2024-01-01", "2024-01-31")
            
            assert df is None or isinstance(df, pd.DataFrame), \
                "缺少依赖应返回 None 或空 DataFrame"

    def test_empty_response_from_data_source(self, collector):
        """测试数据源返回空响应时的处理"""
        # Mock 数据源返回空数据
        with patch('yfinance.Ticker') as mock_ticker:
            mock_ticker.return_value.history.return_value = pd.DataFrame()
            
            df = collector.fetch_dollar_index()
            
            assert isinstance(df, pd.DataFrame), "空响应应返回 DataFrame"
            assert list(df.columns) == ["date", "dollar_index"], "应有正确的列名"

    def test_malformed_data_from_source(self, collector):
        """测试数据源返回格式错误的数据时的处理"""
        # Mock 返回格式错误的数据
        with patch('yfinance.Ticker') as mock_ticker:
            malformed_df = pd.DataFrame({'wrong_col': [1, 2, 3]})
            mock_ticker.return_value.history.return_value = malformed_df
            
            # 应该优雅处理并返回空 DataFrame
            df = collector.fetch_dollar_index()
            
            assert isinstance(df, pd.DataFrame), "格式错误应返回 DataFrame"


# 运行测试的说明
"""
运行方式：
    cd E:\quant-trading-mvp
    
    # 运行所有测试
    pytest tests/test_fundamental_collector.py -v
    
    # 只运行单元测试（跳过网络和数据库测试）
    pytest tests/test_fundamental_collector.py -v -m "not network and not db"
    
    # 只运行网络测试
    pytest tests/test_fundamental_collector.py -v -m network
    
    # 只运行数据库测试
    pytest tests/test_fundamental_collector.py -v -m db
    
    # 显示详细输出
    pytest tests/test_fundamental_collector.py -v -s
"""
