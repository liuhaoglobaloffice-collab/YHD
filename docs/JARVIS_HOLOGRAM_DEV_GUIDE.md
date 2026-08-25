# 🤖 贾维斯3D全息形象开发详细指南

**版本**: v5.3 Final  
**创建日期**: 2026-08-24  
**开发周期**: Week 7 Day 3-4 + Week 9 (10天)  
**优先级**: ⭐⭐⭐⭐⭐ 最高优先级

---

## 🎯 项目概述

### **核心定位**

> **贾维斯是整个鎏灏AI-OS的视觉焦点和交互中心，用户对系统的第一印象和核心体验**

```yaml
设计目标:
  - 视觉冲击: 3D全息投影，科技感十足
  - 情感连接: 让用户感觉在和"真人"对话
  - 交互自然: 语音/文字/手势多模态交互
  - 性能流畅: 60fps流畅运行，无卡顿

参考案例:
  - 钢铁侠贾维斯（电影）⭐⭐⭐⭐⭐
  - 银翼杀手2049全息女友
  - Halo游戏中的Cortana
  - 星际迷航全息医生
```

### **技术架构**

```
┌─────────────────────────────────────┐
│       贾维斯3D全息形象系统          │
├─────────────────────────────────────┤
│                                     │
│  ┌──────────┐   ┌──────────────┐  │
│  │ 3D模型   │   │  动画系统    │  │
│  │ Three.js │◄──┤ Framer Motion│  │
│  └──────────┘   └──────────────┘  │
│       ▲                 ▲          │
│       │                 │          │
│  ┌────┴────┐      ┌────┴─────┐   │
│  │全息圆环 │      │ 粒子系统 │   │
│  └─────────┘      └──────────┘   │
│                                     │
│  ┌─────────────────────────────┐  │
│  │      语音交互系统            │  │
│  ├─────────────────────────────┤  │
│  │ ASR → AI → TTS → 口型同步  │  │
│  └─────────────────────────────┘  │
│                                     │
│  ┌─────────────────────────────┐  │
│  │      对话气泡 UI             │  │
│  └─────────────────────────────┘  │
│                                     │
└─────────────────────────────────────┘
```

---

## 🛠️ 技术栈

### **前端技术**

```yaml
3D渲染:
  - Three.js: 3D引擎
  - React Three Fiber: Three.js的React封装
  - drei: R3F工具库（OrbitControls/useGLTF等）

动画:
  - Framer Motion: UI动画
  - GSAP: 复杂动画
  - React Spring: 物理动画

粒子系统:
  - tsparticles: 粒子引擎
  - 自定义Canvas粒子（性能更好）

UI框架:
  - React 18
  - TypeScript
  - TailwindCSS
  - shadcn/ui
```

### **后端支持**

```yaml
语音服务:
  - ASR: OpenAI Whisper
  - TTS: Azure Neural TTS
  - 音频处理: WebRTC/MediaStream

AI服务:
  - 对话: GPT-4
  - 情感分析: GPT-4
  - 意图识别: GPT-4

实时通信:
  - WebSocket: 实时语音流
  - Server-Sent Events: 流式响应
```

---

## 📦 项目结构

```
frontend/src/components/JarvisHologram/
├── index.tsx                    # 主组件
├── Model.tsx                    # 3D头像模型
├── HologramRings.tsx            # 全息圆环
├── Particles.tsx                # 粒子背景
├── DialogBubble.tsx             # 对话气泡
├── VoiceInput.tsx               # 语音输入框
├── QuickActions.tsx             # 快捷操作按钮
├── animations.ts                # 动画状态机
├── audio-visualizer.tsx         # 音频可视化
├── lip-sync.ts                  # 口型同步算法
├── gesture-system.ts            # 手势系统
└── types.ts                     # TypeScript类型定义

public/
└── models/
    └── jarvis-head.glb          # 3D模型文件

backend/src/jarvis/
├── voice_input.py               # 语音输入
├── voice_output.py              # 语音输出
├── animation_controller.py      # 动画控制
└── websocket_handler.py         # WebSocket处理
```

---

## 🎨 核心组件开发

### **1. 主组件（JarvisHologram/index.tsx）**

