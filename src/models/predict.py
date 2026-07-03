"""Genera la tabla de predicciones de P1 desde el modelo de riesgo serializado.

Carga `artifacts/modelo_riesgo_p1.joblib` (regresor de `dias_vs_promesa` + calibrador
isotónico a P(tarde) + puntos de operación) y produce, para cada orden de la tabla
analítica, la probabilidad calibrada de entrega tardía y la alerta 0/1 en el punto de
operación elegido (por defecto recall≈0.70). Es la forma reproducible de regenerar la
tabla de predicciones sin re-entrenar: el CSV de salida es un artefacto (no se versiona;
lo produce este script bajo demanda).

Nota: el modelo de riesgo lo genera `src/models/train_multimodelo.py` (Etapa 4
re-ejecutada). Reemplaza al antiguo `modelo_p1.joblib` (clasificador) — ver D-31/D-32.

Uso:
    python -m src.models.predict
    python src/models/predict.py --data data/processed/orders_features.csv \
        --modelo artifacts/modelo_riesgo_p1.joblib --output reports/predicciones_p1.csv \
        --punto recall_obj_70
"""

from __future__ import annotations

import argparse
from pathlib import Path

import joblib
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA = ROOT / "data" / "processed" / "orders_features.csv"
DEFAULT_MODELO = ROOT / "artifacts" / "modelo_riesgo_p1.joblib"
DEFAULT_OUTPUT = ROOT / "reports" / "predicciones_p1.csv"
DEFAULT_PUNTO = "recall_obj_70"  # punto de operación por defecto (alto recall)


def predecir(
    data_path: Path, modelo_path: Path, output_path: Path, punto: str = DEFAULT_PUNTO
) -> pd.DataFrame:
    """Aplica el modelo de riesgo (regresión calibrada) y escribe la tabla de predicciones."""
    bundle = joblib.load(modelo_path)
    reg = bundle["modelo_regresion"]
    iso = bundle["calibrador_isotonic"]
    x_cols = bundle["numeric_features"] + bundle["categorical_features"]
    target_bin = bundle["target_binario"]
    puntos = bundle["puntos_operacion"]
    if punto not in puntos:
        punto = next(iter(puntos))
    umbral = float(puntos[punto]["umbral"])

    df = pd.read_csv(data_path)
    proba = iso.predict(reg.predict(df[x_cols]))  # P(tarde) calibrada

    out = pd.DataFrame(
        {
            "order_id": df["order_id"],
            "order_purchase_timestamp": df.get("order_purchase_timestamp"),
            "split": df.get("split"),
            "entrega_tarde_real": df.get(target_bin),
            "proba_riesgo_tarde": proba.round(4),
            "pred_alerta": (proba >= umbral).astype(int),
        }
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(output_path, index=False, encoding="utf-8")
    print(f"Predicciones guardadas en: {output_path}  ({len(out):,} filas)")
    print(f"Punto de operación: {punto} (umbral={umbral:.4f})")
    print(f"Marcadas como riesgo: {int(out['pred_alerta'].sum()):,}")
    return out


def parse_args():
    p = argparse.ArgumentParser(description="Genera la tabla de predicciones de P1 (riesgo de entrega tardía)")
    p.add_argument("--data", default=str(DEFAULT_DATA))
    p.add_argument("--modelo", default=str(DEFAULT_MODELO))
    p.add_argument("--output", default=str(DEFAULT_OUTPUT))
    p.add_argument("--punto", default=DEFAULT_PUNTO)
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    predecir(Path(args.data), Path(args.modelo), Path(args.output), args.punto)
