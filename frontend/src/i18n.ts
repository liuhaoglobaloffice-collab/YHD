export type Locale = 'zh' | 'zh-HK' | 'en';

export const DEFAULT_LOCALE: Locale = 'zh';

export const localeOptions: Array<{ value: Locale; label: string }> = [
  { value: 'zh', label: '中文' },
  { value: 'zh-HK', label: '廣東話' },
  { value: 'en', label: 'English' },
];

const translations: Record<Locale, Record<string, string>> = {
  zh: {
    appTitle: '鎏灏 AI-OS',
    language: '语言',
    dashboard: '总览',
    aiTeam: 'AI 团队',
    workflow: '工作流',
    business: '业务',
    settings: '设置',
    help: '帮助',
    voice: '语音交互',
    assistant: 'Jarvis 助手',
  },
  'zh-HK': {
    appTitle: '鎏灏 AI-OS',
    language: '語言',
    dashboard: '總覽',
    aiTeam: 'AI 團隊',
    workflow: '工作流',
    business: '業務',
    settings: '設定',
    help: '幫助',
    voice: '語音互動',
    assistant: 'Jarvis 助手',
  },
  en: {
    appTitle: 'LiuHao AI-OS',
    language: 'Language',
    dashboard: 'Overview',
    aiTeam: 'AI Team',
    workflow: 'Workflow',
    business: 'Business',
    settings: 'Settings',
    help: 'Help',
    voice: 'Voice',
    assistant: 'Jarvis Assistant',
  },
};

export const getText = (key: string, locale: Locale = DEFAULT_LOCALE): string => {
  if (locale === 'zh-HK') return translations['zh-HK']?.[key] ?? translations.zh[key] ?? key;
  return translations[locale]?.[key] ?? translations[DEFAULT_LOCALE][key] ?? key;
};
