"""Backtesting offline de promesas P80/P90/P95 para Fase 2.

Backtesting significa simular con datos historicos que habria pasado si una
politica se hubiera usado en ese momento. Este modulo reproduce el candidato
elegido en Chat E (`random_forest` + `M0_mas_seller_rolling`), calcula margenes
solo con `val` y evalua en `test` contra la promesa actual de Olist.

Uso:
    python -m src.models.backtest_promesas_fase2
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.models import evaluate_fase2_regresion as ev  # noqa: E402
from src.models import train_fase2_regresion as train_fase2  # noqa: E402


# --------------------------------------------------------------------------- #
# 0. Rutas y contrato
# --------------------------------------------------------------------------- #
TARGET = ev.TARGET
SELECTED_MODEL = "random_forest"
SELECTED_FEATURE_SET = "M0_mas_seller_rolling"
SPLIT_ORDER = ["train", "val", "test"]
POLICY_QUANTILES = {"P80": 0.80, "P90": 0.90, "P95": 0.95}
MIN_ROUTE_N = 80

DEFAULT_DATA = ROOT / "data" / "processed" / "orders_fase2_regresion_rolling.csv"
DEFAULT_INPUT_DIR = Path(
    r"C:\Users\LENOVO\Documents\Cursos\Soy Henry\PF\proyecto"
    r"\MLops_Pipeline_VERTEX\OLIST DATASETS"
)
DEFAULT_REPORT = ROOT / "reports" / "fase2_backtesting_promesas.md"
DEFAULT_METRICS = ROOT / "reports" / "fase2_backtesting_metrics.json"

RAW_ORDERS_FILE = "olist_orders_dataset.csv"
CURRENT_PROMISE_COL = "dias_prometidos_actual"


# --------------------------------------------------------------------------- #
# 1. Preparacion de datos y modelo
# --------------------------------------------------------------------------- #
def load_dataset(path: str | Path = DEFAULT_DATA) -> pd.DataFrame:
    """Carga el dataset rolling y valida que puede usarse para backtesting."""
    df = train_fase2.load_dataset(path)
    required = {
        "order_id",
        "split",
        "order_purchase_timestamp",
        TARGET,
        "customer_state",
        "ruta_estado",
        *selected_features(),
    }
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Faltan columnas requeridas para backtesting: {sorted(missing)}")
    ev.assert_no_forbidden_features(selected_features())
    if "seller_id" in selected_features():
        raise AssertionError("seller_id crudo no puede entrar al modelo de promesa")
    return df


def selected_features() -> list[str]:
    """Devuelve las features del candidato ganador de Chat E."""
    return list(train_fase2.FEATURE_SETS[SELECTED_FEATURE_SET])


def split_data(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Separa train, val y test con el split temporal ya calculado."""
    return train_fase2.split_data(df)


def train_selected_model(splits: dict[str, pd.DataFrame]):
    """Entrena el pipeline ganador solo con train y no guarda artefactos."""
    features = selected_features()
    candidates = train_fase2.build_model_candidates(features)
    model = candidates[SELECTED_MODEL]
    train = splits["train"]
    model.fit(train[features], train[TARGET])
    return model


def add_model_predictions(
    splits: dict[str, pd.DataFrame],
    model: Any,
    prediction_col: str = "prediccion_dias",
) -> pd.DataFrame:
    """Genera predicciones para train, val y test con el modelo ya entrenado."""
    frames = []
    features = selected_features()
    for split in SPLIT_ORDER:
        split_df = splits[split].copy()
        split_df[prediction_col] = train_fase2.clipped_predict(model, split_df[features])
        frames.append(split_df)
    return pd.concat(frames, ignore_index=True)


