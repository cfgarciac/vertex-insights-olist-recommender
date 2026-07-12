# Fase 2 - Modelado de regresion dias_entrega_real

## 1. Resumen ejecutivo

Se entrenaron baselines y regresores para predecir `dias_entrega_real` usando split temporal. La seleccion se hizo solo por MAE en `val`; MAE significa error absoluto medio, es decir, cuantos dias se equivoca el modelo en promedio.

Mejor candidato por validacion: `random_forest` con bloque `M0_mas_seller_rolling` y MAE val 4.553 dias. Su MAE final en test fue 3.989 dias.

## 2. Dataset usado

- Entrada local: `C:\Users\LENOVO\Documents\Cursos\Soy Henry\PF\proyecto\vertex-insights-olist-recommender\data\processed\orders_fase2_regresion_rolling.csv`
- Shape: 96,470 filas x 39 columnas
- Target: `dias_entrega_real`
- No se uso `dias_prometidos`; queda fuera de este chat.
- No se guardo modelo `.joblib`.

| split | ordenes | media | mediana | p90 |
| --- | --- | --- | --- | --- |
| train | 67,529 | 13.82 | 11.48 | 25.09 |
| val | 14,470 | 10.84 | 8.91 | 20.21 |
| test | 14,471 | 8.37 | 7.23 | 14.26 |

## 3. Features por bloque

| bloque | n_features | features |
| --- | --- | --- |
| M0_base_sin_rolling | 15 | mismo_estado, dist_haversine_km, precio_total, flete_total, ratio_flete, n_items, peso_total_g, volumen_total_cm3, mes_compra, dia_semana_compra, tasa_vendedor, sin_historial_vendedor, customer_state, seller_state, categoria_principal |
| M0_mas_ruta_customer_rolling | 23 | mismo_estado, dist_haversine_km, precio_total, flete_total, ratio_flete, n_items, peso_total_g, volumen_total_cm3, mes_compra, dia_semana_compra, tasa_vendedor, sin_historial_vendedor, customer_state, seller_state, categoria_principal, ruta_estado_30d_days_mean_fallback, ruta_estado_30d_days_median, ruta_estado_30d_orders_count, ruta_estado_30d_sin_historial, customer_state_30d_days_mean_fallback, customer_state_30d_days_median, customer_state_30d_orders_count, customer_state_30d_sin_historial |
| M0_mas_categoria_rolling | 18 | mismo_estado, dist_haversine_km, precio_total, flete_total, ratio_flete, n_items, peso_total_g, volumen_total_cm3, mes_compra, dia_semana_compra, tasa_vendedor, sin_historial_vendedor, customer_state, seller_state, categoria_principal, categoria_principal_30d_days_mean_fallback, categoria_principal_30d_orders_count, categoria_principal_30d_sin_historial |
| M0_mas_seller_rolling | 18 | mismo_estado, dist_haversine_km, precio_total, flete_total, ratio_flete, n_items, peso_total_g, volumen_total_cm3, mes_compra, dia_semana_compra, tasa_vendedor, sin_historial_vendedor, customer_state, seller_state, categoria_principal, seller_id_30d_days_mean_fallback, seller_id_30d_orders_count, seller_id_30d_sin_historial |
| M0_todas_las_rolling | 29 | mismo_estado, dist_haversine_km, precio_total, flete_total, ratio_flete, n_items, peso_total_g, volumen_total_cm3, mes_compra, dia_semana_compra, tasa_vendedor, sin_historial_vendedor, customer_state, seller_state, categoria_principal, ruta_estado_30d_days_mean_fallback, ruta_estado_30d_days_median, ruta_estado_30d_orders_count, ruta_estado_30d_sin_historial, customer_state_30d_days_mean_fallback, customer_state_30d_days_median, customer_state_30d_orders_count, customer_state_30d_sin_historial, categoria_principal_30d_days_mean_fallback, categoria_principal_30d_orders_count, categoria_principal_30d_sin_historial, seller_id_30d_days_mean_fallback, seller_id_30d_orders_count, seller_id_30d_sin_historial |

`seller_id` crudo se conserva solo como soporte del dataset, pero no entra a ningun `X_COLS`. La senal de seller se evalua con agregados rolling, conteo y flag de historial.

