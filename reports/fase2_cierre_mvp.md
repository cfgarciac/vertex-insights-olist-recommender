# Fase 2 - Cierre MVP de regresion sobre dias_entrega_real

> **Proyecto:** Vertex Insights - Olist Marketplace
> **Problema:** P1 - Desempeno de entrega
> **Fase:** Fase 2 - MVP offline de regresion tabular
> **Fecha de cierre:** 2026-07-02
> **Estado:** Cerrado para entrega documental

---

## 1. Resumen ejecutivo

La Fase 2 queda cerrada como MVP offline para estimar `dias_entrega_real`, es
decir, la duracion real entre la compra y la entrega al cliente. El objetivo no
fue reemplazar la Fase 1, sino complementarla: Fase 1 clasifica riesgo de romper
la promesa actual; Fase 2 estima dias reales para discutir una promesa de entrega
mas honesta y competitiva.

El mejor modelo fue `random_forest` con el bloque `M0_mas_seller_rolling`.
Alcanzo MAE de 4.553 dias en validacion y 3.989 dias en test. MAE significa
error absoluto medio: en simple, cuantos dias se equivoca el modelo en promedio.
El bias test fue +2.297 dias, lo que indica una tendencia conservadora: el modelo
tiende a predecir mas dias de los que finalmente toma la entrega.

En backtesting, que significa simular en datos historicos que habria pasado si
una politica se hubiera usado, la politica P90 queda como candidata preliminar.
P90 logro 96.46% de cumplimiento simulado en test, con promesa promedio de 17.44
dias, frente a 94.32% y 19.12 dias de la promesa actual de Olist.

---

## 2. Objetivo de negocio y objetivo tecnico

Objetivo de negocio:

> Ayudar a Olist a definir promesas de entrega confiables para el cliente y, al
> mismo tiempo, no innecesariamente conservadoras.

Objetivo tecnico:

> Entrenar y evaluar un modelo de regresion supervisada tabular para predecir
> `dias_entrega_real` usando solo informacion disponible al momento de compra o
> historicos calculados sin mirar el futuro.

Regresion significa predecir un numero. En esta fase, el numero es la duracion
real de entrega en dias.

---

## 3. Alcance final del MVP

Dentro del MVP:

- Construir dataset experimental de Fase 2 a nivel orden.
- Mantener split temporal 70/15/15.
- Construir features rolling point-in-time.
- Entrenar baselines y modelos de regresion.
- Seleccionar modelo por MAE en validacion.
- Evaluar una sola vez en test el candidato elegido.
- Simular politicas de promesa P80, P90 y P95.
- Probar clustering solo como experimento avanzado.
- Documentar decisiones, riesgos y limitaciones.

Fuera del MVP:

- No desplegar API, dashboard ni servicio productivo.
- No guardar modelo `.joblib` de Fase 2.
- No modificar Fase 1.
- No medir conversion, abandono de carrito, recompra ni costos logisticos reales.
- No incorporar clustering al modelo principal.

---

## 4. Dataset usado y splits temporales

Dataset base Fase 2:

- Archivo local: `data/processed/orders_fase2_regresion.csv`
- Shape: 96,470 filas x 21 columnas
- Unidad de analisis: una fila por orden
- Target: `dias_entrega_real`

Dataset con rolling features:

- Archivo local: `data/processed/orders_fase2_regresion_rolling.csv`
- Shape: 96,470 filas x 39 columnas

Split temporal:

| split | ordenes | periodo | uso |
| --- | ---: | --- | --- |
| train | 67,529 | 2016-09-15 a 2018-04-15 | Entrenar modelos |
| val | 14,470 | 2018-04-15 a 2018-06-21 | Elegir modelo y margenes |
| test | 14,471 | 2018-06-21 a 2018-08-29 | Evaluacion final |

Split temporal significa entrenar con pasado y probar con futuro. Es importante
porque evita que el modelo aprenda patrones que todavia no existirian en un uso
real.

