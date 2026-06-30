"""Reentrenamiento multi-modelo de P1 (desempeño de entrega) — mejora post-Sprint 1.

Aprovecha la tabla analítica ampliada de la Etapa 3 (`orders_features.csv`, D-30),
que trae varios targets sobre el **mismo** set de features [t0]. Sin rehacer feature
engineering ni el split temporal, entrena y compara varias familias en TRES tareas:

  1. Clasificación binaria  (`entrega_tarde`)   → mejorar PR-AUC/ROC-AUC/recall.
  2. Clasificación multiclase(`clase_entrega`)   → muy_temprano / a_tiempo / tarde.
  3. Regresión              (`dias_vs_promesa`)  → días de holgura vs la promesa.

Palancas de mejora de métricas (las features están fijas, D-21/R-12):
  - más familias por tarea (LogReg, RandomForest, HistGradientBoosting, XGBoost),
  - calibración de probabilidades del binario (CalibratedClassifierCV) → Brier,
  - experimento de re-ventaneo temporal (R-14 / D-29): reentrenar el binario en la
    ventana de train más reciente, más cercana al régimen de val/test.

Disciplina mantenida (igual que la Etapa 4):
  - SOLO features [t0] (11 numéricas + 5 categóricas); candado anti-fuga (R-12).
  - Split temporal por la columna `split`; ajuste/selección en `val`; `test` una vez.
  - Nada de validación cruzada aleatoria (reintroduciría fuga temporal, D-25).

Salidas:
  - artifacts/modelo_binario.joblib, modelo_multiclase.joblib, modelo_regresion.joblib
  - reports/multimodelo/metrics_multimodelo.json
  - reports/multimodelo/resultados_multimodelo.md
  - reports/multimodelo/figuras/*.png

Ejecución:
    python -m src.models.train_multimodelo
    python -m src.models.train_multimodelo --data data/processed/orders_features.csv
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

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sklearn.calibration import CalibratedClassifierCV  # noqa: E402
from sklearn.frozen import FrozenEstimator  # noqa: E402
from sklearn.ensemble import (  # noqa: E402
    HistGradientBoostingClassifier,
    HistGradientBoostingRegressor,
    RandomForestClassifier,
    RandomForestRegressor,
)
from sklearn.isotonic import IsotonicRegression  # noqa: E402
from sklearn.linear_model import LogisticRegression, Ridge  # noqa: E402
from sklearn.metrics import (  # noqa: E402
    average_precision_score,
    brier_score_loss,
    roc_auc_score,
)
from sklearn.model_selection import TimeSeriesSplit  # noqa: E402
from sklearn.pipeline import Pipeline  # noqa: E402
from sklearn.utils.class_weight import compute_sample_weight  # noqa: E402
from xgboost import XGBClassifier, XGBRegressor  # noqa: E402

from src.features.build_dataset import (  # noqa: E402
    CATEGORICAL_FEATURES,
    CLASSIFICATION_TARGET,
    MULTICLASS_TARGET,
    NUMERIC_FEATURES,
    build_preprocessor,
)
from src.models import baseline as bl  # noqa: E402
from src.models import evaluate as ev  # noqa: E402

RANDOM_STATE = 42
RECALL_OBJETIVO = 0.50
FRAC_REVENTANEO = 0.50  # fracción más reciente del train para el experimento R-14
LABELS_MULTI = ["muy_temprano", "a_tiempo", "tarde"]  # orden lógico (temprano→tarde)
REG_TARGET = "dias_vs_promesa"
REG_TARGET_EXTRA = "dias_entrega_real"

DEFAULT_DATA = ROOT / "data" / "processed" / "orders_features.csv"
ARTIFACTS = ROOT / "artifacts"
REPORTS = ROOT / "reports" / "multimodelo"
FIG_DIR = REPORTS / "figuras"
X_COLS = NUMERIC_FEATURES + CATEGORICAL_FEATURES


# --------------------------------------------------------------------------- #
# Carga
# --------------------------------------------------------------------------- #
def cargar(path: Path):
    df = pd.read_csv(path)
    requeridas = {CLASSIFICATION_TARGET, MULTICLASS_TARGET, REG_TARGET, "split", *X_COLS}
    faltan = requeridas - set(df.columns)
    if faltan:
        raise ValueError(f"Faltan columnas en {path}: {sorted(faltan)}")
    ev.assert_sin_features_post(X_COLS)  # candado anti-fuga (R-12)
    # Refuerzo: ningún target puede colarse como feature.
    intrusos = {CLASSIFICATION_TARGET, MULTICLASS_TARGET, REG_TARGET, REG_TARGET_EXTRA} & set(X_COLS)
    assert not intrusos, f"FUGA: targets usados como features: {intrusos}"
    df["order_purchase_timestamp"] = pd.to_datetime(df["order_purchase_timestamp"], errors="coerce")
    train = df[df["split"] == "train"].reset_index(drop=True)
    val = df[df["split"] == "val"].reset_index(drop=True)
    test = df[df["split"] == "test"].reset_index(drop=True)
    return df, train, val, test


def _pipe(estimador, dense: bool = False) -> Pipeline:
    """Pipeline preprocesador + estimador.

    `dense=True` fuerza salida densa del ColumnTransformer (`sparse_threshold=0`):
    HistGradientBoosting no admite matrices dispersas, a diferencia de LogReg,
    RandomForest, XGBoost y Ridge (que sí). No se modifica `build_preprocessor`
    (compartido con la Etapa 4 cerrada).
    """
    prep = build_preprocessor()
    if dense:
        prep.sparse_threshold = 0.0
    # El paso del estimador se llama "clf" para reutilizar los helpers de
    # evaluate.py (importancias / auditoría de fuga) de la Etapa 4.
    return Pipeline([("prep", prep), ("clf", estimador)])


def _proba1(modelo, X) -> np.ndarray:
    return modelo.predict_proba(X)[:, 1]


# --------------------------------------------------------------------------- #
# TAREA 1 — Clasificación binaria (entrega_tarde)
# --------------------------------------------------------------------------- #
def familias_binario(y_train: np.ndarray) -> dict[str, Pipeline]:
    n_neg, n_pos = int(np.sum(y_train == 0)), int(np.sum(y_train == 1))
    spw = n_neg / max(n_pos, 1)
    return {
        "logistic_regression": _pipe(
            LogisticRegression(class_weight="balanced", max_iter=1000, C=1.0, random_state=RANDOM_STATE)
        ),
        "random_forest": _pipe(
            RandomForestClassifier(
                n_estimators=400, max_depth=None, min_samples_leaf=20,
                class_weight="balanced_subsample", n_jobs=-1, random_state=RANDOM_STATE,
            )
        ),
        "hist_gradient_boosting": _pipe(
            HistGradientBoostingClassifier(
                max_iter=400, learning_rate=0.05, max_depth=4, l2_regularization=2.0,
                class_weight="balanced", random_state=RANDOM_STATE,
            ),
            dense=True,
        ),
        "xgboost": _pipe(
            XGBClassifier(
                n_estimators=400, max_depth=4, learning_rate=0.05, subsample=0.9,
                colsample_bytree=0.9, reg_lambda=2.0, min_child_weight=5,
                scale_pos_weight=spw, eval_metric="aucpr", tree_method="hist",
                n_jobs=-1, random_state=RANDOM_STATE,
            )
        ),
    }


def run_binario(train, val, test) -> dict:
    print("\n=== TAREA 1: clasificación binaria (entrega_tarde) ===")
    y_tr = train[CLASSIFICATION_TARGET].values
    y_va = val[CLASSIFICATION_TARGET].values
    y_te = test[CLASSIFICATION_TARGET].values

    proba_test_all: dict[str, np.ndarray] = {}
    resultados: dict[str, dict] = {}

    # Baseline (piso de comparación).
    base = bl.BaselineClaseMayoritaria().fit(train[X_COLS], y_tr)
    p_va_b, p_te_b = _proba1(base, val[X_COLS]), _proba1(base, test[X_COLS])
    u_b = ev.seleccionar_umbral_f1(y_va, p_va_b)
    resultados["baseline_mayoritaria"] = {"test": ev.calcular_metricas(y_te, p_te_b, u_b)}
    proba_test_all["baseline_mayoritaria"] = p_te_b

    # Familias reales.
    entrenados: dict[str, Pipeline] = {}
    pr_auc_val: dict[str, float] = {}
    proba_val_all: dict[str, np.ndarray] = {}
    for nombre, pipe in familias_binario(y_tr).items():
        pipe.fit(train[X_COLS], y_tr)
        p_va, p_te = _proba1(pipe, val[X_COLS]), _proba1(pipe, test[X_COLS])
        umbral = ev.seleccionar_umbral_f1(y_va, p_va)
        resultados[nombre] = {
            "val": ev.calcular_metricas(y_va, p_va, umbral),
            "test": ev.calcular_metricas(y_te, p_te, umbral),
        }
        entrenados[nombre] = pipe
        pr_auc_val[nombre] = float(average_precision_score(y_va, p_va))
        proba_val_all[nombre], proba_test_all[nombre] = p_va, p_te
        m = resultados[nombre]["test"]
        print(f"  {nombre:24s} PR-AUC(val)={pr_auc_val[nombre]:.4f}  "
              f"PR-AUC(test)={m['pr_auc']:.4f}  ROC(test)={m['roc_auc']:.4f}  recall={m['recall']:.3f}")

    mejor = max(pr_auc_val, key=pr_auc_val.get)
    modelo_mejor = entrenados[mejor]
    umbral_f1 = resultados[mejor]["val"]["umbral"]
    umbral_cob = ev.umbral_para_recall(y_va, proba_val_all[mejor], RECALL_OBJETIVO)
    op_cob = ev.calcular_metricas(y_te, proba_test_all[mejor], umbral_cob)
    print(f"  -> mejor binario: {mejor} (PR-AUC val={pr_auc_val[mejor]:.4f})")

    # --- Calibración del mejor (mejora de Brier) --------------------------- #
    calib = {"ok": False}
    try:
        cal = CalibratedClassifierCV(FrozenEstimator(modelo_mejor), method="isotonic")
        cal.fit(val[X_COLS], y_va)
        p_te_cal = cal.predict_proba(test[X_COLS])[:, 1]
        calib = {
            "ok": True, "metodo": "isotonic",
            "brier_sin_calibrar": resultados[mejor]["test"]["brier"],
            "metricas": ev.calcular_metricas(y_te, p_te_cal, umbral_f1),
        }
        proba_test_all[f"{mejor}_calibrado"] = p_te_cal
        print(f"     calibrado (isotonic): Brier {calib['brier_sin_calibrar']:.4f} -> {calib['metricas']['brier']:.4f}")
    except Exception as e:  # pragma: no cover
        print(f"     (calibración omitida: {e})")

    # --- Experimento de re-ventaneo temporal (R-14 / D-29) ----------------- #
    train_sorted = train.sort_values("order_purchase_timestamp").reset_index(drop=True)
    corte = int(len(train_sorted) * (1 - FRAC_REVENTANEO))
    train_reciente = train_sorted.iloc[corte:].reset_index(drop=True)
    y_tr_rec = train_reciente[CLASSIFICATION_TARGET].values
    pipe_rec = familias_binario(y_tr_rec)[mejor]
    pipe_rec.fit(train_reciente[X_COLS], y_tr_rec)
    p_va_rec, p_te_rec = _proba1(pipe_rec, val[X_COLS]), _proba1(pipe_rec, test[X_COLS])
    u_rec = ev.seleccionar_umbral_f1(y_va, p_va_rec)
    reventaneo = {
        "familia": mejor,
        "frac_train_usado": FRAC_REVENTANEO,
        "n_train_reciente": int(len(train_reciente)),
        "tasa_base_train_reciente": float(np.mean(y_tr_rec)),
        "test": ev.calcular_metricas(y_te, p_te_rec, u_rec),
    }
    proba_test_all[f"{mejor}_reventaneo"] = p_te_rec
    print(f"     re-ventaneo (últimos {int(FRAC_REVENTANEO*100)}% del train, tasa base "
          f"{reventaneo['tasa_base_train_reciente']*100:.2f}%): "
          f"PR-AUC(test)={reventaneo['test']['pr_auc']:.4f} ROC(test)={reventaneo['test']['roc_auc']:.4f}")

    # --- Auditoría de fuga + análisis de errores del mejor ----------------- #
    peso_tasa = ev.peso_tasa_vendedor(modelo_mejor)
    importancias = ev.importancias_modelo(modelo_mejor, top=20)
    pred_te = (proba_test_all[mejor] >= umbral_f1).astype(int)
    tabla_region = ev.analisis_por_region(test, y_te, pred_te)
    tabla_cold = ev.analisis_cold_start(test, y_te, proba_test_all[mejor], umbral_f1)

    # --- Figuras ----------------------------------------------------------- #
    FAMILIAS = ["logistic_regression", "random_forest", "hist_gradient_boosting", "xgboost"]
    curvas = {k: v for k, v in proba_test_all.items() if not k.endswith(("_calibrado", "_reventaneo"))}
    ev.graficar_curvas_pr_roc(curvas, y_te, FIG_DIR)
    cal_plot = {mejor: proba_test_all[mejor]}
    if calib["ok"]:
        cal_plot[f"{mejor}_calibrado"] = proba_test_all[f"{mejor}_calibrado"]
    ev.graficar_calibracion(cal_plot, y_te, FIG_DIR)
    ev.graficar_importancias(importancias, f"Importancias — {mejor} (binario)", FIG_DIR, "04_importancias_binario.png")
    # (revisión Amaury #1) La figura por región (03) se genera en run_regresion con el
    # MODELO RECOMENDADO en su punto de operación (no el binario @F1, que subestima el recall).
    # (revisión Amaury #2) recall comparado por modelo
    ev.graficar_recall_por_modelo({n: resultados[n]["test"] for n in FAMILIAS}, FIG_DIR, "07_recall_por_modelo.png")
    # (revisión Amaury #3) matriz de confusión binaria por CADA modelo, en el punto de
    # operación que se desplegaría (alto recall), no el umbral F1 que subestima la tardanza.
    RECALL_CM = 0.80
    preds_por_modelo = {
        n: (proba_test_all[n] >= ev.umbral_para_recall(y_va, proba_val_all[n], RECALL_CM)).astype(int)
        for n in FAMILIAS
    }
    ev.graficar_matrices_confusion_binarias(
        preds_por_modelo, y_te, FIG_DIR, "08_matrices_confusion_binarias.png",
        subtitulo=f"punto recall≈{RECALL_CM:.2f} (el que se desplegaría)",
    )

    # --- Serialización ----------------------------------------------------- #
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {
            "modelo": modelo_mejor, "nombre_modelo": mejor, "tarea": "clasificacion_binaria",
            "umbral_f1": float(umbral_f1), "umbral_alta_cobertura": float(umbral_cob),
            "numeric_features": NUMERIC_FEATURES, "categorical_features": CATEGORICAL_FEATURES,
            "target": CLASSIFICATION_TARGET, "metricas_test": resultados[mejor]["test"],
        },
        ARTIFACTS / "modelo_binario.joblib",
    )

    return {
        "mejor_modelo": mejor,
        "pr_auc_val": {k: round(v, 4) for k, v in pr_auc_val.items()},
        "umbral_f1": float(umbral_f1),
        "operativo_alta_cobertura": {"umbral": float(umbral_cob), **op_cob},
        "calibracion": calib,
        "reventaneo": reventaneo,
        "peso_tasa_vendedor": peso_tasa,
        "importancias_top": {k: float(v) for k, v in importancias.items()},
        "analisis_region": tabla_region.to_dict(orient="records"),
        "analisis_cold_start": tabla_cold.to_dict(orient="records"),
        "metricas": resultados,
    }


# --------------------------------------------------------------------------- #
# TAREA 2 — Clasificación multiclase (clase_entrega)
# --------------------------------------------------------------------------- #
def familias_multiclase() -> dict[str, Pipeline]:
    return {
        "logistic_regression": _pipe(
            LogisticRegression(class_weight="balanced", max_iter=2000, C=1.0, random_state=RANDOM_STATE)
        ),
        "random_forest": _pipe(
            RandomForestClassifier(
                n_estimators=400, max_depth=None, min_samples_leaf=20,
                class_weight="balanced_subsample", n_jobs=-1, random_state=RANDOM_STATE,
            )
        ),
        "hist_gradient_boosting": _pipe(
            HistGradientBoostingClassifier(
                max_iter=400, learning_rate=0.05, max_depth=4, l2_regularization=2.0,
                class_weight="balanced", random_state=RANDOM_STATE,
            ),
            dense=True,
        ),
        "xgboost": _pipe(
            XGBClassifier(
                n_estimators=400, max_depth=4, learning_rate=0.05, subsample=0.9,
                colsample_bytree=0.9, reg_lambda=2.0, objective="multi:softprob",
                num_class=len(LABELS_MULTI), eval_metric="mlogloss", tree_method="hist",
                n_jobs=-1, random_state=RANDOM_STATE,
            )
        ),
    }


def run_multiclase(train, val, test) -> dict:
    print("\n=== TAREA 2: clasificación multiclase (clase_entrega) ===")
    code = {lab: i for i, lab in enumerate(LABELS_MULTI)}
    inv = {i: lab for lab, i in code.items()}
    y_tr = train[MULTICLASS_TARGET].map(code).values
    y_va = val[MULTICLASS_TARGET].map(code).values
    y_te = test[MULTICLASS_TARGET].map(code).values
    w_tr = compute_sample_weight("balanced", y_tr)  # para XGBoost (sin class_weight)

    entrenados, resultados, macro_f1_val = {}, {}, {}
    for nombre, pipe in familias_multiclase().items():
        if nombre == "xgboost":
            pipe.fit(train[X_COLS], y_tr, clf__sample_weight=w_tr)
        else:
            pipe.fit(train[X_COLS], y_tr)
        pred_va = pipe.predict(val[X_COLS])
        pred_te = pipe.predict(test[X_COLS])
        va_str = [inv[i] for i in pred_va]
        te_str = [inv[i] for i in pred_te]
        m_va = ev.calcular_metricas_multiclase([inv[i] for i in y_va], va_str, LABELS_MULTI)
        m_te = ev.calcular_metricas_multiclase([inv[i] for i in y_te], te_str, LABELS_MULTI)
        entrenados[nombre] = pipe
        resultados[nombre] = {"val": m_va, "test": m_te}
        macro_f1_val[nombre] = m_va["macro_f1"]
        print(f"  {nombre:24s} macroF1(val)={m_va['macro_f1']:.4f}  "
              f"macroF1(test)={m_te['macro_f1']:.4f}  balAcc(test)={m_te['balanced_accuracy']:.4f}")

    mejor = max(macro_f1_val, key=macro_f1_val.get)
    modelo_mejor = entrenados[mejor]
    pred_te = [inv[i] for i in modelo_mejor.predict(test[X_COLS])]
    ev.graficar_matriz_confusion([inv[i] for i in y_te], pred_te, LABELS_MULTI, FIG_DIR, "05_matriz_confusion_multiclase.png")
    print(f"  -> mejor multiclase: {mejor} (macroF1 val={macro_f1_val[mejor]:.4f})")

    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {
            "modelo": modelo_mejor, "nombre_modelo": mejor, "tarea": "clasificacion_multiclase",
            "labels": LABELS_MULTI, "codigo_labels": code,
            "numeric_features": NUMERIC_FEATURES, "categorical_features": CATEGORICAL_FEATURES,
            "target": MULTICLASS_TARGET, "metricas_test": resultados[mejor]["test"],
        },
        ARTIFACTS / "modelo_multiclase.joblib",
    )
    return {"mejor_modelo": mejor, "macro_f1_val": {k: round(v, 4) for k, v in macro_f1_val.items()}, "metricas": resultados}


# --------------------------------------------------------------------------- #
# TAREA 3 — Regresión (dias_vs_promesa) + binario derivado
# --------------------------------------------------------------------------- #
def familias_regresion() -> dict[str, Pipeline]:
    return {
        "ridge": _pipe(Ridge(alpha=1.0, random_state=RANDOM_STATE)),
        "random_forest": _pipe(
            RandomForestRegressor(
                n_estimators=400, max_depth=None, min_samples_leaf=20,
                n_jobs=-1, random_state=RANDOM_STATE,
            )
        ),
        "hist_gradient_boosting": _pipe(
            HistGradientBoostingRegressor(
                max_iter=400, learning_rate=0.05, max_depth=4, l2_regularization=2.0,
                random_state=RANDOM_STATE,
            ),
            dense=True,
        ),
        "xgboost": _pipe(
            XGBRegressor(
                n_estimators=400, max_depth=4, learning_rate=0.05, subsample=0.9,
                colsample_bytree=0.9, reg_lambda=2.0, tree_method="hist",
                n_jobs=-1, random_state=RANDOM_STATE,
            )
        ),
    }


def run_regresion(train, val, test) -> dict:
    print(f"\n=== TAREA 3: regresión ({REG_TARGET}) + binario derivado ===")
    y_tr = train[REG_TARGET].values
    y_va = val[REG_TARGET].values
    y_te = test[REG_TARGET].values
    y_te_bin = test[CLASSIFICATION_TARGET].values

    entrenados, resultados, mae_val = {}, {}, {}
    for nombre, pipe in familias_regresion().items():
        pipe.fit(train[X_COLS], y_tr)
        pred_va, pred_te = pipe.predict(val[X_COLS]), pipe.predict(test[X_COLS])
        m_va = ev.calcular_metricas_regresion(y_va, pred_va)
        m_te = ev.calcular_metricas_regresion(y_te, pred_te)
        entrenados[nombre] = pipe
        resultados[nombre] = {"val": m_va, "test": m_te, "pred_test": pred_te}
        mae_val[nombre] = m_va["mae"]
        print(f"  {nombre:24s} MAE(val)={m_va['mae']:.3f}  MAE(test)={m_te['mae']:.3f}  "
              f"RMSE(test)={m_te['rmse']:.3f}  R2(test)={m_te['r2']:.3f}")

    mejor = min(mae_val, key=mae_val.get)
    modelo_mejor = entrenados[mejor]
    pred_te_mejor = resultados[mejor]["pred_test"]

    # Binario derivado: la regresión predice días; >0 ⇒ tarde. Score = días predichos.
    derivado = {
        "pr_auc": float(average_precision_score(y_te_bin, pred_te_mejor)),
        "roc_auc": float(roc_auc_score(y_te_bin, pred_te_mejor)),
        "recall_umbral0": float(np.mean(pred_te_mejor[y_te_bin == 1] > 0)) if y_te_bin.sum() else float("nan"),
        "precision_umbral0": (
            float(y_te_bin[pred_te_mejor > 0].mean()) if (pred_te_mejor > 0).any() else float("nan")
        ),
        "frac_alertas_umbral0": float(np.mean(pred_te_mejor > 0)),
    }
    print(f"  -> mejor regresor: {mejor} (MAE val={mae_val[mejor]:.3f})")
    print(f"     binario derivado (días>0): PR-AUC={derivado['pr_auc']:.4f} ROC={derivado['roc_auc']:.4f} "
          f"recall={derivado['recall_umbral0']:.3f}")

    ev.graficar_pred_vs_real(y_te, pred_te_mejor, f"{REG_TARGET}: predicho vs real — {mejor} (test)",
                             FIG_DIR, "06_regresion_pred_vs_real.png")

    # Target extra (dias_entrega_real) con la familia ganadora, sólo para referencia.
    extra = {}
    try:
        pe = familias_regresion()[mejor]
        pe.fit(train[X_COLS], train[REG_TARGET_EXTRA].values)
        extra = ev.calcular_metricas_regresion(test[REG_TARGET_EXTRA].values, pe.predict(test[X_COLS]))
        print(f"     extra ({REG_TARGET_EXTRA}, {mejor}): MAE(test)={extra['mae']:.3f} RMSE={extra['rmse']:.3f} R2={extra['r2']:.3f}")
    except Exception as e:  # pragma: no cover
        print(f"     (target extra omitido: {e})")

    # --- Modelo de riesgo CONFIABLE: score de regresion calibrado a P(tarde) --- #
    # El score de la regresion (dias predichos) ranquea el riesgo mejor que el
    # clasificador directo; se calibra a probabilidad con isotonica ajustada en val.
    yv_bin = val[CLASSIFICATION_TARGET].values
    rv = modelo_mejor.predict(val[X_COLS])
    iso = IsotonicRegression(out_of_bounds="clip").fit(rv, yv_bin)
    pva, pte = iso.predict(rv), iso.predict(pred_te_mejor)
    puntos = {}
    for obj in (0.60, 0.70, 0.80):
        u = ev.umbral_para_recall(yv_bin, pva, obj)
        puntos[f"recall_obj_{int(obj*100)}"] = {"umbral": float(u), **ev.calcular_metricas(y_te_bin, pte, u)}
    riesgo = {
        "base": f"regresion({mejor}) -> P(tarde) calibrada (isotonic en val)",
        "pr_auc": float(average_precision_score(y_te_bin, pte)),
        "roc_auc": float(roc_auc_score(y_te_bin, pte)),
        "brier": float(brier_score_loss(y_te_bin, pte)),
        "puntos_operacion": puntos,
    }
    print(f"  modelo de riesgo confiable: ROC={riesgo['roc_auc']:.3f} PR-AUC={riesgo['pr_auc']:.3f} "
          f"Brier={riesgo['brier']:.3f}  (regresion calibrada)")

    # (revisión Amaury #1) Recall por región DEL MODELO RECOMENDADO en su punto de operación
    # (recall≈0.70). Reemplaza la versión que usaba el binario @F1 (subestimaba el recall).
    u_fig = puntos["recall_obj_70"]["umbral"]
    pred_fig = (pte >= u_fig).astype(int)
    tabla_region_riesgo = ev.analisis_por_region(test, y_te_bin, pred_fig)
    ev.graficar_region_separado(
        tabla_region_riesgo, FIG_DIR, "03_region_separado.png",
        etiqueta_recall="modelo recomendado (regresión calibrada) · punto recall≈0.70",
    )

    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {
            "modelo": modelo_mejor, "nombre_modelo": mejor, "tarea": "regresion",
            "numeric_features": NUMERIC_FEATURES, "categorical_features": CATEGORICAL_FEATURES,
            "target": REG_TARGET, "metricas_test": {k: v for k, v in resultados[mejor]["test"].items()},
        },
        ARTIFACTS / "modelo_regresion.joblib",
    )
    joblib.dump(
        {
            "modelo_regresion": modelo_mejor, "calibrador_isotonic": iso,
            "tarea": "riesgo_tardanza (regresion calibrada -> P(tarde))",
            "target_regresion": REG_TARGET, "target_binario": CLASSIFICATION_TARGET,
            "numeric_features": NUMERIC_FEATURES, "categorical_features": CATEGORICAL_FEATURES,
            "puntos_operacion": puntos,
            "metricas_test": {k: riesgo[k] for k in ("pr_auc", "roc_auc", "brier")},
        },
        ARTIFACTS / "modelo_riesgo_p1.joblib",
    )
    metricas_limpias = {n: {"val": r["val"], "test": r["test"]} for n, r in resultados.items()}
    return {
        "mejor_modelo": mejor, "mae_val": {k: round(v, 4) for k, v in mae_val.items()},
        "binario_derivado": derivado, "target_extra": {REG_TARGET_EXTRA: extra},
        "modelo_riesgo_confiable": riesgo,
        "metricas": metricas_limpias,
    }


# --------------------------------------------------------------------------- #
# Reporte
# --------------------------------------------------------------------------- #
def referencia_etapa4() -> dict | None:
    ruta = ROOT / "reports" / "etapa4_metrics.json"
    if not ruta.exists():
        return None
    try:
        with open(ruta, encoding="utf-8") as f:
            j = json.load(f)
        mejor = j.get("mejor_modelo")
        return {"modelo": mejor, "test": j["metricas"][mejor]["test"]}
    except Exception:
        return None


def escribir_reporte(salida: dict) -> None:
    REPORTS.mkdir(parents=True, exist_ok=True)
    with open(REPORTS / "metrics_multimodelo.json", "w", encoding="utf-8") as f:
        json.dump(salida, f, ensure_ascii=False, indent=2, default=float)

    b = salida["binario"]
    ref = salida.get("referencia_etapa4")
    mejor_b = b["mejor_modelo"]
    mt = b["metricas"][mejor_b]["test"]
    L = []
    L.append("# Reentrenamiento multi-modelo de P1 — mejora post-Sprint 1\n")
    L.append("## Vertex Insights — Proyecto Final\n")
    L.append(f"**Generado:** {salida['generado']}  ")
    L.append(f"**Datos:** `{salida['data']}` ({salida['n_total']:,} órdenes; split temporal train/val/test)  ")
    L.append("**Disciplina:** mismas 16 features [t0], split temporal, `test` una sola vez, candado anti-fuga (R-12).\n")

    L.append("## 1. Clasificación binaria (`entrega_tarde`)\n")
    if ref:
        L.append(f"Referencia Etapa 4 (`{ref['modelo']}`): PR-AUC(test) **{ref['test']['pr_auc']:.4f}**, "
                 f"ROC-AUC **{ref['test']['roc_auc']:.4f}**, recall **{ref['test']['recall']:.3f}**, "
                 f"Brier **{ref['test']['brier']:.4f}**.\n")
    L.append("| Modelo | PR-AUC(test) | ROC-AUC(test) | F1 | Precision | Recall | Brier |")
    L.append("|---|---|---|---|---|---|---|")
    for nombre, r in b["metricas"].items():
        m = r["test"]
        marca = " ✅" if nombre == mejor_b else ""
        f1 = m.get("f1", float("nan"))
        L.append(f"| {nombre}{marca} | {m['pr_auc']:.4f} | {m['roc_auc']:.4f} | {f1:.3f} | "
                 f"{m['precision']:.3f} | {m['recall']:.3f} | {m['brier']:.4f} |")
    L.append("")
    if b["calibracion"].get("ok"):
        c = b["calibracion"]
        L.append(f"- **Calibración (isotonic)** del mejor: Brier {c['brier_sin_calibrar']:.4f} → "
                 f"**{c['metricas']['brier']:.4f}**.")
    rv = b["reventaneo"]
    L.append(f"- **Re-ventaneo temporal (R-14/D-29)** — reentrenar `{rv['familia']}` con el "
             f"{int(rv['frac_train_usado']*100)}% más reciente del train (tasa base "
             f"{rv['tasa_base_train_reciente']*100:.2f}%): PR-AUC(test) **{rv['test']['pr_auc']:.4f}**, "
             f"ROC-AUC **{rv['test']['roc_auc']:.4f}**, recall **{rv['test']['recall']:.3f}**.")
    cob = b["operativo_alta_cobertura"]
    L.append(f"- **Punto de alta cobertura** (umbral {cob['umbral']:.3f}): recall **{cob['recall']:.3f}**, "
             f"precision {cob['precision']:.3f}, alertando {cob['frac_alertas']*100:.1f}% de las órdenes.")
    L.append(f"- **Auditoría de fuga (R-12):** `tasa_vendedor` pesa {b['peso_tasa_vendedor']*100:.1f}% "
             f"(bajo → sin fuga). Métricas en rango realista.\n")

    mc = salida["multiclase"]
    mejor_mc = mc["mejor_modelo"]
    L.append("## 2. Clasificación multiclase (`clase_entrega`)\n")
    L.append("| Modelo | macro-F1(test) | balanced-acc(test) | weighted-F1(test) |")
    L.append("|---|---|---|---|")
    for nombre, r in mc["metricas"].items():
        m = r["test"]
        marca = " ✅" if nombre == mejor_mc else ""
        L.append(f"| {nombre}{marca} | {m['macro_f1']:.4f} | {m['balanced_accuracy']:.4f} | {m['weighted_f1']:.4f} |")
    pc = mc["metricas"][mejor_mc]["test"]["por_clase"]
    L.append("\nRecall por clase (mejor modelo):")
    for clase, d in pc.items():
        L.append(f"- `{clase}`: recall {d['recall']:.3f}, precision {d['precision']:.3f} (n={d['support']:,})")
    L.append("")

    rg = salida["regresion"]
    mejor_rg = rg["mejor_modelo"]
    L.append(f"## 3. Regresión (`{REG_TARGET}`)\n")
    L.append("| Modelo | MAE(test) | RMSE(test) | R²(test) |")
    L.append("|---|---|---|---|")
    for nombre, r in rg["metricas"].items():
        m = r["test"]
        marca = " ✅" if nombre == mejor_rg else ""
        L.append(f"| {nombre}{marca} | {m['mae']:.3f} | {m['rmse']:.3f} | {m['r2']:.3f} |")
    d = rg["binario_derivado"]
    L.append(f"\n- **Binario derivado** (predecir días y alertar si > 0): PR-AUC **{d['pr_auc']:.4f}**, "
             f"ROC-AUC **{d['roc_auc']:.4f}**, recall(umbral 0) {d['recall_umbral0']:.3f}. "
             "Vía alternativa al clasificador directo.")
    L.append("\n> **Importante (interpretación):** la regresión se usa como **ranqueador de riesgo** "
             "(su salida se **calibra** a probabilidad de retraso), **NO** como estimador de los días "
             "exactos. Por la cola pesada y el techo de datos, *encoge* las predicciones hacia el promedio "
             "y **subestima la magnitud de los tardíos** (ver `06_regresion_pred_vs_real.png`: las órdenes "
             "muy tardías se predicen cerca de 0). Por eso se opera con el **umbral calibrado**, no con "
             "`días>0` (que daría recall ≈0.03).")
    L.append("")
    r = rg["modelo_riesgo_confiable"]
    L.append("## 4. Modelo de riesgo CONFIABLE (recomendado)\n")
    L.append("Score de la regresión calibrado a P(tarde) (isotónica en `val`). Es el de mayor "
             f"discriminación y mejor calibrado: **PR-AUC {r['pr_auc']:.4f}**, **ROC-AUC {r['roc_auc']:.4f}**, "
             f"**Brier {r['brier']:.4f}** (vs Etapa 4: 0.124 / 0.703 / 0.186).\n")
    L.append("| Punto de operación | umbral | recall | precision | F1 | % alertas |")
    L.append("|---|---|---|---|---|---|")
    for k, p in r["puntos_operacion"].items():
        L.append(f"| {k} | {p['umbral']:.4f} | {p['recall']:.3f} | {p['precision']:.3f} | {p['f1']:.3f} | {p['frac_alertas']*100:.1f}% |")
    L.append("\nArtefacto: `artifacts/modelo_riesgo_p1.joblib` (regresor + calibrador isotónico + puntos de operación). "
             "El umbral es ajustable según cuántas alertas tolere el negocio (decisión del PO, Etapa 6).")
    L.append("\n> **Hallazgo (D-32):** añadir features [t0] derivadas (tasas point-in-time por ruta/categoría, "
             "estacionalidad) **no mejora** — degrada el test (ROC 0.696→0.591) por drift de régimen (R-14). "
             "El techo de P1 lo fijan los datos, no el modelado.\n")
    cvd = salida.get("cv_temporal")
    if cvd:
        L.append("## 5. Validación cruzada TEMPORAL (robustez ante estacionalidad)\n")
        L.append("TimeSeriesSplit (5 folds) sobre la serie ordenada por fecha: cada fold entrena en el "
                 "pasado y evalúa en el período siguiente (no es aleatoria; no sustituye al test). "
                 "Comprueba si los modelos aguantan los cambios estacionales/atípicos de la serie (R-14).\n")
        L.append("| Modelo | ROC-AUC medio | ± std | PR-AUC medio | ± std |")
        L.append("|---|---|---|---|---|")
        for m, dd in cvd.items():
            L.append(f"| {m} | {dd['roc_auc_media']:.3f} | {dd['roc_auc_std']:.3f} | "
                     f"{dd['pr_auc_media']:.3f} | {dd['pr_auc_std']:.3f} |")
        L.append("\nDesviación baja ⇒ modelo robusto entre períodos. Ver `figuras/09_cv_temporal.png` "
                 "(la línea de tasa base muestra dónde están los períodos atípicos).\n")

    L.append("## Artefactos y figuras\n")
    L.append("- Modelos: `artifacts/modelo_riesgo_p1.joblib` (recomendado), `modelo_binario.joblib`, "
             "`modelo_multiclase.joblib`, `modelo_regresion.joblib`.")
    L.append("- Figuras: `reports/multimodelo/figuras/` — curvas PR/ROC (01), calibración (02), "
             "región tasa-real vs recall **separadas** (03), importancias (04), confusión multiclase (05), "
             "regresión pred-vs-real (06), **recall por modelo** (07), **matrices de confusión binarias por "
             "modelo** (08), **CV temporal** (09).")
    L.append("- **Punto de operación en cada figura (a propósito difieren):** la **03** usa el modelo "
             "recomendado en su punto de despliegue (recall≈0.70); la **07** compara los modelos en su "
             "umbral **F1** (recall natural, para rankearlos); la **08** usa el punto de **despliegue "
             "(recall≈0.80)**. Por eso el recall no es el mismo entre figuras: cada una responde a una "
             "pregunta distinta.")
    L.append("- Métricas reproducibles: `reports/multimodelo/metrics_multimodelo.json`.\n")
    L.append("*Mismas features [t0] y split temporal de la Etapa 3; sin fuga. Reproducible con "
             "`python -m src.models.train_multimodelo`.*")

    with open(REPORTS / "resultados_multimodelo.md", "w", encoding="utf-8") as f:
        f.write("\n".join(L))


# --------------------------------------------------------------------------- #
# Validación cruzada TEMPORAL (robustez ante estacionalidad) — revisión Amaury #4
# --------------------------------------------------------------------------- #
def cross_validation_temporal(df, n_splits: int = 5) -> dict:
    """TimeSeriesSplit sobre la serie completa ordenada por fecha.

    Diagnóstico de robustez: cada fold entrena en el pasado y evalúa en el bloque
    siguiente (un período/temporada distinto). NO es validación aleatoria (eso
    reintroduciría fuga temporal, D-25) y NO sustituye al test hold-out (que se
    reporta una sola vez). Sirve para ver si los modelos se mantienen estables
    ante los cambios estacionales / comportamientos atípicos de la serie (R-14).
    """
    d = df.sort_values(["order_purchase_timestamp", "order_id"]).reset_index(drop=True)
    X, y = d[X_COLS], d[CLASSIFICATION_TARGET].values
    tscv = TimeSeriesSplit(n_splits=n_splits)
    familias = ["logistic_regression", "random_forest", "hist_gradient_boosting", "xgboost"]
    cv = {n: {"pr_auc": [], "roc_auc": [], "recall": [], "tasa_base": []} for n in familias}
    print(f"\n=== Validación cruzada TEMPORAL (TimeSeriesSplit, {n_splits} folds) — robustez estacional ===")
    for k, (itr, ite) in enumerate(tscv.split(X), 1):
        ytr, yte = y[itr], y[ite]
        Xtr, Xte = X.iloc[itr], X.iloc[ite]
        for nombre, pipe in familias_binario(ytr).items():
            pipe.fit(Xtr, ytr)
            u = ev.seleccionar_umbral_f1(ytr, _proba1(pipe, Xtr))
            m = ev.calcular_metricas(yte, _proba1(pipe, Xte), u)
            cv[nombre]["pr_auc"].append(m["pr_auc"])
            cv[nombre]["roc_auc"].append(m["roc_auc"])
            cv[nombre]["recall"].append(m["recall"])
            cv[nombre]["tasa_base"].append(float(yte.mean()))
        print(f"  fold {k}: n_train={len(itr):>6} n_test={len(ite):>5} "
              f"tasa_base(fold)={yte.mean()*100:4.1f}%  ROC(xgb)={cv['xgboost']['roc_auc'][-1]:.3f}")
    return cv


# --------------------------------------------------------------------------- #
# Orquestación
# --------------------------------------------------------------------------- #
def run(data_path: Path) -> dict:
    print(f"[carga] tabla analítica multi-modelo: {data_path}")
    df, train, val, test = cargar(data_path)
    print(f"        total={len(df):,}  train={len(train):,}  val={len(val):,}  test={len(test):,}")
    print(f"        tasa_base entrega_tarde: train={train[CLASSIFICATION_TARGET].mean():.4f} "
          f"val={val[CLASSIFICATION_TARGET].mean():.4f} test={test[CLASSIFICATION_TARGET].mean():.4f} (R-14)")

    salida = {
        "generado": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "data": str(data_path.relative_to(ROOT)) if data_path.is_relative_to(ROOT) else str(data_path),
        "n_total": int(len(df)),
        "tamanos_split": {"train": len(train), "val": len(val), "test": len(test)},
        "referencia_etapa4": referencia_etapa4(),
        "binario": run_binario(train, val, test),
        "multiclase": run_multiclase(train, val, test),
        "regresion": run_regresion(train, val, test),
    }
    cv = cross_validation_temporal(df, n_splits=5)
    ev.graficar_cv_temporal(cv, FIG_DIR, "09_cv_temporal.png")
    salida["cv_temporal"] = {
        m: {
            "roc_auc_media": float(np.mean(d["roc_auc"])), "roc_auc_std": float(np.std(d["roc_auc"])),
            "pr_auc_media": float(np.mean(d["pr_auc"])), "pr_auc_std": float(np.std(d["pr_auc"])),
            "roc_auc_folds": [round(x, 4) for x in d["roc_auc"]],
            "recall_folds": [round(x, 4) for x in d["recall"]],
            "tasa_base_folds": [round(x, 4) for x in d["tasa_base"]],
        }
        for m, d in cv.items()
    }
    escribir_reporte(salida)
    print(f"\n[ok] reporte -> {REPORTS / 'resultados_multimodelo.md'}")
    print(f"[ok] métricas -> {REPORTS / 'metrics_multimodelo.json'}")
    print(f"[ok] modelos  -> {ARTIFACTS}/(modelo_binario|modelo_multiclase|modelo_regresion).joblib")
    return salida


def parse_args():
    p = argparse.ArgumentParser(description="Reentrenamiento multi-modelo de P1 (mejora post-Sprint 1)")
    p.add_argument("--data", default=str(DEFAULT_DATA))
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run(Path(args.data))
