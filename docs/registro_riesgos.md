# Registro de Riesgos — Proyecto Final

## Identificación, evaluación y mitigación de riesgos del proyecto

> Documento que registra los riesgos identificados durante el
> desarrollo del Proyecto Final, junto con su probabilidad, impacto y
> plan de mitigación. La identificación de riesgos es continua: nuevos
> riesgos se agregan a este registro a medida que surgen, y los
> existentes se actualizan en su estado y plan de mitigación.

---

## Convenciones

**Probabilidad:**
- Baja: improbable que ocurra en el horizonte del proyecto.
- Media: posibilidad real de ocurrencia.
- Alta: muy probable que ocurra durante el proyecto.

**Impacto:**
- Bajo: afecta una tarea o entregable menor, recuperable rápidamente.
- Medio: afecta una etapa o varias tareas, requiere reorganización.
- Alto: pone en riesgo entregables clave del proyecto o el
  cumplimiento del plazo final.

**Nivel de riesgo (combinación):**

| Probabilidad / Impacto | Bajo | Medio | Alto |
|---|---|---|---|
| Baja | Bajo | Bajo | Medio |
| Media | Bajo | Medio | Alto |
| Alta | Medio | Alto | Crítico |

**Estado:** Activo, Mitigado, Materializado, Cerrado.

---

## Plantilla para nuevos riesgos

```markdown
### R-NN — [Título del riesgo]

**Categoría:** [Técnico / Datos / Tiempo / Equipo / Comunicación / Negocio]
**Probabilidad:** [Baja / Media / Alta]
**Impacto:** [Bajo / Medio / Alto]
**Nivel de riesgo:** [Bajo / Medio / Alto / Crítico]
**Estado:** [Activo / Mitigado / Materializado / Cerrado]
**Responsable de seguimiento:** [Rol o nombre]

**Descripción:**
[En qué consiste el riesgo y por qué es relevante.]

**Detonantes posibles:**
[Eventos o situaciones que pueden hacer que el riesgo se materialice.]

**Plan de mitigación:**
[Acciones preventivas para reducir la probabilidad o el impacto.]

**Plan de contingencia:**
[Qué hacer si el riesgo efectivamente se materializa.]

**Etapas afectadas:** [Lista de etapas potencialmente impactadas.]
```

---

## Riesgos identificados

### R-01 — Sparsity de la matriz cliente-producto en Olist

**Categoría:** Datos
**Probabilidad:** Alta
**Impacto:** Medio
**Nivel de riesgo:** Alto
**Estado:** Cerrado (resuelto por el pivote a P1)
**Fecha de cambio de estado:** 2026-06-20
**Responsable de seguimiento:** Data Scientist

> **Cierre (2026-06-20):** La sparsity se confirmó en el EDA (co-compra 3.3%,
> ~97% de clientes con una sola compra) y fue una de las razones del pivote del
> recomendador a P1 (D-16). Como P1 no usa la matriz cliente-producto, este
> riesgo deja de ser relevante para el proyecto.

**Descripción:**
La gran mayoría de los clientes en Olist realiza una sola compra en
el periodo cubierto por el dataset. Esto hace que la matriz
cliente-producto sea extremadamente sparse, lo cual deteriora el
rendimiento de los enfoques de user-based collaborative filtering
clásicos.

**Detonantes posibles:**
- Intentar implementar un recomendador user-to-item ignorando la
  sparsity.
- Diseñar métricas de evaluación que asumen historial de compras
  recurrentes por cliente.

**Plan de mitigación:**
- Se decidió desde la fase de planificación adoptar un enfoque
  item-to-item (referencia: D-02 en la Bitácora de Decisiones), que
  no depende de la densidad de la matriz cliente-producto.
- En la Etapa 2 (EDA), validar empíricamente la sparsity y ajustar
  los enfoques si la distribución cambia respecto a lo esperado.

**Plan de contingencia:**
- Si durante el EDA la sparsity es aún peor de lo esperado, reforzar
  el peso del canal content-based sobre el colaborativo, ya que el
  primero no depende de co-ocurrencias entre clientes.

