import logging
import os
import shutil
from pathlib import Path

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
    """
    if quality not in ALLOWED_QUALITY:
        quality = "best"

    if quality == "worst":
        if has_ffmpeg:
            return "worstvideo+worstaudio/worst", "mp4"
        return "worst", None

    max_h = _QUALITY_HEIGHT.get(quality)
    if max_h is None:
        if has_ffmpeg:
            return "bestvideo+bestaudio/best", "mp4"
        return "best", None

    if has_ffmpeg:
        return (
            f"bestvideo[height<={max_h}]+bestaudio/best[height<={max_h}]/best",
            "mp4",
        )
    return f"best[height<={max_h}]/best", None


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
