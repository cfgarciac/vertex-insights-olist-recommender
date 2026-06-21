# Bitácora de Decisiones — Proyecto Final

## Registro de decisiones técnicas y de negocio

> Documento que registra las decisiones importantes tomadas durante el
> desarrollo del Proyecto Final. Sigue un formato inspirado en los
> Architecture Decision Records (ADR), simplificado para el contexto
> académico. Es responsabilidad compartida del equipo mantener este
> registro actualizado cada vez que se toma una decisión relevante.

---

## Formato de cada decisión

Cada decisión se documenta con:

- **Identificador:** D-NN secuencial.
- **Título:** descripción corta de la decisión.
- **Fecha:** cuándo se tomó.
- **Estado:** Propuesta, Aceptada, Reemplazada, Deprecada.
- **Contexto:** la situación que motivó la decisión.
- **Decisión:** qué se decidió.
- **Alternativas consideradas:** qué otras opciones se evaluaron.
- **Consecuencias:** implicaciones positivas y negativas.
- **Responsable:** quién tomó o lideró la decisión.

---

## Plantilla para nuevas decisiones

```markdown
### D-NN — [Título corto de la decisión]

**Fecha:** [YYYY-MM-DD]
**Estado:** [Propuesta / Aceptada / Reemplazada / Deprecada]
**Responsable:** [Rol o nombre]

**Contexto:**
[Descripción de la situación que motiva la decisión.]

**Decisión:**
[Qué se decidió, en términos claros.]

**Alternativas consideradas:**
- [Alternativa 1] — [breve razón por la que no se eligió]
- [Alternativa 2] — [breve razón por la que no se eligió]

**Consecuencias:**
- Positivas: [lista]
- Negativas o trade-offs: [lista]

**Etapa asociada:** [Número de etapa o "transversal"]
```

---

## Decisiones registradas

### D-01 — Selección del dataset Olist

**Fecha:** Pre-PF
**Estado:** Aceptada
**Responsable:** Equipo (consenso)

**Contexto:**
El equipo necesitaba elegir un dataset que cumpliera los criterios de
los lineamientos del Proyecto Final: pertenecer a la industria de
comercio y consumo, permitir modelar interacción entre usuarios y
productos, y habilitar el cálculo de métricas como Precision@K y
Recall@K. Inicialmente se consideró el dataset Rossmann Store Sales,
pero se descartó por ser un problema de forecasting de ventas
agregadas que no permite modelar interacción usuario-producto.

**Decisión:**
Se adopta el **Brazilian E-commerce Public Dataset by Olist** (Kaggle)
como dataset principal del proyecto.

**Alternativas consideradas:**
- Rossmann Store Sales — descartado por incompatibilidad estructural
  con el problema requerido.
- Online Retail II (UCI) — opción viable pero con menor riqueza de
  variables auxiliares y sin ratings explícitos.
- H&M Personalized Fashion Recommendations — descartado por su
  volumen (31 millones de transacciones) excesivo para tres sprints.
- RetailRocket — descartado por anonimización extrema de items que
  limita interpretabilidad de negocio.

**Consecuencias:**
- Positivas:
  - Estructura nativa usuario-item-interacción.
  - Disponibilidad de ratings explícitos vía reseñas.
  - Riqueza de variables auxiliares (geografía, categorías, vendedores).
  - Tamaño manejable para tres sprints.
- Negativas o trade-offs:
  - Alta sparsity de la matriz cliente-producto (la mayoría de
    clientes hace una sola compra).
  - Reseñas en portugués (requiere traducción o manejo especial si se
    incorpora NLP).

**Etapa asociada:** 0

---

### D-02 — Tipo de sistema de recomendación

**Fecha:** Pre-PF
**Estado:** Reemplazada por D-16 (pivote del objetivo a P1)
**Responsable:** Data Scientist + Product Owner

> **Nota (2026-06-18):** Reemplazada por el pivote a P1 (D-16). El recomendador item-to-item deja de ser la solución del proyecto y queda como la hipótesis del cliente investigada (viable pero limitada).

**Contexto:**
Definida la elección de Olist, se hace evidente que la alta sparsity
de la matriz cliente-producto hace inviable un sistema de
recomendación user-to-item tradicional. El equipo necesita definir
qué tipo específico de sistema de recomendación construir.

**Decisión:**
Se adopta un **sistema híbrido item-to-item con dos canales
complementarios**: productos similares (content-based filtering) y
productos comprados juntos (item-based collaborative filtering).

**Alternativas consideradas:**
- User-to-item collaborative filtering — descartado por la sparsity
  de la matriz cliente-producto.
- Recomendador basado solo en contenido — descartado por aprovechar
  pobremente la información de co-ocurrencias entre productos.
- Recomendador basado solo en colaborativo — descartado por no
  resolver bien el cold-start de productos nuevos.
- Recomendador basado en sesión — descartado por requerir datos de
  navegación que Olist no provee.

**Consecuencias:**
- Positivas:
  - Aprovecha tanto la información de catálogo como las
    co-ocurrencias.
  - Mapea a casos de uso reales del e-commerce (PDP y carrito).
  - Permite comparación rica entre enfoques en la evaluación.
- Negativas o trade-offs:
  - Mayor complejidad de implementación al manejar dos canales.
  - Necesita doble esfuerzo de evaluación.

**Etapa asociada:** 0

---

### D-03 — Indicadores clave de desempeño del proyecto

**Fecha:** Pre-PF
**Estado:** Reemplazada por D-19 (redefinición de KPIs por el pivote a P1)
**Responsable:** Product Owner

