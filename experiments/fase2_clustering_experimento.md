# Fase 2 - Experimento de clustering

## 1. Resumen ejecutivo

Se probo clustering como experimento avanzado, no como requisito del MVP. Clustering significa agrupar rutas, sellers u ordenes geograficamente parecidas sin usar una etiqueta objetivo. En este experimento los clusters se formaron solo con variables M0 o perfiles de train basados en variables M0; no se uso `dias_entrega_real` para crear los grupos.

El baseline vigente es `random_forest + M0_mas_seller_rolling` con MAE val 4.553 y MAE test 3.989. La mejor variante con clustering fue `ruta_k8` con MAE val 4.553 y delta val -0.001 dias.

## 2. Factibilidad y eleccion del primer experimento

La prueba mas viable era empezar por rutas, porque Fase 2 ya mostro que `ruta_estado` y `customer_state` tienen senal y cobertura alta. Sellers tambien se probo, pero con cautela: muchos sellers tienen poco historial, por eso `seller_id` se uso solo como llave para asignar el cluster, no como feature cruda. El cluster geografico simple se incluyo como control para ver si agrupaba mejor que `customer_state`, `seller_state`, `ruta_estado` y `dist_haversine_km`.

## 3. Criterios de exito definidos antes de correr

- Mejora minima de MAE val: al menos 0.02 dias frente al baseline vigente.
- No degradar test de forma relevante: maximo +0.03 dias de MAE test.
- No empeorar P90: cumplimiento test no debe caer mas de 0.2 puntos porcentuales.
- Cluster interpretable con descripcion operativa simple.
- Cobertura suficiente y fallback claro para rutas/sellers nuevos.
- Costo productivo razonable frente a la mejora observada.

## 4. Variables usadas para clustering

| cluster | variables | usa_target | lectura |
| --- | --- | --- | --- |
| ruta | dist_haversine_km_median, flete_total_median, ratio_flete_median, precio_total_median, peso_total_g_median, volumen_total_cm3_median, n_items_mean, mismo_estado_mean, ordenes_train, customer_state_mode, seller_state_mode | no | perfil de origen-destino por distancia, costo y volumen de train |
| seller | dist_haversine_km_median, flete_total_median, ratio_flete_median, precio_total_median, peso_total_g_median, volumen_total_cm3_median, n_items_mean, mismo_estado_mean, ordenes_train, categorias_unicas, destinos_unicos, seller_state_mode, categoria_principal_mode, customer_state_mode | no | perfil operativo del seller en train; seller_id solo asigna el grupo |
| geo | dist_haversine_km, mismo_estado, customer_state, seller_state | no | agrupacion simple por distancia, mismo estado, destino y origen |

## 5. Comparacion de MAE

MAE significa error absoluto medio: cuantos dias se equivoca el modelo en promedio. Delta negativo frente al baseline seria mejora.

| variant | cluster_type | k | mae_val | delta_mae_val_vs_baseline | mae_test | delta_mae_test_vs_baseline | p90_abs_error_val | bias_val |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ruta_k8 | ruta | 8 | 4.553 | -0.001 | 3.987 | -0.003 | 8.599 | 0.949 |
| ruta_k4 | ruta | 4 | 4.553 | -0.000 | 3.987 | -0.002 | 8.619 | 0.939 |
| geo_k4 | geo | 4 | 4.554 | 0.001 | 3.990 | 0.000 | 8.614 | 0.948 |
| seller_k4 | seller | 4 | 4.555 | 0.002 | 3.993 | 0.004 | 8.609 | 0.956 |
| seller_k8 | seller | 8 | 4.556 | 0.003 | 3.996 | 0.006 | 8.614 | 0.959 |
| geo_k8 | geo | 8 | 4.564 | 0.011 | 4.005 | 0.015 | 8.693 | 0.977 |

## 6. Cobertura

Cobertura indica que porcentaje de ordenes pudo recibir un cluster calculado desde train. Las rutas o sellers nuevos caen en un fallback.

| variant | cluster_type | split | ordenes | coverage_pct | fallback_pct | clusters_observados |
| --- | --- | --- | --- | --- | --- | --- |
| ruta_k4 | ruta | train | 67,529 | 100.000 | 0.000 | 4 |
| ruta_k4 | ruta | val | 14,470 | 99.841 | 0.159 | 5 |
| ruta_k4 | ruta | test | 14,471 | 99.807 | 0.193 | 5 |
| ruta_k8 | ruta | train | 67,529 | 100.000 | 0.000 | 8 |
| ruta_k8 | ruta | val | 14,470 | 99.841 | 0.159 | 9 |
| ruta_k8 | ruta | test | 14,471 | 99.807 | 0.193 | 9 |
| seller_k4 | seller | train | 67,529 | 100.000 | 0.000 | 4 |
| seller_k4 | seller | val | 14,470 | 90.332 | 9.668 | 5 |
| seller_k4 | seller | test | 14,471 | 74.819 | 25.181 | 5 |
| seller_k8 | seller | train | 67,529 | 100.000 | 0.000 | 8 |
| seller_k8 | seller | val | 14,470 | 90.332 | 9.668 | 9 |
| seller_k8 | seller | test | 14,471 | 74.819 | 25.181 | 9 |
| geo_k4 | geo | train | 67,529 | 100.000 | 0.000 | 4 |
| geo_k4 | geo | val | 14,470 | 100.000 | 0.000 | 4 |
| geo_k4 | geo | test | 14,471 | 100.000 | 0.000 | 4 |
| geo_k8 | geo | train | 67,529 | 100.000 | 0.000 | 8 |
| geo_k8 | geo | val | 14,470 | 100.000 | 0.000 | 8 |
| geo_k8 | geo | test | 14,471 | 100.000 | 0.000 | 8 |