---

## 5. Criterios anti-leakage

Leakage significa fuga de informacion: usar datos del futuro como si existieran
en el momento de compra. La Fase 2 mantuvo los siguientes candados:

- `dias_entrega_real` se usa solo como target, no como feature.
- `order_delivered_customer_date` y `order_delivered_carrier_date` no salen como
  features.
- `entrega_tarde`, `dias_vs_promesa`, reviews y variables post-entrega quedan
  fuera del modelo.
- `dias_prometidos` no entra al modelo principal.
- Las rolling features usan solo ordenes previas ya entregadas antes de M0.
- M0 significa momento de compra: el instante en que la promesa deberia definirse.
- El split `test` no se uso para seleccionar modelo ni margenes.

---

## 6. Feature engineering utilizado

Feature engineering significa crear variables utiles para el modelo a partir de
datos disponibles.

Features base M0:

- Geografia: `customer_state`, `seller_state`, `mismo_estado`, `dist_haversine_km`.
- Orden/envio: `precio_total`, `flete_total`, `ratio_flete`, `n_items`,
  `peso_total_g`, `volumen_total_cm3`.
- Temporalidad: `mes_compra`, `dia_semana_compra`.
- Seller historico: `tasa_vendedor`, `sin_historial_vendedor`.
- Producto: `categoria_principal`.

Features rolling point-in-time:

- `ruta_estado_30d_*`
- `customer_state_30d_*`
- `categoria_principal_30d_*`
- `seller_id_30d_*`

Rolling point-in-time significa mirar una ventana movil de historia reciente,
pero solo con eventos cerrados antes de la orden actual. En simple: el modelo
aprende del pasado disponible, no del futuro.

---

## 7. Modelo seleccionado

| campo | valor |
| --- | --- |
| Modelo | `random_forest` |
| Feature set | `M0_mas_seller_rolling` |
| Regla de seleccion | Menor MAE en validacion |
| Modelo guardado | No |

El bloque seleccionado combina features M0 con rolling de seller:

- `seller_id_30d_days_mean_fallback`
- `seller_id_30d_orders_count`
- `seller_id_30d_sin_historial`

`seller_id` crudo no entro como feature del regresor. Se uso solo como llave para
calcular agregados historicos.

---

## 8. Metricas finales

| split | MAE | MedAE | RMSE | P90 error abs. | bias |
| --- | ---: | ---: | ---: | ---: | ---: |
| train | 4.777 | 3.318 | 7.943 | 9.694 | 0.015 |
| val | 4.553 | 3.625 | 6.461 | 8.612 | 0.947 |
| test | 3.989 | 3.314 | 5.324 | 7.653 | 2.297 |

MedAE es la mediana del error absoluto. RMSE penaliza mas los errores grandes.
P90 del error absoluto indica que 90% de los errores quedan por debajo de ese
valor.

Lectura:

- El modelo supera baselines simples.
- El test reciente es mas rapido que train, consistente con R-14.
- El bias positivo en test vuelve al modelo conservador para promesas.

---

## 9. Backtesting de promesas

Los margenes se calcularon en `val` usando el residual:

```text
dias_entrega_real - prediccion_dias
```

La promesa simulada fue:

```text
ceil(prediccion_dias + margen)
```

Margenes:

| politica | margen dias val |
| --- | ---: |
| P80 | 2.397 |
| P90 | 6.278 |
| P95 | 10.054 |

Comparacion en test:

| politica | cumplimiento | incumplimiento | colchon promedio | promesa promedio |
| --- | ---: | ---: | ---: | ---: |
| actual Olist | 94.32% | 5.68% | 10.75 | 19.12 |
| P80 | 91.09% | 8.91% | 5.20 | 13.56 |
| P90 | 96.46% | 3.55% | 9.07 | 17.44 |
| P95 | 98.33% | 1.67% | 12.85 | 21.22 |

