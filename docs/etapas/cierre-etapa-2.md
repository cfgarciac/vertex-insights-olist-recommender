# Cierre de la Etapa 2 — Entendimiento del negocio y análisis exploratorio (EDA)

## Vertex Insights — Proyecto Final

**Fecha de cierre:** 2026-06-20
**Sprint asociado:** Sprint 1
**Fase CRISP-DM:** Business Understanding (refinamiento) + Data Understanding
**Tag de versión:** V1.1.0
**Líder de etapa:** Data Analyst (López Solórzano, Juan Carlos), con el Data Scientist (Aguilar Lomas, Oscar Amaury)

---

## 1. Contexto y objetivos de la etapa

La Etapa 2 es la primera etapa de desarrollo técnico del proyecto. Se planteó como el entendimiento profundo de las nueve tablas de Olist para identificar problemas de calidad, distribuciones y oportunidades, validar la viabilidad del enfoque propuesto y producir el insumo formal para el feature engineering.

El objetivo se cumplió, pero con una **variación de fondo respecto al plan**: el EDA no solo describió los datos, sino que **puso a prueba la hipótesis del cliente** (el recomendador item-to-item) y, al hallarla viable pero limitada, derivó en un **descubrimiento estructurado del problema** que reorientó el proyecto a **P1 — Desempeño de entrega**. Esta variación está documentada en detalle en la sección 7.

---

## 2. Equipo y roles activos durante la etapa

| Rol | Integrante | Participación |
|---|---|---|
| Data Analyst | López Solórzano, Juan Carlos | Carga alta — EDA exhaustivo, descubrimiento del problema, EDA enfocado de P1 |
| Data Scientist | Aguilar Lomas, Oscar Amaury | EDA con geolocalización; entendimiento del problema; co-decisión del pivote |
| Product Owner | Tutalcha Pame, Harrison Alberto | Validación de hallazgos contra el caso de negocio; validación del pivote |
| Scrum Master | García Cadena, Cristian Fernando | Coordinación y cierre formal de la etapa |
| ML Engineer | Wessin, Nassim | Preparación de entorno para la Etapa 3 |

> Nota de roles: se confirma **Juan Carlos = Data Analyst** y **Nassim = ML Engineer**, de acuerdo con `cierre-etapa-0.md` y la asignación de HU. La guía maestra, que los listaba invertidos, se corrigió en esta etapa.

---

## 3. Historias de usuario completadas

| ID | Título | Responsable | Estado |
|---|---|---|---|
| HU-04 | Entender el problema y los datos disponibles | Data Scientist | Completada (reorientada a P1) |
| HU-05 | Análisis exploratorio profundo de las nueve tablas | Data Analyst | Completada (incluye descubrimiento + EDA de P1) |
| HU-06 | Informe exploratorio en Power BI | Data Analyst | Completada (vistas reorientadas a P1) |

Las notas de cierre de cada historia están en `product_backlog.md`.

> **Pendiente de confirmación (HU-06):** el estado y la ubicación del archivo `.pbix` y la validación formal del PO deben verificarse antes de dar por publicado este cierre.

---

## 4. Productos entregados

- **Notebooks de exploración y descubrimiento** (`notebooks/`):
  - `dva.ipynb` — exploración de las 9 tablas + bloque de reviews/drivers (Nivel 2 del embudo).
  - `discovery_nivel2.ipynb` y `nivel_2_dva.ipynb` — confirmación con código de los drivers (entrega, vendedor, flete, geografía).
  - `02_EDA_VERTEX.ipynb` — **EDA enfocado de P1**, consolidado y reorientado: calidad de datos, *target* `entrega_tarde`, error de estimación (colchón), drivers [t0], geoespacial (haversine), magnitud económica, matriz de correlaciones y mapa de leakage.
  - `01_eda_olist.ipynb` — EDA inicial del recomendador (registro del planteamiento original, no del rumbo vigente).
- **Problem Discovery & Data Viability Report** (`docs/`) — registro narrativo del descubrimiento (por qué se pivotó, el embudo, la elección de P1). Cumple el rol del `eda_hallazgos.md` planeado, reorientado a P1.
- **Documentos vivos actualizados:** `bitacora_decisiones.md` (D-16 a D-21), `registro_riesgos.md` (R-01 cerrado; R-12 a R-14 nuevos), `product_backlog.md` (HU-04/05/06 cerradas; HU-07 reescrita; nota de impacto del pivote).
- **Informe Power BI** (`reports/`) — reorientado a la narrativa de P1.

---

## 5. Decisiones tomadas durante la etapa

Registradas en `bitacora_decisiones.md`:

- **D-16** — Pivote del objetivo: de recomendador item-to-item a predicción de entrega tardía (P1). *(Reemplaza D-02.)*
- **D-17** — Metodología de descubrimiento del problema (embudo Descubrimiento–DVA).
- **D-18** — Selección de P1 sobre P2 y P3; frontera P1↔P3 (el vendedor entra como feature).
- **D-19** — Redefinición de KPIs y métricas (tasa de entrega a tiempo, GMV expuesto, métricas de clasificación). *(Reemplaza D-03.)*
- **D-20** — Definición del *target* (`entrega_tarde`) y del universo de análisis (`delivered`; no entregadas aparte).
- **D-21** — Disciplina anti-leakage y *shortlist* de features [t0].

---

## 6. Riesgos detectados o materializados

Registrados en `registro_riesgos.md`:

