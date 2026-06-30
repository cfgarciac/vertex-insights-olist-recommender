# Product Backlog — Proyecto Final

## Sistema de recomendación e-commerce sobre dataset Olist

> Lista priorizada de historias de usuario que componen el alcance
> total del Proyecto Final. Es la fuente única de requisitos del
> proyecto. El Product Owner es el responsable de su mantenimiento y
> priorización. Las historias se incorporan al Sprint Backlog
> correspondiente en cada ceremonia de Sprint Planning.

---

## Información general

**Producto:** Sistema predictivo de **desempeño de entrega** (predicción de
entrega tardía, problema P1) para el marketplace Olist, sobre el dataset
Brazilian E-commerce Public Dataset by Olist.

> **Nota de pivote (Etapa 2 · D-16):** El producto se reorientó durante el EDA,
> de un recomendador item-to-item a la **predicción de entrega tardía (P1)**.
> item-to-item queda como la hipótesis del cliente investigada (viable pero
> limitada). Las historias **HU-07 a HU-18**, escritas para el recomendador,
> se realinean a P1: **HU-07 a HU-10 ya están reescritas y cerradas en su versión
> P1** (Etapas 3-4); HU-11 (cierre del Sprint 1) y HU-12 a HU-18 (Sprint 2) se
> ajustan al avanzar (ver la "Nota de impacto del pivote" tras HU-07 y las
> decisiones D-16 a D-29 en la bitácora).

**Sprint Goals:**

- Sprint 1: Entregar un MVP funcional del **sistema predictivo de entrega
  tardía (P1)**, con EDA/descubrimiento del problema completo, feature
  engineering reproducible y al menos dos modelos de clasificación comparados
  contra un baseline.
- Sprint 2: Llevar el sistema a un estado productivo consumible, con
  API, dashboard, monitoreo, documentación final y presentación
  aprobada por el comité evaluador.

**Convención de identificadores:** `HU-NN` para historias de usuario
numeradas secuencialmente.

**Convención de estimaciones:** S (pequeña, hasta 1 día-persona), M
(media, 1-2 días-persona), L (grande, 2-3 días-persona).

**Convención de prioridades:** Alta, Media, Baja. La prioridad es
relativa al sprint en el que se planifica entregar la historia.

---

## Historias del Sprint 1

### HU-01 — Aprobar la propuesta del Proyecto Final

**Como** Product Owner del equipo,
**quiero** que la propuesta del proyecto sea aprobada por el comité
evaluador,
**para** habilitar formalmente el inicio del desarrollo técnico.

**Criterios de aceptación:**

- Documento de propuesta diligenciado con todos los campos
  requeridos.
- Identidad del equipo definida (nombre, misión, correo).
- Aprobación registrada por mentor o comité evaluador.

**Estimación:** M
**Prioridad:** Alta
**Etapa asociada:** 0
**Estado:** Completada (Etapa 0)

**Notas de cierre:**

- Identidad del equipo registrada en D-11 de la Bitácora de
  Decisiones.
- Aprobación formal registrada en D-12 de la Bitácora de Decisiones.
- Documento entregable: `Propuesta_PF_Vertex_Insights.docx`.

---

### HU-02 — Configurar el repositorio y la infraestructura del proyecto

**Como** equipo,
**quiero** tener el repositorio en GitHub con la estructura completa
de carpetas, ramas y convenciones definidas,
**para** trabajar de forma colaborativa y trazable desde el primer día.

**Criterios de aceptación:**

- Repositorio creado con las siete ramas largas (`master`,
  `developer`, `Cristian`, `Harrison`, `Juan`, `Amaury`, `Nassim`).
- Estructura inicial de carpetas creada y pusheada.
- Primer commit y tag `V1.0.0` registrados en `master`.
- Cinco integrantes con acceso de colaborador.
- Documento de convenciones del equipo agregado al README.

**Estimación:** M
**Prioridad:** Alta
**Etapa asociada:** 1
**Estado:** Completada (Etapa 1)

**Notas de cierre:**

- Repositorio creado en `cfgarciac/vertex-insights-olist-recommender`
  con visibilidad pública y licencia MIT (D-14).
