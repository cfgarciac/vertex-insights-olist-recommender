# Fase 2 - Backtesting offline de promesas P80/P90/P95

## 1. Resumen ejecutivo

Se simularon promesas de entrega con el modelo elegido en Chat E. Backtesting significa probar una politica en datos historicos como si hubiera estado activa en ese momento.

P90 queda como politica candidata para discusion: reduce fuerte el colchon frente a Olist actual y mantiene una zona de cumplimiento simulada de 96.5% en test. P80 es mas competitiva si negocio acepta mas incumplimiento; P95 es la opcion conservadora si se prioriza confiabilidad.

## 2. Modelo usado

- Dataset: `C:\Users\LENOVO\Documents\Cursos\Soy Henry\PF\proyecto\vertex-insights-olist-recommender\data\processed\orders_fase2_regresion_rolling.csv`
- Modelo reproducido: `random_forest`
- Feature set: `M0_mas_seller_rolling`
- Entrenamiento: solo split `train`.
- Politicas/margenes: calculados solo con split `val`.
- Evaluacion final: split `test`.
- No se guardo modelo `.joblib`.

| split | mae | medae | rmse | p90_abs_error | bias_mean |
| --- | --- | --- | --- | --- | --- |
| train | 4.777 | 3.318 | 7.943 | 9.694 | 0.015 |
| val | 4.553 | 3.625 | 6.461 | 8.612 | 0.947 |
| test | 3.989 | 3.314 | 5.324 | 7.653 | 2.297 |

## 3. Margenes P80/P90/P95

El residual usado fue `dias_entrega_real - prediccion_dias`. Si el residual es positivo, el modelo se quedo corto; por eso se agrega como margen. La promesa simulada fue `ceil(prediccion + margen)`, con minimo de 1 dia.

| politica | margen_dias_val |
| --- | --- |
| P80 | 2.397 |
| P90 | 6.278 |
| P95 | 10.054 |

## 4. Comparacion general en test

Cumplimiento es el porcentaje de ordenes donde `dias_entrega_real <= dias_prometidos`. Colchon es `dias_prometidos - dias_entrega_real`: positivo significa que la promesa sobro, negativo que se incumplio.

| politica | ordenes | cumplimiento | incumplimiento | colchon_promedio | colchon_mediano | colchon_p10 | colchon_p90 | promesa_promedio | promesa_mediana | dif_promesa_promedio_vs_actual | dif_cumplimiento_vs_actual |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| actual_olist | 14,471 | 94.320 | 5.680 | 10.752 | 9.873 | 1.573 | 21.251 | 19.120 | 18.000 | 0.000 | 0.000 |
| P80 | 14,471 | 91.093 | 8.907 | 5.195 | 5.708 | 0.569 | 9.826 | 13.563 | 13.000 | -5.558 | -3.227 |
| P90 | 14,471 | 96.455 | 3.545 | 9.073 | 9.568 | 4.422 | 13.706 | 17.441 | 17.000 | -1.680 | 2.135 |
| P95 | 14,471 | 98.328 | 1.672 | 12.848 | 13.188 | 8.063 | 17.506 | 21.216 | 21.000 | 2.096 | 4.008 |

## 5. Resultados por estado destino

Se reportan estados con volumen suficiente en test. La tabla compacta compara la promesa actual contra P90 para enfocar la lectura regional. El JSON conserva todas las politicas por estado.

| customer_state | ordenes | cumpl_actual_pct | cumpl_p90_pct | promesa_actual | promesa_p90 | dif_promesa_dias | colchon_actual | colchon_p90 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| PA | 114 | 97.368 | 94.737 | 31.544 | 25.605 | -5.939 | 16.373 | 10.434 |
| PE | 241 | 95.021 | 95.021 | 26.340 | 25.029 | -1.311 | 13.804 | 12.492 |
| BA | 458 | 95.415 | 95.415 | 26.341 | 23.504 | -2.836 | 13.248 | 10.412 |
| RJ | 1,625 | 95.138 | 95.938 | 24.275 | 18.814 | -5.461 | 15.219 | 9.758 |
| ES | 272 | 95.956 | 95.956 | 23.062 | 20.779 | -2.283 | 11.860 | 9.577 |
| GO | 275 | 96.000 | 96.364 | 22.913 | 20.615 | -2.298 | 11.617 | 9.319 |
| SP | 6,750 | 92.089 | 96.667 | 14.390 | 14.504 | 0.113 | 7.966 | 8.080 |
| SC | 462 | 96.753 | 96.753 | 21.879 | 19.639 | -2.240 | 12.666 | 10.426 |
| RS | 720 | 96.806 | 97.083 | 24.167 | 20.142 | -4.025 | 13.724 | 9.699 |
| DF | 356 | 96.067 | 97.191 | 19.823 | 20.090 | 0.267 | 10.734 | 11.001 |
| PR | 743 | 97.443 | 97.443 | 19.579 | 17.868 | -1.711 | 11.302 | 9.592 |
| MG | 1,581 | 98.229 | 97.660 | 20.197 | 17.387 | -2.810 | 12.286 | 9.476 |
| MT | 110 | 99.091 | 98.182 | 29.155 | 23.273 | -5.882 | 16.449 | 10.567 |
| CE | 168 | 98.810 | 98.214 | 28.875 | 24.256 | -4.619 | 15.748 | 11.129 |

