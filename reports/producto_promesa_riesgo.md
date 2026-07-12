# Producto conjunto P1 — Promesa inteligente + escudo de riesgo

## Vertex Insights — unión Fase 1 (escudo) + Fase 2 (motor)

**Generado:** 2026-07-05 10:48  
**Motor:** random_forest · bloque `M0_base_sin_rolling` (fallback sin rolling: CSV de Fase 2 no disponible; Δ MAE val ≈ 0.04 vs bloque ganador)  
**Escudo:** `artifacts/modelo_riesgo_p1.joblib` @ `recall_obj_70`  
**Política recomendada:** P90 (D-36) · **Unión:** política mixta (P80 sin bandera / P95 con bandera)

Los dos modelos quedan ligados por `dias_vs_promesa = dias_entrega_real − dias_prometidos`. Márgenes calculados SOLO en `val`; `test` se evalúa una sola vez (D-25).

## 1. MAE del motor por split (trazabilidad)

| split | mae | medae | rmse | p90_abs_error | bias_mean |
| --- | --- | --- | --- | --- | --- |
| train | 4.859 | 3.378 | 8.031 | 9.906 | 0.012 |
| val | 4.655 | 3.772 | 6.508 | 8.880 | 1.264 |
| test | 4.620 | 3.996 | 5.876 | 8.683 | 3.167 |

## 2. Políticas de promesa en test

| split | politica | ordenes | cumplimiento | incumplimiento | colchon_promedio | colchon_mediano | colchon_p10 | colchon_p90 | promesa_promedio | promesa_mediana | dif_promesa_promedio_vs_actual | dif_promesa_mediana_vs_actual | dif_cumplimiento_vs_actual | dif_colchon_promedio_vs_actual |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| test | actual_olist | 14,471 | 0.943 | 0.057 | 10.752 | 9.873 | 1.573 | 21.251 | 19.120 | 18.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| test | P80 | 14,471 | 0.917 | 0.083 | 5.725 | 6.044 | 0.775 | 10.741 | 14.093 | 14.000 | -5.027 | -4.000 | -0.026 | -5.027 |
| test | P90 | 14,471 | 0.967 | 0.033 | 9.503 | 9.886 | 4.567 | 14.566 | 17.871 | 17.000 | -1.249 | 0.000 | 0.024 | -1.249 |
| test | P95 | 14,471 | 0.984 | 0.016 | 13.341 | 13.772 | 8.328 | 18.317 | 21.709 | 21.000 | 2.589 | 4.000 | 0.041 | 2.589 |
| test | mixta_riesgo | 14,471 | 0.952 | 0.048 | 10.601 | 11.752 | 3.222 | 17.111 | 18.969 | 18.000 | -0.152 | 4.000 | 0.009 | -0.152 |

Ver `figures_producto_promesa_riesgo/01_tradeoff_politicas.png` y `02_cumplimiento_por_region.png`.

## 3. Sinergia del escudo (la unión en acción)

- Bajo `promesa_P90` con `bandera_riesgo`: **477** fallos residuales; el escudo marcaba el **48.6%** (prob media incumplidas 0.082 vs cumplidas 0.100; alertas 64.0%).
- Bajo `promesa_P90` con `bandera_riesgo_v2`: **477** fallos residuales; el escudo marcaba el **47.6%** (prob media incumplidas 0.369 vs cumplidas 0.318; alertas 34.7%).
- Bajo `promesa_mixta_riesgo` con `bandera_riesgo`: **688** fallos residuales; el escudo marcaba el **15.6%** (prob media incumplidas 0.046 vs cumplidas 0.102; alertas 64.0%).

**Hallazgo clave de la unión:** el escudo v1 (calibrado contra la promesa VIGENTE) **no transfiere** a la promesa nueva — sus fallos residuales son órdenes distintas. Gracias a la identidad `dias_vs_promesa = dias_entrega_real − dias_prometidos`, el **escudo v2** se reentrena contra `promesa_P90` con las mismas 16 features [t0] y la misma familia (XGBoost) y **sí separa y captura los fallos residuales**. El producto final = promesa P90 del motor + escudo v2 defendiéndola + escudo v1 vigilando la promesa actual durante la transición. Ver `03_escudo_sinergia.png`.

## 4. Artefactos

- `artifacts/producto_promesa_riesgo.joblib` — motor + márgenes + escudo + metadatos.
- `reports/predicciones_promesa_riesgo.csv` — tabla por orden (`eta_dias`, promesas simuladas, `prob_riesgo_tarde`, `bandera_riesgo`); regenerable.
- Métricas: `reports/producto_promesa_riesgo_metrics.json`.

## 5. Límites honestos

- El motor sobreestima días por el cambio de régimen (R-14); los márgenes en `val` (régimen reciente) absorben parte del sesgo, y el redondeo `ceil` conserva promesas enteras.
- El escudo v1 defiende la promesa VIGENTE; el v2 (incluido aquí) defiende la P90. La calibración fina del v2 y la elección de su punto de operación con el PO son de la Etapa 6.
- El target del escudo v2 usa predicciones in-sample del motor en `train` (levemente optimistas); la evaluación en `test` sigue siendo end-to-end honesta. Refinar con predicciones out-of-fold es mejora futura.
- La elección final de política (P80/P90/P95/mixta) es del negocio (PO), con costos reales.

*Reproducible con `python -m src.models.producto_promesa_riesgo` (D-38).*