> **Nota (2026-06-20):** CTR no es medible en Olist (sin datos de navegación) y AOV pierde sentido como KPI del nuevo objetivo. Reemplazada por D-19.

**Contexto:**
La consigna del PF requiere definir KPIs de negocio asociados al
sistema de recomendación. Es necesario separar conceptualmente los
KPIs de negocio (los que se medirían en producción) de las métricas
técnicas (las que se calculan offline durante la evaluación).

**Decisión:**
Se adoptan dos KPIs de negocio:
- KPI principal: **Click-Through Rate (CTR)** sobre los productos
  recomendados.
- KPI secundario: **Ticket promedio por orden (Average Order Value,
  AOV)** en las órdenes que incluyeron al menos un producto
  recomendado.

Las métricas técnicas de evaluación offline son: Precision@K,
Recall@K, MAP@K, cobertura del catálogo y diversidad.

**Alternativas consideradas:**
- Tasa de conversión asistida como KPI principal — descartada por
  ser más difícil de definir operacionalmente en Olist.
- Retención del cliente — descartada por requerir periodo de
  observación largo, no medible en el alcance del proyecto.

**Consecuencias:**
- Positivas:
  - KPIs universales del e-commerce, fáciles de comunicar a
    stakeholders.
  - Separación clara entre lo que se reportaría en producción y lo
    que se evalúa offline.
- Negativas o trade-offs:
  - CTR no se puede medir directamente con datos históricos de Olist
    (no hay logs de clicks). Se evalúa mediante aproximaciones offline.

**Etapa asociada:** 0

---

### D-04 — Composición de roles del equipo

**Fecha:** Pre-PF
**Estado:** Aceptada
**Responsable:** Equipo (consenso)

**Contexto:**
La plantilla oficial del PF de Henry sugiere una composición de
cuatro integrantes (1 Product Owner, 2 Data Scientists, 1 Scrum
Master). El equipo está conformado por cinco personas. Es necesario
definir el quinto rol y la distribución de responsabilidades de
manera coherente con un equipo de Machine Learning moderno.

**Decisión:**
Se adopta una composición de cinco roles: **Product Owner, Scrum
Master, Data Analyst, Data Scientist, Machine Learning Engineer**.
Esta composición refleja un equipo de ML real moderno con
especialización clara: el Data Analyst lidera el entendimiento de
datos y EDA, el Data Scientist lidera el modelado, y el ML Engineer
lidera el despliegue y monitoreo.

**Alternativas consideradas:**
- Mantener dos Data Scientists y agregar un quinto Product Owner —
  descartado por crear redundancia en el liderazgo.
- Reemplazar Data Analyst por Data Engineer — opción válida con
  diferencias menores; se prefirió Data Analyst por el peso del EDA
  en Power BI en el proyecto.

**Consecuencias:**
- Positivas:
  - Refleja un equipo de ML real con responsabilidades claras.
  - Cada rol tiene una etapa de carga alta diferenciada.
  - Facilita el aprendizaje individual de cada miembro en su área.
- Negativas o trade-offs:
  - Requiere validar con el mentor que la plantilla acepta cinco
    roles.

**Etapa asociada:** Transversal

---

### D-05 — Stack tecnológico principal

**Fecha:** Pre-PF
**Estado:** Aceptada
**Responsable:** ML Engineer + Data Scientist

**Contexto:**
El equipo necesita definir las tecnologías principales que se
utilizarán durante el proyecto, considerando la disponibilidad de
habilidades en el equipo, la robustez de las herramientas y la
compatibilidad entre los componentes.

**Decisión:**
Se adoptan las siguientes tecnologías como stack principal:

- **Lenguaje:** Python 3.10+
- **Manipulación de datos:** pandas, numpy
- **Modelado:** scikit-learn
- **API:** FastAPI
- **Validación de datos en API:** Pydantic
- **Contenedorización:** Docker
- **Dashboard:** Streamlit
- **Visualización exploratoria:** Power BI (informe del Sprint 1) y
  Matplotlib/Seaborn (notebooks).
- **Serialización de modelos:** joblib
- **Notebooks:** Jupyter

**Alternativas consideradas:**
- Flask en lugar de FastAPI — descartado por menor adopción moderna
  y por no tener validación nativa con Pydantic.
- Dash o Plotly Dash en lugar de Streamlit — descartado por curva de
  aprendizaje mayor.
- Tableau en lugar de Power BI — descartado porque el lineamiento de
  Henry sugiere Power BI explícitamente.

**Consecuencias:**
- Positivas:
  - Stack ampliamente documentado y soportado.
  - Compatibilidad total entre componentes.
  - Skills relativamente comunes en perfiles de Data Science.
- Negativas o trade-offs:
  - Streamlit tiene limitaciones para dashboards muy complejos; será
    suficiente para el alcance del proyecto.

**Etapa asociada:** Transversal

---

### D-06 — Estructura del repositorio y estrategia de ramas

**Fecha:** Cierre Etapa 0 / Inicio Etapa 1
**Estado:** Aceptada
**Responsable:** ML Engineer + Scrum Master

**Contexto:**
El equipo necesita una estrategia de ramas que (i) cumpla con la
recomendación del tutor de hacer visible la colaboración múltiple de
los cinco integrantes, (ii) garantice revisión por pares antes de la
integración, y (iii) mantenga master estable y trazable para la
evaluación.

**Decisión:**
Se adopta un modelo híbrido de **siete ramas** que combina visibilidad
individual con integración controlada:

- `master`: rama de producción, recibe únicamente versiones cerradas
  al cierre de cada etapa. Es la rama de referencia para el comité
  evaluador.
- `developer`: rama de integración común. Todas las ramas personales
  confluyen aquí vía pull request con revisión por pares.
