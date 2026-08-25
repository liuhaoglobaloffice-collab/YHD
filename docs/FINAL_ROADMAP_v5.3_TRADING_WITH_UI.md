# 🚀 鎏灏 AI-OS Y1.0 路线图 v5.3 Final（外贸专用版）
## CEO-First Enterprise AI Operating System for Trading Companies

**版本**: v5.3 Final - Trading with Cyberpunk UI  
**创建日期**: 2026-08-24  
**业务场景**: 外贸出口商（中国产品卖到国外）  
**目标周期**: 22周  
**预计完成**: 2026-12-15

---

## 🎯 版本亮点

### **v5.3 核心特色**
```yaml
业务定位: 外贸出口商AI操作系统
UI风格: 赛博朋克 + 未来科技风 ⭐⭐⭐
核心价值:
  ✅ 海外客户自动开发（LinkedIn/邮件/WhatsApp）
  ✅ 中国供应商智能分析（1688/企查查/微信）
  ✅ AI实时同传（99+种语言 → 粤语/普通话）
  ✅ 贾维斯3D全息形象（核心交互亮点）
  ✅ 智能分析报告（客户/供应商/业务）
  ✅ 每天节省6小时工作时间
  ✅ 24个月150% ROI
```

---

## 📊 时间线总览

| Phase | Weeks | 完成日期 | 核心功能 | 状态 |
|-------|-------|---------|---------|------|
| **Phase 1** | Week 1-6 | 已完成 | 基础架构 + AI Brain | ✅ 100% |
| **Phase 2** | Week 7-9 | 进行中 | 未来风UI + 贾维斯 | ⏳ 12% |
| **Phase 3** | Week 10-14 | 待开发 | AI专家 + 本地LLM | ⏳ 0% |
| **Phase 4** | Week 15-20 | 待开发 | 桌面应用 + 部署 | ⏳ 0% |
| **Phase 5** | Week 21-22 | 待开发 | 外贸业务插件 | ⏳ 0% |

**总进度**: 12% (Week 3 Day 3 / 22周)

---

## 📅 完整路线图（22周详解）

---

### **Week 1: 项目初始化与架构设计** ✅ 已完成
**状态**: 100% 完成  
**代码量**: 1,247行

#### Day 1-2: 项目脚手架
- ✅ FastAPI后端框架
- ✅ PostgreSQL + pgvector数据库
- ✅ React + TypeScript前端
- ✅ Docker开发环境

#### Day 3-4: 核心架构
- ✅ 模块化设计
- ✅ 依赖注入系统
- ✅ 配置管理
- ✅ 日志系统

#### Day 5-7: 开发工具链
- ✅ pytest测试框架
- ✅ pre-commit hooks
- ✅ CI/CD pipeline (GitHub Actions)
- ✅ API文档 (OpenAPI)

**交付物**:
- `src/core/config.py` - 配置管理
- `src/core/database.py` - 数据库连接池
- `src/core/logger.py` - 日志系统
- `tests/conftest.py` - 测试fixtures

---

### **Week 2: 身份权限系统** ✅ 已完成
**状态**: 100% 完成  
**代码量**: 3,192行

#### Day 1-3: 用户认证
- ✅ JWT认证
- ✅ OAuth2集成 (Google/Microsoft)
- ✅ 密码加密 (bcrypt)
- ✅ 登录/注册API

#### Day 4-5: 权限系统
- ✅ RBAC角色权限
- ✅ 权限装饰器
- ✅ API权限验证

#### Day 6-7: 审计日志
- ✅ 操作日志记录
- ✅ 敏感操作追踪
- ✅ 登录历史

**交付物**:
- `src/auth/` - 完整认证模块
- `src/permissions/` - 权限系统
- `tests/test_auth.py` - 认证测试 (92%覆盖率)

---

### **Week 3: 插件系统与工作流引擎** ✅ 已完成
**状态**: 插件100%, 工作流80%  
**代码量**: 5,669行

#### Day 1-3: 插件系统
- ✅ 插件管理器 (安装/卸载/启用)
- ✅ 插件加载器 (动态导入)
- ✅ 插件注册表
- ✅ 插件配置管理
- ✅ CLI命令 (`liuhao plugin`)

#### Day 4-7: 工作流引擎
- ✅ 工作流定义 (YAML)
- ✅ 任务调度 (APScheduler)
- ⏳ 流程编排 (Celery) - 80%
- ✅ 错误处理与重试

**交付物**:
- `src/core/plugins/` - 插件系统
- `src/workflows/` - 工作流引擎
- `tests/test_plugins.py` - 插件测试

