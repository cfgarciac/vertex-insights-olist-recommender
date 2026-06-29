# Contexto del Proyecto — DVA de P1 (Entrega) ↔ Repo, RECONCILIADOS

> Generado: 2026-06-28 (reemplaza la versión anterior, que narraba el proyecto como
> "pre-modelado"; eso era incorrecto: el repo ya cerró la Etapa 4).
> Fuente: Bitácora Maestra v0.11 + Report v0.4 + `context.md` + artefactos del repo
> (`etapa4_metrics.json`, `decisiones_fe.md`, `bitacora_decisiones.md`, EDA 02/03).

---

## 1. Problema elegido

**P1 · Desempeño de entrega.** Elegido en el Punto de Decisión (Report §7.2; decisión
D-18 del equipo) por ser el único completable end-to-end con target limpio, forzar la
lección de data leakage y sostenerse en valor (dolor real, accionable, regional).

**Frontera P1↔P3 resuelta:** P3 (vendedores) NO se desarrolla como problema separado;
la señal del vendedor entra como FEATURE de P1 (tasa histórica de despacho tardío,
point-in-time). Un solo problema, un solo target.

---

## 2. Estado actual REAL (lo que más importa entender)

**El repo NO está antes de modelar: cerró la Etapa 4 (Modelado), tag V1.3.0.** Ya existe
un clasificador `entrega_tarde` (XGBoost) entrenado, testeado y serializado. La narrativa
DVA (Bitácora + Report) corrió **en paralelo** y este chat la **reconcilia** con lo
construido: la narrativa no antecede al modelo, lo explica y lo encuadra.

| Pista | Qué es | Estado |
|---|---|---|
| **Repo / equipo** | CRISP-DM Etapas 0–4. Clasificador entrenado. | Etapa 4 **cerrada** (V1.3.0). |
| **Narrativa DVA** | Embudo Descubrimiento→DVA, Report. | Reconciliada con el modelo (este chat). |

**Reconciliación en una frase:** Fase 1 (clasificación) **entregada**; Fase 2
(regresión de duración) **propuesta como portadora del valor**; mismo cimiento de
features/pipeline. No se tira trabajo del equipo.

---

## 3. Divergencias plan↔repo (y cómo se reconcilian)

| Tema | El PLAN decía (Bitácora/Report) | El REPO dice (código/decisiones) | Cómo se reconcilia |
|---|---|---|---|
| **Fase** | "Nivel 3 en curso, pre-modelado; falta EDA (D1) y D2" | "Etapa 4 cerrada, V1.3.0, modelo entrenado" | El repo ya modeló. La narrativa DVA corre en paralelo y **explica** el modelo; no lo antecede. |
| **EDA** | D1a/D1b/D1c + D2 pendientes | EDA Etapa 2 (`02_EDA`) y Etapa 3 (`03_EDA`) completos: drivers, geo, vendedor, leakage map | D1a–D2 se reencuadran: de "explorar" a **"documentar la señal descriptiva (ya hecha) que justifica las 16 features"**. Se cita el EDA del equipo; no se re-corre. (Ver §6.) |
| **Framing** | "Abierto; 3 targets; la evidencia inclina a C" | "Cerrado en clasificación" (D-19/D-20) | Ninguna decisión pesó clasificación vs. regresión **por valor**; D-20 *parkeó* la regresión y `decisiones_fe.md` la dejó pendiente. Se **MARCA** ahora (ver §5). |
| **Target B** | Candidato (`dias_vs_promesa`) | Prohibido como target y feature (sesgado) | Coinciden en descartarlo: B está sesgado por el colchón. La regresión va sobre **C** (`dias_entrega_real`), no B. |
| **Universo / target A** | 96,470; `entrega_tarde` vs promesa; 8.11%; canceladas aparte | 96,470; `entrega_tarde` vs promesa; 8.11%; canceladas aparte (D-20) | **Coinciden.** El DVA reconstruyó la base desde las 9 tablas y reprodujo la cifra del repo (que partió del CSV consolidado) → prueba de reproducibilidad del target. |
| **Features** | ~30 candidatas válidas (M0) | 16 usadas (subconjunto) | Las 16 son el subconjunto que el equipo seleccionó (`decisiones_fe.md`); el DVA documenta por qué esas. |
| **Anti-leakage** | Inventario D0; seller rate point-in-time | `COLS_POST`; seller rate expanding point-in-time; split temporal | **Misma disciplina.** El DVA la audita y confirma (peso `tasa_vendedor` 6% en test, sin fuga; R-12). |
| **Charter / usuario destino** | Charter en pausa hasta elegir problema (ya elegido) | No hay Charter ni se declara usuario/valor-en-despliegue | Este chat fija usuario destino (sistema de promesa de Olist → cliente) y valor (afinar la promesa). El Charter se redacta en **Chat 2**. |

