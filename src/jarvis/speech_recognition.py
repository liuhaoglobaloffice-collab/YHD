"""
Jarvis Speech Recognition - ASR Module

使用 OpenAI Whisper 进行本地语音识别
支持普通话、粤语、英语
"""

import io
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class SpeechRecognizer:
    """语音识别器

    使用 OpenAI Whisper API 进行语音转文字
    """

    def __init__(self, model: str = "whisper-1", language: Optional[str] = None):
        """初始化语音识别器

        Args:
            model: Whisper 模型名称
            language: 语言代码 (zh/yue/en), None 为自动检测
        """
        self.model = model
        self.language = language
        logger.info(f"Speech recognizer initialized: model={model}, language={language}")

    async def transcribe(self, audio_data: bytes) -> str:
        """转录音频为文字

        Args:
            audio_data: 音频数据 (WAV/MP3/等)

        Returns:
            识别的文本
        """
        try:
            # 注意：实际使用时需要配置 OpenAI API key
            # 这里提供框架代码
            from openai import AsyncOpenAI

            client = AsyncOpenAI()

            # 创建音频文件对象
            audio_file = io.BytesIO(audio_data)
            audio_file.name = "audio.wav"

            # 调用 Whisper API
            transcript = await client.audio.transcriptions.create(
                model=self.model, file=audio_file, language=self.language, response_format="text"
            )

            text = transcript.strip()
            logger.info(f"Transcribed text: {text}")
            return text

        except Exception as e:
            logger.error(f"Transcription error: {e}")
            return ""

    async def transcribe_file(self, audio_path: Path) -> str:
        """从文件转录音频

        Args:
            audio_path: 音频文件路径

        Returns:
            识别的文本
        """
        with open(audio_path, "rb") as f:
            audio_data = f.read()
        return await self.transcribe(audio_data)
