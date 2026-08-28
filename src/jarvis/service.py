"""
Jarvis Voice Interaction Service - Main Service

贾维斯语音交互主服务
整合唤醒词检测、语音识别、AI处理、语音合成
V4 新增：多语言自动检测 + 粤语全栈支持
"""

import logging
from typing import Callable, Optional

from .language_detector import (
    detect_language,
    get_asr_language,
    get_cantonese_system_prompt,
)
from .speech_recognition import SpeechRecognizer
from .state_machine import JarvisState, VoiceInteractionStateMachine
from .tts import TTSBackend, TextToSpeech
from .wake_word import WakeWordConfig, WakeWordDetector

logger = logging.getLogger(__name__)


# 各语言对应的 System Prompt（用于 LLM 回复风格控制）
SYSTEM_PROMPTS = {
    "cantonese": get_cantonese_system_prompt(),
    "mandarin": (
        "你是 LiuHao AI（鎏灏），一个智能 AI 助手。\n\n"
        "特点：\n"
        "- 用普通话与用户交流\n"
        "- 专业、高效、友好\n"
        "- 在合适的时候可以切换粤语或英语"
    ),
    "english": (
        "You are LiuHao AI, an intelligent AI assistant.\n\n"
        "Features:\n"
        "- Communicate with users in English\n"
        "- Professional, efficient, and friendly\n"
        "- Can switch to Cantonese or Mandarin when appropriate"
    ),
}


