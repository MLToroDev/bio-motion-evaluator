import { useMemo } from 'react';
import { Link } from 'react-router-dom';
import { useVideoDownload } from '../hooks/useVideoDownload';
import { readApiBase } from '../lib/prefs';

const qualities = ['best', '1080p', '720p', '480p', '360p', 'worst'];

export default function VideoDownloadPage() {
  const apiBase = useMemo(() => readApiBase(), []);
  const {
    url,
    setUrl,
    quality,
    setQuality,
    status,
    error,
    jobId,
    fileHref,
    enqueue,
    cleanup,
  } = useVideoDownload(apiBase);

  return (
    <div style={{ maxWidth: 560 }}>
      <h1 className="bm-screen-title">Descarga remota de vídeo</h1>
      <p className="bm-caption" style={{ marginBottom: 16 }}>
        Cola en servidor (yt-dlp).{' '}
        <Link to="/backend-status" style={{ color: 'var(--bm-accent)' }}>
          Estado del backend
        </Link>
      </p>
      <label className="field" style={{ display: 'block', marginBottom: 12 }}>
        <span>URL del vídeo</span>
        <input
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          style={{ width: '100%', padding: 8, marginTop: 4, borderRadius: 8, border: '1px solid var(--bm-border)', background: 'var(--bm-surface)', color: 'inherit' }}
        />
      </label>
      <label className="field" style={{ display: 'block', marginBottom: 16 }}>
        <span>Calidad</span>
        <select
          value={quality}
          onChange={(e) => setQuality(e.target.value)}
          style={{ width: '100%', padding: 8, marginTop: 4, borderRadius: 8 }}
        >
          {qualities.map((q) => (
            <option key={q} value={q}>
              {q}
            </option>
          ))}
        </select>
      </label>
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        <button type="button" className="primary" onClick={() => void enqueue()}>
          Encolar descarga
        </button>
        {jobId && (
          <button type="button" onClick={() => void cleanup()}>
            Limpiar job
          </button>
        )}
      </div>
      {status && (
        <p style={{ marginTop: 16 }}>
          Estado: <strong>{status}</strong>
          {jobId && ` · job ${jobId}`}
        </p>
      )}
      {error && <p style={{ color: 'var(--bm-angle-bad)', marginTop: 8 }}>{error}</p>}
      {fileHref && (
        <p style={{ marginTop: 12 }}>
          <a href={fileHref} target="_blank" rel="noreferrer" style={{ color: 'var(--bm-accent)' }}>
            Abrir / descargar archivo
          </a>
        </p>
      )}
    </div>
  );
}
