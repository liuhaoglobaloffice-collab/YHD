import { useCallback, useEffect, useState } from 'react';
import { useI18n } from '../i18n';
import {
  KnowledgeDocument,
  KnowledgeMemory,
  KnowledgeSearchResult,
  listDocuments,
  listMemories,
  semanticSearch,
  uploadDocument,
} from '../services/knowledge';

type Strategy = 'semantic' | 'keyword' | 'hybrid';

export function KnowledgePage() {
  const { t } = useI18n();

  const [documents, setDocuments] = useState<KnowledgeDocument[]>([]);
  const [memories, setMemories] = useState<KnowledgeMemory[]>([]);
  const [loadingDocs, setLoadingDocs] = useState(true);
  const [error, setError] = useState('');

  // Upload state
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState('');
  const [uploading, setUploading] = useState(false);
  const [uploadMsg, setUploadMsg] = useState('');

  // Search state
  const [query, setQuery] = useState('');
  const [strategy, setStrategy] = useState<Strategy>('semantic');
  const [searching, setSearching] = useState(false);
  const [results, setResults] = useState<KnowledgeSearchResult[]>([]);
  const [searchMsg, setSearchMsg] = useState('');

  const refresh = useCallback(async () => {
    setError('');
    try {
      const [docs, mems] = await Promise.all([listDocuments(), listMemories()]);
      setDocuments(docs);
      setMemories(mems);
    } catch (e) {
      console.error('knowledge load failed', e);
      setError('知识数据加载失败，请检查后端服务');
    } finally {
      setLoadingDocs(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const handleUpload = async () => {
    if (!file) {
      setUploadMsg('请先选择文件');
      return;
    }
    setUploading(true);
    setUploadMsg('');
    try {
      const data = (await uploadDocument(file, title || undefined)) as {
        chunk_count?: number;
        document_id?: string;
      };
      setUploadMsg(
        `上传成功：文档 ${data.document_id ?? ''}，已生成 ${data.chunk_count ?? 0} 个分块并完成向量化`
      );
      setFile(null);
      setTitle('');
      await refresh();
    } catch (e) {
      setUploadMsg(e instanceof Error ? e.message : '上传失败');
    } finally {
      setUploading(false);
    }
  };

  const handleSearch = async () => {
    if (!query.trim()) {
      setSearchMsg('请输入检索问题');
      return;
    }
    setSearching(true);
    setSearchMsg('');
    setResults([]);
    try {
      const res = await semanticSearch(query.trim(), strategy);
      setResults(res.results);
      setSearchMsg(
        `命中 ${res.total} 条结果（${
          strategy === 'keyword' ? '关键词' : strategy === 'hybrid' ? '混合' : '语义向量'
        }检索）`
      );
    } catch (e) {
      setSearchMsg(e instanceof Error ? e.message : '检索失败');
    } finally {
      setSearching(false);
    }
  };

  const fmtTime = (s?: string) => {
    if (!s) return '';
    try {
      return new Date(s).toLocaleString();
    } catch {
      return s;
    }
  };

  return (
    <section className="page">
      <h1>{t('knowledgeBase' as never)}</h1>
      <p className="page-subtitle">
        文档上传 → 分块 → Embedding 向量化 → 语义检索 → AI 员工调用，全链路真实数据
      </p>

      {error && <p className="error-text">{error}</p>}

      <div className="grid" style={{ gridTemplateColumns: '1fr 1fr' }}>
        {/* Upload */}
        <div className="card">
          <strong>上传知识文档</strong>
          <div className="card-meta">
            支持 TXT / Markdown / PDF / Word，上传后自动分块并生成向量
          </div>
          <div style={{ marginTop: 12, display: 'flex', flexDirection: 'column', gap: 8 }}>
            <input
              type="file"
              accept=".txt,.md,.pdf,.doc,.docx,.csv"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            />
            <input
              type="text"
              placeholder="文档标题（可选）"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              style={{ padding: '6px 10px' }}
            />
            <button className="btn btn-primary" onClick={handleUpload} disabled={uploading}>
              {uploading ? '正在分块与向量化…' : '上传并建立索引'}
            </button>
            {uploadMsg && (
              <div className={uploadMsg.includes('失败') ? 'error-text' : 'card-meta'}>
                {uploadMsg}
              </div>
            )}
          </div>
        </div>

        {/* Semantic search */}
        <div className="card">
          <strong>语义检索（真实 Embedding）</strong>
          <div className="card-meta">
            用自然语言提问，AI 按语义相似度从文档与记忆中检索
          </div>
          <div style={{ marginTop: 12, display: 'flex', flexDirection: 'column', gap: 8 }}>
            <input
              type="text"
              placeholder="例如：新供应商准入需要做哪些风险审查？"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
              style={{ padding: '6px 10px' }}
            />
            <select
              value={strategy}
              onChange={(e) => setStrategy(e.target.value as Strategy)}
              style={{ padding: '6px 10px' }}
            >
              <option value="semantic">语义向量检索</option>
              <option value="hybrid">混合检索（关键词 + 语义）</option>
              <option value="keyword">关键词检索</option>
            </select>
            <button className="btn btn-primary" onClick={handleSearch} disabled={searching}>
              {searching ? '正在生成向量并检索…' : '检索'}
            </button>
            {searchMsg && <div className="card-meta">{searchMsg}</div>}
          </div>

          {results.length > 0 && (
            <div style={{ marginTop: 12, display: 'flex', flexDirection: 'column', gap: 8 }}>
              {results.map((r, i) => (
                <div className="card" key={`${r.id}-${i}`} style={{ marginBottom: 0 }}>
                  <div className="card-meta">
                    <span>#{i + 1}</span>
                    <span style={{ marginLeft: 8 }}>相似度 {(r.score ?? 0).toFixed(3)}</span>
                    <span style={{ marginLeft: 8 }}>
                      来源：{r.source_type || r.source || 'document'}
                    </span>
                  </div>
                  <div style={{ marginTop: 6, fontSize: 13, lineHeight: 1.6 }}>
                    {r.title && <strong>{r.title}：</strong>}
                    {(r.content || r.snippet || r.text || '').slice(0, 300)}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Documents */}
      <h2 style={{ marginTop: 24 }}>知识文档（{documents.length}）</h2>
      {loadingDocs ? (
        <p>{t('loading' as never)}</p>
      ) : documents.length === 0 ? (
        <div className="card">
          <div className="card-meta">暂无文档，上传第一份知识文档开始构建企业知识库</div>
        </div>
      ) : (
        <div className="grid">
          {documents.map((d) => (
            <div className="card" key={d.id}>
              <strong>{d.title || d.filename || d.id}</strong>
              <div className="card-meta">
                <span>类型：{d.file_type || '未知'}</span>
                <span style={{ marginLeft: 8 }}>时间：{fmtTime(d.created_at)}</span>
              </div>
              <div className="card-status">{d.status || 'unknown'}</div>
            </div>
          ))}
        </div>
      )}

      {/* Memories */}
      <h2 style={{ marginTop: 24 }}>AI 记忆（{memories.length}）</h2>
      {memories.length === 0 ? (
        <div className="card">
          <div className="card-meta">暂无记忆，AI 员工执行任务后会自动沉淀记忆</div>
        </div>
      ) : (
        <div className="grid">
          {memories.slice(0, 12).map((m, i) => (
            <div className="card" key={m.memory_id || m.id || i}>
              <div className="card-meta">
                <span>类型：{m.memory_type || 'memory'}</span>
                <span style={{ marginLeft: 8 }}>{fmtTime(m.created_at)}</span>
              </div>
              <div style={{ marginTop: 6, fontSize: 13, lineHeight: 1.6 }}>
                {(m.content || m.value || m.key || '').slice(0, 200)}
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
