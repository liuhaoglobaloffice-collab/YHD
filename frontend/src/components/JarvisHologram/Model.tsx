/**
 * Jarvis 3D 核心模型组件
 * 全息人物核心球体 + 发光效果
 */

import React, { useRef, useEffect } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';
import { transitionToState, createBreathingAnimation, type JarvisState } from './animations';

interface ModelProps {
  state: JarvisState;
}

const Model: React.FC<ModelProps> = ({ state }) => {
  const coreMeshRef = useRef<THREE.Mesh>(null);
  const innerGlowRef = useRef<THREE.Mesh>(null);
  const outerGlowRef = useRef<THREE.Mesh>(null);

  // 状态切换时更新材质
  useEffect(() => {
    if (!coreMeshRef.current) return;

    const material = coreMeshRef.current.material as THREE.MeshStandardMaterial;
    transitionToState(state, material, 0.8);
  }, [state]);

  // 呼吸动画
  useEffect(() => {
    if (!coreMeshRef.current) return;
    
    const animation = createBreathingAnimation(coreMeshRef.current, 1.0, 0.05, 2);
    
    return () => {
      animation.kill();
    };
  }, []);

  // 自转动画
  useFrame((_, delta) => {
    if (coreMeshRef.current) {
      coreMeshRef.current.rotation.y += 0.001 * delta * 60;
    }
    if (innerGlowRef.current) {
      innerGlowRef.current.rotation.y -= 0.002 * delta * 60;
    }
    if (outerGlowRef.current) {
      outerGlowRef.current.rotation.y += 0.0015 * delta * 60;
    }
  });

  return (
    <group>
      {/* 核心球体 - 主体 */}
      <mesh ref={coreMeshRef}>
        <sphereGeometry args={[1, 64, 64]} />
        <meshStandardMaterial
          color="#00d9ff"
          emissive="#00d9ff"
          emissiveIntensity={1.0}
          metalness={0.9}
          roughness={0.1}
          transparent
          opacity={0.8}
        />
      </mesh>

      {/* 内层发光环 */}
      <mesh ref={innerGlowRef} scale={1.2}>
        <sphereGeometry args={[1, 32, 32]} />
        <meshBasicMaterial
          color="#00ffff"
          transparent
          opacity={0.2}
          blending={THREE.AdditiveBlending}
          side={THREE.BackSide}
        />
      </mesh>

      {/* 外层发光环 */}
      <mesh ref={outerGlowRef} scale={1.5}>
        <sphereGeometry args={[1, 32, 32]} />
        <meshBasicMaterial
          color="#00d9ff"
          transparent
          opacity={0.1}
          blending={THREE.AdditiveBlending}
          side={THREE.BackSide}
        />
      </mesh>

      {/* 网格线 - 全息效果 */}
      <mesh>
        <sphereGeometry args={[1.05, 32, 32]} />
        <meshBasicMaterial
          color="#00ffff"
          wireframe
          transparent
          opacity={0.3}
        />
      </mesh>

      {/* 赤道环 */}
      <mesh rotation={[Math.PI / 2, 0, 0]}>
        <torusGeometry args={[1.1, 0.01, 16, 100]} />
        <meshBasicMaterial
          color="#00d9ff"
          transparent
          opacity={0.6}
          blending={THREE.AdditiveBlending}
        />
      </mesh>

      {/* 经线环 */}
      <mesh>
        <torusGeometry args={[1.1, 0.01, 16, 100]} />
        <meshBasicMaterial
          color="#00d9ff"
          transparent
          opacity={0.6}
          blending={THREE.AdditiveBlending}
        />
      </mesh>
    </group>
  );
};

export default Model;
