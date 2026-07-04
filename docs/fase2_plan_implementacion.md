# Implementation Plan - Fase 2 Regresion dias_entrega_real

> **Estado:** MVP de Fase 2 cerrado documentalmente
> **Proyecto:** Vertex Insights - Olist Marketplace
> **Rama de trabajo:** Harrison
> **Ultimo commit base validado:** d0ca30e feat: agregar experimento clustering fase 2
> **Fecha:** 2026-07-02

---

## 1. Objetivo del plan

Este documento organiza la Fase 2 como una extension controlada de la Fase 1.
La Fase 1 ya esta entregada como clasificacion de `entrega_tarde`; la Fase 2
busca estimar `dias_entrega_real` para apoyar una promesa de entrega mas
honesta, competitiva y defendible.

La Fase 2 no reemplaza la Fase 1. La complementa.

**Regresion** significa predecir un numero. En esta fase, el numero es la
duracion real de entrega en dias.

---

## 2. Reglas duras de trabajo

- No modificar codigo, artefactos ni comportamiento validado de Fase 1.
- Priorizar archivos nuevos para Fase 2.
- No usar `dva_olist` como fuente versionada ni subirlo a GitHub.
- No versionar datasets, archivos `.csv`, `.parquet`, modelos `.joblib` ni
  artefactos pesados.
- No hacer commit, push ni tags sin aprobacion explicita.
- No usar variables posteriores a la compra como features.
- No usar `order_delivered_customer_date` ni `order_delivered_carrier_date`
  como features.
- `dias_entrega_real` es valido como target, pero prohibido como feature.
- `dias_vs_promesa` queda descartado como target principal y prohibido como
  feature.
- `dias_prometidos` no entra al modelo principal inicial; solo puede entrar en
  un benchmark controlado.

**Feature** significa variable de entrada del modelo: una pista usada para
predecir.

**Leakage** significa fuga de datos: usar informacion del futuro como si
existiera al momento de la compra.

---

## 3. Rol de este chat orquestador

Este chat cumple dos funciones:

1. Ejecutar Chat A: dejar plan, criterios y contrato de revision.
2. Revisar los entregables de los demas chats antes de aceptar avances.

El orquestador debe comprobar:

- Si el alcance del subchat coincide con este plan.
- Si se preserva Fase 1 sin modificaciones.
- Si cada archivo nuevo tiene una razon clara.
- Si las features respetan M0, es decir, el momento de compra.
- Si la validacion es temporal, no aleatoria.
- Si los resultados se comparan contra baselines simples.
- Si las conclusiones separan evidencia, inferencia y limitaciones.

**Baseline** significa punto de comparacion simple. Sirve para responder:
"mi modelo aporta algo o solo parece bueno porque lo comparo contra nada?".

---

## 4. Division recomendada por subchats

### Chat A - Planificacion y criterios

**Estado:** completado.

Entregable:

- `docs/fase2_plan_implementacion.md`

Criterio de cierre:

- Plan de subchats definido.
- Archivos nuevos propuestos.
- Checklist de revision listo.
- Sin tocar Fase 1.

### Chat B - ETL experimental Fase 2

**Estado:** completado.

Objetivo:

Construir una tabla experimental a nivel orden para regresion.

Archivos nuevos propuestos:

- `src/features/build_dataset_fase2_regresion.py`
- `tests/test_fase2_dataset.py`

Salida local esperada, no versionada:

- `data/processed/orders_fase2_regresion.csv`

Criterios de aceptacion:

- Una fila por `order_id`.
- Universo: ordenes `delivered` con fecha de compra y entrega real.
- Target: `dias_entrega_real`.
- Split temporal 70/15/15 por `order_purchase_timestamp`.
- Columnas prohibidas fuera del set de features.
- Validacion de que Fase 1 no fue modificada.

### Chat C - EDA e hipotesis de feature engineering

**Estado:** completado.

Objetivo:

Validar hipotesis antes de crear features complejas.

Archivos nuevos propuestos:

- `reports/fase2_eda_regresion.md`
- opcional: `notebooks/05_fase2_eda_regresion.ipynb`

Criterios de aceptacion:

- Comparar `dias_entrega_real` por estado, ruta, categoria y seller.
- Reportar cobertura y estabilidad temporal.
- Separar correlacion de causalidad.
- Justificar que features candidatas son M0 o historicas pasadas.
- Revisar multicolinealidad de forma exploratoria entre features base y
  candidatas.
- Dejar claro que Chat C no selecciona features finales del modelo; solo
  recomienda bloques candidatos y riesgos para las fases siguientes.

**EDA** significa analisis exploratorio de datos: mirar patrones antes de
modelar.

**Multicolinealidad** significa que dos o mas features cuentan informacion muy
parecida. Por ejemplo, `dist_haversine_km`, `flete_total`, `ratio_flete`,
`peso_total_g` y `volumen_total_cm3` pueden solaparse parcialmente porque todas
describen dificultad logistica. En Chat C esto se revisa como advertencia de
diseno, no como eliminacion definitiva.

