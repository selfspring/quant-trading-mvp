"""
消息追踪模块
实现全链路消息追踪，用于调试和性能分析
"""
import uuid
import json
import time
from datetime import datetime
from typing import Optional, Dict, Any, List, Set
from queue import Queue, Full, Empty
from threading import Thread
import redis
import structlog

from .db_pool import get_db_connection

logger = structlog.get_logger()


def generate_trace_id() -> str:
    """
    生成全局唯一的 trace_id
    格式：{timestamp}_{uuid}
    """
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    unique_id = str(uuid.uuid4())
    return f"{timestamp}_{unique_id}"


def generate_child_trace_id(parent_trace_id: str) -> str:
    """
    生成子 trace_id（用于关联上下游事件）
    """
    return f"{parent_trace_id}_child_{uuid.uuid4().hex[:8]}"


class MessageTracer:
    """
    消息追踪中间件（高性能版本）
    自动记录每个进程的事件到 message_trace 表和 Redis
    使用异步批量写入避免阻塞主流程
    """
    
    def __init__(
        self, 
        redis_client: redis.Redis, 
        process_name: str,
        batch_size: int = 100,
        flush_interval: float = 1.0
    ):
        """
        初始化消息追踪器
        
        Args:
            redis_client: Redis 客户端
            process_name: 进程名称（如 'data_collector', 'signal_generator'）
            batch_size: 批量写入大小
            flush_interval: 刷新间隔（秒）
        """
        self.redis = redis_client
        self.process_name = process_name
        self.logger = logger.bind(process=process_name)
        
        # 异步写入队列
        self.write_queue: Queue[Dict[str, Any]] = Queue(maxsize=10000)
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        
        # 启动后台写入线程
        self._running = True
        self.writer_thread = Thread(target=self._batch_writer, daemon=True)
        self.writer_thread.start()
        
        # 统计信息
        self.stats = {
            'total_events': 0,
            'failed_events': 0,
            'queue_full_count': 0,
            'batch_writes': 0,
            'dropped_events': 0  # 被丢弃的非关键事件数量
        }
        
        # 关键事件类型（队列满时优先保留）
        self.critical_event_types = {
            'signal_generated',
            'order_submitted',
            'risk_triggered',
            'order_filled',
            'order_rejected'
        }
    
    def trace_event(
        self,
        trace_id: str,
        event_type: str,
        event_data: Dict[str, Any],
        parent_trace_id: Optional[str] = None,
        status: str = 'success',
        error_msg: Optional[str] = None,
        latency_ms: Optional[int] = None
    ) -> None:
        """
        记录事件到 message_trace 表和 Redis（非阻塞）
        
        Args:
            trace_id: 追踪ID
            event_type: 事件类型（如 'kline_received', 'signal_generated'）
            event_data: 事件数据（JSON格式）
            parent_trace_id: 父追踪ID（用于关联上下游）
            status: 状态（'success', 'failed', 'timeout'）
            error_msg: 错误信息
            latency_ms: 延迟（毫秒）
        """
        timestamp = datetime.now()
        
        trace_record = {
            'trace_id': trace_id,
            'timestamp': timestamp.isoformat(),
            'process_name': self.process_name,
            'event_type': event_type,
            'event_data': event_data,
            'parent_trace_id': parent_trace_id,
            'status': status,
            'error_msg': error_msg,
            'latency_ms': latency_ms
        }
        
        try:
            # 1. 立即写入 Redis（快速查询）
            self.redis.setex(
                f"trace:{trace_id}",
                3600,
                json.dumps(trace_record)
            )
            
            # 2. 异步写入数据库（不阻塞）
            # 队列满时的降级策略：只保留关键事件
            try:
                self.write_queue.put_nowait(trace_record)
                self.stats['total_events'] += 1
            except Full:
                self.stats['queue_full_count'] += 1
                
                # 降级策略：关键事件使用阻塞写入（带超时），非关键事件直接丢弃
                if event_type in self.critical_event_types:
                    try:
                        self.write_queue.put(trace_record, timeout=0.5)
                        self.stats['total_events'] += 1
                        self.logger.warning(
                            "critical_event_queued_with_timeout",
                            trace_id=trace_id,
                            event_type=event_type
                        )
                    except Full:
                        self.stats['dropped_events'] += 1
                        self.logger.error(
                            "critical_event_dropped",
                            trace_id=trace_id,
                            event_type=event_type,
                            queue_size=self.write_queue.qsize()
                        )
                else:
                    # 非关键事件直接丢弃
                    self.stats['dropped_events'] += 1
                    if self.stats['dropped_events'] % 100 == 0:  # 每100条记录一次
                        self.logger.warning(
                            "non_critical_events_dropped",
                            total_dropped=self.stats['dropped_events'],
                            queue_size=self.write_queue.qsize()
                        )
            
            # 3. 记录日志
            self.logger.info(
                "trace_event",
                trace_id=trace_id,
                event_type=event_type,
                status=status,
                latency_ms=latency_ms
            )
            
        except Exception as e:
            self.stats['failed_events'] += 1
            self.logger.error(
                "trace_event_failed",
                trace_id=trace_id,
                error=str(e)
            )
    
    def _batch_writer(self) -> None:
        batch = []
        last_flush = time.time()
        
        while self._running:
            try:
                # 收集记录（带超时）
                try:
                    record = self.write_queue.get(timeout=0.1)
                    batch.append(record)
                except Empty:
                    pass
                
                # 满足批量大小或超时，执行写入
                should_flush = (
                    len(batch) >= self.batch_size or
                    (batch and time.time() - last_flush >= self.flush_interval)
                )
                
                if should_flush:
                    self._batch_insert(batch)
                    batch.clear()
                    last_flush = time.time()
                    
            except Exception as e:
                self.logger.error("batch_writer_failed", error=str(e))
                time.sleep(1)  # 避免错误循环
        
        # 关闭前刷新剩余数据
        if batch:
            self._batch_insert(batch)
    
    def _batch_insert(self, records: List[Dict[str, Any]]) -> None:
        """批量插入数据库（带重试）"""
        if not records:
            return
        
        self._batch_insert_with_retry(records)
    
    def _batch_insert_with_retry(self, records: List[Dict[str, Any]], max_retries: int = 3) -> None:
        """批量插入数据库（带重试和备份）"""
        for attempt in range(max_retries):
            try:
                with get_db_connection() as conn:
                    with conn.cursor() as cursor:
                        query = """
                            INSERT INTO message_trace 
                            (trace_id, timestamp, process_name, event_type, event_data, 
                             parent_trace_id, latency_ms, status, error_msg)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """
                        cursor.executemany(query, [
                            (
                                r['trace_id'],
                                r['timestamp'],
                                r['process_name'],
                                r['event_type'],
                                json.dumps(r['event_data']),
                                r['parent_trace_id'],
                                r['latency_ms'],
                                r['status'],
                                r['error_msg']
                            )
                            for r in records
                        ])
                        conn.commit()
                        
                self.stats['batch_writes'] += 1
                self.logger.debug("batch_inserted", count=len(records))
                return  # 成功则返回
                
            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # 指数退避：1s, 2s, 4s
                    self.logger.warning(
                        "batch_insert_retry",
                        attempt=attempt + 1,
                        max_retries=max_retries,
                        wait_time=wait_time,
                        error=str(e)
                    )
                    time.sleep(wait_time)
                else:
                    # 最后一次失败，写入本地备份
                    self._write_to_backup(records)
                    self.logger.error(
                        "batch_insert_failed_after_retries",
                        count=len(records),
                        max_retries=max_retries,
                        error=str(e)
                    )
    
    def _write_to_backup(self, records: List[Dict[str, Any]]) -> None:
        """写入本地备份文件"""
        try:
            import os
            
            # 确保 logs 目录存在
            os.makedirs('logs', exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_file = f"logs/trace_backup_{timestamp}.jsonl"
            
            with open(backup_file, 'a', encoding='utf-8') as f:
                for record in records:
                    f.write(json.dumps(record, ensure_ascii=False) + '\n')
            
            self.logger.warning(
                "trace_backup_written",
                backup_file=backup_file,
                count=len(records)
            )
            
        except Exception as e:
            self.logger.error(
                "trace_backup_failed",
                count=len(records),
                error=str(e)
            )
    
    def publish_with_trace(
        self,
        channel: str,
        message: Dict[str, Any],
        parent_trace_id: Optional[str] = None
    ) -> str:
        """
        发布消息时自动注入 trace_id
        
        Args:
            channel: Redis 频道名称
            message: 消息内容
            parent_trace_id: 父追踪ID
            
        Returns:
            生成的 trace_id
        """
        start_time = time.time()
        
        # 生成 trace_id
        trace_id = generate_trace_id()
        message['trace_id'] = trace_id
        message['parent_trace_id'] = parent_trace_id
        
        try:
            # 发布消息
            self.redis.publish(channel, json.dumps(message))
            
            # 记录发送事件
            latency_ms = int((time.time() - start_time) * 1000)
            self.trace_event(
                trace_id=trace_id,
                event_type=f'{channel}_published',
                event_data=message,
                parent_trace_id=parent_trace_id,
                status='success',
                latency_ms=latency_ms
            )
            
            return trace_id
            
        except Exception as e:
            # 记录失败事件
            self.trace_event(
                trace_id=trace_id,
                event_type=f'{channel}_published',
                event_data=message,
                parent_trace_id=parent_trace_id,
                status='failed',
                error_msg=str(e)
            )
            raise
    
    def subscribe_with_trace(
        self,
        channel: str,
        callback: Any
    ) -> Thread:
        """
        订阅消息时自动记录 trace（在独立线程中运行）
        
        Args:
            channel: Redis 频道名称
            callback: 消息处理回调函数
        
        Returns:
            Thread: 订阅线程对象
        """
        def _subscribe_thread() -> None:
            pubsub = self.redis.pubsub()
            pubsub.subscribe(channel)
            
            self.logger.info("subscribed_to_channel", channel=channel)
            
            try:
                for message in pubsub.listen():
                    if not self._running:
                        break
                    
                    if message['type'] == 'message':
                        self._handle_message(message, channel, callback)
                        
            except Exception as e:
                self.logger.error("subscription_failed", channel=channel, error=str(e))
            finally:
                pubsub.unsubscribe(channel)
                pubsub.close()
                self.logger.info("unsubscribed_from_channel", channel=channel)
        
        thread = Thread(target=_subscribe_thread, daemon=True)
        thread.start()
        return thread
    
    def _handle_message(self, message: Any, channel: str, callback: Any) -> None:
        """处理单条消息"""
        start_time = time.time()
        trace_id = None
        
        try:
            # 解析消息
            data = json.loads(message['data'])
            trace_id = data.get('trace_id')
            parent_trace_id = data.get('parent_trace_id')
            
            # 记录接收事件
            self.trace_event(
                trace_id=trace_id or generate_trace_id(),
                event_type=f'{channel}_received',
                event_data=data,
                parent_trace_id=parent_trace_id,
                status='success'
            )
            
            # 调用回调函数
            callback(data)
            
            # 记录处理完成
            latency_ms = int((time.time() - start_time) * 1000)
            self.trace_event(
                trace_id=trace_id or generate_trace_id(),
                event_type=f'{channel}_processed',
                event_data={'latency_ms': latency_ms},
                parent_trace_id=parent_trace_id,
                status='success',
                latency_ms=latency_ms
            )
            
        except Exception as e:
            # 记录处理失败
            self.trace_event(
                trace_id=trace_id or generate_trace_id(),
                event_type=f'{channel}_processed',
                event_data={},
                parent_trace_id=parent_trace_id,
                status='failed',
                error_msg=str(e)
            )
            self.logger.error(
                "message_processing_failed",
                channel=channel,
                error=str(e)
            )
    
    def get_stats(self) -> Dict[str, int]:
        return {
            **self.stats,
            'queue_size': self.write_queue.qsize()
        }
    
    def shutdown(self) -> None:
        self.logger.info("shutting_down_tracer", process=self.process_name)
        self._running = False
        self.writer_thread.join(timeout=5)
        self.logger.info("tracer_shutdown_complete", stats=self.get_stats())


class TraceContext:
    """
    追踪上下文管理器
    用于在函数调用中自动记录 trace
    """
    
    def __init__(
        self,
        tracer: MessageTracer,
        event_type: str,
        parent_trace_id: Optional[str] = None
    ):
        self.tracer = tracer
        self.event_type = event_type
        self.parent_trace_id = parent_trace_id
        self.trace_id = generate_trace_id()
        self.start_time: Optional[float] = None
    
    def __enter__(self) -> str:
        self.start_time = time.time()
        return self.trace_id
    
    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        latency_ms = int((time.time() - (self.start_time or 0.0)) * 1000)
        
        if exc_type is None:
            # 成功
            self.tracer.trace_event(
                trace_id=self.trace_id,
                event_type=self.event_type,
                event_data={},
                parent_trace_id=self.parent_trace_id,
                status='success',
                latency_ms=latency_ms
            )
        else:
            # 失败
            self.tracer.trace_event(
                trace_id=self.trace_id,
                event_type=self.event_type,
                event_data={},
                parent_trace_id=self.parent_trace_id,
                status='failed',
                error_msg=str(exc_val),
                latency_ms=latency_ms
            )
        
        return  # 不抑制异常
