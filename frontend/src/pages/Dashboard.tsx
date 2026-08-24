import { useState, useEffect } from 'react';
import { Routes, Route, Link, useLocation } from 'react-router-dom';
import { 
  LayoutDashboard, 
  Users, 
  ListTodo, 
  Activity,
  LogOut,
  Menu,
  X
} from 'lucide-react';
import Overview from './Overview';
import Employees from './Employees';
import Tasks from './Tasks';
import { apiService, User } from '../services/api';

interface DashboardProps {
  onLogout: () => void;
}

export default function Dashboard({ onLogout }: DashboardProps) {
  const [user, setUser] = useState<User | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const location = useLocation();

  useEffect(() => {
    loadUser();
  }, []);

  const loadUser = async () => {
    try {
      const userData = await apiService.getCurrentUser();
      setUser(userData);
    } catch (error) {
      console.error('Failed to load user:', error);
    }
  };

  const navigation = [
    { name: '总览', path: '/', icon: LayoutDashboard },
    { name: 'AI 员工', path: '/employees', icon: Users },
    { name: '任务管理', path: '/tasks', icon: ListTodo },
    { name: '系统状态', path: '/status', icon: Activity },
  ];

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar */}
      <aside className={`${sidebarOpen ? 'w-64' : 'w-20'} bg-gray-900 text-white transition-all duration-300 flex flex-col`}>
        <div className="p-4 flex items-center justify-between border-b border-gray-800">
          {sidebarOpen && <h1 className="text-xl font-bold">LiuHao AI-OS</h1>}
          <button 
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="p-2 hover:bg-gray-800 rounded-lg transition"
          >
            {sidebarOpen ? <X size={20} /> : <Menu size={20} />}
          </button>
        </div>

        <nav className="flex-1 p-4 space-y-2">
          {navigation.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname === item.path;
            return (
              <Link
                key={item.path}
                to={item.path}
                className={`flex items-center px-4 py-3 rounded-lg transition ${
                  isActive 
                    ? 'bg-blue-600 text-white' 
                    : 'text-gray-300 hover:bg-gray-800 hover:text-white'
                }`}
              >
                <Icon size={20} />
                {sidebarOpen && <span className="ml-3">{item.name}</span>}
              </Link>
            );
          })}
        </nav>

        <div className="p-4 border-t border-gray-800">
          {user && sidebarOpen && (
            <div className="mb-4 px-4 py-2 bg-gray-800 rounded-lg">
              <p className="text-sm font-medium">{user.full_name || user.username}</p>
              <p className="text-xs text-gray-400">{user.role}</p>
            </div>
          )}
          <button
            onClick={onLogout}
            className="flex items-center w-full px-4 py-3 text-gray-300 hover:bg-gray-800 hover:text-white rounded-lg transition"
          >
            <LogOut size={20} />
            {sidebarOpen && <span className="ml-3">退出登录</span>}
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 overflow-auto">
        <Routes>
          <Route path="/" element={<Overview />} />
          <Route path="/employees" element={<Employees />} />
          <Route path="/tasks" element={<Tasks />} />
          <Route path="/status" element={<SystemStatus />} />
        </Routes>
      </main>
    </div>
  );
}

function SystemStatus() {
  const [health, setHealth] = useState<any>(null);

  useEffect(() => {
    loadHealth();
  }, []);

  const loadHealth = async () => {
    try {
      const data = await apiService.getHealth();
      setHealth(data);
    } catch (error) {
      console.error('Failed to load health:', error);
    }
  };

  return (
    <div className="p-8">
      <h1 className="text-3xl font-bold text-gray-900 mb-6">系统状态</h1>
      {health && (
        <div className="bg-white rounded-lg shadow p-6">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-sm text-gray-500">状态</p>
              <p className="text-2xl font-bold text-green-600">{health.status}</p>
            </div>
            <div>
              <p className="text-sm text-gray-500">版本</p>
              <p className="text-2xl font-bold">{health.version}</p>
            </div>
            <div>
              <p className="text-sm text-gray-500">环境</p>
              <p className="text-2xl font-bold">{health.environment}</p>
            </div>
            <div>
              <p className="text-sm text-gray-500">时间</p>
              <p className="text-sm font-mono">{new Date(health.timestamp).toLocaleString('zh-CN')}</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
