import { useEffect, useState } from 'react';
import {
  analyzeKeywords,
  fetchRankings,
  fetchSEOContents,
  generateSEOContent,
  trackRankings,
  type KeywordInfo,
  type KeywordRank,
  type SEOContentResult,
  type SEOSavedContent,
} from '../services/site';
import { useI18n } from '../i18n';
import { isReadonly } from '../services/auth';

const TREND_LABELS: Record<string, string> = {
  up: '上升',
  down: '下降',
  stable: '持平',
  new: '新收录',
};

// P1-G5.2: 数据来源徽标（诚实展示，不伪装 AI 生成）
const SOURCE_TYPE_LABELS: Record<string, string> = {
  LLM: 'AI 生成',
  RULE_BASED: '模板生成',
  NOT_CONFIGURED: '模板生成（LLM 未配置）',
};

const sourceLabel = (sourceType?: string, method?: string): string => {
  if (sourceType && SOURCE_TYPE_LABELS[sourceType]) return SOURCE_TYPE_LABELS[sourceType];
  return method === 'ai' ? 'AI 生成' : '模板生成';
};

export function SEOPage() {
  const { t } = useI18n();
  const readonly = isReadonly();

  // 关键词分析
  const [keywordsInput, setKeywordsInput] = useState('');
  const [analyzed, setAnalyzed] = useState<KeywordInfo[]>([]);
  const [analyzing, setAnalyzing] = useState(false);

  // 内容生成
  const [genKeyword, setGenKeyword] = useState('');
  const [generating, setGenerating] = useState(false);
  const [generated, setGenerated] = useState<SEOContentResult | null>(null);

  // 排名跟踪
  const [rankings, setRankings] = useState<KeywordRank[]>([]);
  const [tracking, setTracking] = useState(false);

  // 历史内容
  const [contents, setContents] = useState<SEOSavedContent[]>([]);
  const [error, setError] = useState('');

  const loadSaved = async () => {
    try {
      const [r, c] = await Promise.all([fetchRankings(), fetchSEOContents()]);
      setRankings(r);
      setContents(c);
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    loadSaved();
  }, []);

  const handleAnalyze = async () => {
    setAnalyzing(true);
    setError('');
    try {
      const kws = keywordsInput.split(/[,，]/).map((x) => x.trim()).filter(Boolean);
      const result = await analyzeKeywords(kws.length ? kws : undefined);
      setAnalyzed(result);
    } catch (e) {
      setError(e instanceof Error ? e.message : '关键词分析失败');
    }
    setAnalyzing(false);
  };

  const handleGenerate = async (keyword?: string) => {
    const kw = (keyword ?? genKeyword).trim();
    if (!kw) return;
    setGenerating(true);
    setError('');
    try {
      const result = await generateSEOContent(kw, true);
      setGenerated(result);
      loadSaved();
    } catch (e) {
      setError(e instanceof Error ? e.message : '生成失败');
    }
    setGenerating(false);
  };

  const handleTrack = async (kws?: string[]) => {
    setTracking(true);
    setError('');
    try {
      const list = kws ?? (analyzed.length ? analyzed.map((k) => k.keyword) : []);
      if (list.length === 0) {
        setError('请先分析关键词或输入关键词');
        setTracking(false);
        return;
      }
      const result = await trackRankings(list, true);
      setRankings(result);
      loadSaved();
    } catch (e) {
      setError(e instanceof Error ? e.message : '排名跟踪失败');
    }
    setTracking(false);
  };

  return (
    <section className="page">
      <h1>AI 增长中心 · SEO</h1>
      <p className="card-desc">{t('seoToolboxDesc')}</p>

      {error && <p className="error-text">{error}</p>}

      {/* 关键词分析 */}
      <div className="import-panel">
        <div className="executions-header">
          <strong>{t('keywordAnalysis')}</strong>
        </div>
        <div className="composer-row">
          <input
            placeholder="输入关键词（逗号分隔，留空则用推荐词）"
            value={keywordsInput}
            onChange={(e) => setKeywordsInput(e.target.value)}
          />
          {!readonly && (
            <>
              <button className="btn btn-submit" onClick={handleAnalyze} disabled={analyzing}>
                {analyzing ? '分析中...' : t('analyzeKeywords')}
              </button>
              {analyzed.length > 0 && (
                <button className="btn btn-sm" onClick={() => handleTrack()} disabled={tracking}>
                  跟踪这些排名
                </button>
              )}
            </>
          )}
        </div>
        {analyzed.length > 0 && (
          <div className="kw-list">
            {analyzed.map((k) => (
              <div key={k.keyword} className="kw-item">
                <div className="execution-item-main">
                  <span className="execution-employee">{k.keyword}</span>
                  <span className="kw-metrics">
                    月搜 {k.volume.toLocaleString()} · 难度 {k.difficulty} · 机会 {k.opportunity}
                  </span>
                </div>
                <div className="execution-item-sub">
                  <span className="kw-suggestions">
                    {k.suggestions.slice(0, 3).map((s) => (
                      <span key={s} className="kw-sugg-chip">{s}</span>
                    ))}
                  </span>
                  <button
                    className="btn btn-sm btn-submit"
                    onClick={() => handleGenerate(k.keyword)}
                    disabled={generating}
                  >
                    生成文章
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* 内容生成 */}
      <div className="import-panel">
        <div className="executions-header">
          <strong>{t('contentGenerator')}</strong>
        </div>
        <div className="composer-row">
          <input
            placeholder="输入关键词生成 SEO 文章..."
            value={genKeyword}
            onChange={(e) => setGenKeyword(e.target.value)}
          />
          {!readonly && (
            <button className="btn btn-submit" onClick={() => handleGenerate()} disabled={generating || !genKeyword.trim()}>
              {generating ? '生成中...' : t('generate')}
            </button>
          )}
        </div>
        {generated && (
          <div className="generated-content">
            <div className="executions-header">
              <strong>{generated.title}</strong>
              <span className={`analysis-method`}>{sourceLabel(generated.source_type, generated.method)}</span>
            </div>
            <div className="execution-item-sub">
              <span>URL: /{generated.suggested_slug}</span>
              <span>意图: {generated.search_intent}</span>
            </div>
            {generated.llm_error && (
              <p className="error-text">LLM 调用失败已降级为规则模板：{generated.llm_error}</p>
            )}
            {generated.meta_description && (
              <div className="dimension">
                <strong>Meta 描述</strong>
                <p>{generated.meta_description}</p>
              </div>
            )}
            {generated.outline && generated.outline.length > 0 && (
              <div className="dimension">
                <strong>大纲</strong>
                <p>{generated.outline.join('\n')}</p>
              </div>
            )}
            {generated.content && (
              <div className="analysis-report-body">
                <strong>正文</strong>
                <pre>{generated.content}</pre>
              </div>
            )}
          </div>
        )}
      </div>

      {/* 排名跟踪 */}
      <div className="executions-panel">
        <div className="executions-header">
          <strong>{t('rankTracking')}</strong>
          <span className="executions-count">{rankings.length} 个关键词</span>
        </div>
        {rankings.length === 0 ? (
          <p className="executions-empty">{t('noRankings')}</p>
        ) : (
          <div className="leads-list">
            {rankings.map((r) => (
              <div key={r.keyword} className="lead-item">
                <div className="execution-item-main">
                  <span className="execution-employee">{r.keyword}</span>
                  <span className={`rank-position ${r.rank ? (r.rank <= 10 ? 'top' : 'mid') : 'none'}`}>
                    {r.rank ? `#${r.rank}` : '未进前100'}
                  </span>
                  <span className={`rank-trend trend-${r.trend}`}>
                    {r.trend === 'up' ? '▲' : r.trend === 'down' ? '▼' : r.trend === 'stable' ? '►' : '✦'} {TREND_LABELS[r.trend]}
                  </span>
                  <span className="lead-score">{r.search_volume?.toLocaleString()} 月搜</span>
                </div>
                <div className="execution-item-sub">
                  <span className="execution-prompt">{r.url}</span>
                  <span className="execution-time">
                    前次: {r.previous_rank ?? '-'}
                    {r.checked_at ? ` · 检查于 ${new Date(r.checked_at).toLocaleDateString()}` : ''}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* 已生成内容 */}
      {contents.length > 0 && (
        <div className="executions-panel">
          <div className="executions-header">
            <strong>{t('generatedContents')}</strong>
            <span className="executions-count">{contents.length} 篇</span>
          </div>
          <div className="leads-list">
            {contents.map((c) => (
              <div key={c.id} className="lead-item">
                <div className="execution-item-main">
                  <span className="execution-employee">{c.title}</span>
                  <span className={`analysis-method`}>{sourceLabel(c.source_type, c.method)}</span>
                </div>
                <div className="execution-item-sub">
                  <span>/{c.suggested_slug} · {c.keyword}</span>
                  <span className="execution-time">{new Date(c.created_at).toLocaleString()}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}