## 6. Resultados por ruta estado-estado

Se incluyen rutas con al menos 80 ordenes en test. Las rutas de menor cumplimiento ayudan a ubicar donde una politica candidata necesitaria monitoreo. El JSON conserva todas las politicas por ruta.

| ruta_estado | ordenes | cumpl_actual_pct | cumpl_p90_pct | promesa_actual | promesa_p90 | dif_promesa_dias | colchon_actual | colchon_p90 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| SP_PA | 85 | 96.471 | 94.118 | 30.812 | 25.588 | -5.224 | 15.686 | 10.462 |
| PR_MG | 123 | 95.935 | 94.309 | 23.805 | 18.805 | -5.000 | 13.713 | 8.713 |
| PR_RJ | 149 | 98.658 | 94.631 | 31.772 | 20.477 | -11.295 | 21.723 | 10.428 |
| SP_PE | 169 | 94.675 | 94.675 | 26.639 | 25.391 | -1.249 | 13.805 | 12.556 |
| PR_PR | 142 | 94.366 | 95.070 | 15.458 | 14.521 | -0.937 | 8.762 | 7.825 |
| PR_SP | 470 | 97.660 | 95.532 | 21.279 | 16.881 | -4.398 | 13.235 | 8.837 |
| SP_BA | 319 | 96.238 | 95.611 | 27.091 | 23.859 | -3.232 | 13.843 | 10.611 |
| MG_RJ | 138 | 96.377 | 95.652 | 24.080 | 18.754 | -5.326 | 15.074 | 9.748 |
| SC_SP | 208 | 95.192 | 95.673 | 22.120 | 17.274 | -4.846 | 13.722 | 8.876 |
| RJ_RJ | 191 | 84.293 | 95.812 | 14.513 | 13.005 | -1.508 | 8.902 | 7.394 |
| SP_RJ | 963 | 96.366 | 96.262 | 24.605 | 19.210 | -5.396 | 15.312 | 9.916 |
| SP_GO | 190 | 97.895 | 96.316 | 22.626 | 20.426 | -2.200 | 11.378 | 9.178 |
| SP_DF | 219 | 95.890 | 96.347 | 19.511 | 19.877 | 0.365 | 10.470 | 10.835 |
| RS_SP | 140 | 94.286 | 96.429 | 23.886 | 16.443 | -7.443 | 15.258 | 7.815 |
| PR_RS | 86 | 97.674 | 96.512 | 23.512 | 19.907 | -3.605 | 13.268 | 9.663 |

## 7. Lectura de negocio

- P80 prioriza competitividad: acorta mas la promesa, pero acepta mas riesgo de incumplimiento.
- P90 es el balance inicial: conserva una tasa alta de cumplimiento simulado y reduce colchon frente a la promesa historica.
- P95 prioriza confiabilidad: se acerca mas a una promesa conservadora, con mayor colchon visible.
- La promesa actual de Olist sigue siendo el punto de comparacion; este backtesting no mide conversion, abandono de carrito, recompra ni costos.

## 8. Riesgos y limitaciones

- Test no se uso para definir margenes ni elegir politica final.
- El modelo sobreestima dias en test, lo que aumenta colchon en algunas rutas.
- La comparacion usa dias prometidos reconstruidos desde fechas estimadas crudas.
- La simulacion offline no prueba impacto real en comportamiento de clientes.
- Antes de produccion harian falta calibracion operacional, monitoreo y costos.

## 9. Recomendacion

P90 queda como politica candidata para discusion: reduce fuerte el colchon frente a Olist actual y mantiene una zona de cumplimiento simulada de 96.5% en test. P80 es mas competitiva si negocio acepta mas incumplimiento; P95 es la opcion conservadora si se prioriza confiabilidad.

## 10. Validaciones anti-leakage

- `forbidden_features_intersection`: `[]`
- `seller_id_in_features`: `False`
- `dias_entrega_real_in_features`: `False`
- `dias_prometidos_actual_in_features`: `False`
- `val_used_for_margins`: `True`
- `test_used_for_margins`: `False`
- `fase1_files_modified_by_script`: `False`