- `Cristian`, `Harrison`, `Juan`, `Amaury`, `Nassim`: cinco ramas
  personales largas, una por integrante. Cada persona hace commits
  diarios directamente en su rama. Cuando termina un entregable,
  abre PR hacia developer.

**Flujo de promoción:** rama personal → developer (vía PR + revisión
por pares) → master (al cierre de cada etapa, con tag de versión).

**Alternativas consideradas:**
- Modelo de tres ramas (master/certification/developer) sin ramas
  personales — descartado por recomendación del tutor, que solicitó
  visibilidad explícita del aporte individual.
- Modelo de cinco ramas personales sin rama de integración —
  descartado por no garantizar un punto único de integración limpio
  ni preservar master estable.
- GitFlow completo (release, hotfix, etc.) — descartado por exceso de
  complejidad para un proyecto de tres semanas.
- Trunk-based development — descartado por no garantizar revisión por
  pares explícita.

**Consecuencias:**
- Positivas:
  - Visibilidad individual del aporte de cada integrante, alineada
    con la recomendación del tutor.
  - Master estable y profesional como referencia para el comité
    evaluador.
  - Revisión por pares obligatoria mediante el flujo de pull
    requests hacia developer.
  - Trazabilidad clara entre el trabajo individual y la integración.
- Negativas o trade-offs:
  - Mayor cantidad de pull requests por sprint comparado con un
    modelo de una sola rama.
  - Necesidad de sincronización frecuente entre las ramas personales
    y developer para evitar drift (riesgo R-09 en el Registro).

**Convenciones operativas asociadas:**
- Cada integrante hace pull de developer hacia su rama personal al
  inicio de cada jornada de trabajo.
- Los pull requests deben ser pequeños y frecuentes; no acumular
  trabajo de varios días.
- El nombre del pull request debe incluir el identificador de la
  historia de usuario (HU-NN).
- La promoción developer → master la ejecuta el ML Engineer en
  presencia del Scrum Master al cierre de cada etapa.

**Etapa asociada:** Transversal

---

### D-07 — Esquema de versionado semántico

**Fecha:** Pre-PF
**Estado:** Aceptada
**Responsable:** ML Engineer

**Contexto:**
El equipo necesita una convención de versionado clara que permita
identificar el estado del proyecto en cada momento y facilite la
trazabilidad entre etapas y entregables.

**Decisión:**
Se adopta **versionado semántico (SemVer)** con el patrón
`MAJOR.MINOR.PATCH`. El proyecto inicia en `V1.0.0` al cierre de la
Etapa 1 y avanza incrementalmente con cada etapa:

- Etapa 1: V1.0.0
- Etapa 2: V1.1.0
- Etapa 3: V1.2.0
- Etapa 4: V1.3.0
- Etapa 5: V1.4.0
- Etapa 6: V1.5.0
- Etapa 7: V1.6.0
- Etapa 8: V1.7.0
- Etapa 9: V1.8.0

Los tags se crean siempre desde `master` después de promover el
código a través de las tres ramas.

**Alternativas consideradas:**
- Versionado por fecha (CalVer) — descartado por menor estándar en
  proyectos de ML.
- Sin versionado formal — descartado por incompatible con la
  trazabilidad requerida.

**Consecuencias:**
- Positivas:
  - Estándar conocido y compatible con prácticas de la industria.
  - Trazabilidad clara entre etapas y artefactos generados.

**Etapa asociada:** Transversal

---

### D-08 — Gestión de Sprint Backlogs en GitHub Projects

**Fecha:** Pre-PF
**Estado:** Aceptada
**Responsable:** Scrum Master

**Contexto:**
El equipo necesita una herramienta para gestionar los Sprint Backlogs
y el tablero de trabajo durante el proyecto. La opción de mantener
estos artefactos como archivos markdown fue evaluada pero descartada
por baja agilidad de actualización.

**Decisión:**
Se adopta **GitHub Projects** como herramienta única para la gestión
del tablero de trabajo y los Sprint Backlogs. Las columnas estándar
del tablero son: To Do, In Progress, In Review, Done.

**Alternativas consideradas:**
- Jira — descartado por mayor curva de aprendizaje y por estar
  desacoplado del repositorio.
- Trello — descartado por ofrecer menos integración con GitHub.
- Archivos markdown en el repositorio — descartado por baja
  agilidad y tendencia a desactualizarse.

**Consecuencias:**
- Positivas:
  - Integración nativa con issues y pull requests.
  - Trazabilidad automática entre tareas y código.
  - Sin costo adicional.
- Negativas o trade-offs:
  - Será la primera vez que el Scrum Master gestiona un proyecto en
    GitHub Projects; requiere preparación previa al inicio del
    Sprint 1.

**Etapa asociada:** 1

---

### D-09 — Estrategia de evaluación offline mediante partición temporal

**Fecha:** Pre-PF
**Estado:** Propuesta (a confirmar en Etapa 6)
**Responsable:** Data Scientist

**Contexto:**
Para evaluar los modelos de recomendación offline, es necesario
definir cómo se divide el dataset entre entrenamiento y validación,
de modo que la evaluación sea realista y libre de leakage.

**Decisión:**
Se propone aplicar **partición temporal del dataset** (time-based
split): el modelo se entrena con datos del periodo anterior y se
evalúa con datos del periodo posterior. Las fechas exactas de corte
se definirán al inicio de la Etapa 3 según los hallazgos del EDA.

**Alternativas consideradas:**
- Random split — descartado por introducir leakage temporal
  (entrenamiento ve futuro).
