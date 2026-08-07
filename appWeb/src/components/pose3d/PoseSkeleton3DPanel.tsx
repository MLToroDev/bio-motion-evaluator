import { Suspense, useMemo } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls } from '@react-three/drei';
import * as THREE from 'three';
import type { LandmarkMap } from '../../lib/poseWsPayload';
import { buildPointMapForPose3d, type Pose3dCoordinateSource } from './landmarkToWorld';
import { PoseSkeleton3DScene } from './PoseSkeleton3DScene';

function SceneBackdrop({ source }: { source: Pose3dCoordinateSource }) {
  const grid = useMemo(() => {
    const size = source === 'world' ? 4 : 3;
    const divisions = source === 'world' ? 24 : 30;
    return new THREE.GridHelper(size, divisions, '#3d4540', '#2a302d');
  }, [source]);
  const axes = useMemo(
    () => new THREE.AxesHelper(source === 'world' ? 0.45 : 0.65),
    [source],
  );
  const gridY = source === 'world' ? -0.95 : -1.12;
  return (
    <>
      <primitive object={grid} position={[0, gridY, 0]} />
      <primitive object={axes} position={[0, gridY, 0]} />
    </>
  );
}

function SceneContent({
  points,
  source,
}: {
  points: Map<number, THREE.Vector3>;
  source: Pose3dCoordinateSource;
}) {
  const minD = source === 'world' ? 0.55 : 1.15;
  const maxD = source === 'world' ? 4.2 : 5.5;

  return (
    <>
      <color attach="background" args={['#121614']} />
      <ambientLight intensity={0.72} />
      <directionalLight position={[3.5, 5, 2.5]} intensity={1.05} castShadow={false} />
      <directionalLight position={[-2, 2, -3]} intensity={0.35} />
      <SceneBackdrop source={source} />
      <PoseSkeleton3DScene points={points} />
      <OrbitControls
        enableDamping
        dampingFactor={0.08}
        minDistance={minD}
        maxDistance={maxD}
        target={[0, 0, 0]}
      />
    </>
  );
}

export function PoseSkeleton3DPanel({
  landmarks,
  worldLandmarks,
  mirrorHorizontal = false,
}: {
  landmarks: LandmarkMap[] | null;
  worldLandmarks: LandmarkMap[] | null;
  mirrorHorizontal?: boolean;
}) {
  const { points, source } = useMemo(
    () => buildPointMapForPose3d(landmarks, worldLandmarks, mirrorHorizontal),
    [landmarks, worldLandmarks, mirrorHorizontal],
  );

  const hasPose = points.size >= 4;

  const sourceHint =
    source === 'world'
      ? 'Coordenadas mundo (m) · world_landmarks'
      : 'Proyección 3D desde imagen (world_landmarks incompleto o ausente)';

  return (
    <section
      style={{
        border: '1px solid var(--bm-border)',
        borderRadius: 'var(--bm-radius-md)',
        overflow: 'hidden',
        background: 'var(--bm-surface)',
      }}
      aria-label="Vista 3D del esqueleto"
    >
      <div
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '0.5rem',
          padding: '0.5rem 0.75rem',
          borderBottom: '1px solid var(--bm-border)',
        }}
      >
        <h3
          style={{
            margin: 0,
            fontSize: '0.75rem',
            fontWeight: 700,
            letterSpacing: '0.07em',
            textTransform: 'uppercase',
            color: 'var(--bm-text-disabled)',
            fontFamily: 'var(--bm-font-body)',
          }}
        >
          Pose 3D
        </h3>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 2, maxWidth: '72%' }}>
          <span className="bm-caption" style={{ color: 'var(--bm-text-secondary)', textAlign: 'right' }}>
            Arrastra · rueda zoom
          </span>
          <span
            className="bm-caption"
            style={{
              fontSize: '0.65rem',
              color: source === 'world' ? 'var(--bm-accent)' : 'var(--bm-angle-warn)',
              textAlign: 'right',
              lineHeight: 1.35,
            }}
            title={sourceHint}
          >
            {source === 'world' ? '● Mundo (backend)' : '● Fallback imagen'}
          </span>
        </div>
      </div>
      <div style={{ height: 'min(340px, 42vh)', minHeight: 240, position: 'relative' }}>
        {!hasPose ? (
          <div
            style={{
              position: 'absolute',
              inset: 0,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'var(--bm-text-disabled)',
              fontFamily: 'var(--bm-font-body)',
              fontSize: '0.875rem',
              textAlign: 'center',
              padding: '1rem',
            }}
          >
            Inicia un análisis o espera landmarks del servidor para ver el grafo articulado.
          </div>
        ) : (
          <Canvas
            key={source}
            camera={{
              position: source === 'world' ? ([1.4, 0.85, 1.85] as const) : ([2.1, 1.35, 2.35] as const),
              fov: source === 'world' ? 48 : 42,
              near: 0.02,
              far: 80,
            }}
            dpr={[1, 2]}
            gl={{ antialias: true, alpha: false }}
            style={{ width: '100%', height: '100%', display: 'block' }}
          >
            <Suspense fallback={null}>
              <SceneContent points={points} source={source} />
            </Suspense>
          </Canvas>
        )}
      </div>
    </section>
  );
}
