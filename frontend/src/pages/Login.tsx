import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { LogIn, Zap } from 'lucide-react';
import { useAuthStore } from '../stores/authStore';
import { authAPI } from '../services/authAPI';

export default function Login() {
  const navigate = useNavigate();
  const { login } = useAuthStore();
  
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  // 🚀 自动登录功能：页面加载后自动使用admin账号登录
  useEffect(() => {
    const autoLogin = async () => {
      setLoading(true);
      try {
        const response = await authAPI.login({ 
          username: 'admin', 
          password: 'Admin2026' 
        });
        login(response.access_token, response.user);
        navigate('/overview/dashboard/realtime');
      } catch (err) {
        // 自动登录失败，显示登录表单
        const error = err as any;
        setError(error?.detail || '自动登录失败，请手动登录');
        console.error('自动登录错误:', err);
      } finally {
        setLoading(false);
      }
    };
    
    // 延迟500ms执行自动登录（让用户看到加载动画）
    const timer = setTimeout(autoLogin, 500);
    return () => clearTimeout(timer);
  }, [login, navigate]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const response = await authAPI.login({ username, password });
      login(response.access_token, response.user);
      navigate('/overview/dashboard/realtime');
    } catch (err) {
      const error = err as any;
      setError(error?.detail || '登录失败，请检查用户名和密码');
      console.error('登录错误:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-primary-bg relative overflow-hidden">
      <div className="absolute inset-0 opacity-20" style={{
        backgroundImage: 'linear-gradient(to right, #00d9ff 1px, transparent 1px), linear-gradient(to bottom, #00d9ff 1px, transparent 1px)',
        backgroundSize: '50px 50px'
      }}></div>
      
      <div className="scan-lines absolute inset-0 pointer-events-none"></div>
      
      <div className="absolute top-20 left-1/4 w-96 h-96 bg-neon-blue/10 rounded-full blur-3xl animate-pulse"></div>
      <div className="absolute bottom-20 right-1/4 w-96 h-96 bg-neon-purple/10 rounded-full blur-3xl animate-pulse" style={{ animationDelay: '1s' }}></div>

      <div className="max-w-md w-full mx-4 relative z-10">
        <div className="glass-heavy rounded-2xl shadow-2xl p-8 border-2 border-neon-blue/30 neon-glow-blue relative overflow-hidden">
          <div className="absolute inset-0 scan-lines opacity-30 pointer-events-none"></div>
          
          <div className="flex flex-col items-center mb-8 relative z-10">
            <div className="relative mb-6">
              <div className="absolute inset-0 bg-neon-blue/30 rounded-full blur-xl animate-pulse"></div>
              <div className="relative bg-neon-blue/20 p-6 rounded-full border-2 border-neon-blue neon-glow-blue">
                <LogIn className="w-10 h-10 text-neon-blue animate-pulse" />
              </div>
            </div>
            
            <h1 className="text-4xl font-bold neon-text-blue mb-2 tracking-wider">鎏灏 AI-OS</h1>
            <p className="text-neon-cyan text-sm tracking-widest">CEO 控制台</p>
            
            {loading && (
              <div className="mt-4 px-4 py-2 bg-neon-blue/10 border border-neon-blue/30 rounded-lg">
                <p className="text-sm text-neon-cyan animate-pulse">🚀 正在自动登录...</p>
              </div>
            )}
            
            <div className="flex items-center gap-2 mt-4">
              <div className="w-8 h-0.5 bg-gradient-to-r from-transparent to-neon-blue"></div>
              <Zap className="w-4 h-4 text-neon-yellow animate-pulse" />
              <div className="w-8 h-0.5 bg-gradient-to-l from-transparent to-neon-blue"></div>
            </div>
          </div>

          <form onSubmit={handleSubmit} className="space-y-6 relative z-10">
            {error && (
              <div className="bg-red-500/10 border-l-4 border-red-500 text-red-400 px-4 py-3 rounded-lg backdrop-blur-sm animate-shake">
                <p className="text-sm">{error}</p>
              </div>
            )}

            <div>
              <label htmlFor="username" className="block text-sm font-medium text-neon-cyan mb-2">
                用户名
              </label>
              <input
                id="username"
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="w-full px-4 py-3 bg-glass-light border border-neon-blue/30 rounded-lg text-text-primary placeholder-text-muted focus:ring-2 focus:ring-neon-blue focus:border-neon-blue outline-none transition-all duration-300 hover:border-neon-blue/50"
                placeholder="输入用户名"
                required
                autoComplete="username"
              />
            </div>

            <div>
              <label htmlFor="password" className="block text-sm font-medium text-neon-cyan mb-2">
                密码
              </label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-4 py-3 bg-glass-light border border-neon-blue/30 rounded-lg text-text-primary placeholder-text-muted focus:ring-2 focus:ring-neon-blue focus:border-neon-blue outline-none transition-all duration-300 hover:border-neon-blue/50"
                placeholder="输入密码"
                required
                autoComplete="current-password"
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-neon-blue/20 hover:bg-neon-blue/30 text-neon-blue border-2 border-neon-blue font-semibold py-4 px-4 rounded-lg transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center neon-glow-blue hover:scale-105 relative overflow-hidden group"
            >
              <div className="absolute inset-0 bg-gradient-to-r from-transparent via-neon-blue/20 to-transparent translate-x-[-200%] group-hover:translate-x-[200%] transition-transform duration-1000"></div>
              
              {loading ? (
                <span className="animate-pulse relative z-10">系统验证中...</span>
              ) : (
                <span className="relative z-10 flex items-center">
                  <LogIn className="w-5 h-5 mr-2" />
                  登录
                </span>
              )}
            </button>
          </form>

          <div className="mt-6 text-center relative z-10">
            <div className="inline-block px-4 py-2 bg-glass-light border border-neon-cyan/30 rounded-lg">
              <p className="text-xs text-neon-cyan">✨ 页面打开后自动登录 | 无需输入账号密码</p>
            </div>
          </div>

          <div className="absolute top-2 left-2 w-2 h-2 bg-neon-blue rounded-full animate-pulse"></div>
          <div className="absolute top-2 right-2 w-2 h-2 bg-neon-cyan rounded-full animate-pulse" style={{ animationDelay: '0.5s' }}></div>
          <div className="absolute bottom-2 left-2 w-2 h-2 bg-neon-purple rounded-full animate-pulse" style={{ animationDelay: '1s' }}></div>
          <div className="absolute bottom-2 right-2 w-2 h-2 bg-neon-yellow rounded-full animate-pulse" style={{ animationDelay: '1.5s' }}></div>
        </div>

        <div className="text-center mt-6">
          <p className="text-text-muted text-xs tracking-widest">POWERED BY AI · SECURED BY BLOCKCHAIN</p>
        </div>
      </div>
    </div>
  );
}
