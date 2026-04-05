import { useMemo } from 'react';
import * as THREE from 'three';
import {
  POSE_CONNECTIONS,
  POSE_LEFT_HIP,
  POSE_RIGHT_HIP,
} from '../../lib/poseTopology';

function Bone({
  from,
  to,
}: {
  from: THREE.Vector3;
  to: THREE.Vector3;
}) {
  const geom = useMemo(() => {
    const delta = new THREE.Vector3().subVectors(to, from);
    const len = delta.length();
    if (len < 1e-5) return null;
    const mid = new THREE.Vector3().addVectors(from, to).multiplyScalar(0.5);
    const quat = new THREE.Quaternion();
    quat.setFromUnitVectors(new THREE.Vector3(0, 1, 0), delta.clone().normalize());
    return { mid, quat, len };
  }, [from, to]);

  if (!geom) return null;

  return (
    <mesh position={geom.mid} quaternion={geom.quat} scale={[1, geom.len, 1]}>
      <cylinderGeometry args={[0.026, 0.026, 1, 10]} />
      <meshStandardMaterial color="#0a0a0a" roughness={0.65} metalness={0.08} />
    </mesh>
  );
}

function Joint({ position }: { position: THREE.Vector3 }) {
  return (
    <mesh position={position}>
      <sphereGeometry args={[0.042, 14, 14]} />
      <meshStandardMaterial color="#c62828" roughness={0.45} metalness={0.15} />
    </mesh>
  );
}

function offsetForPose3d(points: Map<number, THREE.Vector3>): THREE.Vector3 {
  const l = points.get(POSE_LEFT_HIP);
  const r = points.get(POSE_RIGHT_HIP);
  if (l && r) {
    return l.clone().add(r).multiplyScalar(0.5);
  }
  return centroidFromMap(points);
}

export function PoseSkeleton3DScene({ points }: { points: Map<number, THREE.Vector3> }) {
  const center = useMemo(() => offsetForPose3d(points), [points]);

  const bones = useMemo(() => {
    const out: [THREE.Vector3, THREE.Vector3][] = [];
    for (const [a, b] of POSE_CONNECTIONS) {
      const pa = points.get(a);
      const pb = points.get(b);
      if (pa && pb) out.push([pa.clone(), pb.clone()]);
    }
    return out;
  }, [points]);

  const joints = useMemo(() => Array.from(points.values()).map((p) => p.clone()), [points]);

  const offset = useMemo(() => new THREE.Vector3(-center.x, -center.y, -center.z), [center]);

  return (
    <group position={offset}>
      {bones.map(([from, to], i) => (
        <Bone key={i} from={from} to={to} />
      ))}
      {joints.map((p, i) => (
        <Joint key={i} position={p} />
      ))}
    </group>
  );
}

function centroidFromMap(points: Map<number, THREE.Vector3>): THREE.Vector3 {
  const c = new THREE.Vector3();
  let n = 0;
  for (const v of points.values()) {
    c.add(v);
    n += 1;
  }
  if (n > 0) c.multiplyScalar(1 / n);
  return c;
}
