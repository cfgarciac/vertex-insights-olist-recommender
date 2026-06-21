"""Entrenamiento y selección de modelos de P1 (entrega tardía) — Etapa 4.

Orquesta el modelado completo sobre la tabla analítica de la Etapa 3:

  1. Carga la tabla y separa train/val/test por la columna `split` (temporal).
  2. Mide dos baselines (clase mayoritaria y regla de negocio) como piso.
  3. Para cada familia (Regresión Logística y XGBoost) entrena una pequeña
     rejilla de candidatos encadenados al preprocesador de la Etapa 3
     (`Pipeline([("prep", build_preprocessor()), ("clf", estimador)])`),
     ajustando SOLO en train, y elige el mejor candidato por PR-AUC en `val`.
     No se usa validación cruzada aleatoria: reintroduciría fuga temporal
     (D-25); la selección mira el split temporal `val`.
  4. Fija el umbral operativo por F1 sobre `val` y selecciona el candidato
     global por PR-AUC en `val` (sin tocar `test`). Calcula además un punto de
     operación de "alta cobertura" (recall objetivo) para la lectura de negocio.
  5. Reporta una sola vez en `test`, audita la fuga de `tasa_vendedor` (R-12) y
     analiza errores por región y *cold-start*.
  6. Serializa el modelo elegido en `artifacts/modelo_p1.joblib` y vuelca las
     métricas en `reports/etapa4_metrics.json` + figuras en
     `reports/figures_modelado_etapa4/`.

Ejecución:
    python -m src.models.train
    python src/models/train.py --data data/processed/orders_p1_features.csv
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

# Hacer importable el paquete `src` al correr como script suelto.
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sklearn.linear_model import LogisticRegression  # noqa: E402
from sklearn.metrics import average_precision_score  # noqa: E402
from sklearn.pipeline import Pipeline  # noqa: E402
from xgboost import XGBClassifier  # noqa: E402

from src.features.build_dataset import (  # noqa: E402
    CATEGORICAL_FEATURES,
    NUMERIC_FEATURES,
    build_preprocessor,
)
from src.models import baseline as bl  # noqa: E402
from src.models import evaluate as ev  # noqa: E402

RANDOM_STATE = 42
RECALL_OBJETIVO = 0.50  # punto de operación de alta cobertura para el negocio
DEFAULT_DATA = ROOT / "data" / "processed" / "orders_p1_features.csv"
ARTIFACT = ROOT / "artifacts" / "modelo_p1.joblib"
REPORTS = ROOT / "reports"
FIG_DIR = REPORTS / "figures_modelado_etapa4"
TARGET = "entrega_tarde"
X_COLS = NUMERIC_FEATURES + CATEGORICAL_FEATURES


# --------------------------------------------------------------------------- #
# Carga de datos
# --------------------------------------------------------------------------- #
def cargar_splits(path: Path):
    """Carga la tabla analítica y la separa por `split` (train/val/test)."""
    df = pd.read_csv(path)
    faltan = {TARGET, "split", *X_COLS} - set(df.columns)
    if faltan:
        raise ValueError(f"Faltan columnas en {path}: {sorted(faltan)}")
    ev.assert_sin_features_post(X_COLS)  # candado anti-fuga (R-12)
    train = df[df["split"] == "train"].reset_index(drop=True)
    val = df[df["split"] == "val"].reset_index(drop=True)
    test = df[df["split"] == "test"].reset_index(drop=True)
    return df, train, val, test


# --------------------------------------------------------------------------- #
# Definición de modelos
# --------------------------------------------------------------------------- #
def _logistica(C: float) -> Pipeline:
    return Pipeline(
        [
            ("prep", build_preprocessor()),
            (
                "clf",
                LogisticRegression(
                    class_weight="balanced", max_iter=1000, C=C, random_state=RANDOM_STATE
                ),
            ),
        ]
    )


def _xgboost(spw: float, **kw) -> Pipeline:
    params = dict(
        n_estimators=300,
        max_depth=5,
        learning_rate=0.05,
        subsample=0.9,
        colsample_bytree=0.9,
        reg_lambda=1.0,
        min_child_weight=1,
        scale_pos_weight=spw,
        eval_metric="aucpr",
        tree_method="hist",
        n_jobs=-1,
        random_state=RANDOM_STATE,
    )
    params.update(kw)
    return Pipeline([("prep", build_preprocessor()), ("clf", XGBClassifier(**params))])


def construir_candidatos(y_train: np.ndarray) -> dict[str, list[tuple[str, Pipeline]]]:
    """Rejilla pequeña por familia; selección por PR-AUC en `val`."""
    n_neg, n_pos = int(np.sum(y_train == 0)), int(np.sum(y_train == 1))
    spw = n_neg / max(n_pos, 1)
    return {
        "logistic_regression": [
            ("lr_C1.0", _logistica(1.0)),
            ("lr_C0.3", _logistica(0.3)),
        ],
        "xgboost": [
            ("xgb_d4_l2", _xgboost(spw, max_depth=4, reg_lambda=2.0, min_child_weight=5)),
            (
                "xgb_d6_l5",
                _xgboost(spw, max_depth=6, n_estimators=350, reg_lambda=5.0,
                         min_child_weight=10, subsample=0.8, colsample_bytree=0.8),
            ),
        ],
    }


def construir_modelos(y_train: np.ndarray) -> dict[str, Pipeline]:
    """Configuración por defecto (primer candidato de cada familia).

    La usan los tests; `run()` explora la rejilla completa de
    `construir_candidatos` y elige por PR-AUC en `val`.
    """
    return {familia: lista[0][1] for familia, lista in construir_candidatos(y_train).items()}


def proba_positiva(modelo, X) -> np.ndarray:
    return modelo.predict_proba(X)[:, 1]


# --------------------------------------------------------------------------- #
# Orquestación
# --------------------------------------------------------------------------- #
def run(data_path: Path) -> dict:
    print(f"[1/6] Cargando tabla analitica: {data_path}")
    df, train, val, test = cargar_splits(data_path)
    y_tr, y_va, y_te = train[TARGET].values, val[TARGET].values, test[TARGET].values
    print(f"      filas: total={len(df):,} train={len(train):,} val={len(val):,} test={len(test):,}")
    print(
        f"      tasa_base: total={df[TARGET].mean():.4f} train={y_tr.mean():.4f} "
        f"val={y_va.mean():.4f} test={y_te.mean():.4f}  (cae con el tiempo: R-14)"
    )

    resultados: dict[str, dict] = {}
    proba_val: dict[str, np.ndarray] = {}
    proba_test: dict[str, np.ndarray] = {}

    # --- Baselines ------------------------------------------------------- #
    print("[2/6] Baselines (piso de comparacion) ...")
    for nombre, modelo in [
        ("baseline_mayoritaria", bl.BaselineClaseMayoritaria()),
        ("baseline_regla", bl.BaselineReglaDistanciaEstado()),
    ]:
        modelo.fit(train[X_COLS], y_tr)
        p_va, p_te = proba_positiva(modelo, val[X_COLS]), proba_positiva(modelo, test[X_COLS])
        umbral = ev.seleccionar_umbral_f1(y_va, p_va)
        resultados[nombre] = {
            "val": ev.calcular_metricas(y_va, p_va, umbral),
            "test": ev.calcular_metricas(y_te, p_te, umbral),
        }
        proba_test[nombre] = p_te
        print(f"      {nombre:22s} PR-AUC(test)={resultados[nombre]['test']['pr_auc']:.4f}")

    # --- Modelos reales: rejilla por familia, selección por PR-AUC(val) -- #
    print("[3/6] Entrenando clasificadores (rejilla; fit solo en train) ...")
    candidatos = construir_candidatos(y_tr)
    entrenados: dict[str, Pipeline] = {}
    busqueda: dict[str, dict] = {}
    for familia, lista in candidatos.items():
        evaluados = []
        for label, pipe in lista:
            pipe.fit(train[X_COLS], y_tr)
            ap = average_precision_score(y_va, proba_positiva(pipe, val[X_COLS]))
            evaluados.append((label, float(ap), pipe))
            print(f"      {familia:20s} {label:12s} PR-AUC(val)={ap:.4f}")
        label_best, ap_best, pipe_best = max(evaluados, key=lambda t: t[1])
        entrenados[familia] = pipe_best
        busqueda[familia] = {"elegido": label_best, "pr_auc_val": {l: round(a, 4) for l, a, _ in evaluados}}
        p_va, p_te = proba_positiva(pipe_best, val[X_COLS]), proba_positiva(pipe_best, test[X_COLS])
        umbral = ev.seleccionar_umbral_f1(y_va, p_va)  # umbral fijado en val
        resultados[familia] = {
            "config": label_best,
            "val": ev.calcular_metricas(y_va, p_va, umbral),
            "test": ev.calcular_metricas(y_te, p_te, umbral),
        }
        proba_val[familia], proba_test[familia] = p_va, p_te
        print(
            f"      -> {familia}: {label_best} | PR-AUC(test)={resultados[familia]['test']['pr_auc']:.4f} "
            f"ROC-AUC(test)={resultados[familia]['test']['roc_auc']:.4f} "
            f"recall(test)={resultados[familia]['test']['recall']:.3f}"
        )

    # --- Selección global por PR-AUC en val ------------------------------ #
    print("[4/6] Seleccion del candidato (PR-AUC en val) ...")
    mejor = max(entrenados, key=lambda n: resultados[n]["val"]["pr_auc"])
    modelo_mejor = entrenados[mejor]
    umbral_f1 = resultados[mejor]["val"]["umbral"]
    umbral_cobertura = ev.umbral_para_recall(y_va, proba_val[mejor], RECALL_OBJETIVO)
    op_cobertura = ev.calcular_metricas(y_te, proba_test[mejor], umbral_cobertura)
    print(f"      candidato: {mejor} ({resultados[mejor]['config']}) | umbral F1={umbral_f1:.3f}")
    print(
        f"      punto alta cobertura (umbral={umbral_cobertura:.3f}): "
        f"recall(test)={op_cobertura['recall']:.3f} precision(test)={op_cobertura['precision']:.3f}"
    )

    # --- Auditoría de fuga (R-12) y análisis de errores ------------------ #
    print("[5/6] Auditoria de fuga y analisis de errores (test) ...")
    peso_tasa = ev.peso_tasa_vendedor(modelo_mejor)
    importancias = ev.importancias_modelo(modelo_mejor, top=20)
    print(f"      peso de `tasa_vendedor` en el modelo: {peso_tasa*100:.1f}%")
    if max(resultados[mejor]["test"]["roc_auc"], resultados[mejor]["test"]["pr_auc"]) > 0.99:
        print("      ! ALERTA: metrica ~1.0 -> revisar posible fuga antes de confiar.")
    else:
        print("      OK: metricas en rango realista, sin senal de fuga.")

    pred_te_mejor = (proba_test[mejor] >= umbral_f1).astype(int)
    tabla_region = ev.analisis_por_region(test, y_te, pred_te_mejor)
    tabla_cold = ev.analisis_cold_start(test, y_te, proba_test[mejor], umbral_f1)
    print("      tardanza/recall por region (test):")
    print(tabla_region.to_string(index=False))
    print("      desempeno por historial de vendedor (test):")
    print(tabla_cold.to_string(index=False))

    # --- Figuras --------------------------------------------------------- #
    ev.graficar_curvas_pr_roc(proba_test, y_te, FIG_DIR)
    ev.graficar_calibracion(
        {k: v for k, v in proba_test.items() if k in ("logistic_regression", "xgboost")},
        y_te,
        FIG_DIR,
    )
    ev.graficar_importancias(importancias, f"Importancias — {mejor} (test)", FIG_DIR, "04_importancias.png")
    ev.graficar_error_regional(tabla_region, FIG_DIR)

    # --- Serialización del modelo elegido -------------------------------- #
    print("[6/6] Serializando modelo elegido y metricas ...")
    ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {
            "modelo": modelo_mejor,
            "nombre_modelo": mejor,
            "config": resultados[mejor]["config"],
            "umbral_f1": float(umbral_f1),
            "umbral_alta_cobertura": float(umbral_cobertura),
            "numeric_features": NUMERIC_FEATURES,
            "categorical_features": CATEGORICAL_FEATURES,
            "target": TARGET,
            "metricas_test": resultados[mejor]["test"],
        },
        ARTIFACT,
    )
    print(f"      modelo serializado en: {ARTIFACT}")

    salida = {
        "generado": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "tasa_base_total": float(df[TARGET].mean()),
        "tasa_base_por_split": {"train": float(y_tr.mean()), "val": float(y_va.mean()), "test": float(y_te.mean())},
        "tamanos_split": {"train": len(train), "val": len(val), "test": len(test)},
        "busqueda_hiperparametros": busqueda,
        "mejor_modelo": mejor,
        "config_mejor": resultados[mejor]["config"],
        "umbral_f1": float(umbral_f1),
        "operativo_alta_cobertura": {"umbral": float(umbral_cobertura), **op_cobertura},
        "peso_tasa_vendedor": peso_tasa,
        "metricas": resultados,
        "importancias_top": {k: float(v) for k, v in importancias.items()},
        "analisis_region": tabla_region.to_dict(orient="records"),
        "analisis_cold_start": tabla_cold.to_dict(orient="records"),
    }
    REPORTS.mkdir(parents=True, exist_ok=True)
    with open(REPORTS / "etapa4_metrics.json", "w", encoding="utf-8") as f:
        json.dump(salida, f, ensure_ascii=False, indent=2)
    print(f"      metricas en: {REPORTS / 'etapa4_metrics.json'}")
    return salida


def parse_args():
    p = argparse.ArgumentParser(description="Modelado P1 (entrega_tarde) — Etapa 4")
    p.add_argument("--data", default=str(DEFAULT_DATA))
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run(Path(args.data))