- Siete ramas largas y tag `V1.0.0` publicados.
- Convenciones del equipo documentadas en `docs/convenciones.md`.
- Acceso de colaboradores pendiente de procesar al recibir los
  usuarios de GitHub de los compañeros (gestión post-Etapa 1).

---

### HU-03 — Configurar el tablero de trabajo en GitHub Projects

**Como** Scrum Master,
**quiero** tener un tablero de trabajo en GitHub Projects con las
historias de usuario del sprint y sus tareas asociadas,
**para** mantener la visibilidad del estado del proyecto en todo
momento.

**Criterios de aceptación:**

- GitHub Project creado y vinculado al repositorio.
- Cinco estados de Status configurados (Backlog, Ready, In progress,
  In review, Done).
- Campo personalizado de Estimación configurado (S, M, L).
- Etiquetas (labels) del proyecto creadas en el repositorio (etapas,
  roles, tipos).
- Plantilla de issue para historias de usuario configurada en el
  repositorio.
- Historias del Sprint 1 cargadas como issues.

**Estimación:** S
**Prioridad:** Alta
**Etapa asociada:** 1
**Estado:** Completada (Etapa 1)

**Notas de cierre:**

- Project "Vertex Insights — Sprint 1" creado y vinculado al repo.
- Cinco estados de Status adoptados según plantilla enriquecida de
  GitHub (D-13).
- Dieciocho labels creados en el repositorio (9 etapas, 5 roles, 4
  tipos).
- Plantilla `historia_usuario.yml` configurada como Issue Form (D-15).
- Historias HU-02 a HU-11 cargadas como issues con su metadata
  completa.

---

### HU-04 — Entender el problema y los datos disponibles

**Como** Data Scientist,
**quiero** entender el problema de negocio y los datos disponibles en
Olist,
**para** definir el enfoque del sistema de recomendación.

**Criterios de aceptación:**

- Mapeo de cada KPI de negocio a una métrica técnica equivalente.
- Identificación de las variables clave del dataset relevantes para el
  caso de uso.
- Hipótesis iniciales de modelado documentadas.

**Estimación:** S
**Prioridad:** Alta
**Etapa asociada:** 2
**Estado:** Completada (Etapa 2)

**Notas de cierre:**

- El entendimiento del problema derivó en un **descubrimiento estructurado**
  (embudo, D-17) que pivotó el objetivo a P1 (D-16, D-18).
- El mapeo original de KPIs (CTR/AOV → Precision@K/Recall@K) quedó inaplicable
  (CTR no medible en Olist; cambio de objetivo) y se **reemplazó por D-19**.
- Variables clave identificadas y volcadas al *shortlist* de features [t0] (D-21).
- Hipótesis inicial de modelado: **clasificación binaria de `entrega_tarde`** (D-20).

---

### HU-05 — Realizar el análisis exploratorio de datos sobre Olist

**Como** Data Analyst,
**quiero** realizar un análisis exploratorio profundo de las nueve
tablas de Olist,
**para** identificar problemas de calidad, distribuciones, sesgos y
oportunidades de feature engineering.

**Criterios de aceptación:**

- Inspección inicial de las nueve tablas completada.
- Análisis univariable, bivariable, multivariable y temporal de
  variables clave.
- Análisis específico de sparsity de la matriz cliente-producto.
- Problemas de calidad identificados y documentados.
- Documento `eda_hallazgos.md` consolidado.

**Estimación:** L
**Prioridad:** Alta
**Etapa asociada:** 2
**Estado:** Completada (Etapa 2)

**Notas de cierre:**

- EDA ejecutado sobre las 9 tablas (`notebooks/dva.ipynb`,
  `discovery_nivel2.ipynb`, `nivel_2_dva.ipynb`) y consolidado en el EDA
  enfocado de P1 `notebooks/02_EDA_VERTEX.ipynb` (con magnitud económica,
  geoespacial, correlaciones y mapa de leakage).
- La **sparsity se cuantificó** (co-compra 3.3%, ~97% de clientes con una sola
  compra), confirmando el techo del recomendador y motivando el pivote
  (riesgo R-01 cerrado).
- Hallazgos consolidados en el **Problem Discovery & Data Viability Report**
  (`docs/`), que cumple el rol del `eda_hallazgos.md` planeado, reorientado a P1.
