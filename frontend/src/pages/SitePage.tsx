import { useEffect, useState } from 'react';
import {
  createPage,
  createSite,
  deletePage,
  deleteSite,
  fetchPages,
  fetchSites,
  fetchSiteStats,
  publishPage,
  updatePage,
  type Site,
  type SitePage,
  type SiteStats,
} from '../services/site';
import { useI18n } from '../i18n';
import { isReadonly } from '../services/auth';

const STATUS_LABELS: Record<string, string> = {
  draft: '草稿',
  published: '已发布',
  archived: '已归档',
};

export function SitePage() {
  const { t } = useI18n();
  const readonly = isReadonly();
  const [sites, setSites] = useState<Site[]>([]);
  const [selected, setSelected] = useState<Site | null>(null);
  const [stats, setStats] = useState<SiteStats | null>(null);
  const [pages, setPages] = useState<SitePage[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // 创建站点
  const [showCreate, setShowCreate] = useState(false);
  const [siteForm, setSiteForm] = useState({ domain: '', name: '', keywords: '' });
  const [creating, setCreating] = useState(false);

  // 创建/编辑页面
  const [showPageForm, setShowPageForm] = useState(false);
  const [editingPage, setEditingPage] = useState<SitePage | null>(null);
  const [pageForm, setPageForm] = useState({
    title: '',
    slug: '',
    content: '',
    content_type: 'blog',
    meta_title: '',
    meta_description: '',
    keywords: '',
  });

  const loadSites = async () => {
    try {
      const data = await fetchSites();
      setSites(data.items);
      if (data.items.length > 0 && !selected) {
        setSelected(data.items[0]);
      }
    } catch (e) {
      console.error(e);
      setError('加载站点失败');
    }
    setLoading(false);
  };

  useEffect(() => {
    loadSites();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (selected) {
      loadSiteData(selected.id);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selected?.id]);

  const loadSiteData = async (siteId: number) => {
    try {
      const [s, p] = await Promise.all([fetchSiteStats(siteId), fetchPages(siteId)]);
      setStats(s);
      setPages(p.items);
    } catch (e) {
      console.error(e);
      setError('加载站点数据失败');
    }
  };

  const handleCreateSite = async () => {
    if (!siteForm.domain.trim()) return;
    setCreating(true);
    setError('');
    try {
      const kw = siteForm.keywords.split(/[,，]/).map((x) => x.trim()).filter(Boolean);
      const site = await createSite({
        domain: siteForm.domain.trim(),
        name: siteForm.name.trim() || undefined,
        target_keywords: kw.length ? kw : undefined,
      });
      setShowCreate(false);
      setSiteForm({ domain: '', name: '', keywords: '' });
      await loadSites();
      setSelected(site);
    } catch (e) {
      setError(e instanceof Error ? e.message : '创建失败');
    }
    setCreating(false);
  };

  const openPageForm = (page?: SitePage) => {
    if (page) {
      setEditingPage(page);
      setPageForm({
        title: page.title,
        slug: page.slug,
        content: page.content ?? '',
        content_type: page.content_type,
        meta_title: page.meta_title ?? '',
        meta_description: page.meta_description ?? '',
        keywords: (page.keywords ?? []).join(', '),
      });
    } else {
      setEditingPage(null);
      setPageForm({ title: '', slug: '', content: '', content_type: 'blog', meta_title: '', meta_description: '', keywords: '' });
    }
    setShowPageForm(true);
  };

  const handleSavePage = async () => {
    if (!selected || !pageForm.title.trim()) return;
    setError('');
    try {
      const kw = pageForm.keywords.split(/[,，]/).map((x) => x.trim()).filter(Boolean);
      const payload = {
        title: pageForm.title.trim(),
        slug: pageForm.slug.trim() || undefined,
        content: pageForm.content.trim() || undefined,
        content_type: pageForm.content_type,
        meta_title: pageForm.meta_title.trim() || undefined,
        meta_description: pageForm.meta_description.trim() || undefined,
        keywords: kw.length ? kw : undefined,
      };
      if (editingPage) {
        await updatePage(selected.id, editingPage.id, payload);
      } else {
        await createPage(selected.id, { ...payload, status: 'draft' });
      }
      setShowPageForm(false);
      loadSiteData(selected.id);
    } catch (e) {
      setError(e instanceof Error ? e.message : '保存失败');
    }
  };

  const handlePublish = async (page: SitePage) => {
    if (!selected) return;
    try {
      await publishPage(selected.id, page.id);
      loadSiteData(selected.id);
    } catch (e) {
      setError(e instanceof Error ? e.message : '发布失败');
    }
  };

  const handleDeletePage = async (page: SitePage) => {
    if (!selected || !confirm(`确认删除『${page.title}』？`)) return;
    try {
      await deletePage(selected.id, page.id);
      loadSiteData(selected.id);
    } catch (e) {
      setError(e instanceof Error ? e.message : '删除失败');
    }
  };

  const handleDeleteSite = async (site: Site) => {
    if (!confirm(`确认删除站点 ${site.domain} ？其下所有页面将被删除。`)) return;
    try {
      await deleteSite(site.id);
      if (selected?.id === site.id) setSelected(null);
      await loadSites();
    } catch (e) {
      setError(e instanceof Error ? e.message : '删除失败');
    }
  };

  if (loading) {
    return (
      <section className="page">
        <h1>AI 增长中心 · 独立站</h1>
        <p>{t('loading')}</p>
      </section>
    );
  }

  return (
    <section className="page">
      <div className="page-header-row">
        <h1>AI 增长中心 · 独立站</h1>
        {!readonly && (
          <button className="btn btn-submit" onClick={() => setShowCreate(true)}>
            + {t('createSite')}
          </button>
        )}
      </div>
      <p className="card-desc">{t('siteBuilderDesc')}</p>

      {error && <p className="error-text">{error}</p>}

      {/* 站点选择 */}
      <div className="site-selector">
        {sites.length === 0 ? (
          <div className="card">
            <p>{t('noSite')}</p>
          </div>
        ) : (
          sites.map((s) => (
            <button
              key={s.id}
              className={`site-chip ${selected?.id === s.id ? 'active' : ''}`}
              onClick={() => setSelected(s)}
            >
              <span className="site-chip-name">{s.name}</span>
              <span className="site-chip-domain">{s.domain}</span>
            </button>
          ))
        )}
      </div>

      {selected && (
        <>
          {/* 统计 */}
          {stats && (
            <div className="grid">
              <div className="card">
                <strong>{t('totalPages')}</strong>
                <div className="card-value">{stats.pages}</div>
                <div className="card-meta">已发布 {stats.published}</div>
              </div>
              <div className="card">
                <strong>{t('totalViews')}</strong>
                <div className="card-value">{stats.total_views}</div>
              </div>
              <div className="card">
                <strong>{t('totalConversions')}</strong>
                <div className="card-value">{stats.total_conversions}</div>
                <div className="card-meta">转化率 {stats.conversion_rate}%</div>
              </div>
              <div className="card">
                <strong>{selected.domain}</strong>
                <div className="card-meta">
                  平台 {selected.platform} · 语言 {selected.default_lang}
                </div>
                {!readonly && (
                  <button className="btn btn-sm btn-cancel" onClick={() => handleDeleteSite(selected)}>
                    删除站点
                  </button>
                )}
              </div>
            </div>
          )}

          {/* 页面管理 */}
          <div className="executions-panel">
            <div className="executions-header">
              <strong>{t('sitePages')}</strong>
              {!readonly && (
                <button className="btn btn-sm btn-submit" onClick={() => openPageForm()}>
                  + {t('newPage')}
                </button>
              )}
            </div>
            {pages.length === 0 ? (
              <p className="executions-empty">{t('noPages')}</p>
            ) : (
              <div className="leads-list">
                {pages.map((p) => (
                  <div key={p.id} className={`lead-item st-${p.status === 'published' ? 'won' : 'new'}`}>
                    <div className="execution-item-main">
                      <span className="execution-employee" onClick={() => openPageForm(p)}>
                        {p.title}
                      </span>
                      <span className="lead-company">/{p.slug}</span>
                      <span className={`execution-status st-${p.status === 'published' ? 'completed' : 'queued'}`}>
                        {STATUS_LABELS[p.status] ?? p.status}
                      </span>
                      <span className="lead-score">
                        {p.views} 浏览 · {p.conversions} 转化
                      </span>
                    </div>
                    <div className="execution-item-sub">
                      <span>
                        {p.content_type} · {p.keywords.length} 关键词
                        {p.published_at ? ` · 发布于 ${new Date(p.published_at).toLocaleDateString()}` : ''}
                      </span>
                      <span className="lead-actions">
                        {!readonly && (
                          <>
                            <button className="btn btn-sm" onClick={() => openPageForm(p)}>编辑</button>
                            {p.status !== 'published' && (
                              <button className="btn btn-sm btn-submit" onClick={() => handlePublish(p)}>发布</button>
                            )}
                            <button className="btn btn-sm btn-cancel" onClick={() => handleDeletePage(p)}>删除</button>
                          </>
                        )}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </>
      )}

      {/* 创建站点 */}
      {showCreate && (
        <div className="modal-overlay" onClick={() => setShowCreate(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h2>{t('createSite')}</h2>
            <div className="form-group">
              <label>{t('siteDomain')} *</label>
              <input
                value={siteForm.domain}
                onChange={(e) => setSiteForm({ ...siteForm, domain: e.target.value })}
                placeholder="mystore.com"
              />
            </div>
            <div className="form-group">
              <label>{t('siteName')}</label>
              <input
                value={siteForm.name}
                onChange={(e) => setSiteForm({ ...siteForm, name: e.target.value })}
                placeholder="My Store"
              />
            </div>
            <div className="form-group">
              <label>{t('targetKeywords')}</label>
              <input
                value={siteForm.keywords}
                onChange={(e) => setSiteForm({ ...siteForm, keywords: e.target.value })}
                placeholder="led lighting, hardware wholesale（逗号分隔）"
              />
            </div>
            <div className="modal-actions">
              <button className="btn btn-cancel" onClick={() => setShowCreate(false)}>{t('cancel')}</button>
              <button className="btn btn-submit" onClick={handleCreateSite} disabled={creating || !siteForm.domain.trim()}>
                {creating ? '创建中...' : t('create')}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 页面表单 */}
      {showPageForm && (
        <div className="modal-overlay" onClick={() => setShowPageForm(false)}>
          <div className="modal modal-wide" onClick={(e) => e.stopPropagation()}>
            <h2>{editingPage ? t('editPage') : t('newPage')}</h2>
            <div className="form-group">
              <label>{t('pageTitle')} *</label>
              <input value={pageForm.title} onChange={(e) => setPageForm({ ...pageForm, title: e.target.value })} />
            </div>
            <div className="form-group">
              <label>{t('pageSlug')}</label>
              <input value={pageForm.slug} onChange={(e) => setPageForm({ ...pageForm, slug: e.target.value })} placeholder="product-led-light" />
            </div>
            <div className="form-group">
              <label>{t('contentType')}</label>
              <select value={pageForm.content_type} onChange={(e) => setPageForm({ ...pageForm, content_type: e.target.value })}>
                <option value="blog">Blog</option>
                <option value="page">Page</option>
                <option value="product">Product</option>
              </select>
            </div>
            <div className="form-group">
              <label>SEO 标题</label>
              <input value={pageForm.meta_title} onChange={(e) => setPageForm({ ...pageForm, meta_title: e.target.value })} />
            </div>
            <div className="form-group">
              <label>SEO 描述</label>
              <textarea rows={2} value={pageForm.meta_description} onChange={(e) => setPageForm({ ...pageForm, meta_description: e.target.value })} />
            </div>
            <div className="form-group">
              <label>关键词（逗号分隔）</label>
              <input value={pageForm.keywords} onChange={(e) => setPageForm({ ...pageForm, keywords: e.target.value })} />
            </div>
            <div className="form-group">
              <label>{t('pageContent')}</label>
              <textarea
                rows={8}
                className="modal-textarea"
                value={pageForm.content}
                onChange={(e) => setPageForm({ ...pageForm, content: e.target.value })}
                placeholder="支持 Markdown..."
              />
            </div>
            <div className="modal-actions">
              <button className="btn btn-cancel" onClick={() => setShowPageForm(false)}>{t('cancel')}</button>
              <button className="btn btn-submit" onClick={handleSavePage} disabled={!pageForm.title.trim()}>
                {t('save')}
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}