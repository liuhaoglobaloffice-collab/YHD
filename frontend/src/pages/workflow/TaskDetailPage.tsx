import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { AlertTriangle, CheckCircle2, Clock3, Cpu, PauseCircle, PlayCircle, RefreshCw } from 'lucide-react';
import {
  getTask,
  Task,
  TaskPriority,
  TaskStatus,
  taskPriorityLabels,
  taskStatusLabels,
  taskTypeLabels,
} from '../../services/taskAPI';

const TaskDetailPage: React.FC = () => {
  const { taskId } = useParams();
  const [task, setTask] = useState<Task | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      if (!taskId) {
        setError('Missing task id');
        setLoading(false);
        return;
      }

      try {
        const data = await getTask(taskId);
        setTask(data);
        setError(null);
      } catch (err) {
        console.error('Failed to load task detail:', err);
        setError('无法加载任务详情，请确认后端任务接口已启动并返回有效数据。');
      } finally {
        setLoading(false);
      }
    };

    load();
  }, [taskId]);

  if (loading) {
    return (
      <div className="p-6 flex items-center justify-center min-h-[400px] text-white">
        <div className="text-center">
          <RefreshCw className="w-8 h-8 animate-spin mx-auto text-blue-400" />
          <p className="mt-4 text-gray-300">加载任务详情中...</p>
        </div>
      </div>
    );
  }

  if (!task) {
    return (
      <div className="p-6 text-red-300">
        <AlertTriangle className="w-6 h-6 inline-block mr-2" />
        {error || '未找到任务'}
      </div>
    );
  }

  const priorityColor =
    task.priority === TaskPriority.CRITICAL
      ? 'bg-red-500/10 text-red-300'
      : task.priority === TaskPriority.URGENT
        ? 'bg-orange-500/10 text-orange-300'
        : task.priority === TaskPriority.HIGH
          ? 'bg-yellow-500/10 text-yellow-300'
          : 'bg-blue-500/10 text-blue-300';

  const statusColor =
    task.status === TaskStatus.COMPLETED
      ? 'bg-green-500/10 text-green-300'
      : task.status === TaskStatus.RUNNING
        ? 'bg-yellow-500/10 text-yellow-300'
        : task.status === TaskStatus.FAILED
          ? 'bg-red-500/10 text-red-300'
          : task.status === TaskStatus.BLOCKED
            ? 'bg-orange-500/10 text-orange-300'
            : 'bg-gray-500/10 text-gray-300';

  return (
    <div className="p-6 space-y-6 text-white">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm uppercase tracking-[0.2em] text-blue-300">Workflow</p>
          <h1 className="text-3xl font-bold mt-2">任务详情</h1>
        </div>
        <div className="flex items-center gap-3">
          <span className={`px-3 py-1 rounded-full text-sm ${priorityColor}`}>
            {taskPriorityLabels[task.priority]}
          </span>
          <span className={`px-3 py-1 rounded-full text-sm ${statusColor}`}>
            {taskStatusLabels[task.status]}
          </span>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {[
          { label: 'Task ID', value: task.task_id, icon: Cpu },
          { label: 'Type', value: taskTypeLabels[task.task_type], icon: Clock3 },
          { label: 'Agents', value: `${task.assigned_agents.length || 0} linked`, icon: PlayCircle },
          { label: 'Updated', value: new Date(task.updated_at).toLocaleString('zh-CN'), icon: CheckCircle2 },
        ].map(({ label, value, icon: Icon }) => (
          <div key={label} className="bg-gray-800 border border-gray-700 rounded-xl p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-400">{label}</p>
                <p className="text-lg font-semibold mt-2 break-all">{value}</p>
              </div>
              <div className="p-2 rounded-lg bg-blue-500/10 text-blue-300">
                <Icon className="w-5 h-5" />
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-[1.2fr_0.8fr] gap-6">
        <div className="bg-gray-800 border border-gray-700 rounded-xl p-6">
          <h2 className="text-xl font-semibold mb-4">{task.title}</h2>
          <p className="text-gray-300 leading-7">{task.description}</p>

          <div className="mt-6 space-y-4">
            <div>
              <p className="text-sm text-gray-400 mb-2">Assigned agents</p>
              <div className="flex flex-wrap gap-2">
                {task.assigned_agents.length ? task.assigned_agents.map((agent) => (
                  <span key={agent} className="px-2 py-1 rounded-full bg-gray-700 text-gray-200 text-xs">{agent}</span>
                )) : <span className="text-gray-400">未分配</span>}
              </div>
            </div>

            <div>
              <p className="text-sm text-gray-400 mb-2">Dependencies</p>
              <div className="flex flex-wrap gap-2">
                {task.dependencies.length ? task.dependencies.map((dep) => (
                  <span key={dep.task_id} className="px-2 py-1 rounded-full bg-purple-500/10 text-purple-300 text-xs">{dep.task_id}</span>
                )) : <span className="text-gray-400">No dependencies</span>}
              </div>
            </div>
          </div>
        </div>

        <div className="bg-gray-800 border border-gray-700 rounded-xl p-6">
          <h2 className="text-xl font-semibold mb-4">Execution summary</h2>
          <div className="space-y-4 text-sm">
            <div className="flex justify-between border-b border-gray-700 pb-3">
              <span className="text-gray-400">Created by</span>
              <span>{task.created_by}</span>
            </div>
            <div className="flex justify-between border-b border-gray-700 pb-3">
              <span className="text-gray-400">Created</span>
              <span>{new Date(task.created_at).toLocaleString('zh-CN')}</span>
            </div>
            <div className="flex justify-between border-b border-gray-700 pb-3">
              <span className="text-gray-400">Started</span>
              <span>{task.started_at ? new Date(task.started_at).toLocaleString('zh-CN') : 'Not started'}</span>
            </div>
            <div className="flex justify-between border-b border-gray-700 pb-3">
              <span className="text-gray-400">Completed</span>
              <span>{task.completed_at ? new Date(task.completed_at).toLocaleString('zh-CN') : 'Pending'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">Result</span>
              <span>{task.result ? 'Available' : 'No result yet'}</span>
            </div>
          </div>
        </div>
      </div>

      {error && (
        <div className="rounded-lg border border-yellow-500/30 bg-yellow-500/10 text-yellow-200 p-3">
          {error}
        </div>
      )}
    </div>
  );
};

export default TaskDetailPage;
