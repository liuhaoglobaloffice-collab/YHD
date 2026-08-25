import React from 'react';
import { CalendarDays, Clock3, Filter, ListTodo } from 'lucide-react';

const dates = [
  { day: 'Mon', date: '19', tasks: 2 },
  { day: 'Tue', date: '20', tasks: 4, primary: true },
  { day: 'Wed', date: '21', tasks: 3 },
  { day: 'Thu', date: '22', tasks: 5 },
  { day: 'Fri', date: '23', tasks: 2 },
  { day: 'Sat', date: '24', tasks: 1 },
  { day: 'Sun', date: '25', tasks: 0 },
];

const daySchedule = [
  { time: '09:00', title: 'Supplier sync review', type: 'Ops', status: 'In progress' },
  { time: '11:30', title: 'AI provider health check', type: 'Platform', status: 'Queued' },
  { time: '14:00', title: 'Workflow approval queue', type: 'Workflow', status: 'Scheduled' },
  { time: '16:30', title: 'Sales lead follow-up', type: 'Sales', status: 'Waiting' },
];

const TaskCalendarPage: React.FC = () => {
  return (
    <div className="p-6 space-y-6 text-white">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm uppercase tracking-[0.2em] text-purple-300">Workflow</p>
          <h1 className="text-3xl font-bold mt-2">任务日历</h1>
        </div>
        <div className="flex items-center gap-2 px-3 py-2 bg-purple-500/10 border border-purple-500/20 rounded-lg text-purple-300">
          <CalendarDays className="w-4 h-4" />
          <span className="text-sm">Weekly planner</span>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-[1.2fr_0.8fr] gap-6">
        <div className="bg-gray-800 border border-gray-700 rounded-xl p-5">
          <div className="flex items-center justify-between mb-5">
            <div className="flex items-center gap-2 text-purple-300">
              <ListTodo className="w-4 h-4" />
              <span className="font-medium">This week</span>
            </div>
            <div className="flex items-center gap-2 text-gray-400 text-sm">
              <Filter className="w-4 h-4" />
              <span>All tasks</span>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-7 gap-3">
            {dates.map((item) => (
              <div
                key={item.date}
                className={`rounded-xl border p-3 ${item.primary ? 'bg-purple-500/10 border-purple-500/30' : 'bg-gray-900 border-gray-700'}`}
              >
                <p className="text-xs uppercase tracking-[0.2em] text-gray-400">{item.day}</p>
                <p className="text-2xl font-bold mt-2">{item.date}</p>
                <div className="mt-3 flex items-center justify-between text-xs text-gray-300">
                  <span>{item.tasks} tasks</span>
                  {item.tasks > 0 && <span className="w-2 h-2 rounded-full bg-purple-400" />}
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-gray-800 border border-gray-700 rounded-xl p-5">
          <div className="flex items-center gap-2 text-purple-300 mb-4">
            <Clock3 className="w-4 h-4" />
            <span className="font-medium">Daily agenda</span>
          </div>
          <div className="space-y-3">
            {daySchedule.map((task) => (
              <div key={task.time} className="flex items-center justify-between gap-3 rounded-lg bg-gray-900 border border-gray-700 px-3 py-3">
                <div>
                  <p className="text-sm font-medium">{task.title}</p>
                  <p className="text-xs text-gray-400 mt-1">{task.type}</p>
                </div>
                <div className="text-right">
                  <p className="text-xs text-gray-400">{task.time}</p>
                  <p className="text-xs mt-1 text-purple-300">{task.status}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default TaskCalendarPage;
