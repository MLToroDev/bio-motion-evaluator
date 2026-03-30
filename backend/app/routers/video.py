import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

log = logging.getLogger(__name__)

router = APIRouter(tags=["video"])


@router.websocket("/ws/video")
async def video_stream(ws: WebSocket) -> None:
    """
    WebSocket para recibir frames binarios (JPEG/RAW) desde IoT o el cliente.
    Responde con métricas ligeras por mensaje; amplía según tu protocolo.
    """
    await ws.accept()
    frames = 0
    bytes_in = 0
    try:
        while True:
            msg = await ws.receive()
            if "bytes" in msg and msg["bytes"] is not None:
                chunk = msg["bytes"]
                frames += 1
                bytes_in += len(chunk)
                await ws.send_json({"frames": frames, "last_chunk_bytes": len(chunk), "total_bytes": bytes_in})
            elif "text" in msg and msg["text"] is not None:
                await ws.send_json({"echo": msg["text"], "frames": frames})
            else:
                break
    except WebSocketDisconnect:
        log.info("WebSocket /ws/video desconectado; frames=%s bytes=%s", frames, bytes_in)
