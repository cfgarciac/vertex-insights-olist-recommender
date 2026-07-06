# Cierre de la Etapa 5 — Cierre del Sprint 1 (Sprint Review y Retrospective)

## Vertex Insights — Proyecto Final

**Fecha de cierre:** junio 2026 (documentado retroactivamente el 2026-07-05)
**Sprint asociado:** Sprint 1
**Fase CRISP-DM:** Evaluation (primera pasada) / gestión
**Tag de versión:** V1.4.0 (pendiente de creación en `master` al merge final; ver cierre-sprint-2)
**Líder de etapa:** Scrum Master (García Cadena, Cristian Fernando)

---

## 1. Contexto y objetivos de la etapa

La Etapa 5 cerró el Sprint 1: validar los entregables de las Etapas 0–4 con el
cliente (Sprint Review), capturar aprendizajes (Retrospective) y dejar priorizado el
Sprint 2. Este documento formaliza retroactivamente ese cierre — el trabajo ocurrió
en junio 2026 (presentación ejecutiva incluida); la documentación del acta y este
cierre se completaron el 2026-07-05 como parte del cierre integral del proyecto.

## 2. Equipo y roles activos durante la etapa

| Rol (vigente en la etapa) | Integrante | Participación |
|---|---|---|
| Scrum Master | García Cadena, Cristian Fernando | Coordinación del cierre y de la presentación |
| Product Owner | Tutalcha Pame, Harrison Alberto | Validación de entregables vs. objetivos de negocio |
| Data Analyst | López Solórzano, Juan Carlos | Deck ejecutivo (`Vertex_Insights_Sprint1_Cierre_v6.pptx`) y mockups de dashboard |
| Data Scientist | Aguilar Lomas, Oscar Amaury | Soporte de contenidos (datos/EDA) |
| Machine Learning Engineer | Wessin, Nassim | Soporte de contenidos (modelado Etapa 4) |

> Roles posteriormente actualizados por **D-40** (2026-07-05); este cierre conserva
> los títulos vigentes en su momento.

## 3. Historias de usuario completadas

| HU | Título | Estado |
|---|---|---|
| HU-11 | Ejecutar el cierre formal del Sprint 1 | Completada (cierre documental retroactivo) |

## 4. Productos entregados

- Presentación ejecutiva del Sprint 1 (`Vertex_Insights_Sprint1_Cierre_v6.pptx`, 27
  slides): pivote, hallazgos, MVP del modelo, Gantt e impacto.
- Acta de Review + Retrospective: `docs/sprints/acta-sprint-1.md`.
- Backlog del Sprint 2 priorizado (HU-12..HU-18, luego realineadas a P1).

## 5. Decisiones tomadas durante la etapa

Sin decisiones D-NN nuevas: la etapa ejecutó lo decidido en D-16..D-29 (pivote,
métricas, modelado) y comunicó sus resultados.

## 6. Resultados y verificaciones clave

- Pivote a P1 validado con el cliente: dolor de 8.1% de tardanza y R$1.1M expuesto.
- MVP de clasificación (XGBoost, D-27) aceptado como base del Sprint 2.
- Aprendizajes registrados (acta): validar viabilidad antes de modelar; PRs pequeños.

## 7. Variaciones respecto al plan original

- El acta y este cierre se documentaron retroactivamente (2026-07-05): la ceremonia
  ocurrió, la formalización quedó pendiente hasta el cierre integral (lección
  recogida en la retrospectiva del Sprint 2).
- El tag `V1.4.0` no se creó en su momento por el desfase de ramas (R-09); queda
  delegado al flujo de merge final.

## 8. Lecciones aprendidas

- Cerrar la documentación al ritmo de las ceremonias, no en bloque al final.
- El deck ejecutivo con lenguaje de negocio (no técnico) funcionó ante el cliente y
  se adopta como plantilla del cierre final.

## 9. Estado de los documentos vivos al cierre

Backlog: HU-01..HU-10 cerradas; bitácora hasta D-29; riesgos con R-09/R-14 activos.
(Estado al momento del cierre retroactivo: ver `cierre-sprint-2.md`.)

## 10. Próximos pasos

Sprint 2 (Etapas 6–9): evaluación final, API, Docker, dashboard, monitoreo,
documentación y presentación final.