---

## 4. Números clave

| Dato | Valor |
|---|---|
| Universo P1 | **96,470 órdenes** entregadas con fecha |
| Tasa de tarde (target A) | **8.11%** (7,826 órdenes) |
| Tasa base por split (régimen 2018, R-14/D-29) | train 9.03% → val 5.34% → **test 6.61%** |
| Canceladas / no-entregadas | 2,963 / R$370K (excluidas + reportadas como limitación) |
| Colchón de promesa | mediana real **10** vs prometida **23** días (~13); p90 del desvío = −2 |
| GMV expuesto (P1) | R$1,124,342 (8.6% del total) |
| Modelo V1.3.0 (test) | ROC-AUC **0.703** · PR-AUC **0.124** · recall 0.35 (umbral F1) / 0.63 (alta cobertura, alerta 35% de órdenes) |
| Dolor regional | AL 23% tarde vs SP 5.8% (~4×) |

---

## 5. Decisión de framing — MARCADA (ya no "abierta")

> Jerga: **clasificación** = respuesta sí/no (¿tarde?). **Regresión** = un número
> (¿cuántos días?); su error se mide en **MAE** (error absoluto medio, "me equivoco por
> X días"). **Nivel de servicio** = qué percentil de la duración eliges para prometer.

**Fase 1 — ENTREGADA: clasificación `entrega_tarde` (target A, V1.3.0).**
Vista de "riesgo de romper la promesa *actual*". Se conserva: es trabajo válido y aporta
el cimiento reutilizable (features [t0], pipeline, split temporal, anti-leakage).

**Fase 2 — PORTADORA DEL VALOR (recomendada; SIN código en estos chats): regresión sobre
`dias_entrega_real` (target C).** Predice la duración real compra→entrega → permite fijar
una **promesa honesta y competitiva** en el momento de la compra.

**Por qué C y no seguir solo con A:**
- La palanca de §7.1.6 ("afinar la estimación") es **continua**, no binaria.
- **C contiene a A:** del reloj de días se deriva "¿tarde?" contra *cualquier* promesa;
  de la alarma binaria no se recupera el reloj.
- A predice contra un blanco que Olist **infló** (~13 días); C es físico e independiente
  de esa política. El punto legítimo de D-20 (el cliente reacciona a la promesa rota) lo
  **preserva** C: sigues protegiendo la promesa y además puedes ponerla mejor.
- Reconcilia la nota pendiente del propio equipo (`decisiones_fe.md`), **corrigiendo el
  target**: regresión sobre **C (duración)**, NO sobre B (`dias_vs_promesa`, sesgado).

**Usuario destino:** el sistema/equipo de Olist que fija la fecha prometida que ve el
comprador (modelo → promesa → cliente final). NO "operaciones que intervienen una orden"
(palanca débil en un marketplace con logística de terceros, y demasiado tarde en M0).

**Límites declarados (honestidad de auditor):**
- El dataset **no permite medir** el costo de sobre-prometer (sin clickstream/funnel): el
  valor de afinar la promesa se argumenta por lógica de e-commerce + el colchón medido,
  **no** se prueba con conversión de Olist.
- Afinar la promesa **sube la tasa de incumplimiento por construcción** → exige una
  **política de nivel de servicio** (qué percentil prometer) que decide el negocio. Eso
  va en el Project Charter (Chat 2).

---

## 6. Señal descriptiva que justifica las 16 features (reencuadre de D1a–D2)

> Ya **no** se explora aquí: el EDA del equipo (`02_EDA_VERTEX.ipynb`,
> `03_EDA_VERTEX.ipynb`) y las importancias del modelo (`etapa4_metrics.json`) ya
> contienen la señal. El trabajo del DVA es **documentar** esa señal y por qué las 16
> features son legítimas y suficientes, no re-correr el análisis.

| Grupo (plan) | Features [t0] del modelo | Dónde vive la evidencia | Lo que dice |
|---|---|---|---|
| G1 Geografía + distancia | `customer_state`, `seller_state`, `dist_haversine_km`, `mismo_estado` | `02_EDA` §7 (regional) + importancias | **El driver #1.** `customer_state_SP/RJ/MG` + `mismo_estado` dominan las importancias; la distancia cruda pesa poco (0.023): manda la región, no los km. |
| G5 Temporales | `mes_compra`, `dia_semana_compra` | `02_EDA` §6.4 + `03_EDA` §6 | Estacionalidad real; `mes_compra` entre las top. Ojo régimen 2018 (R-14/D-29). |
| G2 Físicas del envío | `peso_total_g`, `volumen_total_cm3`, `flete_total`, `ratio_flete` | `02_EDA` §6.2–6.3 | Drivers legítimos pero suaves (flete débil, confirmado en Nivel 2). |
| G3 Categoría | `categoria_principal` | `02_EDA` §6.3 | Tipo de producto como contexto logístico. |
| G4 Valor / pago | `precio_total`, `n_items` | `02_EDA` §6 | Tamaño/complejidad de la orden. |
| G6 Vendedor (point-in-time) | `tasa_vendedor`, `sin_historial_vendedor` | `02_EDA` §6.1/6.1-bis + `decisiones_fe.md` | Feature potente y blindada: expanding, mínimo 5 órdenes previas, respaldo global 9.03%, flag para el 11.57% sin historial. Peso 6% en test (sin fuga; R-12). |

**Síntesis para el veredicto §7.3 (se redacta en Chat 2):** el riesgo #1 del DVA —que lo
único predictivo fuera leakage— queda descartado: las palancas son todas de M0 (región,
vendedor, físicas) y discriminan de verdad (lo confirma que el modelo supera el baseline:
PR-AUC 0.124 vs piso 0.066). La viabilidad de P1 se sostiene; el límite es la magnitud de
la señal, no su honestidad.

---

## 7. Los 3 targets (construidos en D0-pre; framing ya marcado)

| Target | Tipo | Descripción | Rol tras la decisión |
|---|---|---|---|
| A `entrega_tarde` | Clasificación | ¿Rompió la promesa? (1/0) | **Fase 1 — entregada** (V1.3.0) |
| B `dias_vs_promesa` | Regresión | Días de desvío vs promesa | **Descartado** (sesgado por el colchón; prohibido como target) |
| C `dias_entrega_real` | Regresión | Duración real compra→entrega | **Fase 2 — recomendada** (portadora del valor) |

---

## 8. Resumen del embudo (para contexto)

```
NIVEL 0 — 12 dolores → 5 candidatos (P1–P5)                         ✔ CERRADO
NIVEL 1 — Filtro: P1 limpio, P2/P3 con bandera, P4/P5 descartados   ✔ CERRADO
NIVEL 2 — Reviews/drivers: P2 independiente, P3 propio, P1 regional ✔ CERRADO
PUNTO DE DECISIÓN — elegido P1 (D-18)                               ✔ CERRADO
NIVEL 3 — DVA de P1: D0-pre ✔, D0 ✔; D1a–D2 = documentar (no
          re-explorar) la señal del EDA del equipo                  ◄── reconciliado
FRAMING — clasificación (Fase 1) + regresión-C (Fase 2)            ✔ MARCADO (este chat)
PENDIENTE (Chat 2) — Project Charter + veredicto narrativo §7.3
```

---

## 9. Mapa de archivos clave

> **Consolidación de carpetas (acción del equipo):** las reglas del agente deben vivir en
> UNA sola carpeta, `.agents/rules/`. Hoy `context.md` está en `.agent/` (singular). Mover
> con: `git mv .agent/rules/context.md .agents/rules/context.md` y borrar la carpeta vacía
> `.agent/`. El puntero en `AGENTS.md` ya quedó corregido a `.agents/rules/context.md`.

### En `dva_olist` (local, NO GitHub)
- `Bitacora_Maestra_Olist_v0.11.md` — índice + decisiones de una línea
- `Problem_Discovery_DVA_Report_v0.4.md` — narrativa del razonamiento
- `nivel3_dva_p1.ipynb` — DVA de P1 (D0-pre, D0)

### En el repo (`vertex-insights-olist-recommender`)
- `AGENTS.md` — reglas siempre activas (versión corregida)
- `.agents/rules/context.md` — contexto técnico del repo (movido desde `.agent/`)
- `.agents/rules/project-context.md` — este archivo
- `notebooks/02_EDA_VERTEX.ipynb`, `notebooks/03_EDA_VERTEX.ipynb` — EDA del equipo
- `docs/bitacora_decisiones.md` — decisiones D-01…D-29
- `docs/decisiones_fe.md` — feature engineering de P1
- `src/features/build_dataset.py` — ETL + features
- `src/models/train.py` — entrenamiento
- `reports/etapa4_metrics.json` — métricas V1.3.0
- `reports/Problem_Discovery_DVA_Report_v0.4.md` — copia del Report (entregable)