class JarvisService:
    """贾维斯语音交互服务

    完整的语音交互流程管理：
    1. 待机等待唤醒
    2. 检测到唤醒词后开始监听
    3. 识别用户语音命令
    4. 处理命令并生成回复
    5. 播放语音回复

    V4 新增：自动检测语言（粤/普/英），切换 ASR 语言 + TTS 后端 + 回复风格。
    """

    def __init__(
        self,
        wake_word_config: Optional[WakeWordConfig] = None,
        asr_language: Optional[str] = None,
        tts_voice: str = "alloy",
        tts_local_voice: str = "zh-HK-HiuGaaiNeural",
        command_handler: Optional[Callable[[str], str]] = None,
        enable_auto_detect: bool = True,
    ):
        """初始化贾维斯服务

        Args:
            wake_word_config: 唤醒词配置
            asr_language: 语音识别语言 (zh/yue/en)，None 为自动检测
            tts_voice: OpenAI TTS 语音风格
            tts_local_voice: 本地 TTS 语音名称（粤语默认 zh-HK-HiuGaaiNeural）
            command_handler: 命令处理函数
            enable_auto_detect: 是否启用多语言自动检测与切换
        """
        self.state_machine = VoiceInteractionStateMachine()
        self.wake_word_detector = WakeWordDetector(wake_word_config)
        self.speech_recognizer = SpeechRecognizer(language=asr_language)
        # 默认使用 OpenAI TTS；检测到粤语时自动切换到 local 后端
        self.tts = TextToSpeech(backend=TTSBackend.OPENAI, voice=tts_voice, local_voice=tts_local_voice)
        self.command_handler = command_handler or self._default_command_handler
        self.enable_auto_detect = enable_auto_detect
        self._current_language: str = "mandarin"  # 当前对话语言

        self._setup_state_callbacks()

        logger.info(
            f"JarvisService initialized: asr_language={asr_language}, "
            f"tts_voice={tts_voice}, auto_detect={enable_auto_detect}"
        )

    def _setup_state_callbacks(self):
        """设置状态机回调"""
        self.state_machine.on_state_enter(JarvisState.LISTENING, self._on_listening)
        self.state_machine.on_state_enter(JarvisState.PROCESSING, self._on_processing)
        self.state_machine.on_state_enter(JarvisState.RESPONDING, self._on_responding)

    def _on_listening(self):
        """进入监听状态"""
        logger.debug("Jarvis is listening...")

    def _on_processing(self):
        """进入处理状态"""
        logger.debug("Jarvis is processing...")

    def _on_responding(self):
        """进入响应状态"""
        logger.debug("Jarvis is responding...")

    def _detect_and_switch(self, text: str) -> str:
        """检测语言并自动切换 ASR + TTS + 回复风格

        Args:
            text: 识别的文本

        Returns:
            检测到的语言 (cantonese/mandarin/english)
        """
        lang = detect_language(text)

        if lang == self._current_language:
            return lang  # 语言未变，无需切换

        logger.info(f"Language changed: {self._current_language} -> {lang}")

        # 切换 ASR 语言
        asr_lang = get_asr_language(lang)
        if asr_lang:
            self.speech_recognizer.language = asr_lang

        # 切换 TTS 后端
        if lang == "cantonese":
            self.tts.switch_backend(TTSBackend.LOCAL, voice=self.tts.local_voice)
        else:
            self.tts.switch_backend(TTSBackend.OPENAI, voice=self.tts.voice)

        self._current_language = lang
        return lang

    async def process_audio_input(self, audio_data: bytes) -> Optional[bytes]:
        """处理语音输入

        V4 流程：识别 → 检测语言 → 切换风格 → 处理 → 合成回复

        Args:
            audio_data: 音频数据 (WAV/MP3)

        Returns:
            回复音频数据 (MP3)，如果没有则返回 None
        """
        self.state_machine.transition_to(JarvisState.LISTENING)

        try:
            # 语音识别
            text = await self.speech_recognizer.transcribe(audio_data)

            if not text:
                logger.warning("No speech recognized")
                self.state_machine.transition_to(JarvisState.IDLE)
                return None

            logger.info(f"Recognized speech: {text}")

            # 唤醒词检测
            if self.wake_word_detector.detect(text):
                command = self.wake_word_detector.extract_command(text)
                if command:
                    text = command
                else:
                    # 只有唤醒词，没有命令
                    self.state_machine.transition_to(JarvisState.IDLE)
                    return None

            # V4: 检测语言并自动切换
            if self.enable_auto_detect:
                self._detect_and_switch(text)

            # 处理命令
            self.state_machine.transition_to(JarvisState.PROCESSING)
            response_text = self.command_handler(text)

            if not response_text:
                logger.warning("No response generated")
                self.state_machine.transition_to(JarvisState.IDLE)
                return None

            # 合成语音回复
            self.state_machine.transition_to(JarvisState.RESPONDING)
            audio_response = await self.tts.synthesize(response_text)

            self.state_machine.transition_to(JarvisState.IDLE)
            return audio_response

        except Exception as e:
            logger.error(f"Voice interaction error: {e}")
            self.state_machine.transition_to(JarvisState.IDLE)
            return None

    def _default_command_handler(self, command: str) -> str:
        """默认命令处理函数

        Args:
            command: 用户命令文本

        Returns:
            回复文本
        """
        # 获取当前语言的 System Prompt
        system_prompt = SYSTEM_PROMPTS.get(self._current_language, SYSTEM_PROMPTS["mandarin"])

        # 这里可以接入 LLM 处理
        # 目前返回简单回复
        reply_map = {
            "cantonese": f"你啱啱講咗：{command}。有咩可以幫到你？",
            "mandarin": f"你刚才说：{command}。有什么可以帮你的？",
            "english": f"You said: {command}. How can I help you?",
        }
        return reply_map.get(self._current_language, reply_map["mandarin"])

    def get_state(self) -> dict:
        """获取当前状态

        Returns:
            state: 当前状态
            duration: 状态持续时间
            previous_state: 上一个状态
        """
        return {
            "state": self.state_machine.current_state.value,
            "duration": self.state_machine.get_state_duration(),
            "previous_state": (
                self.state_machine.previous_state.value
                if self.state_machine.previous_state
                else None
            ),
        }