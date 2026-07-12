# Vertex Insights — Olist: Promesa inteligente + Escudo de riesgo (P1)

> Producto de Machine Learning que **fija la promesa de entrega y la defiende**:
> un motor de regresión predice los días reales de entrega y emite una promesa
> honesta (política P90), y un clasificador calibrado marca las órdenes en riesgo
> de incumplirla. Sobre el Brazilian E-commerce Public Dataset de Olist.
> Proyecto Final de la carrera Data Science de Henry — equipo **Vertex Insights**.

**Resultado en test (evaluación única, 14.471 órdenes):** cumplimiento **96.70%**
con promesa promedio **17.87 días**, frente a **94.32% / 19.12 días** de la promesa
actual de Olist — más confiable **y** más corta. El escudo de riesgo captura el
47.6% de los incumplimientos residuales alertando solo el 34.7% de las órdenes.

> **Nota histórica:** el encargo original era un recomendador item-to-item; el
> descubrimiento del Sprint 1 (97% de compradores únicos, 3.3% de co-compra, sin
> datos de clics) llevó al **pivote formal a P1 — predicción de entrega tardía**
> (decisiones D-16..D-21 en la bitácora). Este README describe el producto vigente.

## Equipo

| Integrante | Rol (D-40) | Rama |
|---|---|---|
| Tutalcha Pame, Harrison Alberto | Analytics Lead | `Harrison` |
| García Cadena, Cristian Fernando | Data Analyst | `Cristian` |
| López Solórzano, Juan Carlos | BI Analyst | `Juan` |
| Aguilar Lomas, Oscar Amaury | Data Scientist | `Amaury` |
| Wessin, Nassim | Machine Learning Engineer | `Nassim` |

Contacto del equipo: `equipo.vertexinsight@gmail.com`

## El producto (D-38: "la regresión fija la promesa; el clasificador la defiende")

| Pieza | Modelo | Qué entrega |
|---|---|---|
| **Motor de promesa** | Random Forest (regresión de días de entrega) + márgenes residuales P80/P90/P95 calculados en validación | `promesa = max(ceil(pred + margen_P90), 1)` |
| **Escudo de riesgo** | XGBoost de `dias_vs_promesa` + calibración isotónica | P(entrega tarde) + bandera de alerta (v2 defiende la promesa nueva; v1 la vigente) |
| **Serving** | API FastAPI + Docker + dashboard Streamlit + tablero Power BI | contrato de ~7 campos; el servidor deriva el resto |
| **Monitoreo** | PSI/KS/Chi² + vigilante de performance con etiquetas diferidas | runbook R-14: recalibrar márgenes → reentrenar |

### KPIs (D-19, post-pivote)

| Tipo | Métrica |
|---|---|
| Principal | Tasa de entrega a tiempo (cumplimiento de la promesa) |
| Secundario | GMV expuesto por entregas tardías |
| De modelo | PR-AUC / ROC-AUC / Brier (escudo) · MAE y backtesting de cumplimiento (motor) |

## Dataset

Brazilian E-commerce Public Dataset by Olist (Kaggle):
https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce

> Los CSV no se versionan (ver `.gitignore`). Cada integrante los descarga en
> `data/raw/`; la tabla analítica (`orders_features.csv`) se regenera con
> `python -m src.features.build_dataset`.

## Estructura del repositorio

```
vertex-insights-olist-recommender/
├── .github/workflows/      CI (pytest + compileall en cada PR)
├── artifacts/              Modelos serializados + lookups de serving (no versionados)
├── data/processed/         Tabla analítica (no versionada)
├── docs/                   Backlog, bitácora (D-01..D-41), riesgos, arquitectura,
│                           contrato de la API, estrategia de monitoreo, cierres de etapa
├── logs/                   predictions.jsonl (no versionado; puente API→monitoreo)
├── monitoring/             drift_report.json · performance_report.json
├── reports/                Informes y figuras por etapa
├── src/
│   ├── features/           ETL y feature engineering ([t0], anti-fuga)
│   ├── models/             Entrenamiento, evaluación y producto conjunto
│   ├── serving/            Lookups + feature_builder (contrato de la API)
│   ├── api/                FastAPI: /health · /promise · /predict/delivery-risk
│   ├── dashboard/          Streamlit (5 pestañas, incl. scoring por CSV)
│   └── monitoring/         baseline · drift · performance · simulate_production
├── tests/                  67 tests (100% sintéticos: corren sin datos)
├── Dockerfile              python:3.11-slim + libgomp1 + pins (HU-14)
└── requirements.txt        Pins exactos del venv de entrenamiento (D-39)
```

## Instalación local

### Windows (PowerShell)

```powershell
git clone https://github.com/cfgarciac/vertex-insights-olist-recommender.git
cd vertex-insights-olist-recommender
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements-dev.txt
```

### Linux / macOS

