import logging
import os
from pathlib import Path

import yt_dlp

log = logging.getLogger(__name__)


def download_video(url: str, output_dir: str, filename_template: str = "%(title)s.%(ext)s") -> str:
    """
    Descarga un video utilizando yt-dlp asegurando la mejor calidad posible de video y audio.
    Devuelve la ruta absoluta al archivo descargado.

    :param url: URL del video a descargar.
    :param output_dir: Directorio donde se guardará el video.
    :param filename_template: Plantilla para el nombre del archivo.
    :return: Ruta del archivo descargado.
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    outtmpl = os.path.join(output_dir, filename_template)

    ydl_opts = {
        'format': 'bestvideo+bestaudio/best',
        'merge_output_format': 'mp4',
        'outtmpl': outtmpl,
        'quiet': False,
        'noplaylist': True,
    }

    log.info("Iniciando descarga yt-dlp para URL: %s", url)

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            if not info_dict:
                raise ValueError("No se pudo extraer información del video.")

            # Preparar un output path esperado.
            # yt-dlp usa _outtmpl para el nombre final tras el proceso o info_dict['requested_downloads'][0]['filepath']
            filepath = info_dict.get('requested_downloads', [{}])[0].get('filepath')
            if not filepath:
                filepath = ydl.prepare_filename(info_dict)
                # Si se fusiona a mp4, a veces el archivo final cambia la extensión.
                base, _ = os.path.splitext(filepath)
                filepath = f"{base}.mp4"

            log.info("Descarga completada. Archivo en: %s", filepath)
            return filepath
    except Exception as e:
        log.error("Error descargando el video: %s", e)
        raise e
