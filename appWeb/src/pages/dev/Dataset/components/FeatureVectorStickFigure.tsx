import { Suspense, useMemo } from 'react';
import { Canvas } from '@react-three/fiber';
import { Line, OrbitControls } from '@react-three/drei';
import * as THREE from 'three';
import { buildStickFigurePoints } from './featureVectorStickGeometry';
import { buildStickFigure3DSegments } from './featureVectorStick3d';

const STICK_COLOR = '#00e676';

function KneeDot({ position }: { position: THREE.Vector3 }) {
  return (
    <mesh position={position}>
      <sphereGeometry args={[0.018, 14, 14]} />
      <meshStandardMaterial color={STICK_COLOR} emissive={STICK_COLOR} emissiveIntensity={0.35} />
    </mesh>
  );
}

function StickScene({ featureVector }: { featureVector: number[] }) {
  const data = useMemo(() => buildStickFigure3DSegments(featureVector), [featureVector]);

  if (!data) return null;

  return (
    <>
      <ambientLight intensity={0.75} />
      <directionalLight position={[2.2, 3.5, 2]} intensity={1.05} />
      <directionalLight position={[-2, 1.5, -2]} intensity={0.4} />
      {data.segments.map((points, i) => (
        <Line key={i} points={points} color={STICK_COLOR} lineWidth={2.5} transparent opacity={0.95} />
      ))}
      {data.knees.map((pos, i) => (
        <KneeDot key={i} position={pos} />
      ))}
      <OrbitControls
        enableDamping
        dampingFactor={0.06}
        minDistance={0.55}
        maxDistance={3.2}
        autoRotate
        autoRotateSpeed={0.65}
        target={[0, 0.15, 0]}
      />
    </>
  );
}

/** Figura aproximada + vista 3D interactiva (arrastra para orbitar; zoom con rueda). */
export function FeatureVectorStickFigure({ featureVector }: { featureVector: number[] }) {
  const p = buildStickFigurePoints(featureVector);
  if (!p) return null;

  return (
    <div className="bm-dev-feature-stick-wrap">
      <p className="bm-caption bm-dev-feature-stick__note">
        Figura esquemática a partir de las medias de flexión de rodilla del vector (índices 0–1, desescaladas con
        el factor 20). Brazos en pose neutra. <strong>Vista 3D:</strong> arrastra para rotar; la vista gira sola
        lentamente.
      </p>
      <div className="bm-dev-feature-stick__metrics bm-mono">
        Flex. rodilla (aprox.): L {p.flexL.toFixed(1)}° · R {p.flexR.toFixed(1)}°
      </div>
      <div className="bm-dev-feature-stick-canvas">
        <Suspense fallback={<div className="bm-dev-feature-stick-canvas-fallback">Cargando vista 3D…</div>}>
          <Canvas
            camera={{ position: [0, 0.35, 1.15], fov: 42, near: 0.05, far: 20 }}
            gl={{ antialias: true, alpha: true }}
            dpr={[1, 2]}
          >
            <color attach="background" args={['#121614']} />
            <StickScene featureVector={featureVector} />
          </Canvas>
        </Suspense>
      </div>
    </div>
  );
}
