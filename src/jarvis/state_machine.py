"""
Jarvis Voice Interaction System - State Machine

状态机管理语音交互的不同阶段：
1. IDLE (待机) - 等待唤醒词
2. LISTENING (监听) - 录音并识别
3. PROCESSING (处理) - AI处理请求
4. RESPONDING (响应) - TTS播放回复
"""

import logging
from datetime import datetime
from enum import Enum
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class JarvisState(Enum):
    """贾维斯系统状态"""

    IDLE = "idle"  # 待机，等待唤醒
    LISTENING = "listening"  # 监听用户输入
    PROCESSING = "processing"  # 处理请求
    RESPONDING = "responding"  # 播放响应
    ERROR = "error"  # 错误状态


class VoiceInteractionStateMachine:
    """语音交互状态机

    管理贾维斯系统的状态转换和事件处理
    """

    def __init__(self):
        self.current_state = JarvisState.IDLE
        self.previous_state: Optional[JarvisState] = None
        self.state_start_time: Optional[datetime] = None
        self.callbacks: dict[JarvisState, list[Callable]] = {state: [] for state in JarvisState}

    def transition_to(self, new_state: JarvisState) -> bool:
        """状态转换

        Args:
            new_state: 目标状态

        Returns:
            是否成功转换
        """
        if not self._is_valid_transition(self.current_state, new_state):
            logger.warning(
                f"Invalid state transition: {self.current_state.value} -> {new_state.value}"
            )
            return False

        logger.info(f"State transition: {self.current_state.value} -> {new_state.value}")
        self.previous_state = self.current_state
        self.current_state = new_state
        self.state_start_time = datetime.now()

        # 触发状态回调
        self._trigger_callbacks(new_state)

        return True

    def _is_valid_transition(self, from_state: JarvisState, to_state: JarvisState) -> bool:
        """检查状态转换是否有效"""
        valid_transitions = {
            JarvisState.IDLE: [JarvisState.LISTENING, JarvisState.ERROR],
            JarvisState.LISTENING: [JarvisState.PROCESSING, JarvisState.IDLE, JarvisState.ERROR],
            JarvisState.PROCESSING: [JarvisState.RESPONDING, JarvisState.IDLE, JarvisState.ERROR],
            JarvisState.RESPONDING: [JarvisState.IDLE, JarvisState.ERROR],
            JarvisState.ERROR: [JarvisState.IDLE],
        }

        return to_state in valid_transitions.get(from_state, [])

    def on_state_enter(self, state: JarvisState, callback: Callable):
        """注册状态进入回调"""
        self.callbacks[state].append(callback)

    def _trigger_callbacks(self, state: JarvisState):
        """触发状态回调"""
        for callback in self.callbacks[state]:
            try:
                callback()
            except Exception as e:
                logger.error(f"Callback error in state {state.value}: {e}")

    def reset(self):
        """重置到初始状态"""
        self.transition_to(JarvisState.IDLE)

    def get_state_duration(self) -> float:
        """获取当前状态持续时间（秒）"""
        if self.state_start_time:
            return (datetime.now() - self.state_start_time).total_seconds()
        return 0.0
