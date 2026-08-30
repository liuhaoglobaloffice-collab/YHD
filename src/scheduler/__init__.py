"""Business Scheduler — P0 自主经营调度模块。

老板长期不在线（Boss Offline Mode）的执行基座：
- 自动执行 active 状态的 Goal（复用 GoalService 真实执行链）
- 可选自动激活 draft 目标（SCHEDULER_AUTO_ACTIVATE，默认关闭）
- 过期记忆清理（复用 AgentMemoryStore 四级分级策略）

纯 asyncio 后台循环实现，零新增依赖；执行结果全部走既有持久化链路。
"""

from src.scheduler.service import (
    BusinessScheduler,
    get_business_scheduler,
    start_business_scheduler,
    stop_business_scheduler,
)

__all__ = [
    "BusinessScheduler",
    "get_business_scheduler",
    "start_business_scheduler",
    "stop_business_scheduler",
]
