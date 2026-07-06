# Justificación del modelo seleccionado — Producto P1 (Etapa 6, HU-12)

> **Fecha:** 2026-07-05 · **Decisiones asociadas:** D-27/D-31 (escudo), D-33..D-36 (motor),
> D-38 (unión), **D-41 (ratificación de umbrales y política)** · **Evidencia:**
> `reports/producto_promesa_riesgo.md`, `reports/producto_promesa_riesgo_metrics.json`,
> `reports/etapa4_modelado_resultados.md` · **Artefacto:** `artifacts/producto_promesa_riesgo.joblib`

## 1. Qué se seleccionó

El producto de P1 es la **unión de dos modelos complementarios** ("la regresión fija la
promesa; el clasificador la defiende"):

| Pieza | Modelo | Tarea | Selección |
|---|---|---|---|
| **Motor de promesa** (Fase 2) | Random Forest (pipeline sklearn, 15 features [t0], bloque `M0_base_sin_rolling`) | Regresión de `dias_entrega_real` → promesa = `max(ceil(pred + margen_P90), 1)` | D-35 (mejor MAE/estabilidad entre baselines, Lineal, RF y HGB) |
| **Escudo de riesgo** (Fase 1) | XGBoost de `dias_vs_promesa` + calibración isotónica (16 features [t0]) | P(entrega tarde) calibrada + bandera | D-31 (regresión calibrada supera a clasificadores directos en PR-AUC/ROC-AUC/Brier) |
| **Escudo v2** (defensa de la promesa nueva) | Mismo XGBoost reentrenado contra el target `dias_entrega_real > promesa_P90` | Riesgo residual de la promesa P90 | D-38 (el v1 no transfiere a la promesa nueva: anti-señal) |

## 2. Por qué la política P90 (ratificada en D-41)

Comparación en el split de **test** (14.471 órdenes, evaluación única):

| Política | Cumplimiento | Promesa promedio | vs. promesa actual |
|---|---|---|---|
| Actual Olist | 94.32% | 19.12 d | — |
| P80 | 91.71% | 14.09 d | más corta pero menos confiable |
| **P90 (elegida)** | **96.70%** | **17.87 d** | **+2.38 pts de cumplimiento con 1.25 d menos** |
| P95 | 98.38% | 21.71 d | más confiable pero 2.6 d más larga |
| Mixta por riesgo | 95.25% | 18.97 d | dominada por P90 |

**P90 domina a la promesa actual en ambas dimensiones a la vez** (más confiable Y más
corta) — es la única política que no obliga a elegir entre competitividad y confiabilidad.
Los márgenes residuales (P80 = 2.06 d, P90 = 5.84 d, P95 = 9.67 d) se calcularon **solo
en validación** (D-36), nunca en test.

## 3. Por qué el escudo v2 como principal (ratificado en D-41)

- Hallazgo de la unión (D-38): el escudo v1, calibrado contra la promesa VIGENTE, **no
  transfiere** a la promesa nueva (captura 48.6% de sus fallos alertando el 64.0% del
  split — anti-señal operativa).
- El **escudo v2**, reentrenado contra `promesa_P90` con las mismas 16 features [t0],
  captura **47.6%** de los incumplimientos residuales alertando solo **34.7%**
  (lift ≈ 1.4×). Umbral ratificado: **0.3658**.
- El v1 (umbral **0.0721**, punto de operación `recall_obj_70`) se mantiene servible en
  la transición, mientras la promesa vigente de Olist siga operando.

Métricas del escudo en test: **ROC-AUC 0.742**, PR-AUC 0.132 (2× la tasa base de 6.6%),
**Brier 0.063** (bien calibrado — la probabilidad que emite es interpretable como riesgo real).

## 4. Alternativas consideradas y descartadas

| Alternativa | Por qué se descartó |
|---|---|
| Servir solo el clasificador (Fase 1) | No emite promesa; el valor de negocio exige promesa + defensa (D-38) |
| Servir solo el motor (Fase 2) | Sin escudo, el 3.3% de incumplimientos residuales de P90 no se prioriza |
| Escudo v1 como defensa de la promesa nueva | No transfiere (anti-señal); demostrado con datos en D-38 |
| Política mixta por riesgo (P80/P95 según bandera) | Dominada por P90 en test; documentada como experimento |
| Bloque con rolling de vendedor (`M0_mas_seller_rolling`) | Δ MAE val ≈ 0.04 no justifica la dependencia del CSV de rolling no versionado; degradación controlada a `M0_base_sin_rolling` (D-38) |

## 5. Riesgo residual asumido (R-14) y su mitigación

El motor opera con sobre-predicción media de **+3.17 d** en test (convención `bias_mean`
= pred − real): el régimen reciente es más rápido que el train. Los márgenes calculados
en validación (régimen nuevo) lo absorben — el cumplimiento realizado en producción
simulada fue **96.40%**. Postura ratificada (D-41): **sin re-ventaneo por ahora**;
monitoreo continuo con runbook escalonado (1º recalibrar márgenes, 2º reentrenar) según
`docs/estrategia_monitoreo.md` y `docs/plan_validacion.md`.

## 6. Límites conocidos (declarados, no ocultos)

- **R-15**: la política de promesa óptima depende de costos comerciales reales
  (competitividad vs. confiabilidad) que Olist no ha compartido; P90 es la elección
  dominante con la evidencia disponible.
- **R-17**: sin variables logísticas del carrier (rutas, capacidad), el techo de
  predicción es estructural; las features [t0] disponibles no lo superan (D-32).
- Los lookups de serving son de nivel **agregado** (categoría/estado) mientras no se
  disponga de los catálogos por ID; toda imputación viaja flaggeada (D-39).