---

### **Week 4: 知识库系统** ✅ 已完成
**状态**: 100% 完成  
**代码量**: 3,710行

#### Day 1-3: 文档管理
- ✅ 文件上传/下载
- ✅ 文档解析 (PDF/Word/Excel)
- ✅ 版本控制
- ✅ 标签系统

#### Day 4-5: 向量搜索
- ✅ pgvector集成
- ✅ 文档embedding (OpenAI/本地)
- ✅ 语义搜索

#### Day 6-7: RAG系统
- ✅ 检索增强生成
- ✅ 上下文管理
- ✅ 引用追踪

**交付物**:
- `src/knowledge/` - 知识库模块
- `src/vector/` - 向量搜索
- `tests/test_knowledge.py` - 知识库测试

---

### **Week 5: AI Brain - LLM集成层** ✅ 已完成
**状态**: 100% 完成  
**代码量**: 4,939行

#### Day 1-2: LLM Provider抽象
- ✅ 统一LLM接口
- ✅ 6大提供商支持:
  - OpenAI (GPT-4/3.5)
  - Anthropic (Claude)
  - Google (Gemini)
  - Azure OpenAI
  - Ollama (本地)
  - Zhipu (智谱)

#### Day 3-4: 智能路由
- ✅ 成本优化路由
- ✅ 负载均衡
- ✅ 故障转移

#### Day 5-7: 高级功能
- ✅ 流式响应
- ✅ Token计数
- ✅ 缓存系统
- ✅ 速率限制

**交付物**:
- `src/ai/` - AI Brain核心
- `src/ai/providers/` - 提供商实现
- `tests/test_ai.py` - AI测试

---

### **Week 6: 供应商智能系统** ✅ 已完成
**状态**: 100% 完成  
**代码量**: 4,918行

#### Day 1-3: 供应商管理
- ✅ 供应商CRUD
- ✅ 证书管理 (ISO/FDA/CE)
- ✅ 风险评分
- ✅ 供应商对比

#### Day 4-5: AI分析
- ✅ 自动评分算法
- ✅ 风险预测
- ✅ 趋势分析

#### Day 6-7: 集成接口
- ✅ 邮件通知
- ✅ 数据导入/导出
- ✅ API集成

**交付物**:
- `src/suppliers/` - 供应商系统
- `src/suppliers/ai_analysis.py` - AI分析
- `tests/test_suppliers.py` - 供应商测试

---

### **Week 7: CEO Dashboard + 赛博朋克UI系统** ⏳ 待开发 ⭐⭐⭐
**预计代码量**: ~5,000行（前端）+ 800行（后端）

> **核心亮点**: 未来科技风UI + 贾维斯3D全息形象

#### **Day 1-2: UI设计系统搭建**

**1. 设计Token定义**
```typescript
// src/styles/design-tokens.ts

export const designTokens = {
  // 颜色系统
  colors: {
    primary: {
      bg: '#0a1628',           // 深蓝黑背景
      blue: '#00d9ff',         // 霓虹蓝
      cyan: '#00ffff',         // 青色
    },
    status: {
      success: '#00ff88',      // 绿色（正常/增长）
      warning: '#ffbb00',      // 黄色（中等风险）
      danger: '#ff4444',       // 红色（高风险）
      info: '#0099ff',         // 蓝色（信息）
    },
    glass: {
      bg: 'rgba(255, 255, 255, 0.05)',
      border: 'rgba(0, 217, 255, 0.3)',
      hover: 'rgba(255, 255, 255, 0.08)',
    }
  },
  
  // 发光效果
  glows: {
    blue: '0 0 20px rgba(0, 217, 255, 0.6)',
    cyan: '0 0 15px rgba(0, 255, 255, 0.8)',
    purple: '0 0 25px rgba(153, 0, 255, 0.5)',
  },
  
  // 渐变
  gradients: {
    bluePurple: 'linear-gradient(135deg, #0066ff 0%, #9900ff 100%)',
    cyanBlue: 'linear-gradient(135deg, #00ffff 0%, #00d9ff 100%)',
  },
  
  // 字体
  typography: {
    fontFamily: {
      primary: "'Inter', sans-serif",
      mono: "'Fira Code', monospace",
      display: "'Orbitron', sans-serif",  // 科技感字体
    },
    fontSize: {
      xs: '0.75rem',
      sm: '0.875rem',
      base: '1rem',
      lg: '1.125rem',
      xl: '1.25rem',
      '2xl': '1.5rem',
      '3xl': '1.875rem',
      '4xl': '2.25rem',
    }
  },
  
  // 间距
  spacing: {
    xs: '0.25rem',
    sm: '0.5rem',
    md: '1rem',
    lg: '1.5rem',
    xl: '2rem',
    '2xl': '3rem',
  },
  
  // 动画
  animations: {
    duration: {
      fast: '150ms',
      normal: '300ms',
      slow: '500ms',
    },
    easing: {
      easeOut: 'cubic-bezier(0.16, 1, 0.3, 1)',
      easeIn: 'cubic-bezier(0.7, 0, 0.84, 0)',
    }
  }
};
```

