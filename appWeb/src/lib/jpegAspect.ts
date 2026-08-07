/**
 * Lee ancho/alto desde cabecera JPEG SOF sin decodificar píxeles
 * (equivalente a `_jpegAspectFromHeader` en `pose_stream_frame_applier.dart`).
 */
export function jpegAspectFromBase64(b64: string): number | null {
  try {
    const bin = atob(b64);
    const len = Math.min(bin.length, 256 * 1024);
    const bytes = new Uint8Array(len);
    for (let i = 0; i < len; i++) bytes[i] = bin.charCodeAt(i);
    return jpegAspectFromHeader(bytes);
  } catch {
    return null;
  }
}

export function jpegAspectFromHeader(bytes: Uint8Array): number | null {
  if (bytes.length < 4) return null;
  if (bytes[0] !== 0xff || bytes[1] !== 0xd8) return null;

  let i = 2;
  while (i + 3 < bytes.length) {
    if (bytes[i] !== 0xff) return null;
    const marker = bytes[i + 1];
    i += 2;

    if ((marker >= 0xd0 && marker <= 0xd9) || marker === 0x01) continue;
    if (i + 1 >= bytes.length) return null;
    const segLen = (bytes[i] << 8) | bytes[i + 1];
    if (segLen < 2) return null;

    const isSOF =
      marker >= 0xc0 && marker <= 0xcb && marker !== 0xc4 && marker !== 0xc8;

    if (isSOF) {
      if (i + 6 >= bytes.length) return null;
      const h = (bytes[i + 3] << 8) | bytes[i + 4];
      const w = (bytes[i + 5] << 8) | bytes[i + 6];
      if (h > 0 && w > 0) return w / h;
      return null;
    }

    i += segLen;
  }
  return null;
}