### Chat D - Features rolling point-in-time

**Estado:** completado.

Objetivo:

Crear features de historia reciente sin mirar futuro.

Archivos nuevos propuestos:

- puede integrarse en `src/features/build_dataset_fase2_regresion.py`
  si el modulo sigue claro.
- o crear `src/features/rolling_fase2.py` si la logica crece demasiado.
- `tests/test_fase2_rolling.py`

Features iniciales:

- `ruta_estado_30d_days_mean`
- `customer_state_30d_days_mean`
- `categoria_principal_30d_days_mean`
- `seller_id_30d_days_mean`
- flags de historial insuficiente cuando aplique.

Criterios de aceptacion:

- Excluir la orden actual.
- Excluir ordenes futuras.
- Medir cobertura por split.
- Tener fallback cuando no haya historial.
- Comparar 30 dias contra alternativas simples antes de aceptar complejidad.
- Entregar features candidatas con nombres, definicion, cobertura y fallback
  documentados.
- No decidir que features quedan finalmente en el modelo. Esa seleccion se hace
  en Chat E con metricas de modelado.

**Rolling point-in-time** significa calcular una ventana movil usando solo datos
anteriores al momento de prediccion.

Nota de alcance:

> Chat D construye features candidatas y valida que sean calculables sin mirar
> el futuro. Chat D no debe presentar las rolling features como seleccion final
> del modelo.

### Chat E - Modelos baseline y regresion

**Estado:** completado.

Objetivo:

Entrenar modelos de regresion sobre la tabla Fase 2.

Archivos nuevos propuestos:

- `src/models/train_fase2_regresion.py`
- `src/models/evaluate_fase2_regresion.py`
- `tests/test_fase2_models.py`

Modelos candidatos:

- Mediana global.
- Mediana por `customer_state`.
- Ridge o Regresion Lineal regularizada.
- Random Forest Regressor.
- XGBoost Regressor.

Criterios de aceptacion:

- Seleccion por validacion temporal.
- Metrica principal: MAE.
- Reportar MedAE, P90 del error absoluto y bias.
- Evaluar error por estado/ruta.
- Modelo principal sin `dias_prometidos`.
- Benchmark separado con `dias_prometidos`, si se aprueba.
- Seleccionar features finales comparando modelos con y sin bloques de features.
- Reportar ablacion por bloques cuando aplique: base M0, rolling por ruta,
  rolling por estado, rolling por categoria y rolling por seller.
- Validar multicolinealidad formalmente cuando se usen modelos lineales como
  Ridge o Regresion Lineal.
- Para modelos de arboles como Random Forest o XGBoost, revisar si features
  redundantes afectan interpretabilidad de importancias, aunque no necesariamente
  empeoren MAE.

**MAE** significa error absoluto medio. Si MAE = 3, el modelo se equivoca
aproximadamente 3 dias en promedio.

**Ablacion** significa agregar o quitar un bloque de features para medir cuanto
aporta. Ejemplo:

```text
Modelo A: features base M0
Modelo B: features base M0 + rolling por ruta

Si B baja el MAE frente a A, rolling por ruta aporta.
Si B no mejora, rolling por ruta no se justifica para el modelo final.
```

Frontera sin ambiguedad:

```text
Chat C = analiza hipotesis, cobertura, estabilidad y multicolinealidad exploratoria.
Chat D = construye features candidatas point-in-time con fallback.
Chat E = entrena modelos y selecciona features finales por MAE, ablacion y validacion temporal.
```

### Chat F - Backtesting P80/P90/P95

**Estado:** completado.

Objetivo:

Simular politicas de promesa sobre datos historicos.

Archivos nuevos propuestos:

- `src/models/backtest_promesas_fase2.py`
- `reports/fase2_backtesting_promesas.md`
- `reports/fase2_metrics.json`

Politicas iniciales:

- P80: promesa mas competitiva, mayor riesgo.
- P90: balance recomendado para discutir.
- P95: promesa conservadora.

Criterios de aceptacion:

- Comparar contra promesa actual de Olist.
- Reportar cumplimiento simulado.
- Reportar tasa de incumplimiento simulada.
- Reportar colchon promedio y mediano.
- Reportar resultados por estado/ruta.
- No vender valor de negocio no medible por el dataset.

**Backtesting** significa simular con datos historicos que habria pasado si una
politica se hubiera usado en ese momento.

### Chat G - Clustering experimental, no MVP

**Estado:** completado como experimento; no incorporado al MVP.

Objetivo:

Explorar agrupamientos solo si los modelos base dejan una pregunta clara.

Archivos nuevos posibles:

- `experiments/fase2_clustering_sellers.md`
- `experiments/fase2_clustering_geoespacial.md`

Criterios para avanzar:

- Mejorar MAE frente al modelo sin cluster.
- Mejorar o mantener backtesting.
- Mantener interpretabilidad.
- Tener fallback para sellers/rutas nuevas.
- Justificar el costo productivo de mantener dos componentes.

