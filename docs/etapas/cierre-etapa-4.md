# Cierre de la Etapa 4 — Modelado (clasificación de P1, entrega tardía)

## Vertex Insights — Proyecto Final

**Fecha de cierre:** 2026-06-21
**Sprint asociado:** Sprint 1
**Fase CRISP-DM:** Modeling
**Tag de versión:** V1.3.0
**Líder de etapa:** Machine Learning Engineer (Wessin, Nassim)

---

## 1. Contexto y objetivos de la etapa

La Etapa 4 es la fase **Modeling** de CRISP-DM. Su objetivo fue convertir la tabla
analítica de la Etapa 3 en **modelos entrenados y comparables** que predicen
`entrega_tarde` en t0, evaluarlos honestamente sobre el split temporal y seleccionar
un candidato para el cierre del Sprint 1. La etapa **no rehace feature engineering ni
el split** (cerrados en la Etapa 3): añade el estimador al preprocesador y mide.

El objetivo se cumplió: se entrenaron un baseline y dos familias de clasificadores
encadenados al preprocesador serializado, se evaluaron con las métricas de D-19
(PR-AUC, ROC-AUC, F1, calibración), se auditó la fuga (R-12) y se analizaron los
errores por región y *cold-start*. Se seleccionó **XGBoost** como modelo candidato.

> **Variación de plan de equipo:** la guía maestra asignaba el modelado al Data
> Scientist; en la práctica lo ejecutó el **ML Engineer (Nassim)** tras el relevo de
> la Etapa 3 (Amaury → Nassim). Se documenta aquí y en el contexto de la Etapa 5.

---

## 2. Equipo y roles activos durante la etapa

| Rol | Integrante | Participación |
|---|---|---|
| Machine Learning Engineer | Wessin, Nassim | Carga alta — estructura de entrenamiento reproducible, baseline + clasificadores, evaluación, serialización, cierre de la etapa |
| Data Scientist | Aguilar Lomas, Oscar Amaury | Relevo de la Etapa 3 (insumos: tabla analítica + pipeline); revisor técnico |
| Data Analyst | López Solórzano, Juan Carlos | Apoyo — lectura de negocio de los errores por región y *cold-start* |
| Product Owner | Tutalcha Pame, Harrison Alberto | Validación de coherencia con la pregunta de negocio; formalización pendiente de HU-08 a HU-12 |
| Scrum Master | García Cadena, Cristian Fernando | Coordinación y cierre del Sprint 1 (Etapa 5) |

---

## 3. Historias de usuario completadas

| ID | Título (reorientado a P1) | Responsable | Estado |
|---|---|---|---|
| HU-08 | Baseline de clasificación (piso de comparación) | ML Engineer | Completada |
| HU-09 | Primer clasificador de `entrega_tarde` (Regresión Logística) | ML Engineer | Completada |
| HU-10 | Segundo clasificador comparable (XGBoost) | ML Engineer | Completada |

Las notas de cierre están en `product_backlog.md`. **HU-12 (evaluación final y
selección definitiva)** pertenece a la Etapa 6 (Sprint 2): aquí se hizo la evaluación
**comparativa preliminar** que la alimenta, pero HU-12 **no se cierra** en esta etapa.

---

## 4. Productos entregados

- **Estructura de entrenamiento reproducible** (`src/models/`): `baseline.py`
  (clase mayoritaria + regla de negocio), `train.py` (carga, rejilla por familia,
  selección por PR-AUC en val, umbral operativo, serialización) y `evaluate.py`
  (métricas, análisis por región/cold-start, auditoría de fuga, graficado).
- **Modelo candidato serializado** (`artifacts/modelo_p1.joblib`): `Pipeline`
  completo (preprocesador de la Etapa 3 + XGBoost), umbral operativo y metadatos.
- **Reporte de resultados** (`reports/etapa4_modelado_resultados.md`) y **métricas
  reproducibles** (`reports/etapa4_metrics.json`).
- **Figuras** (`reports/figures_modelado_etapa4/`): curvas PR/ROC, calibración,
  importancias y error por región (PNG 150 dpi).
- **Notebook de modelado** (`notebooks/04_modelado_VERTEX.ipynb`): narrativa
  reproducible del baseline, los modelos, la evaluación y el análisis de errores.
- **Pruebas** (`tests/test_models.py`): entrenamiento, serialización, candado
  anti-fuga y "supera al baseline" (5 tests, en verde).
- **Documentos vivos actualizados:** `bitacora_decisiones.md` (D-27 a D-29),
  `product_backlog.md` (HU-08/09/10 en Done), `registro_riesgos.md` (R-12 auditado,
  R-14 observado), `convenciones.md` (tag V1.3.0 reencuadrado a P1).

---

## 5. Decisiones tomadas durante la etapa

Registradas en `bitacora_decisiones.md`:

- **D-27** — Selección de **XGBoost** (`xgb_d4_l2`) como modelo candidato de P1, por
  PR-AUC en validación temporal (sobre Regresión Logística).