```typescript
// frontend/src/components/JarvisHologram/index.tsx

import { Canvas } from '@react-three/fiber';
import { OrbitControls, PerspectiveCamera } from '@react-three/drei';
import { Suspense, useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { JarvisModel } from './Model';
import { HologramRings } from './HologramRings';
import { ParticleBackground } from './Particles';
import { DialogBubble } from './DialogBubble';
import { VoiceInput } from './VoiceInput';
import { QuickActions } from './QuickActions';
import { useWebSocket } from '@/hooks/useWebSocket';

export const JarvisHologram = () => {
  // 状态管理
  const [animationState, setAnimationState] = useState<AnimationState>('idle');
  const [message, setMessage] = useState("老板，我已准备就绪！今天可以帮您做点什么？");
  const [isListening, setIsListening] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [subtitles, setSubtitles] = useState<Subtitle[]>([]);
  
  // WebSocket连接
  const { connected, send, on } = useWebSocket('ws://localhost:8000/ws/jarvis');
  
  // 监听后端事件
  useEffect(() => {
    if (!connected) return;
    
    // 接收消息
    on('message', (data) => {
      setMessage(data.text);
      setAnimationState('speaking');
    });
    
    // 接收语音识别结果
    on('transcription', (data) => {
      setSubtitles(prev => [...prev, {
        type: 'user',
        text: data.text,
        timestamp: Date.now(),
      }]);
    });
    
    // 接收动画指令
    on('animation', (data) => {
      setAnimationState(data.state);
    });
  }, [connected]);
  
  // 语音输入
  const handleVoiceInput = async (audioBlob: Blob) => {
    setIsListening(true);
    setAnimationState('listening');
    
    // 发送音频到后端
    await send({
      type: 'voice_input',
      audio: await audioBlob.arrayBuffer(),
    });
  };
  
  // 文字输入
  const handleTextInput = async (text: string) => {
    setAnimationState('thinking');
    
    // 发送文本到后端
    await send({
      type: 'text_input',
      text: text,
    });
  };
  
  return (
    <div className="relative w-full h-screen overflow-hidden bg-[#0a1628]">
      {/* 背景粒子 */}
      <ParticleBackground />
      
      {/* 3D Canvas */}
      <Canvas
        className="absolute inset-0"
        gl={{ antialias: true, alpha: true }}
        dpr={[1, 2]}
      >
        <Suspense fallback={null}>
          {/* 相机 */}
          <PerspectiveCamera
            makeDefault
            position={[0, 0, 5]}
            fov={45}
          />
          
          {/* 灯光 */}
          <ambientLight intensity={0.5} />
          <pointLight
            position={[10, 10, 10]}
            intensity={1}
            color="#00d9ff"
            distance={20}
          />
          <pointLight
            position={[-10, -10, -10]}
            intensity={0.5}
            color="#9900ff"
            distance={20}
          />
          <spotLight
            position={[0, 10, 0]}
            angle={0.3}
            penumbra={1}
            intensity={1}
            color="#00ffff"
            castShadow
          />
          
          {/* 贾维斯3D模型 */}
          <JarvisModel
            animationState={animationState}
            isSpeaking={isSpeaking}
            audioData={audioData}
          />
          
          {/* 轨道控制器（可选） */}
          <OrbitControls
            enableZoom={false}
            enablePan={false}
            minPolarAngle={Math.PI / 3}
            maxPolarAngle={Math.PI / 1.5}
            autoRotate={animationState === 'idle'}
            autoRotateSpeed={0.5}
          />
        </Suspense>
      </Canvas>
      
      {/* 全息圆环 */}
      <HologramRings
        animationState={animationState}
        isActive={connected}
      />
      
      {/* 标题 */}
      <motion.div
        className="absolute bottom-32 left-1/2 -translate-x-1/2 text-center pointer-events-none"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.5 }}
      >
        <h2 className="text-5xl font-bold text-cyan-400 font-display tracking-wider mb-2">
          JARVIS
        </h2>
        <p className="text-gray-400 text-lg">
          Your AI Business Partner
        </p>
        {connected && (
          <div className="mt-2 flex items-center justify-center gap-2 text-green-400">
            <span className="w-2 h-2 bg-green-400 rounded-full animate-pulse" />
            <span className="text-sm">在线</span>
          </div>
        )}
      </motion.div>
      
      {/* 对话气泡 */}
      <DialogBubble
        message={message}
        isListening={isListening}
        isSpeaking={isSpeaking}
      />
      
      {/* 快捷操作 */}
      <QuickActions
        onAction={(action) => handleTextInput(action)}
      />
      
      {/* 语音输入框 */}
      <VoiceInput
        onVoiceInput={handleVoiceInput}
        onTextInput={handleTextInput}
        isListening={isListening}
        disabled={!connected}
      />
      
      {/* 字幕（可选） */}
      {subtitles.length > 0 && (
        <div className="absolute bottom-24 left-1/2 -translate-x-1/2 w-full max-w-2xl px-4">
          <AnimatePresence>
            {subtitles.slice(-3).map((subtitle, index) => (
              <motion.div
                key={subtitle.timestamp}
                className={`
                  mb-2 p-3 rounded-lg
                  ${subtitle.type === 'user'
                    ? 'bg-cyan-500/20 border border-cyan-500/30 text-cyan-400'
                    : 'bg-blue-500/20 border border-blue-500/30 text-blue-400'
                  }
                `}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
              >
                <span className="text-sm">{subtitle.text}</span>
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
      )}
    </div>
  );
};
```

