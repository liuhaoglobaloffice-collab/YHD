/**
 * Jarvis 全息圆环组件
 * 三层旋转的全息扫描环
 */

import React, { useRef, useMemo } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';

interface HologramRingsProps {
  state: 'idle' | 'thinking' | 'working' | 'speaking' | 'success' | 'warning';
}

const HologramRings: React.FC<HologramRingsProps> = ({ state }) => {
  const ring1Ref = useRef<THREE.Mesh>(null);
  const ring2Ref = useRef<THREE.Mesh>(null);
  const ring3Ref = useRef<THREE.Mesh>(null);

  // 根据状态调整旋转速度
  const speeds = useMemo(() => {
    const baseSpeed = {
      idle: 0.2,
      thinking: 0.5,
      working: 0.8,
      speaking: 0.4,
      success: 1.0,
      warning: 0.9,
    }[state];

    return {
      ring1: baseSpeed * 0.5,
      ring2: baseSpeed * -0.7,
      ring3: baseSpeed * 0.9,
    };
  }, [state]);

  // 根据状态调整颜色
  const colors = useMemo(() => {
    return {
      idle: '#00d9ff',
      thinking: '#00ffff',
      working: '#00d9ff',
      speaking: '#9900ff',
      success: '#00ff88',
      warning: '#ff0055',
    }[state];
  }, [state]);

  // 动画循环
  useFrame((_, delta) => {
    if (ring1Ref.current) {
      ring1Ref.current.rotation.z += speeds.ring1 * delta;
    }
    if (ring2Ref.current) {
      ring2Ref.current.rotation.z += speeds.ring2 * delta;
    }
    if (ring3Ref.current) {
      ring3Ref.current.rotation.z += speeds.ring3 * delta;
    }
  });

  return (
    <group>
      {/* 第一层圆环 - 最外层 */}
      <mesh ref={ring1Ref} rotation={[Math.PI / 2, 0, 0]}>
        <torusGeometry args={[2.5, 0.02, 16, 100]} />
        <meshBasicMaterial
          color={colors}
          transparent
          opacity={0.6}
          blending={THREE.AdditiveBlending}
        />
      </mesh>

      {/* 第二层圆环 - 中层 */}
      <mesh ref={ring2Ref} rotation={[Math.PI / 2, 0, 0]}>
        <torusGeometry args={[2.0, 0.015, 16, 100]} />
        <meshBasicMaterial
          color={colors}
          transparent
          opacity={0.7}
          blending={THREE.AdditiveBlending}
        />
      </mesh>

      {/* 第三层圆环 - 内层 */}
      <mesh ref={ring3Ref} rotation={[Math.PI / 2, 0, 0]}>
        <torusGeometry args={[1.5, 0.01, 16, 100]} />
        <meshBasicMaterial
          color={colors}
          transparent
          opacity={0.8}
          blending={THREE.AdditiveBlending}
        />
      </mesh>

      {/* 扫描线 - 垂直旋转 */}
      {state !== 'idle' && (
        <>
          <mesh rotation={[0, 0, 0]}>
            <planeGeometry args={[5, 0.05]} />
            <meshBasicMaterial
              color={colors}
              transparent
              opacity={0.3}
              blending={THREE.AdditiveBlending}
              side={THREE.DoubleSide}
            />
          </mesh>
          <mesh rotation={[0, Math.PI / 2, 0]}>
            <planeGeometry args={[5, 0.05]} />
            <meshBasicMaterial
              color={colors}
              transparent
              opacity={0.3}
              blending={THREE.AdditiveBlending}
              side={THREE.DoubleSide}
            />
          </mesh>
        </>
      )}
    </group>
  );
};

export default HologramRings;
