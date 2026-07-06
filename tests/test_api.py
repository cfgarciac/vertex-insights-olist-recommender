# -*- coding: utf-8 -*-
"""Tests de la API FastAPI (HU-13, D-39) con artefacto y lookups SINTETICOS.

Se parchean las rutas del modulo (RUTA_ARTEFACTO/RUTA_SERVING/RUTA_LOGS) antes
de abrir el TestClient: el lifespan carga entonces el bundle sintetico, igual
que en produccion cargaria el real. Asi el CI valida el contrato completo sin
necesitar los .joblib (gitignored).
"""
import json

import pytest
from fastapi.testclient import TestClient

import src.api.main as api_main

CUERPO_MINIMO = {
    "precio_total": 100.0,
    "flete_total": 15.0,
    "n_items": 2,
    "customer_state": "BA",
    "timestamp": "2018-07-10T14:30:00",
}


@pytest.fixture()
def cliente(monkeypatch, artefacto_sintetico, lookups_sinteticos, tmp_path):
    monkeypatch.setattr(api_main, "RUTA_ARTEFACTO", artefacto_sintetico)
    monkeypatch.setattr(api_main, "RUTA_SERVING", lookups_sinteticos)
    monkeypatch.setattr(api_main, "RUTA_LOGS", tmp_path / "predictions.jsonl")
    with TestClient(api_main.app) as c:
        yield c


def test_health_ok(cliente):
    r = cliente.get("/health")
    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo["status"] == "ok"
    assert cuerpo["model_version"] == "sintetico-tests"
    assert cuerpo["politica"] == "P90"
    assert "pendientes de confirmacion del PO" in cuerpo["nota"]


def test_promise_responde_y_loguea(cliente, tmp_path):
    r = cliente.post("/promise", json=CUERPO_MINIMO)
    assert r.status_code == 200
    cuerpo = r.json()
    # promesa = max(ceil(pred + margen_P90), 1): entero y > pred.
    assert isinstance(cuerpo["promesa_dias"], int)
    assert cuerpo["promesa_dias"] >= 1
    assert cuerpo["promesa_dias"] >= cuerpo["pred_dias"]
    assert cuerpo["politica"] == "P90"
    assert "seller_state:modal_train" in cuerpo["flags_imputacion"]
    # la prediccion quedo logueada en JSONL (puente API -> monitoreo).
    log = tmp_path / "predictions.jsonl"
    assert log.exists()
    registro = json.loads(log.read_text(encoding="utf-8").splitlines()[-1])
    assert registro["endpoint"] == "/promise"
    assert registro["promesa_dias"] == cuerpo["promesa_dias"]
    assert "features_derivadas" in registro


def test_delivery_risk_v2_y_v1(cliente):
    r = cliente.post("/predict/delivery-risk",
                     json={**CUERPO_MINIMO, "dias_prometidos": 20.0, "incluir_v1": True})
    assert r.status_code == 200
    cuerpo = r.json()
    assert 0.0 <= cuerpo["p_tarde"] <= 1.0
    assert cuerpo["escudo"] == "v2"
    assert cuerpo["bandera_riesgo"] == (cuerpo["p_tarde"] >= cuerpo["umbral"])
    assert cuerpo["escudo_v1"] is not None
    assert 0.0 <= cuerpo["escudo_v1"]["p_tarde"] <= 1.0


def test_delivery_risk_sin_v1_por_defecto(cliente):
    r = cliente.post("/predict/delivery-risk",
                     json={**CUERPO_MINIMO, "dias_prometidos": 20.0})
    assert r.status_code == 200
    assert r.json()["escudo_v1"] is None


def test_delivery_risk_sin_promesa_vigente_422(cliente):
    r = cliente.post("/predict/delivery-risk", json=CUERPO_MINIMO)
    assert r.status_code == 422
    assert "dias_prometidos" in r.json()["detail"]


def test_payload_invalido_422(cliente):
    r = cliente.post("/promise", json={"precio_total": -5})
    assert r.status_code == 422  # Pydantic: faltan campos y precio <= 0


def test_artefacto_ausente_503(monkeypatch, lookups_sinteticos, tmp_path):
    monkeypatch.setattr(api_main, "RUTA_ARTEFACTO", tmp_path / "no_existe.joblib")
    monkeypatch.setattr(api_main, "RUTA_SERVING", lookups_sinteticos)
    monkeypatch.setattr(api_main, "RUTA_LOGS", tmp_path / "predictions.jsonl")
    with TestClient(api_main.app) as c:
        assert c.get("/health").status_code == 503
        assert c.post("/promise", json=CUERPO_MINIMO).status_code == 503