**Etapas afectadas:** 2, 3, 4, 6

---

### R-02 — Duración corta del proyecto (tres semanas) frente al alcance

**Categoría:** Tiempo
**Probabilidad:** Media
**Impacto:** Alto
**Nivel de riesgo:** Alto
**Estado:** Activo
**Responsable de seguimiento:** Scrum Master + Product Owner

**Descripción:**
El proyecto tiene una duración total de tres semanas calendario,
distribuidas en una fase previa y dos sprints de una semana. El
alcance comprometido (EDA exhaustivo, dos canales de recomendación,
API, Docker, dashboard, monitoreo y documentación completa) es
ambicioso para este plazo, especialmente para un equipo que no ha
trabajado junto previamente.

**Detonantes posibles:**
- Sub-estimación del esfuerzo en alguna etapa.
- Curva de aprendizaje en nuevas tecnologías (FastAPI, Docker,
  Streamlit).
- Bloqueos no resueltos a tiempo.
- Cambios de alcance impulsados por el mentor.

**Plan de mitigación:**
- Mantener el alcance estrictamente acotado al plan: si surge algo
  nuevo, va al backlog para sprints futuros, no se introduce al
  sprint en curso.
- Las ceremonias de Daily Stand-up se ejecutan a primera hora todos
  los días para detectar tempranamente cualquier desviación.
- El Scrum Master vigila el avance contra el plan y escala
  rápidamente cualquier riesgo de tiempo.

**Plan de contingencia:**
- Si el Sprint 1 cierra con tareas incompletas críticas, se replantea
  el alcance del Sprint 2 priorizando lo mínimo viable para
  presentación.
- Como último recurso, el monitoreo (HU-16) es la historia con
  prioridad media y puede aplazarse o simplificarse si fuera
  necesario.

**Etapas afectadas:** Todas

---

### R-03 — Curva de aprendizaje en GitHub Projects

**Categoría:** Equipo
**Probabilidad:** Alta
**Impacto:** Bajo
**Nivel de riesgo:** Medio
**Estado:** Mitigado (con plan formativo)
**Responsable de seguimiento:** Scrum Master

**Descripción:**
El líder del proyecto y posiblemente otros miembros del equipo no han
usado antes GitHub Projects como herramienta de gestión de Sprint
Backlogs. La curva de aprendizaje puede generar fricción inicial.

**Detonantes posibles:**
- Iniciar el Sprint 1 sin haber preparado el tablero de trabajo
  previamente.
- Confusión sobre cómo vincular issues, pull requests y elementos del
  tablero.

**Plan de mitigación:**
- Se generará una guía detallada de configuración y uso de GitHub
  Projects al inicio del Sprint 1, como complemento de la guía de la
  Etapa 1 (referencia: D-08 en la Bitácora de Decisiones).
- El Scrum Master dedicará tiempo del Día 1 del Sprint 1 a configurar
  el tablero y socializarlo al equipo.

**Plan de contingencia:**
- Si la herramienta resulta excesivamente lenta de adoptar, se puede
  optar por un Trello temporal mientras se completa la curva de
  aprendizaje, sin afectar el repositorio.

**Etapas afectadas:** 1, 5

---

### R-04 — Curva de aprendizaje en tecnologías de despliegue (FastAPI, Docker, Streamlit)

**Categoría:** Equipo
**Probabilidad:** Media
**Impacto:** Medio
**Nivel de riesgo:** Medio
**Estado:** Activo
**Responsable de seguimiento:** Machine Learning Engineer

**Descripción:**
Las tecnologías de despliegue del Sprint 2 (FastAPI, Docker,
Streamlit) requieren habilidades específicas que pueden no estar
plenamente desarrolladas en todos los miembros del equipo.

**Detonantes posibles:**
- Subestimar el esfuerzo de configurar Docker desde cero.
- Problemas de compatibilidad entre dependencias.
- Configuración inicial de FastAPI que tome más tiempo del esperado.

**Plan de mitigación:**
- El ML Engineer es el responsable primario y debe llegar al Sprint 2
  con la curva de aprendizaje resuelta.
