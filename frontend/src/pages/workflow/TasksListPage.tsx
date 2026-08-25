/**
 * Tasks List Page
 * 
 * LiuHao AI-OS - Week 6 Day 5
 * 任务中心页面 - 显示所有任务、状态筛选、优先级排序
 */

import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  getTasks,
  Task,
  TaskStatus,
  TaskPriority,
  TaskType,
  taskStatusLabels,
  taskPriorityLabels,
  taskTypeLabels,
} from '../../services/taskAPI';

const TasksListPage: React.FC = () => {
  const navigate = useNavigate();
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // 筛选条件
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<TaskStatus | ''>('');
  const [priorityFilter, setPriorityFilter] = useState<TaskPriority | ''>('');
  const [typeFilter, setTypeFilter] = useState<TaskType | ''>('');

  // 加载任务数据
  useEffect(() => {
    loadTasks();
  }, [statusFilter, priorityFilter, typeFilter]);

  const loadTasks = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await getTasks({
        status: statusFilter || undefined,
        priority: priorityFilter || undefined,
        task_type: typeFilter || undefined,
      });
      setTasks(data);
    } catch (err: any) {
      setError(err.message || '加载任务失败');
    } finally {
      setLoading(false);
    }
  };

  // 计算统计数据
  const stats = {
    total: tasks.length,
    running: tasks.filter((t) => t.status === TaskStatus.RUNNING).length,
    completed: tasks.filter((t) => t.status === TaskStatus.COMPLETED).length,
    failed: tasks.filter((t) => t.status === TaskStatus.FAILED).length,
  };

  // 过滤任务（搜索）
  const filteredTasks = tasks.filter((task) =>
    task.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
    task.description.toLowerCase().includes(searchQuery.toLowerCase())
  );

  // 获取状态颜色
  const getStatusColor = (status: TaskStatus): string => {
    const colors: Record<TaskStatus, string> = {
      [TaskStatus.PENDING]: 'text-gray-400 bg-gray-800',
      [TaskStatus.READY]: 'text-blue-400 bg-blue-900/30',
      [TaskStatus.RUNNING]: 'text-yellow-400 bg-yellow-900/30',
      [TaskStatus.COMPLETED]: 'text-green-400 bg-green-900/30',
      [TaskStatus.FAILED]: 'text-red-400 bg-red-900/30',
      [TaskStatus.CANCELLED]: 'text-gray-400 bg-gray-800',
      [TaskStatus.BLOCKED]: 'text-orange-400 bg-orange-900/30',
    };
    return colors[status] || 'text-gray-400 bg-gray-800';
  };

  // 获取优先级颜色
  const getPriorityColor = (priority: TaskPriority): string => {
    const colors: Record<TaskPriority, string> = {
      [TaskPriority.LOW]: 'text-gray-400',
      [TaskPriority.MEDIUM]: 'text-blue-400',
      [TaskPriority.HIGH]: 'text-yellow-400',
      [TaskPriority.URGENT]: 'text-orange-400',
      [TaskPriority.CRITICAL]: 'text-red-400',
    };
    return colors[priority] || 'text-gray-400';
  };

  // 格式化日期
  const formatDate = (dateString?: string): string => {
    if (!dateString) return '-';
    const date = new Date(dateString);
    return date.toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  // 计算任务持续时间
  const getTaskDuration = (task: Task): string => {
    if (!task.started_at) return '-';
    const start = new Date(task.started_at);
    const end = task.completed_at ? new Date(task.completed_at) : new Date();
    const durationMs = end.getTime() - start.getTime();
    const minutes = Math.floor(durationMs / 60000);
    if (minutes < 60) return `${minutes}分钟`;
    const hours = Math.floor(minutes / 60);
    return `${hours}小时${minutes % 60}分钟`;
  };

  return (
    <div className="p-6 space-y-6">
      {/* 标题 */}
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white">任务中心</h1>
          <p className="text-gray-400 mt-1">管理和监控所有任务执行</p>
        </div>
        <button
          onClick={() => navigate('/workflow/tasks/create')}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
        >
          创建任务
        </button>
      </div>

      {/* 统计卡片 */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-gradient-to-br from-blue-900/50 to-blue-800/30 border border-blue-700/50 rounded-lg p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-blue-400 text-sm">总任务数</p>
              <p className="text-white text-2xl font-bold mt-1">{stats.total}</p>
            </div>
            <div className="text-blue-400 text-3xl">📋</div>
          </div>
        </div>

        <div className="bg-gradient-to-br from-yellow-900/50 to-yellow-800/30 border border-yellow-700/50 rounded-lg p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-yellow-400 text-sm">执行中</p>
              <p className="text-white text-2xl font-bold mt-1">{stats.running}</p>
            </div>
            <div className="text-yellow-400 text-3xl">⚡</div>
          </div>
        </div>

        <div className="bg-gradient-to-br from-green-900/50 to-green-800/30 border border-green-700/50 rounded-lg p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-green-400 text-sm">已完成</p>
              <p className="text-white text-2xl font-bold mt-1">{stats.completed}</p>
            </div>
            <div className="text-green-400 text-3xl">✅</div>
          </div>
        </div>

        <div className="bg-gradient-to-br from-red-900/50 to-red-800/30 border border-red-700/50 rounded-lg p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-red-400 text-sm">失败任务</p>
              <p className="text-white text-2xl font-bold mt-1">{stats.failed}</p>
            </div>
            <div className="text-red-400 text-3xl">❌</div>
          </div>
        </div>
      </div>

      {/* 筛选器 */}
      <div className="bg-gray-800 border border-gray-700 rounded-lg p-4">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <input
            type="text"
            placeholder="搜索任务..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="bg-gray-900 border border-gray-700 rounded px-3 py-2 text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"
          />

          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value as TaskStatus | '')}
            className="bg-gray-900 border border-gray-700 rounded px-3 py-2 text-white focus:outline-none focus:border-blue-500"
          >
            <option value="">全部状态</option>
            {Object.entries(taskStatusLabels).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>

          <select
            value={priorityFilter}
            onChange={(e) => setPriorityFilter(e.target.value as TaskPriority | '')}
            className="bg-gray-900 border border-gray-700 rounded px-3 py-2 text-white focus:outline-none focus:border-blue-500"
          >
            <option value="">全部优先级</option>
            {Object.entries(taskPriorityLabels).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>

          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value as TaskType | '')}
            className="bg-gray-900 border border-gray-700 rounded px-3 py-2 text-white focus:outline-none focus:border-blue-500"
          >
            <option value="">全部类型</option>
            {Object.entries(taskTypeLabels).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* 任务列表 */}
      <div className="bg-gray-800 border border-gray-700 rounded-lg overflow-hidden">
        {loading ? (
          <div className="p-8 text-center text-gray-400">加载中...</div>
        ) : error ? (
          <div className="p-8 text-center text-red-400">错误: {error}</div>
        ) : filteredTasks.length === 0 ? (
          <div className="p-8 text-center text-gray-400">暂无任务</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-900/50">
                <tr>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-400">任务标题</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-400">类型</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-400">优先级</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-400">状态</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-400">分配人员</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-400">持续时间</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-400">创建时间</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-400">操作</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-700">
                {filteredTasks.map((task) => (
                  <tr key={task.task_id} className="hover:bg-gray-700/50 transition-colors">
                    <td className="px-4 py-3">
                      <div className="text-white font-medium">{task.title}</div>
                      {task.description && (
                        <div className="text-gray-400 text-sm mt-1 truncate max-w-xs">
                          {task.description}
                        </div>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-blue-400 text-sm">
                        {taskTypeLabels[task.task_type as TaskType]}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`font-semibold ${getPriorityColor(task.priority)}`}>
                        {taskPriorityLabels[task.priority]}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`px-2 py-1 rounded text-xs font-medium ${getStatusColor(
                          task.status
                        )}`}
                      >
                        {taskStatusLabels[task.status]}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="text-gray-300 text-sm">
                        {task.assigned_agents.length > 0
                          ? `${task.assigned_agents.length} 人`
                          : '未分配'}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-gray-400 text-sm">
                      {getTaskDuration(task)}
                    </td>
                    <td className="px-4 py-3 text-gray-400 text-sm">
                      {formatDate(task.created_at)}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex gap-2">
                        <button
                          onClick={() => navigate(`/workflow/tasks/${task.task_id}`)}
                          className="text-blue-400 hover:text-blue-300 text-sm"
                        >
                          查看
                        </button>
                        <button
                          onClick={() => navigate(`/workflow/tasks/${task.task_id}/edit`)}
                          className="text-green-400 hover:text-green-300 text-sm"
                        >
                          编辑
                        </button>
                        <button className="text-red-400 hover:text-red-300 text-sm">
                          删除
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

export default TasksListPage;
