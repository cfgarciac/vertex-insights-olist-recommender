# Informe técnico — Producto P1: Promesa inteligente + Escudo de riesgo

> **Vertex Insights · Proyecto Final Henry · 2026-07-05.** Consolidado técnico del
> proyecto: cada sección enlaza la evidencia primaria (reports/, docs/, bitácora) en
> lugar de duplicarla. Público: evaluadores técnicos.

## 1. Problema y encuadre de negocio

- **Encargo original:** recomendador item-to-item. **Descubrimiento (Sprint 1):**
  techo estructural — 97% de compradores únicos, 3.3% de co-compra, sin datos de
  clics (CTR no medible) → pivote formal (D-16..D-21) a **P1: predicción de entrega
  tardía** con KPIs medibles (tasa de entrega a tiempo, GMV expuesto).
- **Dolor cuantificado:** 8.1% de entregas tarde; insatisfacción 5.8× mayor al
  llegar tarde; GMV expuesto R$1.16M por tardanza (tablero: R$3.80M = 28% sumando
  P1+P2+P3). Brecha regional Norte/Nordeste vs SP ≈ 2.3×.
- Evidencia: `archivos compartidos por harrison/Problem_Discovery_DVA_Report_v0.4.md`,
  deck de cierre del Sprint 1, tablero Power BI.

## 2. Datos y feature engineering (Etapa 3)

- **Fuente:** Brazilian E-commerce Public Dataset (Olist, Kaggle), 9 tablas.
- **Tabla analítica:** 96.470 órdenes entregadas con etiqueta; **16 features [t0]**
  (solo información disponible al momento de la compra — regla anti-fuga D-22, con
  verificación automática `assert_no_forbidden_features` y auditoría R-12).
- **Familias de señales:** geografía (distancia haversine, estados), paquete
  (peso/volumen/precio/flete), vendedor (tasa histórica point-in-time, cold-start
  flaggeado), tiempo (mes, día de semana).
- **Split temporal 70/15/15** (D-23): train → 2018-04-15, val → 2018-06-21,
  test → 2018-08-29. Sin barajado: simula predecir el futuro.
- Detalle: `docs/etapas/cierre-etapa-3.md`, `src/features/build_dataset.py`.

## 3. Modelado

### 3.1 Escudo de riesgo (Fase 1, Etapa 4 + reentrenamiento D-31)
Clasificación de `entrega_tarde` explorada con baselines, Logística y XGBoost
(D-27); el modelo final es una **regresión XGBoost de `dias_vs_promesa` +
calibración isotónica** (D-31) — mejor PR-AUC/ROC-AUC/Brier que los clasificadores
directos. Test: **ROC-AUC 0.742 · PR-AUC 0.132 (tasa base 6.6%) · Brier 0.063**.

### 3.2 Motor de promesa (Fase 2, D-33..D-36)
Regresión de `dias_entrega_real` (baselines → Lineal → **Random Forest** ganador →
HGB), 15 features [t0] (el motor NO usa la promesa vigente). Márgenes residuales
P80/P90/P95 calculados **solo en validación**; promesa = `max(ceil(pred+margen),1)`.
Test: MAE 4.62 d; sobre-predicción media +3.17 d (régimen R-14, absorbido por márgenes).

### 3.3 El producto conjunto (D-38)
"**La regresión fija la promesa; el clasificador la defiende.**" Hallazgo clave: el
escudo v1 (calibrado a la promesa vigente) **no transfiere** a la promesa nueva →
**escudo v2** reentrenado contra `promesa_P90` (mismas 16 features): captura 47.6%
de los incumplimientos alertando 34.7% (lift 1.4×). Política **P90 ratificada
(D-41)**: 96.70% de cumplimiento con promesa media 17.87 d vs 94.32% / 19.12 d de
la actual — domina en ambas dimensiones.

- Justificación completa: [justificacion_modelo.md](justificacion_modelo.md)
- Protocolo de validación: [plan_validacion.md](plan_validacion.md)
- Evidencia: `reports/producto_promesa_riesgo.md` + `_metrics.json`

## 4. Arquitectura de despliegue (D-39)