- En el Sprint 1, el ML Engineer puede comenzar a preparar el
  esqueleto del Dockerfile y la estructura básica de la API,
  aprovechando holguras de carga en esa fase.

**Plan de contingencia:**
- Si Docker presenta dificultades insuperables, el sistema puede
  desplegarse en un entorno virtual local documentado, sacrificando
  reproducibilidad pero manteniendo el resto del entregable.

**Etapas afectadas:** 7, 8

---

### R-05 — Bloqueos entre roles por dependencias secuenciales

**Categoría:** Equipo
**Probabilidad:** Media
**Impacto:** Medio
**Nivel de riesgo:** Medio
**Estado:** Activo
**Responsable de seguimiento:** Scrum Master

**Descripción:**
Las etapas del proyecto tienen dependencias secuenciales (el feature
engineering depende del EDA, el modelado depende del feature
engineering, el despliegue depende del modelado, etc.). Si una etapa
se demora, las siguientes pueden quedar bloqueadas.

**Detonantes posibles:**
- Una etapa se atrasa y no se comunica a tiempo al equipo.
- Algún rol queda esperando entregables sin actividades alternativas.
- Bloqueo técnico no comunicado.

**Plan de mitigación:**
- Las Daily Stand-ups exponen rápidamente los bloqueos.
- Cada rol tiene tareas paralelizables: por ejemplo, mientras el Data
  Analyst termina el EDA, el Data Scientist puede revisar
  documentación de scikit-learn pipelines; mientras el Data Scientist
  modela, el ML Engineer prepara el esqueleto de la API.
- El Scrum Master gestiona la redistribución de cargas cuando
  detecta un cuello de botella.

**Plan de contingencia:**
- Si una dependencia crítica se atrasa, el equipo se reúne para
  redistribuir tareas y dar apoyo al rol bloqueado, en lugar de
  esperar.

**Etapas afectadas:** Todas

---

### R-06 — Cambios de alcance impulsados por el mentor

**Categoría:** Negocio
**Probabilidad:** Media
**Impacto:** Medio
**Nivel de riesgo:** Medio
**Estado:** Activo
**Responsable de seguimiento:** Product Owner

**Descripción:**
Durante las revisiones de sprint o las interacciones con el mentor,
puede surgir feedback que sugiera cambios de alcance, nuevas
funcionalidades, o reorientación de algunos entregables.

**Detonantes posibles:**
- Feedback del mentor en la primera Sprint Review.
- Cambio en los criterios de evaluación del comité.
- Sugerencias específicas de profundización en alguna área.

**Plan de mitigación:**
- El Product Owner es el filtro único de las comunicaciones con el
  mentor.
- Cualquier sugerencia de cambio se evalúa contra el plan original
  antes de comprometerse.
- Si el cambio agrega valor sustancial, se documenta en la Bitácora
  de Decisiones y se ajusta el backlog.

**Plan de contingencia:**
- Para cambios pequeños que no comprometan el plan: aceptar e
  incorporar.
- Para cambios grandes: discutir con el mentor su prioridad real y
  buscar alcanzar el mínimo viable sin sacrificar entregables ya
  comprometidos.

**Etapas afectadas:** Todas

---

### R-07 — Calidad de los datos en categorías y atributos de productos

**Categoría:** Datos
**Probabilidad:** Media
**Impacto:** Medio
**Nivel de riesgo:** Medio
**Estado:** Activo
**Responsable de seguimiento:** Data Analyst

> **Actualización (Etapa 2):** El EDA cuantificó los nulos (categoría de
> producto, atributos físicos) y la cobertura geográfica; sigue activo de cara
> al feature engineering de P1, con estrategia de imputación propuesta (D-21,
> HU-07).
>
> **Actualización (Etapa 3):** Estrategia de imputación implementada y
> documentada (D-26, `docs/decisiones_fe.md`): dimensiones por mediana de
> categoría, geo/distancia y categóricas dentro del pipeline (ajustado solo en
> train). Hallazgo registrado: los nulos de `dist_haversine_km` (0.49%) son la
> **unión** de los huecos de geo cliente (0.27%) y vendedor (0.22%), no un
> deterioro; comparar a nivel orden evita el falso diagnóstico. Sigue activo
> como vigilancia en el modelado.

