import { useEffect, useState, useCallback } from 'react';
import { useI18n } from '../i18n';

const API_BASE = import.meta.env?.VITE_API_BASE ?? '';
const API_PREFIX = '/api/v1';

function getToken(): string {
  return localStorage.getItem('liuhao_auth_token') ?? '';
}

function headers() {
  const t = getToken();
  return t ? { Authorization: `Bearer ${t}`, 'Content-Type': 'application/json' } : { 'Content-Type': 'application/json' };
}

interface CompanyInfo {
  name: string;
  domain: string;
  industry: string;
  country: string;
  employees: number;
  created_at: string;
}

interface Product {
  id: number;
  name: string;
  category: string | null;
  description: string | null;
  price: number | null;
  unit: string | null;
  moq: number | null;
  image_url: string | null;
  status: string;
  tags: string | null;
  created_at: string;
  updated_at: string;
}

interface ProductFormData {
  name: string;
  category: string;
  description: string;
  price: string;
  unit: string;
  moq: string;
  tags: string;
}

const emptyForm: ProductFormData = {
  name: '', category: '', description: '',
  price: '', unit: '件', moq: '', tags: '',
};

export function CompanyPage() {
  const { t } = useI18n();
  const [info, setInfo] = useState<CompanyInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [editMode, setEditMode] = useState(false);
  const [form, setForm] = useState({ name: '', domain: '', industry: '', country: '' });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  // 产品目录
  const [products, setProducts] = useState<Product[]>([]);
  const [prodTotal, setProdTotal] = useState(0);
  const [prodPage, setProdPage] = useState(1);
  const [prodLoading, setProdLoading] = useState(false);
  const [search, setSearch] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [editingProd, setEditingProd] = useState<Product | null>(null);
  const [prodForm, setProdForm] = useState<ProductFormData>(emptyForm);
  const [prodSaving, setProdSaving] = useState(false);
  const [categories, setCategories] = useState<string[]>([]);

  const loadInfo = async () => {
    try {
      const res = await fetch(`${API_BASE}${API_PREFIX}/auth/me`, { headers: headers() });
      if (res.ok) {
        const user = await res.json();
        setInfo({
          name: user.username || '鎏灏贸易',
          domain: 'liuhao-trade.com',
          industry: '进出口贸易',
          country: '中国',
          employees: 10,
          created_at: user.created_at || new Date().toISOString(),
        });
        setForm({
          name: user.username || '鎏灏贸易',
          domain: 'liuhao-trade.com',
          industry: '进出口贸易',
          country: '中国',
        });
      }
    } catch (e) {
      console.error(e);
    }
    setLoading(false);
  };

  const loadProducts = useCallback(async (page = 1) => {
    setProdLoading(true);
    try {
      const params = new URLSearchParams();
      params.set('page', String(page));
      params.set('page_size', '20');
      if (search) params.set('search', search);
      if (categoryFilter) params.set('category', categoryFilter);
      const res = await fetch(`${API_BASE}${API_PREFIX}/products?${params}`, { headers: headers() });
      if (res.ok) {
        const data = await res.json();
        setProducts(data.items || []);
        setProdTotal(data.total || 0);
        setProdPage(data.page || 1);
        // 收集分类
        const cats = new Set<string>();
        (data.items as Product[]).forEach((p: Product) => { if (p.category) cats.add(p.category); });
        setCategories(prev => {
          const all = new Set([...prev, ...cats]);
          return [...all].sort();
        });
      }
    } catch (e) {
      console.error(e);
    }
    setProdLoading(false);
  }, [search, categoryFilter]);

  useEffect(() => { loadInfo(); }, []);
  useEffect(() => { loadProducts(1); }, [loadProducts]);

  const handleSave = async () => {
    setSaving(true);
    setError('');
    try {
      setInfo((prev) => prev ? { ...prev, name: form.name, domain: form.domain,
        industry: form.industry, country: form.country } : prev);
      setEditMode(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : '保存失败');
    }
    setSaving(false);
  };

  // 产品操作
  const openCreateForm = () => {
    setEditingProd(null);
    setProdForm(emptyForm);
    setShowForm(true);
  };

  const openEditForm = (p: Product) => {
    setEditingProd(p);
    setProdForm({
      name: p.name,
      category: p.category || '',
      description: p.description || '',
      price: p.price != null ? String(p.price) : '',
      unit: p.unit || '件',
      moq: p.moq != null ? String(p.moq) : '',
      tags: p.tags || '',
    });
    setShowForm(true);
  };

  const handleProdSave = async () => {
    if (!prodForm.name.trim()) { setError('产品名称不能为空'); return; }
    setProdSaving(true);
    setError('');
    try {
      const payload = {
        name: prodForm.name.trim(),
        category: prodForm.category || null,
        description: prodForm.description || null,
        price: prodForm.price ? parseFloat(prodForm.price) : null,
        unit: prodForm.unit || '件',
        moq: prodForm.moq ? parseInt(prodForm.moq) : null,
        tags: prodForm.tags || null,
      };
      const url = editingProd
        ? `${API_BASE}${API_PREFIX}/products/${editingProd.id}`
        : `${API_BASE}${API_PREFIX}/products`;
      const method = editingProd ? 'PUT' : 'POST';
      const res = await fetch(url, { method, headers: headers(), body: JSON.stringify(payload) });
      if (res.ok) {
        setShowForm(false);
        setEditingProd(null);
        await loadProducts(prodPage);
      } else {
        const err = await res.json();
        setError(err.detail || '保存失败');
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : '保存失败');
    }
    setProdSaving(false);
  };

  const handleDelete = async (id: number) => {
    if (!confirm('确认删除此产品？')) return;
    try {
      const res = await fetch(`${API_BASE}${API_PREFIX}/products/${id}`, {
        method: 'DELETE', headers: headers(),
      });
      if (res.ok) {
        await loadProducts(prodPage);
      } else {
        const err = await res.json();
        setError(err.detail || '删除失败');
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : '删除失败');
    }
  };

  if (loading) return <section className="page"><h1>企业管理</h1><p>{t('loading')}</p></section>;

  return (
    <section className="page">
      <div className="page-header-row">
        <h1>企业管理</h1>
        <button className="btn btn-submit" onClick={() => setEditMode(!editMode)}>
          {editMode ? '取消' : '编辑'}
        </button>
      </div>
      <p className="card-desc">管理企业基本信息与产品目录</p>

      {error && <p className="error-text" style={{ marginBottom: 12 }}>{error}</p>}

      {/* 企业信息 */}
      {info && (
        <div className="import-panel" style={{ marginBottom: 24 }}>
          <div className="executions-header">
            <strong>企业信息</strong>
          </div>
          <div className="form-group" style={{ padding: 16 }}>
            <label>企业名称</label>
            {editMode ? (
              <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
            ) : (
              <p style={{ color: 'rgba(255,255,255,0.8)', marginTop: 4 }}>{info.name}</p>
            )}
          </div>
          <div className="form-group" style={{ padding: '0 16px 16px' }}>
            <label>域名</label>
            {editMode ? (
              <input value={form.domain} onChange={(e) => setForm({ ...form, domain: e.target.value })} />
            ) : (
              <p style={{ color: 'rgba(255,255,255,0.8)', marginTop: 4 }}>{info.domain}</p>
            )}
          </div>
          <div className="form-group" style={{ padding: '0 16px 16px' }}>
            <label>行业</label>
            {editMode ? (
              <input value={form.industry} onChange={(e) => setForm({ ...form, industry: e.target.value })} />
            ) : (
              <p style={{ color: 'rgba(255,255,255,0.8)', marginTop: 4 }}>{info.industry}</p>
            )}
          </div>
          <div className="form-group" style={{ padding: '0 16px 16px' }}>
            <label>国家</label>
            {editMode ? (
              <input value={form.country} onChange={(e) => setForm({ ...form, country: e.target.value })} />
            ) : (
              <p style={{ color: 'rgba(255,255,255,0.8)', marginTop: 4 }}>{info.country}</p>
            )}
          </div>
          {editMode && (
            <div style={{ padding: '0 16px 16px' }}>
              <button className="btn btn-submit" onClick={handleSave} disabled={saving}>
                {saving ? '保存中...' : '保存'}
              </button>
            </div>
          )}
          <div style={{ padding: '0 16px 16px', display: 'flex', gap: 24 }}>
            <div>
              <span className="card-meta">AI 员工</span>
              <p style={{ fontSize: 24, fontWeight: 700, color: '#4cc9f0' }}>{info.employees}</p>
            </div>
            <div>
              <span className="card-meta">注册时间</span>
              <p style={{ fontSize: 14, color: 'rgba(255,255,255,0.6)', marginTop: 4 }}>
                {new Date(info.created_at).toLocaleDateString()}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* 产品目录 */}
      <div className="import-panel">
        <div className="executions-header">
          <strong>产品目录</strong>
          <span className="executions-count">{prodTotal} 个产品</span>
        </div>

        {/* 工具栏 */}
        <div style={{ padding: '12px 16px', display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center', borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
          <input
            placeholder="搜索产品..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            style={{ flex: 1, minWidth: 160, padding: '6px 10px', borderRadius: 6, border: '1px solid rgba(255,255,255,0.15)', background: 'rgba(0,0,0,0.3)', color: '#fff' }}
          />
          <select
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value)}
            style={{ padding: '6px 10px', borderRadius: 6, border: '1px solid rgba(255,255,255,0.15)', background: 'rgba(0,0,0,0.3)', color: '#fff' }}
          >
            <option value="">全部分类</option>
            {categories.map(c => <option key={c} value={c}>{c}</option>)}
          </select>
          <button className="btn btn-submit" onClick={openCreateForm}>+ 添加产品</button>
        </div>

        {/* 产品表单 */}
        {showForm && (
          <div style={{ padding: 16, borderBottom: '1px solid rgba(255,255,255,0.06)', background: 'rgba(76,201,240,0.04)' }}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 12 }}>
              <div className="form-group">
                <label>产品名称 *</label>
                <input value={prodForm.name} onChange={(e) => setProdForm({ ...prodForm, name: e.target.value })} placeholder="如: LED 灯管 60W" />
              </div>
              <div className="form-group">
                <label>分类</label>
                <input value={prodForm.category} onChange={(e) => setProdForm({ ...prodForm, category: e.target.value })} placeholder="如: 照明" />
              </div>
              <div className="form-group" style={{ gridColumn: 'span 2' }}>
                <label>描述</label>
                <textarea value={prodForm.description} onChange={(e) => setProdForm({ ...prodForm, description: e.target.value })} placeholder="产品描述..." rows={2} style={{ padding: '6px 10px', borderRadius: 6, border: '1px solid rgba(255,255,255,0.15)', background: 'rgba(0,0,0,0.3)', color: '#fff', width: '100%', resize: 'vertical' }} />
              </div>
              <div className="form-group">
                <label>价格 (USD)</label>
                <input type="number" value={prodForm.price} onChange={(e) => setProdForm({ ...prodForm, price: e.target.value })} placeholder="0.00" />
              </div>
              <div className="form-group">
                <label>单位</label>
                <input value={prodForm.unit} onChange={(e) => setProdForm({ ...prodForm, unit: e.target.value })} placeholder="件" />
              </div>
              <div className="form-group">
                <label>最小起订量</label>
                <input type="number" value={prodForm.moq} onChange={(e) => setProdForm({ ...prodForm, moq: e.target.value })} placeholder="100" />
              </div>
              <div className="form-group">
                <label>标签</label>
                <input value={prodForm.tags} onChange={(e) => setProdForm({ ...prodForm, tags: e.target.value })} placeholder="逗号分隔" />
              </div>
            </div>
            <div style={{ display: 'flex', gap: 8 }}>
              <button className="btn btn-submit" onClick={handleProdSave} disabled={prodSaving}>
                {prodSaving ? '保存中...' : editingProd ? '更新' : '创建'}
              </button>
              <button className="btn btn-cancel" onClick={() => { setShowForm(false); setEditingProd(null); }}>取消</button>
            </div>
          </div>
        )}

        {/* 产品列表 */}
        {prodLoading ? (
          <p className="executions-empty">加载中...</p>
        ) : products.length === 0 ? (
          <p className="executions-empty">暂无产品，点击上方按钮添加</p>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.08)', color: 'rgba(255,255,255,0.5)', fontSize: 12 }}>
                  <th style={{ padding: '10px 12px', textAlign: 'left' }}>名称</th>
                  <th style={{ padding: '10px 12px', textAlign: 'left' }}>分类</th>
                  <th style={{ padding: '10px 12px', textAlign: 'right' }}>价格</th>
                  <th style={{ padding: '10px 12px', textAlign: 'center' }}>单位</th>
                  <th style={{ padding: '10px 12px', textAlign: 'center' }}>MOQ</th>
                  <th style={{ padding: '10px 12px', textAlign: 'center' }}>状态</th>
                  <th style={{ padding: '10px 12px', textAlign: 'right' }}>操作</th>
                </tr>
              </thead>
              <tbody>
                {products.map((p) => (
                  <tr key={p.id} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                    <td style={{ padding: '10px 12px', fontWeight: 500 }}>{p.name}</td>
                    <td style={{ padding: '10px 12px', color: 'rgba(255,255,255,0.6)' }}>{p.category || '-'}</td>
                    <td style={{ padding: '10px 12px', textAlign: 'right', color: '#4cc9f0' }}>
                      {p.price != null ? `$${p.price.toFixed(2)}` : '-'}
                    </td>
                    <td style={{ padding: '10px 12px', textAlign: 'center' }}>{p.unit || '-'}</td>
                    <td style={{ padding: '10px 12px', textAlign: 'center' }}>{p.moq ?? '-'}</td>
                    <td style={{ padding: '10px 12px', textAlign: 'center' }}>
                      <span style={{
                        padding: '2px 8px', borderRadius: 4, fontSize: 12,
                        background: p.status === 'active' ? 'rgba(76,201,240,0.15)' : 'rgba(255,255,255,0.08)',
                        color: p.status === 'active' ? '#4cc9f0' : 'rgba(255,255,255,0.4)',
                      }}>
                        {p.status === 'active' ? '上架' : '下架'}
                      </span>
                    </td>
                    <td style={{ padding: '10px 12px', textAlign: 'right' }}>
                      <button className="btn btn-sm" onClick={() => openEditForm(p)} style={{ marginRight: 6 }}>编辑</button>
                      <button className="btn btn-sm btn-danger" onClick={() => handleDelete(p.id)}>删除</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* 分页 */}
        {prodTotal > 20 && (
          <div style={{ padding: '12px 16px', display: 'flex', justifyContent: 'center', gap: 8 }}>
            <button className="btn btn-sm" disabled={prodPage <= 1} onClick={() => loadProducts(prodPage - 1)}>上一页</button>
            <span style={{ padding: '4px 12px', color: 'rgba(255,255,255,0.6)' }}>{prodPage} / {Math.ceil(prodTotal / 20)}</span>
            <button className="btn btn-sm" disabled={prodPage >= Math.ceil(prodTotal / 20)} onClick={() => loadProducts(prodPage + 1)}>下一页</button>
          </div>
        )}
      </div>
    </section>
  );
}