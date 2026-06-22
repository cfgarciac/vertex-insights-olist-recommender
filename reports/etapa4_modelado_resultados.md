# Resultados del modelado — P1 (entrega tardía) · Etapa 4

## Vertex Insights — Proyecto Final

**Fecha:** 2026-06-21
**Fase CRISP-DM:** Modeling
**Responsable de la etapa:** Machine Learning Engineer (Wessin, Nassim)
**Insumo:** tabla analítica y preprocesador de la Etapa 3 (`docs/decisiones_fe.md`)
**Artefactos:** `artifacts/modelo_p1.joblib`, `reports/etapa4_metrics.json`,
`reports/figures_modelado_etapa4/`, `notebooks/04_modelado_VERTEX.ipynb`

---

## 1. Objetivo y enfoque

Predecir **en el momento de la compra (t0)** si una orden de Olist llegará
**tarde** respecto a la fecha prometida (`entrega_tarde`). Es una **clasificación
binaria desbalanceada** (tasa base global 8.11%). La etapa **no rehace features ni
el split** (cerrados en la Etapa 3): añade el estimador al preprocesador y mide.

Disciplina mantenida (heredada de la Etapa 3):
- Solo features **[t0]** (11 numéricas + 5 categóricas); columnas [POST]
  (`dias_vs_promesa`, entrega real, reseñas) **excluidas** por un candado de código
  (`assert_sin_features_post`).
- **Split temporal** 70/15/15 por fecha de compra (D-25); el preprocesador se
  ajusta **solo en train**; la selección mira `val`; `test` se reporta **una vez**.
- **Nada de validación cruzada aleatoria** (reintroduciría fuga temporal).

---

## 2. Datos y un hallazgo de coherencia importante

| Split | Órdenes | Tasa `entrega_tarde` |
|---|---|---|
| train (pasado) | 67,529 | **9.03%** |
| val | 14,470 | **5.34%** |
| test (futuro) | 14,471 | **6.61%** |
| total | 96,470 | 8.11% |

> **Cambio de régimen temporal (R-14).** La tardanza **cae con el tiempo**: el
> periodo de entrenamiento (más antiguo) es más tardío que el de val/test. Esto no
> es un error: refleja que el desempeño logístico de Olist mejora hacia el final
> del dataset. Consecuencia práctica: las métricas en `val`/`test` son
> sistemáticamente más bajas que en `train` y la **calibración** queda desplazada
> (un modelo entrenado en un régimen del 9% sobre-estima el riesgo en uno del 6%).
> Se conserva el periodo completo (D-29) y se reporta honestamente; el re-ventaneo
> o la segmentación se evalúan en la Etapa 6.

---

## 3. Modelos y métricas

Se midieron dos **baselines** (piso) y dos **familias** de clasificadores; cada
familia exploró una rejilla pequeña y se eligió su mejor candidato por **PR-AUC en
`val`** (`xgb_d4_l2` ganó a `xgb_d6_l5`: 0.166 vs 0.152).

**Métricas en TEST (umbral F1 fijado en `val`):**

| Modelo | PR-AUC | ROC-AUC | F1 | Precision | Recall | Brier |
|---|---|---|---|---|---|---|
| Baseline clase mayoritaria | 0.066 | 0.500 | — | — | — | 0.062 |
| Baseline regla (dist+estado) | 0.052 | 0.340 | 0.071 | 0.052 | 0.111 | 0.349 |
| Regresión Logística | 0.111 | 0.665 | 0.144 | 0.104 | 0.234 | 0.296 |
| **XGBoost (`xgb_d4_l2`) — elegido** | **0.124** | **0.703** | 0.191 | 0.132 | 0.346 | 0.186 |

Lectura:
- El **PR-AUC** es la métrica principal (D-19): con tasa base 6.61% en test, el azar
  da 0.066. **XGBoost lo casi duplica (0.124 ≈ 1.9×)** y la Regresión Logística lo
  supera con holgura (0.111). Ambos superan claramente al baseline → la complejidad
  se justifica.
- El **baseline de regla** (distancia + cruce de estado) es **anti-informativo en
  test** (ROC-AUC 0.34): la regla simple que parecía razonable en el periodo
  antiguo no generaliza al nuevo régimen. Otra evidencia de que el problema exige un
  modelo, no una heurística.
- **XGBoost** gana a la Logística en discriminación (ROC-AUC 0.703 vs 0.665), recall
  (0.346 vs 0.234) y, sobre todo, **calibración** (Brier 0.186 vs 0.296): el árbol
  regularizado entrega probabilidades mucho más sensatas.

Curvas y calibración: ver `reports/figures_modelado_etapa4/01_curvas_pr_roc.png` y
`02_calibracion.png`.

---

## 4. Puntos de operación (cómo se usa el modelo)

El modelo entrega una **probabilidad de riesgo**; el umbral traduce esa probabilidad
en una alerta. Se documentan dos puntos sobre TEST:

| Punto de operación | Umbral | Recall | Precision | % órdenes alertadas |
|---|---|---|---|---|
| **F1-óptimo** (balance) | 0.574 | 0.346 | 0.132 | 17.3% |
| **Alta cobertura** (recall≈0.5 en val) | 0.468 | **0.628** | 0.118 | 35.2% |

- Para **alertar** órdenes en riesgo, el punto de alta cobertura **captura el ~63%
  de las entregas tardías** alertando el 35% de las órdenes, con precisión 11.8%
  (1.8× la tasa base). La elección final del umbral es una decisión de negocio
  (¿cuántas alertas tolera Olist?) que el PO afinará en la Etapa 6 (D-28).

---

## 5. Auditoría de fuga (R-12)

- **Sin señal de fuga.** Las métricas están en rango realista (ROC-AUC 0.70, PR-AUC
  0.12), **lejos** del 0.99 que delataría fuga.
- **`tasa_vendedor` pesa solo 6.0%** de la importancia total. La feature "más
  sensible a fuga" **no domina** el modelo → el cálculo point-in-time de la Etapa 3
  (con prueba anti-fuga) se sostiene.
- El candado `assert_sin_features_post` confirma que ninguna columna [POST] entró
  como feature.

---

## 6. Qué aprendió el modelo (lectura de negocio)

Top de importancias (XGBoost; ver `04_importancias.png`):

1. `customer_state_SP` (0.107) y `customer_state_RJ` (0.063) — **la geografía del
   cliente manda**.
2. `mismo_estado` (0.062) — **cruce de estado cliente-vendedor** (proxy de distancia
   logística).
3. `tasa_vendedor` (0.060) — **historial de puntualidad del vendedor**.
4. `mes_compra` (0.049) — **estacionalidad** (coherente con el régimen 2018, R-14).
5. `customer_state_MG`, `seller_state_SP`, `dias_prometidos`, `dist_haversine_km`…

Esto **reproduce la narrativa del EDA**: geografía/región, cercanía cliente-vendedor,
desempeño del vendedor, colchón de la promesa y estacionalidad. El modelo aprende
señal de negocio, no un artefacto.

---

## 7. Análisis de errores

### Por región (test, umbral F1)

| Región | Órdenes | Tasa tardía real | Recall del modelo |
|---|---|---|---|
| Sudeste | 10,228 | 7.6% | 0.30 |
| Nordeste | 1,256 | 5.3% | **0.83** |
| Centro-Oeste | 837 | 4.9% | 0.54 |
| Norte | 225 | 4.0% | 0.56 |
| Sul | 1,925 | 3.3% | 0.25 |

> **Matiz de coherencia.** El gradiente regional del EDA (Norte/Nordeste peor que SP)
> se midió sobre **todo el periodo**. En la **ventana de test** (cola temporal, menor
> tardanza global) el Sudeste concentra la tardanza absoluta por volumen, pero el
> modelo alcanza su **mejor recall en Nordeste (0.83) y Norte (0.56)** — justo donde
> el dolor histórico es mayor. Ver `03_error_por_region.png`.

### Cold-start de vendedores (`sin_historial_vendedor == 1`)

| Segmento | Órdenes | PR-AUC | ROC-AUC | Recall | Precision |
|---|---|---|---|---|---|
| Con historial | 12,820 | 0.126 | 0.701 | 0.351 | 0.134 |
| Cold-start (sin historial) | 1,651 | 0.106 | 0.722 | 0.298 | 0.113 |

El desempeño en *cold-start* es **ligeramente menor en PR-AUC/recall** pero
**comparable en ROC-AUC** (0.72): el respaldo a la tasa global + el flag de la Etapa
3 sostienen al modelo cuando el vendedor es nuevo. Es un caso real de producción y se
reporta por separado.

---

## 8. Conclusión y selección

- **Modelo candidato del Sprint 1: XGBoost `xgb_d4_l2`** (profundidad 4, 300 árboles,
  `reg_lambda=2`, `min_child_weight=5`, `scale_pos_weight≈10`), encadenado al
  preprocesador de la Etapa 3 en un único `Pipeline`, serializado en
  `artifacts/modelo_p1.joblib` con su umbral y metadatos.
- **Métricas defendibles y honestas** para un MVP de Sprint 1: PR-AUC 0.124 (1.9× el
  azar), ROC-AUC 0.703, sin fuga, con lectura de negocio coherente.
- **Pendientes para la Etapa 6** (evaluación final, HU-12): calibración formal
  (el Brier mejora pero el régimen desplaza la probabilidad), selección definitiva
  del umbral con el PO, y decisión sobre el re-ventaneo temporal (R-14).

---

*Reporte de resultados del modelado de P1, Etapa 4 — equipo Vertex Insights.
Números reproducibles desde `reports/etapa4_metrics.json` y
`python -m src.models.train`.*
