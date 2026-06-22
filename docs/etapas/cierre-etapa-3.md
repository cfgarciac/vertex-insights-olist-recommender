# Cierre de la Etapa 3 — Preparación de datos y feature engineering (P1)

## Vertex Insights — Proyecto Final

**Fecha de cierre:** 2026-06-20
**Sprint asociado:** Sprint 1
**Fase CRISP-DM:** Data Preparation (centro)
**Tag de versión:** V1.2.0
**Líder de etapa:** Data Scientist (Aguilar Lomas, Oscar Amaury)

---

## 1. Contexto y objetivos de la etapa

La Etapa 3 es el corazón de la fase **Data Preparation** de CRISP-DM. Su objetivo
fue convertir los hallazgos del EDA (Etapa 2) en una **tabla analítica modelable**
y un **pipeline reproducible** para el problema vigente **P1 — predicción de
entrega tardía** (`entrega_tarde`), sin reabrir el pivote ya decidido en la
Etapa 2.

El objetivo se cumplió: se entregó la tabla analítica a nivel orden con el target
y las features [t0], el pipeline de preprocesamiento serializado, el split
temporal sin leakage y un EDA breve que evidencia los cambios del ETL+FE. La
disciplina anti-leakage (R-12) fue el eje rector de la etapa.

---

## 2. Equipo y roles activos durante la etapa

| Rol | Integrante | Participación |
|---|---|---|
| Data Scientist | Aguilar Lomas, Oscar Amaury | Carga alta — diseño y construcción del pipeline de features, target, tasa del vendedor sin fuga, split temporal, serialización |
| Machine Learning Engineer | Wessin, Nassim | Apoyo técnico — estructura de `ColumnTransformer`/`Pipeline`, reproducibilidad |
| Data Analyst | López Solórzano, Juan Carlos | Apoyo — shortlist de features y lógica de negocio; sanity check del gradiente regional |
| Product Owner | Tutalcha Pame, Harrison Alberto | Validación de la tabla contra la pregunta de negocio; comunicación del pivote al mentor (R-13) |
| Scrum Master | García Cadena, Cristian Fernando | Coordinación y cierre formal de la etapa |

---

## 3. Historias de usuario completadas

| ID | Título | Responsable | Estado |
|---|---|---|---|
| HU-07 | Preparar los datos y construir el pipeline de features de P1 (entrega tardía) | Data Scientist | Completada |

Las notas de cierre de la historia están en `product_backlog.md`.

---

## 4. Productos entregados

- **Script reproducible de ETL + feature engineering** (`src/features/build_dataset.py`):
  parte del CSV consolidado, colapsa a nivel orden sobre `delivered`, construye el
  target y las features [t0], calcula la tasa del vendedor sin fuga, ajusta el
  preprocesador solo en train y serializa el pipeline.
- **Tabla analítica de P1** (`vertex_files/orders_p1_features.csv`): 96,470
  órdenes × 21 columnas (identificadores, split, target, features [t0]).
- **Pipeline de preprocesamiento serializado** (`artifacts/pipeline_p1.joblib`):
  `ColumnTransformer` (escalado/encoding/imputación) ajustado solo en train, más
  metadatos (listas de features, target, parámetros).
- **EDA breve de cambios** (`notebooks/03_EDA_VERTEX.ipynb`): gráficas de
  antes/después del ETL+FE (granularidad/universo, target, gradiente regional,
  features nuevas, nulos resueltos, split temporal y régimen 2018). Las 7 figuras
  se exportan a `reports/figures_eda_etapa3/` (PNG a 150 dpi) para reutilizarse en
  informes.
- **Documento técnico de feature engineering** (`docs/decisiones_fe.md`):
  catálogo de features, ventana del vendedor, imputación, encodings, split y
  multicolinealidad.
- **Documentos vivos actualizados:** `bitacora_decisiones.md` (D-22 a D-26),
  `product_backlog.md` (HU-07 en Done), `registro_riesgos.md` (R-12 mitigado en
  esta etapa).

---

## 5. Decisiones tomadas durante la etapa

Registradas en `bitacora_decisiones.md`:

- **D-22** — Fuente del feature engineering: CSV consolidado en vez de las 9
  tablas crudas.
- **D-23** — Granularidad a nivel orden con vendedor/producto principal = primer
  ítem; importes/peso/volumen agregados.
- **D-24** — Ventana de la tasa histórica del vendedor: *expanding* point-in-time,
  mínimo 5 órdenes, respaldo a la tasa global del train + flag.
- **D-25** — Split temporal 70/15/15 por fecha de compra.
- **D-26** — Imputación con sentido de negocio + pipeline serializado
  (`ColumnTransformer`).

---

## 6. Resultados y verificaciones clave

| Métrica de la etapa | Valor |
|---|---|
| Órdenes en la tabla analítica (`delivered`, etiquetables) | 96,470 |
| Tasa base `entrega_tarde` | 8.11% |
| Split temporal (train / val / test) | 67,529 / 14,470 / 14,471 |
| Tasa global del vendedor (respaldo, train) | 9.03% |
| Órdenes sin historial suficiente del vendedor | 11.57% |
| Distancia haversine nula (geo faltante, imputada en pipeline) | 476 (0.49%) |
| Prueba anti-fuga de la tasa del vendedor | OK |
| Sanity check regional (SP vs AL) | 5.9% vs 23.9% (≈4×) |