---

### **2. 3D头像模型（Model.tsx）** ⭐

```typescript
// frontend/src/components/JarvisHologram/Model.tsx

import { useGLTF, useAnimations } from '@react-three/drei';
import { useFrame, useThree } from '@react-three/fiber';
import { useRef, useEffect, useMemo } from 'react';
import * as THREE from 'three';
import { useLipSync } from './lip-sync';

interface JarvisModelProps {
  animationState: AnimationState;
  isSpeaking: boolean;
  audioData?: Uint8Array;
}

export const JarvisModel: React.FC<JarvisModelProps> = ({
  animationState,
  isSpeaking,
  audioData,
}) => {
  const groupRef = useRef<THREE.Group>(null);
  const { scene, animations } = useGLTF('/models/jarvis-head.glb');
  const { actions } = useAnimations(animations, groupRef);
  const { gl } = useThree();
  
  // 口型同步
  const { mouthOpenAmount } = useLipSync(audioData, isSpeaking);
  
  // 呼吸动画
  useFrame((state) => {
    if (!groupRef.current) return;
    
    const elapsed = state.clock.elapsedTime;
    
    // 待机状态：轻微呼吸 + 自动旋转
    if (animationState === 'idle') {
      groupRef.current.rotation.y = Math.sin(elapsed * 0.3) * 0.1;
      groupRef.current.scale.setScalar(1 + Math.sin(elapsed * 2) * 0.02);
    }
    
    // 监听状态：倾听姿态
    if (animationState === 'listening') {
      groupRef.current.rotation.y = Math.sin(elapsed * 0.5) * 0.15;
      groupRef.current.rotation.z = Math.sin(elapsed * 0.3) * 0.05;
    }
    
    // 说话状态：口型同步
    if (animationState === 'speaking' && isSpeaking) {
      // 嘴部动画（根据音频振幅）
      scene.traverse((child) => {
        if (child.name === 'Mouth') {
          child.morphTargetInfluences[0] = mouthOpenAmount;
        }
      });
      
      // 轻微头部摇晃
      groupRef.current.rotation.x = Math.sin(elapsed * 3) * 0.05;
      groupRef.current.rotation.y = Math.sin(elapsed * 2) * 0.08;
    }
    
    // 思考状态：更快的旋转
    if (animationState === 'thinking') {
      groupRef.current.rotation.y += 0.02;
    }
  });
  
  // 发光材质
  useEffect(() => {
    scene.traverse((child) => {
      if (child.isMesh) {
        // 基础材质
        child.material = new THREE.MeshStandardMaterial({
          color: child.material.color,
          metalness: 0.8,
          roughness: 0.2,
          emissive: new THREE.Color(0x00d9ff),
          emissiveIntensity: animationState === 'listening' ? 1.0 : 0.5,
          transparent: true,
          opacity: 0.9,
        });
        
        // 添加边缘光
        child.material.onBeforeCompile = (shader) => {
          shader.uniforms.glowColor = { value: new THREE.Color(0x00ffff) };
          shader.fragmentShader = `
            uniform vec3 glowColor;
            ${shader.fragmentShader}
          `.replace(
            `#include <output_fragment>`,
            `
            #include <output_fragment>
            
            // 边缘光（Fresnel）
            vec3 viewDirection = normalize(vViewPosition);
            vec3 normal = normalize(vNormal);
            float fresnel = pow(1.0 - abs(dot(viewDirection, normal)), 3.0);
            gl_FragColor.rgb += glowColor * fresnel * 0.5;
            `
          );
        };
      }
    });
  }, [scene, animationState]);
  
  // 播放动画
  useEffect(() => {
    if (!actions) return;
    
    // 停止所有动画
    Object.values(actions).forEach(action => action?.stop());
    
    // 播放对应动画
    const animationMap = {
      idle: 'Idle',
      listening: 'Listen',
      speaking: 'Talk',
      thinking: 'Think',
    };
    
    const animationName = animationMap[animationState];
    if (animationName && actions[animationName]) {
      actions[animationName]?.reset().fadeIn(0.5).play();
    }
  }, [animationState, actions]);
  
  return (
    <group ref={groupRef} position={[0, 0, 0]}>
      <primitive object={scene} scale={2} />
      
      {/* 环境光探针（改善光照） */}
      <mesh position={[0, 0, 0]}>
        <sphereGeometry args={[10, 32, 32]} />
        <meshBasicMaterial
          color="#00d9ff"
          transparent
          opacity={0.05}
          side={THREE.BackSide}
        />
      </mesh>
    </group>
  );
};

