/**
 * Jarvis 全息助手动画控制器
 * 管理不同状态下的动画效果
 */

import { gsap } from 'gsap';
import * as THREE from 'three';

export type JarvisState = 'idle' | 'thinking' | 'working' | 'speaking' | 'success' | 'warning';

export interface AnimationConfig {
  coreGlowIntensity: number;
  coreGlowColor: string;
  ringRotationSpeed: number;
  particleSpeed: number;
  particleCount: number;
  pulseSpeed: number;
}

/**
 * 不同状态的动画配置
 */
export const stateConfigs: Record<JarvisState, AnimationConfig> = {
  idle: {
    coreGlowIntensity: 1.0,
    coreGlowColor: '#00d9ff',
    ringRotationSpeed: 0.001,
    particleSpeed: 0.5,
    particleCount: 100,
    pulseSpeed: 2,
  },
  thinking: {
    coreGlowIntensity: 1.5,
    coreGlowColor: '#00ffff',
    ringRotationSpeed: 0.003,
    particleSpeed: 1.0,
    particleCount: 150,
    pulseSpeed: 1,
  },
  working: {
    coreGlowIntensity: 2.0,
    coreGlowColor: '#00d9ff',
    ringRotationSpeed: 0.005,
    particleSpeed: 1.5,
    particleCount: 200,
    pulseSpeed: 0.5,
  },
  speaking: {
    coreGlowIntensity: 1.8,
    coreGlowColor: '#9900ff',
    ringRotationSpeed: 0.002,
    particleSpeed: 1.2,
    particleCount: 180,
    pulseSpeed: 0.8,
  },
  success: {
    coreGlowIntensity: 2.5,
    coreGlowColor: '#00ff88',
    ringRotationSpeed: 0.004,
    particleSpeed: 2.0,
    particleCount: 250,
    pulseSpeed: 0.3,
  },
  warning: {
    coreGlowIntensity: 2.2,
    coreGlowColor: '#ff0055',
    ringRotationSpeed: 0.006,
    particleSpeed: 1.8,
    particleCount: 220,
    pulseSpeed: 0.4,
  },
};

/**
 * 平滑切换状态动画
 */
export const transitionToState = (
  state: JarvisState,
  material: THREE.MeshStandardMaterial,
  duration: number = 0.8
) => {
  const config = stateConfigs[state];
  
  // 使用GSAP平滑过渡材质属性
  gsap.to(material, {
    emissiveIntensity: config.coreGlowIntensity,
    duration,
    ease: 'power2.inOut',
  });

  // 过渡发光颜色
  const targetColor = new THREE.Color(config.coreGlowColor);
  gsap.to(material.emissive, {
    r: targetColor.r,
    g: targetColor.g,
    b: targetColor.b,
    duration,
    ease: 'power2.inOut',
  });

  return config;
};

/**
 * 呼吸动画
 */
export const createBreathingAnimation = (
  mesh: THREE.Mesh,
  baseScale: number = 1.0,
  amplitude: number = 0.05,
  speed: number = 2
) => {
  return gsap.to(mesh.scale, {
    x: baseScale + amplitude,
    y: baseScale + amplitude,
    z: baseScale + amplitude,
    duration: speed,
    yoyo: true,
    repeat: -1,
    ease: 'sine.inOut',
  });
};

/**
 * 旋转动画
 */
export const createRotationAnimation = (
  object: THREE.Object3D,
  speed: number = 0.001,
  axis: 'x' | 'y' | 'z' = 'y'
) => {
  return (delta: number) => {
    object.rotation[axis] += speed * delta * 60;
  };
};

/**
 * 脉冲动画
 */
export const createPulseAnimation = (
  material: THREE.MeshStandardMaterial,
  minIntensity: number = 0.5,
  maxIntensity: number = 2.0,
  speed: number = 1
) => {
  return gsap.to(material, {
    emissiveIntensity: maxIntensity,
    duration: speed,
    yoyo: true,
    repeat: -1,
    ease: 'sine.inOut',
  });
};

/**
 * 扫描线动画
 */
export const createScanLineAnimation = (
  scanLine: THREE.Mesh,
  height: number = 3,
  speed: number = 2
) => {
  scanLine.position.y = -height / 2;
  
  return gsap.to(scanLine.position, {
    y: height / 2,
    duration: speed,
    repeat: -1,
    ease: 'none',
  });
};

/**
 * 波纹扩散动画
 */
export const createRippleAnimation = (
  ring: THREE.Mesh,
  maxScale: number = 2.0,
  duration: number = 1.5
) => {
  ring.scale.set(0.1, 0.1, 0.1);
  const material = ring.material as THREE.MeshBasicMaterial;
  
  return gsap.timeline()
    .to(ring.scale, {
      x: maxScale,
      y: maxScale,
      z: maxScale,
      duration,
      ease: 'power2.out',
    })
    .to(material, {
      opacity: 0,
      duration: duration * 0.5,
      ease: 'power2.in',
    }, duration * 0.5);
};
