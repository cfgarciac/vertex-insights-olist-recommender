# Contexto previo — Etapa 3

> Documento de transferencia entre la Etapa 2 y la Etapa 3 del Proyecto
> Final. Resume el estado del proyecto al cierre de la Etapa 2 para que
> el chat dedicado a la Etapa 3 disponga de todo el contexto relevante
> sin revisar el historial completo. Documento privado de apoyo;
> destinatario principal: el responsable de la Etapa 3.

**Generado al cierre de:** Etapa 2 (2026-06-20)
**Insumo para:** Apertura de la Etapa 3 — Preparación de datos y feature engineering
**Responsable de la Etapa 3:** Data Scientist (Aguilar Lomas, Oscar Amaury)

---

## 0. Lo más importante que cambió en la Etapa 2 (léelo primero)

**El proyecto pivotó de objetivo.** El recomendador item-to-item era la hipótesis del cliente; se investigó, resultó *viable pero limitado* (co-compra 3.3%, ~97% de clientes con una sola compra, CTR no medible) y, mediante un descubrimiento estructurado, el proyecto se reorientó a:

> **P1 — Desempeño de entrega:** predecir, en el momento de la compra, si una orden llegará **tarde** respecto a la fecha prometida (`entrega_tarde`), para que Olist priorice/alerte y afine su estimación de entrega.

Esto NO es un detalle: cambia el problema, los KPIs, las features y los modelos. La Etapa 3 ya no construye matriz de co-ocurrencia ni vectores de producto; construye el **pipeline de features para clasificar `entrega_tarde`**. Decisiones clave: D-16 (pivote), D-18 (P1 y frontera P1↔P3), D-19 (KPIs/métricas), D-20 (target/universo), D-21 (leakage). item-to-item queda como hipótesis investigada, no como solución.

---

## 1. Estado general del proyecto

| Etapa | Estado | Tag asociado |
|---|---|---|
| Etapa 0 — Propuesta del PF | Cerrada | No aplica |
| Etapa 1 — Setup del repositorio | Cerrada | V1.0.0, V1.0.1, V1.0.2 |
| Etapa 2 — EDA + descubrimiento del problema | **Cerrada** | **V1.1.0** |
| Etapa 3 — Feature engineering (P1) | **A iniciar** | V1.2.0 al cierre |
| Etapa 4 — Modelado (clasificación P1) | Pendiente | V1.3.0 al cierre |
| Etapa 5 — Cierre Sprint 1 | Pendiente | V1.4.0 al cierre |
| Etapas 6 a 9 | Sprint 2 | V1.5.0 a V1.8.0 |

**Fecha límite del Sprint 1 (Etapas 2 a 5):** 2026-06-24.

---

## 2. Identidad del equipo

| Atributo | Valor |
|---|---|
| Nombre de la consultora | Vertex Insights |
| Correo institucional | equipo.vertexinsight@gmail.com |
| Repositorio | https://github.com/cfgarciac/vertex-insights-olist-recommender |

### Integrantes y roles

| Integrante | Rol | Rama personal |
|---|---|---|
| Tutalcha Pame, Harrison Alberto | Product Owner | `Harrison` |
| García Cadena, Cristian Fernando | Scrum Master | `Cristian` |
| Wessin, Nassim | Machine Learning Engineer | `Nassim` |
| Aguilar Lomas, Oscar Amaury | Data Scientist | `Amaury` |
| López Solórzano, Juan Carlos | Data Analyst | `Juan` |

> El nombre del repositorio sigue diciendo "recommender" por motivos históricos; se mantiene para no romper enlaces. El objetivo vigente es P1.

---

## 3. El problema P1 en una página (lo que necesitas para feature engineering)

**Target.** `entrega_tarde = (fecha de entrega real > fecha estimada)`, definido contra la promesa. Universo: órdenes `delivered` (las no entregadas se tratan aparte). Tasa base ≈ **8.1%** (desbalance sano). Alternativa continua: `dias_vs_promesa`.

