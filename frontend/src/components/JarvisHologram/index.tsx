/**
 * Jarvis 全息助手主入口组件
 * 整合所有子组件，提供完整的 Jarvis 交互体验
 */

import React, { useState, Suspense } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls, PerspectiveCamera } from '@react-three/drei';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Minimize2 } from 'lucide-react';

import Model from './Model';
import HologramRings from './HologramRings';
import Particles from './Particles';
import DialogBubble from './DialogBubble';
import VoiceInput from './VoiceInput';
import QuickActions from './QuickActions';
import { stateConfigs, type JarvisState } from './animations';

interface JarvisHologramProps {
  isOpen: boolean;
  onClose: () => void;
}

const JarvisHologram: React.FC<JarvisHologramProps> = ({ isOpen, onClose }) => {
  const [jarvisState, setJarvisState] = useState<JarvisState>('idle');
  const [message, setMessage] = useState('你好，我是鎏灏AI助手Jarvis，有什么可以帮您？');
  const [isMinimized, setIsMinimized] = useState(false);

  // 处理语音输入
  const handleVoiceInput = (text: string) => {
    setMessage(`收到：${text}`);
    setJarvisState('thinking');

    // 模拟AI处理
    setTimeout(() => {
      setJarvisState('speaking');
      setMessage('我正在为您处理...');

      setTimeout(() => {
        setJarvisState('success');
        setMessage('任务已完成！');

        setTimeout(() => {
          setJarvisState('idle');
          setMessage('还有其他需要帮助的吗？');
        }, 2000);
      }, 2000);
    }, 1000);
  };

  // 处理快捷操作
  const handleQuickAction = (actionId: string) => {
    const actionMessages = {
      search: '正在启动智能搜索...',
      analyze: '正在分析数据...',
      report: '正在生成报告...',
      risk: '正在进行风险检测...',
      check: '正在执行质量检查...',
      chat: '进入AI对话模式...',
    };

    setJarvisState('working');
    setMessage(actionMessages[actionId as keyof typeof actionMessages] || '正在处理...');

    // TODO: 连接到现有AI系统
    // 调用后端API执行实际任务

    setTimeout(() => {
      setJarvisState('success');
      setMessage('操作成功！');

      setTimeout(() => {
        setJarvisState('idle');
        setMessage('还需要其他帮助吗？');
      }, 2000);
    }, 2000);
  };

  const config = stateConfigs[jarvisState];

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ 
            opacity: 1, 
            scale: isMinimized ? 0.5 : 1,
            y: isMinimized ? '60vh' : 0,
            x: isMinimized ? '45vw' : 0,
          }}
          exit={{ opacity: 0, scale: 0.9 }}
          transition={{ duration: 0.3 }}
          className={`
            fixed inset-0 z-50 flex items-center justify-center
            ${isMinimized ? 'pointer-events-none' : ''}
          `}
        >
          {/* 背景遮罩 */}
          {!isMinimized && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="absolute inset-0 bg-black/60 backdrop-blur-sm"
              onClick={onClose}
            />
          )}

          {/* Jarvis 容器 */}
          <motion.div
            className={`
              relative
              ${isMinimized 
                ? 'w-32 h-32 rounded-full pointer-events-auto' 
                : 'w-full max-w-4xl h-[80vh] rounded-2xl'
              }
              glass-heavy border-glow-cyan
              overflow-hidden
              transition-all duration-500
            `}
            onClick={isMinimized ? () => setIsMinimized(false) : undefined}
          >
            {/* 控制按钮 */}
            {!isMinimized && (
              <div className="absolute top-4 right-4 z-10 flex space-x-2">
                <button
                  onClick={() => setIsMinimized(true)}
                  className="glass rounded-full p-2 border-glow-cyan hover:border-glow-blue transition-all"
                >
                  <Minimize2 className="w-5 h-5 text-neon-cyan" />
                </button>
                <button
                  onClick={onClose}
                  className="glass rounded-full p-2 border-glow-red hover:border-glow-yellow transition-all"
                >
                  <X className="w-5 h-5 text-neon-red" />
                </button>
              </div>
            )}

            {/* Three.js 场景 - Jarvis 3D全息 */}
            <div className={isMinimized ? 'w-full h-full' : 'w-full h-2/3'}>
              <Canvas>
                <Suspense fallback={null}>
                  {/* 相机 */}
                  <PerspectiveCamera makeDefault position={[0, 0, 8]} />

                  {/* 灯光 */}
                  <ambientLight intensity={0.3} />
                  <pointLight position={[10, 10, 10]} intensity={0.8} color="#00d9ff" />
                  <pointLight position={[-10, -10, -10]} intensity={0.5} color="#9900ff" />

                  {/* Jarvis 核心模型 */}
                  <Model state={jarvisState} />

                  {/* 全息圆环 */}
                  <HologramRings state={jarvisState} />

                  {/* 粒子系统 */}
                  <Particles count={config.particleCount} state={jarvisState} />

                  {/* 轨道控制（鼠标交互） */}
                  {!isMinimized && (
                    <OrbitControls
                      enableZoom={false}
                      enablePan={false}
                      minPolarAngle={Math.PI / 3}
                      maxPolarAngle={Math.PI / 1.5}
                      autoRotate={jarvisState === 'idle'}
                      autoRotateSpeed={0.5}
                    />
                  )}
                </Suspense>
              </Canvas>
            </div>

            {/* UI 交互区域 */}
            {!isMinimized && (
              <div className="absolute bottom-0 left-0 right-0 p-6 space-y-4 bg-gradient-to-t from-surface-dark/90 to-transparent">
                {/* 对话气泡 */}
                <DialogBubble
                  message={message}
                  visible={true}
                  type={
                    jarvisState === 'success' ? 'success' :
                    jarvisState === 'warning' ? 'warning' :
                    'info'
                  }
                />

                {/* 快捷操作 */}
                <div className="glass-md rounded-lg p-4 border-glow-blue">
                  <h3 className="text-sm font-semibold text-neon-cyan mb-3">快捷操作</h3>
                  <QuickActions onAction={handleQuickAction} />
                </div>

                {/* 语音输入 */}
                <div className="flex justify-center">
                  <VoiceInput
                    onVoiceInput={handleVoiceInput}
                    disabled={jarvisState === 'working' || jarvisState === 'thinking'}
                  />
                </div>

                {/* 状态指示 */}
                <div className="flex items-center justify-center space-x-2 text-xs text-text-secondary">
                  <div 
                    className="w-2 h-2 rounded-full animate-pulse"
                    style={{ backgroundColor: config.coreGlowColor }}
                  />
                  <span>
                    {jarvisState === 'idle' && '待机中'}
                    {jarvisState === 'thinking' && '思考中...'}
                    {jarvisState === 'working' && '工作中...'}
                    {jarvisState === 'speaking' && '回复中...'}
                    {jarvisState === 'success' && '成功'}
                    {jarvisState === 'warning' && '警告'}
                  </span>
                </div>
              </div>
            )}
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};

export default JarvisHologram;
