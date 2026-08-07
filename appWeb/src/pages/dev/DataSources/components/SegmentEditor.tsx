import { BmButton } from '../../../../components/BmButton';
import { mmssToSec, secToMmss } from '../helpers';

export type VideoSegment = { start_sec: number; end_sec: number };

export interface SegmentFormState {
  startVal: string;
  endVal: string;
}

interface SegmentEditorProps {
  segments: VideoSegment[];
  formState: SegmentFormState;
  onFormChange: (s: SegmentFormState) => void;
  onAdd: (s: VideoSegment) => void;
  onDelete: (idx: number) => void;
  onCaptureStart: () => number;
  onCaptureEnd: () => number;
  playerReady: boolean;
  duration: number;
  addError: string;
  onClearError: () => void;
}

export function SegmentEditor({
  segments,
  formState,
  onFormChange,
  onAdd,
  onDelete,
  onCaptureStart,
  onCaptureEnd,
  playerReady,
  duration,
  addError,
  onClearError,
}: SegmentEditorProps) {
  const { startVal, endVal } = formState;

  const startSec = mmssToSec(startVal);
  const endSec = mmssToSec(endVal);
  const isReadyToAdd =
    !isNaN(startSec) && startSec >= 0 &&
    !isNaN(endSec) && endSec > startSec;

  const hasPendingData = endVal.trim() !== '' || (startVal.trim() !== '' && startVal !== '0:00');

  const handleAdd = () => {
    if (isNaN(startSec) || startSec < 0) {
      onFormChange({ ...formState });
      return;
    }
    if (isNaN(endSec) || endSec <= startSec) {
      onFormChange({ ...formState });
      return;
    }
    if (duration > 0 && endSec > duration + 1) {
      onFormChange({ ...formState });
      return;
    }
    onClearError();
    onAdd({ start_sec: startSec, end_sec: endSec });
    onFormChange({ startVal: secToMmss(endSec), endVal: '' });
  };

  const captureStart = () => {
    const t = onCaptureStart();
    onFormChange({ ...formState, startVal: secToMmss(t) });
  };

  const captureEnd = () => {
    const t = onCaptureEnd();
    onFormChange({ ...formState, endVal: secToMmss(t) });
  };

  return (
    <>
      <div className="bm-dev-segment-steps">
        <span className="bm-dev-segment-step">① Reproduce el vídeo</span>
        <span className="bm-dev-segment-step">② Captura inicio y fin</span>
        <span className="bm-dev-segment-step bm-dev-segment-step--key">③ Pulsa «+ Añadir»</span>
        <span className="bm-dev-segment-step">④ Confirmar</span>
      </div>

      {segments.length > 0 ? (
        <ul className="bm-dev-segment-list">
          {segments.map((seg, i) => (
            <li key={i} className="bm-dev-segment-row">
              <span className="bm-dev-segment-row__time">
                {secToMmss(seg.start_sec)} → {secToMmss(seg.end_sec)}
              </span>
              <span className="bm-caption" style={{ color: 'var(--bm-text-secondary)' }}>
                {Math.round(seg.end_sec - seg.start_sec)}s
              </span>
              <button
                type="button"
                className="bm-dev-segment-row__del"
                aria-label="Eliminar segmento"
                onClick={() => onDelete(i)}
              >
                ×
              </button>
            </li>
          ))}
        </ul>
      ) : (
        <p className="bm-caption" style={{ color: 'var(--bm-text-secondary)', fontStyle: 'italic' }}>
          Sin segmentos — vídeo completo.
        </p>
      )}

      <div className={`bm-dev-segment-add${isReadyToAdd ? ' bm-dev-segment-add--ready' : ''}`}>
        <div className="bm-dev-segment-add__row">
          <span className="bm-dev-segment-add__label">Inicio</span>
          <input
            type="text"
            className="bm-dev-segment-add__input"
            placeholder="0:00"
            value={startVal}
            onChange={(e) => onFormChange({ ...formState, startVal: e.target.value })}
          />
          <button
            type="button"
            className="bm-dev-segment-add__capture"
            disabled={!playerReady}
            title={playerReady ? 'Capturar tiempo actual del player' : 'Cargando player…'}
            onClick={captureStart}
          >
            ⏱ Capturar
          </button>
        </div>
        <div className="bm-dev-segment-add__row">
          <span className="bm-dev-segment-add__label">Fin</span>
          <input
            type="text"
            className="bm-dev-segment-add__input"
            placeholder="mm:ss"
            value={endVal}
            onChange={(e) => onFormChange({ ...formState, endVal: e.target.value })}
          />
          <button
            type="button"
            className="bm-dev-segment-add__capture"
            disabled={!playerReady}
            title={playerReady ? 'Capturar tiempo actual del player' : 'Cargando player…'}
            onClick={captureEnd}
          >
            ⏱ Capturar
          </button>
        </div>

        {isReadyToAdd && (
          <p className="bm-dev-segment-add__ready-hint">
            ↑ Pulsa <strong>«+ Añadir segmento»</strong> para guardar este tramo antes de confirmar.
          </p>
        )}

        {addError && (
          <p className="bm-caption" style={{ color: 'var(--bm-angle-bad)', margin: 0 }}>
            {addError}
          </p>
        )}

        <BmButton
          type="button"
          variant={isReadyToAdd ? 'primary' : 'outline'}
          onClick={handleAdd}
          style={{ alignSelf: 'flex-start' }}
          disabled={!hasPendingData && segments.length === 0 ? false : !hasPendingData && !isReadyToAdd}
        >
          + Añadir segmento
        </BmButton>
      </div>
    </>
  );
}
