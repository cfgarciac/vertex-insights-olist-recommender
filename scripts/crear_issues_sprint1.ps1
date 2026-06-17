# crear_issues_sprint1.ps1
# =========================================================================
# Carga las 10 historias del Sprint 1 (HU-02 a HU-11) como issues en GitHub
# vía gh CLI.
#
# Requisitos previos:
#   - gh CLI instalado y autenticado (verificar con: gh auth status)
#   - Repo default configurado (gh repo set-default cfgarciac/vertex-insights-olist-recommender)
#   - Labels del proyecto creados previamente (story, etapa-1..9, sm, ds, da, mle, po)
#   - Workflow "Auto-add to project" activado en el Project (los issues
#     aparecerán automáticamente en el tablero al crearse)
#
# Uso:
#   .\crear_issues_sprint1.ps1
#
# Si PowerShell bloquea ejecución de scripts, ejecutar primero:
#   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
# =========================================================================

Write-Host "Creando 10 issues del Sprint 1..." -ForegroundColor Cyan
Write-Host ""

# ----- HU-02 -----------------------------------------------------------------
$body02 = @"
## Historia de usuario

**Como** equipo,
**quiero** tener el repositorio en GitHub con la estructura completa de carpetas, ramas y convenciones definidas,
**para** trabajar de forma colaborativa y trazable desde el primer día.

## Criterios de aceptación

- Repositorio creado con las siete ramas largas (master, developer, Cristian, Harrison, Juan, Amaury, Nassim).
- Estructura inicial de carpetas creada y pusheada.
- Primer commit y tag V1.0.0 registrados en master.
- Cinco integrantes con acceso de colaborador (pendiente al cierre de la etapa).
- Documento de convenciones del equipo agregado al README o a docs/convenciones.md.

## Metadatos

- **Estimación:** M
- **Prioridad:** Alta
- **Etapa asociada:** 1
"@

gh issue create --title "[HU-02] Configurar el repositorio y la infraestructura del proyecto" --body $body02 --label "story,etapa-1,sm"
Write-Host "HU-02 creada." -ForegroundColor Green
Write-Host ""

# ----- HU-03 -----------------------------------------------------------------
$body03 = @"
## Historia de usuario

**Como** Scrum Master,
**quiero** tener un tablero de trabajo en GitHub Projects con las historias de usuario del sprint y sus tareas asociadas,
**para** mantener la visibilidad del estado del proyecto en todo momento.

## Criterios de aceptación

- GitHub Project creado y vinculado al repositorio.
- Cinco estados de Status configurados (Backlog, Ready, In progress, In review, Done).
- Campo personalizado de Estimación configurado (S, M, L).
- Etiquetas (labels) del proyecto creadas en el repositorio (etapas, roles, tipos).
- Plantilla de issue para historias de usuario configurada.
- Historias del Sprint 1 cargadas como issues.

## Metadatos

- **Estimación:** S
- **Prioridad:** Alta
- **Etapa asociada:** 1
"@

gh issue create --title "[HU-03] Configurar el tablero de trabajo en GitHub Projects" --body $body03 --label "story,etapa-1,sm"
Write-Host "HU-03 creada." -ForegroundColor Green
Write-Host ""

# ----- HU-04 -----------------------------------------------------------------
$body04 = @"
## Historia de usuario

**Como** Data Scientist,
**quiero** entender el problema de negocio y los datos disponibles en Olist,
**para** definir el enfoque del sistema de recomendación.

## Criterios de aceptación

- Mapeo de cada KPI de negocio a una métrica técnica equivalente.
- Identificación de las variables clave del dataset relevantes para el caso de uso.
- Hipótesis iniciales de modelado documentadas.

## Metadatos

- **Estimación:** S
- **Prioridad:** Alta
- **Etapa asociada:** 2
"@

gh issue create --title "[HU-04] Entender el problema y los datos disponibles" --body $body04 --label "story,etapa-2,ds"
Write-Host "HU-04 creada." -ForegroundColor Green
Write-Host ""

# ----- HU-05 -----------------------------------------------------------------
$body05 = @"
## Historia de usuario

**Como** Data Analyst,
**quiero** realizar un análisis exploratorio profundo de las nueve tablas de Olist,
**para** identificar problemas de calidad, distribuciones, sesgos y oportunidades de feature engineering.

## Criterios de aceptación

- Inspección inicial de las nueve tablas completada.
- Análisis univariable, bivariable, multivariable y temporal de variables clave.
- Análisis específico de sparsity de la matriz cliente-producto.
- Problemas de calidad identificados y documentados.
- Documento eda_hallazgos.md consolidado.

## Metadatos

- **Estimación:** L
- **Prioridad:** Alta
- **Etapa asociada:** 2
"@

gh issue create --title "[HU-05] Realizar el análisis exploratorio de datos sobre Olist" --body $body05 --label "story,etapa-2,da"
Write-Host "HU-05 creada." -ForegroundColor Green
Write-Host ""

# ----- HU-06 -----------------------------------------------------------------
$body06 = @"
## Historia de usuario

**Como** Data Analyst,
**quiero** construir un informe en Power BI con las visualizaciones clave del comportamiento del marketplace,
**para** sustentar la narrativa de negocio del proyecto ante los stakeholders.

## Criterios de aceptación

- Informe Power BI con al menos cuatro vistas clave (comportamiento por categoría, geografía, temporal, reseñas).
- Archivo del informe versionado en reports/.
- Validación del informe por parte del Product Owner.

