/**
 * Geometría 2D para una figura tipo esqueleto a partir del vector 32D.
 * Orden de componentes alineado con `vision/feature_engine.py` → `build_feature_vector`.
 *
 * - Índices 0–1: media de flexión de rodilla izq./der. (ya multiplicada por escala de calibración).
 * - Índice 20: factor de calibración hombro (~0.5–2). Se divide para aproximar grados.
 *
 * No existe inversión única del vector completo a landmarks: esto solo refleja las medias de rodilla.
 */

export type Pt = { x: number; y: number };

/** Flexión aproximada en grados (0 ≈ extensión, mayor ≈ más sentadilla). */
export function kneeFlexDegreesFromVector(vec: number[]): { left: number; right: number; calScale: number } {
  const cal = vec[20] > 1e-6 && Number.isFinite(vec[20]) ? vec[20] : 1;
  const rawL = Number(vec[0]) / cal;
  const rawR = Number(vec[1]) / cal;
  const clamp = (v: number) => Math.max(0, Math.min(175, v));
  return { left: clamp(rawL), right: clamp(rawR), calScale: cal };
}

function ankleFromKnee(hip: Pt, knee: Pt, shinLen: number, flexDeg: number): Pt {
  const internalRad = ((180 - Math.max(0, Math.min(179, flexDeg))) * Math.PI) / 180;
  const ang = Math.atan2(hip.y - knee.y, hip.x - knee.x);
  const ang2 = ang + (Math.PI - internalRad);
  return {
    x: knee.x + Math.cos(ang2) * shinLen,
    y: knee.y + Math.sin(ang2) * shinLen,
  };
}

/** Cadenas pierna + brazos neutros + tronco (coords en espacio 0–100, Y hacia abajo). */
export function buildStickFigurePoints(vec: number[]): {
  flexL: number;
  flexR: number;
  nose: Pt;
  midShoulder: Pt;
  lShoulder: Pt;
  rShoulder: Pt;
  lElbow: Pt;
  rElbow: Pt;
  lWrist: Pt;
  rWrist: Pt;
  midHip: Pt;
  lHip: Pt;
  rHip: Pt;
  lKnee: Pt;
  rKnee: Pt;
  lAnkle: Pt;
  rAnkle: Pt;
} | null {
  if (!vec.length) return null;
  const { left: flexL, right: flexR } = kneeFlexDegreesFromVector(vec);

  const midHip = { x: 50, y: 52 };
  const lHip = { x: 42, y: 52 };
  const rHip = { x: 58, y: 52 };
  const thigh = 13.5;
  const shin = 13.5;

  const spread = 0.22;
  const lk = {
    x: lHip.x + Math.sin(-spread) * thigh,
    y: lHip.y + Math.cos(-spread) * thigh,
  };
  const rk = {
    x: rHip.x + Math.sin(spread) * thigh,
    y: rHip.y + Math.cos(spread) * thigh,
  };

  const lAnkle = ankleFromKnee(lHip, lk, shin, flexL);
  const rAnkle = ankleFromKnee(rHip, rk, shin, flexR);

  const midShoulder = { x: 50, y: 26 };
  const lShoulder = { x: 40, y: 26 };
  const rShoulder = { x: 60, y: 26 };
  const lElbow = { x: 36, y: 39 };
  const rElbow = { x: 64, y: 39 };
  const lWrist = { x: 34, y: 54 };
  const rWrist = { x: 66, y: 54 };
  const nose = { x: 50, y: 14 };

  return {
    flexL,
    flexR,
    nose,
    midShoulder,
    lShoulder,
    rShoulder,
    lElbow,
    rElbow,
    lWrist,
    rWrist,
    midHip,
    lHip,
    rHip,
    lKnee: lk,
    rKnee: rk,
    lAnkle,
    rAnkle,
  };
}