**2. 玻璃态组件库**
```typescript
// src/components/ui/GlassCard.tsx
import { motion } from 'framer-motion';

interface GlassCardProps {
  children: React.ReactNode;
  className?: string;
  glow?: boolean;
  animated?: boolean;
}

export const GlassCard: React.FC<GlassCardProps> = ({
  children,
  className = '',
  glow = false,
  animated = true
}) => {
  return (
    <motion.div
      className={`
        relative
        bg-white/5
        backdrop-blur-xl
        border border-cyan-500/30
        rounded-xl
        p-6
        transition-all duration-300
        hover:bg-white/8
        hover:border-cyan-500/60
        ${glow ? 'shadow-glow-cyan' : ''}
        ${className}
      `}
      initial={animated ? { opacity: 0, y: 20 } : {}}
      animate={animated ? { opacity: 1, y: 0 } : {}}
      whileHover={animated ? { scale: 1.02 } : {}}
    >
      {/* 扫描线效果 */}
      <div className="absolute inset-0 scan-lines opacity-10 pointer-events-none" />
      
      {/* 发光边框 */}
      {glow && (
        <div className="absolute -inset-0.5 bg-gradient-to-r from-cyan-500 to-blue-500 rounded-xl opacity-20 blur-sm" />
      )}
      
      {/* 内容 */}
      <div className="relative z-10">
        {children}
      </div>
    </motion.div>
  );
};

// src/components/ui/GlowButton.tsx
export const GlowButton: React.FC<ButtonProps> = ({
  children,
  variant = 'primary',
  ...props
}) => {
  return (
    <motion.button
      className={`
        relative
        px-6 py-3
        rounded-lg
        font-semibold
        transition-all
        ${variant === 'primary' ? 'bg-cyan-500/20 text-cyan-400 border-2 border-cyan-500' : ''}
        ${variant === 'danger' ? 'bg-red-500/20 text-red-400 border-2 border-red-500' : ''}
      `}
      whileHover={{ scale: 1.05 }}
      whileTap={{ scale: 0.95 }}
      {...props}
    >
      {/* 发光效果 */}
      <div className="absolute inset-0 bg-cyan-500/20 rounded-lg blur-lg opacity-0 hover:opacity-100 transition-opacity" />
      
      {/* 内容 */}
      <span className="relative z-10">{children}</span>
    </motion.button>
  );
};

// src/components/ui/CountUpNumber.tsx
import { useEffect, useState } from 'react';

export const CountUpNumber: React.FC<{ value: number; duration?: number }> = ({
  value,
  duration = 1000
}) => {
  const [displayValue, setDisplayValue] = useState(0);
  
  useEffect(() => {
    let start = 0;
    const increment = value / (duration / 16);
    
    const timer = setInterval(() => {
      start += increment;
      if (start >= value) {
        setDisplayValue(value);
        clearInterval(timer);
      } else {
        setDisplayValue(Math.floor(start));
      }
    }, 16);
    
    return () => clearInterval(timer);
  }, [value, duration]);
  
  return (
    <span className="font-mono text-cyan-400 tabular-nums">
      {displayValue.toLocaleString()}
    </span>
  );
};
```

