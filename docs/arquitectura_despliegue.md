# Arquitectura de despliegue MLOps — Producto P1 (promesa inteligente + escudo de riesgo)

> **Autor:** Nassim (MLE) · **Fecha:** 2026-07-05 · **Estado:** propuesta para aprobación del equipo
> **Ámbito:** Etapas 6 (cierre) → 7 (despliegue, `V1.6.0`) → 8 (monitoreo y calidad, `V1.7.0`)
> **Responde a:** propuesta de 3 etapas del SM (1º drift, 2º dashboard, 3º API+Docker) y su guía de proyectos ML (`archivos_compartido_por_cristian/guia_proyectos_ml (1).md`, Fases 6–8)
> **Decisión asociada:** D-39 en [bitacora_decisiones.md](bitacora_decisiones.md)

---

## 0. Resumen ejecutivo

El producto a desplegar ya existe y está serializado: `artifacts/producto_promesa_riesgo.joblib` (D-38) — **motor** de promesa (RandomForest de `dias_entrega_real` + márgenes residuales P80/P90/P95, política recomendada P90) + **escudo** de riesgo calibrado (v1 contra la promesa vigente, v2 contra la promesa nueva P90).

La propuesta del SM acierta en las herramientas (KS/PSI/Chi², dashboard unificado) pero se corrige en dos puntos:

1. **El orden**: no drift → dashboard → API, sino **contrato+API → Docker → dashboard → monitoreo**, con el *baseline* de drift adelantándose en paralelo. Es el orden de su propia guía (Fase 6 → 7 → 8), del backlog (HU-13/14/15 prioridad Alta antes que HU-16 prioridad Media) y de las dependencias técnicas (el monitoreo vigila requests que loguea la API; el dashboard exige conexión con la API).
2. **"Selección de variables" → contrato del request**: el modelo está entrenado y sus features de entrada son fijas; lo que se diseña con rigor es qué envía el cliente (~7 campos) y qué deriva el servidor (lookups horneados).

---

## 1. Evaluación de la propuesta del SM

### 1.1 Lo acertado

| Punto | Evaluación |
|---|---|
| KS + PSI + Chi² | **Correcto y completo por tipo de variable**: KS para numéricas continuas, Chi² para categóricas, PSI transversal con umbrales estándar (<0.10 ok / 0.10–0.25 moderado / >0.25 severo). Coincide con la Fase 7 de su guía y con HU-16. Se adopta tal cual. |
| Dashboard predicción + drift + métricas | **Correcto**: HU-16 pide literalmente el drift como pestaña del dashboard; la visión unificada se comparte. |
| Énfasis en monitoreo | **Vale doble aquí**: el riesgo #1 documentado del modelo es R-14 (drift de régimen temporal; el motor llega con bias medio en test de **+3.17 días** — el presente es más rápido que el train — absorbido por los márgenes calculados en validación). |
| Rigor con las variables de la API | **La intuición es correcta** (el cliente no puede enviar `dist_haversine_km` ni `tasa_vendedor`); la conclusión se re-encuadra (ver 1.2.2). |

### 1.2 Lo que se corrige

#### 1.2.1 El orden de las etapas

La secuencia propuesta (1º drift, 2º dashboard, 3º API+Docker) contradice tres fuentes, dos de ellas del propio SM:

- **Su guía**: Fase 6 = Despliegue (API + dashboard + Docker) → Fase 7 = Monitoreo → Fase 8 = Calidad.
- **El backlog** ([product_backlog.md](product_backlog.md)): HU-13 (API), HU-14 (Docker) y HU-15 (dashboard) son Etapa 7, prioridad **Alta**, tag `V1.6.0`; HU-16 (monitoreo) es Etapa 8, prioridad **Media**, `V1.7.0`.
- **Las dependencias técnicas**: el monitoreo de producción vigila **requests servidos** — sin API solo puede comparar CSVs estáticos y habrá que reescribirlo cuando exista el esquema real de logs (se construye dos veces). HU-15 tiene como criterio de aceptación "conexión funcional con la API REST". El contrato Pydantic de la API es el artefacto integrador: define el esquema que consumen el logger, el monitoreo y el dashboard.
- **Riesgo R-02** ([registro_riesgos.md](registro_riesgos.md)): marca el monitoreo como el componente **simplificable** si el tiempo aprieta. La propuesta original pone lo sacrificable primero; si el sprint se acorta, quedaríamos sin API ni Docker pero con un detector de drift sin nada que vigilar.

**Concesión justa al SM:** el **baseline de drift** (`monitoring/drift_baseline.json`) solo depende del dataset de entrenamiento y SÍ puede construirse en paralelo desde el primer día (ver Fase 1 del roadmap).

