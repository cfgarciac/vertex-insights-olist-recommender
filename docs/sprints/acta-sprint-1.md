# Acta — Sprint 1: Review y Retrospective

> **Sprint:** 1 (Etapas 0–5) · **Cierre:** junio 2026 · **Acta documentada retroactivamente**
> el 2026-07-05 como parte del cierre formal (HU-11). Los hechos que registra ocurrieron
> al cierre del Sprint 1; la evidencia citada existe desde entonces.

## 1. Sprint Review

- **Formato:** presentación ejecutiva al cliente (rol de junta directiva).
- **Evidencia:** `Vertex_Insights_Sprint1_Cierre_v6.pptx` (27 slides, carpeta compartida
  del equipo) — hallazgos del descubrimiento, pivote recomendado y MVP del modelo.
- **Entregables validados:**
  - Diagnóstico del encargo original (recomendador item-to-item) y su techo
    estructural: 97% de compradores únicos, 3.3% de co-compra, sin datos de clics.
  - **Pivote formal a P1** (predicción de entrega tardía) aceptado (D-16..D-21).
  - Base analítica de 96.470 órdenes con 16 features [t0] (Etapa 3, anti-fuga).
  - Modelo candidato XGBoost auditado (Etapa 4, D-27): recall 63% marcando 35%.
  - Cuantificación del dolor: 8.1% de entregas tarde, R$1.1M de GMV expuesto por ciclo.
- **Feedback recibido:** avanzar en Sprint 2 hacia el producto operativo
  (calibración/evaluación final, API, dashboard, monitoreo).

## 2. Sprint Retrospective

| Categoría | Punto | Acción acordada (responsable) |
|---|---|---|
| Funcionó bien | Descubrimiento honesto del techo del recomendador antes de invertir en él | Mantener la práctica de validar viabilidad antes de modelar (equipo) |
| Funcionó bien | Bitácora de decisiones (D-01..D-29) como memoria del proyecto | Continuar en Sprint 2 (todos) |
| A mejorar | Relevo de etapas con contexto disperso | Flujo de 7 documentos por etapa + notas de handoff en cierres (SM) |
| A mejorar | Desfase entre ramas personales y `developer` (R-09) | PRs más frecuentes y pequeños (todos) |
| Riesgo vigilado | Cambio de régimen temporal 2018 (R-14) | Split temporal + monitoreo planeado para Sprint 2 (MLE/DS) |

## 3. Acuerdos de salida

- Backlog del Sprint 2 priorizado y realineado a P1 (HU-12..HU-18).
- Tag `V1.4.0` (cierre Sprint 1): delegado al flujo de merge a `master`
  (ver `docs/etapas/cierre-sprint-2.md`).