**3. CSS效果库**
```css
/* src/styles/glassmorphism.css */

.glass-card {
  background: rgba(255, 255, 255, 0.05);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(0, 217, 255, 0.3);
  border-radius: 12px;
  box-shadow: 
    0 8px 32px rgba(0, 0, 0, 0.3),
    inset 0 1px 0 rgba(255, 255, 255, 0.1);
}

.glass-card:hover {
  background: rgba(255, 255, 255, 0.08);
  border-color: rgba(0, 217, 255, 0.6);
  box-shadow: 
    0 8px 32px rgba(0, 217, 255, 0.2),
    inset 0 1px 0 rgba(255, 255, 255, 0.2);
}

/* 扫描线效果 */
.scan-lines {
  background: repeating-linear-gradient(
    0deg,
    transparent,
    transparent 2px,
    rgba(0, 217, 255, 0.03) 2px,
    rgba(0, 217, 255, 0.03) 4px
  );
  animation: scan-lines-move 8s linear infinite;
}

@keyframes scan-lines-move {
  0% { transform: translateY(0); }
  100% { transform: translateY(100%); }
}

/* 发光脉冲 */
.glow-pulse {
  animation: glow-pulse 2s ease-in-out infinite;
}

@keyframes glow-pulse {
  0%, 100% {
    box-shadow: 0 0 10px rgba(0, 217, 255, 0.5);
  }
  50% {
    box-shadow: 0 0 20px rgba(0, 217, 255, 0.8);
  }
}

/* 全息效果 */
.hologram {
  position: relative;
  background: radial-gradient(
    ellipse at center,
    rgba(0, 217, 255, 0.2) 0%,
    transparent 70%
  );
  animation: hologram-flicker 3s ease-in-out infinite;
}

@keyframes hologram-flicker {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.95; }
}
```

**交付Day 1-2**:
- ✅ `src/styles/design-tokens.ts` - 设计Token
- ✅ `src/styles/glassmorphism.css` - 玻璃态效果
- ✅ `src/components/ui/` - 20+基础组件
- ✅ Storybook组件文档

---

#### **Day 3-4: 贾维斯3D全息形象** ⭐⭐⭐

> **核心亮点**: 整个系统的视觉焦点和交互中心

**1. Three.js 3D头像**
```typescript
// src/components/JarvisHologram/Model.tsx

import { useGLTF, useAnimations } from '@react-three/drei';
import { useFrame } from '@react-three/fiber';
import { useRef } from 'react';

export const JarvisModel = () => {
  const groupRef = useRef();
  const { scene, animations } = useGLTF('/models/jarvis-head.glb');
  const { actions } = useAnimations(animations, groupRef);
  
  // 自动旋转
  useFrame((state) => {
    if (groupRef.current) {
      groupRef.current.rotation.y += 0.002;
      // 呼吸动画
      groupRef.current.scale.setScalar(1 + Math.sin(state.clock.elapsedTime) * 0.02);
    }
  });
  
  // 发光材质
  useEffect(() => {
    scene.traverse((child) => {
      if (child.isMesh) {
        child.material.emissive = new THREE.Color(0x00d9ff);
        child.material.emissiveIntensity = 0.5;
        child.material.transparent = true;
        child.material.opacity = 0.9;
      }
    });
  }, [scene]);
  
  return (
    <group ref={groupRef}>
      <primitive object={scene} scale={2} />
    </group>
  );
};
```

**2. 全息投影圆环**
```typescript
// src/components/JarvisHologram/HologramRings.tsx

export const HologramRings = () => {
  return (
    <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
      {[0, 1, 2].map((index) => (
        <motion.div
          key={index}
          className="absolute w-full h-full border-2 border-cyan-500/20 rounded-full"
          initial={{ scale: 0.8, opacity: 0 }}
          animate={{
            scale: [0.8, 1.2, 0.8],
            opacity: [0, 0.5, 0],
          }}
          transition={{
            duration: 4,
            repeat: Infinity,
            delay: index * 1.3,
            ease: "easeInOut"
          }}
        />
      ))}
      
      {/* 内圈发光 */}
      <div className="absolute w-96 h-96 border-4 border-cyan-400/40 rounded-full animate-spin-slow shadow-glow-cyan" />
    </div>
  );
};
```

**3. 粒子系统**
```typescript
// src/components/JarvisHologram/Particles.tsx

import Particles from 'react-tsparticles';
import { loadFull } from 'tsparticles';

export const ParticleBackground = () => {
  const particlesInit = useCallback(async (engine) => {
    await loadFull(engine);
  }, []);
  
  return (
    <Particles
      id="jarvis-particles"
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
            value: ["#00d9ff", "#00ffff", "#0099ff"]
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
            outModes: "out"
          },
          links: {
            enable: true,
            distance: 150,
            color: "#00d9ff",
            opacity: 0.2,
            width: 1
          }
        },
        interactivity: {
          events: {
            onHover: {
              enable: true,
              mode: "grab"
            }
          },
          modes: {
            grab: {
              distance: 200,
              links: {
                opacity: 0.5
              }
            }
          }
        }
      }}
    />
  );
};
```