// 预加载模型
useGLTF.preload('/models/jarvis-head.glb');
```

---

### **3. 全息圆环（HologramRings.tsx）**

```typescript
// frontend/src/components/JarvisHologram/HologramRings.tsx

import { motion } from 'framer-motion';

interface HologramRingsProps {
  animationState: AnimationState;
  isActive: boolean;
}

export const HologramRings: React.FC<HologramRingsProps> = ({
  animationState,
  isActive,
}) => {
  // 根据状态调整动画速度
  const duration = {
    idle: 4,
    listening: 2,
    speaking: 3,
    thinking: 1.5,
  }[animationState];
  
  return (
    <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
      {/* 外层圆环（3个） */}
      {[0, 1, 2].map((index) => (
        <motion.div
          key={`outer-${index}`}
          className="absolute border-2 border-cyan-500/20 rounded-full"
          style={{
            width: `${60 + index * 10}%`,
            height: `${60 + index * 10}%`,
          }}
          initial={{ scale: 0.8, opacity: 0 }}
          animate={{
            scale: [0.8, 1.2, 0.8],
            opacity: [0, 0.5, 0],
            rotate: [0, 360],
          }}
          transition={{
            duration: duration,
            repeat: Infinity,
            delay: index * (duration / 3),
            ease: "easeInOut"
          }}
        />
      ))}
      
      {/* 内圈发光圆环 */}
      <motion.div
        className="absolute w-96 h-96 border-4 border-cyan-400/40 rounded-full shadow-glow-cyan"
        animate={{
          rotate: 360,
          scale: isActive ? [1, 1.02, 1] : 1,
        }}
        transition={{
          rotate: {
            duration: 20,
            repeat: Infinity,
            ease: "linear"
          },
          scale: {
            duration: 2,
            repeat: Infinity,
            ease: "easeInOut"
          }
        }}
      />
      
      {/* 中心发光点 */}
      <motion.div
        className="absolute w-4 h-4 bg-cyan-400 rounded-full"
        animate={{
          scale: animationState === 'listening' ? [1, 1.5, 1] : 1,
          opacity: animationState === 'listening' ? [1, 0.5, 1] : 1,
        }}
        transition={{
          duration: 1,
          repeat: Infinity,
          ease: "easeInOut"
        }}
      />
      
      {/* 扫描线 */}
      {animationState === 'thinking' && (
        <motion.div
          className="absolute w-full h-1 bg-gradient-to-r from-transparent via-cyan-400 to-transparent"
          initial={{ top: '0%' }}
          animate={{ top: '100%' }}
          transition={{
            duration: 2,
            repeat: Infinity,
            ease: "linear"
          }}
        />
      )}
    </div>
  );
};
```

---

### **4. 粒子背景（Particles.tsx）**

```typescript
// frontend/src/components/JarvisHologram/Particles.tsx

import Particles from 'react-tsparticles';
import { loadFull } from 'tsparticles';
import { useCallback } from 'react';

