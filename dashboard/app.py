# -*- coding: utf-8 -*-
"""
量化交易系统 Streamlit Dashboard
包含 6 个页面：行情&特征、模型状态、因子实验室、持仓&风控、订单执行、审计日志
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import psycopg2
import json
from datetime import datetime
import os
from dotenv import load_dotenv

# ==================== 加载配置 ====================
# 从 .env 文件加载数据库配置（相对路径兼容不同机器）
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(_BASE_DIR, '.env'))

def get_db_config():
    """从环境变量获取数据库配置"""
    return {
        'host': os.getenv('DATABASE__HOST', 'localhost'),
        'port': int(os.getenv('DATABASE__PORT', 5432)),
        'database': os.getenv('DATABASE__DATABASE', 'quant_trading'),
        'user': os.getenv('DATABASE__USER', 'postgres'),
        'password': os.getenv('DATABASE__PASSWORD', '')
    }

# 因子发现数据文件路径（相对路径）
FACTOR_LOG_PATH = os.path.join(_BASE_DIR, 'data', 'factor_discovery_log.jsonl')

# ==================== 数据库连接函数 ====================
def get_db_connection():
    """获取数据库连接"""
    try:
        config = get_db_config()
        conn = psycopg2.connect(**config)
        return conn
    except Exception as e:
        st.error(f"数据库连接失败：{str(e)}")
        return None

@st.cache_data(ttl=60)  # 缓存60秒，避免每次切页重复查询
def query_to_df(query, params=None):
    """执行 SQL 查询并返回 DataFrame"""
    conn = get_db_connection()
    if conn is None:
        return None
    try:
        df = pd.read_sql_query(query, conn, params=params)
        return df
    except Exception as e:
        st.error(f"查询失败：{str(e)}")
        return None
    finally:
        conn.close()

# ==================== 页面渲染函数 ====================

def render_行情特征():
    """页面 1: 行情 & 特征"""
    st.header("📊 行情 & 特征")
    st.caption(f"最后更新时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # K 线图 - au2606 30m 最近 200 根
    st.subheader("K 线图 (au2606 30m)")
    
    kline_query = """
        SELECT time, open, high, low, close, volume, open_interest
        FROM kline_data
        WHERE symbol = 'au2606' AND interval = '30m'
        ORDER BY time DESC
        LIMIT 200
    """
    
    kline_df = query_to_df(kline_query)
    
    if kline_df is not None and len(kline_df) > 0:
        # 反转数据以便按时间正序显示
        kline_df = kline_df.iloc[::-1].reset_index(drop=True)
        
        # 创建 K 线图
        fig = go.Figure()
        
        fig.add_trace(go.Candlestick(
            x=kline_df['time'],
            open=kline_df['open'],
            high=kline_df['high'],
            low=kline_df['low'],
            close=kline_df['close'],
            name='K 线'
        ))
        
        fig.update_layout(
            title='au2606 30 分钟 K 线图 (最近 200 根)',
            xaxis_title='时间',
            yaxis_title='价格',
            xaxis_rangeslider_visible=False,
            height=600
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # 显示最新特征值
        st.subheader("最新特征值")
        latest = kline_df.iloc[-1]
        
        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("最新收盘价", f"{latest['close']:.2f}")
        col2.metric("24h 成交量", f"{latest['volume']:.0f}")
        col3.metric("持仓量", f"{latest['open_interest']:.0f}")
        col4.metric("最高价", f"{latest['high']:.2f}")
        col5.metric("最低价", f"{latest['low']:.2f}")
        
        # 显示原始数据
        with st.expander("查看原始数据"):
            st.dataframe(kline_df.tail(10))
    else:
        st.info("暂无 K 线数据")

def render_模型状态():
    """页面 2: 模型状态"""
    st.header("🤖 模型状态")
    st.caption(f"最后更新时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 从 ml_predictions 表读取
    pred_query = """
        SELECT * FROM ml_predictions
        ORDER BY time DESC
        LIMIT 10
    """
    
    pred_df = query_to_df(pred_query)
    
    if pred_df is not None and len(pred_df) > 0:
        st.subheader("最新 ML 预测")
        
        # 显示最新预测
        latest_pred = pred_df.iloc[0]
        
        col1, col2, col3 = st.columns(3)
        
        # 根据实际表结构调整
        if 'predicted_return' in pred_df.columns:
            col1.metric("预测值", f"{latest_pred['predicted_return']:.4f}")
        else:
            col1.metric("预测值", "N/A")
            
        if 'confidence' in pred_df.columns:
            col2.metric("置信度", f"{latest_pred['confidence']:.2%}")
        else:
            col2.metric("置信度", "N/A")
        
        # ml_predictions 表没有 signal_direction 字段
        col3.metric("信号方向", "N/A")
        
        # 显示预测历史
        st.subheader("预测历史")
        st.dataframe(pred_df)
    else:
        st.info("暂无 ML 预测数据")

def render_因子实验室():
    """页面 3: 因子实验室"""
    st.header("🧪 因子实验室")
    st.caption(f"最后更新时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 读取 factor_discovery_log.jsonl
    if not os.path.exists(FACTOR_LOG_PATH):
        st.error(f"因子发现日志文件不存在：{FACTOR_LOG_PATH}")
        return
    
    factors = []
    try:
        with open(FACTOR_LOG_PATH, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    factors.append(json.loads(line))
    except Exception as e:
        st.error(f"读取因子日志失败：{str(e)}")
        return
    
    if len(factors) == 0:
        st.info("暂无因子测试数据")
        return
    
    # 转换为 DataFrame
    df = pd.DataFrame(factors)
    
    # 总测试数
    total_tests = len(df)
    
    # 有效数 (假设 effective 字段标记是否有效)
    if 'effective' in df.columns:
        effective_count = df['effective'].sum() if df['effective'].dtype == bool else (df['effective'] == True).sum()
    else:
        effective_count = 0
    
    st.subheader("统计概览")
    col1, col2 = st.columns(2)
    col1.metric("总测试数", total_tests)
    col2.metric("有效因子数", effective_count)
    
    # Top 20 因子表格 (按 avg_abs_ic 排序)
    st.subheader("Top 20 因子")
    
    if 'avg_abs_ic' in df.columns:
        top20 = df.nlargest(20, 'avg_abs_ic')
        
        # 显示表格（json 里字段名是 'name'）
        display_cols = ['name', 'avg_abs_ic', 'effective']
        available_cols = [c for c in display_cols if c in df.columns]
        
        if available_cols:
            st.dataframe(top20[available_cols], use_container_width=True)
        else:
            st.dataframe(top20, use_container_width=True)
        
        # IC 分布直方图
        st.subheader("IC 分布直方图")
        
        fig = go.Figure()
        fig.add_trace(go.Histogram(
            x=df['avg_abs_ic'],
            nbinsx=50,
            name='IC 分布'
        ))
        
        fig.update_layout(
            title='因子 IC 值分布',
            xaxis_title='avg_abs_ic',
            yaxis_title='频数',
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("数据中未找到 avg_abs_ic 字段")
        st.dataframe(df.head(20))

def render_持仓风控():
    """页面 4: 持仓 & 风控"""
    st.header("💼 持仓 & 风控")
    st.caption(f"最后更新时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 当前持仓 (positions 表)
    st.subheader("当前持仓")
    
    pos_query = "SELECT * FROM positions ORDER BY updated_at DESC"
    pos_df = query_to_df(pos_query)
    
    if pos_df is not None and len(pos_df) > 0:
        st.dataframe(pos_df, use_container_width=True)
    else:
        st.info("暂无持仓数据")
    
    # 账户快照 (account_snapshot 表)
    st.subheader("账户快照")
    
    snapshot_query = "SELECT * FROM account_snapshot ORDER BY time DESC LIMIT 10"
    snapshot_df = query_to_df(snapshot_query)
    
    if snapshot_df is not None and len(snapshot_df) > 0:
        st.dataframe(snapshot_df, use_container_width=True)
    else:
        st.info("暂无账户快照数据")

def render_订单执行():
    """页面 5: 订单执行"""
    st.header("📝 订单执行")
    st.caption(f"最后更新时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # orders 表的历史订单
    orders_query = "SELECT * FROM orders ORDER BY created_at DESC"
    orders_df = query_to_df(orders_query)
    
    if orders_df is not None and len(orders_df) > 0:
        # 订单状态统计
        if 'status' in orders_df.columns:
            st.subheader("订单状态统计")
            status_counts = orders_df['status'].value_counts()
            col1, col2, col3 = st.columns(3)
            for i, (status, count) in enumerate(status_counts.items()):
                if i == 0:
                    col1.metric(str(status), count)
                elif i == 1:
                    col2.metric(str(status), count)
                else:
                    col3.metric(str(status), count)
        
        # 订单列表
        st.subheader("订单列表")
        st.dataframe(orders_df, use_container_width=True)
    else:
        st.info("暂无订单数据")

def render_审计日志():
    """页面 6: 审计日志"""
    st.header("📋 审计日志")
    st.caption(f"最后更新时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # trading_signals 表
    st.subheader("交易信号")
    
    signals_query = "SELECT * FROM trading_signals ORDER BY time DESC LIMIT 100"
    signals_df = query_to_df(signals_query)
    
    if signals_df is not None and len(signals_df) > 0:
        st.dataframe(signals_df, use_container_width=True)
    else:
        st.info("暂无交易信号数据")
    
    # signal_performance 表
    st.subheader("信号表现")
    
    perf_query = "SELECT * FROM signal_performance ORDER BY time DESC LIMIT 100"
    perf_df = query_to_df(perf_query)
    
    if perf_df is not None and len(perf_df) > 0:
        st.dataframe(perf_df, use_container_width=True)
    else:
        st.info("暂无信号表现数据")

# ==================== 主程序 ====================

def main():
    st.set_page_config(
        page_title="量化交易 Dashboard",
        page_icon="📈",
        layout="wide"
    )
    
    st.sidebar.title("📊 量化交易系统")
    
    # 侧边栏刷新按钮
    if st.sidebar.button("🔄 刷新页面"):
        st.cache_data.clear()
        st.rerun()
    
    # 侧边栏导航
    page = st.sidebar.radio(
        "导航",
        [
            "行情 & 特征",
            "模型状态",
            "因子实验室",
            "持仓 & 风控",
            "订单执行",
            "审计日志"
        ]
    )
    
    # 数据库连接测试
    with st.sidebar.expander("数据库状态"):
        conn = get_db_connection()
        if conn:
            st.success("✅ 数据库连接正常")
            conn.close()
        else:
            st.error("❌ 数据库连接失败")
    
    # 根据选择渲染页面
    if page == "行情 & 特征":
        render_行情特征()
    elif page == "模型状态":
        render_模型状态()
    elif page == "因子实验室":
        render_因子实验室()
    elif page == "持仓 & 风控":
        render_持仓风控()
    elif page == "订单执行":
        render_订单执行()
    elif page == "审计日志":
        render_审计日志()

if __name__ == "__main__":
    main()
