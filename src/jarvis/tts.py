"""
Jarvis Text-to-Speech Module

支持多后端 TTS 引擎：
- openai: OpenAI TTS API（默认，支持普通话/英语，不支持粤语）
- local: 本地 TTS 引擎（支持粤语，需额外安装依赖与模型文件）
"""

import logging
import os
from abc import ABC, abstractmethod
from enum import Enum
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class TTSBackend(str, Enum):
    """TTS 后端引擎类型"""
    OPENAI = "openai"
    LOCAL = "local"


class TTSBackendBase(ABC):
    """TTS 后端抽象基类"""

    @abstractmethod
    async def synthesize(self, text: str) -> bytes:
        """合成语音，返回 MP3 音频数据"""
        ...


class OpenAITTSBackend(TTSBackendBase):
    """OpenAI TTS API 后端"""

    def __init__(self, voice: str = "alloy", model: str = "tts-1", speed: float = 1.0):
        self.voice = voice
        self.model = model
        self.speed = speed

    async def synthesize(self, text: str) -> bytes:
        try:
            from openai import AsyncOpenAI

            client = AsyncOpenAI()
            response = await client.audio.speech.create(
                model=self.model, voice=self.voice, input=text, speed=self.speed
            )
            return response.content
        except Exception as e:
            logger.error(f"OpenAI TTS synthesis error: {e}")
            raise


class LocalTTSBackend(TTSBackendBase):
    """本地 TTS 引擎（支持粤语）.

    使用 edge-tts（Microsoft Edge TTS）作为后端，支持粤语（zh-HK）。
    需要安装: pip install edge-tts

    注意：edge-tts 需要网络连接至 Microsoft TTS 服务，不是纯离线方案。
    如需完全离线，可替换为 VITS / CosyVoice 本地模型（需额外下载模型文件）。
    """

    def __init__(self, voice: str = "zh-HK-HiuGaaiNeural", rate: str = "+0%", pitch: str = "+0Hz"):
        """
        Args:
            voice: TTS 语音名称，粤语推荐 zh-HK-HiuGaaiNeural（女声）或 zh-HK-WanLungNeural（男声）
            rate: 语速调整，如 "+10%" / "-10%"
            pitch: 音调调整，如 "+10Hz" / "-10Hz"
        """
        self.voice = voice
        self.rate = rate
        self.pitch = pitch

    async def synthesize(self, text: str) -> bytes:
        try:
            import edge_tts

            communicate = edge_tts.Communicate(
                text,
                voice=self.voice,
                rate=self.rate,
                pitch=self.pitch,
            )
            audio_data = b""
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_data += chunk["data"]
            return audio_data
        except ImportError:
            logger.error(
                "edge-tts 未安装。请运行: pip install edge-tts\n"
                "或切换回 openai 后端: tts_backend=openai"
            )
            raise
        except Exception as e:
            logger.error(f"Local TTS synthesis error: {e}")
            raise


class TextToSpeech:
    """文字转语音（多后端适配器）

    支持切换 TTS 后端引擎，默认使用 OpenAI TTS API。
    """

    def __init__(
        self,
        backend: TTSBackend = TTSBackend.OPENAI,
        voice: str = "alloy",
        local_voice: str = "zh-HK-HiuGaaiNeural",
        model: str = "tts-1",
        speed: float = 1.0,
    ):
        """
        Args:
            backend: TTS 后端引擎
            voice: OpenAI TTS 语音风格 (alloy/echo/fable/onyx/nova/shimmer)
            local_voice: 本地 TTS 语音名称（粤语默认 zh-HK-HiuGaaiNeural）
            model: OpenAI TTS 模型
            speed: 语速 0.25-4.0
        """
        self.backend_type = backend
        self.voice = voice
        self.local_voice = local_voice
        self.model = model
        self.speed = speed
        self._backend: Optional[TTSBackendBase] = None

    @property
    def backend(self) -> TTSBackendBase:
        """懒加载 TTS 后端实例"""
        if self._backend is None:
            if self.backend_type == TTSBackend.LOCAL:
                self._backend = LocalTTSBackend(voice=self.local_voice)
            else:
                self._backend = OpenAITTSBackend(voice=self.voice, model=self.model, speed=self.speed)
        return self._backend

    def switch_backend(self, backend: TTSBackend, voice: Optional[str] = None) -> None:
        """运行时切换 TTS 后端

        Args:
            backend: 目标后端
            voice: 语音名称（OpenAI 后端需 alloy/echo/...；本地后端需 zh-HK-xxx）
        """
        self.backend_type = backend
        if voice:
            if backend == TTSBackend.LOCAL:
                self.local_voice = voice
            else:
                self.voice = voice
        # 强制重新创建后端实例
        self._backend = None

    async def synthesize(self, text: str) -> bytes:
        """合成语音

        Args:
            text: 要合成的文本

        Returns:
            MP3 音频数据
        """
        return await self.backend.synthesize(text)

    async def synthesize_to_file(self, text: str, output_path: Path) -> bool:
        """合成语音并保存到文件

        Args:
            text: 要合成的文本
            output_path: 输出文件路径

        Returns:
            是否成功
        """
        try:
            audio_data = await self.synthesize(text)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(audio_data)
            logger.info(f"Saved TTS audio to {output_path}")
            return True
        except Exception as e:
            logger.error(f"TTS save error: {e}")
            return False