## 4. Baselines

Los baselines calculan medianas solo con train y aplican fallback cuando un grupo no existe en el pasado.

| modelo | mae | medae | rmse | p90_abs_error | bias_mean |
| --- | --- | --- | --- | --- | --- |
| mediana_ruta_estado_train | 4.558 | 3.753 | 6.552 | 8.577 | 0.532 |
| mediana_customer_state_train | 4.699 | 3.876 | 6.690 | 8.777 | 0.526 |
| mediana_global_train | 5.694 | 4.726 | 7.741 | 9.681 | 0.635 |

## 5. Modelos candidatos y resultados en val

Se entrenaron Ridge, RandomForestRegressor y XGBoost Regressor porque XGBoost estaba instalado en el entorno. Ridge es una regresion lineal regularizada: una linea base interpretable que penaliza coeficientes excesivos.

| modelo | feature_set | mae | medae | rmse | p90_abs_error | bias_mean |
| --- | --- | --- | --- | --- | --- | --- |
| random_forest | M0_mas_seller_rolling | 4.553 | 3.625 | 6.461 | 8.612 | 0.947 |
| random_forest | M0_base_sin_rolling | 4.593 | 3.692 | 6.492 | 8.614 | 0.961 |
| xgboost | M0_mas_seller_rolling | 4.595 | 3.677 | 6.456 | 8.797 | 1.211 |
| random_forest | M0_mas_categoria_rolling | 4.597 | 3.731 | 6.468 | 8.650 | 1.047 |
| xgboost | M0_base_sin_rolling | 4.638 | 3.771 | 6.453 | 8.776 | 1.381 |
| xgboost | M0_todas_las_rolling | 4.714 | 3.696 | 6.602 | 9.450 | 1.408 |
| xgboost | M0_mas_ruta_customer_rolling | 4.736 | 3.722 | 6.627 | 9.474 | 1.407 |
| random_forest | M0_mas_ruta_customer_rolling | 4.789 | 3.906 | 6.626 | 9.159 | 1.471 |
| random_forest | M0_todas_las_rolling | 4.847 | 4.029 | 6.635 | 9.183 | 1.637 |
| xgboost | M0_mas_categoria_rolling | 4.888 | 4.065 | 6.632 | 9.329 | 1.947 |
| ridge | M0_mas_seller_rolling | 5.499 | 4.818 | 7.111 | 10.233 | 3.030 |
| ridge | M0_mas_ruta_customer_rolling | 5.643 | 4.873 | 7.299 | 10.739 | 3.204 |
| ridge | M0_base_sin_rolling | 5.649 | 5.036 | 7.222 | 10.370 | 3.275 |
| ridge | M0_todas_las_rolling | 5.703 | 4.928 | 7.359 | 10.957 | 3.360 |
| ridge | M0_mas_categoria_rolling | 6.068 | 5.560 | 7.547 | 10.936 | 3.958 |

## 6. Evaluacion final en test

El test se uso una sola vez para el candidato elegido por validacion. Bias positivo significa que el modelo sobreestima dias; bias negativo, que tiende a subestimar.

| split | mae | medae | rmse | p90_abs_error | bias_mean |
| --- | --- | --- | --- | --- | --- |
| train | 4.777 | 3.318 | 7.943 | 9.694 | 0.015 |
| val | 4.553 | 3.625 | 6.461 | 8.612 | 0.947 |
| test | 3.989 | 3.314 | 5.324 | 7.653 | 2.297 |

## 7. Ablacion por bloques

Ablacion significa comparar el mismo tipo de modelo agregando o quitando bloques de features para medir que aporta cada familia.

