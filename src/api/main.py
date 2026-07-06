# -*- coding: utf-8 -*-
"""API REST del producto P1: promesa inteligente + escudo de riesgo (HU-13, D-39).

- Carga UNICA del artefacto y los lookups al arrancar (lifespan); 503 si faltan.
- POST /promise: motor Fase 2 -> pred_dias -> promesa = max(ceil(pred + margen_P90), 1).
- POST /predict/delivery-risk: escudo v2 (riesgo vs promesa P90); v1 opcional.
- Cada prediccion se anexa a logs/predictions.jsonl (puente API -> monitoreo, HU-16).

Ejecucion local:
    venv/Scripts/uvicorn src.api.main:app --reload      # Swagger en /docs

Umbrales y politica PROVISIONALES del artefacto D-38, pendientes del PO (Fase 0).
"""
from __future__ import annotations

import json
import os
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

import joblib
from fastapi import FastAPI, HTTPException

from src.api import schemas
from src.models.backtest_promesas_fase2 import simulate_promise_days
from src.models.train_fase2_regresion import clipped_predict
from src.serving.feature_builder import FeatureBuilder

ROOT = Path(__file__).resolve().parents[2]
RUTA_ARTEFACTO = Path(os.environ.get("PRODUCTO_JOBLIB", ROOT / "artifacts" / "producto_promesa_riesgo.joblib"))
RUTA_SERVING = Path(os.environ.get("SERVING_DIR", ROOT / "artifacts" / "serving"))
RUTA_LOGS = Path(os.environ.get("PREDICTIONS_LOG", ROOT / "logs" / "predictions.jsonl"))

