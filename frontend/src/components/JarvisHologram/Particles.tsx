/**
 * Jarvis 粒子系统组件
 * 动态粒子网络效果
 */

import React, { useRef, useMemo } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';

interface ParticlesProps {
  count: number;
  state: 'idle' | 'thinking' | 'working' | 'speaking' | 'success' | 'warning';
}

const Particles: React.FC<ParticlesProps> = ({ count, state }) => {
  const pointsRef = useRef<THREE.Points>(null);
  const velocitiesRef = useRef<Float32Array>();

  // 根据状态调整粒子颜色
  const color = useMemo(() => {
    return {
      idle: new THREE.Color('#00d9ff'),
      thinking: new THREE.Color('#00ffff'),
      working: new THREE.Color('#00d9ff'),
      speaking: new THREE.Color('#9900ff'),
      success: new THREE.Color('#00ff88'),
      warning: new THREE.Color('#ff0055'),
    }[state];
  }, [state]);

  // 根据状态调整粒子速度
  const speed = useMemo(() => {
    return {
      idle: 0.5,
      thinking: 1.0,
      working: 1.5,
      speaking: 1.2,
      success: 2.0,
      warning: 1.8,
    }[state];
  }, [state]);

  // 初始化粒子位置和速度
  const { positions, colors } = useMemo(() => {
    const positions = new Float32Array(count * 3);
    const colors = new Float32Array(count * 3);
    const velocities = new Float32Array(count * 3);

    for (let i = 0; i < count; i++) {
      const i3 = i * 3;
      
      // 在球体内随机分布
      const radius = 1 + Math.random() * 2;
      const theta = Math.random() * Math.PI * 2;
      const phi = Math.random() * Math.PI;

      positions[i3] = radius * Math.sin(phi) * Math.cos(theta);
      positions[i3 + 1] = radius * Math.sin(phi) * Math.sin(theta);
      positions[i3 + 2] = radius * Math.cos(phi);

      // 随机速度
      velocities[i3] = (Math.random() - 0.5) * 0.02;
      velocities[i3 + 1] = (Math.random() - 0.5) * 0.02;
      velocities[i3 + 2] = (Math.random() - 0.5) * 0.02;

      // 粒子颜色（带随机亮度变化）
      const brightness = 0.5 + Math.random() * 0.5;
      colors[i3] = color.r * brightness;
      colors[i3 + 1] = color.g * brightness;
      colors[i3 + 2] = color.b * brightness;
    }

    velocitiesRef.current = velocities;
    return { positions, colors };
  }, [count, color]);

  // 动画循环 - 粒子运动
  useFrame((_, delta) => {
    if (!pointsRef.current || !velocitiesRef.current) return;

    const positions = pointsRef.current.geometry.attributes.position.array as Float32Array;
    const velocities = velocitiesRef.current;

    for (let i = 0; i < count; i++) {
      const i3 = i * 3;

      // 更新位置
      positions[i3] += velocities[i3] * speed * delta * 60;
      positions[i3 + 1] += velocities[i3 + 1] * speed * delta * 60;
      positions[i3 + 2] += velocities[i3 + 2] * speed * delta * 60;

      // 边界检测 - 保持在球体范围内
      const x = positions[i3];
      const y = positions[i3 + 1];
      const z = positions[i3 + 2];
      const distance = Math.sqrt(x * x + y * y + z * z);

      if (distance > 3) {
        // 反弹
        velocities[i3] *= -1;
        velocities[i3 + 1] *= -1;
        velocities[i3 + 2] *= -1;
      } else if (distance < 0.5) {
        // 从中心推出
        const force = 0.01;
        velocities[i3] += (x / distance) * force;
        velocities[i3 + 1] += (y / distance) * force;
        velocities[i3 + 2] += (z / distance) * force;
      }
    }

    pointsRef.current.geometry.attributes.position.needsUpdate = true;
  });

  return (
    <points ref={pointsRef}>
      <bufferGeometry>
        <bufferAttribute
          attach="attributes-position"
          count={count}
          array={positions}
          itemSize={3}
        />
        <bufferAttribute
          attach="attributes-color"
          count={count}
          array={colors}
          itemSize={3}
        />
      </bufferGeometry>
      <pointsMaterial
        size={0.05}
        vertexColors
        transparent
        opacity={0.8}
        blending={THREE.AdditiveBlending}
        sizeAttenuation
      />
    </points>
  );
};

export default Particles;