**Clustering** significa agrupar observaciones parecidas sin usar una respuesta
correcta como target.

---

## 5. Archivos protegidos de Fase 1

Estos archivos no deben modificarse durante el MVP de Fase 2:

- `src/features/build_dataset.py`
- `src/models/train.py`
- `src/models/evaluate.py`
- `src/models/predict.py`
- `src/models/baseline.py`
- `tests/test_models.py`
- `reports/etapa4_metrics.json`
- `artifacts/modelo_p1.joblib`
- `artifacts/pipeline_p1.joblib`

Si un subchat necesita cambiar alguno, debe detenerse y pedir aprobacion
explicita con justificacion.

---

## 6. Columnas prohibidas como features

Lista minima de columnas prohibidas:

```text
order_delivered_carrier_date
order_delivered_customer_date
delivery_days
delivery_delay_days
is_late_delivery
review_count
avg_review_score
min_review_score
max_review_score
has_review_comment
review_comment_titles
review_comment_messages
last_review_creation_date
last_review_answer_timestamp
is_dissatisfied
entrega_tarde
dias_vs_promesa
dias_entrega_real
```

Notas:

- `dias_entrega_real` se usa como target, no como feature.
- `entrega_tarde` puede usarse para analisis o comparacion, no como feature del
  regresor principal.
- `dias_vs_promesa` no debe usarse como target principal ni como feature.

---

## 7. Dataset experimental esperado

El dataset Fase 2 debe incluir:

- Identificadores minimos para trazabilidad: `order_id`.
- Fecha de compra para split temporal: `order_purchase_timestamp`.
- Split: `train`, `val`, `test`.
- Target: `dias_entrega_real`.
- Features M0 base reutilizables.
- Features rolling aprobadas.
- Flags de historial insuficiente.

No debe incluir como features:

- fechas reales posteriores a la compra;
- reviews;
- target de Fase 1;
- target de Fase 2;
- variables derivadas de la promesa rota.

---

## 8. Criterios de exito de Fase 2

Fase 2 se considera prometedora si:

- [x] Supera la mediana global en MAE.
- [x] Supera o iguala la mediana por estado destino.
- [x] Las rolling 30d fueron construidas y evaluadas por bloques.
- [x] El error regional queda reportado por `customer_state` y `ruta_estado`.
- [x] El backtesting produce una politica P80/P90/P95 defendible.
- [x] La solucion mantiene disciplina anti-leakage.
- [x] Las conclusiones son honestas sobre limites del dataset.

Fase 2 no debe avanzar si:

- [x] No depende de `dias_prometidos`; esa variable no entro al modelo principal.
- [x] No depende de informacion posterior a la compra.
- [x] Supera baselines simples.
- [x] El backtesting deja P90 como politica candidata defendible.
- [x] Las features rolling tienen cobertura documentada y fallback.
- [x] Clustering no se incorpora al MVP porque agrega complejidad sin mejora clara.

---

## 9. Checklist de revision del orquestador

Antes de aceptar cualquier subchat, revisar:

- [x] El subchat declara objetivo y alcance.
- [x] Solo crea archivos nuevos o pide permiso para modificar existentes.
- [x] No toca archivos protegidos de Fase 1.
- [x] No escribe dentro de `dva_olist`.
- [x] No agrega datos o modelos versionables.
- [x] El `git status` queda entendible.
- [x] Las features son M0 o historicas pasadas.
- [x] Hay candado anti-leakage.
- [x] La evaluacion usa split temporal.
- [x] Se comparan baselines simples.
- [x] Se reportan metricas por split.
- [x] Se documentan riesgos y limitaciones.
- [x] No se hace commit, push ni tag sin aprobacion.

---

## 10. Cierre operativo del MVP

La Fase 2 queda cerrada como MVP offline de regresion tabular para
`dias_entrega_real`.

Entregables completados:

- ETL experimental: `src/features/build_dataset_fase2_regresion.py`.
- Dataset base local: `data/processed/orders_fase2_regresion.csv`, 96,470 filas x 21 columnas.
- EDA: `reports/fase2_eda_regresion.md`.
- Rolling point-in-time: `reports/fase2_rolling_features.md`.
- Dataset rolling local: `data/processed/orders_fase2_regresion_rolling.csv`, 96,470 filas x 39 columnas.
- Modelado: `reports/fase2_modelado_regresion.md`.
- Backtesting: `reports/fase2_backtesting_promesas.md`.
- Clustering experimental: `experiments/fase2_clustering_experimento.md`.
- Cierre MVP: `reports/fase2_cierre_mvp.md`.

Decision final del MVP:

- Modelo seleccionado: `random_forest` con feature set `M0_mas_seller_rolling`.
- Metricas finales: MAE val 4.553 dias; MAE test 3.989 dias; bias test +2.297 dias.
- Politica candidata: P90, por balance entre cumplimiento simulado y promesa promedio.
- Clustering: no incorporado al MVP; queda como linea experimental futura.