#### 1.2.2 "Selección de variables" → contrato del request

La propuesta dice: *"evaluación y selección de posibles variables (no necesariamente todas con las que fue entrenado)"*. Esto confunde dos actividades:

- **Feature selection** es una decisión de modelado (Etapas 4–5, cerradas). El motor es un Pipeline sklearn entrenado con el bloque **`M0_base_sin_rolling` = 15 features** (verificado en el artefacto: `motor_feature_set`) y el escudo un XGBoost con **16 features [t0]** (11 numéricas + 5 categóricas). Un `ColumnTransformer` serializado **falla en `predict()` si falta una sola columna**. Servir con un subconjunto = **reentrenar** = reabrir la Etapa 5 e invalidar las métricas reportadas y los márgenes calibrados en validación.
- Lo que SÍ se define con rigor en la Etapa 7 es el **contrato del request** — la separación cliente/servidor:

| Origen | Campos |
|---|---|
| **[CLI] envía el cliente (~7 campos)** | `precio_total`, `flete_total`, `n_items`, `customer_state`, `product_id`(s), `seller_id`, `timestamp` de compra (+ `dias_prometidos` vigente **solo** si se consume el escudo v1) |
| **[SRV] deriva el servidor — aritmética** | `ratio_flete` = flete/precio · `mismo_estado` = (customer_state == seller_state) |
| **[SRV] — calendario** | `mes_compra`, `dia_semana_compra` (del timestamp) |
| **[SRV] — catálogo de producto** | `peso_total_g`, `volumen_total_cm3`, `categoria_principal`, `seller_state` |
| **[SRV] — tabla geo** | `dist_haversine_km` |
| **[SRV] — stats de vendedor point-in-time** | `tasa_vendedor`, `sin_historial_vendedor` |

La API expone ~7 campos hacia afuera y reconstruye las 15–16 hacia adentro. La intuición del SM se satisface **sin tocar el modelo**, mediante la capa de derivación. Los tres lookups (catálogo, geo, stats de vendedor) **no existen hoy** — son el trabajo real de la Etapa 7. Como los datos son históricos (Kaggle, sin tráfico real), se **hornean como tablas estáticas** congeladas a la fecha de corte del train (disciplina point-in-time, sin fuga — coherente con D-05/D-08).

> Nota que simplifica el serving: el artefacto quedó con `M0_base_sin_rolling` (`fallback_sin_rolling: true` en las métricas) → **no se necesitan los agregados rolling 30d** de vendedor; el "feature store" se reduce a las stats estáticas (`tasa_vendedor` + flag).

#### 1.2.3 Piezas ausentes en la propuesta

1. **Prerrequisito de Etapa 6**: congelar con el PO el umbral del escudo y la política de promesa antes de servir (D-28/D-31/D-36 difieren esa decisión explícitamente). Servir un umbral no aprobado invalidaría la demo.
2. **Logging de requests/predicciones**: el puente API → monitoreo; sin él no hay datos que monitorear.
3. **Ground truth diferido**: `dias_entrega_real` se conoce ~30 días después de la compra → el monitoreo debe incluir el join posterior con etiquetas (cumplimiento realizado y residuo real−predicho: el vigilante real de R-14, que dispara **antes** que el PSI de las features).
4. **Estrategia de artefactos en Docker**: los `.joblib` están gitignored → el build debe copiar el artefacto explícitamente (y documentar la regeneración con `python -m src.models.producto_promesa_riesgo` como respaldo).
5. **Dependencias de serving**: FastAPI/uvicorn/pydantic/streamlit están solo en `requirements-dev.txt` → promover a `requirements.txt` con pins compatibles con el pickle.
6. **Tests y CI** (Fase 8 de la guía): tests de la API y del monitoreo + GitHub Actions.
7. Nomenclatura: mejor `src/monitoring/` (convención de paquetes del repo: `src/features/`, `src/models/`) que `model_monitoring.py` suelto — funcionalmente equivalente; se fija en planning.

---

## 2. Arquitectura de producción

### 2.1 Diagrama