## 7. Interpretacion de clusters

La interpretacion usa solo train y variables M0. No es una explicacion causal; solo describe que grupos quedaron parecidos para el algoritmo.

| tipo | cluster | ordenes_train | dist_mediana | flete_mediano | mismo_estado_pct | customer_state_top | seller_state_top | categoria_top | rutas_train | sellers_train |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ruta | ruta_cluster_k4_0 | 38,592 | 575.586 | 17.670 | 0.000 | RJ | SP | bed_bath_table | 174.000 | NA |
| ruta | ruta_cluster_k4_2 | 23,083 | 100.024 | 12.600 | 100.000 | SP | SP | bed_bath_table | 17.000 | NA |
| ruta | ruta_cluster_k4_3 | 5,551 | 2,149.050 | 30.910 | 0.000 | PE | SP | health_beauty | 145.000 | NA |
| ruta | ruta_cluster_k4_1 | 303 | 757.244 | 36.980 | 0.000 | SP | ES | garden_tools | 45.000 | NA |
| seller | seller_cluster_k4_0 | 43,826 | 439.684 | 16.320 | 35.682 | SP | SP | bed_bath_table | NA | 241.000 |
| seller | seller_cluster_k4_1 | 12,565 | 343.830 | 16.000 | 48.301 | SP | SP | health_beauty | NA | 830.000 |
| seller | seller_cluster_k4_2 | 10,524 | 616.244 | 18.700 | 11.412 | SP | PR | computers_accessories | NA | 1,007.000 |
| seller | seller_cluster_k4_3 | 614 | 505.592 | 67.520 | 28.502 | SP | SP | auto | NA | 100.000 |
| geo | geo_cluster_k4_2 | 23,083 | 100.024 | 12.600 | 100.000 | SP | SP | bed_bath_table | NA | NA |
| geo | geo_cluster_k4_1 | 21,910 | 544.194 | 17.385 | 0.000 | RJ | SP | bed_bath_table | NA | NA |
| geo | geo_cluster_k4_0 | 14,680 | 575.842 | 17.980 | 0.000 | SP | PR | computers_accessories | NA | NA |
| geo | geo_cluster_k4_3 | 7,856 | 2,017.918 | 27.730 | 0.000 | BA | SP | health_beauty | NA | NA |

## 8. Backtesting P90

Se compara la politica P90 del baseline contra la mejor variante de clustering. P90 significa agregar un margen calculado en validacion para buscar una promesa conservadora.

| variant | margen_p90_val | cumplimiento_test | incumplimiento_test | colchon_promedio_test | colchon_mediano_test | promesa_promedio_test | promesa_mediana_test |
| --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | 6.278 | 96.455 | 3.545 | 9.073 | 9.568 | 17.441 | 17.000 |
| ruta_k8 | 6.278 | 96.434 | 3.566 | 9.070 | 9.562 | 17.438 | 17.000 |

## 9. Validaciones anti-leakage

- `target_used_for_clustering`: `False`
- `forbidden_cluster_inputs_intersection`: `[]`
- `seller_id_used_as_regressor_feature`: `False`
- `seller_id_used_only_as_mapping_key`: `True`
- `test_used_to_fit_clusters`: `False`
- `test_used_to_select_variant`: `False`
- `models_saved`: `False`

## 10. Costo productivo

Incorporar clusters implicaria mantener un segundo componente: entrenar y versionar el modelo de clustering, guardar mapas de ruta/seller o un transformador geografico, definir fallback para rutas y sellers nuevos, monitorear deriva de perfiles y explicar el significado de cada cluster. Ese costo solo se justifica si la mejora de MAE y backtesting es clara.

## 11. Decision recomendada: incorporar / no incorporar al MVP

**Decision recomendada:** no incorporar al MVP

### Razon

La mejor variante (`ruta_k8`) no supera el umbral minimo de mejora en MAE val frente al baseline vigente. Como el MVP ya funciona sin clustering, la complejidad adicional no queda justificada.

### Costo productivo

Alto frente a una feature tabular simple: exige versionar clusters, fallbacks para llaves nuevas, monitoreo de drift y explicacion adicional para negocio.

### Plan de integracion si se aprueba

- Congelar una definicion de cluster y recalcularla solo con train/historial cerrado.
- Versionar el artefacto de clustering y el mapa ruta/seller -> cluster.
- Definir fallback para rutas o sellers nuevos: cluster `nuevo_o_sin_perfil` o perfil global.
- Agregar tests anti-leakage que fallen si el target entra al clustering.
- Actualizar documentacion de Fase 2, modelado y backtesting antes de integrarlo.
- Integrar solo despues del cierre de Fase 2 MVP, como mejora posterior aprobada.

## 12. Comando reproducible

```powershell
venv\Scripts\python.exe scripts\experiment_fase2_clustering.py --k-list 4,8
```