| modelo | feature_set | mae | medae | rmse | p90_abs_error | bias_mean |
| --- | --- | --- | --- | --- | --- | --- |
| random_forest | M0_mas_seller_rolling | 4.553 | 3.625 | 6.461 | 8.612 | 0.947 |
| random_forest | M0_base_sin_rolling | 4.593 | 3.692 | 6.492 | 8.614 | 0.961 |
| xgboost | M0_mas_seller_rolling | 4.595 | 3.677 | 6.456 | 8.797 | 1.211 |
| random_forest | M0_mas_categoria_rolling | 4.597 | 3.731 | 6.468 | 8.650 | 1.047 |
| xgboost | M0_base_sin_rolling | 4.638 | 3.771 | 6.453 | 8.776 | 1.381 |
| xgboost | M0_todas_las_rolling | 4.714 | 3.696 | 6.602 | 9.450 | 1.408 |
| xgboost | M0_mas_ruta_customer_rolling | 4.736 | 3.722 | 6.627 | 9.474 | 1.407 |
| random_forest | M0_mas_ruta_customer_rolling | 4.789 | 3.906 | 6.626 | 9.159 | 1.471 |
| random_forest | M0_todas_las_rolling | 4.847 | 4.029 | 6.635 | 9.183 | 1.637 |
| xgboost | M0_mas_categoria_rolling | 4.888 | 4.065 | 6.632 | 9.329 | 1.947 |
| ridge | M0_mas_seller_rolling | 5.499 | 4.818 | 7.111 | 10.233 | 3.030 |
| ridge | M0_mas_ruta_customer_rolling | 5.643 | 4.873 | 7.299 | 10.739 | 3.204 |
| ridge | M0_base_sin_rolling | 5.649 | 5.036 | 7.222 | 10.370 | 3.275 |
| ridge | M0_todas_las_rolling | 5.703 | 4.928 | 7.359 | 10.957 | 3.360 |
| ridge | M0_mas_categoria_rolling | 6.068 | 5.560 | 7.547 | 10.936 | 3.958 |

## 8. Error por customer_state

| customer_state | ordenes | target_medio | pred_medio | mae | medae | p90_abs_error | bias_mean |
| --- | --- | --- | --- | --- | --- | --- | --- |
| PE | 241 | 12.537 | 18.276 | 8.013 | 7.558 | 12.509 | 5.740 |
| BA | 458 | 13.092 | 16.734 | 6.045 | 5.501 | 10.205 | 3.641 |
| PA | 114 | 15.171 | 18.835 | 5.979 | 5.817 | 11.057 | 3.664 |
| DF | 356 | 9.089 | 13.337 | 5.602 | 5.431 | 8.800 | 4.248 |
| CE | 168 | 13.127 | 17.465 | 5.419 | 5.152 | 9.855 | 4.338 |
| MT | 110 | 12.706 | 16.532 | 4.969 | 4.683 | 8.393 | 3.826 |
| RJ | 1,625 | 9.056 | 12.036 | 4.738 | 4.494 | 8.085 | 2.980 |
| SC | 462 | 9.213 | 12.871 | 4.718 | 4.565 | 8.223 | 3.658 |
| RS | 720 | 10.442 | 13.368 | 4.694 | 4.282 | 8.070 | 2.926 |
| ES | 272 | 11.202 | 14.015 | 4.237 | 4.027 | 7.734 | 2.813 |
| GO | 275 | 11.296 | 13.847 | 4.190 | 3.852 | 7.618 | 2.551 |
| PR | 743 | 8.276 | 11.103 | 4.065 | 3.838 | 6.945 | 2.827 |
| MG | 1,581 | 7.911 | 10.607 | 3.933 | 3.742 | 6.795 | 2.696 |
| SP | 6,750 | 6.424 | 7.724 | 3.023 | 2.502 | 5.613 | 1.301 |

## 9. Error por ruta_estado

