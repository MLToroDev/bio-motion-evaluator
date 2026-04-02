import type { MetricStatus } from './metricStatus';
import type { LandmarkMap } from './poseWsPayload';

export interface FrameLogEntry {
  frame: number;
  leftDeg: number | null;
  rightDeg: number | null;
  status: MetricStatus;
  sparkLeft: number[];
  sparkRight: number[];
  previewDataUrl: string | null;
  landmarks: LandmarkMap[] | null;
}
