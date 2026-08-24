"""
事件总线

模块间通信的事件系统
"""

from typing import Dict, List, Callable, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import logging
import asyncio
from collections import defaultdict

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """系统事件类型"""
    
    # 系统事件
    SYSTEM_STARTUP = "system.startup"
    SYSTEM_SHUTDOWN = "system.shutdown"
    SYSTEM_ERROR = "system.error"
    
    # 模块事件
    MODULE_REGISTERED = "module.registered"
    MODULE_UNREGISTERED = "module.unregistered"
    MODULE_ENABLED = "module.enabled"
    MODULE_DISABLED = "module.disabled"
    MODULE_STARTED = "module.started"
    MODULE_STOPPED = "module.stopped"
    MODULE_ERROR = "module.error"
    
    # 业务事件
    SUPPLIER_CREATED = "supplier.created"
    SUPPLIER_UPDATED = "supplier.updated"
    SUPPLIER_DELETED = "supplier.deleted"
    
    TASK_CREATED = "task.created"
    TASK_ASSIGNED = "task.assigned"
    TASK_COMPLETED = "task.completed"
    
    AI_EXPERT_CREATED = "ai_expert.created"
    AI_EXPERT_UPDATED = "ai_expert.updated"
    AI_EXPERT_DELETED = "ai_expert.deleted"
    AI_EXPERT_CALLED = "ai_expert.called"
    
    # 用户事件
    USER_LOGIN = "user.login"
    USER_LOGOUT = "user.logout"
    USER_ACTION = "user.action"
    
    # 自定义事件
    CUSTOM = "custom"


@dataclass
class Event:
    """事件对象"""
    
    # 基本信息
    type: EventType                             # 事件类型
    source: str                                 # 事件源（模块名称）
    data: Dict[str, Any] = field(default_factory=dict)  # 事件数据
    
    # 元数据
    event_id: Optional[str] = None              # 事件ID
    timestamp: datetime = field(default_factory=datetime.now)  # 时间戳
    correlation_id: Optional[str] = None        # 关联ID（用于追踪）
    
    # 优先级
    priority: int = 5                           # 优先级 (1-10, 1最高)
    
    # 状态
    is_processed: bool = False                  # 是否已处理
    error_message: Optional[str] = None         # 错误信息


