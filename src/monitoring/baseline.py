# -*- coding: utf-8 -*-
"""Baseline de referencia para el monitoreo de drift (HU-16, D-39).

Computa, SOLO con el split `train` (misma ventana point-in-time que los
lookups), la distribucion de referencia de cada feature del modelo y de los
scores, y la persiste en monitoring/drift_baseline.json. drift.py compara la
produccion (logs/predictions.jsonl) contra este baseline con PSI/KS/Chi2.

Esta es la UNICA pieza del monitoreo que no depende de la API (concesion al
SM en D-39): puede construirse en paralelo desde la Fase 1.

Uso:
    python -m src.monitoring.baseline
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = ROOT / "data" / "processed" / "orders_features.csv"
MONITORING_DIR = ROOT / "monitoring"

# Features vigiladas (las del escudo = superset de las del motor, 16 [t0]).
FEATURES_NUMERICAS = [
    "dias_prometidos", "dist_haversine_km", "ratio_flete", "precio_total",
    "flete_total", "n_items", "peso_total_g", "volumen_total_cm3",
    "tasa_vendedor", "mes_compra", "dia_semana_compra",
]
FEATURES_CATEGORICAS = [
    "customer_state", "seller_state", "categoria_principal",
    "mismo_estado", "sin_historial_vendedor",
]
N_BINS = 10          # deciles del train para PSI
MAX_CATEGORIAS = 30  # categorias explicitas; el resto se agrupa en __otros__
N_MUESTRA_KS = 5000  # muestra del train persistida para el test KS


def bins_baseline(serie: pd.Series, n_bins: int = N_BINS) -> tuple[list[float], list[float]]:
    """Bordes por deciles del train (+/- inf en extremos) y frecuencias relativas."""
    bordes = np.unique(np.quantile(serie.dropna(), np.linspace(0, 1, n_bins + 1)))
    bordes = bordes.astype(float)
    bordes[0], bordes[-1] = -np.inf, np.inf
    conteos, _ = np.histogram(serie.dropna(), bins=bordes)
    frecuencias = conteos / max(conteos.sum(), 1)
    return bordes.tolist(), frecuencias.tolist()


def frecuencias_categoricas(serie: pd.Series, max_cats: int = MAX_CATEGORIAS) -> dict[str, float]:
    """Frecuencias relativas de las categorias mas comunes (+ __otros__)."""
    vc = serie.astype(str).value_counts(normalize=True)
    top = vc.head(max_cats).to_dict()
    resto = float(vc.iloc[max_cats:].sum()) if len(vc) > max_cats else 0.0
    if resto > 0:
        top["__otros__"] = resto
    return {str(k): float(v) for k, v in top.items()}


def construir_baseline(df: pd.DataFrame) -> dict:
    train = df[df["split"] == "train"]
    if train.empty:
        raise ValueError("El dataset no tiene filas con split == 'train'.")

    numericas = {}
    for col in FEATURES_NUMERICAS:
        bordes, frecs = bins_baseline(train[col])
        muestra = train[col].dropna()
        muestra = muestra.sample(min(N_MUESTRA_KS, len(muestra)), random_state=42)
        numericas[col] = {
            "bordes": bordes,
            "frecuencias": frecs,
            "muestra_ks": [float(x) for x in muestra],
            "media": float(train[col].mean()),
            "mediana": float(train[col].median()),
        }

    categoricas = {col: frecuencias_categoricas(train[col]) for col in FEATURES_CATEGORICAS}

    # Scores de referencia: el propio train (target del motor y tasa de tardanza).
    bordes_dias, frecs_dias = bins_baseline(train["dias_entrega_real"])
    return {
        "generado": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "fuente": "data/processed/orders_features.csv (split train)",
        "ventana_train": {
            "desde": str(train["order_purchase_timestamp"].min()),
            "hasta": str(train["order_purchase_timestamp"].max()),
            "n_ordenes": int(len(train)),
        },
        "features_numericas": numericas,
        "features_categoricas": categoricas,
        "scores": {
            "dias_entrega_real_train": {"bordes": bordes_dias, "frecuencias": frecs_dias,
                                        "media": float(train["dias_entrega_real"].mean())},
            "tasa_entrega_tarde_train": float(train["entrega_tarde"].mean()),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Genera el baseline de drift (HU-16).")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    args = parser.parse_args()

    print(f"[1/2] Leyendo {args.input} ...")
    df = pd.read_csv(args.input, parse_dates=["order_purchase_timestamp"])
    baseline = construir_baseline(df)

    MONITORING_DIR.mkdir(parents=True, exist_ok=True)
    salida = MONITORING_DIR / "drift_baseline.json"
    with open(salida, "w", encoding="utf-8") as fh:
        json.dump(baseline, fh, ensure_ascii=False)
    print(f"[2/2] Baseline en {salida} | ventana train: "
          f"{baseline['ventana_train']['desde']} -> {baseline['ventana_train']['hasta']} "
          f"({baseline['ventana_train']['n_ordenes']} ordenes)")


if __name__ == "__main__":
    main()