Colchon significa diferencia entre dias prometidos y dias reales. Si es alto, la
promesa es conservadora; si es negativo, se incumple.

---

## 10. Decision final sobre P80/P90/P95

Decision MVP:

> P90 queda como politica candidata preliminar para discusion de negocio.

Razon:

- Mejora cumplimiento frente a la promesa historica de Olist.
- Reduce la promesa promedio frente a P95 y frente a la promesa actual.
- Mantiene un balance defendible entre confianza y competitividad.

Lectura de alternativas:

- P80 es mas competitiva, pero sube el incumplimiento a 8.91%.
- P95 es mas confiable, pero aumenta la promesa promedio a 21.22 dias.
- P90 no es decision productiva final; requiere validacion con costos y apetito
  de riesgo del negocio.

---

## 11. Decision final sobre clustering

Clustering significa agrupar observaciones parecidas sin usar una etiqueta
objetivo. Se probo como experimento avanzado, no como requisito del MVP.

Mejor variante:

- `ruta_k8`
- MAE val: mejora aproximada de -0.0006 dias frente al baseline.
- MAE test: mejora aproximada de -0.0028 dias frente al baseline.
- Cumplimiento P90 test: baja de 96.455% a 96.434%.

Decision MVP:

> No incorporar clustering al MVP.

Razon:

- La mejora es insignificante.
- No alcanza el umbral minimo definido antes del experimento.
- Agrega costo productivo: versionar clusters, fallbacks, monitoreo y explicacion.

Clustering queda documentado como linea experimental futura.

---

## 12. Limitaciones

- El dataset no contiene conversion, abandono de carrito, recompra ni costo real
  de incumplir o sobre-prometer.
- No hay variables logisticas ricas como carrier real, capacidad, tipo de servicio,
  inventario, SLA interno o eventos operativos.
- Las ordenes canceladas/no entregadas quedan fuera del target principal.
- El test pertenece a un periodo mas rapido que train, por lo que hay riesgo de
  cambio de regimen temporal.
- Las promesas simuladas son offline; no prueban comportamiento real del cliente.
- No se calibro una politica productiva con costos de negocio.

---

## 13. Riesgos pendientes

- R-14: drift temporal o cambio de regimen. El futuro reciente es mas rapido que
  el pasado de entrenamiento.
- Riesgo de promesa agresiva: P80 puede parecer atractiva, pero aumenta el
  incumplimiento simulado.
- Riesgo de promesa conservadora: P95 protege cumplimiento, pero puede hacer que
  Olist parezca lento.
- Riesgo operativo de clustering: complejidad alta sin mejora material.
- Riesgo por ausencia de variables logisticas mas ricas: el modelo usa proxies,
  no observaciones directas de la operacion.

---

## 14. Recomendacion final para la entrega

Presentar Fase 2 como MVP offline cerrado, no como sistema productivo. La entrega
defendible es:

> Olist puede estimar dias reales de entrega con un modelo tabular supervisado y
> usar P90 como politica candidata inicial para promesas mas confiables, dejando
> claro que la validacion productiva requiere costos, monitoreo y calibracion de
> negocio.

La narrativa recomendada es conservar Fase 1 como alerta de riesgo contra la
promesa actual y presentar Fase 2 como evolucion natural para construir mejores
promesas.

---

## 15. Proximos pasos fuera del MVP

- Calibrar la politica de promesa con costos de negocio reales.
- Evaluar ventanas temporales mas recientes para mitigar R-14.
- Monitorear cumplimiento por estado y ruta.
- Probar variables logisticas adicionales si Olist las tuviera disponibles.
- Definir un umbral de riesgo aceptable con Product Owner.
- Preparar una version productiva solo si se aprueba API, monitoreo y estrategia
  de retraining.
- Reabrir clustering solo si aparece una mejora material o una necesidad
  operacional clara.