```
CLIENTE (checkout / operaciones Olist)
  │  POST /promise  ·  POST /predict/delivery-risk
  │  JSON [CLI]: precio_total, flete_total, n_items, customer_state,
  │              product_id, seller_id, timestamp, [dias_prometidos]
  ▼
┌────────────────── Imagen Docker (python slim + libgomp1) ──────────────────┐
│  FastAPI  src/api/main.py                                                  │
│   ├─ startup (lifespan): carga ÚNICA de producto_promesa_riesgo.joblib     │
│   ├─ src/api/schemas.py (Pydantic → 422) · 503 artefacto ausente · 500     │
│   ├─ src/serving/feature_builder.py  (capa de derivación)                  │
│   │     ├─ aritmética: ratio_flete, mismo_estado                           │
│   │     ├─ calendario: mes_compra, dia_semana_compra                       │
│   │     └─ LOOKUPS ESTÁTICOS horneados → artifacts/serving/                │
│   │        catalogo_productos.parquet · catalogo_vendedores.parquet ·      │
│   │        geo_distancias.parquet · stats_vendedor.parquet (point-in-time) │
│   ├─ Motor RF → pred_dias → promesa = ceil(pred + margen_P90)              │
│   ├─ Escudo v2 (riesgo vs promesa P90) · [v1 opcional vs promesa vigente]  │
│   └─ Logger → logs/predictions.jsonl (1 JSON por request)                  │
└─────────────────────────────────────────────────────────────────────────────┘
        ▲ HTTP                                  │ JSONL (puente API → monitoreo)
        │                                       ▼
  Streamlit src/dashboard/app.py         Monitoreo src/monitoring/
   1. Alertas de riesgo (vía API)         ├─ baseline.py → monitoring/drift_baseline.json
   2. Promesa por ruta/región (N/NE)      ├─ drift.py → PSI + KS + Chi² + score drift
   3. Métricas del modelo (reports/)      ├─ performance.py → cumplimiento realizado
   4. Drift (lee drift_report.json)       │    (etiquetas diferidas ~30d; residuo R-14)
                                          └─ simulate_production.py → replay del test
                                               por la API + drift inducido (validación)
```

### 2.2 Componentes

**A. Capa de artefactos (`artifacts/`)**
- `producto_promesa_riesgo.joblib` (~13 MB, gitignored). Claves relevantes para serving (verificadas): `motor` (Pipeline RF), `motor_features` (15), `motor_feature_set` = `M0_base_sin_rolling`, `margenes_val` = {P80: 2.06d, P90: 5.84d, P95: 9.67d}, `politica_recomendada` = P90, `escudo` (bundle regresión+isotónico, umbral 0.0721 @ `recall_obj_70`), `escudo_v2_modelo` (umbral 0.3658).
- **Nuevo — `artifacts/serving/*.parquet`**: los lookups horneados offline por `src/serving/build_lookups.py` desde la data histórica, congelados a la fecha de corte del train. Como `.gitignore` excluye `*.parquet`, la fuente de verdad reproducible es el script, no los archivos.
- `/health` expone la versión/metadatos del artefacto (campo `generado`) para trazabilidad.

**B. Capa de derivación (`src/serving/feature_builder.py`)**
- Función pura: request [CLI] validado → DataFrame de una fila con **exactamente** las columnas de `motor_features` y del escudo, **leídas del propio joblib** (nunca hardcodeadas).
- **Política de faltantes documentada y flaggeada**: `product_id` desconocido → medianas globales de peso/volumen + categoría "desconocida"; `seller_id` desconocido → `sin_historial_vendedor=1` + `tasa_vendedor` = prior global; par de estados sin distancia → mediana de distancia del estado del cliente. Todo con flag de imputación en la respuesta y en el log (insumo del monitoreo de calidad de datos).