- Leave-one-out — descartado por costo computacional excesivo.
- Cross-validation con folds temporales — descartado por
  sobrecomplejidad para el alcance del proyecto.

**Consecuencias:**
- Positivas:
  - Realista respecto a un escenario productivo.
  - Sin leakage temporal.
- Negativas o trade-offs:
  - Una sola pasada de evaluación; menos robusto que cross-validation.
  - Decisión de fecha de corte sensible a la distribución temporal de
    los datos.

**Etapa asociada:** 3 (confirmación en Etapa 6)

---

### D-10 — Mantener documentos de gestión del proyecto fuera del repositorio público

**Fecha:** Pre-PF
**Estado:** Aceptada
**Responsable:** Product Owner

**Contexto:**
El equipo dispone de varios documentos de planificación y gestión
(guía maestra, propuesta metodológica, instrucciones de Scrum,
instrucciones de flujo, guías por etapa, contextos previos) que sirven
como referencia personal del líder del proyecto y como contexto para
chats individuales con asistentes de inteligencia artificial. Es
necesario decidir si estos documentos se versionan en el repositorio
del proyecto o se mantienen aparte.

**Decisión:**
Los documentos de planificación, gestión y orientación se mantienen
**fuera del repositorio público de GitHub**. Solo los documentos
operativos del proyecto se versionan en el repositorio:
`product_backlog.md`, `bitacora_decisiones.md`, `registro_riesgos.md`,
y las actas de Sprint Review y Retrospective.

**Alternativas consideradas:**
- Versionar todos los documentos en una carpeta `docs/` del
  repositorio — descartado para mantener limpio el repositorio
  público.

**Consecuencias:**
- Positivas:
  - Repositorio enfocado en artefactos del producto.
  - Mayor flexibilidad para actualizar guías personales.
- Negativas o trade-offs:
  - El líder del proyecto debe organizar manualmente sus documentos
    personales y cargarlos a las herramientas de soporte
    (proyecto Claude, drive personal).

**Etapa asociada:** Transversal

---

### D-11 — Identidad corporativa del equipo

**Fecha:** Etapa 0
**Estado:** Aceptada
**Responsable:** Equipo (consenso)

**Contexto:**
La consigna del Proyecto Final solicita que el equipo opere como una
consultora ficticia con identidad propia. Era necesario definir el
nombre corporativo, el correo institucional y la misión del equipo,
elementos requeridos por la plantilla oficial de la propuesta.

**Decisión:**
Se adopta la siguiente identidad corporativa:

- **Nombre de la empresa:** Vertex Insights.
- **Correo institucional:** equipo.vertexinsight@gmail.com.
- **Misión:** "Vertex Insights es una consultora de datos que
  convierte información compleja en decisiones de negocio claras.
  Combinamos rigor analítico con un enfoque pragmático para entregar
  soluciones que impacten directamente la gestión de nuestros
  clientes."

Esta identidad se utilizará en todos los entregables y comunicaciones
formales del proyecto.

**Alternativas consideradas:**
- Misión con énfasis exclusivo en el caso de uso del PF — descartada
  por restringir innecesariamente la marca a un solo proyecto.
- Correo institucional en dominio propio — descartado por costo y
  por no aportar valor adicional en el contexto académico.

**Consecuencias:**
- Positivas:
  - Identidad reutilizable en todos los entregables y presentaciones.
  - Misión suficientemente amplia para sustentar la narrativa
    profesional del equipo.
- Negativas o trade-offs:
  - El correo institucional usa Gmail (dominio público); aceptable
    para el contexto académico.
  - Inconsistencia menor entre el nombre plural ("Vertex Insights") y
    el correo singular ("vertexinsight"); se mantiene tal como quedó
    registrada la cuenta.

**Etapa asociada:** 0

---

### D-12 — Aprobación de la propuesta del Proyecto Final

**Fecha:** Etapa 0
**Estado:** Aceptada
**Responsable:** Product Owner

**Contexto:**
La Etapa 0 requiere la aprobación formal de la propuesta del Proyecto
Final por parte del mentor o comité evaluador como condición para
iniciar el Sprint 1. La propuesta consolida la identidad del equipo,
el caso de negocio, las fuentes de datos y el plan de estrategia de
análisis.

**Decisión:**
La propuesta del Proyecto Final, en su versión consolidada con
identidad del equipo Vertex Insights, caso de negocio sobre Olist,
sistema de recomendación item-to-item y plan de despliegue con
FastAPI, Streamlit y Docker, se considera aprobada y vigente. La
aprobación habilita formalmente el inicio del Sprint 1 y confirma la
validez de las decisiones D-01 a D-05 y D-11 en el ámbito del
proyecto.

**Alternativas consideradas:**
No aplica; la decisión consolida los acuerdos previos del equipo y la
validación externa del mentor.

**Consecuencias:**
- Positivas:
  - Cierre formal de la Etapa 0.
  - Habilitación del inicio del Sprint 1.
  - Confirmación del alcance técnico y de negocio.
- Negativas o trade-offs:
  - Ninguno identificado.

**Etapa asociada:** 0

---

### D-13 — Configuración del tablero GitHub Projects con plantilla enriquecida

**Fecha:** 2026-06-17
**Estado:** Aceptada
**Responsable:** Scrum Master

**Contexto:**
Al crear el GitHub Project para el Sprint 1, la plantilla Board de
GitHub entregó una configuración enriquecida con cinco estados de
Status por defecto (Backlog, Ready, In progress, In review, Done) y
un campo Estimate tipo Number. La planeación original de la guía de
Etapa 1 contemplaba solo cuatro estados (To Do, In Progress, In Review,
Done) y un campo Estimación tipo Single select con valores S, M, L.
Adicionalmente, la guía de GitHub Projects sugería duplicar atributos
como campos del Project y como labels del repositorio (etapa, rol,
tipo).