# --------------------------------------------------------------------------- #
# 2. Politicas de promesa
# --------------------------------------------------------------------------- #
def calculate_residual_margins(
    val_df: pd.DataFrame,
    target_col: str = TARGET,
    prediction_col: str = "prediccion_dias",
) -> dict[str, float]:
    """Calcula margenes P80/P90/P95 usando solo residual de validacion."""
    residual = val_df[target_col].to_numpy(dtype="float64") - val_df[
        prediction_col
    ].to_numpy(dtype="float64")
    return {
        policy: float(np.quantile(residual, quantile))
        for policy, quantile in POLICY_QUANTILES.items()
    }


def simulate_promise_days(
    predictions: Iterable[float], margin: float, minimum_days: int = 1
) -> np.ndarray:
    """Convierte prediccion + margen en dias prometidos enteros."""
    promised = np.ceil(np.asarray(predictions, dtype="float64") + margin)
    return np.maximum(promised, minimum_days).astype("int64")


def add_simulated_promises(
    df: pd.DataFrame,
    margins: dict[str, float],
    prediction_col: str = "prediccion_dias",
) -> pd.DataFrame:
    """Agrega columnas de promesa simulada para cada politica."""
    output = df.copy()
    for policy, margin in margins.items():
        output[f"promesa_{policy}"] = simulate_promise_days(
            output[prediction_col], margin
        )
    return output


def load_current_promises(input_dir: str | Path = DEFAULT_INPUT_DIR) -> pd.DataFrame:
    """Reconstruye dias prometidos actuales desde fechas crudas de Olist."""
    orders_path = Path(input_dir) / RAW_ORDERS_FILE
    if not orders_path.exists():
        raise FileNotFoundError(f"No se encontro la tabla de ordenes: {orders_path}")

    orders = pd.read_csv(
        orders_path,
        usecols=[
            "order_id",
            "order_purchase_timestamp",
            "order_estimated_delivery_date",
        ],
        parse_dates=["order_purchase_timestamp", "order_estimated_delivery_date"],
    )
    promised_days = (
        orders["order_estimated_delivery_date"] - orders["order_purchase_timestamp"]
    ).dt.total_seconds() / 86400.0
    orders[CURRENT_PROMISE_COL] = np.maximum(np.ceil(promised_days), 1).astype("int64")
    return orders[["order_id", CURRENT_PROMISE_COL]]


def add_current_promises(
    df: pd.DataFrame, input_dir: str | Path = DEFAULT_INPUT_DIR
) -> pd.DataFrame:
    """Une la promesa actual solo para evaluacion, no para el modelo."""
    if CURRENT_PROMISE_COL in df.columns:
        return df.copy()
    current = load_current_promises(input_dir)
    output = df.merge(current, on="order_id", how="left")
    missing = output[CURRENT_PROMISE_COL].isna().sum()
    if missing:
        raise AssertionError(f"Ordenes sin promesa actual reconstruida: {missing}")
    output[CURRENT_PROMISE_COL] = output[CURRENT_PROMISE_COL].astype("int64")
    return output


# --------------------------------------------------------------------------- #
# 3. Metricas de backtesting
# --------------------------------------------------------------------------- #
def promise_metrics(
    df: pd.DataFrame,
    promise_col: str,
    current_col: str | None = CURRENT_PROMISE_COL,
    target_col: str = TARGET,
) -> dict[str, float]:
    """Calcula cumplimiento, incumplimiento, colchon y promesa promedio."""
    promised = df[promise_col].to_numpy(dtype="float64")
    actual = df[target_col].to_numpy(dtype="float64")
    cushion = promised - actual
    fulfilled = actual <= promised

    metrics = {
        "ordenes": int(len(df)),
        "cumplimiento": float(np.mean(fulfilled)),
        "incumplimiento": float(1.0 - np.mean(fulfilled)),
        "colchon_promedio": float(np.mean(cushion)),
        "colchon_mediano": float(np.median(cushion)),
        "colchon_p10": float(np.quantile(cushion, 0.10)),
        "colchon_p90": float(np.quantile(cushion, 0.90)),
        "promesa_promedio": float(np.mean(promised)),
        "promesa_mediana": float(np.median(promised)),
    }
    if current_col is not None and current_col in df.columns:
        current = df[current_col].to_numpy(dtype="float64")
        current_cushion = current - actual
        current_fulfilled = actual <= current
        metrics.update(
            {
                "dif_promesa_promedio_vs_actual": float(np.mean(promised - current)),
                "dif_promesa_mediana_vs_actual": float(np.median(promised - current)),
                "dif_cumplimiento_vs_actual": float(
                    np.mean(fulfilled) - np.mean(current_fulfilled)
                ),
                "dif_colchon_promedio_vs_actual": float(
                    np.mean(cushion) - np.mean(current_cushion)
                ),
            }
        )
    return metrics