NOTA_PROVISIONAL = "politica y umbrales del artefacto D-38, pendientes de confirmacion del PO (Fase 0)"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Carga artefacto + lookups UNA sola vez. Si fallan, la API vive pero responde 503."""
    app.state.bundle = None
    app.state.builder = None
    app.state.error_carga = None
    try:
        app.state.bundle = joblib.load(RUTA_ARTEFACTO)
        app.state.builder = FeatureBuilder(RUTA_SERVING)
        # Candado anti-divergencia contrato<->modelo al arrancar (fail-fast).
        fila, _ = app.state.builder.construir(
            {"precio_total": 1.0, "flete_total": 0.0, "n_items": 1,
             "customer_state": "SP", "timestamp": "2018-01-01T00:00:00", "dias_prometidos": 10}
        )
        FeatureBuilder.validar_contrato(fila, app.state.bundle)
        print(f"[api] artefacto {RUTA_ARTEFACTO.name} ({app.state.bundle['generado']}) "
              f"y lookups ({app.state.builder.manifest['nivel']}) cargados.")
    except Exception as exc:  # pragma: no cover - camino de arranque degradado
        app.state.error_carga = str(exc)
        print(f"[api] ERROR de carga: {exc} -> los endpoints responderan 503.")
    yield


app = FastAPI(
    title="Vertex Insights - Olist P1",
    description="Promesa inteligente (motor Fase 2) + escudo de riesgo (Fase 1). "
                "Contrato en docs/contrato_api.md. Decision D-39.",
    version="0.1.0-provisional",
    lifespan=lifespan,
)


# --------------------------------------------------------------------------- #
# Utilidades
# --------------------------------------------------------------------------- #
def _exigir_artefactos() -> tuple[dict, FeatureBuilder]:
    if app.state.bundle is None or app.state.builder is None:
        raise HTTPException(status_code=503,
                            detail=f"Artefactos no disponibles: {app.state.error_carga}")
    return app.state.bundle, app.state.builder


def _log_prediccion(registro: dict) -> None:
    """Anexa la prediccion al JSONL (best-effort: nunca rompe el request)."""
    try:
        RUTA_LOGS.parent.mkdir(parents=True, exist_ok=True)
        with open(RUTA_LOGS, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(registro, ensure_ascii=False, default=str) + "\n")
    except OSError:  # pragma: no cover
        pass


def _registro_base(endpoint: str, payload: dict, fila, flags: list[str], t0: float, bundle: dict) -> dict:
    return {
        "request_id": str(uuid.uuid4()),
        "ts": datetime.now().isoformat(timespec="seconds"),
        "endpoint": endpoint,
        "payload_cli": payload,
        "features_derivadas": {k: v for k, v in fila.iloc[0].items()},
        "flags_imputacion": flags,
        "model_version": bundle["generado"],
        "latency_ms": round((time.perf_counter() - t0) * 1000, 1),
    }


# --------------------------------------------------------------------------- #
# Endpoints
# --------------------------------------------------------------------------- #
@app.get("/health", response_model=schemas.HealthResponse)
def health() -> schemas.HealthResponse:
    """Verifica que la API esta viva y los artefactos cargados (Docker/K8s/LB)."""
    bundle, builder = _exigir_artefactos()
    return schemas.HealthResponse(
        status="ok",
        model_version=bundle["generado"],
        motor_feature_set=bundle["motor_feature_set"],
        politica=bundle["politica_recomendada"],
        escudo_umbral_v1=round(float(bundle["escudo_umbral"]), 4),
        escudo_umbral_v2=round(float(bundle["escudo_v2_umbral"]), 4),
        lookups_nivel=builder.manifest["nivel"],
        nota=NOTA_PROVISIONAL,
    )


@app.post("/promise", response_model=schemas.PromesaResponse)
def promise(req: schemas.PromesaRequest) -> schemas.PromesaResponse:
    """Promesa de entrega recomendada: motor -> pred_dias -> P90 (D-36/D-38)."""
    bundle, builder = _exigir_artefactos()
    t0 = time.perf_counter()
    payload = req.model_dump(mode="json")
    try:
        fila, flags = builder.construir(payload)
        pred = float(clipped_predict(bundle["motor"], fila[bundle["motor_features"]])[0])
        margen = float(bundle["margenes_val"][bundle["politica_recomendada"]])
        promesa = int(simulate_promise_days([pred], margen)[0])
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error interno del motor: {exc}") from exc

    registro = _registro_base("/promise", payload, fila, flags, t0, bundle)
    registro.update({"pred_dias": round(pred, 2), "promesa_dias": promesa,
                     "politica": bundle["politica_recomendada"]})
    _log_prediccion(registro)

    return schemas.PromesaResponse(
        pred_dias=round(pred, 2),
        promesa_dias=promesa,
        politica=bundle["politica_recomendada"],
        margenes_val={k: round(float(v), 2) for k, v in bundle["margenes_val"].items()},
        flags_imputacion=flags,
        model_version=bundle["generado"],
    )


@app.post("/predict/delivery-risk", response_model=schemas.RiesgoResponse)
def delivery_risk(req: schemas.RiesgoRequest) -> schemas.RiesgoResponse:
    """Riesgo de entrega tarde: escudo v2 (vs promesa P90); v1 opcional (D-38)."""
    bundle, builder = _exigir_artefactos()
    if req.dias_prometidos is None:
        # El escudo usa la promesa vigente como feature [t0]: sin ella no hay riesgo.
        raise HTTPException(status_code=422,
                            detail="dias_prometidos es obligatorio en /predict/delivery-risk "
                                   "(feature [t0] del escudo; ver docs/contrato_api.md).")
    t0 = time.perf_counter()
    payload = req.model_dump(mode="json", exclude={"incluir_v1"})
    try:
        fila, flags = builder.construir(payload)
        escudo = bundle["escudo"]
        x_cols = escudo["numeric_features"] + escudo["categorical_features"]
        p_v2 = float(bundle["escudo_v2_modelo"].predict_proba(fila[x_cols])[:, 1][0])
        umbral_v2 = float(bundle["escudo_v2_umbral"])

        v1 = None
        if req.incluir_v1:
            p_v1 = float(escudo["calibrador_isotonic"].predict(
                escudo["modelo_regresion"].predict(fila[x_cols]))[0])
            umbral_v1 = float(bundle["escudo_umbral"])
            v1 = schemas.EscudoV1(p_tarde=round(p_v1, 4),
                                  bandera_riesgo=p_v1 >= umbral_v1, umbral=round(umbral_v1, 4))
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error interno del escudo: {exc}") from exc

    registro = _registro_base("/predict/delivery-risk", payload, fila, flags, t0, bundle)
    registro.update({"p_tarde": round(p_v2, 4), "bandera_riesgo": bool(p_v2 >= umbral_v2),
                     "escudo": "v2"})
    _log_prediccion(registro)

    return schemas.RiesgoResponse(
        p_tarde=round(p_v2, 4),
        bandera_riesgo=p_v2 >= umbral_v2,
        umbral=round(umbral_v2, 4),
        escudo="v2",
        escudo_v1=v1,
        flags_imputacion=flags,
        model_version=bundle["generado"],
    )
