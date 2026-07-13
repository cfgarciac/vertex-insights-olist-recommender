# Contribuciones del equipo Vertex Insights

> Registro público de roles, responsabilidades y entregables del proyecto
> **Olist: Promesa inteligente + Escudo de riesgo (P1)**.
> Última actualización: 2026-07-12.

## Propósito

Este documento complementa el historial de Git para facilitar la lectura del
trabajo colaborativo por parte de mentores, evaluadores y reclutadores. No
reemplaza los commits, pull requests ni documentos de decisión: los conecta con
el rol funcional de cada integrante.

La atribución se apoya en cuatro fuentes públicas del repositorio:

1. Los roles vigentes definidos en la decisión D-40 de
   [`docs/bitacora_decisiones.md`](docs/bitacora_decisiones.md).
2. El mapa de entregables y expositores del
   [cierre del Sprint 2](docs/etapas/cierre-sprint-2.md).
3. La autoría conservada en los commits de Git.
4. Los archivos técnicos, analíticos y documentales integrados en `master`.

Los entregables son resultado del equipo. Indicar que una persona lideró un
bloque no implica propiedad exclusiva sobre todos sus archivos: hubo revisión,
integración y apoyo cruzado entre roles.

## Equipo y áreas de contribución

| Integrante | Rol vigente (D-40) | Rama personal | Área principal documentada |
|---|---|---|---|
| Tutalcha Pame, Harrison Alberto | Analytics Lead | [`Harrison`](https://github.com/cfgarciac/vertex-insights-olist-recommender/tree/Harrison) | Descubrimiento del problema, estrategia analítica y Fase 2 de promesa inteligente |
| García Cadena, Cristian Fernando | Data Analyst | [`Cristian`](https://github.com/cfgarciac/vertex-insights-olist-recommender/tree/Cristian) | Estructura del proyecto, gobierno documental y comunicación del análisis |
| López Solórzano, Juan Carlos | BI Analyst | [`Juan`](https://github.com/cfgarciac/vertex-insights-olist-recommender/tree/Juan) | EDA de P1, visualización y tablero de inteligencia de negocio |
| Aguilar Lomas, Oscar Amaury | Data Scientist | [`Amaury`](https://github.com/cfgarciac/vertex-insights-olist-recommender/tree/Amaury) | ETL, feature engineering y validación de señales del modelo |
| Wessin, Nassim | Machine Learning Engineer | [`Nassim`](https://github.com/cfgarciac/vertex-insights-olist-recommender/tree/Nassim) | Modelado, producto integrado, API, dashboard, monitoreo y CI |

## Tutalcha Pame, Harrison Alberto — Analytics Lead

Lideró el encuadre analítico que conectó el dolor de negocio con una solución
medible: desde la evaluación de la hipótesis inicial de recomendación hasta el
pivote a desempeño de entrega y la evolución desde clasificación de riesgo a
regresión de duración real.

Contribuciones principales:

- Reconciliación entre la narrativa de descubrimiento y el modelo construido
  por el equipo.
- Cierre del veredicto de viabilidad de P1 y formalización del Project Charter.
- Diseño de la Fase 2 sobre `dias_entrega_real`, con disciplina anti-leakage y
  partición temporal.
- EDA específico de regresión y documentación de señales geográficas,
  temporales, físicas y de vendedor.
- Implementación de features históricas *point-in-time* y ventanas rolling.
- ETL, entrenamiento y evaluación comparativa de modelos de regresión.
- Backtesting de políticas de promesa P80/P90/P95 y recomendación de P90.
- Experimento de clustering como alternativa evaluada y no incorporada al MVP.
- Cierre técnico y narrativo del MVP de Fase 2.
- Liderazgo del bloque de presentación "La promesa inteligente".

Evidencia destacada:

- [Historial de commits de `hatlpm` integrado en `master`](https://github.com/cfgarciac/vertex-insights-olist-recommender/commits/master/?author=hatlpm)
- [Project Charter de P1](docs/project_charter_p1.md)
- [Diseño de regresión de Fase 2](docs/fase2_diseno_regresion_dias_entrega_real.md)
- [Plan de implementación de Fase 2](docs/fase2_plan_implementacion.md)
- [EDA de regresión](reports/fase2_eda_regresion.md)
- [Rolling features](src/features/rolling_fase2.py)
- [ETL de regresión](src/features/build_dataset_fase2_regresion.py)
- [Entrenamiento de regresión](src/models/train_fase2_regresion.py)
- [Backtesting de promesas](src/models/backtest_promesas_fase2.py)
- [Experimento de clustering](experiments/fase2_clustering_experimento.md)
- [Cierre del MVP](reports/fase2_cierre_mvp.md)

Los 11 commits de esta línea de trabajo conservaron su autoría al integrarse
primero en `developer` y después en `master` mediante el
[PR #30](https://github.com/cfgarciac/vertex-insights-olist-recommender/pull/30).
El orden visual de un merge puede cambiar, pero no modifica el autor original
registrado por Git.

## García Cadena, Cristian Fernando — Data Analyst

Contribuyó a establecer la base organizativa y documental que hizo auditable el
proyecto, y a comunicar el contexto, el pivote y la evolución del trabajo.

Contribuciones principales:

- Estructura inicial del repositorio y convenciones de colaboración.
- Plantillas de issues y soporte al seguimiento de historias de usuario.
- Incorporación de la bitácora de decisiones, el registro de riesgos y el
  backlog del producto.
- Documentación formal de las primeras etapas.
- Comunicación del bloque final de proyecto, objetivos y planificación.

Evidencia destacada:

- [Convenciones del equipo](docs/convenciones.md)
- [Product Backlog](docs/product_backlog.md)
- [Registro de riesgos](docs/registro_riesgos.md)
- [Bitácora de decisiones](docs/bitacora_decisiones.md)

## López Solórzano, Juan Carlos — BI Analyst

Desarrolló análisis exploratorio y visualizaciones que conectaron los datos de
Olist con el problema de entrega, y lideró la capa de visibilidad del negocio.

Contribuciones principales:

- EDA enfocado de P1 y documentación de hallazgos regionales y operativos.
- Figuras analíticas para comunicar el comportamiento de la entrega.
- Actualización de decisiones, riesgos e historias tras el pivote a P1.
- Diseño y presentación del tablero Power BI de cinco páginas documentado en el
  cierre del Sprint 2.

Evidencia destacada:

- [Notebook de EDA](notebooks/02_EDA_VERTEX.ipynb)
- [Figuras de la Etapa 2](reports/figures_eda_etapa2)
- [Cierre de la Etapa 2](docs/etapas/cierre-etapa-2.md)
- [Mapa de expositores y tablero](docs/etapas/cierre-sprint-2.md)

## Aguilar Lomas, Oscar Amaury — Data Scientist

Lideró componentes de preparación de datos y feature engineering, y participó
en la validación técnica de las señales usadas por los modelos.

Contribuciones principales:

- ETL y feature engineering de P1.
- Incorporación de features continuas y binarias.
- Validación de granularidad, target y variables disponibles en el momento de
  la compra.
- Comunicación de la materia prima, la disciplina anti-leakage y las familias
  de señales del producto.
- Revisión e integración final de `developer` en `master` mediante el PR #30.

Evidencia destacada:

- [ETL y feature engineering](notebooks/03_ETL_FE_VERTEX.ipynb)
- [Constructor del dataset](src/features/build_dataset.py)
- [Decisiones de feature engineering](docs/decisiones_fe.md)
- [Cierre de la Etapa 3](docs/etapas/cierre-etapa-3.md)

## Wessin, Nassim — Machine Learning Engineer

Lideró la conversión de los análisis y modelos en un producto integrado,
ejecutable y monitoreable.

Contribuciones principales:

- Baselines, clasificación de riesgo y reentrenamiento multimodelo.
- Unión del motor de promesa con el escudo de riesgo.
- API FastAPI, contrato de entrada y construcción de features para serving.
- Docker, dashboard Streamlit y scoring por CSV.
- Monitoreo de drift y desempeño con etiquetas diferidas.
- Pruebas sintéticas, CI y documentación de despliegue.
- Integración técnica y cierre formal de las Etapas 5 a 9.

Evidencia destacada:

- [Producto promesa + riesgo](src/models/producto_promesa_riesgo.py)
- [API](src/api/main.py)
- [Dashboard](src/dashboard/app.py)
- [Serving](src/serving)
- [Monitoreo](src/monitoring)
- [Arquitectura de despliegue](docs/arquitectura_despliegue.md)
- [Cierre del Sprint 2](docs/etapas/cierre-sprint-2.md)

## Cómo leer la autoría en GitHub

- `master` es la rama pública y oficial del proyecto.
- `developer` conserva la historia consolidada antes de cada entrega.
- Las ramas personales documentan el origen y la evolución del trabajo.
- Los commits se atribuyen por sus metadatos de autor, aunque entren a través de
  una rama de integración o un pull request abierto por otra persona.
- La cantidad de commits o líneas modificadas no se usa como única medida de
  impacto: también cuentan las decisiones, revisiones, análisis, integración y
  comunicación del producto.

Para una vista técnica completa, consulte el
[`README.md`](README.md), la
[`docs/bitacora_decisiones.md`](docs/bitacora_decisiones.md) y el
[`docs/etapas/cierre-sprint-2.md`](docs/etapas/cierre-sprint-2.md).