**Descripción:**
El dataset Olist tiene valores nulos conocidos en las categorías de
producto y en algunos atributos físicos (peso, dimensiones, fotos).
Esto afecta especialmente al canal content-based, que depende
fuertemente de los atributos del producto.

**Detonantes posibles:**
- Decisión apresurada de imputación que introduzca sesgos.
- Eliminación de filas con nulos que reduzca excesivamente el
  catálogo.
- Subvaloración del impacto de la calidad en la Etapa 2.

**Plan de mitigación:**
- El EDA de la Etapa 2 debe cuantificar explícitamente el porcentaje
  de nulos por columna y producto, y proponer una estrategia
  documentada de tratamiento.
- Las decisiones de tratamiento se registran en el documento de
  decisiones de feature engineering en la Etapa 3.

**Plan de contingencia:**
- Si el porcentaje de productos sin categoría es alto (>20%),
  considerar tratar "DESCONOCIDO" como una categoría legítima y
  añadir indicadores de missingness.
- Para atributos físicos, considerar imputación por mediana dentro de
  la categoría.

**Etapas afectadas:** 2, 3

---

### R-08 — Procesamiento de la matriz de co-ocurrencia para volumen grande

**Categoría:** Técnico
**Probabilidad:** Baja
**Impacto:** Medio
**Nivel de riesgo:** Bajo
**Estado:** Cerrado (resuelto por el pivote a P1)
**Fecha de cambio de estado:** 2026-06-20
**Responsable de seguimiento:** Data Scientist

**Notas:** El pivote a P1 (D-16) elimina la dependencia de la matriz de
co-ocurrencia producto-producto: la tarea de predicción de entrega tardía no la
construye. El riesgo queda sin objeto y se cierra, por la misma lógica que R-01.

**Descripción (histórica):**
La matriz de co-ocurrencia producto-producto en Olist puede tener
dimensiones del orden de 32,000 x 32,000 si se considera el catálogo
completo. Esto puede generar problemas de memoria si no se usa una
representación sparse adecuada.

**Detonantes posibles:**
- Implementación inicial con matrices densas.
- Cómputo de similitudes sin aprovechar sparsity.

**Plan de mitigación:**
- Usar `scipy.sparse` desde el inicio para la matriz de co-ocurrencia.
- Aprovechar `sklearn.neighbors.NearestNeighbors` con `algorithm='brute'`
  y métricas optimizadas para sparse arrays.

**Plan de contingencia:**
- Si la memoria es un problema, filtrar productos con menos de N
  apariciones (por ejemplo, N=5) para reducir el tamaño efectivo del
  catálogo modelable.

**Etapas afectadas:** 3, 4

---

### R-09 — Drift entre ramas personales por sincronización tardía con developer

**Categoría:** Equipo / Técnica
**Probabilidad:** Media
**Impacto:** Medio
**Nivel:** Medio
**Estado:** Activo

**Descripción:**
El modelo híbrido de ramas adoptado en D-06 (cinco ramas personales
sobre una rama de integración developer) requiere disciplina de
sincronización diaria. Si un integrante no hace pull regular de
developer hacia su rama personal, sus cambios divergen del resto del
equipo y, al abrir el pull request, los conflictos pueden ser
grandes y difíciles de resolver.

**Detonantes:**
- Un integrante trabaja varios días en su rama personal sin mergear
  developer.
- Pull requests acumulan trabajo de toda una semana en lugar de
  cambios incrementales.
- Cambios cruzados de varias personas sobre el mismo archivo o
  módulo.

**Plan de mitigación:**
- Convención obligatoria: pull diario de developer hacia la rama
  personal al iniciar la jornada.
- Convención: pull requests pequeños y frecuentes, no acumulativos.
- Convención de propiedad suave por subcarpetas según rol para
  reducir cambios cruzados sobre los mismos archivos.

