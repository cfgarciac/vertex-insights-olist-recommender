"""Experimento acotado de clustering para Fase 2.

Este script prueba si agregar clusters como features mejora el modelo vigente de
regresion de `dias_entrega_real`. Clustering significa agrupar observaciones o
perfiles parecidos sin usar el target como etiqueta.

Reglas del experimento:
  - No modifica Fase 1.
  - No guarda modelos joblib.
  - No usa `dias_entrega_real` para formar clusters.
  - No usa fechas post-compra, reviews, `entrega_tarde` ni `dias_vs_promesa`
    como features de clustering.
  - Usa `seller_id` solo como llave para asignar clusters de seller, no como
    feature directa del regresor.

Uso:
    python scripts/experiment_fase2_clustering.py
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
from sklearn.cluster import KMeans
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.models import evaluate_fase2_regresion as ev  # noqa: E402
from src.models import train_fase2_regresion as train_fase2  # noqa: E402


# --------------------------------------------------------------------------- #
# 0. Contrato del experimento
# --------------------------------------------------------------------------- #
RANDOM_STATE = 42
TARGET = ev.TARGET
SPLIT_ORDER = ["train", "val", "test"]
SELECTED_FEATURE_SET = "M0_mas_seller_rolling"
BASE_FEATURES = list(train_fase2.FEATURE_SETS[SELECTED_FEATURE_SET])
BASE_CATEGORICAL = ["customer_state", "seller_state", "categoria_principal"]
DEFAULT_K_LIST = [4, 8]
NEW_CLUSTER_LABEL = "cluster_nuevo_o_sin_perfil"

DEFAULT_DATA = ROOT / "data" / "processed" / "orders_fase2_regresion_rolling.csv"
DEFAULT_REPORT = ROOT / "experiments" / "fase2_clustering_experimento.md"
DEFAULT_METRICS = ROOT / "experiments" / "fase2_clustering_metrics.json"

FORBIDDEN_CLUSTER_INPUTS = {
    TARGET,
    "order_delivered_customer_date",
    "order_delivered_carrier_date",
    "dias_vs_promesa",
    "entrega_tarde",
    "is_late_delivery",
    "delivery_days",
    "delivery_delay_days",
    "review_count",
    "avg_review_score",
    "min_review_score",
    "max_review_score",
    "has_review_comment",
    "review_comment_titles",
    "review_comment_messages",
    "last_review_creation_date",
    "last_review_answer_timestamp",
    "is_dissatisfied",
}

ROUTE_NUMERIC_PROFILE_COLS = [
    "dist_haversine_km_median",
    "flete_total_median",
    "ratio_flete_median",
    "precio_total_median",
    "peso_total_g_median",
    "volumen_total_cm3_median",
    "n_items_mean",
    "mismo_estado_mean",
    "ordenes_train",
]
ROUTE_CATEGORICAL_PROFILE_COLS = ["customer_state_mode", "seller_state_mode"]

SELLER_NUMERIC_PROFILE_COLS = [
    "dist_haversine_km_median",
    "flete_total_median",
    "ratio_flete_median",
    "precio_total_median",
    "peso_total_g_median",
    "volumen_total_cm3_median",
    "n_items_mean",
    "mismo_estado_mean",
    "ordenes_train",
    "categorias_unicas",
    "destinos_unicos",
]
SELLER_CATEGORICAL_PROFILE_COLS = [
    "seller_state_mode",
    "categoria_principal_mode",
    "customer_state_mode",
]

GEO_CLUSTER_NUMERIC_COLS = ["dist_haversine_km", "mismo_estado"]
GEO_CLUSTER_CATEGORICAL_COLS = ["customer_state", "seller_state"]


# --------------------------------------------------------------------------- #
# 1. Utilidades generales
# --------------------------------------------------------------------------- #
def make_one_hot_encoder() -> OneHotEncoder:
    """Crea OneHotEncoder compatible con varias versiones de sklearn."""
    try:
        return OneHotEncoder(handle_unknown="ignore", sparse_output=True)
    except TypeError:
        return OneHotEncoder(handle_unknown="ignore", sparse=True)


def make_preprocessor(
    numeric_cols: list[str],
    categorical_cols: list[str],
    scale_numeric: bool = False,
) -> ColumnTransformer:
    """Construye un preprocesador generico para modelos tabulares."""
    numeric_steps: list[tuple[str, Any]] = [("imputer", SimpleImputer(strategy="median"))]
    if scale_numeric:
        numeric_steps.append(("scaler", StandardScaler()))

    return ColumnTransformer(
        transformers=[
            ("num", Pipeline(numeric_steps), numeric_cols),
            (
                "cat",
                Pipeline(
                    [
                        ("imputer", SimpleImputer(strategy="most_frequent")),
                        ("onehot", make_one_hot_encoder()),
                    ]
                ),
                categorical_cols,
            ),
        ],
        remainder="drop",
    )


def make_kmeans_pipeline(
    numeric_cols: list[str], categorical_cols: list[str], k: int
) -> Pipeline:
    """Preprocesa perfiles M0 y ajusta KMeans."""
    return Pipeline(
        [
            ("prep", make_preprocessor(numeric_cols, categorical_cols, scale_numeric=True)),
            (
                "cluster",
                KMeans(n_clusters=k, n_init=20, random_state=RANDOM_STATE),
            ),
        ]
    )


def make_regressor(feature_cols: list[str], categorical_cols: list[str]) -> Pipeline:
    """Replica el RandomForestRegressor vigente con soporte para clusters."""
    numeric_cols = [col for col in feature_cols if col not in set(categorical_cols)]
    return Pipeline(
        [
            ("prep", make_preprocessor(numeric_cols, categorical_cols, scale_numeric=False)),
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
    )


def regression_metrics_by_split(
    df: pd.DataFrame, pred_col: str
) -> dict[str, dict[str, float]]:
    """Calcula metricas de regresion por split."""
    output: dict[str, dict[str, float]] = {}
    for split in SPLIT_ORDER:
        split_df = df[df["split"] == split]
        output[split] = ev.regression_metrics(split_df[TARGET], split_df[pred_col])
    return output


def train_and_predict_variant(
    df: pd.DataFrame,
    feature_cols: list[str],
    categorical_cols: list[str],
    pred_col: str,
) -> dict[str, Any]:
    """Entrena en train y predice train/val/test para una variante."""
    ev.assert_no_forbidden_features(feature_cols)
    model = make_regressor(feature_cols, categorical_cols)
    train_df = df[df["split"] == "train"].copy()
    model.fit(train_df[feature_cols], train_df[TARGET])

    out = df.copy()
    out[pred_col] = np.clip(model.predict(out[feature_cols]), 0.0, None)
    return {
        "prediction_frame": out,
        "metrics": regression_metrics_by_split(out, pred_col),
    }


def promise_p90_metrics(df: pd.DataFrame, pred_col: str) -> dict[str, Any]:
    """Simula politica P90 usando margen de val y evaluando test."""
    val_df = df[df["split"] == "val"]
    test_df = df[df["split"] == "test"].copy()
    residual_val = val_df[TARGET].to_numpy(dtype="float64") - val_df[pred_col].to_numpy(
        dtype="float64"
    )
    margin = float(np.quantile(residual_val, 0.90))
    promised = np.maximum(np.ceil(test_df[pred_col].to_numpy(dtype="float64") + margin), 1)
    actual = test_df[TARGET].to_numpy(dtype="float64")
    cushion = promised - actual
    fulfilled = actual <= promised
    return {
        "margen_p90_val": margin,
        "test": {
            "cumplimiento": float(np.mean(fulfilled)),
            "incumplimiento": float(1.0 - np.mean(fulfilled)),
            "colchon_promedio": float(np.mean(cushion)),
            "colchon_mediano": float(np.median(cushion)),
            "promesa_promedio": float(np.mean(promised)),
            "promesa_mediana": float(np.median(promised)),
        },
    }


def mode_or_unknown(series: pd.Series) -> str:
    """Devuelve la moda de una serie o desconocido si no existe."""
    values = series.dropna()
    if values.empty:
        return "desconocido"
    return str(values.mode().iloc[0])


def assert_cluster_inputs_allowed(columns: Iterable[str]) -> None:
    """Valida que el clustering no use columnas prohibidas."""
    forbidden = set(columns) & FORBIDDEN_CLUSTER_INPUTS
    if forbidden:
        raise AssertionError(f"Inputs prohibidos para clustering: {sorted(forbidden)}")


# --------------------------------------------------------------------------- #
# 2. Clusters por perfiles de ruta, seller y geografia simple
# --------------------------------------------------------------------------- #
def build_route_profiles(train_df: pd.DataFrame) -> pd.DataFrame:
    """Crea perfiles de rutas usando solo features M0 de train."""
    assert_cluster_inputs_allowed(
        [
            "dist_haversine_km",
            "flete_total",
            "ratio_flete",
            "precio_total",
            "peso_total_g",
            "volumen_total_cm3",
            "n_items",
            "mismo_estado",
            "customer_state",
            "seller_state",
        ]
    )
    grouped = train_df.groupby("ruta_estado", dropna=False)
    profiles = grouped.agg(
        dist_haversine_km_median=("dist_haversine_km", "median"),
        flete_total_median=("flete_total", "median"),
        ratio_flete_median=("ratio_flete", "median"),
        precio_total_median=("precio_total", "median"),
        peso_total_g_median=("peso_total_g", "median"),
        volumen_total_cm3_median=("volumen_total_cm3", "median"),
        n_items_mean=("n_items", "mean"),
        mismo_estado_mean=("mismo_estado", "mean"),
        ordenes_train=("order_id", "size"),
    )
    profiles["customer_state_mode"] = grouped["customer_state"].agg(mode_or_unknown)
    profiles["seller_state_mode"] = grouped["seller_state"].agg(mode_or_unknown)
    return profiles.reset_index()


def build_seller_profiles(train_df: pd.DataFrame) -> pd.DataFrame:
    """Crea perfiles de sellers usando solo features M0 de train."""
    assert_cluster_inputs_allowed(
        [
            "dist_haversine_km",
            "flete_total",
            "ratio_flete",
            "precio_total",
            "peso_total_g",
            "volumen_total_cm3",
            "n_items",
            "mismo_estado",
            "seller_state",
            "categoria_principal",
            "customer_state",
        ]
    )
    grouped = train_df.groupby("seller_id", dropna=False)
    profiles = grouped.agg(
        dist_haversine_km_median=("dist_haversine_km", "median"),
        flete_total_median=("flete_total", "median"),
        ratio_flete_median=("ratio_flete", "median"),
        precio_total_median=("precio_total", "median"),
        peso_total_g_median=("peso_total_g", "median"),
        volumen_total_cm3_median=("volumen_total_cm3", "median"),
        n_items_mean=("n_items", "mean"),
        mismo_estado_mean=("mismo_estado", "mean"),
        ordenes_train=("order_id", "size"),
        categorias_unicas=("categoria_principal", "nunique"),
        destinos_unicos=("customer_state", "nunique"),
    )
    profiles["seller_state_mode"] = grouped["seller_state"].agg(mode_or_unknown)
    profiles["categoria_principal_mode"] = grouped["categoria_principal"].agg(
        mode_or_unknown
    )
    profiles["customer_state_mode"] = grouped["customer_state"].agg(mode_or_unknown)
    return profiles.reset_index()


def add_profile_cluster(
    df: pd.DataFrame,
    profiles: pd.DataFrame,
    key_col: str,
    cluster_col: str,
    numeric_cols: list[str],
    categorical_cols: list[str],
    k: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Ajusta clusters sobre perfiles train y los asigna por llave."""
    effective_k = min(k, len(profiles))
    if effective_k < 2:
        raise ValueError(f"No hay suficientes perfiles para k={k} en {cluster_col}")

    pipe = make_kmeans_pipeline(numeric_cols, categorical_cols, effective_k)
    profile_features = profiles[numeric_cols + categorical_cols]
    cluster_ids = pipe.fit_predict(profile_features)
    profiled = profiles.copy()
    profiled[cluster_col] = [f"{cluster_col}_{int(value)}" for value in cluster_ids]

    mapping = profiled.set_index(key_col)[cluster_col]
    output = df.copy()
    output[cluster_col] = output[key_col].map(mapping).fillna(NEW_CLUSTER_LABEL)
    return output, profiled


