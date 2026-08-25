"""
Jarvis Text-to-Speech Module

本地 TTS 语音合成
支持普通话、粤语、英语
"""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class TextToSpeech:
    """文字转语音

    使用 OpenAI TTS API 或本地 TTS 引擎
    """

    def __init__(self, voice: str = "alloy", model: str = "tts-1", speed: float = 1.0):
        """初始化 TTS

        Args:
            voice: 语音风格 (alloy/echo/fable/onyx/nova/shimmer)
            model: TTS 模型
            speed: 语速 0.25-4.0
        """
        self.voice = voice
        self.model = model
        self.speed = speed
        logger.info(f"TTS initialized: voice={voice}, model={model}, speed={speed}")

    async def synthesize(self, text: str) -> bytes:
        """合成语音

        Args:
            text: 要合成的文本

        Returns:
            音频数据 (MP3)
        """
        try:
            # 注意：实际使用时需要配置 OpenAI API key
            from openai import AsyncOpenAI

            client = AsyncOpenAI()

            response = await client.audio.speech.create(
                model=self.model, voice=self.voice, input=text, speed=self.speed
            )

            # 获取音频数据
            audio_data = b""
            async for chunk in response.iter_bytes():
                audio_data += chunk

            logger.info(f"Synthesized {len(audio_data)} bytes for text: {text[:50]}...")
            return audio_data

        except Exception as e:
            logger.error(f"TTS synthesis error: {e}")
            return b""

    async def synthesize_to_file(self, text: str, output_path: Path) -> bool:
        """合成语音并保存到文件

        Args:
            text: 要合成的文本
            output_path: 输出文件路径

        Returns:
            是否成功
        """
        audio_data = await self.synthesize(text)
        if audio_data:
            output_path.write_bytes(audio_data)
            logger.info(f"Saved TTS audio to {output_path}")
            return True
        return False