**Disciplina de leakage (crítica).** El modelo predice en **t0** (compra/aprobación). Solo se usan features **[t0]**; la fecha de entrega real y derivados son **[POST]** (solo etiquetan).

**Shortlist de features [t0] (D-21), ya explorado en el EDA:**

- `dias_prometidos` (fecha estimada − compra).
- Distancia *haversine* comprador↔vendedor (desde `geolocation`); `mismo_estado`.
- `ratio_flete` (flete/valor) — driver débil pero [t0].
- Producto: peso, volumen, categoría.
- Estacionalidad: mes/día de compra (cuidado con el incidente 2018 — R-14).
- **Tasa histórica de entrega tardía del vendedor**, calculada sin fuga (ventana a fijar; ver abajo).

**Hallazgos del EDA que condicionan el FE:**

- La promesa lleva un **colchón mediano de 12 días**; el dolor vive en la cola que se queda corta. La palanca de negocio es afinar la estimación.
- El dolor es **regional**: Norte/Nordeste sufre ~4× más que São Paulo (AL 23.9% vs SP 5.9%). La distancia sube la tardanza pero suave.
- El vendedor mueve la tardanza → su tasa histórica es señal útil y legítima.
- Correlaciones [t0] moderadas y multifactoriales (ninguna feature domina): el modelo necesitará varias.
- Multicolinealidad esperada: `dist_km`↔`mismo_estado`, peso↔volumen.

**Decisión pendiente de FE — ventana del vendedor.** El EDA incluye un análisis de sensibilidad de la ventana (toda la historia *expanding* vs. últimas N órdenes), midiendo cobertura vs. poder de separación. La recomendación preliminar es *expanding* con un mínimo de órdenes previas, con respaldo a la tasa global cuando no hay historial. Confírmalo con los números del notebook `02_EDA_VERTEX.ipynb`.

---

## 4. Backlog para la Etapa 3

Historia en alcance: **HU-07 — Preparar los datos y construir el pipeline de features de P1**, ya reescrita en `product_backlog.md` (Estimación L, Prioridad Alta). Criterios principales: tabla analítica a nivel orden (universo `delivered`), target `entrega_tarde`, features [t0] del shortlist, tasa histórica del vendedor **sin fuga**, imputación documentada, encodings, pipeline con `Pipeline`/`ColumnTransformer`, **split temporal** sin leakage y pipeline serializado en `artifacts/`.

> Las HU-08 a HU-18 (modelado, evaluación, despliegue) quedan pendientes de redefinición formal por el PO tras el pivote; ver la nota de impacto en `product_backlog.md`.

---

## 5. Decisiones registradas hasta el cierre de la Etapa 2

| ID | Título | Estado |
|---|---|---|
| D-01 | Selección del dataset Olist | Aceptada |
| D-02 | Tipo de sistema de recomendación (item-to-item) | **Reemplazada por D-16** |
| D-03 | KPIs (CTR y AOV) | **Reemplazada por D-19** |
| D-04 a D-08 | Roles, stack, repo, versionado, GitHub Projects | Aceptadas |
| D-09 | Evaluación offline por partición temporal | Propuesta (reforzada por P1) |
| D-10 a D-15 | Gestión, identidad, propuesta, tablero, licencia, issue template | Aceptadas |
| **D-16** | Pivote a P1 (predicción de entrega tardía) | Aceptada |
| **D-17** | Metodología de descubrimiento (embudo Descubrimiento–DVA) | Aceptada |
| **D-18** | Selección de P1; frontera P1↔P3 | Aceptada |
| **D-19** | Redefinición de KPIs y métricas | Aceptada |
| **D-20** | Definición del target y del universo de P1 | Aceptada |
| **D-21** | Disciplina anti-leakage y shortlist de features [t0] | Aceptada |

---

## 6. Riesgos activos relevantes para la Etapa 3

