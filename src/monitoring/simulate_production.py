# -*- coding: utf-8 -*-
"""Produccion simulada: rejuega el split test contra la API (HU-16, D-39).

Los datos son historicos de Kaggle (no hay trafico real), asi que la
"produccion" se simula rejugando ordenes del split `test` por el camino
completo de la API (contrato -> derivacion -> motor -> escudo -> log JSONL).
Ademas permite INDUCIR drift artificial para validar que el detector dispara
(criterio de aceptacion de HU-16).

Genera:
- logs/predictions.jsonl        (via la propia API; insumo de drift.py)
- monitoring/replay_resultados.csv  (prediccion + ground truth por orden;
  simula el join con etiquetas diferidas ~30d que consume performance.py)

Uso:
    python -m src.monitoring.simulate_production                # sin drift
    python -m src.monitoring.simulate_production --drift todo   # drift inducido
    (con --api http://host:8000 apunta a un servidor vivo; por defecto usa la
     app en memoria via TestClient, sin necesidad de levantar uvicorn)
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = ROOT / "data" / "processed" / "orders_features.csv"
SALIDA_REPLAY = ROOT / "monitoring" / "replay_resultados.csv"

# Redistribucion hacia Norte/Nordeste para el drift inducido de estados.
REMAPEO_NE = {"SP": "BA", "RJ": "CE", "MG": "PE", "PR": "PA", "RS": "MA", "SC": "AM"}


def aplicar_drift(df: pd.DataFrame, modo: str, rng: np.random.Generator) -> pd.DataFrame:
    """Transformaciones de drift inducido (documentadas en estrategia_monitoreo.md)."""
    out = df.copy()
    if modo in ("precios", "todo"):
        out["precio_total"] = out["precio_total"] * 1.5          # inflacion 50%
        out["flete_total"] = out["flete_total"] * 1.3
    if modo in ("estados", "todo"):
        mover = rng.random(len(out)) < 0.6                        # 60% remapeado
        out.loc[mover, "customer_state"] = (
            out.loc[mover, "customer_state"].map(REMAPEO_NE)
            .fillna(out.loc[mover, "customer_state"]))
    if modo in ("meses", "todo"):
        ts = pd.to_datetime(out["order_purchase_timestamp"]) + pd.DateOffset(months=5)
        out["order_purchase_timestamp"] = ts.astype(str)          # desplaza estacionalidad
    return out


def construir_payload(fila: pd.Series) -> dict:
    """Payload [CLI] del contrato + promesa vigente (para el escudo)."""
    return {
        "precio_total": float(fila["precio_total"]),
        "flete_total": float(fila["flete_total"]),
        "n_items": int(fila["n_items"]),
        "customer_state": str(fila["customer_state"]),
        "timestamp": str(fila["order_purchase_timestamp"]),
        # En produccion real Olist tambien conoce estos campos: van como overrides.
        "seller_state": str(fila["seller_state"]),
        "categoria_principal": str(fila["categoria_principal"]),
        "peso_total_g": float(fila["peso_total_g"]),
        "volumen_total_cm3": float(fila["volumen_total_cm3"]),
        "dias_prometidos": float(fila["dias_prometidos"]),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Replay del test contra la API (HU-16).")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--n", type=int, default=2000, help="Ordenes a rejugar (default 2000).")
    parser.add_argument("--drift", choices=["none", "precios", "estados", "meses", "todo"],
                        default="none", help="Drift inducido para validar el detector.")
    parser.add_argument("--api", default=None,
                        help="URL de una API viva (ej. http://localhost:8000). "
                             "Por defecto usa la app en memoria (TestClient).")
    args = parser.parse_args()

    rng = np.random.default_rng(42)
    df = pd.read_csv(args.input)
    test = df[df["split"] == "test"].sample(min(args.n, (df["split"] == "test").sum()),
                                            random_state=42)
    print(f"[1/3] Rejugando {len(test)} ordenes de test (drift={args.drift}) ...")
    test_sim = aplicar_drift(test, args.drift, rng)

    if args.api:
        import requests

        def post(ruta: str, payload: dict) -> dict:
            r = requests.post(f"{args.api}{ruta}", json=payload, timeout=15)
            r.raise_for_status()
            return r.json()
    else:
        from fastapi.testclient import TestClient

        from src.api.main import app

        cliente = TestClient(app)
        cliente.__enter__()  # dispara el lifespan (carga unica del artefacto)

        def post(ruta: str, payload: dict) -> dict:
            r = cliente.post(ruta, json=payload)
            r.raise_for_status()
            return r.json()

    registros = []
    for _, fila in test_sim.iterrows():
        payload = construir_payload(fila)
        promesa = post("/promise", payload)
        riesgo = post("/predict/delivery-risk", payload)
        registros.append({
            "order_id": fila["order_id"],
            "timestamp": payload["timestamp"],
            "pred_dias": promesa["pred_dias"],
            "promesa_dias": promesa["promesa_dias"],
            "p_tarde": riesgo["p_tarde"],
            "bandera_riesgo": riesgo["bandera_riesgo"],
            # Ground truth (en produccion real llega ~30 dias despues):
            "dias_entrega_real": float(fila["dias_entrega_real"]),
            "drift_inducido": args.drift,
        })
    print(f"[2/3] {len(registros)} ordenes servidas por la API "
          f"({'servidor ' + args.api if args.api else 'app en memoria'})")

    resultado = pd.DataFrame(registros)
    SALIDA_REPLAY.parent.mkdir(parents=True, exist_ok=True)
    resultado.to_csv(SALIDA_REPLAY, index=False)
    cumplidas = (resultado["dias_entrega_real"] <= resultado["promesa_dias"]).mean()
    print(f"[3/3] {SALIDA_REPLAY} | cumplimiento realizado={cumplidas:.2%} | "
          f"alertas escudo={resultado['bandera_riesgo'].mean():.2%}")
    print("      Siguiente: python -m src.monitoring.drift && python -m src.monitoring.performance")


if __name__ == "__main__":
    main()