## Metadatos

- **Estimación:** M
- **Prioridad:** Media
- **Etapa asociada:** 2
"@

gh issue create --title "[HU-06] Producir el informe exploratorio en Power BI" --body $body06 --label "story,etapa-2,da"
Write-Host "HU-06 creada." -ForegroundColor Green
Write-Host ""

# ----- HU-07 -----------------------------------------------------------------
$body07 = @"
## Historia de usuario

**Como** Data Scientist,
**quiero** construir los pipelines reproducibles de limpieza, integración y feature engineering,
**para** garantizar que las mismas transformaciones se apliquen consistentemente en entrenamiento e inferencia.

## Criterios de aceptación

- Integración de las nueve tablas en el dataset analítico.
- Tratamiento de nulos, outliers y categorías ausentes según estrategia documentada.
- Pipelines encapsulados con Pipeline y ColumnTransformer de scikit-learn.
- Matriz de co-ocurrencia producto-producto construida.
- Vectores de características de producto construidos.
- Split temporal del dataset realizado sin leakage.
- Pipeline serializado en artifacts/.

## Metadatos

- **Estimación:** L
- **Prioridad:** Alta
- **Etapa asociada:** 3
"@

gh issue create --title "[HU-07] Preparar los datos y construir los pipelines de feature engineering" --body $body07 --label "story,etapa-3,ds"
Write-Host "HU-07 creada." -ForegroundColor Green
Write-Host ""

# ----- HU-08 -----------------------------------------------------------------
$body08 = @"
## Historia de usuario

**Como** Data Scientist,
**quiero** implementar el baseline obligatorio de ranking por popularidad por categoría,
**para** disponer de un punto de comparación sólido para los modelos posteriores.

## Criterios de aceptación

- Función baseline implementada en src/train.py.
- Métricas preliminares (Precision@K, Recall@K) calculadas sobre el split de validación.
- Documentación del baseline en el documento de decisiones de modelado.

## Metadatos

- **Estimación:** S
- **Prioridad:** Alta
- **Etapa asociada:** 4
"@

gh issue create --title "[HU-08] Implementar el baseline de popularidad" --body $body08 --label "story,etapa-4,ds"
Write-Host "HU-08 creada." -ForegroundColor Green
Write-Host ""

# ----- HU-09 -----------------------------------------------------------------
$body09 = @"
## Historia de usuario

**Como** Data Scientist,
**quiero** implementar el modelo de recomendación de productos similares basado en contenido,
**para** habilitar la sugerencia de productos parecidos al que el cliente está visualizando.

## Criterios de aceptación

- Modelo content-based implementado y serializado.
- Capaz de devolver los K productos más similares a un product_id dado.
- Métricas preliminares calculadas y comparadas con el baseline.
- Sanity check manual con al menos diez productos de muestra validados por el Product Owner.

## Metadatos

- **Estimación:** M
- **Prioridad:** Alta
- **Etapa asociada:** 4
"@

gh issue create --title "[HU-09] Implementar el canal de productos similares (content-based)" --body $body09 --label "story,etapa-4,ds"
Write-Host "HU-09 creada." -ForegroundColor Green
Write-Host ""

# ----- HU-10 -----------------------------------------------------------------
$body10 = @"
## Historia de usuario

**Como** Data Scientist,
**quiero** implementar el modelo de recomendación de productos frecuentemente comprados juntos basado en co-ocurrencias,
**para** habilitar el cross-selling en el contexto del carrito.

## Criterios de aceptación

- Modelo item-based collaborative filtering implementado y serializado.
- Capaz de devolver los K productos más comprados junto a un product_id dado.
- Métricas preliminares calculadas y comparadas con el baseline.
- Sanity check manual con al menos diez productos de muestra validados por el Product Owner.

## Metadatos

- **Estimación:** M
- **Prioridad:** Alta
- **Etapa asociada:** 4
"@

gh issue create --title "[HU-10] Implementar el canal de productos comprados juntos (collaborative)" --body $body10 --label "story,etapa-4,ds"
Write-Host "HU-10 creada." -ForegroundColor Green
Write-Host ""

# ----- HU-11 -----------------------------------------------------------------
$body11 = @"
## Historia de usuario

**Como** Scrum Master,
**quiero** ejecutar la Sprint Review y la Sprint Retrospective del Sprint 1,
**para** validar entregables, capturar aprendizajes y preparar el Sprint 2.

## Criterios de aceptación

- Sprint Review realizada con presentación del MVP.
- Acta de Sprint Review documentada en docs/sprints/.
- Sprint Retrospective realizada con formato acordado.
- Acta de Sprint Retrospective documentada con acciones de mejora asignadas a responsables.
- Tag V1.4.0 creado en master.
- Backlog del Sprint 2 priorizado.

## Metadatos

- **Estimación:** M
- **Prioridad:** Alta
- **Etapa asociada:** 5
"@

gh issue create --title "[HU-11] Ejecutar el cierre formal del Sprint 1" --body $body11 --label "story,etapa-5,sm"
Write-Host "HU-11 creada." -ForegroundColor Green
Write-Host ""

# ----- Cierre ----------------------------------------------------------------
Write-Host "=========================================================" -ForegroundColor Cyan
Write-Host "10 issues del Sprint 1 cargados exitosamente." -ForegroundColor Cyan
Write-Host "Siguiente: ajustar Status y Estimación en el Project por interfaz." -ForegroundColor Cyan
Write-Host "=========================================================" -ForegroundColor Cyan