- **R-01** (sparsity) — **Cerrado**: la sparsity se confirmó y fue una de las razones del pivote; P1 no usa la matriz cliente-producto, así que deja de ser relevante.
- **R-07** (calidad de datos) — sigue activo; el EDA cuantificó nulos y cobertura geo, con estrategia de imputación propuesta para la Etapa 3.
- **R-12** (data leakage en P1) — nuevo, Alto. Riesgo central del nuevo objetivo.
- **R-13** (alineación del pivote con la propuesta aprobada) — nuevo, Alto. Requiere que el PO comunique el cambio al mentor.
- **R-14** (cambio de régimen temporal / incidente 2018) — nuevo, Medio. Afecta el *split* temporal y la generalización.

---

## 7. Variaciones respecto al plan original

Esta etapa tuvo la variación más importante del proyecto hasta ahora. Se documenta en tres lugares (bitácora, backlog/riesgos y este cierre), como exige la guía de actualización de documentos.

**Qué se desvió.** El plan de la Etapa 2 (guía de etapa) preveía un EDA descriptivo para alimentar un recomendador item-to-item, con mapeo de KPIs CTR/AOV e hipótesis de modelado del recomendador. En la práctica:

1. **Se probó la hipótesis del cliente y se halló su techo.** El recomendador resultó viable pero limitado: co-compra del 3.3%, ~97% de clientes con una sola compra y ausencia de datos de navegación (CTR no medible). La sparsity (R-01) se materializó como límite estructural, no como detalle a mitigar.
2. **Se ejecutó un descubrimiento estructurado** (embudo Descubrimiento–DVA, D-17): de 12 dolores a 5 candidatos (P1–P5), filtrados por tres compuertas. El razonamiento completo está en el *Problem Discovery & DVA Report*.
3. **Se eligió P1 — Desempeño de entrega** (D-16, D-18). Es el único candidato con *target* limpio (`entrega_tarde`), completable end-to-end, con un artefacto que el cliente usaría, y con valor real (≈R$1.1M de GMV expuesto, dolor regional en el Norte/Nordeste). La frontera con P3 (vendedores) se resolvió: el vendedor entra como *feature*, no como segundo problema.
4. **Se redefinieron KPIs y métricas** (D-19, reemplaza D-03) y se fijaron el *target* y la disciplina anti-leakage (D-20, D-21).

**Por qué se manejó así y no se ocultó.** El proyecto simula una consultora de datos: probar la solución que pide el cliente y, con evidencia, proponer un dolor mayor es exactamente el valor de una consultora. item-to-item **no es trabajo perdido**: queda como la hipótesis investigada (el gancho de la narrativa). La divergencia respecto a la propuesta aprobada se registra como riesgo R-13, cuya mitigación es que el PO comunique y justifique el cambio al mentor de forma temprana.

**Impacto en el backlog.** Las historias HU-07 a HU-18, escritas para el recomendador, se realinean a P1. HU-07 (feature engineering) ya se reescribió; HU-08 a HU-18 quedan pendientes de redefinición formal por el PO, con el mapeo propuesto en la nota de impacto del backlog.

---

## 8. Lecciones aprendidas

- **No asumir la solución.** Investigar la hipótesis del cliente antes de comprometerse evitó construir un recomendador de techo bajo y reveló un dolor de mayor valor.
- **El esquema de datos es un fósil de prioridades.** Leer qué midió Olist (fecha estimada vs. real, reseñas, geolocalización) orientó el descubrimiento mejor que la intuición.
- **El leakage es el riesgo metodológico central de P1.** Separar features [t0] de variables [POST] desde el EDA es lo que hará el modelo honesto y desplegable.
- **Documentar la divergencia da credibilidad.** Un proyecto con un pivote bien justificado es más fuerte ante un evaluador que uno que finge no haberse desviado.

---

## 9. Estado de los documentos vivos al cierre

- `product_backlog.md`: HU-04, HU-05 y HU-06 marcadas como Completada; HU-07 reescrita para P1; nota de impacto del pivote sobre HU-08 a HU-18 (pendientes de redefinición por el PO).
- `bitacora_decisiones.md`: D-16 a D-21 agregadas; D-02 y D-03 marcadas como Reemplazadas.
- `registro_riesgos.md`: R-12, R-13 y R-14 agregadas; R-01 actualizado a Cerrado; R-07 con nota de Etapa 2.
- `guia_proyecto_final_olist.md`: actualizada en objetivo, KPIs, alcance y roster de roles, con recuadro de pivote.

---

## 10. Próximos pasos

La **Etapa 3 — Preparación de datos y feature engineering** arranca con el nuevo objetivo. Toma como insumo el *shortlist* de features [t0] (D-21) y el mapa de leakage del EDA de P1. Foco: construir la tabla analítica a nivel orden, el *target* `entrega_tarde`, la tasa histórica del vendedor sin fuga (con la ventana definida según la sensibilidad ya explorada), los encodings e imputaciones, el *split* temporal y el pipeline serializado.

Responsable primario de la Etapa 3: **Data Scientist (Aguilar Lomas, Oscar Amaury)**, con apoyo del Data Analyst (limpieza basada en hallazgos del EDA) y del ML Engineer (arquitectura de pipelines). Tag esperado al cierre: **V1.2.0**.

---

*Cierre formal de la Etapa 2 del Proyecto Final, equipo Vertex Insights — Carrera Data Science de Henry.*