def evaluate_policies(df: pd.DataFrame, split: str = "test") -> list[dict[str, Any]]:
    """Evalua promesa actual y politicas P80/P90/P95 en un split."""
    split_df = df[df["split"] == split].copy()
    policy_cols = {"actual_olist": CURRENT_PROMISE_COL}
    policy_cols.update({policy: f"promesa_{policy}" for policy in POLICY_QUANTILES})

    rows = []
    for policy, col in policy_cols.items():
        rows.append({"split": split, "politica": policy, **promise_metrics(split_df, col)})
    return rows


def evaluate_by_group(
    df: pd.DataFrame,
    group_col: str,
    split: str = "test",
    min_n: int = 100,
) -> list[dict[str, Any]]:
    """Evalua politicas por grupo con volumen minimo."""
    split_df = df[df["split"] == split].copy()
    rows = []
    policy_cols = {"actual_olist": CURRENT_PROMISE_COL}
    policy_cols.update({policy: f"promesa_{policy}" for policy in POLICY_QUANTILES})
    for group_value, group in split_df.groupby(group_col, dropna=False):
        if len(group) < min_n:
            continue
        for policy, col in policy_cols.items():
            rows.append(
                {
                    group_col: group_value,
                    "split": split,
                    "politica": policy,
                    **promise_metrics(group, col),
                }
            )
    return rows


def model_metrics_by_split(df: pd.DataFrame) -> dict[str, dict[str, float]]:
    """Resume MAE/bias del modelo reproducido para trazabilidad."""
    return ev.evaluate_predictions_by_split(df, "prediccion_dias", target=TARGET)


# --------------------------------------------------------------------------- #
# 4. Reporte
# --------------------------------------------------------------------------- #
def _fmt(value: Any, digits: int = 3) -> str:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return "NA"
    if isinstance(value, (float, np.floating)):
        return f"{float(value):,.{digits}f}"
    if isinstance(value, (int, np.integer)):
        return f"{int(value):,}"
    return str(value)


def to_markdown(rows: list[dict[str, Any]] | pd.DataFrame, digits: int = 3) -> str:
    """Convierte filas a tabla Markdown compacta."""
    df = pd.DataFrame(rows) if isinstance(rows, list) else rows.copy()
    if df.empty:
        return "_Sin filas._"
    headers = list(df.columns)
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for _, row in df.iterrows():
        lines.append("| " + " | ".join(_fmt(row[col], digits) for col in headers) + " |")
    return "\n".join(lines)


def _compact_policy_table(rows: list[dict[str, Any]]) -> pd.DataFrame:
    cols = [
        "politica",
        "ordenes",
        "cumplimiento",
        "incumplimiento",
        "colchon_promedio",
        "colchon_mediano",
        "colchon_p10",
        "colchon_p90",
        "promesa_promedio",
        "promesa_mediana",
        "dif_promesa_promedio_vs_actual",
        "dif_cumplimiento_vs_actual",
    ]
    df = pd.DataFrame(rows)[cols].copy()
    for col in ["cumplimiento", "incumplimiento", "dif_cumplimiento_vs_actual"]:
        df[col] = df[col] * 100
    return df


