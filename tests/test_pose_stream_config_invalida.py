"""
Configuración inicial inválida en ``/ws/pose-stream``.

El primer mensaje del cliente se valida con ``PoseStreamConfig.model_validate_json``.
Pydantic v2 señala tanto el JSON mal formado como los campos fuera de rango con
``ValidationError`` (no con ``json.JSONDecodeError``). El servidor debe cerrar la conexión
con el código 4000 en ambos casos, sin dejar escapar la excepción.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.main import app


@pytest.mark.parametrize(
    "mensaje",
    [
        pytest.param("{esto no es json", id="json-mal-formado"),
        pytest.param('{"source": "file", "target_fps": 1000}', id="target-fps-fuera-de-rango"),
        pytest.param('{"source": "satelite"}', id="fuente-desconocida"),
    ],
)
def test_configuracion_invalida_cierra_con_4000(mensaje: str) -> None:
    with TestClient(app) as cliente:
        with cliente.websocket_connect("/ws/pose-stream") as ws:
            ws.send_text(mensaje)
            with pytest.raises(WebSocketDisconnect) as cierre:
                ws.receive_text()
    assert cierre.value.code == 4000
