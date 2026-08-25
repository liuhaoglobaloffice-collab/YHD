"""
Jarvis Voice Interaction Service - Main Service

贾维斯语音交互主服务
整合唤醒词检测、语音识别、AI处理、语音合成
"""

import logging
from typing import Callable, Optional

from .speech_recognition import SpeechRecognizer
from .state_machine import JarvisState, VoiceInteractionStateMachine
from .tts import TextToSpeech
from .wake_word import WakeWordConfig, WakeWordDetector

logger = logging.getLogger(__name__)


class JarvisService:
    """贾维斯语音交互服务

    完整的语音交互流程管理：
    1. 待机等待唤醒
    2. 检测到唤醒词后开始监听
    3. 识别用户语音命令
    4. 处理命令并生成回复
    5. 播放语音回复
    """

    def __init__(
        self,
        wake_word_config: Optional[WakeWordConfig] = None,
        asr_language: Optional[str] = None,
        tts_voice: str = "alloy",
        command_handler: Optional[Callable[[str], str]] = None,
    ):
        """初始化贾维斯服务

        Args:
            wake_word_config: 唤醒词配置
            asr_language: 语音识别语言 (zh/yue/en)
            tts_voice: TTS 语音风格
            command_handler: 命令处理函数
        """
        self.state_machine = VoiceInteractionStateMachine()
        self.wake_word_detector = WakeWordDetector(wake_word_config)
        self.speech_recognizer = SpeechRecognizer(language=asr_language)
        self.tts = TextToSpeech(voice=tts_voice)

        self.command_handler = command_handler or self._default_command_handler

        # 注册状态回调
        self._setup_state_callbacks()

        logger.info("Jarvis service initialized")

    def _setup_state_callbacks(self):
        """设置状态转换回调"""
        self.state_machine.on_state_enter(
            JarvisState.LISTENING, lambda: logger.info("👂 Jarvis is listening...")
        )
        self.state_machine.on_state_enter(
            JarvisState.PROCESSING, lambda: logger.info("🧠 Jarvis is processing...")
        )
        self.state_machine.on_state_enter(
            JarvisState.RESPONDING, lambda: logger.info("🗣️ Jarvis is responding...")
        )

    async def process_audio_input(self, audio_data: bytes) -> Optional[bytes]:
        """处理音频输入

        完整的交互流程：
        1. 识别语音为文字
        2. 检测唤醒词
        3. 提取命令
        4. 处理命令
        5. 生成语音回复

        Args:
            audio_data: 输入的音频数据

        Returns:
            语音回复音频数据，如果没有则返回 None
        """
        try:
            # 1. 语音识别
            text = await self.speech_recognizer.transcribe(audio_data)
            if not text:
                logger.warning("No speech recognized")
                return None

            logger.info(f"Recognized speech: {text}")

            # 2. 检测唤醒词
            if self.state_machine.current_state == JarvisState.IDLE:
                if not self.wake_word_detector.detect(text):
                    logger.debug("Wake word not detected, staying in IDLE")
                    return None

                # 检测到唤醒词，转到监听状态
                self.state_machine.transition_to(JarvisState.LISTENING)

                # 尝试提取命令
                command = self.wake_word_detector.extract_command(text)
                if not command:
                    # 只说了唤醒词，等待下一次输入
                    response_text = "我在，请说"
                    self.state_machine.transition_to(JarvisState.RESPONDING)
                    audio_response = await self.tts.synthesize(response_text)
                    self.state_machine.transition_to(JarvisState.IDLE)
                    return audio_response
            else:
                # 已在监听状态，直接作为命令处理
                command = text

            # 3. 处理命令
            self.state_machine.transition_to(JarvisState.PROCESSING)
            response_text = self.command_handler(command)

            # 4. 生成语音回复
            self.state_machine.transition_to(JarvisState.RESPONDING)
            audio_response = await self.tts.synthesize(response_text)

            # 5. 回到待机
            self.state_machine.transition_to(JarvisState.IDLE)

            return audio_response

        except Exception as e:
            logger.error(f"Error processing audio input: {e}")
            self.state_machine.transition_to(JarvisState.ERROR)
            self.state_machine.reset()
            return None

    def _default_command_handler(self, command: str) -> str:
        """默认命令处理器"""
        logger.info(f"Processing command: {command}")

        # 简单的默认响应
        if "你好" in command or "hello" in command.lower():
            return "你好，我是鎏灏，有什么可以帮你的？"
        elif "时间" in command or "time" in command.lower():
            from datetime import datetime

            now = datetime.now()
            return f"现在是 {now.strftime('%H点%M分')}"
        else:
            return f"收到指令：{command}。功能开发中。"

    def get_state(self) -> dict:
        """获取当前状态"""
        return {
            "state": self.state_machine.current_state.value,
            "duration": self.state_machine.get_state_duration(),
            "previous_state": (
                self.state_machine.previous_state.value
                if self.state_machine.previous_state
                else None
            ),
        }