**Plan de contingencia:**
- Si los conflictos se acumulan en un PR, el ML Engineer organiza
  una sesión de integración con el autor del PR para resolverlos en
  conjunto.
- Si el patrón se repite en varias personas, se eleva como punto de
  Retrospective del sprint en curso.

**Etapas afectadas:** Transversal (Sprint 1 y Sprint 2)

---

### R-10 — Exposición accidental de datos sensibles en repositorio público

**Categoría:** Técnica / Seguridad
**Probabilidad:** Media
**Impacto:** Alto
**Nivel de riesgo:** Alto
**Estado:** Mitigado
**Responsable de seguimiento:** Scrum Master

**Descripción:**
Al ser el repositorio público (D-14 en la Bitácora de Decisiones),
cualquier información sensible commiteada por error queda expuesta en
el historial de Git de forma permanente. Aunque se elimine
posteriormente del estado actual del repositorio, el historial
conserva la información a menos que se reescriba activamente. Este
riesgo cubre la exposición de credenciales, tokens de API, datos
personales del dataset, archivos `.env`, y cualquier configuración
interna que no debería ser pública.

**Detonantes posibles:**
- Commitear un archivo `.env` o `secrets/` por descuido.
- Olvidar agregar un archivo nuevo al `.gitignore` antes del commit.
- Pegar credenciales como literales en código y commitear sin
  revisión visual.
- Subir archivos del dataset que violen su licencia de uso.

**Plan de mitigación:**
- `.gitignore` blindado desde el primer commit, incluyendo
  `data/raw/`, `data/processed/`, `*.env`, `*.pem`, `*.key`,
  `secrets/`.
- Convención del equipo: nunca usar credenciales literales en código;
  siempre vía variables de entorno.
- Revisión visual del `git status` antes de cada commit grande.
- Revisión por pares en los Pull Requests, aplicable plenamente a
  partir del Sprint 2.

**Plan de contingencia:**
- Si se detecta una exposición, se ejecuta inmediatamente
  `git filter-branch` o BFG Repo-Cleaner para eliminar la información
  del historial completo.
- Se rotan las credenciales expuestas (cambiar tokens, contraseñas).
- Se documenta el incidente en este registro como ocurrencia
  materializada para evitar repetirlo.

**Etapas afectadas:** Todas (transversal)

---

### R-11 — Revisor único en Pull Requests durante el setup inicial

**Categoría:** Equipo / Proceso
**Probabilidad:** Alta (durante Etapa 1)
**Impacto:** Bajo
**Nivel de riesgo:** Medio
**Estado:** Materializado (durante Etapa 1)
**Responsable de seguimiento:** Scrum Master

**Descripción:**
La convención del equipo establece que cada Pull Request requiere
revisión por al menos un compañero distinto al autor antes del merge.
Durante la Etapa 1, el Scrum Master fue el único integrante activo en
el repositorio: los demás integrantes se incorporan al inicio del
Sprint 2 con la entrega de la guía operativa del equipo. Esto implicó
que los Pull Requests de la Etapa 1 fueron creados, aprobados y
mergeados por el mismo autor, violando temporalmente la convención.

**Detonantes posibles:**
- Setup inicial liderado por un único integrante.
- Onboarding diferido del resto del equipo al final de la Etapa 1.

**Plan de mitigación:**
- La excepción se documenta formalmente como aplicable únicamente a la
  Etapa 1, donde los Pull Requests son de infraestructura y
  documentación (no contienen código funcional).
- La regla de revisor distinto al autor aplica plenamente desde el
  Sprint 2, cuando el equipo completo está incorporado al repositorio.
- El contenido de los Pull Requests de la Etapa 1 queda públicamente
  visible para auditoría retrospectiva por cualquier integrante.

**Plan de contingencia:**
- Si se detecta un problema en alguno de los Pull Requests
  auto-aprobados de la Etapa 1, se corrige con un nuevo Pull Request
  siguiendo el flujo completo desde el Sprint 2.

**Etapas afectadas:** 1

---

### R-12 — Data leakage en la predicción de entrega tardía

