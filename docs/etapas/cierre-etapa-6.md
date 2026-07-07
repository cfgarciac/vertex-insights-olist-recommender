# Cierre de la Etapa 6 — Evaluación final y selección del modelo

## Vertex Insights — Proyecto Final

**Fecha de cierre:** 2026-07-05
**Sprint asociado:** Sprint 2
**Fase CRISP-DM:** Evaluation
**Tag de versión:** V1.5.0 (a crear en `master` al merge final; ver cierre-sprint-2)
**Líder de etapa:** Machine Learning Engineer (Wessin, Nassim), con el Analytics Lead

---

## 1. Contexto y objetivos de la etapa

Cerrar formalmente la selección del producto de P1: ratificar umbrales y política
(diferidos por D-28/D-31/D-36), fijar la postura ante R-14 y producir la
justificación y el plan de validación exigidos por HU-12. La evaluación técnica ya
existía (D-38, evaluación única en test); esta etapa la convirtió en decisión
ratificada y documentada.

## 2. Equipo y roles activos durante la etapa

| Rol | Integrante | Participación |
|---|---|---|
| Machine Learning Engineer | Wessin, Nassim | Evidencia de test, validación E2E del serving, documentos de la etapa |
| Analytics Lead (D-40) | Tutalcha Pame, Harrison Alberto | Ratificación de política/umbrales; motor de promesa (Fase 2) |
| Data Scientist | Aguilar Lomas, Oscar Amaury | Revisión de la tabla analítica y del protocolo de validación |
| Data Analyst (D-40) | García Cadena, Cristian Fernando | Revisión metodológica (guía de proyectos ML) |
| BI Analyst (D-40) | López Solórzano, Juan Carlos | Cifras de negocio del tablero para contraste |

## 3. Historias de usuario completadas

| HU | Título | Estado |
|---|---|---|
| HU-12 | Evaluación final y selección del modelo | Completada (ver notas en el backlog) |

## 4. Productos entregados

- `docs/justificacion_modelo.md` — por qué motor RF + P90 y escudo XGB calibrado v2.
- `docs/plan_validacion.md` — protocolo aplicado + criterios de re-validación.
- Ratificación D-41 en la bitácora (política P90; v2 = 0.3658; v1 = 0.0721; R-14).
- Artefacto final: `artifacts/producto_promesa_riesgo.joblib` (ya serializado en D-38).

## 5. Decisiones tomadas durante la etapa

- **D-41** — umbrales/política ratificados y postura R-14 (sin re-ventaneo; runbook).

## 6. Resultados y verificaciones clave

| Verificación | Resultado |
|---|---|
| Política P90 vs actual (test, 14.471 órdenes) | 96.70% / 17.87 d vs 94.32% / 19.12 d — domina en ambas dimensiones |
| Escudo (test) | ROC-AUC 0.742 · PR-AUC 0.132 (2× tasa base 6.6%) · Brier 0.063 |
| Sinergia escudo v2 sobre promesa P90 | captura 47.6% de incumplidas alertando 34.7% (lift 1.4×) |
| Serving == evaluación offline | replay 1.500 órdenes por la API: 96.40% vs 96.70% |

## 7. Variaciones respecto al plan original

- La calibración formal con "el PO" se transformó en ratificación de equipo (D-40
  eliminó el rol PO); la evidencia y la trazabilidad quedan en D-41 y `/health`.

## 8. Lecciones aprendidas

- Diferir umbrales a una etapa de cierre funciona SOLO si la evidencia queda
  preparada (puntos de operación serializados en el artefacto lo hicieron trivial).

## 9. Estado de los documentos vivos al cierre

Backlog HU-12 cerrada; bitácora hasta D-41; riesgos R-12 verificado, R-14 con
postura fijada.

## 10. Próximos pasos

Etapa 7 (API + Docker + dashboard) — ya ejecutada en paralelo; ver su cierre.