def add_geo_cluster(df: pd.DataFrame, cluster_col: str, k: int) -> pd.DataFrame:
    """Agrupa ordenes por senales geograficas M0 simples."""
    assert_cluster_inputs_allowed(GEO_CLUSTER_NUMERIC_COLS + GEO_CLUSTER_CATEGORICAL_COLS)
    train_df = df[df["split"] == "train"].copy()
    pipe = make_kmeans_pipeline(
        GEO_CLUSTER_NUMERIC_COLS, GEO_CLUSTER_CATEGORICAL_COLS, k
    )
    pipe.fit(train_df[GEO_CLUSTER_NUMERIC_COLS + GEO_CLUSTER_CATEGORICAL_COLS])
    output = df.copy()
    labels = pipe.predict(output[GEO_CLUSTER_NUMERIC_COLS + GEO_CLUSTER_CATEGORICAL_COLS])
    output[cluster_col] = [f"{cluster_col}_{int(value)}" for value in labels]
    return output


# --------------------------------------------------------------------------- #
# 3. Cobertura e interpretacion
# --------------------------------------------------------------------------- #
def coverage_for_cluster(df: pd.DataFrame, cluster_col: str) -> list[dict[str, Any]]:
    """Mide cobertura del cluster por split."""
    rows = []
    for split in SPLIT_ORDER:
        split_df = df[df["split"] == split]
        rows.append(
            {
                "split": split,
                "ordenes": int(len(split_df)),
                "coverage_pct": float((split_df[cluster_col] != NEW_CLUSTER_LABEL).mean() * 100),
                "fallback_pct": float((split_df[cluster_col] == NEW_CLUSTER_LABEL).mean() * 100),
                "clusters_observados": int(split_df[cluster_col].nunique()),
            }
        )
    return rows