**Categoría:** Técnica / Datos
**Probabilidad:** Media
**Impacto:** Alto
**Nivel de riesgo:** Alto
**Estado:** Mitigado (auditado en Etapa 4; vigilancia en Etapa 6)
**Fecha de cambio de estado:** 2026-06-21
**Responsable de seguimiento:** Data Scientist + Machine Learning Engineer

> **Mitigación (2026-06-20, Etapa 3):** se aplicó la separación [t0]/[POST] como
> checklist (features [POST] —entrega real, reseñas— excluidas), la tasa del
> vendedor se calculó point-in-time con una **prueba anti-fuga automática** (OK),
> el *split* es temporal por fecha de compra y el preprocesador se ajusta **solo
> en train**. El riesgo sigue vigente como vigilancia en el modelado (Etapa 4): si
> una métrica resulta sospechosamente alta, auditar primero `tasa_vendedor`.
>
> **Auditoría (2026-06-21, Etapa 4):** ejecutada. Las métricas quedaron en rango
> realista (ROC-AUC 0.70, PR-AUC 0.12 — lejos del 0.99 que delataría fuga),
> `tasa_vendedor` pesa solo **6.0%** de la importancia del modelo y un candado de
> código (`assert_sin_features_post`) verifica que ninguna columna [POST] entra como
> feature. **Sin fuga detectada.** La vigilancia continúa en la evaluación final
> (Etapa 6).
>
> **Re-ejecución (2026-06-27, Etapa 3 — D-30):** la ampliación a múltiples targets
> (`clase_entrega`, `dias_vs_promesa`, `dias_entrega_real`) **no** relaja el riesgo:
> los nuevos targets son labels [POST] y **nunca** son features; el `X` sigue siendo
> `NUMERIC_FEATURES + CATEGORICAL_FEATURES`. El candado anti-fuga y la prueba
> point-in-time de `tasa_vendedor` se mantienen. Al rehacer la Etapa 4 debe
> auditarse la fuga **para cada familia de modelo** (binaria, multiclase y regresión).

**Descripción:**
El *target* `entrega_tarde` se construye con la fecha de entrega real. Si esa
información, o derivados como los días reales de tránsito, la fecha de despacho
real o la propia reseña, se usa como *feature*, el modelo "ve el futuro":
métricas infladas offline y fracaso en producción.

**Detonantes posibles:**
- Construir features sin separar [t0] de [POST].
- Calcular la tasa histórica del vendedor incluyendo la orden actual.
- Usar un *split* aleatorio en vez de temporal.

**Plan de mitigación:**
- Mapa de leakage [t0]/[POST] aplicado (D-21).
- Features históricas con ventana estrictamente pasada.
- Partición temporal de la evaluación (D-09).
- Revisión cruzada del conjunto de features antes de modelar.

**Plan de contingencia:**
- Si una métrica offline resulta "sospechosamente alta", auditar las features en
  busca de fuga y reentrenar.

**Etapas afectadas:** 3, 4, 6

---

### R-13 — Desalineación con la propuesta aprobada por el pivote de objetivo

**Categoría:** Negocio / Proceso
**Probabilidad:** Media
**Impacto:** Alto
**Nivel de riesgo:** Alto
**Estado:** Activo
**Responsable de seguimiento:** Product Owner

**Descripción:**
La propuesta aprobada en la Etapa 0 (D-12) comprometía un recomendador
item-to-item. El pivote a P1 (D-16), aunque bien fundamentado, cambia el
objetivo a mitad del Sprint 1; el comité podría esperar el entregable original.

**Detonantes posibles:**
- El mentor evalúa contra la propuesta literal.
- El pivote no se comunica ni se justifica a tiempo.

**Plan de mitigación:**
- Documentar el pivote con rigor (Problem Discovery & DVA Report, D-16 a D-21).
- Narrarlo como consultora que probó la hipótesis del cliente antes de proponer
  un dolor mayor; el PO comunica el cambio al mentor de forma explícita y temprana.
- Conservar item-to-item como hipótesis investigada (no es trabajo perdido).