**Decisión:**
Se adoptan los cinco estados de Status que vinieron por defecto en la
plantilla, dado que representan un flujo Scrum más maduro que la
propuesta original de cuatro columnas, al separar Backlog de Ready. Se
reemplaza el campo Estimate (Number) por un campo Estimación (Single
select con valores S, M, L) para mantener consistencia con la
convención del Product Backlog.

Adicionalmente, se establece un reparto pragmático entre campos del
Project y labels del repositorio:

- En el Project viven los atributos dinámicos (Status, Estimación).
- En el repositorio viven los atributos estáticos como labels: etapas
  (`etapa-1` a `etapa-9`), roles (`po`, `sm`, `da`, `ds`, `mle`),
  tipos (`story`, `task`, `bug`, `docs`).

**Alternativas consideradas:**
- Forzar el plan original de cuatro columnas — descartado por requerir
  trabajo de modificación sin valor agregado, y por perder la
  distinción útil entre Backlog (registrada) y Ready (comprometida).
- Mantener el campo Estimate por defecto como Number — descartado por
  inconsistencia con la convención S/M/L del Product Backlog.
- Duplicar atributos como campos del Project y como labels (etapa,
  rol, tipo) — descartado por generar redundancia y doble fuente de
  verdad.

**Consecuencias:**
- Positivas:
  - Flujo Scrum más maduro y alineado con prácticas reales de la
    industria.
  - Consistencia entre la Estimación del Project y la del Backlog.
  - Atributos estáticos visibles incluso al consultar issues fuera del
    Project (vía labels).
- Negativas o trade-offs:
  - Diverge de la planeación original documentada en `etapa_1_guia.md`
    y `guia_github_projects.md`, lo cual genera una pequeña deuda
    documental.

**Etapa asociada:** 1

---

### D-14 — Visibilidad pública del repositorio y licencia MIT

**Fecha:** 2026-06-17
**Estado:** Aceptada
**Responsable:** Scrum Master

**Contexto:**
Al crear el repositorio en la Etapa 1, era necesario decidir entre
visibilidad privada (limitada al equipo y al mentor) y pública
(accesible a cualquier visitante). Adicionalmente, era necesario
decidir si incluir un archivo de licencia explícito que clarificara
las condiciones legales de uso del código.

**Decisión:**
El repositorio se crea con **visibilidad pública** y se incluye un
archivo `LICENSE` con **licencia MIT**. La visibilidad pública habilita
el uso del repositorio como pieza de portafolio para los integrantes
del equipo. La licencia MIT, permisiva y estándar en proyectos de
portafolio, clarifica legalmente el uso del código por terceros y
desbloquea la indexación del repositorio por motores de búsqueda
profesionales.

**Alternativas consideradas:**
- Repositorio privado — descartado por restringir el valor del
  proyecto como portafolio profesional.
- Repositorio público sin archivo `LICENSE` — descartado porque, sin
  licencia explícita, el código queda por defecto en "all rights
  reserved", lo cual desincentiva su uso como referencia.
- Otras licencias (Apache 2.0, GPL-3.0) — descartadas por simplicidad.
  MIT es la más usada en proyectos de portafolio y la más fácil de
  comprender por evaluadores externos.

**Consecuencias:**
- Positivas:
  - El repositorio funciona como pieza de portafolio individual y de
    equipo.
  - El badge de licencia MIT aparece automáticamente en la página
    principal del repositorio en GitHub.
  - Aumenta la trazabilidad pública del proceso del equipo.
- Negativas o trade-offs:
  - Mayor cuidado requerido para no commitear información sensible
    (mitigado vía `.gitignore` blindado desde el primer commit y vía
    el riesgo R-10 del Registro de Riesgos).

**Etapa asociada:** 1

---

### D-15 — Plantilla de issue como Issue Form estructurada en YAML

**Fecha:** 2026-06-17
**Estado:** Aceptada
**Responsable:** Scrum Master

**Contexto:**
Para garantizar consistencia en los issues abiertos durante el
proyecto, se necesitaba una plantilla de issue. GitHub permite dos
formatos: Markdown clásico con frontmatter, o YAML (Issue Forms). El
formato Markdown ofrece un editor en blanco con texto sugerido pero
sin validación. El formato YAML genera formularios interactivos con
campos obligatorios, dropdowns predefinidos y descripciones guiadas.

**Decisión:**
Se adopta el formato **YAML (Issue Forms)**, ubicado en
`.github/ISSUE_TEMPLATE/historia_usuario.yml`. La plantilla incluye
campos obligatorios para la estructura clásica de historias de usuario
(Como/Quiero/Para), los criterios de aceptación, la estimación
(S/M/L), la prioridad (Alta/Media/Baja) y la etapa asociada. La
adopción de este formato reduce la probabilidad de issues mal
estructurados.

**Alternativas consideradas:**
- Plantilla Markdown clásica con frontmatter — descartada porque
  ofrece menos validación y deja un editor en blanco propenso a
  inconsistencias entre integrantes.
- No usar plantilla y crear los issues con texto libre — descartada
  por la pérdida de consistencia entre issues creados por distintos
  integrantes.

**Consecuencias:**
- Positivas:
  - Issues creados por la interfaz quedan estructurados de forma
    uniforme.
  - Los campos obligatorios reducen la creación de issues incompletos.
  - El formato es más legible para evaluadores externos.
- Negativas o trade-offs:
  - Sintaxis YAML sensible a indentación; un error tipográfico rompe
    el formulario silenciosamente (GitHub no muestra error, simplemente
    deja de listar la plantilla).