**4. 完整全息形象组件**
```typescript
// src/components/JarvisHologram/index.tsx

import { Canvas } from '@react-three/fiber';
import { OrbitControls, PerspectiveCamera } from '@react-three/drei';
import { motion, AnimatePresence } from 'framer-motion';

export const JarvisHologram = () => {
  const [isListening, setIsListening] = useState(false);
  const [message, setMessage] = useState("老板，我已准备就绪！今天可以帮您做点什么？");
  
  return (
    <div className="relative w-full h-[600px] overflow-hidden">
      {/* 背景粒子 */}
      <ParticleBackground />
      
      {/* 全息圆环 */}
      <HologramRings />
      
      {/* 3D模型 */}
      <Canvas className="absolute inset-0">
        <PerspectiveCamera makeDefault position={[0, 0, 5]} fov={45} />
        <ambientLight intensity={0.5} />
        <pointLight position={[10, 10, 10]} intensity={1} color="#00d9ff" />
        <pointLight position={[-10, -10, -10]} intensity={0.5} color="#9900ff" />
        
        <JarvisModel />
        
        <OrbitControls
          enableZoom={false}
          enablePan={false}
          minPolarAngle={Math.PI / 3}
          maxPolarAngle={Math.PI / 1.5}
        />
      </Canvas>
      
      {/* 标题 */}
      <motion.div
        className="absolute bottom-32 left-1/2 -translate-x-1/2 text-center"
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
      </motion.div>
      
      {/* 对话气泡 */}
      <AnimatePresence mode="wait">
        <motion.div
          key={message}
          className="absolute top-20 left-1/2 -translate-x-1/2 max-w-2xl"
          initial={{ opacity: 0, scale: 0.8, y: -20 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.8, y: 20 }}
          transition={{ duration: 0.3 }}
        >
          <GlassCard glow className="text-center relative">
            {/* 说话动画波纹 */}
            {isListening && (
              <div className="absolute -inset-1">
                <motion.div
                  className="w-full h-full border-2 border-cyan-400/50 rounded-xl"
                  animate={{
                    scale: [1, 1.1, 1],
                    opacity: [0.5, 0, 0.5]
                  }}
                  transition={{
                    duration: 2,
                    repeat: Infinity,
                    ease: "easeInOut"
                  }}
                />
              </div>
            )}
            
            <p className="text-xl text-gray-200 mb-2">
              {message}
            </p>
            
            {/* 快捷操作 */}
            <div className="flex gap-2 justify-center mt-4 flex-wrap">
              {['市场分析', '供应商推荐', '产品规划', 'SEO优化', '数据报告'].map((action) => (
                <motion.button
                  key={action}
                  className="px-4 py-2 bg-cyan-500/10 border border-cyan-500/30 rounded-lg text-cyan-400 text-sm hover:bg-cyan-500/20 transition-colors"
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                >
                  {action}
                </motion.button>
              ))}
            </div>
          </GlassCard>
        </motion.div>
      </AnimatePresence>
      
      {/* 语音输入框 */}
      <motion.div
        className="absolute bottom-10 left-1/2 -translate-x-1/2 w-full max-w-2xl px-4"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 1 }}
      >
        <GlassCard className="flex items-center gap-4">
          <input
            type="text"
            placeholder="请输入您的需求或者按住说话..."
            className="flex-1 bg-transparent text-gray-200 outline-none placeholder-gray-500"
          />
          
          {/* 语音按钮 */}
          <motion.button
            className="w-12 h-12 rounded-full bg-cyan-500/20 border-2 border-cyan-500 flex items-center justify-center"
            whileHover={{ scale: 1.1 }}
            whileTap={{ scale: 0.9 }}
            animate={isListening ? {
              boxShadow: ['0 0 0 0 rgba(0, 217, 255, 0.7)', '0 0 0 20px rgba(0, 217, 255, 0)']
            } : {}}
            transition={{ duration: 1, repeat: isListening ? Infinity : 0 }}
          >
            <svg className="w-6 h-6 text-cyan-400" fill="currentColor" viewBox="0 0 20 20">
              <path d="M7 4a3 3 0 016 0v4a3 3 0 11-6 0V4z"/>
              <path d="M5.5 9.643a.75.75 0 00-1.5 0V10c0 3.06 2.29 5.585 5.25 5.954V17.5h-1.5a.75.75 0 000 1.5h4.5a.75.75 0 000-1.5h-1.5v-1.546A6.001 6.001 0 0016 10v-.357a.75.75 0 00-1.5 0V10a4.5 4.5 0 01-9 0v-.357z"/>
            </svg>
          </motion.button>
          
          {/* 发送按钮 */}
          <motion.button
            className="w-12 h-12 rounded-full bg-cyan-500 flex items-center justify-center"
            whileHover={{ scale: 1.1 }}
            whileTap={{ scale: 0.9 }}
          >
            <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3"/>
            </svg>
          </motion.button>
        </GlassCard>
      </motion.div>
    </div>
  );
};
```

