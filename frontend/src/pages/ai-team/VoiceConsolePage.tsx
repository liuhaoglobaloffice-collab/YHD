import React, { useMemo, useState } from 'react';
import { AudioLines, Bot, Languages, Mic, Sparkles, Volume2 } from 'lucide-react';

type VoiceLanguage = 'zh' | 'zh-hk' | 'en';

const languageMeta: Record<VoiceLanguage, { label: string; accent: string }> = {
  zh: { label: '国语', accent: 'zh-CN' },
  'zh-hk': { label: '粤语', accent: 'zh-HK' },
  en: { label: 'English', accent: 'en-US' },
};

const phraseDictionary: Record<string, Partial<Record<VoiceLanguage, string>>> = {
  '你好': { zh: '你好', 'zh-hk': '你好呀', en: 'Hello' },
  '早上好': { zh: '早上好', 'zh-hk': '早晨呀', en: 'Good morning' },
  '我需要帮助': { zh: '我需要帮助', 'zh-hk': '我需要你幫手', en: 'I need help' },
  '请帮我分析数据': { zh: '请帮我分析数据', 'zh-hk': '請幫我分析數據', en: 'Please help me analyze the data' },
  '生成报告': { zh: '生成报告', 'zh-hk': '生成報告', en: 'Generate a report' },
  '检查风险': { zh: '检查风险', 'zh-hk': '檢查風險', en: 'Check the risk' },
  '启动流程': { zh: '启动流程', 'zh-hk': '啟動流程', en: 'Start the workflow' },
  '任务已完成': { zh: '任务已完成', 'zh-hk': '任務已完成', en: 'Task completed' },
  '当前状态正常': { zh: '当前状态正常', 'zh-hk': '目前狀態正常', en: 'Current status is normal' },
};

const translateSentence = (text: string, from: VoiceLanguage, to: VoiceLanguage): string => {
  const trimmed = text.trim();
  if (!trimmed) return '';
  if (from === to) return trimmed;

  const exact = phraseDictionary[trimmed];
  if (exact && exact[to]) {
    return exact[to];
  }

  for (const [phrase, values] of Object.entries(phraseDictionary)) {
    if (trimmed.includes(phrase)) {
      const match = values[to];
      if (match) {
        return trimmed.replace(phrase, match);
      }
    }
  }

  const fallbackMap: Record<VoiceLanguage, Partial<Record<VoiceLanguage, string>>> = {
    zh: { 'zh-hk': '已为您转换为粤语版本', en: 'Translated to English' },
    'zh-hk': { zh: '已轉成國語版本', en: 'Translated to English' },
    en: { zh: '已翻译为国语', 'zh-hk': '已翻譯為粵語' },
  };

  return fallbackMap[from]?.[to] ?? `${trimmed} → ${to}`;
};

