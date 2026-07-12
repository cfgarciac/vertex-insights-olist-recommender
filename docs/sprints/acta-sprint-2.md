# Acta — Sprint 2: Review y Retrospective

> **Sprint:** 2 (Etapas 6–9) · **Cierre documental:** 2026-07-05
> **Review formal:** la presentación final al cliente (HU-18,
> `Vertex_Insights_Sprint2_Final_v1.pptx`) hace las veces de Sprint Review ante la
> "junta directiva" de Olist; esta acta registra los entregables y aprendizajes.

## 1. Sprint Review — entregables validados

| Entregable | Evidencia |
|---|---|
| Evaluación final y selección ratificada (HU-12) | `docs/justificacion_modelo.md`, `docs/plan_validacion.md`, D-41 |
| Producto conjunto D-38 (motor + escudo) | `artifacts/producto_promesa_riesgo.joblib`; P90: 96.70% / 17.87 d vs 94.32% / 19.12 d |
| API REST (HU-13) | `src/api/` — `/health`, `/promise`, `/predict/delivery-risk`; Swagger |
| Docker (HU-14) | imagen `vertex-olist-api` validada (unpickle + respuestas idénticas al venv) |
| Dashboard (HU-15) | `src/dashboard/` — 5 pestañas, incl. scoring por CSV |
| Monitoreo (HU-16) | `src/monitoring/` — PSI/KS/Chi², vigilante R-14, detector validado con drift inducido |
| Tablero Power BI | `Vertex Power BI.pbix` (5 páginas) + `Documentacion_Dashboard_PowerBI_Vertex.md` (BI Analyst) |
| Documentación final (HU-17) | README reescrito, `docs/manual_usuario.md`, `docs/informe_tecnico.md` |
| Calidad | 67/67 tests (suite sintética) + CI GitHub Actions en PRs |

## 2. Sprint Retrospective

| Categoría | Punto | Lección / acción |
|---|---|---|
| Funcionó bien | Unir los dos modelos en un producto ("la regresión fija la promesa; el clasificador la defiende") reveló el hallazgo v1→v2 | Los modelos se evalúan también como PRODUCTO, no solo por métrica individual |
| Funcionó bien | Contrato de la API definido antes de codificar (D-39) | El contrato como artefacto integrador evitó retrabajos en dashboard y monitoreo |
| Funcionó bien | Validación E2E (replay por la API == evaluación offline) | Mantener el candado de contrato y el replay como pruebas estándar |
| A mejorar | El orden inicial propuesto para MLOps estaba invertido (drift→dashboard→API) | Contrastar propuestas contra guía + backlog + dependencias antes de ejecutar |
| A mejorar | Cierres formales (HUs, actas, tags) se acumularon para el final | Cerrar documentación al ritmo de cada etapa, no en bloque |
| Riesgo gestionado | R-14 (régimen): márgenes de validación + monitoreo con runbook (D-41) | El vigilante de performance dispara antes que el PSI de features |

## 3. Acuerdos de salida

1. Merge del PR #28 (`Nassim → developer`) y promoción `developer → master`.
2. Tags en `master`: `V1.4.0` (E5), `V1.5.0` (E6), `V1.6.0` (E7), `V1.7.0` (E8) y
   `V1.8.0` tras la presentación (E9).
3. Presentación final según el mapa de expositores de `docs/etapas/cierre-sprint-2.md`.
4. Capturas del tablero Power BI a insertar en las slides 20–22 del deck (BI Analyst).