**交付Day 3-4**:
- ✅ `src/components/JarvisHologram/` - 完整组件
- ✅ `public/models/jarvis-head.glb` - 3D模型
- ✅ 粒子系统
- ✅ 全息圆环动画
- ✅ 对话气泡
- ✅ 语音交互UI

---

#### **Day 5-6: Dashboard核心模块**

**1. 布局框架**
```typescript
// src/pages/Dashboard/layout.tsx

export const DashboardLayout = () => {
  return (
    <div className="min-h-screen bg-[#0a1628] text-gray-200">
      {/* 粒子背景 */}
      <div className="fixed inset-0 -z-10">
        <ParticleBackground />
      </div>
      
      {/* Header */}
      <Header />
      
      {/* 主体 */}
      <div className="flex">
        {/* Sidebar */}
        <Sidebar />
        
        {/* Main Content */}
        <main className="flex-1 p-6">
          <Outlet />
        </main>
        
        {/* 右侧状态面板 */}
        <SystemHealthPanel />
      </div>
    </div>
  );
};

// Header组件
const Header = () => {
  return (
    <header className="h-16 border-b border-cyan-500/20 backdrop-blur-xl">
      <div className="h-full px-6 flex items-center justify-between">
        {/* Logo */}
        <div className="flex items-center gap-4">
          <div className="w-10 h-10 rounded-full bg-cyan-500/20 border-2 border-cyan-500 flex items-center justify-center">
            <span className="text-cyan-400 font-bold">鎏</span>
          </div>
          <div>
            <h1 className="text-xl font-bold text-cyan-400 font-display">
              鎏灏 AI
            </h1>
            <p className="text-xs text-gray-400">LIU-HAO AI - Control Partner</p>
          </div>
          
          <div className="ml-8 px-4 py-1 bg-cyan-500/10 border border-cyan-500/30 rounded-lg">
            <span className="text-cyan-400 font-semibold">CEO COMMAND CENTER</span>
          </div>
          
          <div className="flex gap-2 text-xs">
            <span className="px-2 py-1 bg-blue-500/20 border border-blue-500/30 rounded text-blue-400">
              老板驾驶舱
            </span>
            <span className="px-2 py-1 bg-purple-500/20 border border-purple-500/30 rounded text-purple-400">
              Intelligent
            </span>
            <span className="px-2 py-1 bg-green-500/20 border border-green-500/30 rounded text-green-400">
              Autonomous
            </span>
            <span className="px-2 py-1 bg-orange-500/20 border border-orange-500/30 rounded text-orange-400">
              Global
            </span>
          </div>
        </div>
        
        {/* 右侧 */}
        <div className="flex items-center gap-6">
          {/* 时间和温度 */}
          <div className="text-sm">
            <span className="text-gray-400">2025-08-30 16:36 (PST)</span>
            <span className="ml-4 text-cyan-400">🌡️ 26°C 深圳</span>
          </div>
          
          {/* 通知 */}
          <button className="relative">
            <svg className="w-6 h-6 text-gray-400 hover:text-cyan-400 transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"/>
            </svg>
            <span className="absolute -top-1 -right-1 w-5 h-5 bg-red-500 rounded-full text-xs flex items-center justify-center">
              3
            </span>
          </button>
          
          {/* CEO头像 */}
          <div className="flex items-center gap-2">
            <div className="w-10 h-10 rounded-full bg-gradient-to-br from-cyan-400 to-blue-500 p-0.5">
              <div className="w-full h-full rounded-full bg-[#0a1628] flex items-center justify-center">
                <span className="text-cyan-400 font-bold">外</span>
              </div>
            </div>
            <div className="text-right">
              <div className="text-sm font-semibold">外贸CEO</div>
              <div className="text-xs text-gray-400">CEO</div>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
};
```

