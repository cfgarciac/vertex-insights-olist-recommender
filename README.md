# Vertex Insights — Olist Recommender

> Item-to-item hybrid recommendation system on the Brazilian E-commerce Public Dataset by Olist.  
> Sistema de recomendación item-to-item sobre el dataset público de e-commerce brasileño de Olist.  
> Proyecto Final de la carrera Data Science de Henry — equipo **Vertex Insights**.

## Equipo

| Integrante | Rol |
|---|---|
| Tutalcha Pame, Harrison Alberto | Product Owner |
| García Cadena, Cristian Fernando | Scrum Master |
| Wessin, Nassim | Machine Learning Engineer |
| Aguilar Lomas, Oscar Amaury | Data Scientist |
| López Solórzano, Juan Carlos | Data Analyst |

Contacto del equipo: `equipo.vertexinsight@gmail.com`

## Enfoque del sistema

Sistema híbrido item-to-item que combina:

- **Content-based filtering**: recomendaciones basadas en atributos del producto.
- **Item-based collaborative filtering**: recomendaciones basadas en patrones de co-compra.
- **Popularity baseline**: línea base de productos más vendidos para comparación.

### KPIs

| Tipo | Métrica | Sigla |
|---|---|---|
| Principal | Click-Through Rate | CTR |
| Secundario | Average Order Value | AOV |

## Dataset

Brazilian E-commerce Public Dataset by Olist (Kaggle):  
https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce

> Los archivos CSV del dataset no se versionan en este repositorio (ver `.gitignore`). Cada integrante los descarga localmente en `data/raw/`.

## Estructura del repositorio

vertex-insights-olist-recommender/
├── .github/workflows/      Workflows de CI futuros
├── artifacts/              Modelos serializados (salidas)
├── data/
│   ├── raw/                Datos originales (no versionados)
│   └── processed/          Datos transformados (no versionados)
├── docs/                   Documentación del proyecto
├── notebooks/              Notebooks exploratorios y de modelado
├── reports/                Informes y dashboards
├── src/                    Código fuente del proyecto
├── tests/                  Pruebas unitarias
├── .gitignore
├── Dockerfile              Placeholder, se completa en Etapa 7
├── README.md
├── requirements.txt        Dependencias de producción
└── requirements-dev.txt    Dependencias de desarrollo

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

El producto de P1 (promesa inteligente + escudo de riesgo, D-38/D-39) se sirve
con FastAPI y se visualiza con Streamlit. Contrato en
[docs/contrato_api.md](docs/contrato_api.md); arquitectura en
[docs/arquitectura_despliegue.md](docs/arquitectura_despliegue.md).

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

> Política P90 y umbrales del escudo **provisionales** (artefacto D-38),
> pendientes de confirmación del PO — Fase 0 del roadmap de despliegue.

## Estado del proyecto

Versión actual: **V1.0.0** — Estructura inicial del repositorio.

Hoja de ruta por etapas (alto nivel):

| Etapa | Foco |
|---|---|
| 1 | Setup del repositorio e identidad del equipo |
| 2 | Entendimiento del negocio y análisis exploratorio (EDA) |
| 3 | Feature engineering |
| 4 | Modelado del sistema de recomendación |
| 5 | Evaluación |
| 6 | Dashboard de resultados |
| 7 | Despliegue (API + Docker) |
| 8 | Documentación técnica y manual de usuario |
| 9 | Entrega final |

## Convenciones de trabajo

Las convenciones de commits, ramas y pull requests del equipo se documentan en `docs/convenciones.md` *(pendiente — sub-paso 2.5 de la Etapa 1)*.

## Más información

Documentación detallada y técnica en la carpeta `docs/`.