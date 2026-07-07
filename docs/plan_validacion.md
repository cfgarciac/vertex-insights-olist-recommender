# Plan de validación del producto P1 (Etapa 6, HU-12)

> **Fecha:** 2026-07-05 · **Alcance:** validación aplicada al producto
> `producto_promesa_riesgo.joblib` (D-38) + criterios de re-validación en producción
> (D-39/D-41) · **Complementa:** `docs/justificacion_modelo.md`,
> `docs/estrategia_monitoreo.md`

## 1. Protocolo de validación aplicado (desarrollo)

| # | Control | Cómo se aplicó | Evidencia |
|---|---|---|---|
| 1 | **Split temporal 70/15/15** | train: 2016-09 → 2018-04-15 · val: → 2018-06-21 · test: → 2018-08-29. Sin barajado: simula predecir el futuro | `data/processed/orders_features.csv` (columna `split`), D-23 |
| 2 | **Anti-fuga [t0]** | Solo features conocibles al momento de la compra; verificación automática `assert_no_forbidden_features`; auditoría R-12 | D-22/D-26, cierre Etapa 3/4 |
| 3 | **Evaluación única en test** | Toda selección (modelos, política, umbrales) se hizo en train/val; test se tocó UNA vez al cierre | D-27/D-35/D-36/D-38 |
| 4 | **Márgenes solo en validación** | P80/P90/P95 calculados sobre residuos de val (régimen reciente), nunca de test | `producto_promesa_riesgo.py`, D-36 |
| 5 | **Calibración** | Isotónica sobre el score del escudo; verificada con Brier 0.063 en test | D-31, `reports/etapa4_*` |
| 6 | **Auditoría independiente de métricas** | Recomputación desde cero de todas las cifras reportadas (15/15 checks) | auditoría D-38 |

## 2. Validación del serving (el modelo desplegado == el modelo evaluado)

| # | Control | Resultado |
|---|---|---|
| 1 | **Test de contrato** (`tests/test_feature_builder.py`) | Columnas producidas == listas guardadas EN el artefacto (candado anti-divergencia; también corre al arrancar la API) |
| 2 | **API == modelo directo** | Mismos payloads por HTTP y en memoria: idénticos al decimal |
| 3 | **API == evaluación offline** | 5 órdenes reales de test comparadas por `order_id` contra `reports/predicciones_promesa_riesgo.csv`: promesa, predicción y p_tarde exactas |
| 4 | **Replay E2E de producción simulada** | 1.500 órdenes de test por la API completa: cumplimiento **96.40%** / alertas 34.80% vs 96.70% / 34.66% offline |
| 5 | **Docker == venv** | Unpickle y respuestas idénticas dentro del contenedor (imagen con pins de versiones) |
| 6 | **Suite de tests** | 67/67 (100% sintética: corre en CI sin datos ni artefactos) |

## 3. Validación del monitoreo (el detector funciona en ambos sentidos)

| Escenario | Resultado esperado | Resultado obtenido |
|---|---|---|
| Replay sin drift inducido | Detectar el drift real R-14 (documentado) sin falsas alarmas del vigilante | ✔ 3 severos reales (`mes_compra`, `dias_prometidos`, `flete_total`); vigilante "sin alertas" (+2.90 d vs ref +3.17 d) |
| Features derivadas por lookup | Excluirlas del veredicto (PSI inflado artificialmente) | ✔ marcadas `derivada` vía flags de imputación |
| **Drift inducido** (precios ×1.5, 60% órdenes a N/NE, +5 meses) | El detector DEBE disparar | ✔ score PSI 1.23 → 1.76; alertas 34.8% → 66.3%; vigilante dispara el diagnóstico correcto |

## 4. Criterios de re-validación en producción (D-41)

**Disparadores** (cualquiera activa el runbook):
1. PSI > 0.25 en **≥ 2 features clave no-derivadas**, o
2. Cumplimiento realizado **< 95%** en ventana de 30 días, o
3. Sobre-predicción media **< +1.6 d** (la mitad de la referencia de test) **o negativa**
   (el motor sub-predice → promesas cortas → el cumplimiento caerá).

**Runbook escalonado (R-14):**
1. **Recalibrar márgenes** con residuos de una ventana reciente (barato; no reabre el modelado).
2. **Reentrenar con re-ventaneo** del train y re-serializar el artefacto
   (versión MINOR según convención de tags).
3. Concept drift confirmado (cambia la relación features→target) → **reentrenamiento
   obligatorio** + revisión de features.

**Cadencia propuesta:** el ciclo `simulate → drift → performance` tras cada lote de
predicciones (o semanal); el join con etiquetas reales (~30 días de rezago) alimenta
`performance.py`, el vigilante que dispara ANTES que el PSI de features.

## 5. Qué NO valida este plan (límites declarados)

- No valida la política de promesa contra **costos comerciales reales** (R-15): requiere
  datos de negocio de Olist (tasa de conversión vs. longitud de promesa).
- No valida generalización fuera del período de datos (Kaggle 2016-2018): en producción
  real, los primeros 2 ciclos de etiquetas diferidas son la validación definitiva.
- La demo usa lookups agregados (D-39); con catálogos por ID la precisión de las features
  derivadas mejora sin cambiar el protocolo.