- Problemas de calidad documentados (nulos en categoría y atributos físicos,
  cobertura geo); ver R-07.

---

### HU-06 — Producir el informe exploratorio en Power BI

**Como** Data Analyst,
**quiero** construir un informe en Power BI con las visualizaciones
clave del comportamiento del marketplace,
**para** sustentar la narrativa de negocio del proyecto ante los
stakeholders.

**Criterios de aceptación:**

- Informe Power BI con al menos cuatro vistas clave (comportamiento
  por categoría, geografía, temporal, reseñas).
- Archivo del informe versionado en `reports/`.
- Validación del informe por parte del Product Owner.

**Estimación:** M
**Prioridad:** Media
**Etapa asociada:** 2
**Estado:** Completada (Etapa 2) — reorientada a P1

**Notas de cierre:**

- El informe de narrativa de negocio se **reorienta a P1**. Vistas propuestas:
  (1) tardanza por región (Norte/Nordeste vs São Paulo), (2) distancia vs
  tardanza, (3) curva en "J" de satisfacción vs cumplimiento de la promesa,
  (4) colchón de la estimación (prometido − real).
- **[POR CONFIRMAR — Juan/DA + PO]** estado y ubicación del archivo `.pbix` y la
  validación formal del PO. Ajustar este bloque antes de publicar el cierre.

---

### HU-07 — Preparar los datos y construir el pipeline de features de P1 (entrega tardía)

**Como** Data Scientist,
**quiero** construir el pipeline reproducible de limpieza, integración y
feature engineering para la predicción de entrega tardía,
**para** garantizar que las mismas transformaciones se apliquen en
entrenamiento e inferencia, sin fuga de datos.

**Criterios de aceptación:**

- Tabla analítica a nivel **orden** construida desde las nueve tablas
  (universo `delivered`).
- *Target* `entrega_tarde` construido contra la fecha prometida (D-20).
- Features **[t0]** del *shortlist* (D-21): días prometidos, distancia
  *haversine*, `mismo_estado`, ratio flete/valor, peso/volumen/categoría,
  mes/día de compra.
- **Tasa histórica de entrega tardía del vendedor** construida **sin fuga**
  (ventana definida; solo órdenes pasadas, excluyendo la actual).
- Tratamiento de nulos documentado (geo → centroide del estado; categoría →
  "DESCONOCIDO" + indicador de *missingness*; dimensiones → mediana de categoría).
- Encodings de categóricas (estado, categoría) y transformaciones numéricas.
- Pipeline encapsulado con `Pipeline` y `ColumnTransformer` de scikit-learn.
- **Split temporal** del dataset realizado sin *leakage* (D-09).
- Pipeline serializado en `artifacts/`.

**Estimación:** L
**Prioridad:** Alta
**Etapa asociada:** 3
**Estado:** Completada (Etapa 3)

> **Reorientada por el pivote (D-16).** Reemplaza la versión orientada al
> recomendador (matriz de co-ocurrencia producto-producto y vectores de producto).

**Notas de cierre:**

- Tabla analítica a nivel orden construida sobre `delivered` (96,470 órdenes) a
  partir del CSV consolidado (D-22, D-23); *target* `entrega_tarde` con tasa base
  **8.11%**.
- Features [t0] del *shortlist* construidas; columnas [POST] (entrega real,
  reseñas) excluidas como features.
- **Tasa histórica del vendedor sin fuga** (expanding point-in-time, mínimo 5,
  respaldo global + flag) con **prueba anti-fuga OK** (D-24).
- Imputación documentada (geo, dimensiones, vendedor nuevo) y encodings en un
  `ColumnTransformer` ajustado solo en train; **pipeline serializado** en
  `artifacts/pipeline_p1.joblib` (D-26).
- **Split temporal 70/15/15** por fecha de compra (D-25).
- Entregables: `src/features/build_dataset.py`, `vertex_files/orders_features.csv`,
  `notebooks/03_EDA_VERTEX.ipynb`, `docs/decisiones_fe.md`.

---

### Nota de impacto del pivote en el backlog (Etapa 2 · D-16)