**Etapa asociada:** 1

---

### D-16 — Pivote del objetivo: de recomendador item-to-item a predicción de entrega tardía (P1)

**Fecha:** 2026-06-18
**Estado:** Aceptada
**Responsable:** Data Analyst (lidera el descubrimiento) + Data Scientist, validado por el Product Owner

**Contexto:**
La propuesta aprobada (D-02, D-12) comprometía un recomendador item-to-item. Al investigar a fondo esa hipótesis durante el EDA de la Etapa 2, se confirmó que el dataset es estructuralmente pobre para el mundo pre-compra: co-compra escasa (3.3% de órdenes con 2+ productos), ~97% de clientes con una sola compra, y cero columnas de navegación/clicks (CTR no medible). El recomendador resultó **viable pero limitado**. En paralelo, las tablas `reviews` y `geolocation` (ricas y sin explotar) apuntaban a un dolor post-compra mayor y mejor sostenido por los datos.

**Decisión:**
El equipo pivota. Actuando como consultora que primero probó la hipótesis del cliente, ejecuta un descubrimiento estructurado del problema (D-17) y reorienta el proyecto a **P1 — Desempeño de entrega**: predecir si una orden llegará tarde respecto a la fecha prometida. item-to-item NO se borra del relato: queda como la hipótesis del cliente investigada con rigor (gancho de la narrativa de consultora).

**Alternativas consideradas:**
- Mantener el recomendador como solución final — descartado por su techo (escasez de co-compra y ausencia de señal pre-compra).
- Construir ambos (recomendador + P1) — descartado: dos problemas son dos proyectos, inviable en el plazo.

**Consecuencias:**
- Positivas:
  - Problema con *target* limpio y demostrable end-to-end; aprovecha `geolocation` y `reviews`.
  - Fuerza lecciones de *data leakage* y geoespacial; dolor real, accionable y de valor (~R$1.1M de GMV expuesto).
- Negativas o trade-offs:
  - Divergencia respecto a la propuesta aprobada (riesgo R-13).
  - Reemplaza D-02 y D-03 y obliga a redefinir el backlog del recomendador (HU-07 a HU-18).

**Etapa asociada:** 2

---

### D-17 — Metodología de descubrimiento del problema (embudo Descubrimiento–DVA)

**Fecha:** 2026-06-18
**Estado:** Aceptada
**Responsable:** Data Analyst + Data Scientist

**Contexto:**
Sin un *Subject-Matter Expert* (experto de dominio) de Olist, el equipo necesitaba un método riguroso para elegir el dolor de negocio de mayor valor que los datos sostuvieran, en lugar de asumir una solución.

**Decisión:**
Se adopta un **embudo de descubrimiento (Niveles 0–3)** que persigue en paralelo "¿qué dolor vale más?" y "¿los datos lo sostienen?". Sustituye al SME con tres fuentes: dominio público del e-commerce, lo que Olist midió (lectura del esquema como prioridades reveladas) y la voz del cliente (99k reseñas). De 12 dolores se consolidó a 5 candidatos (P1–P5) y se filtró por tres compuertas (¿duele? ¿accionable? ¿hay materia prima?). El razonamiento completo vive en el *Problem Discovery & Data Viability Report* (`docs/`).

**Alternativas consideradas:**
- Asumir el recomendador (D-02) — descartado por el pivote.
- Elegir el problema por intuición — descartado por falta de rigor y trazabilidad.

**Consecuencias:**
- Positivas:
  - Elección defendible y documentada; narrativa de consultora sólida.
- Negativas o trade-offs:
  - Trabajo de descubrimiento adicional dentro del plazo de la Etapa 2.

**Etapa asociada:** 2

---

### D-18 — Selección de P1 (entrega) sobre P2 y P3; frontera P1↔P3

**Fecha:** 2026-06-19
**Estado:** Aceptada
**Responsable:** Data Scientist + Data Analyst, validado por el Product Owner

**Contexto:**
El embudo dejó tres finalistas: P1 (entrega), P2 (satisfacción) y P3 (vendedores). P2 es el de mayor alcance (2/3 del dolor) pero su corazón es *driver analysis* (un estudio, no un modelo desplegable); P3 es accionable pero con *target* a construir y mayor riesgo; P1 es el único con *target* limpio y un artefacto que el cliente usaría.

**Decisión:**
Se elige **P1 — Desempeño de entrega**. **Frontera P1↔P3:** el vendedor NO es un problema aparte; su señal entra como *feature* de P1 (tasa histórica de despacho/entrega tardía). Un solo problema, un solo *target*.

**Alternativas consideradas:**
- P2 satisfacción — descartado como problema central por ser un estudio, no un modelo desplegable (se asume su mayor alcance como trade-off consciente).
- P3 vendedores — descartado como problema independiente por riesgo de completitud; se reubica como *feature* de P1.

**Consecuencias:**
- Positivas:
  - Completable end-to-end; valor real y regionalmente nítido (Norte/Nordeste); evita doble conteo P1/P3.
- Negativas o trade-offs:
  - Alcance acotado (~1/3 del dolor total) frente a P2.

**Etapa asociada:** 2

---

### D-19 — Redefinición de KPIs y métricas de evaluación (reemplaza D-03)

**Fecha:** 2026-06-20
**Estado:** Aceptada
**Responsable:** Product Owner + Data Scientist

**Contexto:**
Los KPIs CTR/AOV (D-03) eran del recomendador y dejan de aplicar: CTR no es medible en Olist y AOV no es el indicador del nuevo objetivo. P1 exige KPIs y métricas propias.

