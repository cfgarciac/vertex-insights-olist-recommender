# Reentrenamiento multi-modelo de P1 — mejora post-Sprint 1

## Vertex Insights — Proyecto Final

**Generado:** 2026-06-29 17:36  
**Datos:** `data\processed\orders_features.csv` (96,470 órdenes; split temporal train/val/test)  
**Disciplina:** mismas 16 features [t0], split temporal, `test` una sola vez, candado anti-fuga (R-12).

## 1. Clasificación binaria (`entrega_tarde`)

Referencia Etapa 4 (`xgboost`): PR-AUC(test) **0.1237**, ROC-AUC **0.7028**, recall **0.346**, Brier **0.1855**.

| Modelo | PR-AUC(test) | ROC-AUC(test) | F1 | Precision | Recall | Brier |
|---|---|---|---|---|---|---|
| baseline_mayoritaria | 0.0661 | 0.5000 | 0.124 | 0.066 | 1.000 | 0.0623 |
| logistic_regression | 0.1105 | 0.6650 | 0.144 | 0.104 | 0.234 | 0.2963 |
| random_forest | 0.0922 | 0.6480 | 0.117 | 0.082 | 0.207 | 0.1464 |
| hist_gradient_boosting | 0.1237 | 0.6902 | 0.181 | 0.123 | 0.342 | 0.1842 |
| xgboost ✅ | 0.1215 | 0.6955 | 0.194 | 0.123 | 0.463 | 0.1809 |

- **Calibración (isotonic)** del mejor: Brier 0.1809 → **0.0615**.
- **Re-ventaneo temporal (R-14/D-29)** — reentrenar `xgboost` con el 50% más reciente del train (tasa base 13.37%): PR-AUC(test) **0.0672**, ROC-AUC **0.4545**, recall **0.163**.
- **Punto de alta cobertura** (umbral 0.463): recall **0.600**, precision 0.115, alertando 34.4% de las órdenes.
- **Auditoría de fuga (R-12):** `tasa_vendedor` pesa 5.1% (bajo → sin fuga). Métricas en rango realista.

## 2. Clasificación multiclase (`clase_entrega`)

| Modelo | macro-F1(test) | balanced-acc(test) | weighted-F1(test) |
|---|---|---|---|
| logistic_regression | 0.2581 | 0.4413 | 0.3905 |
| random_forest ✅ | 0.4224 | 0.4996 | 0.7048 |
| hist_gradient_boosting | 0.3356 | 0.4901 | 0.5534 |
| xgboost | 0.3579 | 0.4975 | 0.5829 |

Recall por clase (mejor modelo):
- `muy_temprano`: recall 0.690, precision 0.933 (n=12,033)
- `a_tiempo`: recall 0.683, precision 0.271 (n=1,481)
- `tarde`: recall 0.126, precision 0.066 (n=957)

## 3. Regresión (`dias_vs_promesa`)

| Modelo | MAE(test) | RMSE(test) | R²(test) |
|---|---|---|---|
| ridge | 5.209 | 6.604 | 0.373 |
| random_forest | 4.304 | 5.868 | 0.505 |
| hist_gradient_boosting | 4.181 | 5.694 | 0.534 |
| xgboost ✅ | 4.238 | 5.729 | 0.528 |

- **Binario derivado** (predecir días y alertar si > 0): PR-AUC **0.1428**, ROC-AUC **0.7563**, recall(umbral 0) 0.027. Vía alternativa al clasificador directo.

> **Importante (interpretación):** la regresión se usa como **ranqueador de riesgo** (su salida se **calibra** a probabilidad de retraso), **NO** como estimador de los días exactos. Por la cola pesada y el techo de datos, *encoge* las predicciones hacia el promedio y **subestima la magnitud de los tardíos** (ver `06_regresion_pred_vs_real.png`: las órdenes muy tardías se predicen cerca de 0). Por eso se opera con el **umbral calibrado**, no con `días>0` (que daría recall ≈0.03).

## 4. Modelo de riesgo CONFIABLE (recomendado)

Score de la regresión calibrado a P(tarde) (isotónica en `val`). Es el de mayor discriminación y mejor calibrado: **PR-AUC 0.1323**, **ROC-AUC 0.7421**, **Brier 0.0629** (vs Etapa 4: 0.124 / 0.703 / 0.186).

| Punto de operación | umbral | recall | precision | F1 | % alertas |
|---|---|---|---|---|---|
| recall_obj_60 | 0.0813 | 0.918 | 0.097 | 0.175 | 62.7% |
| recall_obj_70 | 0.0721 | 0.921 | 0.095 | 0.172 | 64.0% |
| recall_obj_80 | 0.0496 | 0.946 | 0.088 | 0.161 | 71.0% |

Artefacto: `artifacts/modelo_riesgo_p1.joblib` (regresor + calibrador isotónico + puntos de operación). El umbral es ajustable según cuántas alertas tolere el negocio (decisión del PO, Etapa 6).

> **Hallazgo (D-32):** añadir features [t0] derivadas (tasas point-in-time por ruta/categoría, estacionalidad) **no mejora** — degrada el test (ROC 0.696→0.591) por drift de régimen (R-14). El techo de P1 lo fijan los datos, no el modelado.

## 5. Validación cruzada TEMPORAL (robustez ante estacionalidad)

TimeSeriesSplit (5 folds) sobre la serie ordenada por fecha: cada fold entrena en el pasado y evalúa en el período siguiente (no es aleatoria; no sustituye al test). Comprueba si los modelos aguantan los cambios estacionales/atípicos de la serie (R-14).

| Modelo | ROC-AUC medio | ± std | PR-AUC medio | ± std |
|---|---|---|---|---|
| logistic_regression | 0.691 | 0.046 | 0.170 | 0.085 |
| random_forest | 0.670 | 0.034 | 0.167 | 0.086 |
| hist_gradient_boosting | 0.671 | 0.023 | 0.164 | 0.074 |
| xgboost | 0.675 | 0.026 | 0.173 | 0.085 |

Desviación baja ⇒ modelo robusto entre períodos. Ver `figuras/09_cv_temporal.png` (la línea de tasa base muestra dónde están los períodos atípicos).

## Artefactos y figuras

- Modelos: `artifacts/modelo_riesgo_p1.joblib` (recomendado), `modelo_binario.joblib`, `modelo_multiclase.joblib`, `modelo_regresion.joblib`.
- Figuras: `reports/multimodelo/figuras/` — curvas PR/ROC (01), calibración (02), región tasa-real vs recall **separadas** (03), importancias (04), confusión multiclase (05), regresión pred-vs-real (06), **recall por modelo** (07), **matrices de confusión binarias por modelo** (08), **CV temporal** (09).
- **Punto de operación en cada figura (a propósito difieren):** la **03** usa el modelo recomendado en su punto de despliegue (recall≈0.70); la **07** compara los modelos en su umbral **F1** (recall natural, para rankearlos); la **08** usa el punto de **despliegue (recall≈0.80)**. Por eso el recall no es el mismo entre figuras: cada una responde a una pregunta distinta.
- Métricas reproducibles: `reports/multimodelo/metrics_multimodelo.json`.

*Mismas features [t0] y split temporal de la Etapa 3; sin fuga. Reproducible con `python -m src.models.train_multimodelo`.*