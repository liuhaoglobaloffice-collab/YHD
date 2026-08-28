import { useEffect, useState } from 'react';
import {
  fetchMarketEmployees,
  fetchMetaKnowledge,
  fetchProposals,
  fetchSkillPacks,
  fetchTemplates,
  generateEvolution,
  installSkillToEmployee,
  installTemplate,
  runMetaLearning,
  deleteMetaKnowledge,
  applyProposal,
  type EmployeeTemplate,
  type EvolutionProposal,
  type MarketEmployee,
  type MetaKnowledge,
  type SkillPack,
} from '../services/market';
import { useI18n } from '../i18n';

const DEPT_LABELS: Record<string, string> = {
  ceo_office: 'CEO 办公室',
  marketing: '市场营销',
  sales: '销售',
  research: '研究',
  operations: '运营',
  engineering: '工程',
  analytics: '数据分析',
};

export function MarketPage() {
  const { t } = useI18n();
  const [templates, setTemplates] = useState<EmployeeTemplate[]>([]);
  const [skillPacks, setSkillPacks] = useState<SkillPack[]>([]);
  const [employees, setEmployees] = useState<MarketEmployee[]>([]);
  const [knowledge, setKnowledge] = useState<MetaKnowledge[]>([]);
  const [proposals, setProposals] = useState<EvolutionProposal[]>([]);

  const [category, setCategory] = useState('');
  const [loading, setLoading] = useState(true);
  const [installing, setInstalling] = useState(false);
  const [learning, setLearning] = useState(false);
  const [evolving, setEvolving] = useState(false);
  const [error, setError] = useState('');
  const [currentKnowledge, setCurrentKnowledge] = useState<MetaKnowledge | null>(null);
  const [currentProposal, setCurrentProposal] = useState<EvolutionProposal | null>(null);

  const loadAll = async () => {
    try {
      const [tm, sk, em, kn, pr] = await Promise.all([
        fetchTemplates(category || undefined),
        fetchSkillPacks(),
        fetchMarketEmployees(),
        fetchMetaKnowledge(),
        fetchProposals(),
      ]);
      setTemplates(tm);
      setSkillPacks(sk);
      setEmployees(em);
      setKnowledge(kn);
      setProposals(pr);
    } catch (e) {
      console.error(e);
      setError('加载市场数据失败');
    }
    setLoading(false);
  };

  useEffect(() => {
    loadAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (category !== undefined) {
      fetchTemplates(category || undefined).then(setTemplates).catch(() => {});
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [category]);

  const handleInstall = async (template: EmployeeTemplate) => {
    setInstalling(true);
    setError('');
    try {
      await installTemplate(template.id);
      await loadAll();
    } catch (e) {
      setError(e instanceof Error ? e.message : '安装失败');
    }
    setInstalling(false);
  };

  const handleInstallSkill = async (employee: MarketEmployee, skill: SkillPack) => {
    setError('');
    try {
      await installSkillToEmployee(employee.id, skill.id);
      await loadAll();
    } catch (e) {
      setError(e instanceof Error ? e.message : '安装技能失败');
    }
  };

  const handleLearn = async () => {
    setLearning(true);
    setError('');
    try {
      const result = await runMetaLearning();
      setCurrentKnowledge(result);
      loadAll();
    } catch (e) {
      setError(e instanceof Error ? e.message : '元学习失败');
    }
    setLearning(false);
  };

  const handleEvolve = async () => {
    setEvolving(true);
    setError('');
    try {
      const result = await generateEvolution();
      setCurrentProposal(result);
      loadAll();
    } catch (e) {
      setError(e instanceof Error ? e.message : '进化失败');
    }
    setEvolving(false);
  };

  const handleDeleteKnowledge = async (id: number) => {
    try {
      await deleteMetaKnowledge(id);
      setKnowledge((prev) => prev.filter((k) => k.id !== id));
      if (currentKnowledge?.id === id) setCurrentKnowledge(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : '删除知识失败');
    }
  };

  const handleApplyProposal = async (id: number, action: 'apply' | 'reject') => {
    try {
      await applyProposal(id, action);
      loadAll();
    } catch (e) {
      setError(e instanceof Error ? e.message : '操作方案失败');
    }
  };

  if (loading) {
    return (
      <section className="page">
        <h1>{t('aiMarket')}</h1>
        <p>{t('loading')}</p>
      </section>
    );
  }

  return (
    <section className="page">
      <h1>{t('aiMarket')}</h1>
      <p className="card-desc">{t('aiMarketDesc')}</p>

      {error && <p className="error-text">{error}</p>}

      {/* 员工团队 */}
      {employees.length > 0 && (
        <div className="executions-panel">
          <div className="executions-header">
            <strong>{t('myTeam')}</strong>
            <span className="executions-count">{employees.length} 名</span>
          </div>
          <div className="market-team">
            {employees.map((e) => (
              <div key={e.id} className="team-member">
                <div className="execution-item-main">
                  <span className="execution-employee">{e.name}</span>
                  <span className="lead-badge">{DEPT_LABELS[e.department] ?? e.department}</span>
                  {e.market_category && (
                    <span className={`lead-badge src-${e.market_category}`}>
                      {e.market_category === 'external' ? '外部' : '内部'}
                    </span>
                  )}
                </div>
                <div className="execution-item-sub">
                  <span>{e.position} · {e.agent_type || 'no agent'}</span>
                  <span className="team-skills">
                    {(e.skills ?? []).map((s) => (
                      <span key={s} className="kw-sugg-chip">{s}</span>
                    ))}
                  </span>
                </div>
                <div className="team-skill-install">
                  {skillPacks.slice(0, 4).map((sp) => (
                    <button
                      key={sp.id}
                      className="btn btn-sm"
                      onClick={() => handleInstallSkill(e, sp)}
                      disabled={e.skills?.includes(sp.code)}
                      title={e.skills?.includes(sp.code) ? '已安装' : `安装 ${sp.name}`}
                    >
                      {e.skills?.includes(sp.code) ? `✓ ${sp.name}` : `+ ${sp.name}`}
                    </button>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 员工市场 */}
      <div className="executions-panel">
        <div className="executions-header">
          <strong>{t('employeeMarket')}</strong>
          <select className="market-filter" value={category} onChange={(e) => setCategory(e.target.value)}>
            <option value="">全部</option>
            <option value="internal">内部模板</option>
            <option value="external">外部模板</option>
          </select>
        </div>
        {templates.length === 0 ? (
          <p className="executions-empty">{t('noTemplates')}</p>
        ) : (
          <div className="market-grid">
            {templates.map((tmpl) => (
              <div key={tmpl.id} className="market-card">
                <div className="platform-card-head">
                  <span className={`platform-badge ${tmpl.category === 'external' ? 'ext' : ''}`}>
                    {tmpl.category === 'external' ? '外部模板' : '内部模板'}
                  </span>
                  <span className="execution-time">⭐ {tmpl.rating} · 安装 {tmpl.installs}</span>
                </div>
                <strong>{tmpl.name}</strong>
                <div className="card-meta">
                  {DEPT_LABELS[tmpl.department] ?? tmpl.department} · {tmpl.position}
                </div>
                {tmpl.description && <p className="card-desc">{tmpl.description}</p>}
                <div className="card-meta">
                  {tmpl.agent_type && <span>Agent: {tmpl.agent_type}</span>}
                  {tmpl.price > 0 && <span className="market-price">¥{tmpl.price}</span>}
                </div>
                <button
                  className="btn btn-submit"
                  onClick={() => handleInstall(tmpl)}
                  disabled={installing}
                >
                  {installing ? '安装中...' : tmpl.price > 0 ? `${t('addExternal')}（¥${tmpl.price}）` : t('addEmployee')}
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* 技能包 */}
      <div className="import-panel">
        <div className="executions-header">
          <strong>{t('skillPacks')}</strong>
          <span className="executions-count">{skillPacks.length} 个</span>
        </div>
        <div className="skill-list">
          {skillPacks.map((sp) => (
            <div key={sp.id} className="skill-item">
              <div className="execution-item-main">
                <span className="execution-employee">{sp.name}</span>
                <span className="lead-badge">{sp.category}</span>
                <span className="execution-time">v{sp.version}</span>
              </div>
              <div className="execution-item-sub">
                <span>{sp.description}</span>
                <span className="team-skills">
                  {(sp.capabilities ?? []).map((c) => (
                    <span key={c} className="kw-sugg-chip">{c}</span>
                  ))}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* 鎏灏元学习 */}
      <div className="import-panel">
        <div className="executions-header">
          <strong>{t('metaLearning')}</strong>
          <button className="btn btn-submit" onClick={handleLearn} disabled={learning}>
            {learning ? '学习中...' : t('runMetaLearning')}
          </button>
        </div>
        <p className="card-desc">{t('metaLearningDesc')}</p>
        {currentKnowledge && (
          <div className="generated-content">
            <div className="executions-header">
              <strong>{currentKnowledge.title}</strong>
              <span className="analysis-method">{currentKnowledge.method === 'ai' ? 'AI 学习' : '规则学习'}</span>
            </div>
            {currentKnowledge.summary && (
              <div className="dimension">
                <strong>摘要</strong>
                <p>{currentKnowledge.summary}</p>
              </div>
            )}
            {currentKnowledge.knowledge && (
              <div className="analysis-report-body">
                <strong>吸收知识</strong>
                <pre>{currentKnowledge.knowledge}</pre>
              </div>
            )}
          </div>
        )}
        {knowledge.length > 0 && (
          <div className="knowledge-list">
            {knowledge.slice(0, 5).map((k) => (
              <div key={k.id} className="customs-item" style={{ cursor: 'pointer' }} onClick={() => setCurrentKnowledge(k)}>
                <div className="execution-item-main">
                  <span className="execution-employee">{k.title}</span>
                  <span className="execution-time">{new Date(k.created_at).toLocaleString()}</span>
                  <button
                    className="btn btn-sm btn-cancel"
                    style={{ marginLeft: 'auto' }}
                    onClick={(e) => { e.stopPropagation(); handleDeleteKnowledge(k.id); }}
                    title="删除"
                  >
                    ✕
                  </button>
                </div>
                <div className="execution-item-sub">{k.summary}</div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* 自我进化 */}
      <div className="import-panel">
        <div className="executions-header">
          <strong>{t('selfEvolution')}</strong>
          <button className="btn btn-submit" onClick={handleEvolve} disabled={evolving}>
            {evolving ? '生成中...' : t('generateProposal')}
          </button>
        </div>
        <p className="card-desc">{t('selfEvolutionDesc')}</p>
        {currentProposal && (
          <div className="generated-content">
            <div className="executions-header">
              <strong>{currentProposal.title}</strong>
              <span className="analysis-method">{currentProposal.method === 'ai' ? 'AI 方案' : '规则方案'}</span>
            </div>
            {currentProposal.summary && (
              <div className="dimension">
                <strong>摘要</strong>
                <p>{currentProposal.summary}</p>
              </div>
            )}
            {currentProposal.analysis && (
              <div className="dimension">
                <strong>系统评估</strong>
                <p>{currentProposal.analysis}</p>
              </div>
            )}
            {currentProposal.improvements.length > 0 && (
              <div className="analysis-recommendations">
                <strong>改进建议</strong>
                <ul>
                  {currentProposal.improvements.map((imp, i) => (
                    <li key={i}>{imp}</li>
                  ))}
                </ul>
              </div>
            )}
            {currentProposal.action_plan.length > 0 && (
              <div className="analysis-recommendations" style={{ borderColor: 'rgba(76,201,240,0.3)' }}>
                <strong>行动计划</strong>
                <ul>
                  {currentProposal.action_plan.map((a, i) => (
                    <li key={i}>{a}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
        {proposals.length > 0 && (
          <div className="knowledge-list">
            {proposals.slice(0, 5).map((p) => (
              <div key={p.id} className="customs-item" style={{ cursor: 'pointer' }} onClick={() => setCurrentProposal(p)}>
                <div className="execution-item-main">
                  <span className="execution-employee">{p.title}</span>
                  <span className={`lead-badge st-${p.status}`}>{p.status === 'draft' ? '草稿' : p.status === 'applied' ? '已采纳' : '已拒绝'}</span>
                  <span className="execution-time">{new Date(p.created_at).toLocaleString()}</span>
                </div>
                <div className="execution-item-sub">{p.summary}</div>
                {p.status === 'draft' && (
                  <div className="team-skill-install" style={{ marginTop: 6 }}>
                    <button
                      className="btn btn-sm"
                      style={{ borderColor: '#10b981', color: '#10b981' }}
                      onClick={(e) => { e.stopPropagation(); handleApplyProposal(p.id, 'apply'); }}
                    >
                      采纳
                    </button>
                    <button
                      className="btn btn-sm btn-cancel"
                      style={{ marginLeft: 6 }}
                      onClick={(e) => { e.stopPropagation(); handleApplyProposal(p.id, 'reject'); }}
                    >
                      拒绝
                    </button>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}