**Decisión:**
- **KPI de negocio principal:** tasa de entrega a tiempo (% de órdenes entregadas en o antes de la fecha prometida); su complemento es la tasa de entrega tardía (8.1% base).
- **KPI secundario / valor en riesgo:** GMV expuesto a la tardanza (~R$1.1M) y GMV no realizado de las no entregadas.
- **Métricas técnicas offline** (clasificación de `entrega_tarde`): ROC-AUC, PR-AUC, precision/recall/F1 a un umbral y calibración. Se mantiene la **partición temporal** de la evaluación (D-09).

**Alternativas consideradas:**
- Conservar CTR/AOV — descartado por inaplicables al nuevo objetivo.
- Evaluar solo con *accuracy* — descartado por el desbalance (8.1%); PR-AUC y *recall* son más informativos.

**Consecuencias:**
- Positivas:
  - KPIs medibles y alineados al dolor real; métricas adecuadas a un problema desbalanceado.
- Negativas o trade-offs:
  - Reemplaza D-03; obliga a redefinir la HU de evaluación (HU-12) y los endpoints (HU-13).

**Etapa asociada:** 2

---

### D-20 — Definición del *target* y del universo de análisis de P1

**Fecha:** 2026-06-20
**Estado:** Aceptada
**Responsable:** Data Analyst + Data Scientist

**Contexto:**
Para modelar P1 hay que fijar qué se predice y sobre qué órdenes.

**Decisión:**
- *Target* binario `entrega_tarde = (fecha de entrega real > fecha estimada)`, definido **contra la promesa** que percibe el cliente (no contra días absolutos).
- **Universo predictivo:** órdenes `delivered` (las únicas etiquetables). Las no entregadas/canceladas (2.98%) se caracterizan **aparte** como ausencia informativa (dolor de P1 puro, sin etiqueta tarde/puntual).
- Se deja como alternativa continua `dias_vs_promesa` para una posible regresión.

**Alternativas consideradas:**
- "Tarde" por días absolutos — descartado: el cliente reacciona a la promesa rota (la insatisfacción salta al cruzar el 0), no a un umbral fijo.
- Incluir las no entregadas en el *target* binario — descartado: no tienen fecha real; se tratan aparte.

**Consecuencias:**
- Positivas:
  - *Target* limpio con tasa base sana (8.1%, desbalance modelable).
- Negativas o trade-offs:
  - El universo `delivered` ciega a la insatisfacción por no-entrega (se documenta).

**Etapa asociada:** 2

---

### D-21 — Disciplina anti-leakage y *shortlist* de features [t0]

**Fecha:** 2026-06-20
**Estado:** Aceptada
**Responsable:** Data Scientist + Data Analyst

**Contexto:**
P1 se predeciría en el momento de la compra/aprobación (t0). Variables como la fecha de entrega real o la reseña solo existen después; usarlas como *feature* sería *data leakage* (fuga de datos).

**Decisión:**
Toda variable se clasifica **[t0]** (disponible al comprar → *feature* legítima) o **[POST]** (resultado → prohibida como *feature*; la fecha real solo *etiqueta*). La tasa histórica del vendedor se calcula con sus órdenes pasadas, **excluyendo la orden actual** (ventana a fijar en la Etapa 3). *Shortlist* [t0]: días prometidos, distancia *haversine*, `mismo_estado`, ratio flete/valor, peso/volumen/categoría del producto, mes/día de compra, tasa histórica de entrega tardía del vendedor. Se apoya en la partición temporal (D-09).

**Alternativas consideradas:**
- Usar todas las variables disponibles — descartado por *leakage* (infla métricas offline y no es desplegable).

**Consecuencias:**
- Positivas:
  - Modelo honesto y desplegable; lección metodológica central; insumo directo de la Etapa 3.
- Negativas o trade-offs:
  - Descarta features potentes pero ilegítimas; exige cuidado en el *split* y en la construcción de features históricas.

**Etapa asociada:** 2

---

### D-22 — Fuente del feature engineering: CSV consolidado en vez de las 9 tablas crudas

**Fecha:** 2026-06-20
**Estado:** Aceptada
**Responsable:** Data Scientist

**Contexto:**
La guía de la Etapa 3 sugería partir de las nueve tablas crudas. Para esta etapa se dispone de un CSV ya consolidado a nivel ítem (`orders_consolidated.csv`) que integra ítems, pagos, reseñas, producto y geolocalización.

**Decisión:**
Construir la tabla analítica de P1 partiendo del CSV consolidado `orders_consolidated.csv`, no de las nueve tablas crudas. El script `src/features/build_dataset.py` parte de ese archivo y produce `vertex_files/orders_p1_features.csv`.

**Alternativas consideradas:**
- Reconstruir desde las 9 tablas crudas — descartado por redundante: el consolidado ya integra las uniones validadas en el EDA y acelera la etapa (R-02).

**Consecuencias:**
- Positivas:
  - Menos código de unión, menos riesgo de *fan-out*, etapa más rápida.
- Negativas o trade-offs:
  - Se depende de la trazabilidad del consolidado; se documenta su origen para reproducibilidad.

**Etapa asociada:** 3

---

### D-23 — Granularidad a nivel orden con vendedor/producto principal = primer ítem

**Fecha:** 2026-06-20
**Estado:** Aceptada
**Responsable:** Data Scientist

**Contexto:**
El CSV viene a nivel ítem (112,650 filas; 1,275 órdenes multi-vendedor). P1 predice a nivel orden, así que hay que colapsar sin duplicar.