| ID | Título | Nivel | Estado | Relevancia en Etapa 3 |
|---|---|---|---|---|
| R-12 | Data leakage en la predicción de entrega tardía | Alto | Activo | **Máxima** — el FE debe separar [t0] de [POST] |
| R-14 | Cambio de régimen temporal / incidente 2018 | Medio | Activo | Alta — afecta el split temporal y la estacionalidad |
| R-07 | Calidad de datos (categorías, atributos, geo) | Medio | Activo | Alta — define la estrategia de imputación |
| R-02 | Duración corta vs alcance | Alto | Activo | Alta — vigilar el tiempo de HU-07 (L) |
| R-13 | Alineación del pivote con la propuesta aprobada | Alto | Activo | Media — el PO comunica al mentor |
| R-09 | Drift entre ramas personales | Medio | Activo | Media — disciplina de sincronización |

R-01 (sparsity) quedó **cerrado** por el pivote.

---

## 7. Estado del repositorio al inicio de la Etapa 3

- Repositorio público, licencia MIT, estructura estándar de ML.
- Ramas largas activas: `master`, `developer`, `Cristian`, `Harrison`, `Juan`, `Amaury`, `Nassim`.
- Tags publicados: hasta **V1.1.0** (cierre de Etapa 2).
- Documentación vigente: `docs/convenciones.md`, `docs/etapas/cierre-etapa-0.md`, `cierre-etapa-1.md`, `cierre-etapa-2.md`, los documentos vivos (`bitacora_decisiones.md`, `product_backlog.md`, `registro_riesgos.md`) y el `Problem Discovery & DVA Report`.
- Notebooks en `notebooks/`: `dva.ipynb`, `discovery_nivel2.ipynb`, `nivel_2_dva.ipynb`, `02_EDA_VERTEX.ipynb`, `01_eda_olist.ipynb`.

---

## 8. Convenciones operativas vigentes

- **Commits:** Conventional Commits (`feat`, `fix`, `docs`, `chore`, etc.).
- **Trabajo:** cada integrante en su rama personal; PR hacia `developer` con título `[HU-NN] Descripción` y un revisor distinto al autor.
- **Sincronización:** pull diario de `developer` hacia la rama personal.
- **Definition of Done:** criterios cumplidos, código mergeado a `developer`, documentación actualizada, pruebas pasando (cuando aplique), issue cerrado.
- **Subcarpetas del DS:** `notebooks/modelado/`, `src/recommender/` (renómbralo si conviene a `src/p1/` o `src/delivery/` — decisión menor a coordinar).

---

## 9. Enfoque pragmático del proyecto

- Scrum como marco de referencia, no aplicado ceremonialmente.
- Las comunicaciones formales se documentan, no se ejecutan si no aportan valor.
- Foco: entregables visibles en GitHub y en el tablero, cierre de etapa documentado.
- **Confirmación previa antes de generar artefactos** (planificar el plan, validar, luego ejecutar).

---

## 10. Pendientes administrativos al inicio de la Etapa 3

- **Comunicar el pivote al mentor** (responsabilidad del PO; riesgo R-13).
- Confirmar el estado real de HU-06 (informe Power BI) antes de dar por publicado el cierre de Etapa 2.
- Verificar acceso de colaboradores al repositorio para todo el equipo.

---

## 11. Salida esperada al cierre de la Etapa 3

- Script/notebook de feature engineering reproducible en `src/`/`notebooks/`.
- Tabla analítica de P1 a nivel orden con el target y los features [t0].
- Pipeline serializado (`artifacts/pipeline_p1.pkl` o equivalente).
- Split temporal definido y validado sin leakage.
- Documento de decisiones de feature engineering (`docs/decisiones_fe.md`), incluyendo la ventana del vendedor elegida y la estrategia de imputación.
- Documento público `docs/etapas/cierre-etapa-3.md` y tag `V1.2.0`.
- HU-07 cerrada como Done; documentos vivos actualizados.
- Documentos privados de la Etapa 4: `contexto_previo_etapa_4.md` y `etapa_4_guia.md`.

---

*Documento de contexto previo de la Etapa 3 del Proyecto Final. Generado al cierre de la Etapa 2.*