**2. 侧边栏**
```typescript
// src/components/Sidebar.tsx

const menuItems = [
  { icon: '🏠', label: '首页', path: '/dashboard', enLabel: 'Dashboard' },
  { icon: '🤖', label: 'Jarvis智能助手', path: '/jarvis', enLabel: 'Jarvis' },
  { icon: '📊', label: 'CEO简报', path: '/brief', enLabel: 'CEO Brief' },
  { icon: '🎯', label: '任务与目标', path: '/tasks', enLabel: 'Mission & Tasks' },
  { icon: '👥', label: '客户与销售', path: '/sales', enLabel: 'Sales & Pipeline' },
  { icon: '📈', label: '业务数据中心', path: '/analytics', enLabel: 'Business Reality', active: true },
  { icon: '🔍', label: '市场研究', path: '/market', enLabel: 'Market Research' },
  { icon: '🧠', label: 'AI决策中枢', path: '/ai-agents', enLabel: 'AI Decision' },
  { icon: '✅', label: '审批中心', path: '/approval', enLabel: 'Approval Gateway', badge: 42 },
  { icon: '📚', label: '知识中心', path: '/knowledge', enLabel: 'Knowledge Center' },
  { icon: '⚙️', label: '系统状态', path: '/system', enLabel: 'System Health' },
  { icon: '⚙️', label: '设置', path: '/settings', enLabel: 'Settings' },
];

export const Sidebar = () => {
  const location = useLocation();
  
  return (
    <aside className="w-64 border-r border-cyan-500/20 backdrop-blur-xl">
      {/* 安全运行模式 */}
      <div className="p-4 border-b border-cyan-500/20">
        <div className="flex items-center gap-2 text-green-400">
          <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M2.166 4.999A11.954 11.954 0 0010 1.944 11.954 11.954 0 0017.834 5c.11.65.166 1.32.166 2.001 0 5.225-3.34 9.67-8 11.317C5.34 16.67 2 12.225 2 7c0-.682.057-1.35.166-2.001zm11.541 3.708a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd"/>
          </svg>
          <span className="text-sm font-semibold">安全运行模式</span>
        </div>
        <div className="text-xs text-gray-400 mt-1">SAFE MODE</div>
        
        <div className="mt-3 space-y-1">
          <div className="flex items-center justify-between text-xs">
            <span className="text-gray-400">Execution Lock</span>
            <span className="text-green-400">●</span>
          </div>
          <div className="flex items-center justify-between text-xs">
            <span className="text-gray-400">Browser Guard</span>
            <span className="text-green-400">●</span>
          </div>
        </div>
      </div>
      
      {/* 菜单 */}
      <nav className="p-2">
        {menuItems.map((item) => (
          <Link
            key={item.path}
            to={item.path}
            className={`
              relative
              flex items-center gap-3
              px-4 py-3
              rounded-lg
              mb-1
              transition-all
              group
              ${location.pathname === item.path
                ? 'bg-cyan-500/20 border border-cyan-500/50 text-cyan-400'
                : 'text-gray-400 hover:bg-white/5 hover:text-gray-200'
              }
            `}
          >
            {/* 发光效果 */}
            {location.pathname === item.path && (
              <motion.div
                className="absolute inset-0 bg-cyan-500/10 rounded-lg blur-md"
                layoutId="sidebar-active"
              />
            )}
            
            <span className="text-xl relative z-10">{item.icon}</span>
            <div className="flex-1 relative z-10">
              <div className="text-sm font-medium">{item.label}</div>
              <div className="text-xs opacity-60">{item.enLabel}</div>
            </div>
            
            {/* Badge */}
            {item.badge && (
              <span className="px-2 py-0.5 bg-red-500 rounded-full text-xs font-bold">
                {item.badge}
              </span>
            )}
          </Link>
        ))}
      </nav>
    </aside>
  );
};
```