**Decisión:**
Una fila por `order_id`. El **vendedor/producto principal** es el del primer ítem (`order_item_id == 1`): de él salen `seller_id`, `seller_state`, geo del vendedor y `categoria_principal`. Los importes, peso y volumen se **agregan sobre todos los ítems** (`precio_total`, `flete_total`, `peso_total_g`, `volumen_total_cm3`, `n_items`).

**Alternativas consideradas:**
- Modelar a nivel ítem — descartado: el target y el dolor son de la orden completa.
- Promediar geo/categoría de todos los ítems — descartado por complejidad sin valor claro para P1 en este sprint.

**Consecuencias:**
- Positivas:
  - Tabla limpia (96,470 órdenes) consistente con el EDA; sin *fan-out*.
- Negativas o trade-offs:
  - El "principal" es una aproximación para órdenes multi-ítem/multi-vendedor; anotado para revisión futura.

**Etapa asociada:** 3

---

### D-24 — Ventana de la tasa histórica del vendedor: expanding point-in-time, mínimo 5

**Fecha:** 2026-06-20
**Estado:** Aceptada
**Responsable:** Data Scientist

**Contexto:**
La tasa histórica de tardanza del vendedor es la feature más predictiva y la más peligrosa por fuga (R-12). El EDA dejó un análisis de sensibilidad de la ventana.

**Decisión:**
Ventana **expanding y point-in-time**: para cada orden, la tasa usa solo órdenes **anteriores** del vendedor (excluye la actual). Mínimo de **5 órdenes previas**; por debajo se respalda con la **tasa global del train** (9.03%) y se marca `sin_historial_vendedor` (afecta al 11.57% de las órdenes). Se incluye una **prueba anti-fuga** automática en el script.

**Alternativas consideradas:**
- Ventana de últimas N órdenes — descartado por menor cobertura sin ganancia clara de separación en el rango explorado.
- Sin mínimo de historial — descartado: tasas inestables con 1–2 órdenes.

**Consecuencias:**
- Positivas:
  - Feature potente y legítima; respaldo explícito para vendedores nuevos.
- Negativas o trade-offs:
  - El respaldo global atenúa la señal en el 11.57% de órdenes (aceptable).

**Etapa asociada:** 3

---

### D-25 — Split temporal 70/15/15 por fecha de compra

**Fecha:** 2026-06-20
**Estado:** Aceptada
**Responsable:** Data Scientist

**Contexto:**
Un split aleatorio filtraría el futuro al pasado y contaminaría tanto la evaluación como los agregados históricos (R-12, R-14).

**Decisión:**
Corte **por fecha de compra** (no aleatorio): train = pasado, val/test = futuro, en proporción **70/15/15** (train 67,529 · val 14,470 · test 14,471). La tasa global de respaldo del vendedor y el ajuste del preprocesador se calculan **solo sobre train**. Se apoya en D-09.

**Alternativas consideradas:**
- Split aleatorio estratificado — descartado por *leakage* temporal.
- Recortar la cola de 2018 ya en esta etapa — diferido: se inspecciona (R-14) pero se conserva el periodo completo y se vigila en la Etapa 4.

**Consecuencias:**
- Positivas:
  - Evaluación honesta y desplegable; coherente con la disciplina anti-leakage.
- Negativas o trade-offs:
  - El régimen 2018 cae en test; se documenta como punto de vigilancia.

**Etapa asociada:** 3

---

### D-26 — Imputación de negocio + pipeline serializado (ColumnTransformer)

**Fecha:** 2026-06-20
**Estado:** Aceptada
**Responsable:** Data Scientist + Machine Learning Engineer

**Contexto:**
Los huecos de P1 tienen causas distintas y las transformaciones que aprenden parámetros no deben ajustarse sobre validación/prueba (fuente de fuga).

**Decisión:**
- **Imputación con sentido de negocio:** geo faltante → imputación dentro del pipeline (mediana en train), tras transformarse en `dist_haversine_km`; dimensiones de producto → **mediana de la categoría**; vendedor sin historial → tasa global del train + flag.
- **Nulos de la distancia (`dist_haversine_km`):** el `NaN` se **conserva en el CSV** (no se imputa en el ETL); lo rellena el `SimpleImputer(median)` del pipeline, ajustado solo en train. Su % de nulos (0.49%, 476 órdenes) es la **unión** de los huecos de geo cliente (0.27%) y geo vendedor (0.22%) —no un deterioro del vendedor—; la comparación antes/después a nivel orden confirma que no aumenta.
- **Encodings/escala** encapsulados en un `ColumnTransformer` (numéricas: mediana + `StandardScaler`; categóricas: más frecuente + `OneHotEncoder(handle_unknown="ignore", min_frequency=0.01)`), dentro de un `Pipeline` **ajustado solo en train** y serializado en `artifacts/pipeline_p1.joblib`.

**Alternativas consideradas:**
- `fillna(0)` global — descartado: borra la causa del hueco e introduce sesgo.
- Imputar antes del split — descartado por *leakage* estadístico.

**Consecuencias:**
- Positivas:
  - Preprocesamiento determinista y reutilizable por la Etapa 4 y el despliegue.
- Negativas o trade-offs:
  - Una sola fuente de transformación a mantener; documentada en `docs/decisiones_fe.md`.

**Etapa asociada:** 3

---

*Bitácora de decisiones del Proyecto Final. D-01 a D-12 corresponden a la
planificación y al cierre de la Etapa 0; D-13 a D-15 al cierre de la Etapa 1;
D-16 a D-21 al pivote a P1 documentado en la Etapa 2 (D-02 y D-03 quedan
reemplazadas); D-22 a D-26 al feature engineering de la Etapa 3. Nuevas
decisiones se agregarán durante la ejecución del proyecto.*
