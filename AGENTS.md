# Proyecto Olist — P1 Desempeño de entrega (DVA ↔ repo reconciliados)

## Misión del agente

Continuar el desarrollo del proyecto de datos Olist. Mi plan razonado vive en la
carpeta `dva_olist` (Bitácora Maestra = fuente de verdad interna; Problem Discovery &
DVA Report = narrativa). El trabajo del equipo vive en este repo, que **ya entrenó un
modelo** (Etapa 4 cerrada, V1.3.0). Tu trabajo:

1. **Entender mi plan** — lee la Bitácora y el Report antes de proponer nada.
2. **Comparar plan vs. repo** — la narrativa DVA y el código del repo corrieron en
   PARALELO y se reconciliaron (ver `project-context.md`, "Divergencias plan↔repo").
   La narrativa NO antecede al modelo: lo EXPLICA y lo encuadra.
3. **Adaptarte a las exigencias del repo** — respeta la estructura, convenciones y stack existentes.
4. **Continuar mi actividad** creando archivos NUEVOS que avancen el análisis.

> **Detalle técnico completo** (stack, arquitectura, reglas de código, git, tests, modelo):
> ver `.agents/rules/context.md`. Este archivo es el resumen ejecutivo; aquel es la
> referencia técnica.

---

## Restricciones DURAS (no negociables)

1. **NUNCA edites archivos existentes** (`.py`, `.ipynb`, `.md`, configs). Solo CREA archivos
   nuevos que complementen el análisis. Si algo existente está mal, propónlo en el plan,
   no lo toques. (Las correcciones a estos archivos del agente se entregan como versiones
   nuevas completas para que el equipo las reemplace, nunca editadas en sitio.)
2. **SIEMPRE genera el Artifact de plan** (implementation_plan) y espera mi aprobación
   antes de ejecutar cualquier cambio. No auto-ejecutes.
3. **Responde en español.** Explica la jerga técnica (inglés + traducción) la primera vez
   que la uses.
4. **No subas la Bitácora a GitHub** (es interna, vive en `dva_olist`). El Report SÍ es
   entregable de GitHub (va a `reports/`).
5. **Nivel del usuario: básico.** No asumas conocimiento previo de scikit-learn, Git
   avanzado, Docker, APIs o arquitectura de ML. Usa analogías simples. Muestra comandos
   completos con explicación de cada flag.

---

## Hogares de la documentación (no mezclar)

| Documento | Dónde vive | Regla |
|---|---|---|
| Bitácora Maestra | `dva_olist/` (local, NO GitHub) | Índice + decisiones de una línea. Fuente de verdad interna. |
| Problem Discovery & DVA Report | `reports/` (GitHub) | Narrativa del razonamiento. Entregable de GitHub. |
| Project Charter, Data Dictionary, Decision Log, Model Card, etc. | `docs/` (GitHub) | Entregables del equipo. |
| Reglas del agente | `AGENTS.md` (raíz) + `.agents/rules/` | Contexto siempre activo para el agente. **Una sola carpeta** (`.agents/rules/`); ya no `.agent/`. |

---

## Principio anti-leakage (regla permanente para features de P1)

> **Data leakage** (fuga de información) = usar como pista algo que solo se conoce
> *después* del momento de predecir. Es el riesgo #1 del proyecto.

**Regla única:** una columna es feature válida SOLO si su valor se conoce en el
**momento de la compra (M0)**. Lo que aparece después (despacho M2, entrega M3,
reseña M4) es leakage y se descarta.

**Columnas prohibidas como features:**
```
order_delivered_carrier_date, order_delivered_customer_date,
delivery_days, delivery_delay_days, is_late_delivery,
review_count, avg_review_score, min_review_score,
max_review_score, has_review_comment, review_comment_titles,
review_comment_messages, last_review_creation_date,
last_review_answer_timestamp, is_dissatisfied,
entrega_tarde (target), dias_vs_promesa
```

> **Nota sobre la Fase 2 (regresión).** El target propuesto para la regresión es
> `dias_entrega_real` (duración real compra→entrega). Como TARGET es legítimo (las
> etiquetas siempre se conocen a posteriori); lo que NO cambia es que las FEATURES
> siguen siendo solo las [t0] de arriba. `dias_vs_promesa` permanece prohibido como
> target (sesgado por el colchón de la promesa) y como feature.

**Señales de alerta:** ROC-AUC o PR-AUC > 0.99 → probablemente hay fuga → revisar.

---

## Estado actual (junio 2026) — REPO Y NARRATIVA RECONCILIADOS

**Fase del repo:** **Etapa 4 (Modelado) CERRADA, tag V1.3.0.** El equipo ya entrenó un
clasificador `entrega_tarde` (XGBoost). Métricas en test: ROC-AUC 0.703, PR-AUC 0.124
(`reports/etapa4_metrics.json`). NO estamos "antes de modelar".

**Fase de la narrativa DVA:** corre en paralelo y AHORA reconcilia lo construido. El
"EDA pendiente" que listaba el plan (D1a–D2) **ya está cubierto** por el EDA del equipo
(`notebooks/02_EDA_VERTEX.ipynb` Etapa 2 y `03_EDA_VERTEX.ipynb` Etapa 3). Por eso esas
celdas se reencuadran: de "explorar antes de modelar" a **"documentar la señal
descriptiva que explica el desempeño del modelo y justifica las 16 features"** (ver
`project-context.md`).

**Decisión de framing — MARCADA (ya no "abierta"):**
- **Fase 1 (ENTREGADA):** clasificación `entrega_tarde` (V1.3.0). Vista de riesgo de
  incumplir la promesa actual. Se conserva; es la base reutilizable (features [t0],
  pipeline, split temporal, anti-leakage).
- **Fase 2 (portadora del valor; recomendada, SIN código aún):** regresión sobre
  `dias_entrega_real` (target C) para **afinar la promesa de entrega** que ve el cliente.
- **Usuario destino:** el sistema/equipo de Olist que fija la fecha prometida en la
  compra (modelo → promesa → cliente final), NO "operaciones que intervienen una orden".
- No es redirección: es re-priorización. Reusa todo el cimiento del repo.

**Pendiente (Chat 2, no en este contexto):** Project Charter completo y cierre del
veredicto narrativo §7.3 del Report. **Sin código/entrenamiento en estos chats de
reconciliación.**

**Detalle vivo:** `dva_olist/Bitacora_Maestra_Olist_v0.11.md` (§1, §5) y
`.agents/rules/project-context.md`.

---

## Punteros clave

- **Bitácora Maestra:** `dva_olist/Bitacora_Maestra_Olist_v0.11.md`
- **Report (narrativa):** `reports/Problem_Discovery_DVA_Report_v0.4.md`
- **Contexto técnico del repo:** `.agents/rules/context.md`
- **Estado DVA + divergencias:** `.agents/rules/project-context.md`
- **Notebook DVA P1:** `dva_olist/nivel3_dva_p1.ipynb`
- **EDA del equipo (señal descriptiva):** `notebooks/02_EDA_VERTEX.ipynb`, `notebooks/03_EDA_VERTEX.ipynb`
- **Decisiones del equipo:** `docs/bitacora_decisiones.md` (D-16 pivote, D-20 target, D-27 XGBoost)
- **Modelo actual (V1.3.0):** `artifacts/modelo_p1.joblib` + `reports/etapa4_metrics.json`