def _comparison_group_table(
    rows: list[dict[str, Any]],
    group_col: str,
    candidate_policy: str = "P90",
    top_n: int = 15,
) -> pd.DataFrame:
    """Compara promesa actual contra una politica candidata por grupo."""
    df = pd.DataFrame(rows)
    actual = df[df["politica"] == "actual_olist"].copy()
    candidate = df[df["politica"] == candidate_policy].copy()
    merged = actual.merge(
        candidate,
        on=group_col,
        suffixes=("_actual", f"_{candidate_policy.lower()}"),
    )
    out = pd.DataFrame(
        {
            group_col: merged[group_col],
            "ordenes": merged["ordenes_actual"].astype("int64"),
            "cumpl_actual_pct": merged["cumplimiento_actual"] * 100,
            f"cumpl_{candidate_policy.lower()}_pct": merged[
                f"cumplimiento_{candidate_policy.lower()}"
            ]
            * 100,
            "promesa_actual": merged["promesa_promedio_actual"],
            f"promesa_{candidate_policy.lower()}": merged[
                f"promesa_promedio_{candidate_policy.lower()}"
            ],
            "dif_promesa_dias": merged[
                f"promesa_promedio_{candidate_policy.lower()}"
            ]
            - merged["promesa_promedio_actual"],
            "colchon_actual": merged["colchon_promedio_actual"],
            f"colchon_{candidate_policy.lower()}": merged[
                f"colchon_promedio_{candidate_policy.lower()}"
            ],
        }
    )
    return out.sort_values(
        [f"cumpl_{candidate_policy.lower()}_pct", "ordenes"],
        ascending=[True, False],
    ).head(top_n)


def _best_candidate(rows: list[dict[str, Any]]) -> str:
    """Elige recomendacion interpretativa sin recalibrar con test."""
    by_policy = {row["politica"]: row for row in rows}
    p90 = by_policy["P90"]
    return (
        "P90 queda como politica candidata para discusion: reduce fuerte el "
        "colchon frente a Olist actual y mantiene una zona de cumplimiento "
        f"simulada de {p90['cumplimiento'] * 100:.1f}% en test. P80 es mas "
        "competitiva si negocio acepta mas incumplimiento; P95 es la opcion "
        "conservadora si se prioriza confiabilidad."
    )


