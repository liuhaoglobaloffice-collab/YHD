"""
Jarvis Voice Interaction API Routes

语音交互 REST API 端点
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import Response
from pydantic import BaseModel

from ...identity.models import User
from ...jarvis import JarvisService, TTSBackend
from ...jarvis.wake_word import WakeWordConfig
from ..dependencies import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/jarvis", tags=["jarvis"])

# 全局 Jarvis 服务实例
_jarvis_service: Optional[JarvisService] = None


def get_jarvis_service() -> JarvisService:
    """获取 Jarvis 服务实例"""
    global _jarvis_service
    if _jarvis_service is None:
        # 初始化服务
        wake_config = WakeWordConfig(wake_words=["嘿鎏灏", "hey liuhao", "jarvis", "贾维斯"])
        _jarvis_service = JarvisService(wake_word_config=wake_config)
    return _jarvis_service


# ============================================================
# Request/Response Schemas
# ============================================================


class JarvisStateResponse(BaseModel):
    """Jarvis 状态响应"""

    state: str
    duration: float
    previous_state: Optional[str]


class JarvisConfigResponse(BaseModel):
    """Jarvis 配置响应"""

    wake_words: list[str]
    asr_language: Optional[str]
    tts_backend: str
    tts_voice: str
    current_language: str
    auto_detect: bool


# ============================================================
# API Endpoints
# ============================================================


@router.post("/interact", response_class=Response)
async def voice_interact(
    audio: UploadFile = File(..., description="Audio file (WAV/MP3/etc)"),
    current_user: User = Depends(get_current_user),
    jarvis: JarvisService = Depends(get_jarvis_service),
):
    """语音交互端点

    上传音频文件，返回语音回复

    流程：
    1. 上传用户语音 (WAV/MP3)
    2. Jarvis 识别、处理、生成回复
    3. 返回语音回复 (MP3)
    """
    try:
        # 读取音频数据
        audio_data = await audio.read()

        if not audio_data:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty audio file")

        logger.info(f"Processing audio input from user {current_user.id}")

        # 处理音频
        response_audio = await jarvis.process_audio_input(audio_data)

        if response_audio:
            return Response(
                content=response_audio,
                media_type="audio/mpeg",
                headers={"Content-Disposition": "inline; filename=jarvis_response.mp3"},
            )
        else:
            # 没有生成回复
            raise HTTPException(
                status_code=status.HTTP_204_NO_CONTENT, detail="No response generated"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Voice interaction error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/state", response_model=JarvisStateResponse)
async def get_jarvis_state(jarvis: JarvisService = Depends(get_jarvis_service)):
    """获取 Jarvis 当前状态

    返回状态机的当前状态、持续时间等信息
    """
    state = jarvis.get_state()
    return JarvisStateResponse(**state)


@router.post("/reset")
async def reset_jarvis(
    jarvis: JarvisService = Depends(get_jarvis_service),
    current_user: User = Depends(get_current_user),
):
    """重置 Jarvis 到初始状态

    将状态机重置为 IDLE 状态
    """
    jarvis.state_machine.reset()
    logger.info(f"Jarvis reset by user {current_user.id}")
    return {"message": "Jarvis reset to IDLE state"}


@router.get("/config", response_model=JarvisConfigResponse)
async def get_jarvis_config(jarvis: JarvisService = Depends(get_jarvis_service)):
    """获取 Jarvis 配置信息"""
    return JarvisConfigResponse(
        wake_words=jarvis.wake_word_detector.config.wake_words,
        asr_language=jarvis.speech_recognizer.language,
        tts_backend=jarvis.tts.backend_type.value,
        tts_voice=jarvis.tts.voice,
        current_language=jarvis._current_language,
        auto_detect=jarvis.enable_auto_detect,
    )
