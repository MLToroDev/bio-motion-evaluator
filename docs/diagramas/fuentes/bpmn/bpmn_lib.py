"""
Mini-biblioteca para escribir BPMN 2.0 (semántica + BPMN DI) con maquetación en rejilla.

Cada elemento se ubica por (carril, columna, fila); las coordenadas y los puntos de paso
de los flujos se calculan aquí, de modo que el XML resultante abre en bpmn.io y en
Camunda Modeler sin retoques. Solo usa la biblioteca estándar.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from xml.sax.saxutils import escape, quoteattr

COL_W = 150  # ancho de columna
ROW_H = 130  # alto de fila dentro de un carril
POOL_LABEL_W = 30
LANE_LABEL_W = 30
MARGEN_X = 40  # margen interior antes de la primera columna
MARGEN_Y = 10
POOL_GAP = 60

TAMANO = {
    "task": (120, 90),
    "event": (36, 36),
    "gateway": (50, 50),
    "data": (36, 50),
}

TIPOS_TAREA = {"task", "userTask", "serviceTask", "sendTask", "receiveTask", "scriptTask", "manualTask"}
TIPOS_EVENTO = {"startEvent", "endEvent", "intermediateCatchEvent", "intermediateThrowEvent", "boundaryEvent"}
TIPOS_GATEWAY = {"exclusiveGateway", "parallelGateway", "eventBasedGateway", "inclusiveGateway"}


def _familia(tipo: str) -> str:
    if tipo in TIPOS_TAREA:
        return "task"
    if tipo in TIPOS_EVENTO:
        return "event"
    if tipo in TIPOS_GATEWAY:
        return "gateway"
    if tipo == "dataObjectReference":
        return "data"
    raise ValueError(tipo)


@dataclass
class Nodo:
    id: str
    tipo: str
    nombre: str
    carril: str
    col: float
    fila: float
    evento: str | None = None  # message | timer | error | terminate | signal
    bucle: bool = False
    adjunto_a: str | None = None  # boundaryEvent
    duracion: str | None = None  # timer: ISO 8601
    error_ref: str | None = None
    default: str | None = None
    entradas: list[str] = field(default_factory=list)
    salidas: list[str] = field(default_factory=list)
    datos_salida: list[str] = field(default_factory=list)
    datos_entrada: list[str] = field(default_factory=list)
    etiqueta: str = "abajo"  # abajo | arriba | derecha (eventos y compuertas)
    etiqueta_v: str = "derecha"  # posición física de la etiqueta en diagramas verticales
    # calculado
    x: float = 0
    y: float = 0
    w: float = 0
    h: float = 0

    @property
    def cx(self) -> float:
        return self.x + self.w / 2

    @property
    def cy(self) -> float:
        return self.y + self.h / 2


@dataclass
class Flujo:
    id: str
    origen: str
    destino: str
    nombre: str | None = None
    condicion: str | None = None
    puntos: list[tuple[float, float]] | None = None
    ruta: str = "auto"  # auto | abajo | arriba
    canal: float | None = None  # desplazamiento vertical del canal de retorno respecto del centro del origen
    salida: str | None = None  # forzar lado de salida: arriba | abajo | derecha
    entrada: str | None = None  # forzar lado de entrada: izquierda | arriba | abajo
    etiqueta_xy: tuple[float, float] | None = None
    etiqueta_en: str = "inicio"  # inicio | fin (tramo donde se rotula el flujo)
    pasillo: float | None = None  # corredor horizontal: desplazamiento vertical desde el centro del origen


@dataclass
class Mensaje:
    id: str
    origen: str
    destino: str
    nombre: str | None = None
    dx_origen: float = 0
    dx_destino: float = 0
    etiqueta_xy: tuple[float, float] | None = None
    etiqueta_lado: str = "derecha"  # derecha | izquierda (respecto del último tramo)


@dataclass
class Anotacion:
    id: str
    texto: str
    carril: str
    col: float
    fila: float
    ancho: float = 200
    alto: float = 60
    asociada_a: str | None = None
    dy: float = 0
    dx: float = 0


@dataclass
class Carril:
    id: str
    nombre: str
    filas: int


@dataclass
class Piscina:
    id: str
    nombre: str
    proceso: str
    carriles: list[Carril]
    nombre_proceso: str | None = None
    x: float = 0
    y: float = 0
    w: float = 0
    h: float = 0


class Diagrama:
    def __init__(self, id_def: str, nombre: str, columnas: int, *, col_w: float = COL_W,
                 row_h: float = ROW_H, tarea: tuple[float, float] = TAMANO["task"],
                 vertical: bool = False):
        # Con vertical=True la maquetación se hace igual (columna = avance del flujo,
        # fila = posición transversal) y se traspone al escribir el BPMN DI: el flujo
        # avanza de arriba abajo y las piscinas y carriles quedan en columnas.
        self.col_w, self.row_h, self.tarea, self.vertical = col_w, row_h, tarea, vertical
        self.id_def = id_def
        self.nombre = nombre
        self.columnas = columnas
        self.piscinas: list[Piscina] = []
        self.nodos: dict[str, Nodo] = {}
        self.flujos: list[Flujo] = []
        self.mensajes: list[Mensaje] = []
        self.anotaciones: list[Anotacion] = []
        self.errores: dict[str, str] = {}
        self.carril_de: dict[str, tuple[Piscina, Carril, float]] = {}
        self._n = 0

    # ---------------------------------------------------------------- construcción
    def piscina(self, id_: str, nombre: str, carriles: list[tuple[str, str, int]], nombre_proceso: str | None = None) -> None:
        self.piscinas.append(
            Piscina(id_, nombre, f"Proceso_{id_}", [Carril(*c) for c in carriles], nombre_proceso)
        )

    def nodo(self, id_: str, tipo: str, nombre: str, carril: str, col: float, fila: float = 0, **kw) -> Nodo:
        n = Nodo(id_, tipo, nombre, carril, col, fila, **kw)
        self.nodos[id_] = n
        return n

    def flujo(self, origen: str, destino: str, nombre: str | None = None, **kw) -> Flujo:
        self._n += 1
        f = Flujo(f"Flujo_{self._n:02d}", origen, destino, nombre, **kw)
        self.flujos.append(f)
        self.nodos[origen].salidas.append(f.id)
        self.nodos[destino].entradas.append(f.id)
        return f

    def mensaje(self, origen: str, destino: str, nombre: str | None = None, **kw) -> Mensaje:
        m = Mensaje(f"Mensaje_{len(self.mensajes) + 1:02d}", origen, destino, nombre, **kw)
        self.mensajes.append(m)
        return m

    def anotacion(self, id_: str, texto: str, carril: str, col: float, fila: float, **kw) -> Anotacion:
        a = Anotacion(id_, texto, carril, col, fila, **kw)
        self.anotaciones.append(a)
        return a

    def error(self, id_: str, nombre: str) -> str:
        self.errores[id_] = nombre
        return id_

    # ---------------------------------------------------------------- maquetación
    def _maquetar(self) -> None:
        y = 40.0
        ancho = POOL_LABEL_W + LANE_LABEL_W + MARGEN_X * 2 + self.columnas * self.col_w
        for p in self.piscinas:
            p.x, p.y, p.w = 40.0, y, ancho
            yc = y
            for c in p.carriles:
                alto = MARGEN_Y * 2 + c.filas * self.row_h
                self.carril_de[c.id] = (p, c, yc)
                yc += alto
            p.h = yc - y
            y = yc + POOL_GAP
        x0 = 40.0 + POOL_LABEL_W + LANE_LABEL_W + MARGEN_X
        for n in self.nodos.values():
            if n.adjunto_a:
                continue
            fam = _familia(n.tipo)
            n.w, n.h = self.tarea if fam == "task" else TAMANO[fam]
            if self.vertical and fam in ("task", "data"):
                n.w, n.h = n.h, n.w  # dimensiones lógicas (a lo largo del flujo, transversal)
            _, _, ytop = self.carril_de[n.carril]
            cx = x0 + n.col * self.col_w + self.col_w / 2
            cy = ytop + MARGEN_Y + n.fila * self.row_h + self.row_h / 2
            n.x, n.y = cx - n.w / 2, cy - n.h / 2
        for n in self.nodos.values():
            if n.adjunto_a:
                t = self.nodos[n.adjunto_a]
                n.w, n.h = TAMANO["event"]
                n.x = t.x + t.w - n.w - 8
                n.y = t.y + t.h - n.h / 2

    # Trasposición lógica -> física
    def _P(self, pts):
        return [(y, x) for x, y in pts] if self.vertical else list(pts)

    def _B(self, x, y, w, h):
        return (y, x, h, w) if self.vertical else (x, y, w, h)

    # Puntos de anclaje
    @staticmethod
    def _lado(n: Nodo, lado: str) -> tuple[float, float]:
        return {
            "izquierda": (n.x, n.cy),
            "derecha": (n.x + n.w, n.cy),
            "arriba": (n.cx, n.y),
            "abajo": (n.cx, n.y + n.h),
        }[lado]

    def _puntos(self, f: Flujo) -> list[tuple[float, float]]:
        if f.puntos:
            return f.puntos
        s, t = self.nodos[f.origen], self.nodos[f.destino]
        if f.pasillo is not None:
            p0 = self._lado(s, f.salida or ("arriba" if f.pasillo < 0 else "abajo"))
            p3 = self._lado(t, f.entrada or "izquierda")
            yp = s.cy + f.pasillo
            if f.entrada in ("arriba", "abajo"):
                return [p0, (p0[0], yp), (p3[0], yp), p3]
            return [p0, (p0[0], yp), (p3[0] - 20, yp), (p3[0] - 20, p3[1]), p3]
        es_gw_s = _familia(s.tipo) == "gateway"
        es_gw_t = _familia(t.tipo) == "gateway"
        if s.adjunto_a:  # evento de borde: sale hacia abajo
            p0 = self._lado(s, "abajo")
            p1 = self._lado(t, "izquierda") if t.cx > s.cx + 40 else self._lado(t, "arriba")
            if abs(p0[0] - p1[0]) < 1:
                return [p0, p1]
            return [p0, (p0[0], p1[1]), p1] if p1 == self._lado(t, "izquierda") else [p0, (p0[0], (p0[1] + p1[1]) / 2), (p1[0], (p0[1] + p1[1]) / 2), p1]
        if abs(t.cx - s.cx) < 1 and f.ruta == "auto":  # alineados en vertical
            return [self._lado(s, "abajo"), self._lado(t, "arriba")] if t.cy > s.cy else [self._lado(s, "arriba"), self._lado(t, "abajo")]
        if t.cx <= s.cx + 1 or f.ruta in ("abajo", "arriba"):
            # Retorno: por debajo (o por encima) hasta el destino.
            arriba = f.ruta == "arriba"
            lado_s = "arriba" if arriba else "abajo"
            p0 = self._lado(s, f.salida or lado_s)
            p3 = self._lado(t, f.entrada or lado_s)
            if f.canal is not None:
                yc = s.cy + f.canal
            else:
                yc = (max(s.y + s.h, t.y + t.h) + 25) if not arriba else (min(s.y, t.y) - 25)
            return [p0, (p0[0], yc), (p3[0], yc), p3]
        if abs(s.cy - t.cy) < 1 and not f.salida and not f.entrada:
            return [self._lado(s, "derecha"), self._lado(t, "izquierda")]
        if f.salida in ("arriba", "abajo") or (es_gw_s and not f.salida and not es_gw_t):
            lado = f.salida or ("abajo" if t.cy > s.cy else "arriba")
            p0 = self._lado(s, lado)
            if f.entrada in ("arriba", "abajo"):
                p3 = self._lado(t, f.entrada)
                ym = (p0[1] + p3[1]) / 2
                return [p0, (p0[0], ym), (p3[0], ym), p3]
            p3 = self._lado(t, "izquierda")
            return [p0, (p0[0], p3[1]), p3]
        if es_gw_t or f.entrada in ("arriba", "abajo"):
            lado = f.entrada or ("arriba" if s.cy < t.cy else "abajo")
            p0 = self._lado(s, "derecha")
            p3 = self._lado(t, lado)
            return [p0, (p3[0], p0[1]), p3]
        p0 = self._lado(s, "derecha")
        p3 = self._lado(t, "izquierda")
        xm = (p0[0] + p3[0]) / 2
        return [p0, (xm, p0[1]), (xm, p3[1]), p3]

    def _puntos_mensaje(self, m: Mensaje) -> list[tuple[float, float]]:
        s, t = self.nodos[m.origen], self.nodos[m.destino]
        hacia_abajo = t.cy > s.cy
        sx = s.cx + m.dx_origen
        tx = t.cx + m.dx_destino
        sy = s.y + s.h if hacia_abajo else s.y
        ty = t.y if hacia_abajo else t.y + t.h
        if abs(sx - tx) < 1:
            return [(sx, sy), (tx, ty)]
        # Codo en el hueco entre piscinas.
        ps = self.carril_de[s.carril][0]
        ym = (ps.y + ps.h + POOL_GAP / 2) if hacia_abajo else (ps.y - POOL_GAP / 2)
        return [(sx, sy), (sx, ym), (tx, ym), (tx, ty)]

    # ---------------------------------------------------------------- XML
    def xml(self) -> str:
        self._maquetar()
        L: list[str] = []
        a = L.append
        a('<?xml version="1.0" encoding="UTF-8"?>')
        a(
            '<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL" '
            'xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI" '
            'xmlns:dc="http://www.omg.org/spec/DD/20100524/DC" '
            'xmlns:di="http://www.omg.org/spec/DD/20100524/DI" '
            'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
            f'id={quoteattr(self.id_def)} name={quoteattr(self.nombre)} '
            'targetNamespace="https://bio-motion-evaluator/bpmn" '
            'exporter="bio-motion-evaluator generar_bpmn.py" exporterVersion="1.0">'
        )
        for eid, nombre in self.errores.items():
            a(f'  <bpmn:error id={quoteattr(eid)} name={quoteattr(nombre)} />')
        a(f'  <bpmn:collaboration id="Colab_{self.id_def}">')
        for p in self.piscinas:
            a(f'    <bpmn:participant id={quoteattr(p.id)} name={quoteattr(p.nombre)} processRef={quoteattr(p.proceso)} />')
        for m in self.mensajes:
            nm = f" name={quoteattr(m.nombre)}" if m.nombre else ""
            ref = ""
            a(f'    <bpmn:messageFlow id={quoteattr(m.id)}{nm} sourceRef={quoteattr(m.origen)} targetRef={quoteattr(m.destino)}{ref} />')
        for an in self.anotaciones:
            if self.carril_de[an.carril][0] is None:
                pass
        a("  </bpmn:collaboration>")

        for p in self.piscinas:
            carriles = {c.id for c in p.carriles}
            nodos = [n for n in self.nodos.values() if n.carril in carriles]
            ids = {n.id for n in nodos}
            nombre_proc = f" name={quoteattr(p.nombre_proceso)}" if p.nombre_proceso else ""
            a(f'  <bpmn:process id={quoteattr(p.proceso)}{nombre_proc} isExecutable="false">')
            if len(p.carriles) > 1 or p.carriles[0].nombre:
                a(f'    <bpmn:laneSet id="LaneSet_{p.id}">')
                for c in p.carriles:
                    a(f'      <bpmn:lane id={quoteattr(c.id)} name={quoteattr(c.nombre)}>')
                    for n in nodos:
                        if n.carril == c.id and n.tipo != "dataObjectReference":
                            a(f"        <bpmn:flowNodeRef>{n.id}</bpmn:flowNodeRef>")
                    a("      </bpmn:lane>")
                a("    </bpmn:laneSet>")
            for n in nodos:
                a(self._xml_nodo(n))
            for f in self.flujos:
                if f.origen in ids:
                    nm = f" name={quoteattr(f.nombre)}" if f.nombre else ""
                    if f.condicion:
                        a(f'    <bpmn:sequenceFlow id="{f.id}"{nm} sourceRef="{f.origen}" targetRef="{f.destino}">')
                        a(f'      <bpmn:conditionExpression xsi:type="bpmn:tFormalExpression">{escape(f.condicion)}</bpmn:conditionExpression>')
                        a("    </bpmn:sequenceFlow>")
                    else:
                        a(f'    <bpmn:sequenceFlow id="{f.id}"{nm} sourceRef="{f.origen}" targetRef="{f.destino}" />')
            for an in self.anotaciones:
                if an.carril in carriles:
                    a(f'    <bpmn:textAnnotation id={quoteattr(an.id)}><bpmn:text>{escape(an.texto)}</bpmn:text></bpmn:textAnnotation>')
                    if an.asociada_a:
                        a(f'    <bpmn:association id="Asoc_{an.id}" associationDirection="None" sourceRef="{an.asociada_a}" targetRef="{an.id}" />')
            a("  </bpmn:process>")

        # ------------------------------------------------------------ DI
        a(f'  <bpmndi:BPMNDiagram id="Diagrama_{self.id_def}" name={quoteattr(self.nombre)}>')
        a(f'    <bpmndi:BPMNPlane id="Plano_{self.id_def}" bpmnElement="Colab_{self.id_def}">')
        hz = "false" if self.vertical else "true"
        for p in self.piscinas:
            bx_, by_, bw_, bh_ = self._B(p.x, p.y, p.w, p.h)
            a(f'      <bpmndi:BPMNShape id="{p.id}_di" bpmnElement="{p.id}" isHorizontal="{hz}">')
            a(f'        <dc:Bounds x="{bx_:.0f}" y="{by_:.0f}" width="{bw_:.0f}" height="{bh_:.0f}" />')
            a("      </bpmndi:BPMNShape>")
            if len(p.carriles) > 1 or p.carriles[0].nombre:
                for c in p.carriles:
                    _, _, yt = self.carril_de[c.id]
                    alto = MARGEN_Y * 2 + c.filas * self.row_h
                    bx_, by_, bw_, bh_ = self._B(p.x + POOL_LABEL_W, yt, p.w - POOL_LABEL_W, alto)
                    a(f'      <bpmndi:BPMNShape id="{c.id}_di" bpmnElement="{c.id}" isHorizontal="{hz}">')
                    a(f'        <dc:Bounds x="{bx_:.0f}" y="{by_:.0f}" width="{bw_:.0f}" height="{bh_:.0f}" />')
                    a("      </bpmndi:BPMNShape>")
        for n in self.nodos.values():
            a(self._di_nodo(n))
        for f in self.flujos:
            pts = self._P(self._puntos(f))
            a(f'      <bpmndi:BPMNEdge id="{f.id}_di" bpmnElement="{f.id}">')
            for x, y in pts:
                a(f'        <di:waypoint x="{x:.0f}" y="{y:.0f}" />')
            if f.nombre:
                if f.etiqueta_xy:
                    lx, ly = f.etiqueta_xy
                elif f.etiqueta_en == "fin" and len(pts) >= 3:
                    lx, ly = pts[-2][0] + 8, pts[-2][1] - 18
                else:
                    lx, ly = self._pos_etiqueta_flujo(pts)
                    if self.vertical and abs(pts[0][1] - pts[1][1]) < 1:
                        ly = pts[0][1] + 4  # en vertical, bajo el tramo horizontal
                        if pts[1][0] < pts[0][0]:  # tramo hacia la izquierda
                            lx = pts[0][0] - 8 - 70
                a(f'        <bpmndi:BPMNLabel><dc:Bounds x="{lx:.0f}" y="{ly:.0f}" width="70" height="14" /></bpmndi:BPMNLabel>')
            a("      </bpmndi:BPMNEdge>")
        for m in self.mensajes:
            pts = self._P(self._puntos_mensaje(m))
            a(f'      <bpmndi:BPMNEdge id="{m.id}_di" bpmnElement="{m.id}">')
            for x, y in pts:
                a(f'        <di:waypoint x="{x:.0f}" y="{y:.0f}" />')
            if m.nombre:
                if m.etiqueta_xy:
                    lx, ly = m.etiqueta_xy
                elif self.vertical:
                    tx, ty = pts[-1]
                    px_, py_ = pts[-2]
                    if abs(py_ - ty) < 1:  # último tramo horizontal: rótulo encima, junto al destino
                        lx = tx - 96 if tx > px_ else tx + 6
                        ly = ty - 30
                    else:
                        lx, ly = tx + 6, (py_ + ty) / 2 - 13
                    if m.etiqueta_lado in ("origen", "origen-abajo"):
                        sx, sy = pts[0]
                        lx = sx + 6 if pts[1][0] > sx else sx - 96
                        ly = sy - 30 if m.etiqueta_lado == "origen" else sy + 4
                else:
                    tx, ty = pts[-1]
                    abajo = ty > pts[-2][1]
                    if abajo:  # junto al destino, por encima
                        lx = tx + 6 if m.etiqueta_lado == "derecha" else tx - 6 - 90
                        ly = ty - 34
                    else:  # junto al origen, por encima (el destino suele concentrar mensajes)
                        sx, sy = pts[0]
                        lx = sx + 6 if m.etiqueta_lado == "derecha" else sx - 6 - 90
                        ly = sy - 32
                a(f'        <bpmndi:BPMNLabel><dc:Bounds x="{lx:.0f}" y="{ly:.0f}" width="90" height="27" /></bpmndi:BPMNLabel>')
            a("      </bpmndi:BPMNEdge>")
        x0 = 40.0 + POOL_LABEL_W + LANE_LABEL_W + MARGEN_X
        for an in self.anotaciones:
            _, _, ytop = self.carril_de[an.carril]
            if self.vertical:  # dx/dy se interpretan en coordenadas físicas
                ay = x0 + an.col * self.col_w + an.dy
                ax = ytop + MARGEN_Y + an.fila * self.row_h + an.dx
            else:
                ax = x0 + an.col * self.col_w + an.dx
                ay = ytop + MARGEN_Y + an.fila * self.row_h + an.dy
            a(f'      <bpmndi:BPMNShape id="{an.id}_di" bpmnElement="{an.id}">')
            a(f'        <dc:Bounds x="{ax:.0f}" y="{ay:.0f}" width="{an.ancho:.0f}" height="{an.alto:.0f}" />')
            a("      </bpmndi:BPMNShape>")
            if an.asociada_a:
                n = self.nodos[an.asociada_a]
                nx, ny, nw, nh = self._B(n.x, n.y, n.w, n.h)
                if self.vertical and (ax >= nx + nw or ax + an.ancho <= nx):
                    # anotación a un lado: del borde lateral del elemento al de la caja
                    izq = ax + an.ancho <= nx
                    ex, ey = (nx if izq else nx + nw), ny + nh / 2
                    bx = ax + an.ancho if izq else ax
                    by = min(max(ey, ay), ay + an.alto)
                else:
                    # de la caja de la anotación al borde más cercano del elemento
                    ex, ey = nx + nw / 2, (ny if ay + an.alto <= ny else ny + nh)
                    bx = min(max(ex, ax), ax + an.ancho)
                    by = ay + an.alto if ay + an.alto <= ny else ay
                a(f'      <bpmndi:BPMNEdge id="Asoc_{an.id}_di" bpmnElement="Asoc_{an.id}">')
                a(f'        <di:waypoint x="{ex:.0f}" y="{ey:.0f}" />')
                a(f'        <di:waypoint x="{bx:.0f}" y="{by:.0f}" />')
                a("      </bpmndi:BPMNEdge>")
        a("    </bpmndi:BPMNPlane>")
        a("  </bpmndi:BPMNDiagram>")
        a("</bpmn:definitions>")
        return "\n".join(L) + "\n"

    @staticmethod
    def _pos_etiqueta_flujo(pts: list[tuple[float, float]]) -> tuple[float, float]:
        (x0, y0), (x1, y1) = pts[0], pts[1]
        if abs(y0 - y1) < 1:  # primer tramo horizontal
            return x0 + 8, y0 - 18
        return x0 + 6, (y0 + 4) if y1 > y0 else (y0 - 20)

    def _xml_nodo(self, n: Nodo) -> str:
        nm = f" name={quoteattr(n.nombre)}" if n.nombre else ""
        extra = ""
        if n.tipo == "boundaryEvent":
            extra += f' attachedToRef="{n.adjunto_a}"'
        if n.default:
            extra += f' default="{n.default}"'
        if n.tipo == "dataObjectReference":
            return (
                f'    <bpmn:dataObject id="DO_{n.id}" />\n'
                f'    <bpmn:dataObjectReference id="{n.id}"{nm} dataObjectRef="DO_{n.id}" />'
            )
        partes = [f"    <bpmn:{n.tipo} id=\"{n.id}\"{nm}{extra}>"]
        for i in n.entradas:
            partes.append(f"      <bpmn:incoming>{i}</bpmn:incoming>")
        for o in n.salidas:
            partes.append(f"      <bpmn:outgoing>{o}</bpmn:outgoing>")
        for k, d in enumerate(n.datos_entrada):
            partes.append(f'      <bpmn:property id="Prop_{n.id}_{k}" name="__targetRef_placeholder" />')
        for k, d in enumerate(n.datos_entrada):
            partes.append(
                f'      <bpmn:dataInputAssociation id="DIA_{n.id}_{k}"><bpmn:sourceRef>{d}</bpmn:sourceRef>'
                f"<bpmn:targetRef>Prop_{n.id}_{k}</bpmn:targetRef></bpmn:dataInputAssociation>"
            )
        for k, d in enumerate(n.datos_salida):
            partes.append(
                f'      <bpmn:dataOutputAssociation id="DOA_{n.id}_{k}"><bpmn:targetRef>{d}</bpmn:targetRef></bpmn:dataOutputAssociation>'
            )
        if n.bucle:
            partes.append(f'      <bpmn:standardLoopCharacteristics id="Bucle_{n.id}" />')
        if n.evento == "message":
            partes.append(f'      <bpmn:messageEventDefinition id="Def_{n.id}" />')
        elif n.evento == "timer":
            partes.append(
                f'      <bpmn:timerEventDefinition id="Def_{n.id}"><bpmn:timeDuration xsi:type="bpmn:tFormalExpression">'
                f"{escape(n.duracion or '')}</bpmn:timeDuration></bpmn:timerEventDefinition>"
            )
        elif n.evento == "error":
            ref = f' errorRef="{n.error_ref}"' if n.error_ref else ""
            partes.append(f'      <bpmn:errorEventDefinition id="Def_{n.id}"{ref} />')
        elif n.evento == "terminate":
            partes.append(f'      <bpmn:terminateEventDefinition id="Def_{n.id}" />')
        elif n.evento == "signal":
            partes.append(f'      <bpmn:signalEventDefinition id="Def_{n.id}" />')
        partes.append(f"    </bpmn:{n.tipo}>")
        return "\n".join(partes)

    def _di_nodo(self, n: Nodo) -> str:
        fam = _familia(n.tipo)
        extra = ' isMarkerVisible="true"' if n.tipo == "exclusiveGateway" else ""
        s = [f'      <bpmndi:BPMNShape id="{n.id}_di" bpmnElement="{n.id}"{extra}>']
        nx, ny, nw, nh = self._B(n.x, n.y, n.w, n.h)
        s.append(f'        <dc:Bounds x="{nx:.0f}" y="{ny:.0f}" width="{nw:.0f}" height="{nh:.0f}" />')
        if self.vertical and fam in ("event", "gateway", "data") and n.nombre:
            pos = n.etiqueta_v
            if pos == "izquierda":
                lx, ly = nx - 98, ny + nh / 2 - 14
            elif pos == "arriba":
                lx, ly = nx + nw / 2 - 45, ny - 32
            elif pos == "abajo-derecha":
                lx, ly = nx + nw + 2, ny + nh - 2
            elif pos == "arriba-derecha":
                lx, ly = nx + nw / 2 + 8, ny - 30
            elif pos == "abajo":
                lx, ly = nx + nw / 2 - 45, ny + nh + 4
            else:
                lx, ly = nx + nw + 4, ny + nh / 2 - 14
            s.append(f'        <bpmndi:BPMNLabel><dc:Bounds x="{lx:.0f}" y="{ly:.0f}" width="94" height="28" /></bpmndi:BPMNLabel>')
        elif fam in ("event", "gateway", "data") and n.nombre:
            lw = 110
            lh = 40
            if n.etiqueta == "arriba":
                lx, ly = n.cx - lw / 2, n.y - lh - 4
            elif n.etiqueta == "derecha":
                lx, ly = n.x + n.w + 4, n.cy - lh / 2 - 10
            elif n.etiqueta == "arriba-derecha":
                lx, ly = n.cx + 6, n.y - lh + 4
            elif n.etiqueta == "abajo-izquierda":
                lx, ly = n.x - lw - 2, n.y + n.h - 6
            elif n.etiqueta == "izquierda":
                lx, ly = n.x - lw - 4, n.cy - lh / 2
            else:
                lx, ly = n.cx - lw / 2, n.y + n.h + 4
            s.append(f'        <bpmndi:BPMNLabel><dc:Bounds x="{lx:.0f}" y="{ly:.0f}" width="{lw}" height="{lh}" /></bpmndi:BPMNLabel>')
        s.append("      </bpmndi:BPMNShape>")
        out = "\n".join(s)
        # Asociaciones de datos
        for k, d in enumerate(n.datos_salida):
            dn = self.nodos[d]
            p0 = (n.cx, n.y + n.h) if dn.cy > n.cy else (n.cx, n.y)
            p1 = (dn.cx, dn.y) if dn.cy > n.cy else (dn.cx, dn.y + dn.h)
            p0, p1 = self._P([p0, p1])
            out += (
                f'\n      <bpmndi:BPMNEdge id="DOA_{n.id}_{k}_di" bpmnElement="DOA_{n.id}_{k}">'
                f'\n        <di:waypoint x="{p0[0]:.0f}" y="{p0[1]:.0f}" />'
                f'\n        <di:waypoint x="{p1[0]:.0f}" y="{p1[1]:.0f}" />'
                "\n      </bpmndi:BPMNEdge>"
            )
        for k, d in enumerate(n.datos_entrada):
            dn = self.nodos[d]
            p0 = (dn.cx, dn.y) if dn.cy > n.cy else (dn.cx, dn.y + dn.h)
            p1 = (n.cx + 20, n.y + n.h) if dn.cy > n.cy else (n.cx + 20, n.y)
            p0, p1 = self._P([p0, p1])
            out += (
                f'\n      <bpmndi:BPMNEdge id="DIA_{n.id}_{k}_di" bpmnElement="DIA_{n.id}_{k}">'
                f'\n        <di:waypoint x="{p0[0]:.0f}" y="{p0[1]:.0f}" />'
                f'\n        <di:waypoint x="{p1[0]:.0f}" y="{p1[1]:.0f}" />'
                "\n      </bpmndi:BPMNEdge>"
            )
        return out
