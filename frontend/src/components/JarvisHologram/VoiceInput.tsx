/**
 * Jarvis 语音输入组件
 * 语音识别入口（预留接口，后续接入 Whisper）
 */

import React, { useState } from 'react';
import { Mic, MicOff } from 'lucide-react';
import { motion } from 'framer-motion';

interface VoiceInputProps {
  onVoiceInput: (text: string) => void;
  disabled?: boolean;
}

const VoiceInput: React.FC<VoiceInputProps> = ({ onVoiceInput, disabled = false }) => {
  const [isListening, setIsListening] = useState(false);

  const handleToggleListening = () => {
    if (disabled) return;

    setIsListening(!isListening);

    // TODO: 后续接入 Whisper 语音识别
    // 当前仅演示UI交互
    if (!isListening) {
      // 模拟语音识别
      setTimeout(() => {
        onVoiceInput('这是一个语音输入示例（待接入Whisper）');
        setIsListening(false);
      }, 2000);
    }
  };

  return (
    <motion.button
      onClick={handleToggleListening}
      disabled={disabled}
      whileHover={{ scale: 1.05 }}
      whileTap={{ scale: 0.95 }}
      className={`
        relative w-16 h-16 rounded-full
        flex items-center justify-center
        transition-all duration-300
        ${isListening 
          ? 'glass-heavy border-glow-red animate-pulse' 
          : 'glass border-glow-cyan'
        }
        ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
      `}
    >
      {/* 背景脉冲效果 */}
      {isListening && (
        <motion.div
          className="absolute inset-0 rounded-full border-2 border-neon-red"
          animate={{
            scale: [1, 1.5, 1],
            opacity: [0.5, 0, 0.5],
          }}
          transition={{
            duration: 1.5,
            repeat: Infinity,
          }}
        />
      )}

      {/* 图标 */}
      {isListening ? (
        <Mic className="w-6 h-6 text-neon-red animate-pulse-glow" />
      ) : (
        <MicOff className="w-6 h-6 text-neon-cyan" />
      )}

      {/* 状态指示灯 */}
      <div
        className={`
          absolute -top-1 -right-1 w-3 h-3 rounded-full
          ${isListening ? 'bg-neon-red animate-pulse' : 'bg-neon-green'}
        `}
      />
    </motion.button>
  );
};

export default VoiceInput;
