"""Evaluación de los modelos de P1 (entrega tardía) — Etapa 4.

Métricas para clasificación binaria desbalanceada (tasa base 8.11%, D-19):
PR-AUC (principal), ROC-AUC, F1/precision/recall a un umbral operativo y
calibración (Brier). Incluye:

  - selección de umbral por F1 sobre validación (sin tocar test),
  - análisis de errores por región y por *cold-start* de vendedores,
  - auditoría de fuga (R-12): peso de `tasa_vendedor` y verificación de que
    ninguna columna [POST] entró como feature,
  - graficado (curvas PR/ROC, calibración, importancias, error regional) con
    exportación a `reports/figures_modelado_etapa4/`.

Las funciones no dependen de un modelo concreto: reciben `y` y probabilidades,
o un `Pipeline([("prep", ...), ("clf", ...)])` ya entrenado.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # backend sin display, para entornos headless
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.calibration import calibration_curve
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)

# --------------------------------------------------------------------------- #
# Mapa de regiones de Brasil (para el análisis de errores por región)
# --------------------------------------------------------------------------- #
REGIONES = {
    "Norte": ["AC", "AP", "AM", "PA", "RO", "RR", "TO"],
    "Nordeste": ["AL", "BA", "CE", "MA", "PB", "PE", "PI", "RN", "SE"],
    "Centro-Oeste": ["DF", "GO", "MT", "MS"],
    "Sudeste": ["ES", "MG", "RJ", "SP"],
    "Sul": ["PR", "RS", "SC"],
}
ESTADO_A_REGION = {e: r for r, estados in REGIONES.items() for e in estados}

# Columnas que NO pueden ser features (información [POST], D-21 / R-12).
COLS_POST_PROHIBIDAS = {
    "dias_vs_promesa",
    "order_delivered_customer_date",
    "order_delivered_carrier_date",
    "delivery_days",
    "delivery_delay_days",
    "is_late_delivery",
    "avg_review_score",
    "is_dissatisfied",
}


# --------------------------------------------------------------------------- #
# Selección de umbral y métricas
# --------------------------------------------------------------------------- #
def seleccionar_umbral_f1(y_true: np.ndarray, proba: np.ndarray) -> float:
    """Umbral que maximiza F1 sobre el conjunto dado (se usa en `val`)."""
    prec, rec, thr = precision_recall_curve(y_true, proba)
    if len(thr) == 0:
        return 0.5
    f1 = 2 * prec[:-1] * rec[:-1] / (prec[:-1] + rec[:-1] + 1e-12)
    return float(thr[int(np.nanargmax(f1))])


def umbral_para_recall(y_true: np.ndarray, proba: np.ndarray, recall_objetivo: float = 0.5) -> float:
    """Umbral más alto (mayor precisión) que aún alcanza `recall_objetivo`.

    Punto de operación "alta cobertura": útil cuando el negocio prioriza
    detectar órdenes en riesgo (recall) sobre la precisión de la alerta.
    """
    prec, rec, thr = precision_recall_curve(y_true, proba)
    if len(thr) == 0:
        return 0.5
    # Contrato de sklearn: thr[i] <-> prec[i], rec[i]; `rec` trae un valor extra (=0)
    # al final sin umbral, por eso se alinea con rec[:-1]. El recall decrece al subir
    # el umbral, así que el mayor umbral con recall>=objetivo da la mejor precisión
    # cumpliendo el recall objetivo.
    candidatos = [t for t, r in zip(thr, rec[:-1]) if r >= recall_objetivo]
    return float(max(candidatos)) if candidatos else float(thr[0])


def calcular_metricas(y_true: np.ndarray, proba: np.ndarray, umbral: float) -> dict:
    """Diccionario de métricas a un umbral dado."""
    y_pred = (proba >= umbral).astype(int)
    return {
        "pr_auc": float(average_precision_score(y_true, proba)),
        "roc_auc": float(roc_auc_score(y_true, proba)),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "brier": float(brier_score_loss(y_true, proba)),
        "umbral": float(umbral),
        "tasa_base": float(np.mean(y_true)),
        "frac_alertas": float(np.mean(y_pred)),
    }


# --------------------------------------------------------------------------- #
# Análisis de errores
# --------------------------------------------------------------------------- #
def analisis_por_region(
    df: pd.DataFrame, y_true: np.ndarray, y_pred: np.ndarray
) -> pd.DataFrame:
    """Recall y volumen de tardanza por región (foco Norte/Nordeste)."""
    tmp = df.copy()
    tmp["_y"] = np.asarray(y_true)
    tmp["_pred"] = np.asarray(y_pred)
    tmp["region"] = tmp["customer_state"].map(ESTADO_A_REGION).fillna("Otro")

    filas = []
    for region, g in tmp.groupby("region"):
        positivos = g["_y"].sum()
        recall = (g.loc[g["_y"] == 1, "_pred"].mean() if positivos else np.nan)
        filas.append(
            {
                "region": region,
                "n_ordenes": int(len(g)),
                "tasa_tarde_real": float(g["_y"].mean()),
                "recall_tarde": float(recall) if positivos else np.nan,
                "n_tarde": int(positivos),
            }
        )
    return pd.DataFrame(filas).sort_values("tasa_tarde_real", ascending=False)


def analisis_cold_start(
    df: pd.DataFrame, y_true: np.ndarray, proba: np.ndarray, umbral: float
) -> pd.DataFrame:
    """Desempeño separando vendedores con y sin historial suficiente."""
    tmp = df.copy()
    tmp["_y"] = np.asarray(y_true)
    tmp["_proba"] = np.asarray(proba)
    filas = []
    for valor, etiqueta in [(0, "con historial"), (1, "cold-start (sin historial)")]:
        g = tmp[tmp["sin_historial_vendedor"] == valor]
        if g.empty or g["_y"].nunique() < 2:  # ROC/PR-AUC requieren ambas clases
            continue
        m = calcular_metricas(g["_y"].values, g["_proba"].values, umbral)
        filas.append(
            {
                "segmento": etiqueta,
                "n_ordenes": int(len(g)),
                "tasa_tarde_real": m["tasa_base"],
                "pr_auc": m["pr_auc"],
                "roc_auc": m["roc_auc"],
                "recall": m["recall"],
                "precision": m["precision"],
            }
        )
    return pd.DataFrame(filas)


# --------------------------------------------------------------------------- #
# Auditoría de fuga (R-12)
# --------------------------------------------------------------------------- #
def assert_sin_features_post(x_cols: list[str]) -> None:
    """Falla si alguna columna [POST] o el target se coló como feature.

    Une la lista local con la lista canónica de columnas [POST] de la Etapa 3
    (`build_dataset.COLS_POST`) para no depender de una lista parcial, y añade el
    target `entrega_tarde`. Es el candado central de R-12.
    """
    prohibidas = set(COLS_POST_PROHIBIDAS) | {"entrega_tarde"}
    try:
        from src.features.build_dataset import COLS_POST

        prohibidas |= set(COLS_POST)
    except Exception:
        pass
    intrusas = set(x_cols) & prohibidas
    assert not intrusas, f"FUGA: features [POST]/target en el modelo: {sorted(intrusas)}"


def importancias_modelo(modelo, top: int = 20) -> pd.Series:
    """Importancias (boosting) o |coeficientes| (lineal) por feature de salida."""
    prep = modelo.named_steps["prep"]
    clf = modelo.named_steps["clf"]
    nombres = prep.get_feature_names_out()
    if hasattr(clf, "feature_importances_"):
        imp = np.asarray(clf.feature_importances_, dtype=float)
    elif hasattr(clf, "coef_"):
        imp = np.abs(np.asarray(clf.coef_, dtype=float).ravel())
    else:
        raise ValueError("El estimador no expone importancias ni coeficientes.")
    return pd.Series(imp, index=nombres).sort_values(ascending=False).head(top)


def peso_tasa_vendedor(modelo) -> float:
    """Fracción de la importancia total que recae en `tasa_vendedor` (R-12)."""
    serie = importancias_modelo(modelo, top=10**6)
    total = serie.sum()
    if total <= 0:
        return float("nan")
    tasa = serie[[n for n in serie.index if "tasa_vendedor" in n]].sum()
    return float(tasa / total)


# --------------------------------------------------------------------------- #
# Graficado (exporta PNG a reports/figures_modelado_etapa4/)
# --------------------------------------------------------------------------- #
def _guardar(fig, fig_dir: Path, nombre: str) -> None:
    fig_dir.mkdir(parents=True, exist_ok=True)
    fig.savefig(fig_dir / nombre, dpi=150, bbox_inches="tight")
    plt.close(fig)


def graficar_curvas_pr_roc(
    resultados: dict, y_true: np.ndarray, fig_dir: Path
) -> None:
    """Curvas PR y ROC superpuestas para todos los modelos (en test)."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    base = float(np.mean(y_true))
    ax1.axhline(base, ls="--", c="gray", lw=1, label=f"azar (tasa base={base:.3f})")
    ax2.plot([0, 1], [0, 1], ls="--", c="gray", lw=1, label="azar")
    for nombre, proba in resultados.items():
        prec, rec, _ = precision_recall_curve(y_true, proba)
        ap = average_precision_score(y_true, proba)
        ax1.plot(rec, prec, lw=2, label=f"{nombre} (PR-AUC={ap:.3f})")
        fpr, tpr, _ = roc_curve(y_true, proba)
        auc = roc_auc_score(y_true, proba)
        ax2.plot(fpr, tpr, lw=2, label=f"{nombre} (ROC-AUC={auc:.3f})")
    ax1.set(xlabel="Recall", ylabel="Precision", title="Curva Precision-Recall (test)")
    ax2.set(xlabel="FPR", ylabel="TPR", title="Curva ROC (test)")
    ax1.legend(fontsize=8)
    ax2.legend(fontsize=8)
    _guardar(fig, fig_dir, "01_curvas_pr_roc.png")


