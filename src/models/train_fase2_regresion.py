"""Entrenamiento de modelos Fase 2 para regresion de dias_entrega_real.

Chat E compara baselines y regresores usando validacion temporal:

  1. Carga `orders_fase2_regresion_rolling.csv`.
  2. Define bloques de features sin columnas prohibidas.
  3. Entrena baselines de mediana calculados solo con train.
  4. Entrena Ridge, RandomForestRegressor y XGBoost Regressor si esta instalado.
  5. Selecciona por MAE en val, sin usar test para elegir.
  6. Evalua una sola vez en test el candidato elegido.
  7. Genera reporte Markdown y JSON liviano; no guarda modelos joblib.

Uso:
    python -m src.models.train_fase2_regresion
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sklearn.compose import ColumnTransformer  # noqa: E402
from sklearn.ensemble import RandomForestRegressor  # noqa: E402
from sklearn.impute import SimpleImputer  # noqa: E402
from sklearn.linear_model import Ridge  # noqa: E402
from sklearn.pipeline import Pipeline  # noqa: E402
from sklearn.preprocessing import OneHotEncoder, StandardScaler  # noqa: E402

from src.models import evaluate_fase2_regresion as ev  # noqa: E402


# --------------------------------------------------------------------------- #
# 0. Rutas, contrato y bloques de features
# --------------------------------------------------------------------------- #
RANDOM_STATE = 42
TARGET = ev.TARGET
SPLIT_ORDER = ["train", "val", "test"]

DEFAULT_DATA = ROOT / "data" / "processed" / "orders_fase2_regresion_rolling.csv"
DEFAULT_REPORT = ROOT / "reports" / "fase2_modelado_regresion.md"
DEFAULT_METRICS = ROOT / "reports" / "fase2_modelado_metrics.json"

BASE_NUMERIC_FEATURES = [
    "mismo_estado",
    "dist_haversine_km",
    "precio_total",
    "flete_total",
    "ratio_flete",
    "n_items",
    "peso_total_g",
    "volumen_total_cm3",
    "mes_compra",
    "dia_semana_compra",
    "tasa_vendedor",
    "sin_historial_vendedor",
]

BASE_CATEGORICAL_FEATURES = [
    "customer_state",
    "seller_state",
    "categoria_principal",
]

ROUTE_CUSTOMER_ROLLING_FEATURES = [
    "ruta_estado_30d_days_mean_fallback",
    "ruta_estado_30d_days_median",
    "ruta_estado_30d_orders_count",
    "ruta_estado_30d_sin_historial",
    "customer_state_30d_days_mean_fallback",
    "customer_state_30d_days_median",
    "customer_state_30d_orders_count",
    "customer_state_30d_sin_historial",
]

CATEGORY_ROLLING_FEATURES = [
    "categoria_principal_30d_days_mean_fallback",
    "categoria_principal_30d_orders_count",
    "categoria_principal_30d_sin_historial",
]

SELLER_ROLLING_FEATURES = [
    "seller_id_30d_days_mean_fallback",
    "seller_id_30d_orders_count",
    "seller_id_30d_sin_historial",
]

FEATURE_SETS = {
    "M0_base_sin_rolling": BASE_NUMERIC_FEATURES + BASE_CATEGORICAL_FEATURES,
    "M0_mas_ruta_customer_rolling": (
        BASE_NUMERIC_FEATURES
        + BASE_CATEGORICAL_FEATURES
        + ROUTE_CUSTOMER_ROLLING_FEATURES
    ),
    "M0_mas_categoria_rolling": (
        BASE_NUMERIC_FEATURES
        + BASE_CATEGORICAL_FEATURES
        + CATEGORY_ROLLING_FEATURES
    ),
    "M0_mas_seller_rolling": (
        BASE_NUMERIC_FEATURES
        + BASE_CATEGORICAL_FEATURES
        + SELLER_ROLLING_FEATURES
    ),
    "M0_todas_las_rolling": (
        BASE_NUMERIC_FEATURES
        + BASE_CATEGORICAL_FEATURES
        + ROUTE_CUSTOMER_ROLLING_FEATURES
        + CATEGORY_ROLLING_FEATURES
        + SELLER_ROLLING_FEATURES
    ),
}

SUPPORT_COLUMNS = ["order_id", "order_purchase_timestamp", "split", "seller_id", "ruta_estado"]


# --------------------------------------------------------------------------- #
# 1. Utilidades de datos y preprocesamiento
# --------------------------------------------------------------------------- #
def load_dataset(path: str | Path = DEFAULT_DATA) -> pd.DataFrame:
    """Carga el dataset rolling y valida su contrato minimo."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"No se encontro el dataset rolling: {path}")
    df = pd.read_csv(path, parse_dates=["order_purchase_timestamp"])
    required = {TARGET, "split", "order_purchase_timestamp", *all_feature_columns()}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Faltan columnas requeridas: {sorted(missing)}")
    ev.assert_temporal_split(df)
    for feature_set in FEATURE_SETS.values():
        ev.assert_no_forbidden_features(feature_set)
    return df