```bash
git clone https://github.com/cfgarciac/vertex-insights-olist-recommender.git
cd vertex-insights-olist-recommender
python -m venv venv
source venv/bin/activate
pip install -r requirements-dev.txt
```

## Despliegue del producto P1 (API + Dashboard + Docker)

El producto se sirve con FastAPI y se visualiza con Streamlit. Contrato en
[docs/contrato_api.md](docs/contrato_api.md); arquitectura en
[docs/arquitectura_despliegue.md](docs/arquitectura_despliegue.md); guía de uso en
[docs/manual_usuario.md](docs/manual_usuario.md).

### Prerrequisitos (una sola vez)

Los artefactos no se versionan; hay que generarlos localmente:

```bash
python -m src.features.build_dataset               # requiere data/raw (o pedir orders_features.csv al equipo)
python -m src.models.train_multimodelo             # entrena el escudo (modelo_riesgo_p1.joblib)
python -m src.models.producto_promesa_riesgo       # une motor + escudo (producto_promesa_riesgo.joblib)
python -m src.serving.build_lookups                # hornea artifacts/serving/ (lookups del contrato)
python -m src.monitoring.baseline                  # baseline de drift (monitoring/)
```

### API (HU-13)

```bash
venv/Scripts/uvicorn src.api.main:app --reload     # Windows (Linux: uvicorn src.api.main:app)
# Swagger interactivo: http://localhost:8000/docs
curl http://localhost:8000/health
```

### Dashboard (HU-15) — necesita la API viva para la pestaña de alertas

```bash
venv/Scripts/streamlit run src/dashboard/app.py    # http://localhost:8501
```

### Docker (HU-14)

```bash
docker build -t vertex-olist-api .
docker run --rm -p 8000:8000 vertex-olist-api
# smoke test del unpickle dentro del contenedor:
docker run --rm vertex-olist-api python -c "import joblib; joblib.load('artifacts/producto_promesa_riesgo.joblib'); print('OK')"
```

### Monitoreo (HU-16) — ver [docs/estrategia_monitoreo.md](docs/estrategia_monitoreo.md)

```bash
python -m src.monitoring.simulate_production       # producción simulada (replay del test)
python -m src.monitoring.drift                     # PSI/KS/Chi² → monitoring/drift_report.json
python -m src.monitoring.performance               # etiquetas diferidas (vigilante R-14)
python -m src.monitoring.simulate_production --drift todo   # demo: el detector dispara
```

> Política **P90** y umbrales del escudo (v2 = 0.3658 principal, v1 = 0.0721 en
> transición) **ratificados en D-41**; `/health` los expone para trazabilidad.

## Estado del proyecto

**Sprint 2 entregado** (cierre documental 2026-07-05): evaluación final ratificada
(D-41), despliegue completo (API + Docker + dashboard + monitoreo), documentación
final y suite 67/67 con CI. Detalle en
[docs/etapas/cierre-sprint-2.md](docs/etapas/cierre-sprint-2.md).

| Etapa | Foco | Estado |
|---|---|---|
| 0–1 | Propuesta, setup e identidad del equipo | ✅ V1.0.x |
| 2 | Entendimiento del negocio, EDA y **pivote a P1** | ✅ V1.1.0 |
| 3 | Feature engineering ([t0], anti-fuga, split temporal) | ✅ V1.2.0 |
| 4 | Modelado P1 (baseline + clasificadores + regresión calibrada) | ✅ V1.3.x |
| 5 | Cierre Sprint 1 (review + retrospective) | ✅ V1.4.0* |
| 6 | Evaluación final y selección (justificación + plan de validación) | ✅ V1.5.0* |
| 7 | Despliegue: API + Docker + dashboard | ✅ V1.6.0* |
| 8 | Monitoreo + documentación técnica | ✅ V1.7.0* |
| 9 | Entrega final (presentación al comité) | 🔶 V1.8.0* pendiente de fecha |

\* Tags a crear en `master` tras el merge del PR #28 (`Nassim → developer → master`);
ver los actos formales pendientes en `docs/etapas/cierre-sprint-2.md`.

## Convenciones de trabajo

Commits (Conventional Commits en español), ramas por integrante, flujo de PRs a
`developer` y esquema de tags `V<sprint>.<etapa>.<patch>`:
[docs/convenciones.md](docs/convenciones.md).

## Más información

- **Manual de usuario** (API, dashboard, tablero Power BI): [docs/manual_usuario.md](docs/manual_usuario.md)
- **Informe técnico** (problema → datos → modelos → despliegue): [docs/informe_tecnico.md](docs/informe_tecnico.md)
- **Bitácora de decisiones** (D-01..D-41): [docs/bitacora_decisiones.md](docs/bitacora_decisiones.md)
- **Registro de riesgos**: [docs/registro_riesgos.md](docs/registro_riesgos.md)
