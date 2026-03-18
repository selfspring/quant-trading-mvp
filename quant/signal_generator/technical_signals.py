"""
技术信号生成模块
基于技术指标生成交易信号
"""
import logging
from typing import Dict, List
import pandas as pd
import numpy as np
from .technical_indicators import calculate_all_indicators

logger = logging.getLogger(__name__)


class TechnicalSignalGenerator:
    """
    技术信号生成器
    基于多个技术指标生成综合交易信号
    """
    
    def __init__(self):
        """初始化信号生成器"""
        logger.info("TechnicalSignalGenerator initialized")
    
    def generate_signal(self, df: pd.DataFrame) -> Dict:
        """
        基于技术指标生成交易信号
        
        Parameters:
            df: K线数据 DataFrame，包含 OHLCV (open, high, low, close, volume)
        
        Returns:
            {
                "signal": "buy|sell|hold",
                "strength": 0.0-1.0,  # 信号强度
                "indicators": {
                    "ma_5": float,
                    "ma_10": float,
                    ...
                },
                "reasoning": "简短解释"
            }
        """
        try:
            # 数据验证
            if df is None or len(df) < 60:
                logger.warning(f"Insufficient data: {len(df) if df is not None else 0} rows")
                return self._default_hold_signal("数据不足")
            
            # 计算所有技术指标
            df_with_indicators = calculate_all_indicators(df)
            
            if len(df_with_indicators) == 0:
                logger.warning("No data after calculating indicators")
                return self._default_hold_signal("指标计算后数据为空")
            
            # 获取最新的指标值
            latest = df_with_indicators.iloc[-1]
            
            # 检查各个子信号
            ma_signal = self._check_ma_cross(df_with_indicators)
            macd_signal = self._check_macd(df_with_indicators)
            rsi_signal = self._check_rsi(df_with_indicators)
            bollinger_signal = self._check_bollinger(df_with_indicators)
            
            # 聚合信号
            signals = [ma_signal, macd_signal, rsi_signal, bollinger_signal]
            final_signal = self._aggregate_signals(signals)
            
            # 添加指标快照
            final_signal["indicators"] = {
                "ma_5": float(latest['ma_5']),
                "ma_10": float(latest['ma_10']),
                "ma_20": float(latest['ma_20']),
                "ma_60": float(latest['ma_60']),
                "macd": float(latest['macd']),
                "macd_signal": float(latest['macd_signal']),
                "macd_hist": float(latest['macd_hist']),
                "rsi": float(latest['rsi']),
                "bb_upper": float(latest['bb_upper']),
                "bb_middle": float(latest['bb_middle']),
                "bb_lower": float(latest['bb_lower']),
                "atr": float(latest['atr']),
                "close": float(latest['close'])
            }
            
            logger.info(f"Generated signal: {final_signal['signal']} (strength: {final_signal['strength']:.2f})")
            return final_signal
            
        except Exception as e:
            logger.error(f"Error generating signal: {e}", exc_info=True)
            return self._default_hold_signal(f"计算异常: {str(e)}")
    
    def _check_ma_cross(self, df: pd.DataFrame) -> Dict:
        """
        检查均线交叉信号
        
        Parameters:
            df: 包含 MA 指标的 DataFrame
        
        Returns:
            {
                "signal": "buy|sell|hold",
                "strength": 0.0-1.0,
                "reasoning": str
            }
        """
        try:
            if len(df) < 2:
                return {"signal": "hold", "strength": 0.0, "reasoning": "数据不足"}
            
            # 获取最新两根K线的均线值
            current = df.iloc[-1]
            previous = df.iloc[-2]
            
            ma5_current = current['ma_5']
            ma10_current = current['ma_10']
            ma5_previous = previous['ma_5']
            ma10_previous = previous['ma_10']
            
            # 检查交叉
            # 金叉: MA5 上穿 MA10
            if ma5_previous <= ma10_previous and ma5_current > ma10_current:
                # 计算交叉强度: 基于交叉角度和距离
                cross_distance = abs(ma5_current - ma10_current) / ma10_current
                strength = min(0.8, 0.5 + cross_distance * 100)  # 0.5-0.8
                return {
                    "signal": "buy",
                    "strength": strength,
                    "reasoning": f"MA5上穿MA10 (金叉), 距离{cross_distance*100:.2f}%"
                }
            
            # 死叉: MA5 下穿 MA10
            elif ma5_previous >= ma10_previous and ma5_current < ma10_current:
                cross_distance = abs(ma5_current - ma10_current) / ma10_current
                strength = min(0.8, 0.5 + cross_distance * 100)
                return {
                    "signal": "sell",
                    "strength": strength,
                    "reasoning": f"MA5下穿MA10 (死叉), 距离{cross_distance*100:.2f}%"
                }
            
            # 无交叉，检查趋势
            else:
                # MA5 在 MA10 上方 → 多头趋势
                if ma5_current > ma10_current:
                    distance = (ma5_current - ma10_current) / ma10_current
                    strength = min(0.5, distance * 50)  # 0.0-0.5
                    return {
                        "signal": "buy",
                        "strength": strength,
                        "reasoning": f"MA5在MA10上方 (多头趋势), 距离{distance*100:.2f}%"
                    }
                # MA5 在 MA10 下方 → 空头趋势
                else:
                    distance = (ma10_current - ma5_current) / ma10_current
                    strength = min(0.5, distance * 50)
                    return {
                        "signal": "sell",
                        "strength": strength,
                        "reasoning": f"MA5在MA10下方 (空头趋势), 距离{distance*100:.2f}%"
                    }
                    
        except Exception as e:
            logger.error(f"Error in _check_ma_cross: {e}")
            return {"signal": "hold", "strength": 0.0, "reasoning": f"MA计算异常: {str(e)}"}
    
    def _check_macd(self, df: pd.DataFrame) -> Dict:
        """
        检查 MACD 信号
        
        Parameters:
            df: 包含 MACD 指标的 DataFrame
        
        Returns:
            {
                "signal": "buy|sell|hold",
                "strength": 0.0-1.0,
                "reasoning": str
            }
        """
        try:
            if len(df) < 2:
                return {"signal": "hold", "strength": 0.0, "reasoning": "数据不足"}
            
            current = df.iloc[-1]
            previous = df.iloc[-2]
            
            macd_current = current['macd']
            signal_current = current['macd_signal']
            hist_current = current['macd_hist']
            
            macd_previous = previous['macd']
            signal_previous = previous['macd_signal']
            hist_previous = previous['macd_hist']
            
            # 检查金叉/死叉
            # 金叉: MACD 上穿信号线
            if macd_previous <= signal_previous and macd_current > signal_current:
                # 强度基于柱状图高度
                strength = min(0.8, 0.5 + abs(hist_current) * 10)
                return {
                    "signal": "buy",
                    "strength": strength,
                    "reasoning": f"MACD金叉, 柱状图{hist_current:.3f}"
                }
            
            # 死叉: MACD 下穿信号线
            elif macd_previous >= signal_previous and macd_current < signal_current:
                strength = min(0.8, 0.5 + abs(hist_current) * 10)
                return {
                    "signal": "sell",
                    "strength": strength,
                    "reasoning": f"MACD死叉, 柱状图{hist_current:.3f}"
                }
            
            # 无交叉，检查柱状图方向
            else:
                if hist_current > 0:
                    strength = min(0.5, abs(hist_current) * 10)
                    return {
                        "signal": "buy",
                        "strength": strength,
                        "reasoning": f"MACD柱状图为正 ({hist_current:.3f})"
                    }
                elif hist_current < 0:
                    strength = min(0.5, abs(hist_current) * 10)
                    return {
                        "signal": "sell",
                        "strength": strength,
                        "reasoning": f"MACD柱状图为负 ({hist_current:.3f})"
                    }
                else:
                    return {
                        "signal": "hold",
                        "strength": 0.0,
                        "reasoning": "MACD中性"
                    }
                    
        except Exception as e:
            logger.error(f"Error in _check_macd: {e}")
            return {"signal": "hold", "strength": 0.0, "reasoning": f"MACD计算异常: {str(e)}"}
    
    def _check_rsi(self, df: pd.DataFrame) -> Dict:
        """
        检查 RSI 超买超卖信号
        
        Parameters:
            df: 包含 RSI 指标的 DataFrame
        
        Returns:
            {
                "signal": "buy|sell|hold",
                "strength": 0.0-1.0,
                "reasoning": str
            }
        """
        try:
            current = df.iloc[-1]
            rsi = current['rsi']
            
            # RSI < 30: 超卖，买入信号
            if rsi < 30:
                # 强度: 距离30越远越强
                strength = min(0.9, (30 - rsi) / 30 * 1.5)
                return {
                    "signal": "buy",
                    "strength": strength,
                    "reasoning": f"RSI超卖 ({rsi:.1f} < 30)"
                }
            
            # RSI > 70: 超买，卖出信号
            elif rsi > 70:
                strength = min(0.9, (rsi - 70) / 30 * 1.5)
                return {
                    "signal": "sell",
                    "strength": strength,
                    "reasoning": f"RSI超买 ({rsi:.1f} > 70)"
                }
            
            # 30 <= RSI <= 70: 中性区域
            else:
                # 轻微倾向
                if rsi < 45:
                    strength = (45 - rsi) / 45 * 0.3
                    return {
                        "signal": "buy",
                        "strength": strength,
                        "reasoning": f"RSI偏低 ({rsi:.1f})"
                    }
                elif rsi > 55:
                    strength = (rsi - 55) / 45 * 0.3
                    return {
                        "signal": "sell",
                        "strength": strength,
                        "reasoning": f"RSI偏高 ({rsi:.1f})"
                    }
                else:
                    return {
                        "signal": "hold",
                        "strength": 0.0,
                        "reasoning": f"RSI中性 ({rsi:.1f})"
                    }
                    
        except Exception as e:
            logger.error(f"Error in _check_rsi: {e}")
            return {"signal": "hold", "strength": 0.0, "reasoning": f"RSI计算异常: {str(e)}"}
    
    def _check_bollinger(self, df: pd.DataFrame) -> Dict:
        """
        检查布林带突破信号
        
        Parameters:
            df: 包含布林带指标的 DataFrame
        
        Returns:
            {
                "signal": "buy|sell|hold",
                "strength": 0.0-1.0,
                "reasoning": str
            }
        """
        try:
            current = df.iloc[-1]
            close = current['close']
            bb_upper = current['bb_upper']
            bb_middle = current['bb_middle']
            bb_lower = current['bb_lower']
            bb_width = current['bb_width']
            
            # 计算价格在布林带中的位置 (0-1)
            bb_position = (close - bb_lower) / (bb_upper - bb_lower) if bb_width > 0 else 0.5
            
            # 触及下轨: 买入信号
            if bb_position < 0.1:
                # 强度: 突破程度
                penetration = abs(close - bb_lower) / bb_width if bb_width > 0 else 0
                strength = min(0.85, 0.6 + penetration * 2)
                return {
                    "signal": "buy",
                    "strength": strength,
                    "reasoning": f"价格触及布林带下轨 (位置{bb_position:.2f})"
                }
            
            # 触及上轨: 卖出信号
            elif bb_position > 0.9:
                penetration = abs(close - bb_upper) / bb_width if bb_width > 0 else 0
                strength = min(0.85, 0.6 + penetration * 2)
                return {
                    "signal": "sell",
                    "strength": strength,
                    "reasoning": f"价格触及布林带上轨 (位置{bb_position:.2f})"
                }
            
            # 中轨附近: 观望
            elif 0.4 < bb_position < 0.6:
                return {
                    "signal": "hold",
                    "strength": 0.0,
                    "reasoning": f"价格在布林带中轨附近 (位置{bb_position:.2f})"
                }
            
            # 偏离中轨但未触及边界
            else:
                if bb_position < 0.4:
                    strength = (0.4 - bb_position) * 0.8
                    return {
                        "signal": "buy",
                        "strength": strength,
                        "reasoning": f"价格偏向布林带下方 (位置{bb_position:.2f})"
                    }
                else:  # bb_position > 0.6
                    strength = (bb_position - 0.6) * 0.8
                    return {
                        "signal": "sell",
                        "strength": strength,
                        "reasoning": f"价格偏向布林带上方 (位置{bb_position:.2f})"
                    }
                    
        except Exception as e:
            logger.error(f"Error in _check_bollinger: {e}")
            return {"signal": "hold", "strength": 0.0, "reasoning": f"布林带计算异常: {str(e)}"}
    
    def _aggregate_signals(self, signals: List[Dict]) -> Dict:
        """
        聚合多个子信号
        
        Parameters:
            signals: 子信号列表，每个包含 signal, strength, reasoning
        
        Returns:
            {
                "signal": "buy|sell|hold",
                "strength": 0.0-1.0,
                "reasoning": "简短解释"
            }
        """
        try:
            # 统计各方向的信号数量和强度
            buy_signals = [s for s in signals if s['signal'] == 'buy']
            sell_signals = [s for s in signals if s['signal'] == 'sell']
            hold_signals = [s for s in signals if s['signal'] == 'hold']
            
            buy_count = len(buy_signals)
            sell_count = len(sell_signals)
            hold_count = len(hold_signals)
            
            # 计算加权强度
            buy_strength = sum(s['strength'] for s in buy_signals) / len(signals) if buy_signals else 0.0
            sell_strength = sum(s['strength'] for s in sell_signals) / len(signals) if sell_signals else 0.0
            
            # 决策逻辑: 多数一致
            total_signals = len(signals)
            
            # 买入信号占多数
            if buy_count > sell_count and buy_count >= total_signals / 2:
                final_strength = buy_strength
                reasoning_parts = [s['reasoning'] for s in buy_signals[:2]]  # 取前2个
                reasoning = f"买入 ({buy_count}/{total_signals}): " + "; ".join(reasoning_parts)
                return {
                    "signal": "buy",
                    "strength": final_strength,
                    "reasoning": reasoning
                }
            
            # 卖出信号占多数
            elif sell_count > buy_count and sell_count >= total_signals / 2:
                final_strength = sell_strength
                reasoning_parts = [s['reasoning'] for s in sell_signals[:2]]
                reasoning = f"卖出 ({sell_count}/{total_signals}): " + "; ".join(reasoning_parts)
                return {
                    "signal": "sell",
                    "strength": final_strength,
                    "reasoning": reasoning
                }
            
            # 信号分歧或观望占多数
            else:
                return {
                    "signal": "hold",
                    "strength": 0.0,
                    "reasoning": f"信号分歧 (买{buy_count}/卖{sell_count}/观望{hold_count})"
                }
                
        except Exception as e:
            logger.error(f"Error in _aggregate_signals: {e}")
            return {"signal": "hold", "strength": 0.0, "reasoning": f"信号聚合异常: {str(e)}"}
    
    def _default_hold_signal(self, reason: str) -> Dict:
        """
        返回默认的观望信号
        
        Parameters:
            reason: 观望原因
        
        Returns:
            标准格式的 hold 信号
        """
        return {
            "signal": "hold",
            "strength": 0.0,
            "indicators": {},
            "reasoning": reason
        }


# 数据库表结构 (可选，用于持久化技术信号)
"""
CREATE TABLE IF NOT EXISTS technical_signals (
    id SERIAL PRIMARY KEY,
    datetime TIMESTAMP NOT NULL,
    symbol VARCHAR(20),
    signal VARCHAR(10),
    strength FLOAT,
    ma_5 FLOAT,
    ma_10 FLOAT,
    ma_20 FLOAT,
    ma_60 FLOAT,
    macd FLOAT,
    macd_signal FLOAT,
    macd_hist FLOAT,
    rsi FLOAT,
    bb_upper FLOAT,
    bb_middle FLOAT,
    bb_lower FLOAT,
    atr FLOAT,
    close FLOAT,
    reasoning TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_technical_signals_datetime ON technical_signals(datetime, symbol);
"""