def make_report(
    dataset_path: Path,
    metrics: dict[str, Any],
) -> str:
    """Renderiza el reporte Markdown del backtesting."""
    general = _compact_policy_table(metrics["test_policy_metrics"])
    state_comparison = _comparison_group_table(
        metrics["test_by_customer_state"], "customer_state"
    )
    route_comparison = _comparison_group_table(
        metrics["test_by_ruta_estado"], "ruta_estado"
    )
    margins = pd.DataFrame(
        [{"politica": k, "margen_dias_val": v} for k, v in metrics["margins_val"].items()]
    )
    model_rows = pd.DataFrame(
        [{"split": split, **values} for split, values in metrics["model_metrics"].items()]
    )

    lines: list[str] = []
    lines.append("# Fase 2 - Backtesting offline de promesas P80/P90/P95")
    lines.append("")
    lines.append("## 1. Resumen ejecutivo")
    lines.append("")
    lines.append(
        "Se simularon promesas de entrega con el modelo elegido en Chat E. "
        "Backtesting significa probar una politica en datos historicos como si "
        "hubiera estado activa en ese momento."
    )
    lines.append("")
    lines.append(_best_candidate(metrics["test_policy_metrics"]))
    lines.append("")
    lines.append("## 2. Modelo usado")
    lines.append("")
    lines.append(f"- Dataset: `{dataset_path}`")
    lines.append(f"- Modelo reproducido: `{SELECTED_MODEL}`")
    lines.append(f"- Feature set: `{SELECTED_FEATURE_SET}`")
    lines.append("- Entrenamiento: solo split `train`.")
    lines.append("- Politicas/margenes: calculados solo con split `val`.")
    lines.append("- Evaluacion final: split `test`.")
    lines.append("- No se guardo modelo `.joblib`.")
    lines.append("")
    lines.append(to_markdown(model_rows))
    lines.append("")
    lines.append("## 3. Margenes P80/P90/P95")
    lines.append("")
    lines.append(
        "El residual usado fue `dias_entrega_real - prediccion_dias`. Si el "
        "residual es positivo, el modelo se quedo corto; por eso se agrega como "
        "margen. La promesa simulada fue `ceil(prediccion + margen)`, con minimo "
        "de 1 dia."
    )
    lines.append("")
    lines.append(to_markdown(margins))
    lines.append("")
    lines.append("## 4. Comparacion general en test")
    lines.append("")
    lines.append(
        "Cumplimiento es el porcentaje de ordenes donde `dias_entrega_real <= "
        "dias_prometidos`. Colchon es `dias_prometidos - dias_entrega_real`: "
        "positivo significa que la promesa sobro, negativo que se incumplio."
    )
    lines.append("")
    lines.append(to_markdown(general))
    lines.append("")
    lines.append("## 5. Resultados por estado destino")
    lines.append("")
    lines.append(
        "Se reportan estados con volumen suficiente en test. La tabla compacta "
        "compara la promesa actual contra P90 para enfocar la lectura regional. "
        "El JSON conserva todas las politicas por estado."
    )
    lines.append("")
    lines.append(to_markdown(state_comparison, digits=3))
    lines.append("")
    lines.append("## 6. Resultados por ruta estado-estado")
    lines.append("")
    lines.append(
        f"Se incluyen rutas con al menos {MIN_ROUTE_N} ordenes en test. Las rutas "
        "de menor cumplimiento ayudan a ubicar donde una politica candidata "
        "necesitaria monitoreo. El JSON conserva todas las politicas por ruta."
    )
    lines.append("")
    lines.append(to_markdown(route_comparison, digits=3))
    lines.append("")
    lines.append("## 7. Lectura de negocio")
    lines.append("")
    lines.append(
        "- P80 prioriza competitividad: acorta mas la promesa, pero acepta mas "
        "riesgo de incumplimiento."
    )
    lines.append(
        "- P90 es el balance inicial: conserva una tasa alta de cumplimiento "
        "simulado y reduce colchon frente a la promesa historica."
    )
    lines.append(
        "- P95 prioriza confiabilidad: se acerca mas a una promesa conservadora, "
        "con mayor colchon visible."
    )
    lines.append(
        "- La promesa actual de Olist sigue siendo el punto de comparacion; este "
        "backtesting no mide conversion, abandono de carrito, recompra ni costos."
    )
    lines.append("")
    lines.append("## 8. Riesgos y limitaciones")
    lines.append("")
    lines.append("- Test no se uso para definir margenes ni elegir politica final.")
    lines.append("- El modelo sobreestima dias en test, lo que aumenta colchon en algunas rutas.")
    lines.append("- La comparacion usa dias prometidos reconstruidos desde fechas estimadas crudas.")
    lines.append("- La simulacion offline no prueba impacto real en comportamiento de clientes.")
    lines.append("- Antes de produccion harian falta calibracion operacional, monitoreo y costos.")
    lines.append("")
    lines.append("## 9. Recomendacion")
    lines.append("")
    lines.append(_best_candidate(metrics["test_policy_metrics"]))
    lines.append("")
    lines.append("## 10. Validaciones anti-leakage")
    lines.append("")
    for key, value in metrics["anti_leakage"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.append("")
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# 5. Orquestacion
# --------------------------------------------------------------------------- #
def run(
    data_path: str | Path = DEFAULT_DATA,
    input_dir: str | Path = DEFAULT_INPUT_DIR,
    report_path: str | Path = DEFAULT_REPORT,
    metrics_path: str | Path = DEFAULT_METRICS,
) -> dict[str, Any]:
    """Ejecuta el backtesting completo y guarda reporte/metricas."""
    data_path = Path(data_path)
    report_path = Path(report_path)
    metrics_path = Path(metrics_path)

    print(f"[1/7] Cargando dataset rolling: {data_path}")
    df = load_dataset(data_path)
    splits = split_data(df)

    print("[2/7] Reentrenando candidato ganador solo con train")
    model = train_selected_model(splits)

    print("[3/7] Generando predicciones para train/val/test")
    pred_df = add_model_predictions(splits, model)
    model_metrics = model_metrics_by_split(pred_df)

    print("[4/7] Calculando margenes P80/P90/P95 solo con val")
    val_df = pred_df[pred_df["split"] == "val"]
    margins = calculate_residual_margins(val_df)
    pred_df = add_simulated_promises(pred_df, margins)

    print("[5/7] Reconstruyendo promesa actual de Olist solo para evaluacion")
    pred_df = add_current_promises(pred_df, input_dir=input_dir)

    print("[6/7] Evaluando politicas en test y por segmentos")
    test_policy_metrics = evaluate_policies(pred_df, split="test")
    test_by_customer_state = evaluate_by_group(
        pred_df, "customer_state", split="test", min_n=100
    )
    test_by_ruta_estado = evaluate_by_group(
        pred_df, "ruta_estado", split="test", min_n=MIN_ROUTE_N
    )

    print("[7/7] Guardando reporte y metricas JSON")
    metrics: dict[str, Any] = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "dataset": str(data_path),
        "target": TARGET,
        "question": (
            "Si en el pasado hubieramos prometido usando Fase 2, que porcentaje "
            "se habria cumplido y cuanto colchon habriamos mostrado?"
        ),
        "model": {
            "modelo": SELECTED_MODEL,
            "feature_set": SELECTED_FEATURE_SET,
            "trained_on": "train",
            "features": selected_features(),
            "model_saved": False,
        },
        "policy_definition": {
            "residual": "dias_entrega_real - prediccion_dias",
            "margins_source_split": "val",
            "test_used_for_policy_definition": False,
            "promise_formula": "max(ceil(prediccion_dias + margen), 1)",
            "current_promise_source": (
                "olist_orders_dataset: order_estimated_delivery_date - "
                "order_purchase_timestamp"
            ),
        },
        "split_sizes": {split: int(len(splits[split])) for split in SPLIT_ORDER},
        "model_metrics": model_metrics,
        "margins_val": margins,
        "test_policy_metrics": test_policy_metrics,
        "test_by_customer_state": test_by_customer_state,
        "test_by_ruta_estado": test_by_ruta_estado,
        "anti_leakage": {
            "forbidden_features_intersection": sorted(
                set(selected_features()) & ev.PROHIBITED_AS_FEATURES
            ),
            "seller_id_in_features": "seller_id" in selected_features(),
            "dias_entrega_real_in_features": TARGET in selected_features(),
            "dias_prometidos_actual_in_features": CURRENT_PROMISE_COL
            in selected_features(),
            "val_used_for_margins": True,
            "test_used_for_margins": False,
            "fase1_files_modified_by_script": False,
        },
    }

    report_path.parent.mkdir(parents=True, exist_ok=True)
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    metrics_path.write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    report_path.write_text(make_report(data_path, metrics), encoding="utf-8")
    print(f"      reporte: {report_path}")
    print(f"      metricas: {metrics_path}")
    return metrics


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Backtesting offline de promesas P80/P90/P95 para Fase 2"
    )
    parser.add_argument("--data", default=str(DEFAULT_DATA))
    parser.add_argument("--input-dir", default=str(DEFAULT_INPUT_DIR))
    parser.add_argument("--report", default=str(DEFAULT_REPORT))
    parser.add_argument("--metrics", default=str(DEFAULT_METRICS))
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run(args.data, args.input_dir, args.report, args.metrics)