def describe_clusters(
    df: pd.DataFrame, cluster_col: str, kind: str, top_n: int = 12
) -> list[dict[str, Any]]:
    """Describe clusters en train sin usar target."""
    train_df = df[df["split"] == "train"].copy()
    rows = []
    for cluster, group in train_df.groupby(cluster_col, dropna=False):
        if cluster == NEW_CLUSTER_LABEL:
            continue
        row: dict[str, Any] = {
            "tipo": kind,
            "cluster": str(cluster),
            "ordenes_train": int(len(group)),
            "dist_mediana": float(group["dist_haversine_km"].median()),
            "flete_mediano": float(group["flete_total"].median()),
            "mismo_estado_pct": float(group["mismo_estado"].mean() * 100),
            "customer_state_top": mode_or_unknown(group["customer_state"]),
            "seller_state_top": mode_or_unknown(group["seller_state"]),
            "categoria_top": mode_or_unknown(group["categoria_principal"]),
        }
        if kind == "seller":
            row["sellers_train"] = int(group["seller_id"].nunique())
        if kind == "ruta":
            row["rutas_train"] = int(group["ruta_estado"].nunique())
        rows.append(row)
    return sorted(rows, key=lambda x: x["ordenes_train"], reverse=True)[:top_n]


def to_markdown(rows: list[dict[str, Any]] | pd.DataFrame, digits: int = 3) -> str:
    """Convierte filas a tabla Markdown."""
    df = pd.DataFrame(rows) if isinstance(rows, list) else rows.copy()
    if df.empty:
        return "_Sin filas._"
    headers = list(df.columns)
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for _, row in df.iterrows():
        values = []
        for col in headers:
            value = row[col]
            if pd.isna(value):
                values.append("NA")
            elif isinstance(value, (float, np.floating)):
                values.append(f"{float(value):,.{digits}f}")
            elif isinstance(value, (int, np.integer)):
                values.append(f"{int(value):,}")
            else:
                values.append(str(value))
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# 4. Reporte
# --------------------------------------------------------------------------- #
def render_report(metrics: dict[str, Any]) -> str:
    """Renderiza el reporte Markdown del experimento."""
    val_table = pd.DataFrame(metrics["comparison"]).sort_values("mae_val")
    val_table["delta_mae_val_vs_baseline"] = (
        val_table["mae_val"] - metrics["baseline"]["metrics"]["val"]["mae"]
    )
    val_table["delta_mae_test_vs_baseline"] = (
        val_table["mae_test"] - metrics["baseline"]["metrics"]["test"]["mae"]
    )
    best = metrics["best_variant"]
    p90_table = pd.DataFrame(metrics["p90_comparison"])

    lines: list[str] = []
    lines.append("# Fase 2 - Experimento de clustering")
    lines.append("")
    lines.append("## 1. Resumen ejecutivo")
    lines.append("")
    lines.append(
        "Se probo clustering como experimento avanzado, no como requisito del MVP. "
        "Clustering significa agrupar rutas, sellers u ordenes geograficamente "
        "parecidas sin usar una etiqueta objetivo. En este experimento los clusters "
        "se formaron solo con variables M0 o perfiles de train basados en variables "
        "M0; no se uso `dias_entrega_real` para crear los grupos."
    )
    lines.append("")
    lines.append(
        f"El baseline vigente es `random_forest + {SELECTED_FEATURE_SET}` con MAE "
        f"val {metrics['baseline']['metrics']['val']['mae']:.3f} y MAE test "
        f"{metrics['baseline']['metrics']['test']['mae']:.3f}. La mejor variante "
        f"con clustering fue `{best['variant']}` con MAE val "
        f"{best['mae_val']:.3f} y delta val "
        f"{best['delta_mae_val_vs_baseline']:+.3f} dias."
    )
    lines.append("")
    lines.append("## 2. Factibilidad y eleccion del primer experimento")
    lines.append("")
    lines.append(
        "La prueba mas viable era empezar por rutas, porque Fase 2 ya mostro que "
        "`ruta_estado` y `customer_state` tienen senal y cobertura alta. Sellers "
        "tambien se probo, pero con cautela: muchos sellers tienen poco historial, "
        "por eso `seller_id` se uso solo como llave para asignar el cluster, no "
        "como feature cruda. El cluster geografico simple se incluyo como control "
        "para ver si agrupaba mejor que `customer_state`, `seller_state`, "
        "`ruta_estado` y `dist_haversine_km`."
    )
    lines.append("")
    lines.append("## 3. Criterios de exito definidos antes de correr")
    lines.append("")
    for item in metrics["success_criteria"]:
        lines.append(f"- {item}")
    lines.append("")
    lines.append("## 4. Variables usadas para clustering")
    lines.append("")
    lines.append(to_markdown(pd.DataFrame(metrics["cluster_inputs"])))
    lines.append("")
    lines.append("## 5. Comparacion de MAE")
    lines.append("")
    lines.append(
        "MAE significa error absoluto medio: cuantos dias se equivoca el modelo "
        "en promedio. Delta negativo frente al baseline seria mejora."
    )
    lines.append("")
    lines.append(
        to_markdown(
            val_table[
                [
                    "variant",
                    "cluster_type",
                    "k",
                    "mae_val",
                    "delta_mae_val_vs_baseline",
                    "mae_test",
                    "delta_mae_test_vs_baseline",
                    "p90_abs_error_val",
                    "bias_val",
                ]
            ]
        )
    )
    lines.append("")
    lines.append("## 6. Cobertura")
    lines.append("")
    lines.append(
        "Cobertura indica que porcentaje de ordenes pudo recibir un cluster "
        "calculado desde train. Las rutas o sellers nuevos caen en un fallback."
    )
    lines.append("")
    lines.append(to_markdown(pd.DataFrame(metrics["coverage"])))
    lines.append("")
    lines.append("## 7. Interpretacion de clusters")
    lines.append("")
    lines.append(
        "La interpretacion usa solo train y variables M0. No es una explicacion "
        "causal; solo describe que grupos quedaron parecidos para el algoritmo."
    )
    lines.append("")
    lines.append(to_markdown(pd.DataFrame(metrics["cluster_descriptions"])))
    lines.append("")
    lines.append("## 8. Backtesting P90")
    lines.append("")
    lines.append(
        "Se compara la politica P90 del baseline contra la mejor variante de "
        "clustering. P90 significa agregar un margen calculado en validacion para "
        "buscar una promesa conservadora."
    )
    lines.append("")
    lines.append(to_markdown(p90_table))
    lines.append("")
    lines.append("## 9. Validaciones anti-leakage")
    lines.append("")
    for key, value in metrics["anti_leakage"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.append("")
    lines.append("## 10. Costo productivo")
    lines.append("")
    lines.append(
        "Incorporar clusters implicaria mantener un segundo componente: entrenar "
        "y versionar el modelo de clustering, guardar mapas de ruta/seller o un "
        "transformador geografico, definir fallback para rutas y sellers nuevos, "
        "monitorear deriva de perfiles y explicar el significado de cada cluster. "
        "Ese costo solo se justifica si la mejora de MAE y backtesting es clara."
    )
    lines.append("")
    lines.append("## 11. Decision recomendada: incorporar / no incorporar al MVP")
    lines.append("")
    lines.append(f"**Decision recomendada:** {metrics['recommended_decision']}")
    lines.append("")
    lines.append("### Razon")
    lines.append("")
    lines.append(metrics["reason"])
    lines.append("")
    lines.append("### Costo productivo")
    lines.append("")
    lines.append(metrics["productive_cost"])
    lines.append("")
    lines.append("### Plan de integracion si se aprueba")
    lines.append("")
    for item in metrics["integration_plan_if_approved"]:
        lines.append(f"- {item}")
    lines.append("")
    lines.append("## 12. Comando reproducible")
    lines.append("")
    lines.append("```powershell")
    lines.append("venv\\Scripts\\python.exe scripts\\experiment_fase2_clustering.py --k-list 4,8")
    lines.append("```")
    lines.append("")
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# 5. Orquestacion
# --------------------------------------------------------------------------- #
def run(
    data_path: str | Path = DEFAULT_DATA,
    report_path: str | Path = DEFAULT_REPORT,
    metrics_path: str | Path = DEFAULT_METRICS,
    k_list: Iterable[int] = DEFAULT_K_LIST,
) -> dict[str, Any]:
    """Ejecuta el experimento completo y guarda reporte/metricas."""
    data_path = Path(data_path)
    report_path = Path(report_path)
    metrics_path = Path(metrics_path)
    k_values = [int(k) for k in k_list]

    print(f"[1/7] Cargando dataset rolling: {data_path}")
    df = train_fase2.load_dataset(data_path)
    ev.assert_temporal_split(df)
    required_support = {"order_id", "seller_id", "ruta_estado", *BASE_FEATURES}
    missing = required_support - set(df.columns)
    if missing:
        raise ValueError(f"Faltan columnas para clustering: {sorted(missing)}")

    print("[2/7] Entrenando baseline vigente")
    baseline_result = train_and_predict_variant(
        df,
        feature_cols=BASE_FEATURES,
        categorical_cols=BASE_CATEGORICAL,
        pred_col="pred_baseline",
    )
    baseline_frame = baseline_result["prediction_frame"]
    baseline_metrics = baseline_result["metrics"]

    train_df = df[df["split"] == "train"].copy()
    route_profiles = build_route_profiles(train_df)
    seller_profiles = build_seller_profiles(train_df)

    comparison: list[dict[str, Any]] = []
    coverage_rows: list[dict[str, Any]] = []
    variant_frames: dict[str, pd.DataFrame] = {"baseline": baseline_frame}
    cluster_descriptions: list[dict[str, Any]] = []

    print("[3/7] Probando clusters de rutas")
    for k in k_values:
        cluster_col = f"ruta_cluster_k{k}"
        variant_df, _ = add_profile_cluster(
            df,
            route_profiles,
            key_col="ruta_estado",
            cluster_col=cluster_col,
            numeric_cols=ROUTE_NUMERIC_PROFILE_COLS,
            categorical_cols=ROUTE_CATEGORICAL_PROFILE_COLS,
            k=k,
        )
        feature_cols = BASE_FEATURES + [cluster_col]
        categorical_cols = BASE_CATEGORICAL + [cluster_col]
        result = train_and_predict_variant(
            variant_df, feature_cols, categorical_cols, pred_col=f"pred_{cluster_col}"
        )
        pred_df = result["prediction_frame"]
        variant = f"ruta_k{k}"
        variant_frames[variant] = pred_df
        comparison.append(
            summarize_variant(variant, "ruta", k, result["metrics"])
        )
        coverage_rows.extend(
            {"variant": variant, "cluster_type": "ruta", **row}
            for row in coverage_for_cluster(pred_df, cluster_col)
        )
        if k == k_values[0]:
            cluster_descriptions.extend(describe_clusters(pred_df, cluster_col, "ruta"))

    print("[4/7] Probando clusters de sellers")
    for k in k_values:
        cluster_col = f"seller_cluster_k{k}"
        variant_df, _ = add_profile_cluster(
            df,
            seller_profiles,
            key_col="seller_id",
            cluster_col=cluster_col,
            numeric_cols=SELLER_NUMERIC_PROFILE_COLS,
            categorical_cols=SELLER_CATEGORICAL_PROFILE_COLS,
            k=k,
        )
        feature_cols = BASE_FEATURES + [cluster_col]
        categorical_cols = BASE_CATEGORICAL + [cluster_col]
        result = train_and_predict_variant(
            variant_df, feature_cols, categorical_cols, pred_col=f"pred_{cluster_col}"
        )
        pred_df = result["prediction_frame"]
        variant = f"seller_k{k}"
        variant_frames[variant] = pred_df
        comparison.append(
            summarize_variant(variant, "seller", k, result["metrics"])
        )
        coverage_rows.extend(
            {"variant": variant, "cluster_type": "seller", **row}
            for row in coverage_for_cluster(pred_df, cluster_col)
        )
        if k == k_values[0]:
            cluster_descriptions.extend(describe_clusters(pred_df, cluster_col, "seller"))

    print("[5/7] Probando clusters geograficos simples")
    for k in k_values:
        cluster_col = f"geo_cluster_k{k}"
        variant_df = add_geo_cluster(df, cluster_col, k)
        feature_cols = BASE_FEATURES + [cluster_col]
        categorical_cols = BASE_CATEGORICAL + [cluster_col]
        result = train_and_predict_variant(
            variant_df, feature_cols, categorical_cols, pred_col=f"pred_{cluster_col}"
        )
        pred_df = result["prediction_frame"]
        variant = f"geo_k{k}"
        variant_frames[variant] = pred_df
        comparison.append(
            summarize_variant(variant, "geo", k, result["metrics"])
        )
        coverage_rows.extend(
            {"variant": variant, "cluster_type": "geo", **row}
            for row in coverage_for_cluster(pred_df, cluster_col)
        )
        if k == k_values[0]:
            cluster_descriptions.extend(describe_clusters(pred_df, cluster_col, "geo"))

    print("[6/7] Comparando mejor variante y backtesting P90")
    baseline_val_mae = baseline_metrics["val"]["mae"]
    baseline_test_mae = baseline_metrics["test"]["mae"]
    for row in comparison:
        row["delta_mae_val_vs_baseline"] = row["mae_val"] - baseline_val_mae
        row["delta_mae_test_vs_baseline"] = row["mae_test"] - baseline_test_mae

    best_row = min(comparison, key=lambda row: row["mae_val"])
    best_frame = variant_frames[best_row["variant"]]
    best_pred_col = [col for col in best_frame.columns if col.startswith("pred_")][-1]
    baseline_p90 = promise_p90_metrics(baseline_frame, "pred_baseline")
    best_p90 = promise_p90_metrics(best_frame, best_pred_col)
    p90_comparison = [
        {"variant": "baseline", **flatten_p90_metrics(baseline_p90)},
        {"variant": best_row["variant"], **flatten_p90_metrics(best_p90)},
    ]

    improves_val = best_row["delta_mae_val_vs_baseline"] <= -0.02
    degrades_test = best_row["delta_mae_test_vs_baseline"] > 0.03
    p90_worse = (
        best_p90["test"]["cumplimiento"] + 0.002 < baseline_p90["test"]["cumplimiento"]
    )
    recommended_decision = (
        "incorporar al MVP"
        if improves_val and not degrades_test and not p90_worse
        else "no incorporar al MVP"
    )

    reason = build_reason(best_row, improves_val, degrades_test, p90_worse)
    productive_cost = (
        "Alto frente a una feature tabular simple: exige versionar clusters, "
        "fallbacks para llaves nuevas, monitoreo de drift y explicacion adicional "
        "para negocio."
    )
    integration_plan = [
        "Congelar una definicion de cluster y recalcularla solo con train/historial cerrado.",
        "Versionar el artefacto de clustering y el mapa ruta/seller -> cluster.",
        "Definir fallback para rutas o sellers nuevos: cluster `nuevo_o_sin_perfil` o perfil global.",
        "Agregar tests anti-leakage que fallen si el target entra al clustering.",
        "Actualizar documentacion de Fase 2, modelado y backtesting antes de integrarlo.",
        "Integrar solo despues del cierre de Fase 2 MVP, como mejora posterior aprobada.",
    ]

    metrics: dict[str, Any] = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "dataset": str(data_path),
        "target": TARGET,
        "baseline": {
            "modelo": "random_forest",
            "feature_set": SELECTED_FEATURE_SET,
            "metrics": baseline_metrics,
        },
        "success_criteria": [
            "Mejora minima de MAE val: al menos 0.02 dias frente al baseline vigente.",
            "No degradar test de forma relevante: maximo +0.03 dias de MAE test.",
            "No empeorar P90: cumplimiento test no debe caer mas de 0.2 puntos porcentuales.",
            "Cluster interpretable con descripcion operativa simple.",
            "Cobertura suficiente y fallback claro para rutas/sellers nuevos.",
            "Costo productivo razonable frente a la mejora observada.",
        ],
        "cluster_inputs": cluster_input_summary(),
        "comparison": comparison,
        "best_variant": best_row,
        "coverage": coverage_rows,
        "cluster_descriptions": cluster_descriptions,
        "p90_comparison": p90_comparison,
        "recommended_decision": recommended_decision,
        "reason": reason,
        "productive_cost": productive_cost,
        "integration_plan_if_approved": integration_plan,
        "anti_leakage": {
            "target_used_for_clustering": False,
            "forbidden_cluster_inputs_intersection": sorted(
                FORBIDDEN_CLUSTER_INPUTS
                & set(
                    ROUTE_NUMERIC_PROFILE_COLS
                    + ROUTE_CATEGORICAL_PROFILE_COLS
                    + SELLER_NUMERIC_PROFILE_COLS
                    + SELLER_CATEGORICAL_PROFILE_COLS
                    + GEO_CLUSTER_NUMERIC_COLS
                    + GEO_CLUSTER_CATEGORICAL_COLS
                )
            ),
            "seller_id_used_as_regressor_feature": False,
            "seller_id_used_only_as_mapping_key": True,
            "test_used_to_fit_clusters": False,
            "test_used_to_select_variant": False,
            "models_saved": False,
        },
    }

    print("[7/7] Guardando reporte y metricas")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    metrics_path.write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    report_path.write_text(render_report(metrics), encoding="utf-8")
    print(f"      reporte: {report_path}")
    print(f"      metricas: {metrics_path}")
    return metrics