def all_feature_columns() -> list[str]:
    """Lista unica de features candidatas usadas en cualquier bloque."""
    cols: list[str] = []
    for feature_set in FEATURE_SETS.values():
        for col in feature_set:
            if col not in cols:
                cols.append(col)
    return cols


def split_data(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Devuelve train, val y test respetando la columna temporal `split`."""
    return {
        split: df[df["split"] == split].reset_index(drop=True)
        for split in SPLIT_ORDER
    }


def numeric_features(feature_cols: list[str]) -> list[str]:
    """Identifica features numericas dentro de un bloque."""
    categorical = set(BASE_CATEGORICAL_FEATURES)
    return [col for col in feature_cols if col not in categorical]


def categorical_features(feature_cols: list[str]) -> list[str]:
    """Identifica features categoricas dentro de un bloque."""
    categorical = set(BASE_CATEGORICAL_FEATURES)
    return [col for col in feature_cols if col in categorical]


def make_one_hot_encoder() -> OneHotEncoder:
    """Crea OneHotEncoder compatible con versiones recientes de sklearn."""
    try:
        return OneHotEncoder(handle_unknown="ignore", sparse_output=True)
    except TypeError:
        return OneHotEncoder(handle_unknown="ignore", sparse=True)


def build_preprocessor(feature_cols: list[str], scale_numeric: bool = True) -> ColumnTransformer:
    """Preprocesador ajustado solo en train dentro de cada Pipeline."""
    num_cols = numeric_features(feature_cols)
    cat_cols = categorical_features(feature_cols)
    numeric_steps: list[tuple[str, Any]] = [("imputer", SimpleImputer(strategy="median"))]
    if scale_numeric:
        numeric_steps.append(("scaler", StandardScaler()))

    return ColumnTransformer(
        transformers=[
            ("num", Pipeline(numeric_steps), num_cols),
            (
                "cat",
                Pipeline(
                    [
                        ("imputer", SimpleImputer(strategy="most_frequent")),
                        ("onehot", make_one_hot_encoder()),
                    ]
                ),
                cat_cols,
            ),
        ],
        remainder="drop",
    )


# --------------------------------------------------------------------------- #
# 2. Modelos candidatos
# --------------------------------------------------------------------------- #
def build_model_candidates(feature_cols: list[str]) -> dict[str, Pipeline]:
    """Construye candidatos de regresion para un bloque de features."""
    candidates: dict[str, Pipeline] = {
        "ridge": Pipeline(
            [
                ("prep", build_preprocessor(feature_cols, scale_numeric=True)),
                ("reg", Ridge(alpha=10.0)),
            ]
        ),
        "random_forest": Pipeline(
            [
                ("prep", build_preprocessor(feature_cols, scale_numeric=False)),
                (
                    "reg",
                    RandomForestRegressor(
                        n_estimators=80,
                        max_depth=14,
                        min_samples_leaf=20,
                        random_state=RANDOM_STATE,
                        n_jobs=-1,
                    ),
                ),
            ]
        ),
    }

    if importlib.util.find_spec("xgboost") is not None:
        from xgboost import XGBRegressor

        candidates["xgboost"] = Pipeline(
            [
                ("prep", build_preprocessor(feature_cols, scale_numeric=False)),
                (
                    "reg",
                    XGBRegressor(
                        n_estimators=220,
                        max_depth=4,
                        learning_rate=0.05,
                        subsample=0.9,
                        colsample_bytree=0.9,
                        reg_lambda=2.0,
                        objective="reg:squarederror",
                        tree_method="hist",
                        random_state=RANDOM_STATE,
                        n_jobs=-1,
                    ),
                ),
            ]
        )
    return candidates


def clipped_predict(model: Pipeline, X: pd.DataFrame) -> np.ndarray:
    """Predice dias y evita valores negativos."""
    return np.clip(model.predict(X), 0.0, None)


# --------------------------------------------------------------------------- #
# 3. Entrenamiento y evaluacion
# --------------------------------------------------------------------------- #
def evaluate_baselines(splits: dict[str, pd.DataFrame]) -> list[dict[str, Any]]:
    """Entrena baselines en train y los evalua en train/val."""
    rows: list[dict[str, Any]] = []
    train = splits["train"]
    eval_splits = ["train", "val"]
    for name, baseline in ev.build_baselines().items():
        baseline.fit(train, train[TARGET])
        for split in eval_splits:
            split_df = splits[split]
            metrics = ev.regression_metrics(split_df[TARGET], baseline.predict(split_df))
            rows.append(
                {
                    "tipo": "baseline",
                    "modelo": name,
                    "feature_set": "regla_mediana_train",
                    "split": split,
                    **metrics,
                }
            )
    return rows


def train_candidates(
    splits: dict[str, pd.DataFrame],
) -> tuple[list[dict[str, Any]], dict[str, Pipeline]]:
    """Entrena candidatos por bloque y registra metricas train/val."""
    train = splits["train"]
    val = splits["val"]
    rows: list[dict[str, Any]] = []
    fitted: dict[str, Pipeline] = {}

    for feature_set_name, feature_cols in FEATURE_SETS.items():
        ev.assert_no_forbidden_features(feature_cols)
        for model_name, model in build_model_candidates(feature_cols).items():
            key = f"{model_name}__{feature_set_name}"
            model.fit(train[feature_cols], train[TARGET])
            fitted[key] = model
            for split_name, split_df in [("train", train), ("val", val)]:
                preds = clipped_predict(model, split_df[feature_cols])
                metrics = ev.regression_metrics(split_df[TARGET], preds)
                rows.append(
                    {
                        "tipo": "modelo",
                        "modelo": model_name,
                        "feature_set": feature_set_name,
                        "split": split_name,
                        **metrics,
                    }
                )
    return rows, fitted


def select_best_model(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Elige el candidato con menor MAE en val, sin mirar test."""
    val_rows = [
        row for row in rows if row["tipo"] == "modelo" and row["split"] == "val"
    ]
    return min(val_rows, key=lambda row: row["mae"])


def final_test_evaluation(
    best_row: dict[str, Any],
    fitted: dict[str, Pipeline],
    splits: dict[str, pd.DataFrame],
) -> tuple[dict[str, dict[str, float]], np.ndarray]:
    """Evalua train/val/test para el candidato elegido."""
    feature_cols = FEATURE_SETS[best_row["feature_set"]]
    key = f"{best_row['modelo']}__{best_row['feature_set']}"
    model = fitted[key]
    final_metrics: dict[str, dict[str, float]] = {}
    test_pred = np.array([], dtype="float64")
    for split_name in SPLIT_ORDER:
        split_df = splits[split_name]
        preds = clipped_predict(model, split_df[feature_cols])
        final_metrics[split_name] = ev.regression_metrics(split_df[TARGET], preds)
        if split_name == "test":
            test_pred = preds
    return final_metrics, test_pred


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


def summarize_feature_blocks() -> list[dict[str, Any]]:
    """Resumen de features por bloque para el reporte."""
    return [
        {
            "bloque": name,
            "n_features": len(cols),
            "features": ", ".join(cols),
        }
        for name, cols in FEATURE_SETS.items()
    ]


def make_report(
    dataset_path: Path,
    df: pd.DataFrame,
    baseline_rows: list[dict[str, Any]],
    model_rows: list[dict[str, Any]],
    best_row: dict[str, Any],
    final_metrics: dict[str, dict[str, float]],
    state_error: pd.DataFrame,
    route_error: pd.DataFrame,
    correlation_table: pd.DataFrame,
) -> str:
    """Renderiza el reporte Markdown de modelado."""
    val_model_rows = (
        pd.DataFrame(model_rows)
        .query("split == 'val'")
        .sort_values("mae")
        .reset_index(drop=True)
    )
    baseline_val = (
        pd.DataFrame(baseline_rows)
        .query("split == 'val'")
        .sort_values("mae")
        .reset_index(drop=True)
    )
    ablation = val_model_rows[
        ["modelo", "feature_set", "mae", "medae", "rmse", "p90_abs_error", "bias_mean"]
    ].copy()
    final_table = pd.DataFrame(
        [{"split": split, **metrics} for split, metrics in final_metrics.items()]
    )
    split_summary = (
        df.groupby("split")[TARGET]
        .agg(ordenes="size", media="mean", mediana="median", p90=lambda x: x.quantile(0.90))
        .reindex(SPLIT_ORDER)
        .reset_index()
    )

    lines: list[str] = []
    lines.append("# Fase 2 - Modelado de regresion dias_entrega_real")
    lines.append("")
    lines.append("## 1. Resumen ejecutivo")
    lines.append("")
    lines.append(
        "Se entrenaron baselines y regresores para predecir `dias_entrega_real` "
        "usando split temporal. La seleccion se hizo solo por MAE en `val`; "
        "MAE significa error absoluto medio, es decir, cuantos dias se equivoca "
        "el modelo en promedio."
    )
    lines.append("")
    lines.append(
        f"Mejor candidato por validacion: `{best_row['modelo']}` con bloque "
        f"`{best_row['feature_set']}` y MAE val {_fmt(best_row['mae'], 3)} dias. "
        f"Su MAE final en test fue {_fmt(final_metrics['test']['mae'], 3)} dias."
    )
    lines.append("")
    lines.append("## 2. Dataset usado")
    lines.append("")
    lines.append(f"- Entrada local: `{dataset_path}`")
    lines.append(f"- Shape: {df.shape[0]:,} filas x {df.shape[1]:,} columnas")
    lines.append("- Target: `dias_entrega_real`")
    lines.append("- No se uso `dias_prometidos`; queda fuera de este chat.")
    lines.append("- No se guardo modelo `.joblib`.")
    lines.append("")
    lines.append(to_markdown(split_summary, digits=2))
    lines.append("")
    lines.append("## 3. Features por bloque")
    lines.append("")
    lines.append(to_markdown(pd.DataFrame(summarize_feature_blocks()), digits=0))
    lines.append("")
    lines.append(
        "`seller_id` crudo se conserva solo como soporte del dataset, pero no entra "
        "a ningun `X_COLS`. La senal de seller se evalua con agregados rolling, "
        "conteo y flag de historial."
    )
    lines.append("")
    lines.append("## 4. Baselines")
    lines.append("")
    lines.append(
        "Los baselines calculan medianas solo con train y aplican fallback cuando "
        "un grupo no existe en el pasado."
    )
    lines.append("")
    lines.append(to_markdown(baseline_val[["modelo", "mae", "medae", "rmse", "p90_abs_error", "bias_mean"]]))
    lines.append("")
    lines.append("## 5. Modelos candidatos y resultados en val")
    lines.append("")
    lines.append(
        "Se entrenaron Ridge, RandomForestRegressor y XGBoost Regressor porque "
        "XGBoost estaba instalado en el entorno. Ridge es una regresion lineal "
        "regularizada: una linea base interpretable que penaliza coeficientes "
        "excesivos."
    )
    lines.append("")
    lines.append(to_markdown(val_model_rows[["modelo", "feature_set", "mae", "medae", "rmse", "p90_abs_error", "bias_mean"]]))
    lines.append("")
    lines.append("## 6. Evaluacion final en test")
    lines.append("")
    lines.append(
        "El test se uso una sola vez para el candidato elegido por validacion. "
        "Bias positivo significa que el modelo sobreestima dias; bias negativo, "
        "que tiende a subestimar."
    )
    lines.append("")
    lines.append(to_markdown(final_table))
    lines.append("")
    lines.append("## 7. Ablacion por bloques")
    lines.append("")
    lines.append(
        "Ablacion significa comparar el mismo tipo de modelo agregando o quitando "
        "bloques de features para medir que aporta cada familia."
    )
    lines.append("")
    lines.append(to_markdown(ablation))
    lines.append("")
    lines.append("## 8. Error por customer_state")
    lines.append("")
    lines.append(to_markdown(state_error.head(15), digits=3))
    lines.append("")
    lines.append("## 9. Error por ruta_estado")
    lines.append("")
    lines.append(to_markdown(route_error.head(20), digits=3))
    lines.append("")
    lines.append("## 10. Multicolinealidad")
    lines.append("")
    lines.append(
        "Multicolinealidad significa que dos features cuentan informacion parecida. "
        "No invalida el modelo, pero en modelos lineales reduce interpretabilidad "
        "porque el merito predictivo se reparte entre variables redundantes."
    )
    lines.append("")
    lines.append(to_markdown(correlation_table.head(15), digits=3))
    lines.append("")
    lines.append("## 11. Riesgos y limitaciones")
    lines.append("")
    lines.append("- R-14 sigue visible: train tiene entregas mas lentas que test.")
    lines.append("- `ruta_estado` cruda no se uso como feature principal por cardinalidad; se priorizaron rolling/fallbacks.")
    lines.append("- Seller rolling aporta con cautela por menor cobertura y posible inestabilidad.")
    lines.append("- Las features fisicas, flete y distancia tienen redundancia; no se eliminaron sin evidencia de ablacion.")
    lines.append("- No se hizo backtesting P80/P90/P95; corresponde a Chat F.")
    lines.append("")
    lines.append("## 12. Recomendacion para Chat F")
    lines.append("")
    lines.append(
        "Usar el candidato elegido como insumo inicial para simular politicas "
        "P80/P90/P95. Chat F debe convertir predicciones de dias en promesas y "
        "medir cumplimiento, colchon y riesgo por estado/ruta sin cambiar la "
        "seleccion realizada aqui."
    )
    lines.append("")
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# 5. Orquestacion
# --------------------------------------------------------------------------- #
def run(
    data_path: str | Path = DEFAULT_DATA,
    report_path: str | Path = DEFAULT_REPORT,
    metrics_path: str | Path = DEFAULT_METRICS,
) -> dict[str, Any]:
    """Ejecuta el modelado completo de Fase 2."""
    data_path = Path(data_path)
    report_path = Path(report_path)
    metrics_path = Path(metrics_path)

    print(f"[1/6] Cargando dataset rolling: {data_path}")
    df = load_dataset(data_path)
    splits = split_data(df)
    print(
        "      filas: "
        + " ".join(f"{split}={len(splits[split]):,}" for split in SPLIT_ORDER)
    )

    print("[2/6] Entrenando baselines de mediana (solo train)")
    baseline_rows = evaluate_baselines(splits)

    print("[3/6] Entrenando regresores por bloques de features")
    model_rows, fitted = train_candidates(splits)

    print("[4/6] Seleccionando por MAE en val")
    best_row = select_best_model(model_rows)
    print(
        f"      elegido: {best_row['modelo']} + {best_row['feature_set']} "
        f"(MAE val={best_row['mae']:.3f})"
    )

    print("[5/6] Evaluando una sola vez en test el candidato elegido")
    final_metrics, test_pred = final_test_evaluation(best_row, fitted, splits)
    state_error = ev.error_by_group(splits["test"], test_pred, "customer_state", min_n=100)
    route_error = ev.error_by_group(splits["test"], test_pred, "ruta_estado", min_n=80)
    correlation_table = ev.correlation_pairs(
        splits["train"],
        [
            "dist_haversine_km",
            "flete_total",
            "ratio_flete",
            "precio_total",
            "peso_total_g",
            "volumen_total_cm3",
            "mismo_estado",
            "n_items",
        ],
    )

    print("[6/6] Guardando reporte y metricas JSON")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    report = make_report(
        data_path,
        df,
        baseline_rows,
        model_rows,
        best_row,
        final_metrics,
        state_error,
        route_error,
        correlation_table,
    )
    report_path.write_text(report, encoding="utf-8")

    metrics: dict[str, Any] = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "dataset": str(data_path),
        "target": TARGET,
        "selection_rule": "menor MAE en val; test solo para candidato elegido",
        "split_sizes": {split: int(len(splits[split])) for split in SPLIT_ORDER},
        "feature_sets": FEATURE_SETS,
        "baselines_train_val": baseline_rows,
        "candidate_metrics_train_val": model_rows,
        "best_model": {
            "modelo": best_row["modelo"],
            "feature_set": best_row["feature_set"],
            "val_metrics": {
                key: value
                for key, value in best_row.items()
                if key in {"mae", "medae", "rmse", "p90_abs_error", "bias_mean"}
            },
        },
        "final_metrics_selected_model": final_metrics,
        "error_by_customer_state_test": state_error.to_dict(orient="records"),
        "error_by_ruta_estado_test": route_error.to_dict(orient="records"),
        "multicollinearity_spearman_train": correlation_table.to_dict(orient="records"),
        "anti_leakage": {
            "forbidden_features": sorted(ev.PROHIBITED_AS_FEATURES),
            "seller_id_in_x_cols": any("seller_id" == col for col in all_feature_columns()),
            "dias_prometidos_used": "dias_prometidos" in all_feature_columns(),
        },
    }
    metrics_path.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"      reporte: {report_path}")
    print(f"      metricas: {metrics_path}")
    return metrics


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Entrena modelos de Fase 2 para regresion de dias_entrega_real"
    )
    parser.add_argument("--data", default=str(DEFAULT_DATA))
    parser.add_argument("--report", default=str(DEFAULT_REPORT))
    parser.add_argument("--metrics", default=str(DEFAULT_METRICS))
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run(args.data, args.report, args.metrics)

