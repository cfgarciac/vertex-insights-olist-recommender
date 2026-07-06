# Cierre del Sprint 2 — Consolidado (Etapas 6–9)

## Vertex Insights — Proyecto Final

**Fecha de cierre documental:** 2026-07-05
**Alcance:** Etapas 6 (evaluación final), 7 (despliegue), 8 (monitoreo y documentación)
y 9 (entrega final — deck listo, presentación pendiente de fecha)
**Acta asociada:** `docs/sprints/acta-sprint-2.md`
**Roles vigentes (D-40):** Analytics Lead (Harrison) · Data Analyst (Cristian) ·
BI Analyst (Juan Carlos) · Data Scientist (Amaury) · MLE (Nassim)

---

## 1. Qué entrega el Sprint 2 (el producto completo)

**"La promesa que sí se cumple":** un producto de dos modelos que fija la promesa de
entrega y la defiende, servido en producción local + contenedor, con visibilidad para
la operación (dashboard) y la dirección (tablero Power BI), y vigilancia continua.

| Pieza | Qué hace | Cifra clave (test) |
|---|---|---|
| Motor de promesa (Fase 2) | Predice días reales → promesa P90 | 96.70% cumplimiento / 17.87 d (vs 94.32% / 19.12 d actual) |
| Escudo de riesgo (Fase 1) | P(tarde) calibrada + bandera | ROC-AUC 0.742 · Brier 0.063 · v2 captura 47.6% alertando 34.7% |
| API + Docker | `/promise` · `/predict/delivery-risk` · `/health` | replay E2E 96.40% == offline |
| Dashboard Streamlit | simulador, scoring CSV, región, métricas, drift | 5 pestañas |
| Monitoreo | PSI/KS/Chi² + vigilante R-14 (etiquetas ~30 d) | validado con drift inducido (alertas 34.8% → 66.3%) |
| Tablero Power BI | 5 páginas para la dirección | GMV en riesgo R$3.80M = 28% |

## 2. Historias del Sprint 2 — estado final

| HU | Título | Estado | Evidencia |
|---|---|---|---|
| HU-12 | Evaluación final y selección | ✅ Completada | justificacion_modelo.md · plan_validacion.md · D-41 |
| HU-13 | API REST FastAPI | ✅ Completada | src/api/ · contrato_api.md |
| HU-14 | Docker | ✅ Completada | Dockerfile · imagen validada |
| HU-15 | Dashboard | ✅ Completada | src/dashboard/ (5 pestañas) |
| HU-16 | Monitoreo | ✅ Completada | src/monitoring/ · estrategia_monitoreo.md |
| HU-17 | Documentación final | ✅ Completada | README · manual_usuario.md · informe_tecnico.md |
| HU-18 | Presentación final | 🔶 En curso | deck diseñado; falta exponer + tag V1.8.0 |

(HU-11, del Sprint 1, cerrada retroactivamente: `cierre-etapa-5.md`.)

## 3. Decisiones del ciclo (bitácora)

D-38 (unión de modelos) → D-39 (arquitectura de despliegue, Aceptada) →
D-40 (cambio de roles por el tutor) → D-41 (ratificación: política P90, umbrales
v2 = 0.3658 / v1 = 0.0721, postura R-14 con runbook, decisiones de despliegue).

## 4. Riesgos al cierre

| Riesgo | Estado al cierre |
|---|---|
| R-02 (tiempo vs alcance) | Cerrado — Sprint 2 entregado completo |
| R-04 (curva FastAPI/Docker/Streamlit) | Cerrado — despliegue implementado y validado |
| R-09 (drift de ramas) | En cierre — se resuelve al mergear PR #28 |
| R-13 (desalineación con la propuesta) | Mitigado — presentación final lo comunica |
| R-14 (cambio de régimen) | Activo bajo monitoreo — D-41: márgenes + runbook |
| R-15 (política de promesa sin costos reales) | Declarado — revisión cuando Olist comparta costos |
| R-17 (sin variables logísticas del carrier) | Declarado — techo estructural documentado |

## 5. Actos formales PENDIENTES (en manos del equipo)

> El cierre documental está completo; estos actos requieren al equipo y CIERRAN el
> proyecto en el repositorio:

1. **Aprobar y mergear el PR #28** (`Nassim → developer`) — contiene TODO el Sprint 2.
2. **Promover `developer → master`** (PR de release).
3. **Crear los tags en `master`** (por el flujo de convenciones §8):
   ```bash
   git tag V1.4.0 -m "Etapa 5: cierre Sprint 1"     # retroactivo
   git tag V1.5.0 -m "Etapa 6: evaluación final y selección (D-41)"
   git tag V1.6.0 -m "Etapa 7: API + Docker + dashboard"
   git tag V1.7.0 -m "Etapa 8: monitoreo + documentación final"
   git push origin --tags
   ```
4. **Presentar** (HU-18) y crear **`V1.8.0`** tras la presentación.
5. Insertar las **capturas del tablero Power BI** en las slides 20–22 del deck
   (BI Analyst).

## 6. Presentación final — mapa de expositores (30 slides · 30 min)

| Bloque | Expositor | Slides | Tema |
|---|---|---|---|
| 1. El proyecto | Cristian (Data Analyst) | 1–6 | portada · equipo/agenda · pivote 60 s · dolor en cifras · objetivo S2 · **Gantt final** |
| 2. Los datos | Amaury (Data Scientist) | 7–12 | materia prima · anti-fuga [t0] · 4 familias de señales · régimen R-14 · particiones · señal→decisión |
| 3. La promesa inteligente | Harrison (Analytics Lead) | 13–18 | dos modelos un producto · motor · **política P90** · región N/NE · qué gana Olist · alternativas |
| 4. La visibilidad del negocio | Juan Carlos (BI Analyst) | 19–24 | tablero 5 páginas · [capturas ×3] · decisiones por página · tablero vs dashboard |
| 5. El producto en producción | Nassim (MLE) | 25–30 | escudo calibrado · API [Swagger] · dashboard operativo · vigilancia/drift · entregables + roadmap · gracias |

Deck: `archivos_compartidos por nassim/Vertex_Insights_Sprint2_Final_v1.pptx`
(estilo del deck v6 del Sprint 1: paleta azul `#1A2A4F`/`#3A7BFD`, Cambria/Calibri,
logo, 16:9).

## 7. Lecciones del sprint (síntesis de la retrospectiva)

1. Los modelos también se evalúan como **producto** (el hallazgo v1→v2 solo emergió
   al unirlos).
2. El **contrato** de la API primero: integra dashboard, logs y monitoreo sin retrabajo.
3. Monitorear **salidas** (cumplimiento/sobre-predicción), no solo entradas (PSI).
4. Cerrar documentación **al ritmo de cada etapa** — no en bloque al final.