Orden corregido respecto a la propuesta inicial: **contrato+API → Docker →
dashboard → monitoreo** (el monitoreo consume los logs de la API). El cliente envía
**~7 campos** y el servidor deriva el resto (aritmética, calendario, lookups
estáticos point-in-time del train: catálogo por categoría, geo por par de estados,
stats de vendedor por estado — degradación controlada; toda imputación flaggeada).

- **API** (`src/api/`): `/health`, `/promise`, `/predict/delivery-risk`; Pydantic
  (422), 503 sin artefactos, carga única con candado anti-divergencia
  contrato↔modelo; log JSONL por request. Contrato: [contrato_api.md](contrato_api.md).
- **Docker:** python:3.11-slim + libgomp1 + **pins exactos** del venv (el unpickle
  con versiones distintas puede degradar silenciosamente); COPY de `src/` completo
  (el pickle referencia `src.features`); healthcheck nativo.
- **Dashboard** (`src/dashboard/`): 5 pestañas, modo híbrido (predicción vía API —
  valida el contrato E2E; analítica desde reports/). Scoring por lote CSV.
- Documento completo: [arquitectura_despliegue.md](arquitectura_despliegue.md).

## 5. Validación del serving (el modelo desplegado == el evaluado)

| Control | Resultado |
|---|---|
| API == modelo directo (mismos payloads) | idénticos al decimal |
| API == evaluación offline D-38 (por order_id) | promesa/pred/p_tarde exactas (5 órdenes) |
| Replay E2E de 1.500 órdenes de test por la API | cumplimiento 96.40% vs 96.70% offline |
| Docker vs venv | respuestas idénticas |
| Latencia | p50 ≈ 32 ms |
| Suite | 67/67 tests (100% sintéticos) + CI |

## 6. Monitoreo (HU-16) y gestión de R-14

- `baseline.py` (train) → `drift.py` (PSI con umbrales 0.10/0.25 + KS numéricas +
  Chi² categóricas + score drift) → `performance.py` (etiquetas diferidas ~30 d:
  cumplimiento realizado y sobre-predicción — **vigilante R-14**, dispara antes que
  el PSI de features) → `simulate_production.py` (producción simulada + drift
  inducido).
- **Detector validado en ambos sentidos:** sin drift inducido detecta el régimen
  real R-14 sin falsas alarmas (features `derivada` excluidas del veredicto); con
  drift inducido dispara (alertas 34.8% → 66.3%).
- Runbook y severidades: [estrategia_monitoreo.md](estrategia_monitoreo.md).

## 7. Visibilidad de negocio (tablero Power BI)

Tablero de 5 páginas (`Vertex Power BI.pbix`, BI Analyst): Resumen Ejecutivo,
Drivers, Logística, Financiero-GMV. Modelo de datos de 9 tablas + 2 geo; medidas
DAX documentadas; corrección crítica de locale (price ×100). GMV total R$13.59M;
en riesgo R$3.80M (28%). Documentación completa:
`archivos_compartido_por_juancarlos/Documentacion_Dashboard_PowerBI_Vertex.md`.

## 8. Limitaciones declaradas

- **R-15:** la política de promesa óptima depende de costos comerciales que Olist
  no compartió; P90 es la dominante con la evidencia disponible.
- **R-17:** sin variables del carrier (rutas/capacidad) hay un techo estructural de
  predicción (D-32: las features [t0] derivadas no lo superan).
- **Lookups agregados** en serving (sin catálogos por ID en el repo); imputaciones
  flaggeadas y regenerables por ID con los datos crudos.
- **Datos históricos (Kaggle 2016-2018):** la validación definitiva en producción
  real son los primeros ciclos de etiquetas diferidas (plan en
  [plan_validacion.md](plan_validacion.md)).

## 9. Reproducibilidad

```bash
pip install -r requirements.txt          # pins exactos (D-39)
python -m src.features.build_dataset     # tabla analítica desde data/raw
python -m src.models.train_multimodelo   # escudo
python -m src.models.producto_promesa_riesgo  # producto conjunto + reportes
python -m src.serving.build_lookups && python -m src.monitoring.baseline
pytest tests/                            # 67/67 sin necesitar datos
```

Trazabilidad completa: bitácora **D-01..D-41** ([bitacora_decisiones.md](bitacora_decisiones.md)),
riesgos ([registro_riesgos.md](registro_riesgos.md)), cierres por etapa
(`docs/etapas/`), actas (`docs/sprints/`).
