# Estrategia de monitoreo en producción — Producto P1 (HU-16, D-39)

> Complementa [arquitectura_despliegue.md](arquitectura_despliegue.md) §2.2-F y
> [contrato_api.md](contrato_api.md). Los módulos viven en `src/monitoring/`.

## Flujo

```
API (logs/predictions.jsonl)          etiquetas diferidas (~30 d)
        │                                      │
        ▼                                      ▼
  drift.py  ◄── drift_baseline.json     performance.py ◄── replay_resultados.csv
  PSI + KS + Chi² + score drift         cumplimiento realizado + sobre-predicción
        │                                      │
        └────────────► monitoring/*.json ◄─────┘  → pestaña Drift del dashboard
```

- **Baseline** (`baseline.py`): distribución de referencia de las 16 features y
  de los scores, calculada SOLO con el split train (corte 2018-04-15, misma
  ventana point-in-time que los lookups). Única pieza independiente de la API.
- **Drift de entrada** (`drift.py`): PSI por feature (numéricas y categóricas),
  KS para numéricas continuas, Chi² para categóricas, sobre las predicciones
  logueadas por la API.
- **Drift del score**: PSI de `pred_dias` contra la distribución del target en
  train + tasa de alertas del escudo vs tasa base (9.03%).
- **Performance con etiquetas diferidas** (`performance.py`) — **el vigilante
  de R-14**: `dias_entrega_real` llega ~30 días después; al hacer el join se
  calcula el cumplimiento realizado, el MAE de producción y la
  **sobre-predicción media** (`pred − real`, convención `bias_mean` del repo;
  referencia test **+3.17 d**). Si cae hacia 0 o se invierte, las promesas
  quedan cortas ANTES de que el PSI de features lo delate.
- **Producción simulada** (`simulate_production.py`): sin tráfico real (datos
  Kaggle), se rejuega el split test por el camino completo de la API y se
  puede **inducir drift artificial** para validar el detector.

## Severidad → acción (PSI, umbrales de la guía del SM)

| PSI | Severidad | Acción |
|---|---|---|
| < 0.10 | ok | nada |
| 0.10 – 0.25 | moderado | investigar causa; aumentar frecuencia de monitoreo |
| > 0.25 | **severo** | runbook R-14 (abajo) |
| — | derivada | PSI inflado por lookup: no cuenta para el veredicto (ver matiz) |

**Disparadores de acción (D-39, pendientes de aprobación del PO):**
- PSI > 0.25 en **≥ 2 features clave no-derivadas**, o
- cumplimiento realizado **< 95%** en ventana de 30 días, o
- sobre-predicción media **< +1.6 d** (mitad de la referencia) o **negativa**.

**Runbook R-14 (escalonado):**
1. **Recalibrar márgenes** con datos recientes (barato: recalcular P80/P90/P95
   sobre residuos de una ventana reciente; no reabre el modelado).
2. **Reentrenar con re-ventaneo** (decisión R-14 de la Etapa 6) y re-serializar
   el artefacto (versionar como MINOR según convención de tags).
3. Concept drift confirmado (la relación features→target cambió) →
   **reentrenamiento obligatorio** (guía del SM, Fase 7).

## Matiz importante: features derivadas por lookup

`dist_haversine_km`, `tasa_vendedor` y `sin_historial_vendedor` se derivan en
el servidor con lookups agregados (medianas por estado): su distribución en
producción **colapsa a pocos valores** y el PSI contra el baseline por-orden se
infla artificialmente (p. ej. tasa_vendedor PSI ≈ 4.6 sin drift real).
`drift.py` las detecta con los `flags_imputacion` de los logs (si > 50% de los
requests derivaron la feature) y las reporta como severidad **`derivada`**,
excluidas del veredicto. Remedios de fondo: exigir el campo en el contrato o
regenerar los lookups con granularidad por ID (con los CSV crudos de Olist).

## Validación del detector (criterio de aceptación HU-16) — realizada 2026-07-05

| Escenario | Score PSI | Alertas escudo | Vigilante R-14 |
|---|---|---|---|
| Normal (replay test, n=1500) | 1.23 | 34.8% | sin alertas (+2.90 d vs ref +3.17 d) |
| **Drift inducido** (`--drift todo`: precios ×1.5, 60% órdenes a N/NE, +5 meses, n=800) | **1.76** | **66.3%** | **dispara**: "sobre-predicción +10.39 d duplica la referencia → recalibrar márgenes" |

El run "normal" también detecta el **drift real R-14** documentado
(train 2016-09→2018-04 vs test 2018-06→08): `mes_compra` (estacionalidad del
split), `dias_prometidos` (Olist acortó promesas) y `flete_total` salen severos
— coherente con el registro de riesgos.

## Cómo correr el ciclo completo

```bash
python -m src.monitoring.baseline                    # 1. baseline (una vez)
python -m src.monitoring.simulate_production         # 2. tráfico simulado (o API real)
python -m src.monitoring.drift                       # 3. PSI/KS/Chi² → drift_report.json
python -m src.monitoring.performance                 # 4. etiquetas diferidas → performance_report.json
# demo del detector con drift inducido:
python -m src.monitoring.simulate_production --drift todo
```
