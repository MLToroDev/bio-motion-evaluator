import logging
import os
import shutil
from pathlib import Path
from typing import Any, NamedTuple
from urllib.parse import urlparse

import yt_dlp

log = logging.getLogger(__name__)

ALLOWED_QUALITY = frozenset({"best", "1080p", "720p", "480p", "360p", "worst"})

# Altura máxima aproximada del vídeo (yt-dlp filtra por pista de vídeo).
_QUALITY_HEIGHT = {
    "best": None,
    "1080p": 1080,
    "720p": 720,
    "480p": 480,
    "360p": 360,
    "worst": None,
}


def _ffmpeg_on_path() -> bool:
    return shutil.which("ffmpeg") is not None


def _format_and_merge(*, has_ffmpeg: bool, quality: str) -> tuple[str, str | None]:
    """
    Devuelve (format_string, merge_output_format o None).
    Con ffmpeg se puede fusionar video+audio; sin ffmpeg solo formatos en un solo archivo.

    Se fuerza códec de vídeo H.264 (``vcodec^=avc1``) con fallback a "mejor disponible":
    la build de OpenCV/ffmpeg usada por el pipeline de pose (``opencv-python-headless``)
    no siempre trae decoders AV1/VP9 (dav1d/libaom), lo que hacía que
    ``VideoSource`` abriera el archivo pero leyera 0 frames en vídeos servidos por YouTube
    en AV1 (itags ~394-401) — incidencia detectada en la ronda de ingesta masiva
    (ver docs/spec/dev-learning-api.md).
    """
    if quality not in ALLOWED_QUALITY:
        quality = "best"

    if quality == "worst":
        if has_ffmpeg:
            return "worstvideo[vcodec^=avc1]+worstaudio/worstvideo+worstaudio/worst", "mp4"
        return "worst", None

    max_h = _QUALITY_HEIGHT.get(quality)
    if max_h is None:
        if has_ffmpeg:
            return "bestvideo[vcodec^=avc1]+bestaudio/bestvideo+bestaudio/best", "mp4"
        return "best", None

    if has_ffmpeg:
        return (
            f"bestvideo[height<={max_h}][vcodec^=avc1]+bestaudio"
            f"/bestvideo[height<={max_h}]+bestaudio"
            f"/best[height<={max_h}]/best",
            "mp4",
        )
    return f"best[height<={max_h}]/best", None


_YOUTUBE_HOSTS = frozenset(
    {
        "youtube.com",
        "m.youtube.com",
        "youtu.be",
        "youtube-nocookie.com",
    }
)


class PlayableStream(NamedTuple):
    """URL de media lista para OpenCV, sin archivo local."""

    url: str
    finite: bool
    is_live: bool
    duration_s: float | None
    title: str | None
    http_headers: dict[str, str] | None = None


