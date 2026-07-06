# Cierre de la Etapa 8 — Monitoreo y documentación técnica

## Vertex Insights — Proyecto Final

**Fecha de cierre:** 2026-07-05
**Sprint asociado:** Sprint 2
**Fase CRISP-DM:** Deployment / Monitoring
**Tag de versión:** V1.7.0 (a crear en `master` al merge final; ver cierre-sprint-2)
**Líder de etapa:** Machine Learning Engineer (Wessin, Nassim), documentación con el equipo

---

## 1. Contexto y objetivos de la etapa

Dar al producto vigilancia de producción (HU-16) y dejar el repositorio
autocontenido para cualquier evaluador externo (HU-17): monitoreo de drift con
acciones por severidad, vigilante de performance con etiquetas diferidas (el
riesgo R-14 es el #1 del modelo) y documentación final (README, manual de usuario,
informe técnico).

## 2. Equipo y roles activos durante la etapa

| Rol | Integrante | Participación |
|---|---|---|
| Machine Learning Engineer | Wessin, Nassim | Monitoreo completo, CI, documentación técnica |
| Analytics Lead (D-40) | Tutalcha Pame, Harrison Alberto | Revisión de umbrales de acción y del informe |
| Data Analyst (D-40) | García Cadena, Cristian Fernando | Base metodológica del monitoreo (PSI/KS/Chi², Fase 7 de su guía) |
| BI Analyst (D-40) | López Solórzano, Juan Carlos | Documentación del tablero Power BI |
| Data Scientist | Aguilar Lomas, Oscar Amaury | Revisión del baseline de referencia |

## 3. Historias de usuario completadas

| HU | Título | Estado |
|---|---|---|
| HU-16 | Componente de monitoreo | Completada (detector validado con drift inducido) |
| HU-17 | Documentación final | Completada (README + manual + informe técnico) |

## 4. Productos entregados

- `src/monitoring/` — `baseline.py`, `drift.py` (PSI + KS + Chi² + score drift,
  severidad `derivada` para features de lookup), `performance.py` (etiquetas
  diferidas ~30 d; vigilante R-14), `simulate_production.py` (replay + drift
  inducido). Reportes en `monitoring/*.json` + pestaña Drift del dashboard.
- `docs/estrategia_monitoreo.md` — severidad → acción, runbook R-14, validación.
- `docs/manual_usuario.md`, `docs/informe_tecnico.md`, `README.md` reescrito.
- `.github/workflows/ci.yml` — pytest + compileall en cada PR (suite 100% sintética).

## 5. Decisiones tomadas durante la etapa

- Ratificados en D-41: disparadores de reentrenamiento y demo de drift inducido.
- Matiz metodológico incorporado: las features **derivadas por lookup** se excluyen
  del veredicto de drift (PSI inflado artificialmente) vía flags de imputación.

## 6. Resultados y verificaciones clave

| Verificación | Resultado |
|---|---|
| Run normal (replay test) | Detecta el drift real R-14 (`mes_compra`, `dias_prometidos`, `flete_total`) sin falsas alarmas del vigilante (+2.90 d vs ref +3.17 d; cumplimiento 96.40%) |
| **Drift inducido** (precios ×1.5, 60% a N/NE, +5 meses) | Score PSI 1.23 → 1.76; alertas 34.8% → 66.3%; vigilante dispara el diagnóstico correcto |
| Suite de tests | 67/67 (24 nuevos de serving/API/monitoreo/scoring) |
| CI | Workflow verde en el PR #28 |

## 7. Variaciones respecto al plan original

- HU-16 era prioridad Media/simplificable (R-02): se entregó completa (PSI + KS +
  Chi² + score drift + performance diferida + simulador), por encima del mínimo.
- El monitoreo se demuestra con **producción simulada** (datos Kaggle, sin tráfico
  real): el replay del split test por la API + drift inducido.

## 8. Lecciones aprendidas

- El vigilante de performance (sobre-predicción/cumplimiento) dispara ANTES que el
  PSI de features cuando el margen se descalibra: monitorear salidas, no solo entradas.
- Convenciones de signo importan: alinear `bias_mean = pred − real` con el repo
  evitó una falsa alarma invertida.

## 9. Estado de los documentos vivos al cierre

Backlog HU-16/17 cerradas; bitácora hasta D-41; riesgos actualizados al cierre
(R-02/R-04 cerrados; R-14 activo-bajo monitoreo con runbook).

## 10. Próximos pasos

Etapa 9: presentación final (HU-18, deck `Vertex_Insights_Sprint2_Final_v1.pptx`),
merge del PR #28, tags V1.4.0–V1.8.0. Ver `cierre-sprint-2.md`.
