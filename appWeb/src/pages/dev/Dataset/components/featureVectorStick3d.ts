/**
 * Segmentos 3D para el monigote aproximado (misma geometría 2D → plano XZ frontal,
 * eje Y arriba en espacio Three.js).
 */
import * as THREE from 'three';
import { buildStickFigurePoints } from './featureVectorStickGeometry';

const SCALE = 0.021;

/** 2D frontal (x, y pantalla) → 3D: X derecha, Y arriba, Z hacia cámara (figura en Z≈0). */
export function stickPointToWorld(p: { x: number; y: number }): THREE.Vector3 {
  return new THREE.Vector3((p.x - 50) * SCALE, (50 - p.y) * SCALE, 0);
}

export function buildStickFigure3DSegments(vec: number[]): {
  segments: [THREE.Vector3, THREE.Vector3][];
  knees: THREE.Vector3[];
} | null {
  const fig = buildStickFigurePoints(vec);
  if (!fig) return null;
  const t = stickPointToWorld;
  const seg = (a: { x: number; y: number }, b: { x: number; y: number }): [THREE.Vector3, THREE.Vector3] => [
    t(a),
    t(b),
  ];
  const segments: [THREE.Vector3, THREE.Vector3][] = [
    seg(fig.nose, fig.midShoulder),
    seg(fig.midShoulder, fig.midHip),
    seg(fig.lShoulder, fig.rShoulder),
    seg(fig.midShoulder, fig.lShoulder),
    seg(fig.midShoulder, fig.rShoulder),
    seg(fig.lShoulder, fig.lElbow),
    seg(fig.lElbow, fig.lWrist),
    seg(fig.rShoulder, fig.rElbow),
    seg(fig.rElbow, fig.rWrist),
    seg(fig.lHip, fig.lKnee),
    seg(fig.lKnee, fig.lAnkle),
    seg(fig.rHip, fig.rKnee),
    seg(fig.rKnee, fig.rAnkle),
    seg(fig.midHip, fig.lHip),
    seg(fig.midHip, fig.rHip),
  ];
  return {
    segments,
    knees: [t(fig.lKnee), t(fig.rKnee)],
  };
}
