"""
Jarvis Voice Recognition Module - Wake Word Detection

唤醒词检测：支持 "嘿鎏灏", "Hey LiuHao" 等多种激活方式
"""

import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class WakeWordConfig:
    """唤醒词配置"""

    wake_words: list[str]
    sensitivity: float = 0.7  # 灵敏度 0-1
    timeout: float = 5.0  # 超时时间（秒）


class WakeWordDetector:
    """唤醒词检测器

    检测用户是否说出了唤醒词来激活贾维斯
    """

    DEFAULT_WAKE_WORDS = [
        "嘿鎏灏",
        "hey liuhao",
        "hi liuhao",
        "jarvis",
        "贾维斯",
        "小灏",
    ]

    def __init__(self, config: Optional[WakeWordConfig] = None):
        self.config = config or WakeWordConfig(wake_words=self.DEFAULT_WAKE_WORDS)
        logger.info(f"Wake word detector initialized with: {self.config.wake_words}")

    def detect(self, text: str) -> bool:
        """检测文本中是否包含唤醒词

        Args:
            text: 识别的文本

        Returns:
            是否检测到唤醒词
        """
        text_lower = text.lower().strip()

        for wake_word in self.config.wake_words:
            if wake_word.lower() in text_lower:
                logger.info(f"Wake word detected: '{wake_word}' in '{text}'")
                return True

        return False

    def extract_command(self, text: str) -> Optional[str]:
        """从文本中提取命令（去除唤醒词）

        Args:
            text: 原始文本

        Returns:
            提取的命令，如果没有则返回 None
        """
        text_lower = text.lower().strip()

        for wake_word in self.config.wake_words:
            wake_lower = wake_word.lower()
            if wake_lower in text_lower:
                # 移除唤醒词及其之前的内容
                idx = text_lower.find(wake_lower)
                command = text[idx + len(wake_word) :].strip()

                if command:
                    logger.info(f"Extracted command: '{command}'")
                    return command

        return None