class EventBus:
    """
    事件总线
    
    单例模式，负责事件的发布和订阅
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        # 订阅者: event_type -> [handlers]
        self._subscribers: Dict[EventType, List[Callable]] = defaultdict(list)
        
        # 异步订阅者
        self._async_subscribers: Dict[EventType, List[Callable]] = defaultdict(list)
        
        # 事件历史（最近1000个）
        self._event_history: List[Event] = []
        self._max_history = 1000
        
        # 统计信息
        self._stats = defaultdict(int)
        
        self._initialized = True
        logger.info("EventBus initialized")
    
    def subscribe(self, 
                  event_type: EventType, 
                  handler: Callable[[Event], None]) -> bool:
        """
        订阅事件（同步）
        
        Args:
            event_type: 事件类型
            handler: 事件处理函数
            
        Returns:
            bool: 订阅是否成功
        """
        try:
            if handler not in self._subscribers[event_type]:
                self._subscribers[event_type].append(handler)
                logger.info(f"Subscribed to event '{event_type.value}'")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Failed to subscribe to event '{event_type.value}': {e}")
            return False
    
    def subscribe_async(self, 
                        event_type: EventType, 
                        handler: Callable[[Event], Any]) -> bool:
        """
        订阅事件（异步）
        
        Args:
            event_type: 事件类型
            handler: 异步事件处理函数
            
        Returns:
            bool: 订阅是否成功
        """
        try:
            if handler not in self._async_subscribers[event_type]:
                self._async_subscribers[event_type].append(handler)
                logger.info(f"Subscribed to event '{event_type.value}' (async)")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Failed to subscribe to event '{event_type.value}': {e}")
            return False
    
    def unsubscribe(self, 
                    event_type: EventType, 
                    handler: Callable) -> bool:
        """
        取消订阅事件
        
        Args:
            event_type: 事件类型
            handler: 事件处理函数
            
        Returns:
            bool: 取消订阅是否成功
        """
        try:
            # 从同步订阅者中移除
            if handler in self._subscribers[event_type]:
                self._subscribers[event_type].remove(handler)
                logger.info(f"Unsubscribed from event '{event_type.value}'")
                return True
            
            # 从异步订阅者中移除
            if handler in self._async_subscribers[event_type]:
                self._async_subscribers[event_type].remove(handler)
                logger.info(f"Unsubscribed from event '{event_type.value}' (async)")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to unsubscribe from event '{event_type.value}': {e}")
            return False
    
    def publish(self, event: Event) -> int:
        """
        发布事件（同步）
        
        Args:
            event: 事件对象
            
        Returns:
            int: 成功处理的订阅者数量
        """
        try:
            # 记录事件
            self._add_to_history(event)
            self._stats[event.type.value] += 1
            
            # 获取订阅者
            handlers = self._subscribers.get(event.type, [])
            
            if not handlers:
                logger.debug(f"No subscribers for event '{event.type.value}'")
                return 0
            
            # 按优先级排序订阅者（可选）
            # handlers = sorted(handlers, key=lambda h: getattr(h, 'priority', 5))
            
            # 调用所有订阅者
            success_count = 0
            for handler in handlers:
                try:
                    handler(event)
                    success_count += 1
                except Exception as e:
                    logger.error(
                        f"Error in event handler for '{event.type.value}': {e}",
                        exc_info=True
                    )
                    event.error_message = str(e)
            
            event.is_processed = True
            logger.debug(
                f"Event '{event.type.value}' published to {success_count} subscribers"
            )
            
            return success_count
            
        except Exception as e:
            logger.error(f"Failed to publish event '{event.type.value}': {e}")
            return 0
    
    async def publish_async(self, event: Event) -> int:
        """
        发布事件（异步）
        
        Args:
            event: 事件对象
            
        Returns:
            int: 成功处理的订阅者数量
        """
        try:
            # 记录事件
            self._add_to_history(event)
            self._stats[event.type.value] += 1
            
            # 获取异步订阅者
            handlers = self._async_subscribers.get(event.type, [])
            
            if not handlers:
                logger.debug(f"No async subscribers for event '{event.type.value}'")
                return 0
            
            # 并发调用所有订阅者
            tasks = []
            for handler in handlers:
                try:
                    task = asyncio.create_task(handler(event))
                    tasks.append(task)
                except Exception as e:
                    logger.error(
                        f"Error creating task for '{event.type.value}': {e}",
                        exc_info=True
                    )
            
            # 等待所有任务完成
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 统计成功数量
            success_count = sum(1 for r in results if not isinstance(r, Exception))
            
            # 记录错误
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(
                        f"Error in async event handler for '{event.type.value}': {result}",
                        exc_info=True
                    )
                    event.error_message = str(result)
            
            event.is_processed = True
            logger.debug(
                f"Event '{event.type.value}' published to {success_count} async subscribers"
            )
            
            return success_count
            
        except Exception as e:
            logger.error(f"Failed to publish async event '{event.type.value}': {e}")
            return 0
    
    def _add_to_history(self, event: Event):
        """将事件添加到历史记录"""
        self._event_history.append(event)
        
        # 保持历史记录大小
        if len(self._event_history) > self._max_history:
            self._event_history.pop(0)
    
    def get_history(self, 
                    event_type: Optional[EventType] = None,
                    limit: int = 100) -> List[Event]:
        """
        获取事件历史
        
        Args:
            event_type: 筛选特定类型的事件
            limit: 返回数量限制
            
        Returns:
            List[Event]: 事件列表（最新的在前）
        """
        history = self._event_history[::-1]  # 反转，最新的在前
        
        if event_type:
            history = [e for e in history if e.type == event_type]
        
        return history[:limit]
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取统计信息
        
        Returns:
            Dict: 统计信息
        """
        return {
            "total_events": sum(self._stats.values()),
            "event_breakdown": dict(self._stats),
            "total_subscribers": sum(len(h) for h in self._subscribers.values()),
            "total_async_subscribers": sum(len(h) for h in self._async_subscribers.values()),
            "history_size": len(self._event_history),
        }
    
    def clear_history(self):
        """清空事件历史"""
        self._event_history.clear()
        logger.info("Event history cleared")
    
    def reset(self):
        """重置事件总线（用于测试）"""
        self._subscribers.clear()
        self._async_subscribers.clear()
        self._event_history.clear()
        self._stats.clear()
        logger.info("EventBus reset")