export const ParticleBackground = () => {
  const particlesInit = useCallback(async (engine) => {
    await loadFull(engine);
  }, []);
  
  return (
    <Particles
      id="jarvis-particles"
      className="absolute inset-0"
      init={particlesInit}
      options={{
        fullScreen: false,
        background: {
          color: "transparent"
        },
        fpsLimit: 60,
        particles: {
          number: {
            value: 100,
            density: {
              enable: true,
              area: 800
            }
          },
          color: {
            value: ["#00d9ff", "#00ffff", "#0099ff", "#9900ff"]
          },
          shape: {
            type: "circle"
          },
          opacity: {
            value: 0.5,
            random: true,
            animation: {
              enable: true,
              speed: 1,
              minimumValue: 0.1
            }
          },
          size: {
            value: 3,
            random: true,
            animation: {
              enable: true,
              speed: 2,
              minimumValue: 0.5
            }
          },
          move: {
            enable: true,
            speed: 0.5,
            direction: "none",
            outModes: {
              default: "out"
            }
          },
          links: {
            enable: true,
            distance: 150,
            color: "#00d9ff",
            opacity: 0.2,
            width: 1,
            triangles: {
              enable: false
            }
          }
        },
        interactivity: {
          events: {
            onHover: {
              enable: true,
              mode: "grab"
            },
            onClick: {
              enable: true,
              mode: "push"
            }
          },
          modes: {
            grab: {
              distance: 200,
              links: {
                opacity: 0.5
              }
            },
            push: {
              quantity: 4
            }
          }
        }
      }}
    />
  );
};
```

---

### **5. 对话气泡（DialogBubble.tsx）**

```typescript
// frontend/src/components/JarvisHologram/DialogBubble.tsx

import { motion, AnimatePresence } from 'framer-motion';
import { GlassCard } from '@/components/ui/GlassCard';

interface DialogBubbleProps {
  message: string;
  isListening: boolean;
  isSpeaking: boolean;
}

export const DialogBubble: React.FC<DialogBubbleProps> = ({
  message,
  isListening,
  isSpeaking,
}) => {
  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={message}
        className="absolute top-20 left-1/2 -translate-x-1/2 max-w-2xl w-full px-4"
        initial={{ opacity: 0, scale: 0.8, y: -20 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.8, y: 20 }}
        transition={{ duration: 0.3 }}
      >
        <GlassCard glow={isListening || isSpeaking} glowColor="cyan">
          {/* 说话动画波纹 */}
          {(isListening || isSpeaking) && (
            <div className="absolute -inset-1">
              {[0, 1, 2].map((i) => (
                <motion.div
                  key={i}
                  className="absolute inset-0 border-2 border-cyan-400/50 rounded-xl"
                  animate={{
                    scale: [1, 1.1, 1],
                    opacity: [0.5, 0, 0.5]
                  }}
                  transition={{
                    duration: 2,
                    repeat: Infinity,
                    delay: i * 0.4,
                    ease: "easeInOut"
                  }}
                />
              ))}
            </div>
          )}
          
          {/* 消息内容 */}
          <div className="relative z-10">
            {/* 状态指示器 */}
            <div className="flex items-center gap-2 mb-3">
              <div className={`
                w-3 h-3 rounded-full
                ${isListening ? 'bg-cyan-400 animate-pulse' : ''}
                ${isSpeaking ? 'bg-blue-400 animate-pulse' : ''}
                ${!isListening && !isSpeaking ? 'bg-gray-500' : ''}
              `} />
              <span className="text-xs text-gray-400">
                {isListening && 'Listening...'}
                {isSpeaking && 'Speaking...'}
                {!isListening && !isSpeaking && 'Ready'}
              </span>
            </div>
            
            {/* 消息文本 */}
            <p className="text-xl text-gray-200 mb-4">
              {message}
            </p>
            
            {/* 快捷操作按钮（移到这里） */}
            {/* 见下一个组件 */}
          </div>
        </GlassCard>
      </motion.div>
    </AnimatePresence>
  );
};
```

---

### **6. 语音输入框（VoiceInput.tsx）**

```typescript
// frontend/src/components/JarvisHologram/VoiceInput.tsx

import { useState, useRef } from 'react';
import { motion } from 'framer-motion';
import { GlassCard } from '@/components/ui/GlassCard';
import { useVoiceRecording } from '@/hooks/useVoiceRecording';

interface VoiceInputProps {
  onVoiceInput: (audioBlob: Blob) => void;
  onTextInput: (text: string) => void;
  isListening: boolean;
  disabled?: boolean;
}