**C. API FastAPI (`src/api/`) — HU-13**
- `GET /health` → `{status, model_version, motor_feature_set, politica, umbrales}`; 503 si el artefacto no cargó.
- `POST /promise` → `{pred_dias, promesa_dias (P90), margenes}`.
- `POST /predict/delivery-risk` → `{p_tarde, bandera_riesgo, umbral, escudo}` (v2 por defecto; v1 opcional si el request trae `dias_prometidos` — decisión abierta #2).
- Pydantic 422 automático; `HTTPException` 503/500; Swagger en `/docs`; **carga única** en startup.
- **Logger**: middleware que anexa a `logs/predictions.jsonl` → `{request_id, ts, payload_cli, features_derivadas, flags_imputacion, pred_dias, promesa_dias, p_tarde, bandera, model_version, latency_ms}`. JSONL y no SQLite: append-only, cero dependencias, `pandas.read_json(lines=True)`.

**D. Docker — HU-14**
- Base slim + **`libgomp1`** (crítica: sin ella XGBoost construye pero falla en runtime — advertencia explícita de la guía).
- Orden de capas: `COPY requirements.txt` → `pip install --no-cache-dir` → `COPY src/ artifacts/` → `CMD uvicorn src.api.main:app --host 0.0.0.0 --port 8000`.
- `.dockerignore`: venv, data, notebooks, reports, docs, .git, tests.
- **Acoplamiento del unpickle (verificado en el código)**: el escudo se construyó con `src.features.build_dataset.build_preprocessor` → `joblib.load` necesita `src/` importable en el contenedor → COPY de `src/` completo + **smoke test**: `docker run <img> python -c "import joblib; joblib.load('artifacts/producto_promesa_riesgo.joblib')"` + `curl /health`.
- **Pins de versiones**: `requirements.txt` debe fijar las versiones exactas del venv de entrenamiento (sklearn/xgboost/joblib) y la imagen la misma versión de Python — un unpickle con versiones distintas puede fallar o degradar silenciosamente.

**E. Dashboard Streamlit (`src/dashboard/app.py`) — HU-15**
- **Modo híbrido (recomendado)**: las pestañas de *predicción* consumen la **API por HTTP** (cumple el criterio "conexión funcional con la API REST" y valida el contrato end-to-end; leer el artefacto directo duplicaría `feature_builder` y los dos caminos divergirían). Las pestañas *analíticas* leen archivos con `st.cache_data` (`reports/producto_promesa_riesgo_metrics.json`, `reports/predicciones_promesa_riesgo.csv`, `monitoring/drift_report.json`).
- Pestañas: (1) simulador de alertas de riesgo, (2) promesa por ruta/región con foco N/NE, (3) métricas del modelo (P90: 96.70% cumplimiento con promesa media 17.87d vs actual 94.32% con 19.12d), (4) drift (se añade en Etapa 8).
- `st.cache_resource` para el cliente HTTP; URL de la API por variable de entorno (default `http://localhost:8000`).

**F. Monitoreo (`src/monitoring/`) — HU-16, Etapa 8**
- `baseline.py`: desde el train computa bins+frecuencias (PSI), muestras/cuantiles (KS), tablas de frecuencia (Chi²) **y** la distribución baseline de los scores (`pred_dias`, `p_tarde`) → `monitoring/drift_baseline.json`. *Única pieza paralelizable desde la Fase 1.*
- `drift.py`: lee `logs/predictions.jsonl` → PSI por feature (0.10/0.25), KS numéricas, Chi² categóricas, **score drift** (PSI sobre la distribución de predicciones) → `monitoring/drift_report.json` con severidad y acción.
- `performance.py` — **el vigilante de R-14**: con etiquetas diferidas (~30d) calcula cumplimiento realizado vs 96.70% esperado, MAE del motor en producción y el **residuo (real − predicho)**: el motor tiene bias test +3.17d absorbido por los márgenes; si ese bias se reduce o invierte, el margen P90 queda descalibrado **antes** de que el PSI de las features lo delate.
- `simulate_production.py`: sin tráfico real (datos Kaggle), se **rejuega el split de test contra la API** ("producción simulada", genera logs por el camino completo) y se **induce drift artificial** (precios ×1.5, redistribución de estados hacia N/NE, desplazamiento de meses) para demostrar que el detector dispara — criterio de aceptación de HU-16.
- `docs/estrategia_monitoreo.md`: tabla severidad → acción (PSI<0.10 nada; 0.10–0.25 investigar; >0.25 o caída de cumplimiento → recalibrar márgenes / reentrenar; concept drift confirmado → reentrenamiento obligatorio, por guía).
- **Escalación R-14 (runbook)**: 1º **recalibrar márgenes** con datos recientes (barato, no reabre el modelado); 2º reentrenar con re-ventaneo (según decisión R-14 pendiente de Etapa 6). Disparadores propuestos: PSI > 0.25 en ≥2 features clave, o cumplimiento < 95% en ventana de 30 días.

**G. Tests y CI — Etapa 8**
- `tests/test_api.py` (TestClient: /health 200, /promise happy path, 422 payload inválido, 503 sin artefacto), `tests/test_feature_builder.py` (**test de contrato**: columnas == listas del joblib; defaults de faltantes), `tests/test_monitoring.py` (PSI sintético: idénticas ≈ 0, desplazadas > 0.25; drift inducido detectado).
- `.github/workflows/ci.yml`: lint + pytest. **Fixture sintético** en `tests/conftest.py` (mismo esquema de dict, modelos diminutos) porque los `.joblib` no se versionan — así CI valida el contrato de verdad.

---

## 3. Roadmap (dependencias → roles → HU/tag → criterio de salida)

| # | Fase | Rol | HU/Tag | Criterio de salida |
|---|---|---|---|---|
| 0 | **Cierre Etapa 6 (BLOQUEANTE)**: calibración formal; umbral + política congelados con el PO; postura R-14 (re-ventaneo sí/no); `justificacion_modelo.md`; `plan_validacion.md` | DS + PO | HU-12 / V1.5.0 | decisiones en bitácora; artefacto re-serializado si cambió |
| 1 | **Contrato + derivación**: `docs/contrato_api.md`; `build_lookups.py` → `artifacts/serving/`; `feature_builder.py` + test de contrato. **En paralelo: baseline de drift** (concesión al SM) | MLE + DS | base HU-13 | columnas == listas del joblib; faltantes flaggeados |
| 2 | **API FastAPI** + logger JSONL; deps promovidas con pins | MLE | HU-13 | /health /promise /predict/delivery-risk; 422/503; Swagger; carga única |
| 3 | **Docker**: slim + libgomp1 + capas + `.dockerignore` + COPY artifacts + smoke test unpickle | MLE | HU-14 / V1.6.0 | build + run local OK; README |
| 4 | **Dashboard** (híbrido, consume API) | DA/MLE | HU-15 | 4 pestañas; conexión API; cache; E2E |
| 5 | **Monitoreo**: drift.py, performance.py (etiquetas diferidas), simulate_production.py (replay + drift inducido), pestaña drift, `estrategia_monitoreo.md` | MLE + DS | HU-16 / V1.7.0 | detector validado con drift inducido; acciones por severidad |
| 6 | **Tests + CI**: test_api, test_monitoring, fixture sintético, GitHub Actions | equipo | Fase 8 guía | pytest + lint en cada PR |

**Cadena de dependencias:** 0 → 1 → 2 → {3, 4} → 5 → 6, con el baseline (1) paralelo desde el inicio.

**Mínimo viable si R-02 se materializa** (lo simplificable es el monitoreo, no lo primero): Fases 0–3 completas sirviendo solo escudo v2; dashboard de 2 pestañas (simulador + métricas); monitoreo reducido a PSI sobre 5 features clave + score drift + drift inducido; CI solo pytest.

---

## 4. Decisiones abiertas (deciden PO/equipo; recomendación incluida)

| # | Decisión | Recomendación | Decide |
|---|---|---|---|
| 1 | ¿Dashboard consume la API o el artefacto directo? | **Híbrido**: predicción vía API (cumple HU-15, valida el contrato E2E); analítica leyendo reports/ | equipo |
| 2 | ¿Servir escudo v1, v2 o ambos? | **v2 como principal** (defiende la promesa P90 que emite el producto: captura 47.6% de los incumplimientos residuales alertando 34.7% del split); v1 opcional en transición cuando el request traiga `dias_prometidos` | **PO** (fija el contrato) |
| 3 | ¿Feature store estático o dinámico? | **Tablas estáticas horneadas** a fecha de corte (datos Kaggle, sin tráfico real). Confirmado: el artefacto usa `M0_base_sin_rolling` → sin rolling 30d, el serving se simplifica | equipo |
| 4 | ¿Demostrar el drift inducido EN VIVO en la presentación final? | **Sí** — convierte HU-16 en el momento más vistoso de la demo | equipo |
| 5 | Política de reentrenamiento simulada | Aprobar disparadores: PSI > 0.25 en ≥2 features clave o cumplimiento < 95% en 30d; runbook: 1º recalibrar márgenes, 2º reentrenar con re-ventaneo | PO + DS |

---

## 5. Referencias

- Guía del SM: `archivos_compartido_por_cristian/guia_proyectos_ml (1).md` — Fase 6 (API/dashboard/Docker), Fase 7 (PSI/KS/Chi², baseline, acciones por severidad, ground truth diferido), Fase 8 (pytest, CI).
- Backlog: [product_backlog.md](product_backlog.md) — HU-12 (evaluación final), HU-13 (API), HU-14 (Docker), HU-15 (dashboard), HU-16 (monitoreo).
- Riesgos: [registro_riesgos.md](registro_riesgos.md) — R-14 (drift de régimen, Activo), R-02 (tiempo vs alcance), R-04 (curva FastAPI/Docker/Streamlit).
- Decisiones: [bitacora_decisiones.md](bitacora_decisiones.md) — D-28/D-31/D-36 (umbral/política diferidos al PO), D-38 (producto conjunto), **D-39 (esta arquitectura)**.
- Métricas citadas: `reports/producto_promesa_riesgo_metrics.json` (generado 2026-07-05; P90 test: cumplimiento 96.70%, promesa media 17.87d vs actual 94.32%/19.12d; bias motor test +3.17d; sinergia escudo v2: 47.6%/34.7%).