**3. 今日CEO简报**
```typescript
// src/components/CEOBrief.tsx

const briefItems = [
  {
    id: 1,
    title: '泰国食品包装价格持续走高',
    status: 'danger',
    label: '高风险',
    description: '注意对影响成本估算',
  },
  {
    id: 2,
    title: '客户洽口建立 20 家',
    status: 'success',
    label: '进行中',
    description: '其中 5 家高意向开始报价',
  },
  {
    id: 3,
    title: '供应商资料特卖清',
    status: 'warning',
    label: '中度风险',
    description: '建议对接流程优化避免延迟',
  },
  {
    id: 4,
    title: '续订站与SEO策划已就绪',
    status: 'success',
    label: '低风险',
    description: '可开始启动营销推广活动',
  },
];

export const CEOBrief = () => {
  return (
    <GlassCard className="mb-6">
      <div className="flex items-center gap-3 mb-4">
        <div className="w-10 h-10 rounded-lg bg-cyan-500/20 border border-cyan-500 flex items-center justify-center">
          <span className="text-2xl">🤖</span>
        </div>
        <div className="flex-1">
          <h3 className="text-lg font-semibold text-gray-200">今日CEO简报</h3>
          <p className="text-sm text-gray-400">Today's Brief</p>
        </div>
      </div>
      
      <div className="space-y-3">
        {briefItems.map((item, index) => (
          <motion.div
            key={item.id}
            className={`
              flex items-start gap-3
              p-3 rounded-lg
              border
              ${item.status === 'danger' ? 'bg-red-500/10 border-red-500/30' : ''}
              ${item.status === 'warning' ? 'bg-yellow-500/10 border-yellow-500/30' : ''}
              ${item.status === 'success' ? 'bg-green-500/10 border-green-500/30' : ''}
              hover:scale-[1.02] transition-transform
            `}
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: index * 0.1 }}
          >
            <div className="flex-shrink-0 w-6 h-6 rounded-full bg-white/10 flex items-center justify-center text-sm font-bold">
              {item.id}
            </div>
            
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-1">
                <span className="text-sm font-medium text-gray-200">{item.title}</span>
                <span className={`
                  px-2 py-0.5 rounded text-xs font-semibold
                  ${item.status === 'danger' ? 'bg-red-500/20 text-red-400' : ''}
                  ${item.status === 'warning' ? 'bg-yellow-500/20 text-yellow-400' : ''}
                  ${item.status === 'success' ? 'bg-green-500/20 text-green-400' : ''}
                `}>
                  {item.label}
                </span>
              </div>
              <p className="text-xs text-gray-400">{item.description}</p>
            </div>
          </motion.div>
        ))}
      </div>
      
      <motion.button
        className="w-full mt-4 py-2 bg-cyan-500/10 border border-cyan-500/30 rounded-lg text-cyan-400 text-sm hover:bg-cyan-500/20 transition-colors flex items-center justify-center gap-2"
        whileHover={{ scale: 1.02 }}
        whileTap={{ scale: 0.98 }}
      >
        <span>查看完整 AI 建议</span>
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7"/>
        </svg>
      </motion.button>
    </GlassCard>
  );
};
```

**4. 销售漏斗**
```typescript
// src/components/SalesPipeline.tsx

const stages = [
  { name: 'Prospect', count: 20, change: 8, color: 'blue' },
  { name: 'Qualified', count: 5, change: 2, color: 'cyan' },
  { name: '待开发', count: 3, change: 1, color: 'purple' },
  { name: '已联系', count: 0, change: 0, color: 'indigo' },
  { name: '回复', count: 0, change: 0, color: 'violet' },
  { name: '需求提认', count: 0, change: 0, color: 'fuchsia' },
  { name: '报价', count: 0, change: 0, color: 'pink' },
  { name: '谈判', count: 0, change: 0, color: 'rose' },
  { name: '成交', count: 0, change: 0, color: 'green' },
];

export const SalesPipeline = () => {
  return (
    <GlassCard className="mb-6">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-lg font-semibold text-gray-200">销售 Pipeline</h3>
          <p className="text-sm text-gray-400">5 个机会进行中</p>
        </div>
        <button className="text-cyan-400 text-sm hover:underline flex items-center gap-1">
          查看详情
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7"/>
          </svg>
        </button>
      </div>
      
      <div className="flex gap-2 overflow-x-auto pb-2">
        {stages.map((stage, index) => (
          <motion.div
            key={stage.name}
            className={`
              flex-shrink-0
              w-28
              p-3
              rounded-lg
              border-2
              bg-gradient-to-br
              cursor-pointer
              ${index < 3 ? `border-${stage.color}-500/50 from-${stage.color}-500/20 to-${stage.color}-500/5` : 'border-gray-600/30 from-gray-600/10 to-gray-600/5'}
              hover:scale-105 transition-transform
            `}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.05 }}
            whileHover={{ y: -5 }}
          >
            <div className="text-xs text-gray-400 mb-1">{stage.name}</div>
            <div className="text-2xl font-bold text-white mb-1">
              <CountUpNumber value={stage.count} />
            </div>
            {stage.change !== 0 && (
              <div className={`text-xs ${stage.change > 0 ? 'text-green-400' : 'text-red-400'}`}>
                {stage.change > 0 ? '↑' : '↓'} {Math.abs(stage.change)}
              </div>
            )}
          </motion.div>
        ))}
      </div>
    </GlassCard>
  );
};
```

**继续下一部分...**

由于内容太长，我需要分成多个部分。这是Week 7的Day 5-6部分，还需要继续：

5. 核心业务数据指标
6. 全球市场焦点地图  
7. 系统状态面板
8. Day 7的动画优化

**是否继续生成剩余内容？** 🚀