export const VoiceInput: React.FC<VoiceInputProps> = ({
  onVoiceInput,
  onTextInput,
  isListening,
  disabled = false,
}) => {
  const [inputText, setInputText] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);
  
  // 语音录制
  const {
    isRecording,
    startRecording,
    stopRecording,
    audioBlob,
  } = useVoiceRecording();
  
  // 处理语音输入
  const handleVoiceClick = async () => {
    if (isRecording) {
      await stopRecording();
      if (audioBlob) {
        onVoiceInput(audioBlob);
      }
    } else {
      await startRecording();
    }
  };
  
  // 处理文本输入
  const handleTextSubmit = () => {
    if (inputText.trim()) {
      onTextInput(inputText.trim());
      setInputText('');
      inputRef.current?.blur();
    }
  };
  
  // 处理键盘事件
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleTextSubmit();
    }
  };
  
  return (
    <motion.div
      className="absolute bottom-10 left-1/2 -translate-x-1/2 w-full max-w-2xl px-4"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 1 }}
    >
      <GlassCard className="flex items-center gap-4" padding="md">
        {/* 文本输入框 */}
        <input
          ref={inputRef}
          type="text"
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={isListening ? "Listening..." : "请输入您的需求或者按住说话..."}
          disabled={disabled || isListening}
          className="flex-1 bg-transparent text-gray-200 outline-none placeholder-gray-500 disabled:opacity-50"
        />
        
        {/* 语音按钮 */}
        <motion.button
          className={`
            w-12 h-12 rounded-full flex items-center justify-center
            ${isRecording
              ? 'bg-red-500/20 border-2 border-red-500'
              : 'bg-cyan-500/20 border-2 border-cyan-500'
            }
            disabled:opacity-50 disabled:cursor-not-allowed
          `}
          whileHover={{ scale: disabled ? 1 : 1.1 }}
          whileTap={{ scale: disabled ? 1 : 0.9 }}
          onClick={handleVoiceClick}
          disabled={disabled}
          animate={isRecording ? {
            boxShadow: [
              '0 0 0 0 rgba(239, 68, 68, 0.7)',
              '0 0 0 20px rgba(239, 68, 68, 0)'
            ]
          } : {}}
          transition={{
            duration: 1.5,
            repeat: isRecording ? Infinity : 0
          }}
        >
          {isRecording ? (
            // 录音中图标（正方形）
            <div className="w-4 h-4 bg-red-500 rounded" />
          ) : (
            // 麦克风图标
            <svg className="w-6 h-6 text-cyan-400" fill="currentColor" viewBox="0 0 20 20">
              <path d="M7 4a3 3 0 016 0v4a3 3 0 11-6 0V4z"/>
              <path d="M5.5 9.643a.75.75 0 00-1.5 0V10c0 3.06 2.29 5.585 5.25 5.954V17.5h-1.5a.75.75 0 000 1.5h4.5a.75.75 0 000-1.5h-1.5v-1.546A6.001 6.001 0 0016 10v-.357a.75.75 0 00-1.5 0V10a4.5 4.5 0 01-9 0v-.357z"/>
            </svg>
          )}
        </motion.button>
        
        {/* 发送按钮 */}
        <motion.button
          className="w-12 h-12 rounded-full bg-cyan-500 flex items-center justify-center disabled:opacity-50 disabled:cursor-not-allowed"
          whileHover={{ scale: disabled ? 1 : 1.1 }}
          whileTap={{ scale: disabled ? 1 : 0.9 }}
          onClick={handleTextSubmit}
          disabled={disabled || !inputText.trim()}
        >
          <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3"/>
          </svg>
        </motion.button>
      </GlassCard>
      
      {/* 快捷键提示 */}
      <div className="mt-2 text-center text-xs text-gray-500">
        按 Enter 发送 · 按住空格键说话 · Ctrl+Shift+L 唤醒贾维斯
      </div>
    </motion.div>
  );
};
```

---

### **7. 快捷操作按钮（QuickActions.tsx）**

```typescript
// frontend/src/components/JarvisHologram/QuickActions.tsx

import { motion } from 'framer-motion';

interface QuickActionsProps {
  onAction: (action: string) => void;
}

const actions = [
  { label: '市场分析', action: '帮我分析最新的市场趋势' },
  { label: '供应商推荐', action: '推荐几个优质的供应商' },
  { label: '产品规划', action: '生成产品路线图' },
  { label: 'SEO优化', action: '优化网站SEO' },
  { label: '数据报告', action: '生成本周数据报告' },
];

export const QuickActions: React.FC<QuickActionsProps> = ({
  onAction,
}) => {
  return (
    <div className="absolute top-72 left-1/2 -translate-x-1/2 w-full max-w-2xl px-4">
      <div className="flex gap-2 justify-center flex-wrap">
        {actions.map((item, index) => (
          <motion.button
            key={item.label}
            className="px-4 py-2 bg-cyan-500/10 border border-cyan-500/30 rounded-lg text-cyan-400 text-sm hover:bg-cyan-500/20 transition-colors"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.1 }}
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={() => onAction(item.action)}
          >
            {item.label}
          </motion.button>
        ))}
      </div>
    </div>
  );
};
```

---

## 🎤 语音系统

### **1. 语音输入（ASR）**

```python
# backend/src/jarvis/voice_input.py