def summarize_variant(
    variant: str, cluster_type: str, k: int, metrics: dict[str, dict[str, float]]
) -> dict[str, Any]:
    """Aplana metricas principales de una variante."""
    return {
        "variant": variant,
        "cluster_type": cluster_type,
        "k": int(k),
        "mae_val": metrics["val"]["mae"],
        "mae_test": metrics["test"]["mae"],
        "p90_abs_error_val": metrics["val"]["p90_abs_error"],
        "p90_abs_error_test": metrics["test"]["p90_abs_error"],
        "bias_val": metrics["val"]["bias_mean"],
        "bias_test": metrics["test"]["bias_mean"],
    }


def flatten_p90_metrics(metrics: dict[str, Any]) -> dict[str, float]:
    """Aplana metricas P90 para reporte."""
    test = metrics["test"]
    return {
        "margen_p90_val": metrics["margen_p90_val"],
        "cumplimiento_test": test["cumplimiento"] * 100,
        "incumplimiento_test": test["incumplimiento"] * 100,
        "colchon_promedio_test": test["colchon_promedio"],
        "colchon_mediano_test": test["colchon_mediano"],
        "promesa_promedio_test": test["promesa_promedio"],
        "promesa_mediana_test": test["promesa_mediana"],
    }


def build_reason(
    best_row: dict[str, Any],
    improves_val: bool,
    degrades_test: bool,
    p90_worse: bool,
) -> str:
    """Construye razon textual de decision."""
    if improves_val and not degrades_test and not p90_worse:
        return (
            f"La variante `{best_row['variant']}` supera el umbral de mejora en val "
            "sin degradar test ni P90. Aun asi, por costo productivo, conviene "
            "integrarla solo como mejora posterior y con tests adicionales."
        )
    blockers = []
    if not improves_val:
        blockers.append(
            "no supera el umbral minimo de mejora en MAE val frente al baseline vigente"
        )
    if degrades_test:
        blockers.append("degrada MAE test mas de lo aceptado")
    if p90_worse:
        blockers.append("empeora el cumplimiento P90 en test")
    return (
        f"La mejor variante (`{best_row['variant']}`) "
        + ", ".join(blockers)
        + ". Como el MVP ya funciona sin clustering, la complejidad adicional no "
        "queda justificada."
    )


