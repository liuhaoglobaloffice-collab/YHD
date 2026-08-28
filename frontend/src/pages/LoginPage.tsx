import { useState } from 'react';
import { fetchOwnerInfo, registerSubAccount, type OwnerInfo } from '../services/accounts';
import { fetchMe, saveAuthToken, clearAuthToken } from '../services/auth';
import { useI18n } from '../i18n';

export function LoginPage() {
  const { t } = useI18n();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  // 注册子账号模式
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [registered, setRegistered] = useState(false);
  const [regForm, setRegForm] = useState({
    username: '',
    password: '',
  });
  const [regError, setRegError] = useState('');
  const [registering, setRegistering] = useState(false);
  // 注册结果（含主账号信息）
  const [regResult, setRegResult] = useState<{ owner_username: string; message: string } | null>(null);
  // 主账号信息
  const [ownerInfo, setOwnerInfo] = useState<OwnerInfo | null>(null);
  const [ownerInfoLoading, setOwnerInfoLoading] = useState(false);
  const [ownerInfoError, setOwnerInfoError] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username.trim() || !password.trim()) return;
    setLoading(true);
    setError('');

    try {
      // Step 1: 登录获取 token
      const res = await fetch(
        `${import.meta.env?.VITE_API_BASE ?? ''}/api/v1/auth/login`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ username: username.trim(), password }),
        }
      );
      const data = await res.json();
      if (!res.ok) {
        // 根据后端返回的不同错误类型显示不同提示
        if (res.status === 403) {
          const detail = data.detail || '';
          if (detail.includes('审核')) setError('账号待主账号审核，请等待通过');
          else if (detail.includes('拒绝')) setError('子账号申请已被拒绝，请联系主账号');
          else if (detail.includes('inactive')) setError('账号已被停用，请联系管理员');
          else setError(detail);
        } else if (res.status === 401) {
          setError(t('loginError'));
        } else if (res.status >= 500) {
          setError('登录服务异常，请稍后重试');
        } else {
          setError('登录失败，请稍后重试');
        }
        return;
      }

      // Step 2: 先保存 token，再获取用户信息
      saveAuthToken(data.access_token);

      // Step 3: 验证 token 可用并获取用户信息
      try {
        const user = await fetchMe();
        if (user.account_type === 'sub') {
          window.location.href = '/sub-portal';
        } else {
          window.location.href = '/dashboard';
        }
      } catch {
        // fetchMe 失败 → token 可能无效，清除并提示
        clearAuthToken();
        setError('登录验证失败，请稍后重试');
      }
    } catch (e) {
      // 网络错误或 JSON 解析失败
      if (e instanceof TypeError && e.message === 'Failed to fetch') {
        setError('网络连接异常，请检查后端服务是否启动');
      } else {
        setError('网络连接异常，请检查网络后重试');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleRegisterSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!regForm.username.trim() || !regForm.password.trim()) return;
    setRegistering(true);
    setRegError('');
    try {
      const result = await registerSubAccount({
        username: regForm.username.trim(),
        password: regForm.password,
      });
      setRegResult({ owner_username: result.owner_username, message: result.message });
      setRegistered(true);
    } catch (err) {
      setRegError(err instanceof Error ? err.message : t('loginError'));
    } finally {
      setRegistering(false);
    }
  };

  return (
    <div className="login-page">
      {/* 全息人物背景 */}
      <div className="login-hologram" />

      {/* 网格地面 */}
      <div className="login-grid-floor" />

      {/* 霓虹光晕 */}
      <div className="login-glow login-glow-1" />
      <div className="login-glow login-glow-2" />

      {/* 数据流装饰 */}
      <div className="login-dataflow login-dataflow-1" />
      <div className="login-dataflow login-dataflow-2" />

      {/* 左侧品牌信息 */}
      <div className="login-brand-panel">
        <div className="login-brand-logo">L</div>
        <h1 className="login-brand-title">{t('brand')}</h1>
        <p className="login-brand-sub">{t('loginTitle')}</p>
        <p className="login-brand-desc">{t('loginSubtitle')}</p>
        <div className="login-features">
          <span className="login-feature">AI Workforce</span>
          <span className="login-feature">RAG Knowledge</span>
          <span className="login-feature">Governance</span>
          <span className="login-feature">Audit</span>
        </div>
      </div>

      {/* 右侧卡片：登录 / 注册子账号 */}
      {mode === 'login' && (
      <form className="login-card" onSubmit={handleSubmit}>
        <div className="login-card-header">
          <div className="login-status-dot" />
          <span>{t('systemOnline')}</span>
        </div>
        <h2 className="login-card-title">{t('login')}</h2>

        <div className="login-field">
          <label htmlFor="username">{t('username')}</label>
          <input
            id="username"
            type="text"
            value={username}
            placeholder={t('loginPlaceholder')}
            onChange={(e) => setUsername(e.target.value)}
            autoComplete="username"
          />
        </div>

        <div className="login-field">
          <label htmlFor="password">{t('password')}</label>
          <input
            id="password"
            type="password"
            value={password}
            placeholder={t('passwordPlaceholder')}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
          />
        </div>

        {error && <div className="login-error">{error}</div>}

        <button
          className="login-submit"
          type="submit"
          disabled={loading || !username.trim() || !password.trim()}
        >
          {loading ? t('loggingIn') : t('login')}
        </button>

        {/* 子账号自助注册入口 */}
        <button
          className="login-register-link"
          type="button"
          onClick={() => {
            setMode('register');
            setRegError('');
            setRegistered(false);
            setRegResult(null);
            setOwnerInfo(null);
            setOwnerInfoLoading(true);
            setOwnerInfoError(false);
            fetchOwnerInfo()
              .then(setOwnerInfo)
              .catch(() => { setOwnerInfo(null); setOwnerInfoError(true); })
              .finally(() => setOwnerInfoLoading(false));
          }}
        >
          {t('registerSub')}
        </button>
      </form>
      )}

      {/* 注册子账号 */}
      {mode === 'register' && (
        <div className="login-card">
          <div className="login-card-header">
            <div className="login-status-dot" />
            <span>{t('registerSub')}</span>
          </div>

          {registered ? (
            <div className="register-done">
              <div className="register-done-title">{t('registerDone')}</div>
              {regResult && (
                <p className="card-desc" style={{ marginTop: 8, color: '#facc15' }}>
                  归属主账号：<strong>{regResult.owner_username}</strong>
                </p>
              )}
              <p className="card-desc">{t('registerPendingHint')}</p>
              <button
                className="login-submit"
                type="button"
                onClick={() => {
                  setMode('login');
                  setRegistered(false);
                  setRegResult(null);
                }}
              >
                {t('backToLogin')}
              </button>
            </div>
          ) : (
            <>
              <h2 className="login-card-title">{t('registerSub')}</h2>
              <p className="card-desc">{t('registerSubDesc')}</p>

              {/* 主账号信息 */}
              {ownerInfoLoading ? (
                <p className="card-desc" style={{ fontSize: 12, marginBottom: 12 }}>
                  加载主账号信息...
                </p>
              ) : ownerInfoError ? (
                <p className="card-desc" style={{ fontSize: 12, marginBottom: 12, color: '#ff6b6b' }}>
                  获取主账号信息失败，请稍后重试
                </p>
              ) : ownerInfo && ownerInfo.has_owner ? (
                <div className="login-owner-info">
                  <div className="login-owner-row">
                    <span className="login-owner-label">归属主账号：</span>
                    <strong className="login-owner-name">{ownerInfo.owner_username}</strong>
                  </div>
                  {ownerInfo.owner_email && (
                    <div className="login-owner-row">
                      <span className="login-owner-label">主账号邮箱：</span>
                      <span className="login-owner-email">{ownerInfo.owner_email}</span>
                    </div>
                  )}
                </div>
              ) : (
                <p className="card-desc" style={{ fontSize: 12, marginBottom: 12, color: '#ff6b6b' }}>
                  系统中没有主账号，无法注册子账号
                </p>
              )}

              <div className="login-field">
                <label htmlFor="reg-username">{t('username')}</label>
                <input
                  id="reg-username"
                  type="text"
                  value={regForm.username}
                  placeholder={t('loginPlaceholder')}
                  onChange={(e) => setRegForm({ ...regForm, username: e.target.value })}
                />
              </div>

              <div className="login-field">
                <label htmlFor="reg-password">{t('password')}</label>
                <input
                  id="reg-password"
                  type="password"
                  value={regForm.password}
                  placeholder={t('passwordPlaceholder')}
                  onChange={(e) => setRegForm({ ...regForm, password: e.target.value })}
                  autoComplete="new-password"
                />
              </div>

              {regError && <div className="login-error">{regError}</div>}

              <button
                className="login-submit"
                type="button"
                disabled={
                  registering ||
                  !regForm.username.trim() ||
                  regForm.password.length < 8
                }
                onClick={handleRegisterSubmit}
              >
                {registering ? t('registering') : t('submitRegister')}
              </button>

              <button
                className="login-register-link"
                type="button"
                onClick={() => {
                  setMode('login');
                  setRegError('');
                }}
              >
                {t('backToLogin')}
              </button>
            </>
          )}
        </div>
      )}
    </div>
  );
}