/**
 * AI员工列表页面
 * Week 6 Day 1-2: CEO Dashboard - AI Team Management
 */

import React, { useEffect, useState } from 'react';
import workforceAPI, { AIEmployee, Department, AIEmployeeStatus } from '../../services/workforceAPI';

const AIEmployeesListPage: React.FC = () => {
  const [employees, setEmployees] = useState<AIEmployee[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filterDept, setFilterDept] = useState<Department | ''>('');
  const [filterStatus, setFilterStatus] = useState<AIEmployeeStatus | ''>('');
  const [searchTerm, setSearchTerm] = useState('');

  const loadEmployees = async () => {
    try {
      setLoading(true);
      setError(null);
      const params: any = {};
      if (filterDept) params.department = filterDept;
      if (filterStatus) params.status = filterStatus;
      const data = await workforceAPI.listEmployees(params);
      setEmployees(data);
    } catch (err: any) {
      console.error('加载AI员工失败:', err);
      setError(err.response?.data?.detail || '加载失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadEmployees();
  }, [filterDept, filterStatus]);

  const filteredEmployees = employees.filter(emp =>
    emp.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    workforceAPI.getPositionLabel(emp.position).includes(searchTerm) ||
    workforceAPI.getDepartmentLabel(emp.department).includes(searchTerm)
  );

  const stats = {
    total: employees.length,
    active: employees.filter(e => e.status === 'active').length,
    training: employees.filter(e => e.status === 'training').length,
    suspended: employees.filter(e => e.status === 'suspended').length,
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-white">AI员工管理</h1>
          <p className="text-gray-400 mt-1">External AI Workforce - 32 Agents</p>
        </div>
        <button
          onClick={loadEmployees}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
        >
          刷新列表
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div className="bg-gray-800 p-6 rounded-lg border border-gray-700">
          <div className="text-gray-400 text-sm">总员工数</div>
          <div className="text-3xl font-bold text-white mt-2">{stats.total}</div>
          <div className="text-xs text-gray-500 mt-1">Total Employees</div>
        </div>
        <div className="bg-gray-800 p-6 rounded-lg border border-green-500/20">
          <div className="text-gray-400 text-sm">活跃员工</div>
          <div className="text-3xl font-bold text-green-400 mt-2">{stats.active}</div>
          <div className="text-xs text-gray-500 mt-1">Active Workers</div>
        </div>
        <div className="bg-gray-800 p-6 rounded-lg border border-yellow-500/20">
          <div className="text-gray-400 text-sm">培训中</div>
          <div className="text-3xl font-bold text-yellow-400 mt-2">{stats.training}</div>
          <div className="text-xs text-gray-500 mt-1">In Training</div>
        </div>
        <div className="bg-gray-800 p-6 rounded-lg border border-orange-500/20">
          <div className="text-gray-400 text-sm">暂停中</div>
          <div className="text-3xl font-bold text-orange-400 mt-2">{stats.suspended}</div>
          <div className="text-xs text-gray-500 mt-1">Suspended</div>
        </div>
      </div>

      <div className="bg-gray-800 p-4 rounded-lg border border-gray-700">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="text-gray-400 text-sm block mb-2">搜索</label>
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="员工名称、职位、部门..."
              className="w-full px-4 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white focus:border-blue-500 focus:outline-none"
            />
          </div>
          <div>
            <label className="text-gray-400 text-sm block mb-2">部门</label>
            <select
              value={filterDept}
              onChange={(e) => setFilterDept(e.target.value as Department | '')}
              className="w-full px-4 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white focus:border-blue-500 focus:outline-none"
            >
              <option value="">全部部门</option>
              <option value={Department.CEO_OFFICE}>CEO办公室</option>
              <option value={Department.MARKETING}>市场部</option>
              <option value={Department.SALES}>销售部</option>
              <option value={Department.RESEARCH}>研发部</option>
              <option value={Department.OPERATIONS}>运营部</option>
              <option value={Department.ENGINEERING}>工程部</option>
              <option value={Department.ANALYTICS}>分析部</option>
            </select>
          </div>
          <div>
            <label className="text-gray-400 text-sm block mb-2">状态</label>
            <select
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value as AIEmployeeStatus | '')}
              className="w-full px-4 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white focus:border-blue-500 focus:outline-none"
            >
              <option value="">全部状态</option>
              <option value={AIEmployeeStatus.ACTIVE}>活跃</option>
              <option value={AIEmployeeStatus.TRAINING}>培训中</option>
              <option value={AIEmployeeStatus.SUSPENDED}>暂停</option>
              <option value={AIEmployeeStatus.CREATED}>已创建</option>
              <option value={AIEmployeeStatus.RETIRED}>已退役</option>
            </select>
          </div>
        </div>
      </div>

      <div className="bg-gray-800 rounded-lg border border-gray-700 overflow-hidden">
        {loading ? (
          <div className="p-12 text-center text-gray-400">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
            加载中...
          </div>
        ) : error ? (
          <div className="p-12 text-center text-red-400">
            <div className="text-xl mb-2">⚠️ 加载失败</div>
            <div className="text-sm">{error}</div>
            <button
              onClick={loadEmployees}
              className="mt-4 px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg"
            >
              重试
            </button>
          </div>
        ) : filteredEmployees.length === 0 ? (
          <div className="p-12 text-center text-gray-400">
            <div className="text-xl mb-2">📭 无数据</div>
            <div className="text-sm">暂无符合条件的AI员工</div>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-900 border-b border-gray-700">
                <tr>
                  <th className="px-6 py-4 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">员工信息</th>
                  <th className="px-6 py-4 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">部门</th>
                  <th className="px-6 py-4 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">职位</th>
                  <th className="px-6 py-4 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Agent类型</th>
                  <th className="px-6 py-4 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">状态</th>
                  <th className="px-6 py-4 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">创建时间</th>
                  <th className="px-6 py-4 text-right text-xs font-medium text-gray-400 uppercase tracking-wider">操作</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-700">
                {filteredEmployees.map((emp) => (
                  <tr key={emp.id} className="hover:bg-gray-700/50 transition-colors">
                    <td className="px-6 py-4">
                      <div className="flex items-center">
                        <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full flex items-center justify-center text-white font-bold mr-3">
                          {emp.name.substring(0, 2).toUpperCase()}
                        </div>
                        <div>
                          <div className="text-white font-medium">{emp.name}</div>
                          <div className="text-gray-400 text-sm truncate max-w-xs">{emp.description || '暂无描述'}</div>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4 text-gray-300">{workforceAPI.getDepartmentLabel(emp.department)}</td>
                    <td className="px-6 py-4 text-gray-300">{workforceAPI.getPositionLabel(emp.position)}</td>
                    <td className="px-6 py-4">
                      {emp.agent_type ? (
                        <span className="px-2 py-1 text-xs bg-blue-500/20 text-blue-300 rounded">{emp.agent_type}</span>
                      ) : (
                        <span className="text-gray-500 text-sm">未配置</span>
                      )}
                    </td>
                    <td className="px-6 py-4">
                      <span className={`font-medium ${workforceAPI.getStatusColor(emp.status)}`}>
                        {workforceAPI.getStatusLabel(emp.status)}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-gray-400 text-sm">
                      {new Date(emp.created_at).toLocaleDateString('zh-CN')}
                    </td>
                    <td className="px-6 py-4 text-right">
                      <button
                        onClick={() => window.location.href = `/ai-team/employees/${emp.id}`}
                        className="text-blue-400 hover:text-blue-300 text-sm font-medium"
                      >
                        查看详情 →
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div className="text-center text-gray-500 text-sm">
        显示 {filteredEmployees.length} / {employees.length} 个员工
        {searchTerm && ` · 搜索: "${searchTerm}"`}
      </div>
    </div>
  );
};

export default AIEmployeesListPage;
