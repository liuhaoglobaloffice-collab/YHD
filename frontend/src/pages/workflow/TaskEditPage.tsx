import React, { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { CheckCircle2, PencilLine, RefreshCw } from 'lucide-react';
import {
  getTask,
  Task,
  TaskStatus,
  taskPriorityLabels,
  taskTypeLabels,
  updateTaskStatus,
} from '../../services/taskAPI';

const TaskEditPage: React.FC = () => {
  const { taskId } = useParams();
  const navigate = useNavigate();
  const [task, setTask] = useState<Task | null>(null);
  const [status, setStatus] = useState<TaskStatus | ''>('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      if (!taskId) {
        setLoading(false);
        return;
      }
      try {
        const data = await getTask(taskId);
        setTask(data);
        setStatus(data.status);
      } catch (err) {
        console.error('Failed to load task for edit:', err);
        setTask(null);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [taskId]);

  const handleSave = async () => {
    if (!taskId || !status) return;
    setSaving(true);
    setMessage(null);
    try {
      await updateTaskStatus(taskId, { status });
      setMessage('状态已更新');
      navigate(`/workflow/tasks/${taskId}`);
    } catch (err) {
      console.error('Failed to update task status:', err);
      setMessage('状态更新失败，请检查后端任务 API 与权限配置。');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="p-6 flex items-center justify-center min-h-[400px] text-white">
        <div className="text-center">
          <RefreshCw className="w-8 h-8 animate-spin mx-auto text-blue-400" />
          <p className="mt-4 text-gray-300">加载任务中...</p>
        </div>
      </div>
    );
  }

  if (!task) {
    return <div className="p-6 text-red-300">任务不存在</div>;
  }

  return (
    <div className="p-6 max-w-3xl mx-auto text-white">
      <div className="flex items-center justify-between mb-6">
        <div>
          <p className="text-sm uppercase tracking-[0.2em] text-blue-300">Workflow</p>
          <h1 className="text-3xl font-bold mt-2">编辑任务</h1>
        </div>
        <div className="flex items-center gap-2 text-blue-300">
          <PencilLine className="w-5 h-5" />
          <span className="text-sm">Task edit</span>
        </div>
      </div>

      <div className="bg-gray-800 border border-gray-700 rounded-xl p-6 space-y-6">
        <div>
          <label className="text-sm text-gray-300">任务标题</label>
          <input
            readOnly
            value={task.title}
            className="mt-2 w-full rounded-lg border border-gray-600 bg-gray-900 px-4 py-3 text-white"
          />
        </div>

        <div>
          <label className="text-sm text-gray-300">任务类型</label>
          <input
            readOnly
            value={taskTypeLabels[task.task_type] || task.task_type}
            className="mt-2 w-full rounded-lg border border-gray-600 bg-gray-900 px-4 py-3 text-white"
          />
        </div>

        <div>
          <label className="text-sm text-gray-300">任务状态</label>
          <select
            className="mt-2 w-full rounded-lg border border-gray-600 bg-gray-900 px-4 py-3 text-white outline-none focus:border-blue-500"
            value={status}
            onChange={(e) => setStatus(e.target.value as TaskStatus)}
          >
            {Object.entries({
              [TaskStatus.PENDING]: '待处理',
              [TaskStatus.READY]: '准备就绪',
              [TaskStatus.RUNNING]: '执行中',
              [TaskStatus.COMPLETED]: '已完成',
              [TaskStatus.FAILED]: '失败',
              [TaskStatus.CANCELLED]: '已取消',
              [TaskStatus.BLOCKED]: '阻塞中',
            }).map(([value, label]) => (
              <option key={value} value={value}>{label}</option>
            ))}
          </select>
        </div>

        <div>
          <label className="text-sm text-gray-300">优先级</label>
          <input
            readOnly
            value={taskPriorityLabels[task.priority] || task.priority}
            className="mt-2 w-full rounded-lg border border-gray-600 bg-gray-900 px-4 py-3 text-white"
          />
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleSave}
            disabled={saving}
            className="px-5 py-3 bg-blue-600 hover:bg-blue-700 disabled:opacity-60 rounded-lg font-medium"
          >
            {saving ? '保存中...' : '保存更改'}
          </button>
          <button
            onClick={() => navigate(`/workflow/tasks/${taskId}`)}
            className="px-5 py-3 bg-gray-700 hover:bg-gray-600 rounded-lg font-medium"
          >
            取消
          </button>
        </div>

        {message && (
          <div className="border border-green-500/30 rounded-lg bg-green-500/10 px-4 py-3 text-green-300 flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4" />
            {message}
          </div>
        )}
      </div>
    </div>
  );
};

export default TaskEditPage;
