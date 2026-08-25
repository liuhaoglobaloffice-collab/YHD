import React, { useMemo, useState } from 'react';
import { CheckCircle2, PlusCircle, Sparkles } from 'lucide-react';
import { createTask, CreateTaskRequest, TaskPriority, TaskType, taskPriorityLabels, taskTypeLabels } from '../../services/taskAPI';

const defaultForm = {
  title: 'Supplier review task',
  description: 'Review supplier compliance and risk assessment before approval.',
  task_type: TaskType.RESEARCH,
  priority: TaskPriority.HIGH,
  assigned_agents: 'supplier-bot,ops-agent',
  metadata: '{"source":"frontend","category":"supplier"}',
};

const TaskCreatePage: React.FC = () => {
  const [form, setForm] = useState(defaultForm);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const metadataObj = useMemo(() => {
    try {
      return JSON.parse(form.metadata || '{}');
    } catch {
      return {};
    }
  }, [form.metadata]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setMessage(null);

    const payload: CreateTaskRequest = {
      title: form.title,
      description: form.description,
      task_type: form.task_type,
      priority: form.priority,
      assigned_agents: form.assigned_agents
        .split(',')
        .map((item) => item.trim())
        .filter(Boolean),
      metadata: Object.keys(metadataObj).length ? metadataObj : { source: 'frontend' },
    };

    try {
      const task = await createTask(payload);
      setMessage(`任务已创建：${task.task_id}`);
      setError(null);
      setForm({ ...defaultForm, title: '', description: 'New task ready for execution.', metadata: '{"source":"frontend"}' });
    } catch (err: any) {
      console.error('Failed to create task:', err);
      setMessage(null);
      setError(err?.response?.data?.detail || err?.message || '创建任务失败，请检查后端任务 API 和认证状态。');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-6 max-w-4xl mx-auto text-white">
      <div className="flex items-center justify-between mb-6">
        <div>
          <p className="text-sm uppercase tracking-[0.2em] text-blue-300">Workflow</p>
          <h1 className="text-3xl font-bold mt-2">创建任务</h1>
        </div>
        <div className="flex items-center gap-2 text-blue-300">
          <Sparkles className="w-5 h-5" />
          <span className="text-sm">Task orchestration</span>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="bg-gray-800 border border-gray-700 rounded-xl p-6 space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <label className="block md:col-span-2">
            <span className="text-sm text-gray-300">任务标题</span>
            <input
              className="mt-2 w-full rounded-lg border border-gray-600 bg-gray-900 px-4 py-3 text-white outline-none focus:border-blue-500"
              value={form.title}
              onChange={(e) => setForm({ ...form, title: e.target.value })}
              required
            />
          </label>

          <label className="block md:col-span-2">
            <span className="text-sm text-gray-300">任务描述</span>
            <textarea
              className="mt-2 w-full rounded-lg border border-gray-600 bg-gray-900 px-4 py-3 text-white outline-none focus:border-blue-500 min-h-[120px]"
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
              required
            />
          </label>

          <label className="block">
            <span className="text-sm text-gray-300">任务类型</span>
            <select
              className="mt-2 w-full rounded-lg border border-gray-600 bg-gray-900 px-4 py-3 text-white outline-none focus:border-blue-500"
              value={form.task_type}
              onChange={(e) => setForm({ ...form, task_type: e.target.value as TaskType })}
            >
              {Object.entries(taskTypeLabels).map(([value, label]) => (
                <option key={value} value={value}>{label}</option>
              ))}
            </select>
          </label>

          <label className="block">
            <span className="text-sm text-gray-300">优先级</span>
            <select
              className="mt-2 w-full rounded-lg border border-gray-600 bg-gray-900 px-4 py-3 text-white outline-none focus:border-blue-500"
              value={form.priority}
              onChange={(e) => setForm({ ...form, priority: e.target.value as TaskPriority })}
            >
              {Object.entries(taskPriorityLabels).map(([value, label]) => (
                <option key={value} value={value}>{label}</option>
              ))}
            </select>
          </label>

          <label className="block md:col-span-2">
            <span className="text-sm text-gray-300">分配代理（逗号分隔）</span>
            <input
              className="mt-2 w-full rounded-lg border border-gray-600 bg-gray-900 px-4 py-3 text-white outline-none focus:border-blue-500"
              value={form.assigned_agents}
              onChange={(e) => setForm({ ...form, assigned_agents: e.target.value })}
            />
          </label>

          <label className="block md:col-span-2">
            <span className="text-sm text-gray-300">附加元数据（JSON）</span>
            <textarea
              className="mt-2 w-full rounded-lg border border-gray-600 bg-gray-900 px-4 py-3 text-white outline-none focus:border-blue-500 min-h-[100px]"
              value={form.metadata}
              onChange={(e) => setForm({ ...form, metadata: e.target.value })}
            />
          </label>
        </div>

        <div className="flex items-center gap-3">
          <button
            type="submit"
            disabled={loading}
            className="inline-flex items-center gap-2 px-5 py-3 bg-blue-600 hover:bg-blue-700 disabled:opacity-60 rounded-lg font-medium"
          >
            <PlusCircle className="w-4 h-4" />
            {loading ? '创建中...' : '创建任务'}
          </button>
        </div>

        {message && (
          <div className="border border-green-500/30 rounded-lg bg-green-500/10 px-4 py-3 text-green-300">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4" />
              <span>{message}</span>
            </div>
          </div>
        )}

        {error && (
          <div className="border border-red-500/30 rounded-lg bg-red-500/10 px-4 py-3 text-red-300">
            {error}
          </div>
        )}
      </form>
    </div>
  );
};

export default TaskCreatePage;