Las siguientes historias se escribieron para el recomendador y se realinean a P1.
**HU-08, HU-09 y HU-10 ya fueron formalizadas y cerradas** en su versión P1 durante
la Etapa 4 (ver sus notas de cierre); **HU-12 a HU-18 quedan pendientes de
redefinición formal por el Product Owner**. El mapeo aplicado/propuesto es:

- **HU-08 (baseline):** de "ranking por popularidad de categoría" → **baseline de
  clasificación** (regla simple, p. ej. "cruce de estado + larga distancia = tarde",
  o clase mayoritaria) como piso de comparación.
- **HU-09 y HU-10 (canales content-based / collaborative):** se sustituyen por
  **entrenar ≥2 modelos de clasificación comparables** de `entrega_tarde`
  (p. ej. Regresión Logística y *Gradient Boosting*).
- **HU-12 (evaluación):** de Precision@K/Recall@K/MAP@K → **ROC-AUC, PR-AUC, F1,
  calibración**, con análisis por región y por *cold-start* de vendedores nuevos.
- **HU-13 (API):** de `/recommend/similar` y `/recommend/complementary` →
  endpoint **`/predict`** de riesgo de entrega tardía (entrada: features de la
  orden en t0; salida: probabilidad/clase).
- **HU-15 (dashboard):** pestañas de **predicción de riesgo**, exploración
  regional del dolor y métricas del sistema.
- **HU-16 (monitoreo):** se mantiene (PSI), ahora sobre las features de P1.
- **HU-11, HU-14, HU-17, HU-18:** agnósticas al objetivo (cierre de Sprint,
  Docker, documentación, presentación); ajustes menores de redacción.

---


---

### HU-08 — Implementar el baseline de popularidad

**Como** Data Scientist,
**quiero** implementar el baseline obligatorio de ranking por
popularidad por categoría,
**para** disponer de un punto de comparación sólido para los modelos
posteriores.

**Criterios de aceptación:**

- Baseline de clasificación implementado en `src/models/baseline.py`
  (clase mayoritaria + regla simple distancia/estado).
- Métricas de piso (PR-AUC, ROC-AUC) calculadas sobre el split temporal.
- Documentado como piso de comparación en
  `reports/etapa4_modelado_resultados.md`.

**Estimación:** S
**Prioridad:** Alta
**Etapa asociada:** 4
**Estado:** Completada (Etapa 4)

> **Reorientada por el pivote (D-16).** De "ranking por popularidad de categoría"
> a **baseline de clasificación** de `entrega_tarde` (clase mayoritaria + regla de
> negocio distancia/estado) como piso de comparación.

**Notas de cierre:**

- Baselines implementados en `src/models/baseline.py`: clase mayoritaria (PR-AUC
  test = tasa base 0.066, ROC-AUC 0.5) y regla distancia+estado.
- Fijan el piso: ambos modelos (Logística y XGBoost) los superan con holgura en
  PR-AUC/ROC-AUC (D-27); detalle en `reports/etapa4_modelado_resultados.md`.
- Las métricas de ranking (Precision@K/Recall@K) se sustituyen por
  PR-AUC/ROC-AUC/recall (D-19), coherente con el pivote.

---

### HU-09 — Implementar el canal de productos similares (content-based)

**Como** Data Scientist,
**quiero** implementar el modelo de recomendación de productos
similares basado en contenido,
**para** habilitar la sugerencia de productos parecidos al que el
cliente está visualizando.

**Criterios de aceptación:**

- Primer clasificador de `entrega_tarde` implementado (Regresión Logística,
  `class_weight="balanced"`), encadenado al preprocesador de la Etapa 3 en un
  `Pipeline` y ajustado solo en train.
- Métricas (PR-AUC, ROC-AUC, F1) calculadas sobre el split temporal y comparadas
  con el baseline.
- Coeficientes revisados como lectura interpretable, validada por el Product Owner.

**Estimación:** M
**Prioridad:** Alta
**Etapa asociada:** 4
**Estado:** Completada (Etapa 4)

> **Reorientada por el pivote (D-16).** De "canal content-based de productos
> similares" a **primer clasificador de `entrega_tarde`** (Regresión Logística con
> `class_weight="balanced"`).