def is_youtube_page_url(url: str) -> bool:
    """True si ``url`` es una página de YouTube (watch, shorts, youtu.be), no un RTSP/MP4 directo."""
    raw = (url or "").strip()
    if not raw:
        return False
    try:
        parsed = urlparse(raw)
    except ValueError:
        return False
    host = (parsed.hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    return host in _YOUTUBE_HOSTS


def normalize_youtube_url(url: str) -> str:
    """
    Quita tracking (``si``, ``feature``, …) y unifica ``youtu.be`` / shorts a ``watch?v=``.

    OpenCV no puede abrir una página HTML; yt-dlp sí, pero los query params de share
    a veces rompen extractores viejos. La forma canónica es más estable.
    """
    raw = (url or "").strip()
    if not raw or not is_youtube_page_url(raw):
        return raw
    try:
        parsed = urlparse(raw)
    except ValueError:
        return raw
    host = (parsed.hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    path = (parsed.path or "").strip("/")
    vid = ""
    if host == "youtu.be":
        vid = path.split("/")[0].split("?")[0]
    elif "/shorts/" in f"/{path}/" or path.startswith("shorts/"):
        parts = path.split("/")
        if "shorts" in parts:
            i = parts.index("shorts")
            if i + 1 < len(parts):
                vid = parts[i + 1]
    else:
        from urllib.parse import parse_qs

        qs = parse_qs(parsed.query)
        vid = (qs.get("v") or [""])[0]
        if not vid and path.startswith("embed/"):
            vid = path.split("/", 1)[-1].split("/")[0]
        if not vid and path.startswith("v/"):
            vid = path.split("/", 1)[-1].split("/")[0]
    vid = "".join(c for c in vid if c.isalnum() or c in "-_")
    if len(vid) < 6:
        return raw
    return f"https://www.youtube.com/watch?v={vid}"


def _stream_format_string(*, quality: str) -> str:
    """Selector yt-dlp para reproducción (solo vídeo H.264; OpenCV no necesita audio)."""
    if quality not in ALLOWED_QUALITY:
        quality = "720p"
    if quality == "worst":
        return "worst[vcodec^=avc1]/worstvideo[vcodec^=avc1]/worst"
    max_h = _QUALITY_HEIGHT.get(quality)
    if max_h is None:
        return (
            "best[vcodec^=avc1][ext=mp4]"
            "/best[vcodec^=avc1][protocol^=m3u8]"
            "/bestvideo[vcodec^=avc1]"
            "/best[vcodec^=avc1]/best"
        )
    return (
        f"best[height<={max_h}][vcodec^=avc1][ext=mp4]"
        f"/best[height<={max_h}][vcodec^=avc1][protocol^=m3u8]"
        f"/bestvideo[height<={max_h}][vcodec^=avc1]"
        f"/best[height<={max_h}][vcodec^=avc1]"
        f"/best[height<={max_h}]/best"
    )


def _http_headers_from(obj: dict[str, Any] | None) -> dict[str, str] | None:
    if not obj:
        return None
    raw = obj.get("http_headers")
    if not isinstance(raw, dict) or not raw:
        return None
    out: dict[str, str] = {}
    for k, v in raw.items():
        ks = str(k).strip()
        if not ks:
            continue
        out[ks] = str(v)
    return out or None


def pick_stream_url_from_info(info: dict[str, Any]) -> tuple[str, dict[str, str] | None]:
    """Elige la URL de vídeo (y cabeceras HTTP) de un ``extract_info`` sin descarga."""
    direct = info.get("url")
    if isinstance(direct, str) and direct.strip():
        vcodec = str(info.get("vcodec") or "none")
        if vcodec != "none":
            return direct.strip(), _http_headers_from(info)

    requested = info.get("requested_formats") or info.get("formats") or []
    if isinstance(requested, list):
        video_url = ""
        video_fmt: dict[str, Any] | None = None
        fallback = ""
        fallback_fmt: dict[str, Any] | None = None
        for fmt in requested:
            if not isinstance(fmt, dict):
                continue
            u = fmt.get("url")
            if not isinstance(u, str) or not u.strip():
                continue
            if not fallback:
                fallback = u.strip()
                fallback_fmt = fmt
            if str(fmt.get("vcodec") or "none") != "none":
                video_url = u.strip()
                video_fmt = fmt
                break
        if video_url:
            return video_url, _http_headers_from(video_fmt) or _http_headers_from(info)
        if fallback:
            return fallback, _http_headers_from(fallback_fmt) or _http_headers_from(info)

    if isinstance(direct, str) and direct.strip():
        return direct.strip(), _http_headers_from(info)
    raise ValueError("yt-dlp no devolvió una URL de reproducción de vídeo.")


def extract_playable_stream_url(page_url: str, *, quality: str = "720p") -> PlayableStream:
    """
    Resuelve una URL de página (p. ej. YouTube) a un stream HTTP(S) reproducible
    por OpenCV **sin descargar** el archivo. Prefiere H.264 (``avc1``).
    """
    raw = normalize_youtube_url((page_url or "").strip()) if is_youtube_page_url(page_url or "") else (
        page_url or ""
    ).strip()
    if not raw:
        raise ValueError("URL vacía.")

    fmt = _stream_format_string(quality=quality)
    ydl_opts: dict[str, Any] = {
        "format": fmt,
        "quiet": True,
        "noplaylist": True,
        "skip_download": True,
        "no_warnings": True,
    }
    log.info("Resolviendo stream yt-dlp (sin descarga) quality=%s fmt=%s", quality, fmt)
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(raw, download=False)
    except Exception as exc:
        log.error("Error resolviendo stream yt-dlp: %s", exc)
        raise

    if not isinstance(info, dict) or not info:
        raise ValueError("No se pudo extraer información del video.")

    playable, headers = pick_stream_url_from_info(info)
    is_live = bool(info.get("is_live"))
    duration_raw = info.get("duration")
    duration_s: float | None
    try:
        duration_s = float(duration_raw) if duration_raw is not None else None
        if duration_s is not None and duration_s <= 0:
            duration_s = None
    except (TypeError, ValueError):
        duration_s = None
    title = info.get("title")
    title_s = str(title).strip() if title else None
    finite = not is_live
    log.info(
        "Stream resuelto sin descarga: live=%s duration_s=%s title=%r",
        is_live,
        duration_s,
        (title_s or "")[:80],
    )
    return PlayableStream(
        url=playable,
        finite=finite,
        is_live=is_live,
        duration_s=duration_s,
        title=title_s,
        http_headers=headers,
    )


def resolve_playable_stream(url: str, *, quality: str = "720p") -> PlayableStream:
    """
    Si ``url`` es una página de YouTube, extrae el stream H.264 sin descargar.
    RTSP/HTTP(S) directos se devuelven tal cual (``finite=False``, cámara/PTZ).
    """
    raw = (url or "").strip()
    if not raw:
        raise ValueError("stream_url es obligatorio.")
    if is_youtube_page_url(raw):
        return extract_playable_stream_url(normalize_youtube_url(raw), quality=quality)
    return PlayableStream(url=raw, finite=False, is_live=False, duration_s=None, title=None)


def download_video(
    url: str,
    output_dir: str,
    filename_template: str = "%(title)s.%(ext)s",
    *,
    quality: str = "best",
) -> str:
    """
    Descarga un video utilizando yt-dlp.
    ``quality``: best | 1080p | 720p | 480p | 360p | worst

    :param url: URL del video a descargar.
    :param output_dir: Directorio donde se guardará el video.
    :param filename_template: Plantilla para el nombre del archivo.
    :return: Ruta absoluta al archivo descargado.
    """
    if quality not in ALLOWED_QUALITY:
        quality = "best"

    Path(output_dir).mkdir(parents=True, exist_ok=True)
    outtmpl = os.path.join(output_dir, filename_template)

    has_ff = _ffmpeg_on_path()
    fmt, merge_fmt = _format_and_merge(has_ffmpeg=has_ff, quality=quality)

    ydl_opts: dict = {
        "format": fmt,
        "outtmpl": outtmpl,
        "quiet": False,
        "noplaylist": True,
    }
    if merge_fmt:
        ydl_opts["merge_output_format"] = merge_fmt

    if has_ff:
        log.info("ffmpeg en PATH: calidad=%s formato=%s", quality, fmt)
    else:
        log.warning(
            "ffmpeg no en PATH: un solo archivo; calidad=%s formato=%s",
            quality,
            fmt,
        )

    log.info("Iniciando descarga yt-dlp para URL: %s", url)

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            if not info_dict:
                raise ValueError("No se pudo extraer información del video.")

            filepath = info_dict.get("filepath")
            if not filepath:
                downloads = info_dict.get("requested_downloads") or []
                if downloads:
                    filepath = downloads[-1].get("filepath")
            if not filepath:
                filepath = ydl.prepare_filename(info_dict)

            log.info("Descarga completada. Archivo en: %s", filepath)
            return filepath
    except Exception as e:
        log.error("Error descargando el video: %s", e)
        raise e