**Plan de contingencia:**
- Si el mentor exige el recomendador, presentar el DVA de item-to-item (viable
  pero limitado) como evidencia y negociar alcance; el recomendador investigado
  puede reincorporarse como anexo.

**Etapas afectadas:** 2, 5, 9

---

### R-14 — Cambio de régimen temporal y eventos puntuales que afectan la generalización

**Categoría:** Datos
**Probabilidad:** Media
**Impacto:** Medio
**Nivel de riesgo:** Medio
**Estado:** Activo
**Responsable de seguimiento:** Data Analyst

> **Observación (2026-06-21, Etapa 4):** el split temporal lo confirma: la tasa de
> `entrega_tarde` cae de 9.03% (train, periodo antiguo) a 5.34% (val) y 6.61%
> (test). El modelo se evalúa en un régimen distinto al de entrenamiento; las
> métricas de test son honestas pero más bajas y la calibración queda desplazada
> (D-29). Se conserva el periodo completo y se difiere el re-ventaneo/segmentación a
> la Etapa 6.

**Descripción:**
El EDA detectó variación temporal de la tasa de tardanza y un posible incidente
logístico puntual en 2018 que infla algún mes. Un modelo entrenado sobre un
periodo y validado en otro (partición temporal) puede degradarse si el régimen
cambia; además, los meses de bajo volumen producen tasas inestables.

**Detonantes posibles:**
- *Split* temporal que deja el incidente solo en *train* o solo en validación.
- Features estacionales sobreajustadas a un evento irrepetible.

**Plan de mitigación:**
- Elegir la fecha de corte del *split* a la luz de la distribución temporal.
- Tratar con cuidado las features de estacionalidad; filtrar o ponderar meses de
  bajo volumen; documentar el incidente.

**Plan de contingencia:**
- Si la validación temporal muestra degradación por régimen, reportarla
  honestamente y discutir una ventana de entrenamiento más representativa.

**Etapas afectadas:** 3, 4, 6

---

## Resumen ejecutivo del registro

| Identificador | Categoría | Nivel | Estado |
|---|---|---|---|
| R-01 | Datos | Alto | Cerrado (pivote) |
| R-02 | Tiempo | Alto | Activo |
| R-03 | Equipo | Medio | Mitigado |
| R-04 | Equipo | Medio | Activo |
| R-05 | Equipo | Medio | Activo |
| R-06 | Negocio | Medio | Activo |
| R-07 | Datos | Medio | Activo |
| R-08 | Técnico | Bajo | Cerrado (pivote) |
| R-09 | Equipo / Técnica | Medio | Activo |
| R-10 | Técnica / Seguridad | Alto | Mitigado |
| R-11 | Equipo / Proceso | Medio | Materializado (Etapa 1) |
| R-12 | Técnica / Datos | Alto | Mitigado (auditado en Etapa 4) |
| R-13 | Negocio / Proceso | Alto | Activo |
| R-14 | Datos | Medio | Activo |

**Riesgos críticos:** ninguno al cierre de la Etapa 4.

**Riesgos altos no mitigados:** R-02 (duración corta vs alcance) y R-13 (alineación
del pivote con la propuesta aprobada). R-12 (data leakage en P1) quedó **mitigado y
auditado** en la Etapa 4 (sin fuga: `tasa_vendedor` 6%, métricas realistas), con
vigilancia en la evaluación final.

**Foco de seguimiento prioritario:** R-02 (tiempo, cierre del Sprint 1), R-13
(comunicar y justificar el pivote al mentor) y R-14 (régimen temporal, a resolver en
la Etapa 6).

---

## Reglas de mantenimiento del registro

- El registro se revisa en cada Sprint Review como parte del cierre
  del sprint.
- Nuevos riesgos identificados durante el proyecto se agregan al
  documento con el siguiente identificador disponible.
- El estado de cada riesgo se actualiza cuando hay cambios
  significativos.
- Cuando un riesgo se materializa, su entrada se actualiza con la
  descripción de qué ocurrió y cómo se manejó.

---

*Registro de riesgos del Proyecto Final. Versión inicial al arranque
del proyecto. Documento vivo, actualizado durante la ejecución.*