**Notas de cierre:**

- Regresión Logística encadenada al preprocesador de la Etapa 3 en un `Pipeline`,
  `fit` solo en train (`src/models/train.py`): PR-AUC(test) 0.111, ROC-AUC 0.665.
- Supera al baseline; queda como modelo interpretable de referencia (coeficientes).
- Los criterios de "productos similares / sanity check de catálogo" se sustituyen
  por la evaluación de clasificación sobre el split temporal (D-19).

---

### HU-10 — Implementar el canal de productos comprados juntos (collaborative)

**Como** Data Scientist,
**quiero** implementar el modelo de recomendación de productos
frecuentemente comprados juntos basado en co-ocurrencias,
**para** habilitar el cross-selling en el contexto del carrito.

**Criterios de aceptación:**

- Segundo clasificador comparable de `entrega_tarde` implementado y serializado
  (XGBoost) en un `Pipeline` con el preprocesador.
- Métricas calculadas y comparadas con el baseline y el primer modelo; selección
  del candidato por PR-AUC en validación.
- Auditoría de fuga (R-12) revisada; sanity check de negocio validado por el
  Product Owner.

**Estimación:** M
**Prioridad:** Alta
**Etapa asociada:** 4
**Estado:** Completada (Etapa 4)

> **Reorientada por el pivote (D-16).** De "canal collaborative item-based" a
> **segundo clasificador comparable** de `entrega_tarde` (XGBoost), seleccionado
> como modelo candidato del Sprint 1.

**Notas de cierre:**

- XGBoost (`xgb_d4_l2`) encadenado al preprocesador en un `Pipeline`; **modelo
  elegido** (D-27): PR-AUC(test) 0.124 (≈1.9× el azar), ROC-AUC 0.703, recall 0.346.
- Serializado en `artifacts/modelo_p1.joblib`; auditoría de fuga OK (`tasa_vendedor`
  6%). Detalle en `reports/etapa4_modelado_resultados.md`.
- La evaluación final formal y la selección definitiva quedan para HU-12 (Etapa 6).

---

### HU-11 — Ejecutar el cierre formal del Sprint 1

**Como** Scrum Master,
**quiero** ejecutar la Sprint Review y la Sprint Retrospective del
Sprint 1,
**para** validar entregables, capturar aprendizajes y preparar el
Sprint 2.

**Criterios de aceptación:**

- Sprint Review realizada con presentación del MVP.
- Acta de Sprint Review documentada en `docs/sprints/`.
- Sprint Retrospective realizada con formato acordado.
- Acta de Sprint Retrospective documentada con acciones de mejora
  asignadas a responsables.
- Tag `V1.4.0` creado en `master`.
- Backlog del Sprint 2 priorizado.

**Estimación:** M
**Prioridad:** Alta
**Etapa asociada:** 5

---

## Historias del Sprint 2

### HU-12 — Realizar la evaluación final y seleccionar el modelo

**Como** Data Scientist,
**quiero** evaluar rigurosamente los modelos del Sprint 1 con métricas
finales y seleccionar el modelo ganador,
**para** justificar técnicamente la elección que se desplegará en
producción.

**Criterios de aceptación:**

- Métricas finales calculadas: Precision@K, Recall@K, MAP@K, cobertura,
  diversidad.
- Análisis de sensibilidad a K y comportamiento por categoría.
- Análisis de cold-start documentado.
- Documento de justificación del modelo elegido (`justificacion_modelo.md`).
- Plan de validación documentado (`plan_validacion.md`).
- Artefactos finales serializados.

**Estimación:** L
**Prioridad:** Alta
**Etapa asociada:** 6

---

### HU-13 — Desplegar la API REST con FastAPI

**Como** Machine Learning Engineer,
**quiero** construir y desplegar la API REST del sistema de
recomendación,
**para** que el modelo sea consumible vía HTTP por cualquier cliente.

**Criterios de aceptación:**

- Endpoints implementados: `/health`, `/recommend/similar`,
  `/recommend/complementary`.
- Validación de entradas con Pydantic.
- Manejo de errores con códigos HTTP apropiados.
- Carga única de artefactos al iniciar la aplicación.
- Documentación Swagger UI disponible en `/docs`.