El gradiente regional y el colchón de la promesa del EDA de la Etapa 2 se
reproducen sobre las features construidas, lo que confirma que el FE preserva la
señal de negocio.

> **Nota sobre los nulos de la distancia.** El 0.49% (476) de `dist_haversine_km`
> nula es la **unión** de los huecos de geo cliente (0.27%) y geo vendedor (0.22%):
> la distancia es nula si falta cualquiera de los dos extremos. **No es un
> deterioro** de la geo del vendedor; la comparación antes/después a nivel orden
> confirma que el porcentaje no aumenta. El `NaN` se conserva en el CSV y lo
> imputa el pipeline (mediana en train).

---

## 7. Riesgos detectados o materializados

Registrados en `registro_riesgos.md`:

- **R-12** (data leakage en P1) — **mitigado en esta etapa**: separación [t0]/[POST]
  aplicada como checklist, tasa del vendedor point-in-time con prueba anti-fuga,
  split temporal y preprocesador ajustado solo en train. Sigue vigente como
  vigilancia en la Etapa 4.
- **R-14** (régimen temporal / incidente 2018) — activo: se inspeccionó la tasa
  mensual; el periodo se conserva completo y la cola final queda como punto de
  vigilancia para el modelado.
- **R-07** (calidad de datos) — atendido con la estrategia de imputación
  documentada; sigue activo como vigilancia.
- **R-02** (tiempo vs alcance) — controlado: partir del CSV consolidado (D-22)
  redujo el esfuerzo de integración.

---

## 8. Variaciones respecto al plan original

La guía de la Etapa 3 preveía partir de las **nueve tablas crudas** y construir
desde ahí. En la práctica se partió del **CSV consolidado** (`orders_consolidated.csv`),
que ya integra las uniones validadas en el EDA. La variación se documenta como
decisión **D-22** y no altera el resultado esperado (tabla analítica + pipeline +
split): solo evita repetir el trabajo de unión y reduce el riesgo de *fan-out*,
en línea con la presión de tiempo del Sprint 1 (R-02).

El artefacto de salida principal pedido por el responsable de la etapa fue un
**CSV de features** en `vertex_files/`; adicionalmente se serializó el **pipeline
de preprocesamiento** en `artifacts/`, como pedía la guía, para que la Etapa 4 lo
consuma sin recalcular parámetros.

---

## 9. Lecciones aprendidas

- **El leakage se previene por construcción, no por revisión.** La tasa del
  vendedor point-in-time con una prueba anti-fuga automática es más fiable que
  auditar el resultado a posteriori.
- **Imputar con la causa del hueco en mente.** Geo, vendedor nuevo y dimensiones
  faltantes piden estrategias distintas; un `fillna(0)` global habría borrado
  señal.
- **Una feature derivada hereda la unión de los huecos de sus fuentes.** Los
  nulos de la distancia (0.49%) parecían "más" que los del vendedor (0.22%), pero
  son la suma de geo cliente + vendedor; comparar siempre a la misma granularidad
  (nivel orden) evita falsos diagnósticos de deterioro.
- **El split temporal es parte del feature engineering, no un paso posterior.**
  La tasa global de respaldo y el preprocesador se ajustan solo en train; el orden
  importa.
- **Reusar trabajo validado acelera sin perder rigor.** Partir del consolidado fue
  una decisión de tiempo razonable y trazable.

---

## 10. Estado de los documentos vivos al cierre

- `product_backlog.md`: HU-07 marcada como Completada con notas de cierre.
- `bitacora_decisiones.md`: D-22 a D-26 agregadas.
- `registro_riesgos.md`: R-12 actualizado a Mitigado (con vigilancia en Etapa 4);
  nota de Etapa 3 en R-14 y R-07.
- `guia_proyecto_final_olist.md`: actualizada con el cierre de la Etapa 3 y el
  estado de artefactos.
- `docs/decisiones_fe.md`: documento técnico de feature engineering publicado.

---

## 11. Próximos pasos

La **Etapa 4 — Modelado (clasificación de P1)** arranca con la tabla analítica y
el pipeline de preprocesamiento ya listos. Toma como insumo el split temporal y la
disciplina anti-leakage de esta etapa. Foco: añadir el estimador al `Pipeline`,
entrenar un baseline y modelos (regresión logística, árboles/boosting), evaluar
con ROC-AUC/PR-AUC/F1 (D-19) sobre el split temporal, y vigilar la `tasa_vendedor`
y el régimen 2018.

Responsable primario de la Etapa 4: **Data Scientist (Aguilar Lomas, Oscar
Amaury)**, con apoyo del ML Engineer. Tag esperado al cierre: **V1.3.0**.

---

*Cierre formal de la Etapa 3 del Proyecto Final, equipo Vertex Insights — Carrera Data Science de Henry.*
