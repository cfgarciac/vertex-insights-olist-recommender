# -*- coding: utf-8 -*-
"""Tests del scoring por CSV del dashboard (HU-15, D-39).

La logica es pura (src/dashboard/scoring.py) y recibe el `post` inyectado:
aqui se prueba con un stub, sin API ni Streamlit (CI-safe).
"""
import pandas as pd
import pytest

from src.dashboard import scoring


def post_stub(ruta: str, payload: dict) -> tuple[int, dict]:
    """Respuestas con la MISMA forma que la API real."""
    if ruta == "/promise":
        return 200, {"pred_dias": 10.0, "promesa_dias": 16, "politica": "P90",
                     "margenes_val": {"P90": 5.84}, "flags_imputacion": [],
                     "model_version": "stub"}
    if ruta == "/predict/delivery-risk":
        return 200, {"p_tarde": 0.42, "bandera_riesgo": True, "umbral": 0.3658,
                     "escudo": "v2", "escudo_v1": None, "flags_imputacion": [],
                     "model_version": "stub"}
    return 404, {"detail": "ruta desconocida"}


def test_plantilla_cumple_su_propio_contrato():
    assert scoring.validar_csv(scoring.PLANTILLA) == []


def test_validar_detecta_columnas_faltantes():
    df = pd.DataFrame({"precio_total": [10.0]})
    problemas = scoring.validar_csv(df)
    assert any("obligatorias" in p for p in problemas)


def test_validar_limite_de_filas():
    df = pd.concat([scoring.PLANTILLA] * 200, ignore_index=True)  # 600 filas
    assert any("maximo" in p for p in scoring.validar_csv(df))


def test_validar_avisa_columnas_desconocidas():
    df = scoring.PLANTILLA.assign(columna_rara=1)
    assert any("ignoradas" in p for p in scoring.validar_csv(df))


def test_construir_payload_omite_opcionales_vacios():
    fila = pd.Series({"precio_total": 50.0, "flete_total": 5.0, "n_items": 1,
                      "customer_state": " sp ", "timestamp": "2018-07-01T10:00:00",
                      "dias_prometidos": None, "seller_state": ""})
    payload = scoring.construir_payload(fila)
    assert payload["customer_state"] == "SP"
    assert "dias_prometidos" not in payload
    assert "seller_state" not in payload


def test_puntuar_lote_promesa_y_riesgo():
    resultados = scoring.puntuar_lote(scoring.PLANTILLA, post_stub)
    assert len(resultados) == 3
    assert (resultados["promesa_P90_dias"] == 16).all()
    # la plantilla trae dias_prometidos -> el riesgo se calcula para todas.
    assert resultados["alerta_riesgo"].all()
    assert "error" not in resultados.columns


def test_puntuar_lote_sin_dias_prometidos_solo_promesa():
    lote = scoring.PLANTILLA.drop(columns=["dias_prometidos"])
    resultados = scoring.puntuar_lote(lote, post_stub)
    assert "p_tarde_v2" not in resultados.columns
    assert (resultados["promesa_P90_dias"] == 16).all()


def test_puntuar_lote_reporta_progreso():
    avances = []
    scoring.puntuar_lote(scoring.PLANTILLA, post_stub, al_progresar=avances.append)
    assert avances == pytest.approx([1 / 3, 2 / 3, 1.0])


def test_puntuar_lote_registra_errores_de_api():
    def post_error(ruta, payload):
        return 503, {"detail": "artefacto no disponible"}
    resultados = scoring.puntuar_lote(scoring.PLANTILLA.head(1), post_error)
    assert "error" in resultados.columns
    assert "503" in resultados.loc[0, "error"]
