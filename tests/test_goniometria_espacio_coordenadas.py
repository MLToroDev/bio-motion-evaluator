# -*- coding: utf-8 -*-
"""
Pruebas de regresión del espacio de coordenadas del cálculo goniométrico.

Protegen la corrección documentada en ``docs/spec/goniometria-espacio-de-coordenadas.md``:
el ángulo debe calcularse sobre coordenadas **isótropas**. Calcularlo sobre los landmarks
normalizados de MediaPipe (``x`` dividido por el ancho, ``y`` por el alto) introduce un
sesgo sistemático de hasta ~32 grados en vídeo 16:9.
"""

from __future__ import annotations

import math

import pytest

from vision.biomechanics import (
    angulos_rodilla,
    escalar_a_isotropico,
    knee_angles_from_landmarks,
)

LEFT_HIP, LEFT_KNEE, LEFT_ANKLE = 23, 25, 27
RIGHT_HIP, RIGHT_KNEE, RIGHT_ANKLE = 24, 26, 28

ANCHO, ALTO = 1920, 1080
RELACION = ALTO / ANCHO  # 0.5625


def _pierna_metrica(theta_interno_deg: float) -> dict[str, tuple[float, float, float]]:
    """Terna cadera-rodilla-tobillo en metros, con ángulo interno conocido por construcción."""
    th = math.radians(theta_interno_deg)
    return {
        "rodilla": (0.0, 0.0, 0.0),
        "cadera": (0.0, 0.42, 0.0),
        "tobillo": (0.40 * math.sin(th), 0.40 * math.cos(th), 0.0),
    }


def _landmarks(puntos: dict[str, tuple[float, float, float]], escala_x: float,
               escala_y: float) -> list[dict[str, float]]:
    """Proyecta la pierna a landmarks aplicando escalas independientes por eje."""
    lms = [{"x": 0.0, "y": 0.0, "z": 0.0, "visibility": 1.0} for _ in range(33)]
    for nombre, idx in (("cadera", LEFT_HIP), ("rodilla", LEFT_KNEE), ("tobillo", LEFT_ANKLE)):
        x, y, z = puntos[nombre]
        lms[idx] = {"x": x * escala_x, "y": -y * escala_y, "z": z * escala_x,
                    "visibility": 1.0}
    for nombre, idx in (("cadera", RIGHT_HIP), ("rodilla", RIGHT_KNEE), ("tobillo", RIGHT_ANKLE)):
        x, y, z = puntos[nombre]
        lms[idx] = {"x": x * escala_x, "y": -y * escala_y, "z": z * escala_x,
                    "visibility": 1.0}
    return lms


@pytest.mark.parametrize("theta_interno", [30.0, 60.0, 120.0, 150.0])
def test_coordenadas_anisotropicas_deforman_el_angulo(theta_interno: float) -> None:
    """El defecto histórico: con ejes de distinta escala el ángulo sale mal."""
    puntos = _pierna_metrica(theta_interno)
    # Normalización de MediaPipe: x entre el ancho, y entre el alto.
    anisotropicos = _landmarks(puntos, escala_x=1.0 / ANCHO, escala_y=1.0 / ALTO)
    medido = knee_angles_from_landmarks(anisotropicos)["left_knee_flexion_angle_deg"]
    verdadero = 180.0 - theta_interno
    assert abs(medido - verdadero) > 5.0, (
        "se esperaba deformación apreciable con coordenadas anisótropas"
    )


@pytest.mark.parametrize("theta_interno", [30.0, 60.0, 90.0, 120.0, 150.0])
def test_escalado_isotropico_recupera_el_angulo_verdadero(theta_interno: float) -> None:
    """Corregir la relación de aspecto devuelve el ángulo exacto."""
    puntos = _pierna_metrica(theta_interno)
    anisotropicos = _landmarks(puntos, escala_x=1.0 / ANCHO, escala_y=1.0 / ALTO)
    corregidos = escalar_a_isotropico(anisotropicos, RELACION)
    medido = knee_angles_from_landmarks(corregidos)["left_knee_flexion_angle_deg"]
    assert medido == pytest.approx(180.0 - theta_interno, abs=1e-9)


@pytest.mark.parametrize("theta_interno", [30.0, 90.0, 150.0])
def test_coordenadas_metricas_recuperan_el_angulo_verdadero(theta_interno: float) -> None:
    """Sobre world_landmarks (metros, isótropos) el ángulo es exacto."""
    metricos = _landmarks(_pierna_metrica(theta_interno), escala_x=1.0, escala_y=1.0)
    medido = knee_angles_from_landmarks(metricos)["left_knee_flexion_angle_deg"]
    assert medido == pytest.approx(180.0 - theta_interno, abs=1e-9)


def test_angulos_rodilla_prefiere_world_landmarks() -> None:
    """Habiendo world_landmarks, se ignoran los normalizados aunque estén sesgados."""
    puntos = _pierna_metrica(120.0)
    normalizados = _landmarks(puntos, escala_x=1.0 / ANCHO, escala_y=1.0 / ALTO)
    metricos = _landmarks(puntos, escala_x=1.0, escala_y=1.0)
    resultado = angulos_rodilla(normalizados, metricos, RELACION)
    assert resultado["left_knee_flexion_angle_deg"] == pytest.approx(60.0, abs=1e-9)


def test_angulos_rodilla_corrige_aspecto_sin_world_landmarks() -> None:
    """Sin world_landmarks pero con relación de aspecto, se corrige antes de calcular."""
    puntos = _pierna_metrica(120.0)
    normalizados = _landmarks(puntos, escala_x=1.0 / ANCHO, escala_y=1.0 / ALTO)
    resultado = angulos_rodilla(normalizados, None, RELACION)
    assert resultado["left_knee_flexion_angle_deg"] == pytest.approx(60.0, abs=1e-9)


def test_angulos_rodilla_sin_fuente_devuelve_none() -> None:
    assert angulos_rodilla(None, None, None) is None
    assert angulos_rodilla([], None, None) is None


def test_escalar_a_isotropico_no_muta_la_entrada() -> None:
    """El escalado es puro: no debe alterar la lista original."""
    original = _landmarks(_pierna_metrica(90.0), escala_x=1.0 / ANCHO, escala_y=1.0 / ALTO)
    copia_y = original[LEFT_KNEE]["y"], original[LEFT_HIP]["y"]
    escalar_a_isotropico(original, RELACION)
    assert (original[LEFT_KNEE]["y"], original[LEFT_HIP]["y"]) == copia_y


def test_escalar_a_isotropico_ignora_relacion_invalida() -> None:
    original = _landmarks(_pierna_metrica(90.0), escala_x=1.0 / ANCHO, escala_y=1.0 / ALTO)
    assert escalar_a_isotropico(original, 0.0) is original
    assert escalar_a_isotropico(original, -1.0) is original


def test_ambas_piernas_se_corrigen_por_igual() -> None:
    """La corrección no puede favorecer a un lado: la asimetría espuria debe anularse."""
    puntos = _pierna_metrica(105.0)
    normalizados = _landmarks(puntos, escala_x=1.0 / ANCHO, escala_y=1.0 / ALTO)
    r = angulos_rodilla(normalizados, None, RELACION)
    izq = r["left_knee_flexion_angle_deg"]
    der = r["right_knee_flexion_angle_deg"]
    assert izq == pytest.approx(der, abs=1e-9)
    assert izq == pytest.approx(75.0, abs=1e-9)