def cluster_input_summary() -> list[dict[str, str]]:
    """Resume variables usadas en cada familia de clustering."""
    return [
        {
            "cluster": "ruta",
            "variables": ", ".join(
                ROUTE_NUMERIC_PROFILE_COLS + ROUTE_CATEGORICAL_PROFILE_COLS
            ),
            "usa_target": "no",
            "lectura": "perfil de origen-destino por distancia, costo y volumen de train",
        },
        {
            "cluster": "seller",
            "variables": ", ".join(
                SELLER_NUMERIC_PROFILE_COLS + SELLER_CATEGORICAL_PROFILE_COLS
            ),
            "usa_target": "no",
            "lectura": "perfil operativo del seller en train; seller_id solo asigna el grupo",
        },
        {
            "cluster": "geo",
            "variables": ", ".join(GEO_CLUSTER_NUMERIC_COLS + GEO_CLUSTER_CATEGORICAL_COLS),
            "usa_target": "no",
            "lectura": "agrupacion simple por distancia, mismo estado, destino y origen",
        },
    ]


def parse_k_list(raw: str) -> list[int]:
    """Parsea lista de k separada por comas."""
    values = [int(value.strip()) for value in raw.split(",") if value.strip()]
    if any(value < 2 for value in values):
        raise ValueError("Todos los k deben ser >= 2")
    return values


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Experimento de clustering para Fase 2 de Olist"
    )
    parser.add_argument("--data", default=str(DEFAULT_DATA))
    parser.add_argument("--report", default=str(DEFAULT_REPORT))
    parser.add_argument("--metrics", default=str(DEFAULT_METRICS))
    parser.add_argument(
        "--k-list",
        default=",".join(str(k) for k in DEFAULT_K_LIST),
        help="Lista de numeros de clusters separados por coma.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run(args.data, args.report, args.metrics, parse_k_list(args.k_list))
