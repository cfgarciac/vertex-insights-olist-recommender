"""Evaluacion de modelos de Fase 2 para regresion de dias_entrega_real.

Este modulo contiene piezas reutilizables para Chat E:

  - baselines de mediana calculados solo con train;
  - metricas de regresion en dias;
  - candado anti-leakage para columnas prohibidas;
  - analisis de error por estado destino y ruta estado-estado;
  - revision simple de multicolinealidad por correlaciones.

Baseline significa regla simple de comparacion. Sirve como piso: un modelo de
machine learning solo se justifica si mejora estas reglas sencillas.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from typing import Iterable

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, median_absolute_error, mean_squared_error


TARGET = "dias_entrega_real"

PROHIBITED_AS_FEATURES = {
    TARGET,
    "order_delivered_customer_date",
    "order_delivered_carrier_date",
    "delivery_days",
    "delivery_delay_days",
    "is_late_delivery",
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
    "entrega_tarde",
    "dias_vs_promesa",
    "seller_id",
    "order_id",
    "order_purchase_timestamp",
    "split",
}


# --------------------------------------------------------------------------- #
# 1. Candados de contrato
# --------------------------------------------------------------------------- #
def assert_no_forbidden_features(x_cols: Iterable[str]) -> None:
    """Falla si una columna prohibida entra a X_COLS."""
    intrusas = set(x_cols) & PROHIBITED_AS_FEATURES
    if intrusas:
        raise AssertionError(
            "Features prohibidas detectadas en Fase 2: "
            f"{sorted(intrusas)}"
        )


def assert_temporal_split(df: pd.DataFrame) -> None:
    """Valida que train, val y test respeten el orden temporal."""
    required = {"split", "order_purchase_timestamp"}
    missing = required - set(df.columns)
    if missing:
        raise AssertionError(f"Faltan columnas para validar split: {sorted(missing)}")

    tmp = df.copy()
    tmp["order_purchase_timestamp"] = pd.to_datetime(
        tmp["order_purchase_timestamp"], errors="coerce"
    )
    observed = set(tmp["split"].unique())
    if observed != {"train", "val", "test"}:
        raise AssertionError(f"Splits inesperados: {sorted(observed)}")

    max_train = tmp.loc[tmp["split"] == "train", "order_purchase_timestamp"].max()
    min_val = tmp.loc[tmp["split"] == "val", "order_purchase_timestamp"].min()
    max_val = tmp.loc[tmp["split"] == "val", "order_purchase_timestamp"].max()
    min_test = tmp.loc[tmp["split"] == "test", "order_purchase_timestamp"].min()
    if not (max_train <= min_val <= max_val <= min_test):
        raise AssertionError("El split temporal no respeta train <= val <= test")


# --------------------------------------------------------------------------- #
# 2. Baselines de mediana
# --------------------------------------------------------------------------- #
@dataclass
class GlobalMedianBaseline:
    """Predice siempre la mediana global del target en train."""

    median_: float | None = None

    def fit(self, X: pd.DataFrame, y: Iterable[float]):
        self.median_ = float(pd.Series(y).median())
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        if self.median_ is None:
            raise ValueError("El baseline debe entrenarse con fit antes de predecir")
        return np.full(len(X), self.median_, dtype="float64")


@dataclass
class CustomerStateMedianBaseline:
    """Mediana por customer_state con fallback a mediana global de train."""

    medians_: pd.Series | None = None
    global_median_: float | None = None

    def fit(self, X: pd.DataFrame, y: Iterable[float]):
        frame = X[["customer_state"]].copy()
        frame[TARGET] = np.asarray(y, dtype="float64")
        self.global_median_ = float(frame[TARGET].median())
        self.medians_ = frame.groupby("customer_state")[TARGET].median()
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        if self.medians_ is None or self.global_median_ is None:
            raise ValueError("El baseline debe entrenarse con fit antes de predecir")
        return (
            X["customer_state"]
            .map(self.medians_)
            .fillna(self.global_median_)
            .to_numpy(dtype="float64")
        )


@dataclass
class RouteStateMedianBaseline:
    """Mediana por ruta_estado con fallback customer_state y luego global."""

    route_medians_: pd.Series | None = None
    customer_medians_: pd.Series | None = None
    global_median_: float | None = None

    def fit(self, X: pd.DataFrame, y: Iterable[float]):
        frame = X[["ruta_estado", "customer_state"]].copy()
        frame[TARGET] = np.asarray(y, dtype="float64")
        self.global_median_ = float(frame[TARGET].median())
        self.route_medians_ = frame.groupby("ruta_estado")[TARGET].median()
        self.customer_medians_ = frame.groupby("customer_state")[TARGET].median()
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        if (
            self.route_medians_ is None
            or self.customer_medians_ is None
            or self.global_median_ is None
        ):
            raise ValueError("El baseline debe entrenarse con fit antes de predecir")
        route_pred = X["ruta_estado"].map(self.route_medians_)
        customer_pred = X["customer_state"].map(self.customer_medians_)
        return (
            route_pred.fillna(customer_pred)
            .fillna(self.global_median_)
            .to_numpy(dtype="float64")
        )


def build_baselines() -> dict[str, object]:
    """Devuelve los baselines aprobados para Fase 2."""
    return {
        "mediana_global_train": GlobalMedianBaseline(),
        "mediana_customer_state_train": CustomerStateMedianBaseline(),
        "mediana_ruta_estado_train": RouteStateMedianBaseline(),
    }


# --------------------------------------------------------------------------- #
# 3. Metricas
# --------------------------------------------------------------------------- #
def regression_metrics(y_true: Iterable[float], y_pred: Iterable[float]) -> dict[str, float]:
    """Calcula metricas de regresion interpretables en dias."""
    y_true_arr = np.asarray(y_true, dtype="float64")
    y_pred_arr = np.asarray(y_pred, dtype="float64")
    abs_error = np.abs(y_true_arr - y_pred_arr)
    return {
        "mae": float(mean_absolute_error(y_true_arr, y_pred_arr)),
        "medae": float(median_absolute_error(y_true_arr, y_pred_arr)),
        "rmse": float(sqrt(mean_squared_error(y_true_arr, y_pred_arr))),
        "p90_abs_error": float(np.quantile(abs_error, 0.90)),
        "bias_mean": float(np.mean(y_pred_arr - y_true_arr)),
    }


def evaluate_predictions_by_split(
    df: pd.DataFrame, prediction_col: str, target: str = TARGET
) -> dict[str, dict[str, float]]:
    """Calcula metricas por split para una columna de prediccion."""
    output: dict[str, dict[str, float]] = {}
    for split in ["train", "val", "test"]:
        split_df = df[df["split"] == split]
        output[split] = regression_metrics(split_df[target], split_df[prediction_col])
    return output


def error_by_group(
    df: pd.DataFrame,
    y_pred: Iterable[float],
    group_col: str,
    min_n: int = 100,
    target: str = TARGET,
) -> pd.DataFrame:
    """Resume error por grupo con volumen suficiente."""
    tmp = df[[group_col, target]].copy()
    tmp["_pred"] = np.asarray(y_pred, dtype="float64")
    tmp["_abs_error"] = (tmp[target] - tmp["_pred"]).abs()
    tmp["_error"] = tmp["_pred"] - tmp[target]
    grouped = (
        tmp.groupby(group_col, dropna=False)
        .agg(
            ordenes=(target, "size"),
            target_medio=(target, "mean"),
            pred_medio=("_pred", "mean"),
            mae=("_abs_error", "mean"),
            medae=("_abs_error", "median"),
            p90_abs_error=("_abs_error", lambda x: x.quantile(0.90)),
            bias_mean=("_error", "mean"),
        )
        .reset_index()
    )
    grouped = grouped[grouped["ordenes"] >= min_n]
    return grouped.sort_values(["mae", "ordenes"], ascending=[False, False])


# --------------------------------------------------------------------------- #
# 4. Multicolinealidad
# --------------------------------------------------------------------------- #
def correlation_pairs(
    df: pd.DataFrame, columns: Iterable[str], method: str = "spearman"
) -> pd.DataFrame:
    """Devuelve pares de features numericas ordenados por correlacion absoluta."""
    available = [
        col
        for col in columns
        if col in df.columns and pd.api.types.is_numeric_dtype(df[col])
    ]
    if len(available) < 2:
        return pd.DataFrame(
            columns=["feature_a", "feature_b", "correlation", "abs_correlation"]
        )
    corr = df[available].corr(method=method)
    rows = []
    for i, left in enumerate(available):
        for right in available[i + 1 :]:
            value = corr.loc[left, right]
            rows.append(
                {
                    "feature_a": left,
                    "feature_b": right,
                    "correlation": float(value),
                    "abs_correlation": float(abs(value)),
                    "lectura": (
                        "alta"
                        if abs(value) >= 0.70
                        else "moderada"
                        if abs(value) >= 0.40
                        else "baja"
                    ),
                }
            )
    return (
        pd.DataFrame(rows)
        .sort_values(["abs_correlation", "feature_a", "feature_b"], ascending=False)
        .reset_index(drop=True)
    )

