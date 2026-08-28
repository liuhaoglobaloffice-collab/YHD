"""
Jarvis Language Detector

多语言自动检测：粤语 / 普通话 / 英语 / 其他
基于特征字符快速判断，零依赖。
"""

import re
from typing import Optional

# 粤语特征字（口语常用，普通话几乎不用）
CANTONESE_MARKERS = {
    '係', '喺', '嘅', '咗', '啦', '嘞', '啵', '冇', '嚟', '乜', '咩',
    '佢', '哋', '唔', '啲', '先', '吓', '嘛', '㗎', '啫', '嗰', '咁',
    '哋', '囉', '咯', '喎', '吖', '唓', '咋', '㖭', '𠵱',
}

# 粤语特有词汇（二字及以上）
CANTONESE_PHRASES = {
    '平靚正', '有冇', '係唔係', '唔該', '唔好', '多謝', '點樣',
    '邊度', '幾時', '點解', '即係', '仲有', '搞掂', '食咗',
    '做緊', '睇吓', '嚟緊', '知唔知', '得唔得', '可唔可以',
    '唔使', '唔緊要', '唔知', '唔得', '搞掂', '點算', '乜嘢',
    '好嘢', '細路', '老豆', '老母', '屋企', '返工', '放工',
}


def detect_language(text: str) -> str:
    """检测文本语言：'cantonese' | 'mandarin' | 'english' | 'other'

    基于粤语特征字和词汇的启发式检测，适合在线路由决策。
    """
    if not text or not text.strip():
        return "other"

    stripped = text.strip()

    # 检测英文（拼音文字占比高）
    latin_chars = sum(1 for c in stripped if c.isascii() and c.isalpha())
    total_chars = sum(1 for c in stripped if c.isalpha())
    if total_chars > 0 and latin_chars / total_chars > 0.6:
        return "english"

    # 检测粤语
    # 1. 特征字计数
    marker_count = sum(1 for c in stripped if c in CANTONESE_MARKERS)
    # 2. 粤语短语匹配
    phrase_count = sum(1 for p in CANTONESE_PHRASES if p in stripped)

    # 阈值：至少 2 个特征字或 1 个粤语短语
    if marker_count >= 2 or phrase_count >= 1:
        return "cantonese"

    # 有中文字符但无粤语特征 → 普通话
    if any('\u4e00' <= c <= '\u9fff' for c in stripped):
        return "mandarin"

    return "other"


def get_asr_language(detected: str) -> Optional[str]:
    """将检测结果映射到 Whisper 语言代码。"""
    return {
        "cantonese": "yue",
        "mandarin": "zh",
        "english": "en",
    }.get(detected)


def get_cantonese_system_prompt() -> str:
    """获取粤语优化的 System Prompt。"""
    return (
        "你係 LiuHao AI（鎏灏），一個識講粵語嘅 AI 助手。\n\n"
        "特點：\n"
        "- 用粵語同用戶傾偈（對話）\n"
        "- 明白粵語口語同俚語\n"
        "- 支持繁體字同簡體字\n"
        "- 理解中英夾雜嘅講法\n\n"
        "講嘢風格：\n"
        "- 親切自然，唔使太正式\n"
        "- 用粵語口語化表達\n"
        "- 適當使用語氣詞（啦、喎、咯）\n"
        "- 保持專業但唔失幽默\n\n"
        "例子：\n"
        '用戶："幫我搵個平靚正嘅供應商"\n'
        '你："好嘅！我即刻幫你搵，搵到 156 間供應商，幫你揀咗 5 間性價比最高嘅俾你睇下..."'
    )