import asyncio
import openai
from typing import AsyncIterator

class VoiceInput:
    """语音输入系统"""
    
    def __init__(self):
        self.client = openai.AsyncOpenAI()
    
    async def transcribe(
        self,
        audio_file: bytes,
        language: str = "zh"
    ) -> dict:
        """
        语音识别
        
        参数：
        - audio_file: 音频文件（bytes）
        - language: 语言代码（zh/en）
        
        返回：
        - text: 识别文本
        - language: 检测到的语言
        - confidence: 置信度
        """
        
        response = await self.client.audio.transcriptions.create(
            model="whisper-1",
            file=("audio.wav", audio_file),
            language=language,
            response_format="verbose_json"
        )
        
        return {
            "text": response.text,
            "language": response.language,
            "confidence": getattr(response, 'confidence', 0.9),
            "segments": getattr(response, 'segments', [])
        }
    
    async def transcribe_stream(
        self,
        audio_stream: AsyncIterator[bytes]
    ) -> AsyncIterator[dict]:
        """
        实时流式语音识别
        
        用于：
        - 实时对话
        - 长时间录音
        """
        
        buffer = b''
        
        async for chunk in audio_stream:
            buffer += chunk
            
            # 每3秒识别一次
            if len(buffer) >= 48000 * 3:  # 48kHz * 3秒
                result = await self.transcribe(buffer)
                yield result
                buffer = b''
```

---

### **2. 语音输出（TTS）**

```python
# backend/src/jarvis/voice_output.py

from azure.cognitiveservices.speech import SpeechSynthesizer, SpeechConfig
import asyncio

class VoiceOutput:
    """语音输出系统"""
    
    def __init__(self):
        self.speech_config = SpeechConfig(
            subscription=os.getenv('AZURE_SPEECH_KEY'),
            region=os.getenv('AZURE_REGION')
        )
    
    async def synthesize(
        self,
        text: str,
        voice: str = "zh-CN-XiaoxiaoNeural",
        style: str = "friendly",
        rate: float = 1.0,
        pitch: float = 0
    ) -> bytes:
        """
        语音合成
        
        参数：
        - text: 要合成的文本
        - voice: 声音ID
        - style: 情感风格（friendly/professional/cheerful）
        - rate: 语速（0.5-2.0）
        - pitch: 音调（-50 到 +50）
        
        返回：
        - audio_data: 音频字节
        """
        
        # 构建SSML
        ssml = f"""
        <speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' 
               xmlns:mstts='https://www.w3.org/2001/mstts' xml:lang='zh-CN'>
            <voice name='{voice}'>
                <mstts:express-as style='{style}'>
                    <prosody rate='{rate}' pitch='{pitch}%'>
                        {text}
                    </prosody>
                </mstts:express-as>
            </voice>
        </speak>
        """
        
        synthesizer = SpeechSynthesizer(speech_config=self.speech_config)
        result = await synthesizer.speak_ssml_async(ssml)
        
        return result.audio_data
```

---

### **3. 口型同步算法**

```typescript
// frontend/src/components/JarvisHologram/lip-sync.ts

export const useLipSync = (
  audioData?: Uint8Array,
  isSpeaking?: boolean
) => {
  const [mouthOpenAmount, setMouthOpenAmount] = useState(0);
  
  useEffect(() => {
    if (!audioData || !isSpeaking) {
      setMouthOpenAmount(0);
      return;
    }
    
    // 分析音频振幅
    const analyzeAudio = () => {
      // 计算RMS（均方根）
      let sum = 0;
      for (let i = 0; i < audioData.length; i++) {
        const normalized = (audioData[i] - 128) / 128;
        sum += normalized * normalized;
      }
      const rms = Math.sqrt(sum / audioData.length);
      
      // 映射到嘴部开合量（0-1）
      const openAmount = Math.min(rms * 3, 1);
      
      setMouthOpenAmount(openAmount);
    };
    
    // 每16ms分析一次（60fps）
    const interval = setInterval(analyzeAudio, 16);
    
    return () => clearInterval(interval);
  }, [audioData, isSpeaking]);
  
  return { mouthOpenAmount };
};
```

---

## 🚀 优化与性能

### **1. 性能优化**

```typescript
// 性能优化清单

