import type { MetricStatus } from './metricStatus';

export interface AnalysisSummary {
  framesProcessed: number;
  framesWithBothKnees: number;
  framesGoodRom: number;
  pctGood: number;
  meanLeftDeg: number | null;
  meanRightDeg: number | null;
  minLeftDeg: number | null;
  maxLeftDeg: number | null;
  minLeftFrame: number;
  maxLeftFrame: number;
  minRightDeg: number | null;
  maxRightDeg: number | null;
  minRightFrame: number;
  maxRightFrame: number;
  lastExerciseLabel: string;
  lastRepCount: number;
  lastRepPhase: string;
  lastQualityFlags: string[];
}

export function summaryQualityStatus(s: AnalysisSummary): MetricStatus {
  if (s.pctGood >= 70) return 'good';
  if (s.pctGood >= 40) return 'warn';
  return 'bad';
}

/** Port de VideoAnalysisAccumulator (analysis_summary.dart) */
export class VideoAnalysisAccumulator {
  framesProcessed = 0;
  framesWithBothKnees = 0;
  framesGoodRom = 0;
  private _sumL = 0;
  private _sumR = 0;
  private _nL = 0;
  private _nR = 0;
  private _minL: number | null = null;
  private _maxL: number | null = null;
  private _minLFrame = 0;
  private _maxLFrame = 0;
  private _minR: number | null = null;
  private _maxR: number | null = null;
  private _minRFrame = 0;
  private _maxRFrame = 0;
  private _lastExerciseLabel = 'unknown';
  private _lastRepCount = 0;
  private _lastRepPhase = 'idle';
  private _lastQualityFlags: string[] = [];

  reset(): void {
    this.framesProcessed = 0;
    this.framesWithBothKnees = 0;
    this.framesGoodRom = 0;
    this._sumL = 0;
    this._sumR = 0;
    this._nL = 0;
    this._nR = 0;
    this._minL = null;
    this._maxL = null;
    this._minR = null;
    this._maxR = null;
    this._minLFrame = 0;
    this._maxLFrame = 0;
    this._minRFrame = 0;
    this._maxRFrame = 0;
    this._lastExerciseLabel = 'unknown';
    this._lastRepCount = 0;
    this._lastRepPhase = 'idle';
    this._lastQualityFlags = [];
  }

  addFrame(params: {
    frameIndex: number;
    leftDeg: number | null;
    rightDeg: number | null;
    bothGoodRom: (l: number, r: number) => boolean;
    exerciseLabel?: string;
    repCount?: number;
    repPhase?: string;
    qualityFlags?: string[];
  }): void {
    const {
      frameIndex,
      leftDeg,
      rightDeg,
      bothGoodRom,
      exerciseLabel = 'unknown',
      repCount = 0,
      repPhase = 'idle',
      qualityFlags = [],
    } = params;
    this._lastExerciseLabel = exerciseLabel;
    this._lastRepCount = repCount;
    this._lastRepPhase = repPhase;
    this._lastQualityFlags = [...qualityFlags];
    this.framesProcessed++;
    if (leftDeg != null) {
      this._sumL += leftDeg;
      this._nL++;
      if (this._minL == null || leftDeg < this._minL) {
        this._minL = leftDeg;
        this._minLFrame = frameIndex;
      }
      if (this._maxL == null || leftDeg > this._maxL) {
        this._maxL = leftDeg;
        this._maxLFrame = frameIndex;
      }
    }
    if (rightDeg != null) {
      this._sumR += rightDeg;
      this._nR++;
      if (this._minR == null || rightDeg < this._minR) {
        this._minR = rightDeg;
        this._minRFrame = frameIndex;
      }
      if (this._maxR == null || rightDeg > this._maxR) {
        this._maxR = rightDeg;
        this._maxRFrame = frameIndex;
      }
    }
    if (leftDeg != null && rightDeg != null) {
      this.framesWithBothKnees++;
      if (bothGoodRom(leftDeg, rightDeg)) {
        this.framesGoodRom++;
      }
    }
  }

  buildSummary(): AnalysisSummary {
    const pct =
      this.framesWithBothKnees > 0 ? (this.framesGoodRom * 100) / this.framesWithBothKnees : 0;
    return {
      framesProcessed: this.framesProcessed,
      framesWithBothKnees: this.framesWithBothKnees,
      framesGoodRom: this.framesGoodRom,
      pctGood: pct,
      meanLeftDeg: this._nL > 0 ? this._sumL / this._nL : null,
      meanRightDeg: this._nR > 0 ? this._sumR / this._nR : null,
      minLeftDeg: this._minL,
      maxLeftDeg: this._maxL,
      minLeftFrame: this._minLFrame,
      maxLeftFrame: this._maxLFrame,
      minRightDeg: this._minR,
      maxRightDeg: this._maxR,
      minRightFrame: this._minRFrame,
      maxRightFrame: this._maxRFrame,
      lastExerciseLabel: this._lastExerciseLabel,
      lastRepCount: this._lastRepCount,
      lastRepPhase: this._lastRepPhase,
      lastQualityFlags: [...this._lastQualityFlags],
    };
  }
}
