/**
 * Jarvis 快捷操作组件
 * 快速触发常用AI任务
 */

import React from 'react';
import { motion } from 'framer-motion';
import { 
  Search, 
  FileText, 
  BarChart3, 
  AlertTriangle, 
  CheckCircle,
  MessageSquare 
} from 'lucide-react';

interface QuickAction {
  id: string;
  label: string;
  icon: React.ElementType;
  color: string;
  action: () => void;
}

interface QuickActionsProps {
  onAction: (actionId: string) => void;
}

const QuickActions: React.FC<QuickActionsProps> = ({ onAction }) => {
  const actions: QuickAction[] = [
    {
      id: 'search',
      label: '智能搜索',
      icon: Search,
      color: 'text-neon-cyan',
      action: () => onAction('search'),
    },
    {
      id: 'analyze',
      label: '数据分析',
      icon: BarChart3,
      color: 'text-neon-blue',
      action: () => onAction('analyze'),
    },
    {
      id: 'report',
      label: '生成报告',
      icon: FileText,
      color: 'text-neon-purple',
      action: () => onAction('report'),
    },
    {
      id: 'risk',
      label: '风险检测',
      icon: AlertTriangle,
      color: 'text-neon-yellow',
      action: () => onAction('risk'),
    },
    {
      id: 'check',
      label: '质量检查',
      icon: CheckCircle,
      color: 'text-neon-green',
      action: () => onAction('check'),
    },
    {
      id: 'chat',
      label: 'AI对话',
      icon: MessageSquare,
      color: 'text-neon-cyan',
      action: () => onAction('chat'),
    },
  ];

  return (
    <div className="grid grid-cols-3 gap-3">
      {actions.map((action, index) => (
        <motion.button
          key={action.id}
          onClick={action.action}
          initial={{ opacity: 0, scale: 0.8 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: index * 0.05 }}
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          className={`
            glass rounded-lg p-3
            border-glow-cyan
            hover:border-glow-blue
            transition-all duration-300
            flex flex-col items-center justify-center
            space-y-2
            group
          `}
        >
          <action.icon 
            className={`w-6 h-6 ${action.color} group-hover:animate-pulse-glow transition-all`} 
          />
          <span className="text-xs text-text-secondary group-hover:text-white transition-colors">
            {action.label}
          </span>
        </motion.button>
      ))}
    </div>
  );
};

export default QuickActions;
