import { Canvas } from '@react-three/fiber'
import { OrbitControls, Environment, ContactShadows } from '@react-three/drei'
import { useMemo } from 'react'
import * as THREE from 'three'

function RoomSketch() {
  const wall = useMemo(() => new THREE.MeshStandardMaterial({ color: '#c4b8a8', roughness: 0.55 }), [])
  const floor = useMemo(() => new THREE.MeshStandardMaterial({ color: '#2a2520', roughness: 0.4, metalness: 0.05 }), [])
  const glass = useMemo(
    () =>
      new THREE.MeshPhysicalMaterial({
        color: '#a8c4e8',
        roughness: 0.1,
        metalness: 0,
        transmission: 0.92,
        thickness: 0.4,
        transparent: true,
      }),
    [],
  )

  return (
    <group>
      <mesh position={[0, -0.01, 0]} rotation={[-Math.PI / 2, 0, 0]} material={floor}>
        <planeGeometry args={[5, 4]} />
      </mesh>
      <mesh position={[0, 1.2, -2]} material={wall}>
        <boxGeometry args={[5, 2.4, 0.08]} />
      </mesh>
      <mesh position={[-2.4, 1.2, 0]} material={wall}>
        <boxGeometry args={[0.08, 2.4, 3.8]} />
      </mesh>
      <mesh position={[2.4, 1.2, 0]} material={wall}>
        <boxGeometry args={[0.08, 2.4, 3.8]} />
      </mesh>
      <mesh position={[0, 0.65, -1.95]} material={glass}>
        <boxGeometry args={[2.2, 1.3, 0.04]} />
      </mesh>
      <mesh position={[0, 0.4, 0]} castShadow>
        <boxGeometry args={[1.2, 0.08, 0.7]} />
        <meshStandardMaterial color="#8b7355" roughness={0.5} />
      </mesh>
      <mesh position={[0, 0.85, 0]} castShadow>
        <boxGeometry args={[0.4, 0.5, 0.35]} />
        <meshStandardMaterial color="#e8dfd0" roughness={0.35} />
      </mesh>
      <pointLight position={[1.2, 2.2, 1.5]} intensity={12} distance={8} decay={2} />
      <spotLight
        position={[-2, 3.5, 2]}
        angle={0.35}
        penumbra={0.6}
        intensity={28}
        castShadow
        shadow-mapSize-width={1024}
        shadow-mapSize-height={1024}
      />
    </group>
  )
}

export function Property3DPreview() {
  return (
    <div className="preview-3d" role="img" aria-label="Interactive 3D layout preview — drag to rotate">
      <Canvas
        shadows
        camera={{ position: [4.2, 2.4, 4.2], fov: 42 }}
        gl={{ antialias: true }}
      >
        <color attach="background" args={['#0c0e12']} />
        <ambientLight intensity={0.35} />
        <RoomSketch />
        <ContactShadows
          position={[0, 0, 0]}
          opacity={0.45}
          scale={12}
          blur={2.5}
          far={5}
        />
        <Environment preset="city" />
        <OrbitControls
          enablePan={false}
          minPolarAngle={0.35}
          maxPolarAngle={Math.PI / 2.1}
          minDistance={3.5}
          maxDistance={8}
        />
      </Canvas>
      <span className="preview-3d__hint">Drag to orbit · scroll to zoom</span>
    </div>
  )
}