// 1. 3D模型优化
- 使用GLTF/GLB格式（二进制）
- 压缩纹理（Basis Universal）
- 减少多边形数量（< 50k faces）
- 使用LOD（距离级别细节）

// 2. 渲染优化
- 启用frustum culling（视锥裁剪）
- 使用instancing（实例化）
- 合并geometry（几何体合并）
- 懒加载模型（Suspense）

// 3. 动画优化
- 使用CSS动画代替JS（更流畅）
- requestAnimationFrame（同步刷新率）
- debounce/throttle事件（防抖/节流）
- 使用transform代替top/left（GPU加速）

// 4. 资源优化
- 图片懒加载
- 代码分割（code splitting）
- 树摇优化（tree shaking）
- CDN加速
```

---

### **2. 性能监控**

```typescript
// 性能监控

import { useFrame } from '@react-three/fiber';

const PerformanceMonitor = () => {
  useFrame((state) => {
    // FPS
    const fps = 1 / state.clock.getDelta();
    
    // 渲染时间
    const renderTime = state.gl.info.render.frame;
    
    // 内存使用
    const memory = (performance as any).memory;
    
    // 如果FPS低于30，降低质量
    if (fps < 30) {
      // 降低分辨率
      state.gl.setPixelRatio(Math.min(window.devicePixelRatio * 0.5, 1));
      
      // 禁用一些效果
      // ...
    }
  });
  
  return null;
};
```

---

## 📋 开发清单

### **Week 7 Day 3-4: 贾维斯3D形象**

- [ ] **Day 3 上午**: 搭建Three.js环境
  - [ ] 安装依赖（three, @react-three/fiber, @react-three/drei）
  - [ ] 配置Canvas基础场景
  - [ ] 设置灯光系统
  - [ ] 测试渲染性能

- [ ] **Day 3 下午**: 3D模型集成
  - [ ] 导入3D头像模型（.glb文件）
  - [ ] 配置发光材质
  - [ ] 实现自动旋转
  - [ ] 添加轨道控制器

- [ ] **Day 4 上午**: 动画系统
  - [ ] 待机动画（呼吸）
  - [ ] 监听动画（倾听）
  - [ ] 说话动画（口型同步）
  - [ ] 思考动画（旋转加速）

- [ ] **Day 4 下午**: 特效集成
  - [ ] 全息圆环
  - [ ] 粒子背景
  - [ ] 扫描线效果
  - [ ] 发光脉冲

---

### **Week 9: 贾维斯交互系统**

- [ ] **Day 1-2: 语音输入**
  - [ ] Whisper ASR集成
  - [ ] 唤醒词检测（"嘿鎏灏"）
  - [ ] 实时录音
  - [ ] 音频预处理

- [ ] **Day 3-4: 语音输出**
  - [ ] Azure TTS集成
  - [ ] 多种声音选择
  - [ ] 情感风格
  - [ ] 音频播放

- [ ] **Day 5: 多模态激活**
  - [ ] 语音激活
  - [ ] 热键激活（Ctrl+Shift+L）
  - [ ] 系统托盘激活
  - [ ] 鼠标点击激活

- [ ] **Day 6-7: UI完善**
  - [ ] 对话气泡
  - [ ] 语音输入框
  - [ ] 快捷操作按钮
  - [ ] 实时字幕
  - [ ] 音频可视化

---

## 🎯 测试清单

### **功能测试**

- [ ] 3D模型正常加载
- [ ] 动画流畅运行（60fps）
- [ ] 语音识别准确（>85%）
- [ ] 语音合成自然
- [ ] 口型同步准确
- [ ] 快捷键响应正常
- [ ] 多模态激活正常

### **性能测试**

- [ ] CPU使用率 <30%
- [ ] 内存使用 <500MB
- [ ] GPU使用率 <50%
- [ ] 帧率 ≥60fps
- [ ] 加载时间 <3秒

### **兼容性测试**

- [ ] Chrome/Edge（推荐）
- [ ] Firefox
- [ ] Safari
- [ ] Windows 10/11
- [ ] macOS

---

## 🎉 预期效果

完成后，贾维斯将是：

1. ✅ **视觉震撼** - 3D全息投影，科技感十足
2. ✅ **交互自然** - 语音/文字/手势多模态
3. ✅ **性能流畅** - 60fps丝滑运行
4. ✅ **功能完整** - 语音识别/合成/口型同步
5. ✅ **易于扩展** - 模块化设计，便于添加功能

**这将是鎏灏AI-OS的核心竞争力！** 🚀

---

**文档结束**