**Estimación:** M
**Prioridad:** Alta
**Etapa asociada:** 7

---

### HU-14 — Empaquetar el sistema con Docker

**Como** Machine Learning Engineer,
**quiero** empaquetar la solución completa en una imagen Docker,
**para** garantizar la reproducibilidad del despliegue en cualquier
entorno.

**Criterios de aceptación:**

- `Dockerfile` con imagen base slim y dependencias necesarias.
- `.dockerignore` configurado correctamente.
- Imagen construida y testeada localmente.
- Documentación de comandos de build y run en el README.

**Estimación:** M
**Prioridad:** Alta
**Etapa asociada:** 7

---

### HU-15 — Construir el dashboard interactivo

**Como** equipo,
**quiero** un dashboard interactivo en Streamlit para visualizar las
recomendaciones, las métricas y el comportamiento del catálogo,
**para** comunicar valor a stakeholders no técnicos.

**Criterios de aceptación:**

- Dashboard con pestañas: predicción, exploración del catálogo,
  métricas del sistema.
- Conexión funcional con la API REST.
- Cache de artefactos para minimizar latencia.
- Pruebas end-to-end del flujo completo realizadas.

**Estimación:** M
**Prioridad:** Alta
**Etapa asociada:** 7

---

### HU-16 — Implementar el componente de monitoreo

**Como** Machine Learning Engineer,
**quiero** implementar el componente de monitoreo conceptual del
sistema,
**para** verificar la salud del modelo en un escenario productivo.

**Criterios de aceptación:**

- Cálculo de PSI por feature clave implementado.
- Baseline de referencia construido a partir del periodo de
  entrenamiento.
- Reporte de drift integrado como pestaña en el dashboard.
- Validación del detector con drift inducido artificialmente.
- Documentación de la estrategia de acción según severidad.

**Estimación:** M
**Prioridad:** Media
**Etapa asociada:** 8

---

### HU-17 — Producir la documentación final del proyecto

**Como** equipo,
**quiero** producir toda la documentación final del proyecto (README,
manual de usuario, informe técnico),
**para** que el repositorio sea autocontenido y consultable por
cualquier evaluador externo.

**Criterios de aceptación:**

- `README.md` final completo con instalación, uso y arquitectura.
- Manual de usuario del sistema (`docs/manual_usuario.md`).
- Informe técnico completo (`docs/informe_tecnico.md`).
- Toda la documentación referencia correctamente los artefactos del
  repositorio.

**Estimación:** M
**Prioridad:** Alta
**Etapa asociada:** 9

---

### HU-18 — Presentar el proyecto al comité evaluador

**Como** Product Owner,
**quiero** presentar el proyecto completo al comité evaluador de
Henry,
**para** obtener la aprobación final del Proyecto Final.

**Criterios de aceptación:**

- Presentación ejecutiva preparada en formato slide.
- Demostración en vivo del sistema funcional.
- Cada miembro presenta la sección que lideró.
- Presentación realizada en la fecha establecida.
- Tag final `V1.8.0` creado en `master`.

**Estimación:** L
**Prioridad:** Alta
**Etapa asociada:** 9

---

## Resumen del backlog

| Sprint | Historias | Etapas asociadas | Estimación total |
|---|---|---|---|
| Sprint 1 | HU-01 a HU-11 | Etapas 0 a 5 | 4 S, 5 M, 2 L |
| Sprint 2 | HU-12 a HU-18 | Etapas 6 a 9 | 0 S, 5 M, 2 L |

---

## Reglas de mantenimiento del backlog

- El Product Owner es el dueño de este documento y el único que
  modifica prioridades.
- Las historias se incorporan al Sprint Backlog correspondiente en
  cada Sprint Planning.
- Las historias completadas no se eliminan; se marcan como hechas con
  el tag de versión asociado.
- Cuando surge una nueva historia durante el sprint, se añade al
  backlog para sprints futuros, no se introduce al sprint en curso.
- El backlog se revisa en cada Sprint Planning y se ajusta según los
  aprendizajes del sprint anterior.

---

*Product Backlog del Proyecto Final. Versión inicial al arranque del
proyecto. Documento vivo, actualizado durante la ejecución.*
