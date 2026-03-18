"""
信号融合模块
融合技术指标、ML预测、LLM新闻三个信号源，生成最终交易信号
"""
from typing import Dict, List, Tuple, Optional
import logging
from datetime import datetime

from quant.common.db_pool import get_db_connection
from quant.common.config import config

logger = logging.getLogger(__name__)


class SignalFusion:
    """信号融合器"""
    
    def __init__(
        self,
        ml_weight: float = 0.5,
        technical_weight: float = 0.3,
        llm_weight: float = 0.2
    ):
        """
        初始化信号融合器
        
        Parameters:
            ml_weight: ML预测权重
            technical_weight: 技术指标权重
            llm_weight: LLM新闻权重
        """
        # 验证权重和为1
        total_weight = ml_weight + technical_weight + llm_weight
        if abs(total_weight - 1.0) > 0.001:
            raise ValueError(
                f"权重之和必须为1.0，当前为 {total_weight}"
            )
        
        self.ml_weight = ml_weight
        self.technical_weight = technical_weight
        self.llm_weight = llm_weight
        
        logger.info(f"signal_fusion_initialized ml_weight=ml_weight technical_weight=technical_weight llm_weight=llm_weight")
    
    def fuse_signals(
        self,
        technical_signal: Optional[Dict] = None,
        ml_signal: Optional[Dict] = None,
        llm_signal: Optional[Dict] = None,
        symbol: str = "au2606",
        timestamp: Optional[datetime] = None
    ) -> Dict:
        """
        融合三个信号源
        
        Parameters:
            technical_signal: {"signal": "buy|sell|hold", "strength": 0.0-1.0}
            ml_signal: {"prediction": float, "confidence": 0.0-1.0}
            llm_signal: {"direction": "bullish|bearish|neutral", "confidence": 0.0-1.0}
            symbol: 交易品种
            timestamp: 信号时间戳（可选，默认当前时间）
        
        Returns:
            {
                "direction": "buy|sell|hold",
                "strength": 0.0-1.0,
                "components": {
                    "technical": {...},
                    "ml": {...},
                    "llm": {...}
                },
                "timestamp": datetime,
                "symbol": str
            }
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        # 处理信号缺失情况
        if not any([technical_signal, ml_signal, llm_signal]):
            logger.warning(f"all_signals_missing symbol=symbol timestamp=timestamp")
            return self._create_hold_signal(
                technical_signal, ml_signal, llm_signal,
                symbol, timestamp, reason="all_signals_missing"
            )
        
        # 归一化信号方向
        tech_dir, ml_dir, llm_dir = self._normalize_signals(
            technical_signal, ml_signal, llm_signal
        )
        
        # 收集有效方向
        directions = []
        if tech_dir:
            directions.append(tech_dir)
        if ml_dir:
            directions.append(ml_dir)
        if llm_dir:
            directions.append(llm_dir)
        
        # 检查方向一致性
        is_consistent, final_direction = self._check_consistency(directions)
        
        if not is_consistent:
            logger.info(f"signal_inconsistent directions=directions symbol=symbol timestamp=timestamp")
            return self._create_hold_signal(
                technical_signal, ml_signal, llm_signal,
                symbol, timestamp, reason="inconsistent_directions"
            )
        
        # 计算信号强度
        strength = self._calculate_strength(
            technical_signal, ml_signal, llm_signal, final_direction
        )
        
        # 构建融合信号
        fused_signal = {
            "direction": final_direction,
            "strength": strength,
            "components": {
                "technical": technical_signal,
                "ml": ml_signal,
                "llm": llm_signal
            },
            "timestamp": timestamp,
            "symbol": symbol
        }
        
        logger.info(f"signal_fused direction=final_direction strength=strength symbol=symbol timestamp=timestamp")
        
        return fused_signal
    
    def _normalize_signals(
        self,
        technical: Optional[Dict],
        ml: Optional[Dict],
        llm: Optional[Dict]
    ) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        将三个信号源归一化为统一的方向表示 (buy/sell/hold)
        
        - technical: 已经是 buy/sell/hold
        - ml: prediction > 0.005 → buy, < -0.005 → sell, ~0 → hold
        - llm: bullish → buy, bearish → sell, neutral → hold
        
        Returns:
            (tech_direction, ml_direction, llm_direction)
        """
        # 技术信号归一化
        tech_dir = None
        if technical and "signal" in technical:
            tech_dir = technical["signal"]
            if tech_dir not in ["buy", "sell", "hold"]:
                logger.warning(f"invalid_technical_signal signal=tech_dir")
                tech_dir = None
        
        # ML信号归一化
        ml_dir = None
        if ml and "prediction" in ml:
            prediction = ml["prediction"]
            if prediction > 0.005:
                ml_dir = "buy"
            elif prediction < -0.005:
                ml_dir = "sell"
            else:
                ml_dir = "hold"
        
        # LLM信号归一化
        llm_dir = None
        if llm and "direction" in llm:
            direction = llm["direction"].lower()
            if direction == "bullish":
                llm_dir = "buy"
            elif direction == "bearish":
                llm_dir = "sell"
            elif direction == "neutral":
                llm_dir = "hold"
            else:
                logger.warning(f"invalid_llm_direction direction={llm['direction']}")
        
        return tech_dir, ml_dir, llm_dir
    
    def _check_consistency(
        self,
        directions: List[str]
    ) -> Tuple[bool, str]:
        """
        检查方向一致性：至少 2/3 一致
        
        Parameters:
            directions: 方向列表，如 ["buy", "buy", "sell"]
        
        Returns:
            (is_consistent, final_direction)
            - is_consistent: 是否一致
            - final_direction: 最终方向（一致时返回多数方向，不一致时返回 "hold"）
        """
        if not directions:
            return False, "hold"
        
        # 统计各方向数量
        buy_count = directions.count("buy")
        sell_count = directions.count("sell")
        hold_count = directions.count("hold")
        
        total = len(directions)
        
        # 至少 2/3 一致（向上取整）
        threshold = (total + 1) // 2  # 例如：3个信号需要2个，2个信号需要1个
        
        if buy_count >= threshold:
            return True, "buy"
        elif sell_count >= threshold:
            return True, "sell"
        elif hold_count >= threshold:
            return True, "hold"
        else:
            # 分歧太大
            return False, "hold"
    
    def _calculate_strength(
        self,
        technical_signal: Optional[Dict],
        ml_signal: Optional[Dict],
        llm_signal: Optional[Dict],
        final_direction: str
    ) -> float:
        """
        计算最终信号强度（加权平均）
        
        只考虑与 final_direction 一致的信号
        
        例如：
        - technical: buy, strength=0.7
        - ml: buy, confidence=0.8
        - llm: sell, confidence=0.6
        - final_direction = buy
        - strength = (0.7 * 0.3 + 0.8 * 0.5) / (0.3 + 0.5) = 0.7625
        
        Parameters:
            technical_signal: 技术信号
            ml_signal: ML信号
            llm_signal: LLM信号
            final_direction: 最终方向
        
        Returns:
            信号强度 (0.0-1.0)
        """
        weighted_sum = 0.0
        weight_sum = 0.0
        
        # 技术信号
        if technical_signal and "signal" in technical_signal:
            tech_dir = technical_signal["signal"]
            tech_strength = technical_signal.get("strength", 0.5)
            
            if tech_dir == final_direction:
                weighted_sum += tech_strength * self.technical_weight
                weight_sum += self.technical_weight
        
        # ML信号
        if ml_signal and "prediction" in ml_signal:
            prediction = ml_signal["prediction"]
            ml_confidence = ml_signal.get("confidence", 0.5)
            
            # 判断ML方向
            if prediction > 0.005 and final_direction == "buy":
                weighted_sum += ml_confidence * self.ml_weight
                weight_sum += self.ml_weight
            elif prediction < -0.005 and final_direction == "sell":
                weighted_sum += ml_confidence * self.ml_weight
                weight_sum += self.ml_weight
            elif abs(prediction) <= 0.005 and final_direction == "hold":
                weighted_sum += ml_confidence * self.ml_weight
                weight_sum += self.ml_weight
        
        # LLM信号
        if llm_signal and "direction" in llm_signal:
            llm_dir = llm_signal["direction"].lower()
            llm_confidence = llm_signal.get("confidence", 0.5)
            
            # 判断LLM方向
            if (llm_dir == "bullish" and final_direction == "buy") or \
               (llm_dir == "bearish" and final_direction == "sell") or \
               (llm_dir == "neutral" and final_direction == "hold"):
                weighted_sum += llm_confidence * self.llm_weight
                weight_sum += self.llm_weight
        
        # 计算加权平均
        if weight_sum > 0:
            strength = weighted_sum / weight_sum
        else:
            # 没有一致的信号，返回默认强度
            strength = 0.5
        
        return min(max(strength, 0.0), 1.0)  # 限制在 [0, 1]
    
    def _create_hold_signal(
        self,
        technical_signal: Optional[Dict],
        ml_signal: Optional[Dict],
        llm_signal: Optional[Dict],
        symbol: str,
        timestamp: datetime,
        reason: str
    ) -> Dict:
        """
        创建 hold 信号
        
        Parameters:
            technical_signal: 技术信号
            ml_signal: ML信号
            llm_signal: LLM信号
            symbol: 交易品种
            timestamp: 时间戳
            reason: 原因
        
        Returns:
            hold 信号字典
        """
        return {
            "direction": "hold",
            "strength": 0.0,
            "components": {
                "technical": technical_signal,
                "ml": ml_signal,
                "llm": llm_signal
            },
            "timestamp": timestamp,
            "symbol": symbol,
            "reason": reason
        }
    
    def save_to_db(self, fused_signal: Dict) -> bool:
        """
        保存融合信号到 fused_signals 表
        
        Parameters:
            fused_signal: 融合信号字典
        
        Returns:
            是否保存成功
        """
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    # 提取组件信息
                    components = fused_signal.get("components", {})
                    technical = components.get("technical", {})
                    ml = components.get("ml", {})
                    llm = components.get("llm", {})
                    
                    # 插入数据
                    cursor.execute(
                        """
                        INSERT INTO fused_signals (
                            datetime, symbol, direction, strength,
                            technical_signal, technical_strength,
                            ml_prediction, ml_confidence,
                            llm_direction, llm_confidence
                        ) VALUES (
                            %s, %s, %s, %s,
                            %s, %s,
                            %s, %s,
                            %s, %s
                        )
                        """,
                        (
                            fused_signal.get("timestamp"),
                            fused_signal.get("symbol"),
                            fused_signal.get("direction"),
                            fused_signal.get("strength"),
                            technical.get("signal") if technical else None,
                            technical.get("strength") if technical else None,
                            ml.get("prediction") if ml else None,
                            ml.get("confidence") if ml else None,
                            llm.get("direction") if llm else None,
                            llm.get("confidence") if llm else None
                        )
                    )
                    conn.commit()
                    
                    logger.info(f"fused_signal_saved symbol=fused_signal.get('symbol') direction=fused_signal.get('direction') strength=fused_signal.get('strength')")
                    return True
        
        except Exception as e:
            logger.error(f"fused_signal_save_failed error=str(e) signal=fused_signal")
            return False
    
    def create_table_if_not_exists(self):
        """
        创建 fused_signals 表（如果不存在）
        """
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        CREATE TABLE IF NOT EXISTS fused_signals (
                            id SERIAL PRIMARY KEY,
                            datetime TIMESTAMP NOT NULL,
                            symbol VARCHAR(20),
                            direction VARCHAR(10),
                            strength FLOAT,
                            technical_signal VARCHAR(10),
                            technical_strength FLOAT,
                            ml_prediction FLOAT,
                            ml_confidence FLOAT,
                            llm_direction VARCHAR(20),
                            llm_confidence FLOAT,
                            created_at TIMESTAMP DEFAULT NOW()
                        )
                        """
                    )
                    
                    # 创建索引
                    cursor.execute(
                        """
                        CREATE INDEX IF NOT EXISTS idx_fused_signals_datetime_symbol
                        ON fused_signals (datetime, symbol)
                        """
                    )
                    
                    conn.commit()
                    logger.info("fused_signals_table_created")
        
        except Exception as e:
            logger.error(f"fused_signals_table_creation_failed error=str(e)")
            raise


# 便捷函数
def fuse_signals(
    technical_signal: Optional[Dict] = None,
    ml_signal: Optional[Dict] = None,
    llm_signal: Optional[Dict] = None,
    symbol: str = "au2606",
    timestamp: Optional[datetime] = None,
    save_to_db: bool = True
) -> Dict:
    """
    便捷函数：融合信号
    
    Parameters:
        technical_signal: 技术信号
        ml_signal: ML信号
        llm_signal: LLM信号
        symbol: 交易品种
        timestamp: 时间戳
        save_to_db: 是否保存到数据库
    
    Returns:
        融合信号字典
    """
    # 使用配置中的权重
    fusion = SignalFusion(
        ml_weight=config.strategy.signal_weights_ml,
        technical_weight=config.strategy.signal_weights_technical,
        llm_weight=config.strategy.signal_weights_news
    )
    
    fused_signal = fusion.fuse_signals(
        technical_signal=technical_signal,
        ml_signal=ml_signal,
        llm_signal=llm_signal,
        symbol=symbol,
        timestamp=timestamp
    )
    
    if save_to_db:
        fusion.save_to_db(fused_signal)
    
    return fused_signal