def graficar_calibracion(
    resultados: dict, y_true: np.ndarray, fig_dir: Path
) -> None:
    fig, ax = plt.subplots(figsize=(6, 6))
    ax.plot([0, 1], [0, 1], ls="--", c="gray", label="calibración perfecta")
    for nombre, proba in resultados.items():
        frac_pos, media_pred = calibration_curve(y_true, proba, n_bins=10, strategy="quantile")
        ax.plot(media_pred, frac_pos, "o-", lw=2, label=nombre)
    ax.set(
        xlabel="Probabilidad predicha media",
        ylabel="Fracción real de tardanza",
        title="Curva de calibración (test)",
    )
    ax.legend(fontsize=8)
    _guardar(fig, fig_dir, "02_calibracion.png")


def graficar_importancias(serie: pd.Series, titulo: str, fig_dir: Path, nombre: str) -> None:
    fig, ax = plt.subplots(figsize=(8, 6))
    serie.iloc[::-1].plot.barh(ax=ax, color="#2b6cb0")
    ax.set(title=titulo, xlabel="Importancia")
    _guardar(fig, fig_dir, nombre)


def graficar_error_regional(tabla: pd.DataFrame, fig_dir: Path) -> None:
    fig, ax = plt.subplots(figsize=(8, 5))
    t = tabla[tabla["region"] != "Otro"].set_index("region")
    t[["tasa_tarde_real", "recall_tarde"]].plot.bar(ax=ax)
    ax.set(title="Tardanza real vs recall del modelo por región (test)", ylabel="Proporción")
    ax.legend(["Tasa real de tardanza", "Recall del modelo"], fontsize=8)
    plt.xticks(rotation=0)
    _guardar(fig, fig_dir, "03_error_por_region.png")