- **D-28** — Política de **umbral operativo** (dos puntos: F1-óptimo y alta cobertura
  recall≈0.5) y manejo del **desbalance** (`scale_pos_weight`/`class_weight`);
  calibración formal diferida a la Etapa 6.
- **D-29** — Tratamiento del **cambio de régimen temporal (R-14)** en el modelado:
  conservar el periodo completo, reportar la caída de tasa base train→test y diferir
  el re-ventaneo a la Etapa 6.

---

## 6. Resultados y verificaciones clave

**Métricas en TEST (umbral F1 fijado en val):**

| Modelo | PR-AUC | ROC-AUC | Recall | Precision | Brier |
|---|---|---|---|---|---|
| Baseline clase mayoritaria | 0.066 | 0.500 | — | — | 0.062 |
| Baseline regla | 0.052 | 0.340 | 0.111 | 0.052 | 0.349 |
| Regresión Logística | 0.111 | 0.665 | 0.234 | 0.104 | 0.296 |
| **XGBoost (elegido)** | **0.124** | **0.703** | 0.346 | 0.132 | 0.186 |

| Verificación de la etapa | Valor |
|---|---|
| Tasa base `entrega_tarde` (total / train / val / test) | 8.11% / 9.03% / 5.34% / 6.61% |
| PR-AUC del modelo vs azar (test) | 0.124 vs 0.066 (≈ 1.9×) |
| Punto de alta cobertura (umbral 0.468) | recall 0.63 · precision 0.118 |
| Peso de `tasa_vendedor` en el modelo (auditoría de fuga) | 6.0% (sin fuga) |
| Recall por región (Nordeste / Norte / Sudeste) | 0.83 / 0.56 / 0.30 |
| Cold-start vs con historial (ROC-AUC) | 0.722 vs 0.701 |
| Pruebas `pytest` | 5/5 en verde |

El modelo reproduce la narrativa del EDA (geografía, cruce de estado, vendedor,
estacionalidad), sin métricas sospechosas: resultado honesto y defendible para un MVP
de Sprint 1.

---

## 7. Variaciones respecto al plan original

- **Recomendador → clasificación P1.** Las HU-08/09/10, escritas para el recomendador
  (popularidad, content-based, collaborative), se realinearon a P1 (baseline de
  clasificación + dos clasificadores de `entrega_tarde`), según la "Nota de impacto
  del pivote" del backlog y D-16.
- **Responsable de la etapa.** El modelado lo ejecutó el ML Engineer (Nassim) en vez
  del Data Scientist, por el relevo Etapa 3 → Etapa 4. Sin impacto en los entregables.
- **HU-12** (evaluación final) permanece en la Etapa 6 (Sprint 2); aquí se entregó la
  comparación preliminar que la alimenta.

---

## 8. Lecciones aprendidas

- **El split temporal cuenta una verdad incómoda y útil.** La tasa base cae de 9.0%
  (train) a 6.6% (test): el modelo se evalúa en un régimen distinto al de
  entrenamiento (R-14). Verlo en las métricas es más honesto que esconderlo con CV
  aleatoria.
- **Una heurística "razonable" puede ser anti-informativa.** La regla
  distancia+estado dio ROC-AUC 0.34 en test: el piso correcto lo fija un baseline
  trivial, y el valor del modelo se mide contra él.
- **Regularizar generaliza.** El XGBoost menos profundo y más regularizado superó al
  más complejo en val y test: con desbalance y cambio de régimen, menos es más.
- **La auditoría de fuga se diseña, no se improvisa.** El candado anti-[POST] y la
  baja importancia de `tasa_vendedor` (6%) dan confianza en que el 0.70 de ROC-AUC es
  real.

---

## 9. Estado de los documentos vivos al cierre

- `product_backlog.md`: HU-08, HU-09 y HU-10 marcadas como Completada con notas de
  cierre reorientadas a P1.
- `bitacora_decisiones.md`: D-27 a D-29 agregadas.
- `registro_riesgos.md`: R-12 actualizado (auditado en Etapa 4, sin fuga); R-14
  actualizado (régimen observado en test; re-ventaneo diferido a Etapa 6).
- `convenciones.md`: fila del tag V1.3.0 reencuadrada a P1.
- `docs/etapas/cierre-etapa-4.md`: este documento.

---

## 10. Próximos pasos

La **Etapa 5 — Cierre del Sprint 1** la lidera el **Scrum Master (Cristian)** con
HU-11: Sprint Review (demostrar el MVP predictivo), Sprint Retrospective, cierre
documental y tag **V1.4.0**. El modelo candidato (`artifacts/modelo_p1.joblib`) y este
reporte son el insumo del MVP a mostrar.

Pendientes que entran al Sprint 2 (Etapa 6, HU-12): evaluación final con calibración
formal, selección definitiva del umbral con el PO y decisión sobre el re-ventaneo
temporal (R-14).

Responsable primario de la Etapa 5: **Scrum Master (García Cadena, Cristian
Fernando)**. Tag esperado al cierre del Sprint 1: **V1.4.0**.

---

*Cierre formal de la Etapa 4 del Proyecto Final, equipo Vertex Insights — Carrera Data Science de Henry.*
