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