| ruta_estado | ordenes | target_medio | pred_medio | mae | medae | p90_abs_error | bias_mean |
| --- | --- | --- | --- | --- | --- | --- | --- |
| SP_PE | 169 | 12.834 | 18.641 | 8.336 | 7.607 | 12.809 | 5.807 |
| SP_PA | 85 | 15.126 | 18.813 | 6.179 | 5.801 | 11.054 | 3.687 |
| SP_BA | 319 | 13.248 | 17.082 | 6.041 | 5.554 | 9.966 | 3.834 |
| SP_DF | 219 | 9.041 | 13.129 | 5.802 | 5.464 | 8.518 | 4.088 |
| SP_CE | 122 | 13.546 | 17.727 | 5.432 | 5.152 | 9.952 | 4.181 |
| PR_MG | 123 | 10.092 | 12.039 | 5.392 | 4.672 | 8.046 | 1.948 |
| MG_RJ | 138 | 9.006 | 11.940 | 5.385 | 4.667 | 8.243 | 2.935 |
| PR_RJ | 149 | 10.049 | 13.679 | 5.289 | 5.361 | 8.936 | 3.630 |
| SP_RS | 463 | 10.968 | 13.841 | 4.816 | 4.312 | 8.025 | 2.872 |
| SP_RJ | 963 | 9.293 | 12.435 | 4.772 | 4.571 | 7.716 | 3.141 |
| SP_MT | 87 | 12.103 | 16.458 | 4.723 | 4.491 | 8.307 | 4.355 |
| SP_SC | 276 | 9.581 | 13.160 | 4.627 | 4.572 | 7.938 | 3.579 |
| RJ_MG | 94 | 7.572 | 10.924 | 4.487 | 4.429 | 7.464 | 3.352 |
| PR_RS | 86 | 10.244 | 13.141 | 4.325 | 4.277 | 7.430 | 2.897 |
| SP_ES | 200 | 11.029 | 13.970 | 4.223 | 4.113 | 7.537 | 2.941 |
| SP_GO | 190 | 11.249 | 13.659 | 4.205 | 3.931 | 7.253 | 2.411 |
| SP_PR | 443 | 8.404 | 11.606 | 4.048 | 4.094 | 6.675 | 3.202 |
| MG_SP | 319 | 7.633 | 9.927 | 3.934 | 3.502 | 6.536 | 2.294 |
| PR_SP | 470 | 8.043 | 10.099 | 3.913 | 3.540 | 6.454 | 2.055 |
| SC_SP | 208 | 8.398 | 10.519 | 3.893 | 3.658 | 6.693 | 2.120 |

## 10. Multicolinealidad

Multicolinealidad significa que dos features cuentan informacion parecida. No invalida el modelo, pero en modelos lineales reduce interpretabilidad porque el merito predictivo se reparte entre variables redundantes.

| feature_a | feature_b | correlation | abs_correlation | lectura |
| --- | --- | --- | --- | --- |
| ratio_flete | precio_total | -0.807 | 0.807 | alta |
| peso_total_g | volumen_total_cm3 | 0.781 | 0.781 | alta |
| dist_haversine_km | mismo_estado | -0.748 | 0.748 | alta |
| dist_haversine_km | flete_total | 0.582 | 0.582 | moderada |
| precio_total | peso_total_g | 0.552 | 0.552 | moderada |
| flete_total | mismo_estado | -0.548 | 0.548 | moderada |
| flete_total | peso_total_g | 0.510 | 0.510 | moderada |
| flete_total | precio_total | 0.480 | 0.480 | moderada |
| precio_total | volumen_total_cm3 | 0.432 | 0.432 | moderada |
| flete_total | volumen_total_cm3 | 0.430 | 0.430 | moderada |
| flete_total | n_items | 0.397 | 0.397 | baja |
| ratio_flete | peso_total_g | -0.287 | 0.287 | baja |
| dist_haversine_km | ratio_flete | 0.212 | 0.212 | baja |
| ratio_flete | volumen_total_cm3 | -0.200 | 0.200 | baja |
| volumen_total_cm3 | n_items | 0.193 | 0.193 | baja |

## 11. Riesgos y limitaciones

- R-14 sigue visible: train tiene entregas mas lentas que test.
- `ruta_estado` cruda no se uso como feature principal por cardinalidad; se priorizaron rolling/fallbacks.
- Seller rolling aporta con cautela por menor cobertura y posible inestabilidad.
- Las features fisicas, flete y distancia tienen redundancia; no se eliminaron sin evidencia de ablacion.
- No se hizo backtesting P80/P90/P95; corresponde a Chat F.

## 12. Recomendacion para Chat F

Usar el candidato elegido como insumo inicial para simular politicas P80/P90/P95. Chat F debe convertir predicciones de dias en promesas y medir cumplimiento, colchon y riesgo por estado/ruta sin cambiar la seleccion realizada aqui.