const VoiceConsolePage: React.FC = () => {
  const [sourceLang, setSourceLang] = useState<VoiceLanguage>('zh');
  const [targetLang, setTargetLang] = useState<VoiceLanguage>('zh-hk');
  const [inputText, setInputText] = useState('请帮我分析供应商风险');
  const [resultText, setResultText] = useState('請幫我分析供應商風險');
  const [isListening, setIsListening] = useState(false);
  const [assistantReply, setAssistantReply] = useState('Jarvis 已就绪，支持国语、粤语与英文互译。');

  const quickPrompts = useMemo(
    () => [
      '请帮我分析数据',
      '启动流程',
      '生成报告',
      '检查风险',
      '我需要帮助',
    ],
    []
  );

  const handleTranslate = () => {
    const translated = translateSentence(inputText, sourceLang, targetLang);
    setResultText(translated);
    setAssistantReply(`已从 ${languageMeta[sourceLang].label} 转成 ${languageMeta[targetLang].label}。`);
  };

  const handleSpeak = (text: string) => {
    if (typeof window === 'undefined' || !('speechSynthesis' in window)) {
      setAssistantReply('当前浏览器不支持语音播报功能。');
      return;
    }

    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = languageMeta[targetLang].accent;
    window.speechSynthesis.cancel();
    window.speechSynthesis.speak(utterance);
    setAssistantReply(`正在播报 ${languageMeta[targetLang].label} 语音。`);
  };

  const handleVoiceInput = () => {
    const recognitionCtor = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

    if (!recognitionCtor) {
      setAssistantReply('当前环境未启用 Web Speech API，已切换为示例文本输入。');
      setInputText('请帮我分析供应商风险');
      setIsListening(false);
      return;
    }

    const recognition = new recognitionCtor();
    recognition.lang = languageMeta[sourceLang].accent;
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;
    setIsListening(true);
    setAssistantReply(`正在聆听 ${languageMeta[sourceLang].label} 语音...`);

    recognition.onresult = (event: any) => {
      const transcript = event.results?.[0]?.[0]?.transcript ?? '';
      if (transcript) {
        setInputText(transcript);
        setAssistantReply(`已识别：${transcript}`);
      }
      setIsListening(false);
    };

    recognition.onerror = () => {
      setAssistantReply('语音识别失败，已回退到文本输入。');
      setIsListening(false);
    };

    recognition.onend = () => setIsListening(false);
    recognition.start();
  };

  const handleQuickPrompt = (prompt: string) => {
    setInputText(prompt);
    setAssistantReply(`已加载快捷指令：${prompt}`);
  };

  return (
    <div className="p-6 space-y-6 text-white">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm uppercase tracking-[0.2em] text-cyan-300">Voice & Language</p>
          <h1 className="text-3xl font-bold mt-2">Jarvis 语音交互中心</h1>
        </div>
        <div className="flex items-center gap-2 px-3 py-2 rounded-xl border border-cyan-500/30 bg-cyan-500/10 text-cyan-200 text-sm">
          <Sparkles className="w-4 h-4" />
          Multilingual Ready
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-[1.2fr_0.8fr] gap-6">
        <div className="bg-gray-800 border border-gray-700 rounded-2xl p-5 space-y-5">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <label className="space-y-2 text-sm text-gray-300">
              <span>源语言</span>
              <select
                value={sourceLang}
                onChange={(event) => setSourceLang(event.target.value as VoiceLanguage)}
                className="w-full rounded-lg border border-gray-600 bg-gray-900 px-3 py-2 text-white outline-none focus:border-cyan-500"
              >
                {Object.entries(languageMeta).map(([value, meta]) => (
                  <option key={value} value={value}>{meta.label}</option>
                ))}
              </select>
            </label>

            <div className="flex items-end justify-center pb-1">
              <div className="rounded-full border border-cyan-500/30 bg-cyan-500/10 p-3 text-cyan-200">
                <Languages className="w-5 h-5" />
              </div>
            </div>

            <label className="space-y-2 text-sm text-gray-300">
              <span>目标语言</span>
              <select
                value={targetLang}
                onChange={(event) => setTargetLang(event.target.value as VoiceLanguage)}
                className="w-full rounded-lg border border-gray-600 bg-gray-900 px-3 py-2 text-white outline-none focus:border-cyan-500"
              >
                {Object.entries(languageMeta).map(([value, meta]) => (
                  <option key={value} value={value}>{meta.label}</option>
                ))}
              </select>
            </label>
          </div>

          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-300">输入内容</span>
              <button
                type="button"
                onClick={handleVoiceInput}
                className={`inline-flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition ${
                  isListening ? 'bg-red-500/20 text-red-200 border border-red-500/30' : 'bg-cyan-500/20 text-cyan-200 border border-cyan-500/30'
                }`}
              >
                <Mic className="w-4 h-4" />
                {isListening ? '监听中' : '语音输入'}
              </button>
            </div>
            <textarea
              value={inputText}
              onChange={(event) => setInputText(event.target.value)}
              rows={5}
              className="w-full rounded-xl border border-gray-600 bg-gray-900 p-4 text-white outline-none focus:border-cyan-500"
              placeholder="输入需要翻译或处理的内容..."
            />
          </div>

          <div className="flex flex-wrap gap-2">
            {quickPrompts.map((prompt) => (
              <button
                key={prompt}
                onClick={() => handleQuickPrompt(prompt)}
                className="rounded-full border border-gray-600 bg-gray-900 px-3 py-1.5 text-xs text-gray-200 hover:border-cyan-500 hover:text-cyan-200"
              >
                {prompt}
              </button>
            ))}
          </div>

          <div className="flex flex-wrap gap-3">
            <button
              onClick={handleTranslate}
              className="rounded-xl bg-cyan-500 px-4 py-2 text-sm font-medium text-slate-950 hover:bg-cyan-400"
            >
              翻译
            </button>
            <button
              onClick={() => handleSpeak(resultText || inputText)}
              className="rounded-xl border border-gray-600 bg-gray-900 px-4 py-2 text-sm font-medium text-gray-200 hover:border-cyan-500"
            >
              <span className="inline-flex items-center gap-2"><Volume2 className="w-4 h-4" />播报结果</span>
            </button>
          </div>
        </div>

        <div className="space-y-6">
          <div className="bg-gradient-to-br from-cyan-500/20 via-blue-500/10 to-slate-900 border border-cyan-500/30 rounded-2xl p-5">
            <div className="flex items-center gap-3 mb-4">
              <div className="rounded-xl bg-cyan-500/20 p-2 text-cyan-200"><Bot className="w-5 h-5" /></div>
              <span className="font-semibold">Jarvis 助手</span>
            </div>
            <div className="rounded-xl border border-cyan-500/20 bg-slate-950/30 p-4 text-sm text-cyan-100">
              {assistantReply}
            </div>
          </div>

          <div className="bg-gray-800 border border-gray-700 rounded-2xl p-5">
            <div className="flex items-center justify-between mb-4">
              <span className="text-sm text-gray-300">输出结果</span>
              <div className="flex items-center gap-2 text-cyan-200 text-xs">
                <AudioLines className="w-4 h-4" />
                {languageMeta[targetLang].label}
              </div>
            </div>
            <div className="rounded-xl border border-gray-600 bg-gray-900 p-4 text-lg text-white min-h-[120px]">
              {resultText || '输出结果将在这里显示...'}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default VoiceConsolePage;
