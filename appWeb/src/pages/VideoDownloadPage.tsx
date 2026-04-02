import { useMemo } from 'react';
import { Link } from 'react-router-dom';
import { BmButton } from '../components/BmButton';
import { BmInput, BmSelect } from '../components/BmInput';
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
      <p className="bm-caption" style={{ marginBottom: 'var(--bm-space-md)' }}>
        Cola en servidor (yt-dlp).{' '}
        <Link to="/backend-status" style={{ color: 'var(--bm-accent)' }}>
          Estado del backend
        </Link>
      </p>
      <BmInput label="URL del vídeo" value={url} onChange={(e) => setUrl(e.target.value)} autoComplete="off" />
      <BmSelect label="Calidad" value={quality} onChange={(e) => setQuality(e.target.value)}>
        {qualities.map((q) => (
          <option key={q} value={q}>
            {q}
          </option>
        ))}
      </BmSelect>
      <div style={{ display: 'flex', gap: 'var(--bm-space-sm)', flexWrap: 'wrap' }}>
        <BmButton variant="primary" onClick={() => void enqueue()}>
          Encolar descarga
        </BmButton>
        {jobId ? (
          <BmButton variant="outline" onClick={() => void cleanup()}>
            Limpiar job
          </BmButton>
        ) : null}
      </div>
      {status && (
        <p className="bm-body" style={{ marginTop: 'var(--bm-space-md)' }}>
          Estado: <strong>{status}</strong>
          {jobId ? ` · job ${jobId}` : ''}
        </p>
      )}
      {error && <p className="bm-caption" style={{ color: 'var(--bm-angle-bad)', marginTop: 'var(--bm-space-sm)' }}>{error}</p>}
      {fileHref && (
        <p style={{ marginTop: 'var(--bm-space-md)' }}>
          <a href={fileHref} target="_blank" rel="noreferrer" style={{ color: 'var(--bm-accent)' }}>
            Abrir / descargar archivo
          </a>
        </p>
      )}
    </div>
  );
}
