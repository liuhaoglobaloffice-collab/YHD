/**
 * Jarvis 对话气泡组件
 * 显示AI回复和状态信息
 */

import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';

interface DialogBubbleProps {
  message: string;
  visible: boolean;
  type?: 'info' | 'success' | 'warning' | 'error';
}

const DialogBubble: React.FC<DialogBubbleProps> = ({ message, visible, type = 'info' }) => {
  const typeStyles = {
    info: 'border-neon-cyan bg-neon-cyan/10',
    success: 'border-neon-green bg-neon-green/10',
    warning: 'border-neon-yellow bg-neon-yellow/10',
    error: 'border-neon-red bg-neon-red/10',
  };

  const typeTextColors = {
    info: 'text-neon-cyan',
    success: 'text-neon-green',
    warning: 'text-neon-yellow',
    error: 'text-neon-red',
  };

  return (
    <AnimatePresence>
      {visible && message && (
        <motion.div
          initial={{ opacity: 0, y: 20, scale: 0.9 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: -20, scale: 0.9 }}
          transition={{ duration: 0.3 }}
          className={`
            absolute bottom-4 left-1/2 transform -translate-x-1/2
            max-w-md w-full
            glass-md rounded-lg p-4
            border-2 ${typeStyles[type]}
            scan-lines
          `}
        >
          <div className="flex items-start space-x-3">
            {/* 指示灯 */}
            <div className={`mt-1 w-2 h-2 rounded-full ${typeTextColors[type]} animate-pulse-glow`} />
            
            {/* 消息内容 */}
            <div className="flex-1">
              <p className={`text-sm ${typeTextColors[type]} leading-relaxed`}>
                {message}
              </p>
            </div>

            {/* 波形动画 - 说话时 */}
            {type === 'info' && (
              <div className="flex items-center space-x-1">
                {[...Array(3)].map((_, i) => (
                  <motion.div
                    key={i}
                    className="w-1 bg-neon-cyan rounded-full"
                    animate={{
                      height: [4, 12, 4],
                    }}
                    transition={{
                      duration: 0.6,
                      repeat: Infinity,
                      delay: i * 0.1,
                    }}
                  />
                ))}
              </div>
            )}
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};

export default DialogBubble;
