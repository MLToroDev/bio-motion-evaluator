import * as THREE from 'three';
import type { LandmarkMap } from '../../lib/poseWsPayload';

/** Alineado con `kPose3dMinWorldLandmarkEntries` en el cliente Flutter. */
export const MIN_WORLD_LANDMARKS_FOR_3D = 20;

/** Visibilidad mínima para fallback imagen (Flutter `kPose3dImageMinVisibility`). */
const MIN_VIS_IMAGE_3D = 0.08;

/**
 * BlazePose **world** (backend sin transformar): metros, origen entre caderas.
 * Documentación Google: X = derecha del sujeto, Y = arriba, Z = hacia el sujeto (alejado de la cámara).
 * Three.js: Y arriba. En WebGL el mismo vector suele verse invertido en vertical respecto a
 * `plot_landmarks` de matplotlib; se aplica **−Y** al mapear (validado frente al preview 2D).
 * Z se deja tal cual salvo que más adelante quieras alinear profundidad con la cámara (−Z en Three).
 *
 * @see https://developers.google.com/mediapipe/solutions/vision/pose_landmarker (world landmarks)
 */
const MP_WORLD_TO_THREE = {
  flipY: -1,
  flipZ: 1,
} as const;

/**
 * Landmarks **world** del backend: `x,y,z` en **metros** (`pose_world_landmarks` en JSON).
 * Espejo horizontal: invierte X en mundo (equivalente a voltear el sujeto).
 */
export function buildWorldLandmarkPointMap(
  worldLandmarks: LandmarkMap[] | null,
  mirror: boolean,
): Map<number, THREE.Vector3> {
  const map = new Map<number, THREE.Vector3>();
  if (!worldLandmarks) return map;
  for (const m of worldLandmarks) {
    const i = m.index;
    if (typeof i !== 'number') continue;
    const x = m.x;
    const y = m.y;
    const z = m.z;
    if (typeof x !== 'number' || typeof y !== 'number' || typeof z !== 'number') continue;
    if (!Number.isFinite(x) || !Number.isFinite(y) || !Number.isFinite(z)) continue;
    const wx = mirror ? -x : x;
    map.set(
      i,
      new THREE.Vector3(wx, MP_WORLD_TO_THREE.flipY * y, MP_WORLD_TO_THREE.flipZ * z),
    );
  }
  return map;
}

/**
 * Fallback cuando no hay `world_landmarks` suficientes: mismo remapeo que Flutter
 * `landmarksToVector3Map(..., isWorld: false)` → (x−0.5, z, −(y−0.5)) con x,y normalizados.
 */
export function buildImageLandmarkPointMapFor3d(
  landmarks: LandmarkMap[] | null,
  mirror: boolean,
): Map<number, THREE.Vector3> {
  const map = new Map<number, THREE.Vector3>();
  if (!landmarks) return map;
  for (const m of landmarks) {
    const i = m.index;
    if (typeof i !== 'number') continue;
    const vis = m.visibility;
    if (typeof vis === 'number' && vis < MIN_VIS_IMAGE_3D) continue;
    const x = m.x;
    const y = m.y;
    const z = m.z;
    if (typeof x !== 'number' || typeof y !== 'number' || typeof z !== 'number') continue;
    const nx = mirror ? 1 - x : x;
    map.set(i, new THREE.Vector3(nx - 0.5, z, -(y - 0.5)));
  }
  return map;
}

export type Pose3dCoordinateSource = 'world' | 'image';

export function buildPointMapForPose3d(
  landmarks: LandmarkMap[] | null,
  worldLandmarks: LandmarkMap[] | null,
  mirror: boolean,
): { points: Map<number, THREE.Vector3>; source: Pose3dCoordinateSource } {
  const worldMap = buildWorldLandmarkPointMap(worldLandmarks, mirror);
  if (worldMap.size >= MIN_WORLD_LANDMARKS_FOR_3D) {
    return { points: worldMap, source: 'world' };
  }
  const imageMap = buildImageLandmarkPointMapFor3d(landmarks, mirror);
  return { points: imageMap, source: 'image' };
}
