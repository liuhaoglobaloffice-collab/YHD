"""
S2 多语言自动翻译服务

支持 8 种语言 + 粤语。优先调用 LLM（Ollama/OpenAI）进行真实翻译，
LLM 不可用时回退到 Mock 翻译，保证功能可用。
"""

import logging
import os
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# 支持的语言（代码 -> 中文名 -> 英文名）
SUPPORTED_LANGUAGES: Dict[str, Dict[str, str]] = {
    "zh": {"name": "中文", "en": "Chinese"},
    "en": {"name": "英语", "en": "English"},
    "es": {"name": "西班牙语", "en": "Spanish"},
    "fr": {"name": "法语", "en": "French"},
    "ja": {"name": "日语", "en": "Japanese"},
    "ko": {"name": "韩语", "en": "Korean"},
    "de": {"name": "德语", "en": "German"},
    "ar": {"name": "阿拉伯语", "en": "Arabic"},
    "yue": {"name": "粤语", "en": "Cantonese"},
}

LANGUAGE_LIST = [
    {"code": code, "name": info["name"], "en": info["en"]}
    for code, info in SUPPORTED_LANGUAGES.items()
]


class TranslationService:
    """多语言翻译服务"""

    async def translate(self, text: str, target_lang: str) -> Dict[str, str]:
        """
        将文本翻译为目标语言。

        Returns:
            {"translated": str, "source_lang": str, "mock": bool}
        """
        text = (text or "").strip()
        if not text:
            return {"translated": "", "source_lang": "", "mock": True}
        if target_lang not in SUPPORTED_LANGUAGES:
            raise ValueError(f"不支持的语言: {target_lang}")

        try:
            return await self._translate_with_llm(text, target_lang)
        except Exception as e:  # noqa: BLE001
            logger.warning("translation_llm_failed_falling_back error=%s", str(e))
            return self._mock_translate(text, target_lang)

    async def _translate_with_llm(self, text: str, target_lang: str) -> Dict[str, str]:
        """调用 LLM 翻译。"""
        from src.ai.gateway import get_gateway
        from src.ai.providers import ProviderType
        from uuid import uuid4

        gateway = get_gateway()
        provider_str = os.getenv("LLM_PROVIDER", "mock").lower().strip()
        lang_name = SUPPORTED_LANGUAGES[target_lang]["name"]

        if provider_str == "openai":
            provider = ProviderType.OPENAI
            model = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")
        elif provider_str == "ollama":
            provider = ProviderType.OLLAMA
            model = os.getenv("OLLAMA_DEFAULT_MODEL", "qwen2.5:3b")
        else:
            # 未配置真实 LLM，直接回退 Mock
            return self._mock_translate(text, target_lang)

        prompt = (
            f"你是一名专业翻译。请把以下内容翻译成{lang_name}。"
            f"只输出翻译结果，不要添加任何解释或引号。\n\n{text}"
        )
        response = await gateway.complete(
            provider=provider,
            model_id=model,
            messages=[{"role": "user", "content": prompt}],
            trace_id=uuid4(),
            temperature=0.2,
            max_tokens=2000,
        )
        translated = response.content.strip()
        return {
            "translated": translated,
            "source_lang": "auto",
            "target_lang": target_lang,
            "mock": False,
        }

    def _mock_translate(self, text: str, target_lang: str) -> Dict[str, str]:
        """Mock 翻译（LLM 不可用时）。"""
        lang_name = SUPPORTED_LANGUAGES[target_lang]["name"]
        return {
            "translated": f"[{lang_name}] {text}",
            "source_lang": "auto",
            "target_lang": target_lang,
            "mock": True,
        }
