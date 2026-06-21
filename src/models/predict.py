"""Genera la tabla de predicciones de P1 desde el modelo serializado.

Carga `artifacts/modelo_p1.joblib` (Pipeline completo + umbrales + listas de
features) y produce, para cada orden de la tabla analítica, el riesgo de entrega
tardía y la predicción 0/1 en dos puntos de operación (balance F1 y alta
cobertura). Es la forma reproducible de regenerar la tabla de predicciones sin
re-entrenar: el CSV de salida es un artefacto (no se versiona; lo produce este
script bajo demanda).

Uso:
    python -m src.models.predict
    python src/models/predict.py --data data/processed/orders_p1_features.csv \
        --modelo artifacts/modelo_p1.joblib --output reports/predicciones_p1.csv
"""

from __future__ import annotations

import argparse
from pathlib import Path

import joblib
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA = ROOT / "data" / "processed" / "orders_p1_features.csv"
DEFAULT_MODELO = ROOT / "artifacts" / "modelo_p1.joblib"
DEFAULT_OUTPUT = ROOT / "reports" / "predicciones_p1.csv"


def predecir(data_path: Path, modelo_path: Path, output_path: Path) -> pd.DataFrame:
    """Aplica el modelo serializado a la tabla y escribe la tabla de predicciones."""
    bundle = joblib.load(modelo_path)
    modelo = bundle["modelo"]
    x_cols = bundle["numeric_features"] + bundle["categorical_features"]
    target = bundle["target"]
    umbral_f1 = bundle["umbral_f1"]
    umbral_cobertura = bundle["umbral_alta_cobertura"]

    df = pd.read_csv(data_path)
    proba = modelo.predict_proba(df[x_cols])[:, 1]

    out = pd.DataFrame(
        {
            "order_id": df["order_id"],
            "order_purchase_timestamp": df.get("order_purchase_timestamp"),
            "split": df.get("split"),
            "entrega_tarde_real": df.get(target),
            "proba_riesgo_tarde": proba.round(4),
            "pred_balance_f1": (proba >= umbral_f1).astype(int),
            "pred_alta_cobertura": (proba >= umbral_cobertura).astype(int),
        }
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(output_path, index=False, encoding="utf-8")
    print(f"Predicciones guardadas en: {output_path}  ({len(out):,} filas)")
    print(f"Umbrales -> balance_f1={umbral_f1:.3f}  alta_cobertura={umbral_cobertura:.3f}")
    print(f"Marcadas como riesgo (balance F1): {int(out['pred_balance_f1'].sum()):,}")
    return out


def parse_args():
    p = argparse.ArgumentParser(description="Genera la tabla de predicciones de P1 (entrega_tarde)")
    p.add_argument("--data", default=str(DEFAULT_DATA))
    p.add_argument("--modelo", default=str(DEFAULT_MODELO))
    p.add_argument("--output", default=str(DEFAULT_OUTPUT))
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    predecir(Path(args.data), Path(args.modelo), Path(args.output))
