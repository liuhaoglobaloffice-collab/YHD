"""
Jarvis Voice Interaction Module

贾维斯级语音交互系统
"""

from .service import JarvisService
from .speech_recognition import SpeechRecognizer
from .state_machine import JarvisState, VoiceInteractionStateMachine
from .tts import TTSBackend, TextToSpeech
from .wake_word import WakeWordConfig, WakeWordDetector
from .language_detector import detect_language, get_asr_language, get_cantonese_system_prompt

__all__ = [
    "JarvisService",
    "JarvisState",
    "VoiceInteractionStateMachine",
    "WakeWordDetector",
    "WakeWordConfig",
    "SpeechRecognizer",
    "TextToSpeech",
    "TTSBackend",
    "detect_language",
    "get_asr_language",
    "get_cantonese_system_prompt",
]
