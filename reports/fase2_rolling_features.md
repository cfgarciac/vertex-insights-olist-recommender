# Fase 2 - Rolling features point-in-time

## 1. Resumen ejecutivo

Se construyeron features rolling de 30 dias para regresion sobre `dias_entrega_real`, sin entrenar modelos. Rolling significa ventana movil de historia reciente: para cada orden se miran ordenes del mismo grupo cuya entrega real ya ocurrio antes de la compra actual.

La salida local `data/processed/orders_fase2_regresion_rolling.csv` quedo con 96,470 filas x 39 columnas. Las fechas reales de entrega se usaron solo internamente para validar que el historial estuviera cerrado; no salen en el dataset final.

## 2. Features creadas

Columnas rolling puras:

- `ruta_estado_30d_days_mean`
- `ruta_estado_30d_days_median`
- `ruta_estado_30d_orders_count`
- `ruta_estado_30d_sin_historial`
- `customer_state_30d_days_mean`
- `customer_state_30d_days_median`
- `customer_state_30d_orders_count`
- `customer_state_30d_sin_historial`
- `categoria_principal_30d_days_mean`
- `categoria_principal_30d_orders_count`
- `categoria_principal_30d_sin_historial`
- `seller_id_30d_days_mean`
- `seller_id_30d_orders_count`
- `seller_id_30d_sin_historial`

Columnas con fallback jerarquico:

- `customer_state_30d_days_mean_fallback`
- `ruta_estado_30d_days_mean_fallback`
- `categoria_principal_30d_days_mean_fallback`
- `seller_id_30d_days_mean_fallback`

## 3. Definicion de cada familia

| familia | definicion | fallback |
| --- | --- | --- |
| ruta_estado | Ordenes con mismo origen-destino estado en los 30 dias previos ya entregadas antes de M0. | ruta_estado -> customer_state -> mediana global train |
| customer_state | Ordenes al mismo estado destino en los 30 dias previos ya entregadas antes de M0. | customer_state -> mediana global train |
| categoria_principal | Ordenes de la misma categoria principal en los 30 dias previos ya entregadas antes de M0. | categoria_principal -> mediana global train |
| seller_id | Ordenes del mismo seller en los 30 dias previos ya entregadas antes de M0. | seller_id -> ruta_estado -> customer_state -> mediana global train |

## 4. Cobertura por split

| split | grupo | ordenes | cobertura_pct | conteo_mediano | conteo_p90 |
| --- | --- | --- | --- | --- | --- |
| train | ruta_estado | 67,529 | 97.65 | 178.00 | 1,942.20 |
| train | customer_state | 67,529 | 99.41 | 602.00 | 2,723.00 |
| train | categoria_principal | 67,529 | 99.05 | 218.00 | 510.00 |
| train | seller_id | 67,529 | 89.83 | 11.00 | 84.00 |
| val | ruta_estado | 14,470 | 99.04 | 450.00 | 2,564.00 |
| val | customer_state | 14,470 | 100.00 | 1,050.00 | 3,305.00 |
| val | categoria_principal | 14,470 | 99.94 | 396.00 | 684.00 |
| val | seller_id | 14,470 | 92.19 | 12.00 | 103.00 |
| test | ruta_estado | 14,471 | 98.75 | 227.00 | 2,241.00 |
| test | customer_state | 14,471 | 100.00 | 823.00 | 3,056.00 |
| test | categoria_principal | 14,471 | 99.90 | 338.00 | 674.00 |
| test | seller_id | 14,471 | 89.90 | 9.00 | 65.00 |

## 5. Porcentaje de fallback por split

| split | grupo | fallback_pct |
| --- | --- | --- |
| train | customer_state | 0.59 |
| train | ruta_estado | 2.35 |
| train | categoria_principal | 0.95 |
| train | seller_id | 10.17 |
| val | customer_state | 0.00 |
| val | ruta_estado | 0.96 |
| val | categoria_principal | 0.06 |
| val | seller_id | 7.81 |
| test | customer_state | 0.00 |
| test | ruta_estado | 1.25 |
| test | categoria_principal | 0.10 |
| test | seller_id | 10.10 |

## 6. Comparacion basica 30d por grupo

La siguiente tabla usa cada columna `_fallback` como regla simple de prediccion y calcula MAE. MAE significa error absoluto medio: cuantos dias se equivoca la regla en promedio. Esto no selecciona features finales; solo mide senal candidata para Chat E.

| split | regla | mae_dias | pred_mediana |
| --- | --- | --- | --- |
| test | ruta_estado_30d | 3.73 | 8.18 |
| test | customer_state_30d | 3.74 | 8.27 |
| test | seller_id_30d | 4.14 | 8.57 |
| test | categoria_principal_30d | 4.16 | 9.28 |
| train | ruta_estado_30d | 5.79 | 11.84 |
| train | customer_state_30d | 5.91 | 11.55 |
| train | categoria_principal_30d | 6.75 | 12.47 |
| train | seller_id_30d | 6.85 | 12.00 |
| val | ruta_estado_30d | 5.79 | 11.52 |
| val | customer_state_30d | 5.85 | 11.62 |
| val | categoria_principal_30d | 6.69 | 13.58 |
| val | seller_id_30d | 6.71 | 12.18 |

## 7. Validaciones anti-leakage

- La orden actual queda excluida porque su entrega ocurre despues de su compra.
- Ordenes futuras quedan excluidas al exigir entrega real anterior a M0.
- Ordenes compradas antes pero entregadas despues de M0 no aportan historial.
- La ventana usa entregas cerradas dentro de los 30 dias previos a la compra.
- `order_delivered_customer_date` no sale en el dataset final.
- `order_delivered_carrier_date`, `dias_vs_promesa`, reviews y `entrega_tarde` no salen como features.
- `seller_id` crudo se conserva solo como soporte heredado del ETL base; la feature de seller es agregada historica.

## 8. Riesgos y limitaciones

- El cambio de regimen R-14 sigue abierto: test es mas rapido que train.
- Seller tiene menor cobertura reciente; por eso requiere conteo, flag y fallback.
- Las columnas `_fallback` usan la mediana global de train como respaldo final.
- La multicolinealidad entre distancia, flete, peso, volumen y `mismo_estado` debe evaluarse en Chat E.
- Estas features son candidatas; todavia no hay seleccion final ni entrenamiento.

## 9. Recomendacion para Chat E

Entrenar baselines y modelos de regresion comparando bloques: base M0, base + ruta/customer rolling, base + categoria rolling y base + seller rolling. La seleccion debe hacerse con validacion temporal y MAE en val, manteniendo las alertas de cobertura y multicolinealidad.
