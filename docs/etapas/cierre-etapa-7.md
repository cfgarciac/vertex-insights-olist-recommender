# Cierre de la Etapa 7 — Despliegue: API REST, Docker y dashboard

## Vertex Insights — Proyecto Final

**Fecha de cierre:** 2026-07-05
**Sprint asociado:** Sprint 2
**Fase CRISP-DM:** Deployment
**Tag de versión:** V1.6.0 (a crear en `master` al merge final; ver cierre-sprint-2)
**Líder de etapa:** Machine Learning Engineer (Wessin, Nassim)

---

## 1. Contexto y objetivos de la etapa

Convertir el producto D-38 en un servicio consumible: API REST con contrato mínimo,
imagen Docker reproducible y dashboard para stakeholders, según la arquitectura
D-39 (`docs/arquitectura_despliegue.md`) que corrigió el orden propuesto
inicialmente (contrato+API → Docker → dashboard → monitoreo).

## 2. Equipo y roles activos durante la etapa

| Rol | Integrante | Participación |
|---|---|---|
| Machine Learning Engineer | Wessin, Nassim | Carga alta — serving, API, Docker, dashboard, tests |
| Analytics Lead (D-40) | Tutalcha Pame, Harrison Alberto | Revisión del PR; funciones de Fase 2 reutilizadas en la API |
| Data Analyst (D-40) | García Cadena, Cristian Fernando | Guía metodológica (Fases 6–8) y revisión |
| BI Analyst (D-40) | López Solórzano, Juan Carlos | Tablero Power BI (visibilidad de negocio complementaria) |
| Data Scientist | Aguilar Lomas, Oscar Amaury | Dataset base de lookups (orders_features) |

## 3. Historias de usuario completadas

| HU | Título | Estado |
|---|---|---|
| HU-13 | API REST con FastAPI | Completada |
| HU-14 | Empaquetado con Docker | Completada |
| HU-15 | Dashboard interactivo | Completada (5 pestañas; scoring por CSV añadido) |

## 4. Productos entregados

- `src/serving/` — `build_lookups.py` (lookups point-in-time del train) y
  `feature_builder.py` (contrato ~7 campos → 15-16 features, faltantes flaggeados).
- `src/api/` — `/health`, `/promise`, `/predict/delivery-risk`; Pydantic; carga
  única; logging JSONL; Swagger. `docs/contrato_api.md`.
- `Dockerfile` + `.dockerignore` — slim + libgomp1 + pins; healthcheck.
- `src/dashboard/` — app Streamlit (5 pestañas) + `scoring.py` (lote por CSV).
- `requirements.txt` con pins exactos del venv de entrenamiento.
- Tests: `test_feature_builder.py`, `test_api.py`, `test_scoring.py` (fixtures
  sintéticos — corren sin datos).

## 5. Decisiones tomadas durante la etapa

- D-39 (arquitectura) pasó a **Aceptada** al implementarse.
- Ratificadas en D-41: dashboard híbrido y lookups estáticos horneados.

## 6. Resultados y verificaciones clave

| Verificación | Resultado |
|---|---|
| API == modelo directo | idénticos al decimal (3 casos) |
| API == evaluación offline D-38 | 5 órdenes reales por order_id: exactas |
| Replay E2E 1.500 órdenes | cumplimiento 96.40% / alertas 34.80% (offline 96.70% / 34.66%) |
| Docker | unpickle dentro del contenedor OK; `/promise` idéntico al venv; healthy |
| Latencia | p50 ≈ 32 ms por predicción (sesión keep-alive) |
| Smoke test integral | 52/52 verificaciones |

## 7. Variaciones respecto al plan original

- El "feature store" quedó a nivel **agregado** (categoría/estado): el repo no
  versiona product_id/seller_id. Documentado como degradación controlada (D-39)
  con regeneración por ID cuando existan los catálogos.
- Se añadió la pestaña de **scoring por CSV** (no estaba en el criterio de HU-15).

## 8. Lecciones aprendidas

- El contrato Pydantic como artefacto integrador: definirlo primero evitó
  retrabajo en dashboard y monitoreo.
- `streamlit run` no incluye la raíz en `sys.path` (fix documentado en commit).
- `localhost` en Windows penaliza ~2 s por conexión (IPv6): usar 127.0.0.1 +
  sesión keep-alive.

## 9. Estado de los documentos vivos al cierre

Backlog HU-13/14/15 cerradas; contrato y arquitectura publicados; README con
sección de despliegue.

## 10. Próximos pasos

Etapa 8 (monitoreo + documentación final) — ver su cierre.
