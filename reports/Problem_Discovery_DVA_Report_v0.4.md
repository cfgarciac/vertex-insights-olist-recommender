# Problem Discovery & Data Viability Report — Recomendador / Olist

> **Documento de la Guía §3.** Recopila TODO el proceso de descubrimiento del problema y la evaluación de viabilidad: desde la hipótesis del cliente, pasando por el embudo (Niveles 0–3), hasta el veredicto. Vive en GitHub `/docs`. Es la **fuente de verdad** narrativa del proyecto y la base de la que luego se derivan el **informe ejecutivo** y la **presentación** para stakeholders de Olist (plataforma + cliente + sellers).

---

## 0. Estado del documento

- **Estado:** BORRADOR (captura cruda, append-only — *no* es prosa de venta todavía; eso se compone al final).
- **Alcance redactado hasta ahora:** **Niveles 0, 1, 2 del embudo + Punto de Decisión + Nivel 3 de P1.** Nivel 0 (descubrimiento), Nivel 1 (filtro + fichas), Nivel 2 (§7.1), Punto de Decisión (§7.2) y el **DVA de P1** (§7.3: universo, targets, anti-leakage, señal descriptiva, feature de vendedor y veredicto final). Capturado en caliente al cierre de cada fase.
- **Secciones pendientes (stubs):** §3 backfill (DVA item-to-item, de chat previo). El veredicto de viabilidad de P1 ya queda cerrado en §7.3.3.
- **Regla de mantenimiento:** cada nivel del embudo, al cerrarse, vuelca aquí su razonamiento, conclusiones y decisiones-con-su-porqué. Solo se **añade**; no se reescribe lo anterior. La composición persuasiva (informe + deck) ocurre una sola vez, al final.

---

## 1. Contexto y objetivo *(frame breve — fuente: Bitácora §1)*

Actuamos como una **consultora de datos**; en el ejercicio, Olist nos confió encontrar el dolor de negocio que más le aqueja. El cliente **sugirió** una solución: un recomendador **item-to-item**. La pusimos a prueba con un DVA completo y el veredicto fue **viable pero limitado** (co-compra escasa: 3.3% de órdenes con 2+ productos; ~97% de clientes compran una sola vez). En lugar de aceptar esa solución como final, **pivotamos a un descubrimiento de problema**: verificar si existe un dolor *mayor* que estos datos sostengan mejor —notando que las tablas `reviews` y `geolocation`, ricas, quedaron sin explotar—.

**Pregunta madre del descubrimiento:** *¿cuál es el dolor de Olist con más valor de negocio que estos datos puedan sostener?*

---

## 2. Marco metodológico *(frame — versión canónica completa en Bitácora §2)*

**Embudo Descubrimiento–DVA.** Descubrimiento (negocio) y DVA (datos) no son fases en fila: son dos preguntas que se persiguen juntas —"¿qué dolor vale más?" y "¿los datos lo sostienen?"— a lo largo de un embudo que descarta candidatos por niveles (0→3).

**Sustituto del SME.** No contamos con un *Subject-Matter Expert* (experto de dominio de Olist). Lo reemplazamos con tres fuentes:
1. **Dominio público** del e-commerce (dolores universales: logística, retención, calidad de vendedores, satisfacción).
2. **Qué midió Olist** — el diseño del dataset revela sus prioridades.
3. **La voz del cliente** — 99k reseñas con puntuación y texto.

**Dónde entra el código.** Niveles 0–1 son razonamiento de negocio (sin código nuevo; reuso del notebook `dva.ipynb` para precisar). El código entra recién en Nivel 2 (mínimo) y Nivel 3 (a fondo).

---

## 3. Hipótesis del cliente: recomendador item-to-item

> **STUB — pendiente backfill del chat del DVA item-to-item.**
> Resumen de una línea: el DVA mostró que item-to-item es **viable pero limitado** por la escasez de co-compra (3.3%) y el patrón de compra única (~97%). **item-to-item NO se descarta del proyecto:** queda registrado como la hipótesis del cliente que investigamos con rigor — es el gancho de la narrativa de consultora ("probamos lo que pidió y lo demostramos con datos"). Sale del *pool* que compite por ser el problema elegido, pero permanece en la historia.

---

## 4. Nivel 0 — Descubrimiento del universo de dolores

*Sin código. Razonamiento de negocio cruzando las tres fuentes del sustituto del SME.*

### 4.1 Lectura del diseño del dataset como pistas de negocio

**Técnica empleada.** El esquema (*schema*) de una empresa es un **fósil de sus prioridades**: lo que decide medir, almacenar y a qué nivel de detalle revela qué intentaba gestionar. Se lee en tres capas: (1) qué entidades existen, (2) qué columnas guardó en cada una, (3) la granularidad y los pares (p. ej., guardar fecha *estimada* **y** *real* de entrega solo tiene sentido si querías compararlas). Como no hay SME, "leer lo que Olist midió" es nuestro mejor sustituto: es la prioridad **revelada**, no la declarada.

**Pistas más fuertes detectadas:**

| Pista en el diseño | Qué revela que le importaba | Fuerza |
|---|---|---|
| `orders` guarda 4 sellos de tiempo del viaje (compra → aprobación → entrega al transportador → entrega al cliente) **+ fecha estimada de entrega** | Quería **calificarse contra su propia promesa**. Una estimación solo se guarda para medir si se cumple. | Muy fuerte |
| `order_items.shipping_limit_date` (fecha límite de despacho del vendedor) | Vigila si **el vendedor despacha a tiempo** — un SLA (acuerdo de nivel de servicio) por vendedor. | Fuerte |
| `reviews`: nota + título + texto libre + fechas; encuesta disparada al recibir el producto o vencer la fecha estimada | Mide satisfacción **y quiere saber el porqué** (texto libre), y la **ata a la entrega**. | Muy fuerte |
| Tabla `geolocation` aparte (1M filas, zip→lat/lng) + `freight_value` por ítem + dimensiones/peso del producto | Le importan la **distancia vendedor↔comprador** y el **costo de envío** (el flete se calcula de ahí). | Fuerte |
| `customer_unique_id`, creado a propósito para detectar recompra | Quería **poder ver si el cliente vuelve**: retención en el radar. | Media |
| `products`: largo del nombre, largo de la descripción, # de fotos | Midió la **calidad del anuncio**. Es de los pocos datos *pre-compra* que guardó. | Media |
| Tabla `sellers` + `seller_id` por ítem (varios vendedores por orden) | El **desempeño/calidad del vendedor** es un objeto de gestión del marketplace. | Media |

**Hallazgo central — la asimetría post/pre-compra.** Todo lo que Olist instrumentó con detalle es **post-compra**: entrega, satisfacción, flete, distancia, recompra. Lo que **brilla por su ausencia** es cualquier rastro **pre-compra**: ni clics, ni vistas, ni búsquedas, ni sesiones, ni carrito (verificado: cero columnas de navegación en las 47 totales). 

Esto explica de raíz por qué item-to-item salió *viable pero limitado* —el recomendador vive en el mundo pre-compra, justo donde los datos son más delgados— y **dónde vive probablemente un dolor mayor y mejor sostenido: la experiencia post-compra** (entrega + satisfacción). Dicho como negocio: *los datos sugieren que la obsesión de Olist era llevar el paquete a tiempo y mantener contento al cliente, no ayudarlo a descubrir más productos.*

**Límite honesto de la técnica (registrado).** "Lo que Olist midió" es la prioridad *revelada*, no necesariamente el dolor *más valioso sin resolver* — esto es **sesgo de instrumentación** (*instrumentation bias*): una empresa puede no haber medido su punto ciego. Que no haya *clickstream* no significa que el descubrimiento no importe al negocio; significa que es invisible para nosotros. Por eso el esquema se cruza con el dominio público; es necesario pero no suficiente.

### 4.2 Lluvia de dolores: 12 candidatos desde tres lentes

Cruzando las tres fuentes emergió un universo amplio (boca ancha del embudo, sin filtrar):

**Lente 1 — Lo que Olist midió:** entrega tardía · mejor estimación de entrega · despacho lento del vendedor · anticipar/explicar insatisfacción · calidad del anuncio · calidad/curaduría de vendedores · cancelaciones.

**Lente 2 — Dominio público del e-commerce:** baja recompra/retención (*churn*) · fricción por flete.

**Lente 3 — Voz del cliente (reseñas con texto):** minería de texto de reseñas (NLP — *Natural Language Processing*) para descubrir temas de queja.

**Hipótesis del cliente (en la mesa, fuera del pool):** item-to-item.

### 4.3 La cadena causal: raíz vs. síntoma

Al organizar los 12, salta que **varios no son dolores independientes, sino la misma cadena vista desde puntos distintos**:

```
[ raíz · operativo · se puede actuar ]                         [ síntoma · se mide ]
Despacho lento del vendedor → Entrega tardía → Cliente insatisfecho → Mala reseña (review_score)
```

Por la regla **raíz-vs-síntoma** (atacar la causa, no el síntoma), buena parte de los candidatos logísticos y de satisfacción **colapsan en un solo problema**: la entrega. Subir el `review_score` no es un proyecto aparte — es lo que ocurre *si* se arregla la entrega. En cambio, sí viven **fuera** de esta cadena: retención (P4) y fricción por flete (P5), y —en otra dimensión— la curaduría de vendedores (P3). El universo quedó honesto: un centro de gravedad logístico fuerte **y** una constelación real de alternativas. La respuesta no está cantada.

### 4.4 Consolidación a 5 candidatos + descartes

**Descartados en el Nivel 0 (con razón):**
- **Calidad del anuncio** — su *resultado* (la conversión) no es medible sin datos de navegación, que no existen. La materia prima para *evaluar* el dolor es débil → sale temprano.
- **item-to-item como candidato que compite** — el DVA ya lo resolvió (viable pero limitado) y el pivote existió para buscar algo mayor. **No se borra:** permanece como la hipótesis del cliente investigada (§3), fuera del pool de selección.

*Criterio de fusión:* se agrupó por **identidad del dolor** (¿es el mismo dolor visto desde otro ángulo?), **no** por mérito — juzgar si duele/es accionable/los datos lo sostienen es el filtro del Nivel 1, no se tocó aquí.

---

## 5. Los 5 candidatos resultantes (P1–P5)

**P1 · Desempeño de entrega (cumplir la promesa).** Olist promete una fecha estimada y la incumple; la tardanza erosiona confianza. *Fusiona:* entrega tardía + despacho lento del vendedor + mejor estimación de entrega (la causa y sus palancas). *Tensión para el filtro:* es la raíz de la cadena causal; probablemente "absorbe" parte de P2.

**P2 · Satisfacción del cliente (causas + anticipación).** El cliente queda insatisfecho y lo deja en `review_score`; Olist quiere saber por qué e intervenir. *Fusiona:* anticipar insatisfacción + entender sus drivers + minería de texto de reseñas (NLP es una *técnica* al servicio del dolor, no un dolor aparte). *Tensión para el filtro:* solapa fuerte con P1. Por la regla raíz-vs-síntoma, si la entrega es el driver dominante, P2 se vuelve el síntoma de P1. **Pregunta empírica clave:** ¿cuánta insatisfacción NO viene de la entrega? → se resuelve con código en el Nivel 2.

**P3 · Calidad / curaduría de vendedores.** El marketplace vive de su reputación; algunos vendedores generan retrasos, cancelaciones y quejas. *Fusiona:* calidad de vendedores + cancelaciones. *Tensión para el filtro:* solapa con P1, pero mirado desde la **entidad vendedor** (a quién premiar/penalizar) en vez del pedido. Como P1 ya absorbió "despacho lento", P3 debe quedarse con la dimensión que P1 NO cubre (calidad de producto, cancelaciones) para no contar doble. Cancelaciones es volumen pequeño (~1.3k).

**P4 · Retención / recompra.** ~97% compra una sola vez; adquirir clientes cuesta y no vuelven (*churn*). *No fusiona* — vive fuera de la cadena de entrega. *Tensión para el filtro:* los datos miden bien *el problema*, pero pueden ser delgados en *causas accionables*, y hay una duda de fondo (¿la relación con el cliente la "posee" Olist o el vendedor?).

**P5 · Fricción por flete (costo de envío).** El flete caro frena o molesta la compra. *No fusiona* — es sobre dinero/costo, distinto de "llega tarde". *Tensión para el filtro:* su *resultado* (ventas perdidas) no es medible sin navegación; se entrelaza con distancia (geolocation) y con P1/P3.

> **Mapa de dependencias (insumo para el filtro):** P1↔P2 (síntoma posible), P1↔P3 (doble conteo a evitar), P4 y P5 independientes. **Riesgo a vigilar:** sesgo de confirmación hacia P1/P2/P5 por usar las tablas "vistosas" (`reviews`/`geolocation`). Juzgar por mérito en las compuertas, no por qué tabla es más atractiva.

---

## 6. Nivel 1 — Filtro de negocio + olfato de datos

*Razonamiento de negocio + olfato de datos. **SIN código nuevo:** se reusó lo ya verificado en `dva.ipynb` (leerlo para precisar es Nivel 1; correr algo nuevo sería Nivel 2). Instrumento por candidato: **mini-ficha de 4 datos** (dolor · problema concreto · target candidato · palanca) pasada por **3 compuertas** (¿duele? · ¿accionable? · ¿materia prima?: PASA / MUERE / INCIERTO→bandera). El Nivel 1 **FILTRA, no rankea**: decide quién sobrevive, no quién gana (elegir UN problema es el punto de decisión, **después** del Nivel 2).*

### 6.1 Mapa de solapes ejecutado (P1↔P2↔P3)

Se mapearon las dependencias **antes** de juzgar, para no contar doble ni matar el eslabón equivocado. Idea central: **P2 está "río abajo"** — P1 y P3 son causas candidatas; P2 es donde esas causas se *miden* (vía `review_score`).

```
            P3 Vendedores
       (causa: calidad / despacho)
          │                 │
     (hipótesis)       (hipótesis)
          ▼                 ▼
     P1 Entrega ───────▶ P2 Satisfacción
       (causa)  (hipótesis)  (síntoma: se mide en review_score)

   P4 Retención · P5 Flete → fuera del solape (independientes)
```

Relaciones (todas **hipótesis causales**, NO medidas — se confirman en Nivel 2):
- **P1 → P2:** entrega que incumple la promesa → peor reseña.
- **P3 → P2:** mal vendedor (producto / despacho / cancelación) → peor reseña.
- **P3 → P1:** el despacho lento del vendedor *es parte del* resultado de entrega → **doble conteo a vigilar**: el `seller` toca P1 (componente de entrega) y P3 (calidad del vendedor) con dos lentes distintos.
- **Superficie compartida:** `review_score` es el termómetro común. Atacar el termómetro (subir la nota) sin tocar las causas sería atacar el síntoma.

> **Tensión central registrada (sigue ABIERTA):** parte de la "insatisfacción" (P2) puede ser el síntoma de la entrega (P1). *Cuánta* NO viene de la entrega es **empírico → Nivel 2**; no se decide en el filtro.

### 6.2 Evidencia reusada del notebook — y un vacío que define el Nivel 2

Se leyó `dva.ipynb` completo (sin correr nada nuevo). Hechos **verificados con datos** que alimentan el filtro:
- Integridad referencial impecable; catálogo 100% vendido (32,951/32,951). `[ver]`
- Co-compra escasa (3.3% de órdenes con 2+ productos) y **96.9% de personas compran una sola vez**. `[ver]`
- CTR no medible: barrido de las 47 columnas → ninguna de navegación/clics. `[ver]`
- AOV: promedio R$ 137.75 (solo productos), R$ 160.99 con flete; mediana R$ 86.90. `[ver]`
- Timestamps del ciclo de entrega **casi completos**; `review_score` **100% poblado**. `[ver — pero ver el vacío abajo]`

**Vacío crítico (verificado al leer el notebook):** las reseñas **nunca se analizaron**. `order_reviews` quedó explícitamente fuera de alcance del DVA ("futuro / v2"). Lo único confirmado de `review_score` es su **presencia** (100% poblado), **NO su contenido**: no hay distribución de notas, ni minería de texto, ni cruce nota↔entrega. Por eso "qué dicen los clientes" es **materia de Nivel 2**, y por eso P2 y P3 salen del filtro **con bandera**.

### 6.3 El filtro: P1–P5 por las 3 compuertas

> **Marcado de evidencia:** sin SME, la mayoría de los "¿duele?" son **argumentados** (dominio público + inferencia del diseño que midió Olist), no **medidos**. Se marca `[arg]` lo argumentado y `[ver]` lo verificado con datos.

**P1 · Entrega** — *mini-ficha:* incumple la fecha prometida · anticipar órdenes en riesgo de tardar · target "tarde sí/no" o "días de retraso" (estimada vs. real) · palanca alertar/priorizar/ajustar promesa.
- ¿Duele? **Sí** `[arg, fuerte]`: Olist guardó fecha estimada **Y** real + ciclo completo de timestamps (solo se mide lo que importa); Kaggle lo lista como uso esperado; puntualidad = dolor universal.
- ¿Accionable? **Sí**: palancas reales; demostrable end-to-end con históricos.
- ¿Materia prima? **PASA** `[ver]`: timestamps casi completos. *Nota:* las no-entregadas/canceladas no tienen fecha real (ausencia informativa, no hueco ciego → manejo en Nivel 2).
- **Veredicto: PASA — limpio.** El más sólido en datos.

**P2 · Satisfacción** — *mini-ficha:* clientes insatisfechos a anticipar/entender · predecir/explicar insatisfacción + driver analysis · target `review_score`/`insatisfecho`(≤2) · palanca depende del driver.
- ¿Duele? **Sí** `[arg + señal de diseño]`: encuesta post-compra activa; `review_score` 100% poblado `[ver]`; 99k reseñas existen.
- ¿Accionable? **Sí, con matiz**: predecir insatisfacción es accionable, pero "actuar sobre P2" puede ser actuar sobre P1/P3 → bandera.
- ¿Materia prima? **PASA** `[ver, presencia]`: nota poblada + texto disponible. (La bandera **no** es de materia prima; es de raíz-vs-síntoma.)
- **Veredicto: PASA con bandera.** *Bandera:* ¿cuánta insatisfacción es independiente de la entrega? → Nivel 2 (bloque reviews).

**P3 · Vendedores** — *mini-ficha:* vendedores flojos erosionan la confianza · score de riesgo/calidad por vendedor · target **a construir** · palanca advertir/despriorizar/desvincular/onboarding.
- ¿Duele? **Sí** `[arg]`: el modelo de Olist es conectar vendedores pequeños (su calidad es existencial); registra resultados de fulfillment incl. cancelaciones; Kaggle ("categorías propensas a insatisfacción").
- ¿Accionable? **Sí**: palanca de curaduría clara; demostrable construyendo el score con históricos.
- ¿Materia prima? **PASA con reservas** `[ver, parcial]`: existe `seller_id` por ítem, nota cruzable a vendedor, tiempos de despacho. *Reservas:* (a) target a construir; (b) cancelaciones delgadas (casi todo `delivered`); (c) estadísticas ralas en la cola de vendedores con pocas órdenes.
- **Veredicto: PASA con bandera.**

**P4 · Retención** — *mini-ficha:* pocos vuelven · predecir recompra · target "recompró sí/no" (`customer_unique_id`) · palanca campañas de retención.
- ¿Duele? **Débil** `[arg, genérico]`: real en dominio público, pero SIN señal de que sea prioridad de Olist (no guardaron nada de fidelización/CRM) y la voz del cliente no habla de esto.
- ¿Accionable? **Marginal**: depende de poder predecir la recompra → compuerta 3.
- ¿Materia prima? **Casi vacía** `[ver]`: se puede *etiquetar* la recompra, pero *predecirla* es casi imposible — 97% tiene una sola orden (sin historial por cliente del cual aprender) y la clase positiva (~3%) es un **desbalance extremo**. No es cero literal como el CTR, pero para un modelo útil es prácticamente inexistente.
- **Veredicto: DESCARTADO (confirmado por el equipo).** *(Alternativa considerada y rechazada → §6.6.)*

**P5 · Flete** — *mini-ficha:* el flete pesa sobre órdenes pequeñas (indicativo grueso: ~R$23 sobre orden típica ~R$87 ≈ ¼; derivado de los AOV, a precisar) · caracterizar/estimar la fricción · target `freight_value` o ratio flete/valor · palanca subsidio/umbral envío gratis/match por distancia.
- ¿Duele? **Sí** `[arg]`: el flete es factor #1 de fricción en dominio público; Olist guardó `freight_value` y `geolocation` (mide costo y distancia).
- ¿Accionable? **Sí, con matiz**: la versión fuerte (¿el flete hace abandonar el carrito?) **NO es medible** — no hay datos de navegación/carrito, solo órdenes completadas (muro del CTR).
- ¿Materia prima? **PASA** para versiones descriptivas / **MUERE** para la de abandono `[ver/arg]`.
- **Veredicto: DESCARTADO (confirmado por el equipo), con reubicación.** *(Razón completa → §6.6.)*

### 6.4 Matriz de decisión + mapa de dependencias actualizado

| Candidato | ¿Duele? | ¿Accionable? | ¿Materia prima? | Veredicto |
|---|---|---|---|---|
| P1 Entrega | Sí (fuerte) `[arg]` | Sí | PASA `[ver]` | **PASA — limpio** |
| P2 Satisfacción | Sí `[arg]` | Sí (matiz) | PASA `[ver]` | **PASA con bandera** |
| P3 Vendedores | Sí `[arg]` | Sí | PASA c/ reservas `[ver]` | **PASA con bandera** |
| P4 Retención | Débil/genérico `[arg]` | Marginal | Casi vacía `[ver]` | **DESCARTADO** |
| P5 Flete | Sí `[arg]` | Sí (matiz) | Parcial `[ver/arg]` | **DESCARTADO (reubicado)** |

Tablero tras el filtro:
```
   P3 Vendedores (pasa, bandera)
        │ (impulsa, hipótesis)
        ├───────────────┐
        ▼               ▼
   P1 Entrega ──────▶ P2 Satisfacción (pasa, bandera)
   (pasa, limpio)      ▲  superficie de medición (review_score)
                       ┊ (pregunta Nivel 2: ¿flete → peor nota?)
   [P5 Flete] ·········┘  reubicado como posible DRIVER dentro de P2
   [P4 Retención]  ✗  descartado
```

**Sobrevivientes: P1 (limpio), P2 (bandera), P3 (bandera).** Patrón clave para Nivel 2: **P1 se sostiene solo; P2 y P3 dependen del análisis de reviews** → ese bloque es el **árbitro** entre los tres.

### 6.5 Fichas completas (6 elementos) de los sobrevivientes

> **Términos (una vez):** *clasificación* = predecir una categoría (tarde sí/no); *regresión* = predecir un número (días); *recall* = de los positivos reales, cuántos atrapé; *precision* = de los que marqué positivos, cuántos acerté (importan cuando la clase es minoría, la "exactitud" engaña); *data leakage (fuga de información)* = usar como pista algo que solo se conoce *después* del momento de predecir; *driver analysis* = medir cuánto pesa cada factor sobre un resultado. Métricas = **propuesta**; la definitiva se cierra en el Evaluation Report.

**FICHA — P1 · Entrega**
1. **Dolor de negocio:** incumplir la fecha prometida → molestia, malas reseñas visibles, reclamos, pérdida de confianza; depende de logística + despacho del vendedor (punto frágil). `[arg, con señal de diseño fuerte]`
2. **Problema concreto:** anticipar (al comprar o al despachar) qué órdenes están en riesgo de tardar vs. la fecha prometida. *Variante:* mejor estimación de la fecha mostrada. (Cuál es el principal → Decision Log.)
3. **Tarea ML:** clasificación binaria (tarde sí/no) principal; regresión (días) variante.
4. **Variable objetivo:** `entrega_tarde = (order_delivered_customer_date > order_estimated_delivery_date)`. *Construcción:* canceladas/no-entregadas no tienen fecha real → decidir tratamiento (Nivel 2).
5. **Métricas (propuesta):** *téc* recall/precision sobre "tarde" + AUC (clase minoritaria, no exactitud); *neg* % de retrasos detectados a tiempo; (hipotético en prod) reducción de reseñas negativas por entrega.
6. **Accionabilidad:** alertar al cliente, priorizar despacho, ajustar la promesa en checkout, presionar SLA de vendedores lentos. End-to-end con históricos.
> **Bandera técnica (data leakage):** no usar features conocidas solo tras la entrega (p. ej. la fecha real). Predecir con lo disponible al momento de compra/despacho. Es el riesgo #1 de P1.

**FICHA — P2 · Satisfacción** *(con bandera)*
1. **Dolor de negocio:** insatisfacción → no vuelve + mala reseña visible → daño reputacional; Olist mide satisfacción a propósito (encuesta post-compra). `[arg + señal de diseño]`
2. **Problema concreto:** (a) predecir mala reseña *antes* de que ocurra (intervenir); (b) **driver analysis** — qué pesa (entrega/vendedor/producto/flete). El corazón es (b): arbitra entre P1/P2/P3.
3. **Tarea ML:** clasificación (insatisfecho sí/no) para (a); modelo interpretable + importancia de variables para (b); NLP opcional sobre el texto.
4. **Variable objetivo:** `review_score` (1–5) / `insatisfecho` (≤2) `[ver, poblado]`. Para (b): cruzar la reseña con features de entrega (P1), vendedor (P3) y flete.
5. **Métricas (propuesta):** *téc* recall/precision/AUC sobre "insatisfecho" (minoría) + importancia por bloque de drivers; *neg* el **reparto de la insatisfacción por causa** (entrega X% · vendedor Y% · otras Z%) — ese reparto **ES la respuesta a la bandera**.
6. **Accionabilidad:** depende del driver (de ahí la bandera) — invertir en P1 o P3 según domine; soporte proactivo a órdenes en riesgo.
> **Bandera:** si casi toda la insatisfacción viene de la entrega, P2 colapsa en P1 (síntoma) y preferiríamos P1. La resuelve el bloque de reviews (Nivel 2).

**FICHA — P3 · Vendedores** *(con bandera)*
1. **Dolor de negocio:** vendedores que cancelan / despachan tarde / entregan mal erosionan la confianza; curar el roster es existencial para el marketplace. `[arg]`
2. **Problema concreto:** score de riesgo/calidad por vendedor para advertir/despriorizar/desvincular/afinar onboarding.
3. **Tarea ML (honesto):** **no hay etiqueta dada** de "vendedor malo". (a) score compuesto interpretable (cancelación + nota promedio + despacho atribuible al vendedor) → *scoring/ranking*, más que ML predictivo; (b) extensión predictiva: P(mal resultado | atributos) → clasificación. Base = (a), extensión = (b).
4. **Variable objetivo:** **a construir** (bandera). Candidatas: tasa de cancelación / nota promedio / retraso de despacho por vendedor / compuesto. Constructibilidad → Nivel 2.
5. **Métricas (propuesta):** si scoring → estabilidad del orden + si el score *predice* resultados futuros; si clasificación → recall/precision/AUC sobre "mal resultado". *neg* % de cancelaciones/malas reseñas concentrado en el peor X% de vendedores.
6. **Accionabilidad:** advertir/despriorizar/desvincular/onboarding. Palanca muy "de marketplace".
> **Banderas:** (i) target a construir; (ii) cancelaciones delgadas (¿hay suficientes negativos?); (iii) cola de vendedores con pocas órdenes → scores inestables; (iv) **delimitar la frontera con P1** para no contar doble el despacho (P1 ya absorbió "despacho lento"; P3 se queda con la dimensión vendedor que P1 no cubre). Verificar en Nivel 2.

### 6.6 Decisiones derivadas (Nivel 1) — con su porqué y las alternativas descartadas

1. **P2 pasa con bandera** (no "pleno", no muerto). *Alternativas:* (a) declararlo problema pleno —rechazada: afirmaría sin datos que P2 es independiente de P1—; (b) matarlo como puro síntoma —rechazada: afirmaría sin datos lo contrario—. Ambas deciden sin evidencia lo que toca a Nivel 2. El argumento del equipo ("aún no sabemos qué dicen los clientes") **ES la bandera**, no una razón para cerrarla.
2. **P4 descartado (confirmado).** *Alternativa considerada:* mantenerlo con bandera roja (regla "la incertidumbre no mata"). *Rechazada:* gate 1 solo se sostiene en lo genérico **y** gate 3 es casi vacío (sin historial por cliente; desbalance ~3%) → no demostrable end-to-end como problema predictivo. El equipo confirmó el descarte.
3. **P5 descartado (confirmado) + reubicado.** *Distinción importante:* el argumento del equipo ("no sabemos cuánta gente no compró por el flete; eso exige métricas de carrito abandonado/navegación inexistentes") tumba **solo** la versión de **conversión/abandono** (correcto: mismo muro del CTR). La razón **completa** añade que, quitada esa versión, lo que queda no se sostiene como problema independiente: *predecir el flete* ≈ determinista (fórmula peso×dimensiones×distancia, poco ML); *ratio flete/valor* = EDA, no un problema con target/modelo; *flete→insatisfacción* sí es útil, pero eso lo vuelve un **driver (feature) dentro de P2**, no un candidato propio. *Decisión:* descartar como candidato independiente y **reubicar el flete como posible driver de insatisfacción en P2** (no se pierde la parte útil; no se cuenta doble).
4. **El mapa se mantiene honesto:** P5→P2 **NO** se dibujó como flecha asertada, sino como *pregunta para Nivel 2*. Se dibuja solo lo que se sostiene.

> **Handoff a Nivel 2 (no llena §7, solo apunta):** el primer bloque de Nivel 2 es el **análisis de reviews/drivers**, con encargo triple — resolver la bandera de P2 (raíz vs. síntoma), medir el aporte de P3 y probar el flete como driver. Requiere subir los CSV de `reviews`, `orders` e `items`. El veredicto final y el punto de decisión van a §7 cuando ese nivel se ejecute.


---

## 7. Niveles 2–3 + veredicto final

> **Estado:** §7.1 (Nivel 2 — bloque de reviews/drivers) REDACTADO; §7.2 (Punto de
> Decisión) REDACTADO; §7.3 (Nivel 3 de P1 + veredicto final) REDACTADO. Estilo:
> Borrador, append-only, captura en caliente.

---

### 7.1 Nivel 2 — Bloque de reviews/drivers

#### 7.1.0 Encargo y método

El Nivel 1 dejó tres sobrevivientes, dos de ellos *con bandera*: pasaron por la regla
"la incertidumbre no mata", no porque supiéramos que se sostienen. El Nivel 2 existe
para **resolver esas banderas con datos**, con el mínimo código que las conteste. El
encargo de este bloque fue triple:

1. **Bandera de P2** — ¿cuánta insatisfacción NO viene de la entrega? (Si casi toda
   viniera de ahí, P2 colapsaría en P1 como mero síntoma.)
2. **Aporte de P3** — ¿cuánto pesa el vendedor sobre la nota, por encima de la entrega?
3. **Flete como driver** — ¿el flete alto predice peor `review_score`? (P5 fue reubicado
   en el Nivel 1 como posible driver dentro de P2.)

**Por qué este bloque era ineludible.** Hasta aquí, `order_reviews` nunca se había
analizado: el DVA de item-to-item la dejó explícitamente fuera de alcance ("futuro/v2")
y lo único confirmado de `review_score` era su **presencia** (100% poblado), nunca su
**contenido**. Este bloque abre esa caja por primera vez. Lo mismo con `geolocation`:
tabla rica (1M filas zip→lat/lng) que el proyecto no había tocado.

**El método: estratificación.** *Stratification* (estratificación) = en vez de un modelo
que "controle" estadísticamente por la entrega, partimos los datos en grupos —órdenes
*tarde* vs. *puntuales*— y miramos dentro de cada uno. Es la versión honesta y ligera del
control causal. La idea que vertebra todo el bloque: **si entre las órdenes que llegaron
a tiempo todavía hay insatisfacción que varía por vendedor, por flete o por región, esa
parte NO la explica la entrega** → ahí vive el territorio propio de P2 y P3.

```
              Reseñas de órdenes 'delivered'  (review_score 1–5)
                                │
                ┌───────────────┴────────────────┐
                ▼                                 ▼
         ENTREGA TARDE                      ENTREGA PUNTUAL
   insatisfacción ≈ síntoma de P1     insatisfacción = NO es la entrega
   (la explica la tardanza)           → ¿de qué es entonces? (vendedor/flete/otro)
```

**Qué NO se hizo (y por qué), declarado para honestidad del registro:**

- **NLP del texto de las reseñas — diferido a propósito.** El 40.6% de las reseñas trae
  comentario (~39k textos). Minar *de qué* se queja la gente es más pesado y no hace falta
  para responder "cuánta insatisfacción es independiente de la entrega" —eso se resuelve con
  los cruces estructurados de abajo—. Se posterga al EDA o al final del embudo, según el
  problema elegido.
- **No es modelado ni EDA completo.** Son verificaciones quirúrgicas. El método es
  **descriptivo, no causal**: respondemos "¿hay señal independiente?", no "el vendedor
  explica exactamente el X%". La descomposición causal con pesos por driver es modelado
  posterior.
- **El universo `delivered` nos ciega a la insatisfacción por no-entrega** (órdenes
  canceladas/no entregadas), que es dolor puro de P1. Para este bloque está bien, pero se
  recuerda al interpretar.

El flujo de trabajo fue: orientar la celda → correrla en `dva.ipynb` local → pegar el
output → analizar juntos. No se subieron CSV (se evitó gastar tokens en datos crudos).

#### 7.1.1 Higiene y base de trabajo (celda C0)

Antes de cruzar nada, se construyó una **base a nivel orden** y se neutralizó el riesgo
#1 del bloque: el ***fan-out*** (multiplicación de filas al unir tablas de distinta
granularidad). `reviews` y `orders` viven a nivel **orden**; `order_items` vive a nivel
**ítem**. Unir ítems con reseñas sin cuidado convertiría una orden de 3 ítems en 3 filas
con la misma nota repetida, sesgando todo promedio hacia las órdenes grandes. Decisión de
diseño: P1 y P2 se analizan a nivel orden; P3 se analiza solo sobre órdenes **mono-vendedor**.

Hallazgos de higiene (sobre 96,478 órdenes `delivered`):

- **Cobertura:** 95,832 entregadas tienen reseña; solo 646 (0.7%) sin reseña. Universo amplio.
- **Fan-out de reviews:** 547 órdenes con 2+ reseñas y 789 review_id que tocan 2+ órdenes
  (~1% de las filas, casos raros típicos de Olist). Se neutraliza quedándose con la **reseña
  más reciente por orden** ("una orden = su reseña más reciente"). Efecto residual menor,
  anotado.
- **Insumo para C2:** solo 8 entregadas sin fecha de entrega real → se excluyen del cálculo
  de "tarde".
- **Insumo para C3:** 95,203 órdenes con base son **mono-vendedor**; solo 1,278 multi-vendedor.
  La atribución a vendedor es limpia para el 98%+ → **desinfla** la pata "multi-vendedor
  ensucia la atribución" de la bandera de P3. (No resuelve la pata de la *cola rala*; eso se
  mide en C3.)

> Nota de granularidad: el `dva.ipynb` contó 3,197 entregadas con 2+ **productos**; aquí
> salieron 1,278 multi-**vendedor**. No se contradicen: una orden puede llevar varios
> productos de un mismo vendedor (co-compra, pero mono-vendedor). C3 usa mono-vendedor
> (atribución), no mono-producto.

#### 7.1.2 La distribución de review_score (lo nunca hecho) — celda C1

Primer vistazo al **contenido** de la nota (95,832 órdenes con reseña):

| Nota | Órdenes | % |
|---|---|---|
| 1 ★ | 9,352 | 9.76% |
| 2 ★ | 2,921 | 3.05% |
| 3 ★ | 7,916 | 8.26% |
| 4 ★ | 18,888 | 19.71% |
| 5 ★ | 56,755 | 59.22% |

La distribución tiene **forma de "J"**: mayoría de 5★, caída, y **repunte en 1★** (más alto
que el 2★). Típico de e-commerce: quien califica suele estar muy contento o francamente
molesto. Buena noticia para el análisis: el dolor no está diluido, está **concentrado en el
1★**, lo que da una señal nítida.

**Decisión — definición de "insatisfecho" = `review_score ≤ 2` (tasa base 12.81%).** El 3★
queda fuera por ser el neutro literal de la escala (incluirlo contaminaría la señal con gente
que no estaba molesta); el 2★ entra por ser inequívocamente una mala experiencia. La tasa
base de 12.81% es un ***class imbalance*** (desbalance de clases) **sano**: minoría —como debe
ser el dolor— pero suficientemente densa para que las tasas por subgrupo sean estables. De
paso confirma que **P2 no cae en el problema de P4**, cuya clase positiva (~3%) era demasiado
rara para modelar; 12.81% es cuatro veces más densa.

#### 7.1.3 La entrega como árbitro de P2 (celda C2 — la celda madre)

Se construyó `entrega_tarde = (delivered_customer > estimated_delivery)` — tarde respecto a
la **promesa**, que es lo que el cliente percibe— y se miró el dolor desde dos ángulos.

**Ángulo 1 — la brecha (¿cuánto jala la entrega?):**

| Grupo | Órdenes | Insatisfacción (≤2) |
|---|---|---|
| PUNTUAL (a tiempo/antes) | 88,163 | 9.22% |
| TARDE (incumplió promesa) | 7,661 | 54.07% |

Una orden tarde se queja **5.9× más** que una puntual. La entrega **sí** importa, y mucho.

**Ángulo 2 — el reparto (LA RESPUESTA A LA BANDERA):** de las 12,272 reseñas malas (≤2):

| Origen | Reseñas malas | % |
|---|---|---|
| de entregas TARDE | 4,142 | **33.75%** |
| de entregas PUNTUALES | 8,130 | **66.25%** |

> **El 66.2% de la insatisfacción NO la explica la entrega. La entrega explica como mucho
> el 33.8%.** → **P2 NO colapsa en P1: tiene territorio propio.**

**La sutileza que reconcilia ambos ángulos:** la entrega tardía es **muy tóxica pero poco
frecuente**. Hace mucho daño donde aparece (54% se queja), pero aparece en pocas órdenes
(7,661 de 95,824 ≈ 8%). Por eso su contribución *total* al dolor es solo un tercio. El otro
dos tercios arde a fuego bajo (9.22%) pero en las 88,163 puntuales, que en números absolutos
aportan más casos. En lenguaje de negocio: *la entrega tardía es un incendio intenso pero
localizado; la insatisfacción de fondo arde en todas partes, en entregas que sí cumplieron.*
**Arreglar la entrega apagaría como mucho un tercio del problema.**

**El gradiente confirma que la señal es real (no ruido):**

```
  ≤-10 muy antes   8.89%   ┐
  -9 a -5          9.60%   │  PISO ESTABLE ~9-12%  ← dolor de fondo (NO es entrega)
  -4 a -1         11.17%   │
  justo a tiempo  12.42%   ┘
  ─────────────────────────  umbral de la promesa
  1-5 tarde       41.15%   ┐
  6-10 tarde      77.48%   │  SALTO BRUSCO al incumplir la promesa
  11+ tarde       78.86%   ┘
```

Dos hallazgos finos: (a) el salto ocurre exactamente al cruzar la promesa, no en "días
absolutos" —pasar de 0 a 1 día tarde triplica la queja (12%→41%)—, lo que confirma que el
cliente reacciona a la **expectativa rota**; (b) hay un **piso irreducible de ~9-12% incluso
llegando antes de tiempo**, que por construcción no puede ser entrega: es el corazón de P2.

#### 7.1.4 El peso del vendedor (celda C3)

Pregunta del equipo que afinó la celda: *¿puede el vendedor ser también responsable de la
llegada tarde?* Sí — el vendedor toca la nota por **dos caminos**:

```
   CAMINO 1: vendedor → despacho lento → entrega tarde → mala nota   (solapa con P1)
   CAMINO 2: vendedor → producto / descripción / cancelación → mala nota  (P3 puro)
```

Por eso C3 se corrió sobre **todas** las órdenes y luego se filtró a puntuales: la diferencia
separa los dos caminos. Sobre 94,563 órdenes mono-vendedor, 2,944 vendedores; con umbral de
**≥30 órdenes/vendedor** quedan 614 vendedores que cubren el 83% de las órdenes (la "cola rala"
de la bandera queda **desinflada**: hay base amplia y estable).

**A — ¿la nota varía entre vendedores? (TODAS):** dispersión **ancha**.

| Percentil | p10 | p25 | p50 | p75 | p90 |
|---|---|---|---|---|---|
| Insatisfacción | 4.63% | 7.25% | 10.94% | 15.19% | 19.65% |

Un vendedor del p90 genera >4× más quejas que uno del p10. El vendedor importa.

**B — ¿el vendedor causa la tardanza? (TODAS):** la tasa de entrega-tarde varía de 2.17%
(p10) a 14.76% (p90) entre vendedores → **sí, el vendedor causa parte de la tardanza
(Camino 1 confirmado).**

**C — ¿el efecto sobrevive sin entrega? (SOLO PUNTUALES) — el veredicto de P3:**

| Percentil | Todas | Solo puntuales |
|---|---|---|
| p10 | 4.63% | 2.53% |
| p50 | 10.94% | 7.34% |
| p90 | 19.65% | 15.54% |
| **Rango p10→p90** | **15.0 pts** | **13.0 pts** |

La dispersión casi no se encoge al quitar las órdenes tarde (15 → 13 puntos). Si el vendedor
solo importara por despachar tarde, en puntuales todos se verían iguales. No pasa: **el
vendedor arruina la nota por su cuenta (Camino 2 real) → P3 vive como problema propio.**

**D — ¿es accionable?** El peor 10% de vendedores (61 de 614) acumula **16.7%** de las malas
reseñas (1.7× lo esperado si todos fueran iguales). Hay concentración → palanca de curaduría
("vigilar/curar el peor X%"), justo lo que pedía la ficha de P3.

#### 7.1.5 El flete como driver (celda C4)

El flete crudo está confundido con peso, distancia y valor; el indicador útil es el **ratio
flete/valor** (`freight_total / price_total` a nivel orden), que captura la **fricción
percibida**. Tres miradas, por quintiles del ratio:

**A — insatisfacción por tramo (TODAS):**

| Tramo | ratio medio | Insatisfacción |
|---|---|---|
| Q1 muy bajo | 0.08 | 12.36% |
| Q2 bajo | 0.15 | 12.31% |
| Q3 medio | 0.22 | 12.33% |
| Q4 alto | 0.34 | 13.53% |
| Q5 muy alto | 0.62 | 13.51% |

Sin gradiente real: plano (~12.3%) hasta Q3, sube apenas **~1.2 puntos** en los más caros y
se aplana. Comparado con la entrega (12%→78%) o el vendedor (4.6%→19.7%), el flete se mueve
**1 punto**.

**B — ¿sobrevive en puntuales?** El salto Q1→Q5 es +1.15 pts en todas y +1.02 pts en
puntuales → el efecto es **propio** (no tardanza disfrazada) pero **diminuto**.

**C — ¿el flete alto tarda más?** La tasa de entrega-tarde es **plana** por tramo de flete
(7.48%–8.29%). Hallazgo importante e inesperado: **el flete alto NO se asocia a más tardanza**
→ se desmiente el enredo "flete caro = lejano = tarda más". Probablemente la fecha estimada
ya incorpora la distancia.

> **Veredicto del flete:** driver **débil** (~1 punto), propio pero marginal. Se confirma
> fuera del pool como candidato independiente. Su parte útil dentro de P2 es escasa.

#### 7.1.6 Geografía del dolor de entrega (celda C5 — haversine vía geolocation)

El hallazgo C del flete (no predice tardanza) **debilitó** una de las dos razones para usar
`geolocation` (desenredar flete↔distancia↔tardanza). Pero la otra razón —la de mayor valor de
negocio— seguía viva: *¿el dolor de entrega se concentra geográficamente?* C5 se reorientó a
**caracterizar P1**, no a repartir el 66% no-entrega. Se usó la fórmula **haversine** (distancia
sobre la esfera terrestre entre dos lat/lng), colapsando `geolocation` a un centroide por
prefijo de zip y limpiando outliers fuera del bounding box de Brasil.

**A — dolor de entrega por estado del comprador (con volumen ≥200 órdenes):**

| Estado | Órdenes | Insat. | Tarde |
|---|---|---|---|
| AL (Alagoas) | 394 | 21.32% | **23.35%** |
| MA (Maranhão) | 712 | 19.94% | 19.24% |
| PI (Piauí) | 471 | 16.14% | 15.92% |
| CE (Ceará) | 1,273 | 17.12% | 15.24% |
| … | | | |
| **SP (São Paulo)** | 40,266 | 10.69% | **5.83%** |
| PR (Paraná) | 4,900 | 10.88% | 4.92% |
| RO | 242 | 11.98% | 2.89% |

> **P1 es un dolor regional.** Un comprador en Alagoas sufre entrega tarde el 23% de las
> veces; uno en São Paulo, el 5.8% (≈4×). La insatisfacción acompaña (21% vs 10.7%). El
> reencuadre: P1 no es "Olist entrega tarde" en abstracto, sino **"Olist entrega tarde al
> Norte/Nordeste"** — mucho más accionable y vendible.

**B — ¿mismo estado comprador-vendedor vs. distinto?**

| | Órdenes | Insat. | Tarde |
|---|---|---|---|
| Mismo estado | 34,490 | 10.48% | 6.01% |
| Distinto estado | 61,334 | 14.12% | 9.11% |

Cruzar de estado (la mayoría de las órdenes, por la concentración de vendedores en SP) sube
tardanza ~50% e insatisfacción.

**C — distancia real (haversine):** mediana 434 km, p90 1,456 km; 478 órdenes sin cobertura
geo (excluidas).

| Tramo | dist. media | Insat. | Tarde |
|---|---|---|---|
| Q1 cerca | 34 km | 10.43% | 6.43% |
| Q2 | 276 km | 12.22% | 6.73% |
| Q3 | 434 km | 12.88% | 7.49% |
| Q4 | 694 km | 13.51% | 8.45% |
| Q5 lejos | 1,456 km | 15.02% | 10.80% |

**C-bis — ¿la promesa compensa la distancia?** El gradiente de tardanza sube con la distancia
(6.4%→10.8%) pero **suavemente**, no de forma brutal. Esto reconcilia con C4: el flete (proxy
sucio de distancia) no predecía tardanza, pero la distancia **real** sí, de modo leve.
Lectura: **la promesa de Olist compensa la distancia, pero no del todo** —alarga la fecha
estimada para envíos lejanos, mas se queda corta para lo más remoto—. Palanca real: **afinar
la estimación de entrega para envíos remotos**.

#### 7.1.7 Síntesis — el mapa del dolor

```
  TODO EL DOLOR (reseñas ≤2)
   │
   ├── 33.8% ENTREGA TARDE (P1) ── caracterizado por C5:
   │        concentrado en Norte/Nordeste (AL 23% vs SP 5.8%);
   │        crece con la distancia (suave); la promesa compensa parcialmente.
   │
   └── 66.2% NO-ENTREGA ── repartido por C3 y C4:
            ├── VENDEDOR (C3): driver FUERTE y propio (4.6%→19.7%), accionable (peor 10% = 16.7%)
            ├── FLETE    (C4): driver DÉBIL (~1 punto)
            └── resto: producto / expectativa / otros (no medido — sería NLP, diferido)
```

#### 7.1.8 Estado de las banderas tras el Nivel 2

| Bandera (origen Nivel 1) | Estado |
|---|---|
| P2 independiente de la entrega | **RESUELTA** — 66.2% del dolor no es entrega → P2 vive |
| P3 efecto propio del vendedor | **RESUELTA** — sobrevive en puntuales; accionable → P3 vive |
| Flete (P5 reubicado) como driver | **RESUELTA** — driver débil (~1 pt) → confirmado fuera del pool |
| (extra) ¿el vendedor causa la tardanza? | **CONFIRMADO** — Camino 1 existe → solape real P1↔P3 |

**Frontera P1↔P3 a dibujar en el Punto de Decisión.** El solape (Camino 1: el vendedor
despacha tarde) es real y, mal declarado, sería doble conteo. La frontera honesta:
**P1 = "la entrega llega tarde" (sea por quien sea); P3 = "el vendedor como entidad a
gestionar, incluyendo que despacha lento Y que vende/describe mal".** Comparten el despacho
lento; al elegir, hay que decidir explícitamente a cuál se le acredita para no vender dos
problemas que se pisan.

#### 7.1.9 Handoff al Punto de Decisión

El Nivel 2 cerró su trabajo: convirtió tres banderas de "quizás" en veredictos con número y
le puso tamaño a P1. Lo que **no** hace este nivel —por regla del embudo— es elegir el
problema. Los tres finalistas llegan al **Punto de Decisión** así:

- **P1 Entrega** — dolor real y potente pero de alcance acotado (1/3 del total); reencuadrable
  como problema regional (Norte/Nordeste), con palanca en la estimación de entrega.
- **P2 Satisfacción** — el de mayor alcance (2/3 del dolor); su naturaleza es de *driver
  analysis* (entender de qué está hecha la insatisfacción), no de una sola palanca.
- **P3 Vendedores** — efecto propio, concentrado y accionable vía curaduría; comparte frontera
  con P1.

El Punto de Decisión (próximo chat) elige UNO, con su justificación, y de ahí arranca el
Nivel 3 (DVA enfocado y completo del ganador).

---

### 7.2 Punto de Decisión — elección del problema

**Método (anti-sesgo).** Para no llegar "enamorados" del de mayor alcance, se fijaron
los 6 criterios y se acordó que la ponderación la haría el equipo AL FINAL, a la vista
de la evidencia y explicada (no un peso retroajustado). Cada celda de la matriz se
sostiene en datos del Nivel 2 (§7.1) o del dimensionamiento económico Nivel B de este
punto. Abogado del diablo obligatorio.

**Dimensionamiento económico (Nivel B).** Se midió el TAMAÑO en R$ y volumen (no valor
causal, imposible sin recompra/clickstream). GMV = suma de price por orden. Base: 95,832
órdenes con reseña, GMV R$13,109,994.

| Problema | Órdenes | GMV expuesto | % GMV | AOV |
|---|---|---|---|---|
| P1 Entrega (tarde) | 7,661 | R$1,124,342 | 8.6% | R$147 |
| P1 + no-entregadas | — | ~R$1,494,488 | — | — |
| P2 Satisfacción (≤2) | 12,273 | R$1,962,665 | 15.0% | R$160 |
| P3 peor decil vendedores | 6,341 | R$833,769 | 6.4% | R$131 |

Hallazgo: el dolor vive en órdenes más caras (insatisfechas AOV R$160 vs R$137 base,
+17%), lo que amplifica P2. Pero el reparto tarde/puntual del dolor en R$ (32.6/67.4) ≈
al de conteo (33.8/66.2): el dinero no vuelca la historia. Regional (P1): N/NE tiene la
intensidad más alta (13.5% de su GMV atascado vs 8.0% del Sudeste) pero el Sudeste
concentra el 61.2% del GMV-tarde absoluto → el reencuadre regional se vende por
intensidad/accionabilidad, no por volumen de dinero.

**Matriz problema × criterio** (●●● fuerte · ●● medio · ● débil; riesgo en clave robustez):

| Criterio | P1 | P2 | P3 |
|---|---|---|---|
| 1. Alcance | ●● (1/3) | ●●● (2/3) | ● (12.5% R$) |
| 2. Valor económico | ●● R$1.12–1.49M | ●●● R$1.96M | ● R$0.83M |
| 3. Accionabilidad | ●●● | ● (lente, no palanca) | ●●● (curar 63 vend.) |
| 4. Demostrable e2e | ●●● (cliente lo usa) | ●● (análisis interno) | ●● (target a construir) |
| 5. Riesgo (bajo=mejor) | ●●● | ●● | ● |
| 6. Portafolio | ●● | ●●● | ●●● |

Ninguno arrasa: P2 gana tamaño/narrativa, P3 accionabilidad/distinción, P1 ejecución.

**Decisión: P1 · Desempeño de entrega.** En este ejercicio —que exige demostrar un stack
end-to-end y simular una consultora que ENTREGA un producto— el bloque de ejecución
(criterios 3-4-5) pesó fuerte, y P1 lo domina: único con target limpio (completable sin
construir la etiqueta), único cuyo artefacto el cliente final USA, y el que fuerza la
lección de data leakage. Crucialmente, P1 también se sostiene en VALOR (dolor real,
accionable, regionalmente nítido), de modo que la elección no sacrifica honestidad ante
el stakeholder. Se asume conscientemente su alcance acotado (~1/3) frente a P2.

**Por qué no P2 ni P3.** P2 es el mayor dolor y la mejor narrativa, pero su corazón
(driver analysis) es un ESTUDIO, no un modelo desplegable: forzar MLOps/API sobre él sería
artificial. P3 es el más distintivo (target engineering) pero el de mayor riesgo de no
completarse (etiqueta de cero, colas inestables) y el menos canónico en despliegue.

**Abogado del diablo de P1.** EN CONTRA: el más pequeño en alcance y R$; el menos original;
riesgo de data leakage; el dinero absoluto del dolor de entrega está en el Sudeste, no en
N/NE. CÓMO SE ASUME: alcance acotado aceptado a cambio de completar/demostrar; distinción
vía giro regional + capa de producto + honestidad del leakage; narrativa elegida =
intensidad/accionabilidad regional, no "donde está la plata".

**Frontera P1↔P3 resuelta.** El despacho lento del vendedor es input de la tardanza → vive
dentro de P1. P3 NO se desarrolla como problema; su señal entra como FEATURE de P1 (tasa
histórica de despacho tardío del vendedor). Un solo problema, un solo target; el seller-
score pasa de "target a construir" (riesgo) a feature derivada (bajo riesgo).

**Handoff al Nivel 3.** Arranca el DVA enfocado de P1: construir entrega_tarde, EDA
(incl. geoespacial), feature engineering con features de vendedor, y la disciplina de
evitar leakage. De ahí el stack end-to-end.

### 7.3 Veredicto de viabilidad final + decisiones que cierran el Project Charter

> **BORRADOR en construcción (append-only).** Este es el entregable narrativo del Nivel 3.
> Integra la base del DVA (§7.3.0), la señal descriptiva que justifica las features
> (§7.3.1), la auditoría de la feature de vendedor (§7.3.2) y el veredicto final de
> viabilidad (§7.3.3).

#### 7.3.0 Base del DVA — universo, targets y blindaje anti-leakage (celdas D0-pre, D0)

**Notebook.** El Nivel 3 se trabaja en `nivel3_dva_p1.ipynb`, que **reconstruye** la base desde
las 9 tablas en vez de heredarla del Nivel 2. Esa reconstrucción es, en sí, la prueba de
reproducibilidad del target que el DVA debe afirmar.

**Universo de P1 — fijado en 96,470 órdenes.** Se parte de las 99,441 órdenes; se filtran las
no-entregadas (2,963) y 8 entregadas sin fecha real → 96,470 órdenes entregadas con fecha. Se
**abandona** el filtro "con reseña" que usó el Nivel 2 (95,824): la reseña no interviene en el
target (que son fechas) y exigirla **sesga la muestra**, porque las 646 órdenes sin reseña son
**3× más tardías** (25.5% vs 7.99%) — excluirlas borraría justo parte de la clase que se quiere
predecir. Decisión: universo amplio, sin condicionar a reseña. La tasa de tarde resultante es
**8.11%** (7,826 órdenes), consistente con el ~8% heredado del Nivel 2.

**Canceladas / no-entregadas — excluidas del modelado, reportadas como limitación (decisión B).**
Son 2,963 órdenes (2.98%) / R$370K de GMV. No tienen fecha de entrega, de modo que el target
`entrega_tarde` no se les puede calcular; incluirlas obligaría a un target distinto ("nunca
llegó" = predecir cancelación, otro problema). Dentro de ellas se distingue **fallo real**
(canceled 625 + unavailable 609 = 1,234) de **censura por corte de datos** (shipped 1,107 +
invoiced 314 + processing 301 = 1,722): la ventana del dataset cierra compras el 2018-08-29
pero registra entregas hasta el 2018-10-17, así que las `shipped` son en su mayoría compras
tardías aún en tránsito, no fracasos. Quedan como **alcance no cubierto declarado**, no como
clase del modelo.

**Tres targets sobre las mismas fechas — framing abierto.** En vez de asumir clasificación, se
construyen tres etiquetas y se decide el framing con evidencia (en §7.3.3): **A** `entrega_tarde`
(clasificación: ¿rompe la promesa?), **B** `dias_vs_promesa` (regresión: días de desvío vs la
promesa), **C** `dias_entrega_real` (regresión: duración real compra→entrega). Motivo del giro:
la palanca de negocio identificada en §7.1.6 —*afinar la estimación de entrega*— es **continua**
por naturaleza, no binaria; además el binario es escaso (8.11%) y el target B está sesgado por
el margen que mete Olist (ver hallazgo siguiente). La evidencia inclina hacia **C** como el más
"físico" y alineado con la palanca, pero no se congela aquí.

**Hallazgo — la promesa de Olist está fuertemente inflada.** Mediana de entrega real **10 días**
vs mediana prometida **23 días**: ~13 días de colchón. Esto explica por qué solo el 8.11% llega
tarde pese a una cola larga de entrega real (hasta 209 días): el colchón absorbe casi toda la
variabilidad. Implicación: la promesa no describe la realidad, la sobreprotege — hay margen para
afinarla (refuerza el framing C).

**Inventario anti-leakage (D0).** Principio único: una columna es feature válida solo si su valor
se conoce en el **momento de la compra (M0)**; lo que aparece después es *data leakage*. Resultado
sobre las 9 tablas: **~52 columnas físicas / ~47 de información única** (la diferencia son claves
de unión repetidas: `order_id` ×5, `product_id` ×3, etc.). De ahí, **~30 features candidatas
válidas** sin leakage. El leakage es **concentrado y evidente**: toda la tabla `reviews` (5
columnas, M4 post-entrega) + `order_delivered_carrier_date` (M2) + `order_delivered_customer_date`
(M3, que además es parte del target). Casos resueltos: `order_approved_at` ≈ M0 (mediana 20 min
tras la compra) → válida pero de bajo valor; `shipping_limit_date` → válida en M0 y, además,
ingrediente de la feature histórica del vendedor. Por **alta cardinalidad**, `seller_id` (3,095)
y `customer_city` (4,119) no entran crudos: el vendedor se representa por su tasa histórica
(point-in-time, D2) y la ciudad por `state` (27) o por coordenadas. Completitud: peso y dimensiones
~0% nulos; categoría 1.9% nulos.

**Lectura parcial de viabilidad (no es el veredicto).** El riesgo técnico #1 del DVA —que lo
único predictivo fuera leakage— queda **descartado**: las palancas fuertes heredadas del Nivel 2
(distancia, región, peso, vendedor) son todas de M0. La viabilidad no muere por falta de features
honestas. Falta confirmar que esas features **discriminan** de verdad tarde vs puntual (D1) y que
la del vendedor **se calcula sin leakage temporal** (D2) antes de emitir el veredicto.

**Agrupación de features candidatas (organiza el EDA).** G1 geografía+distancia · G2 físicas del
envío (peso, volumen, flete) · G3 categoría · G4 valor/pago · G5 temporales · G6 vendedor
(point-in-time). El EDA descriptivo se divide en consecuencia: **D1a** (G1+G5), **D1b** (G2+G3),
**D1c** (G4), y **D2** para G6.

#### 7.3.1 Señal descriptiva del EDA enfocado (celdas D1a/D1b/D1c)

El EDA enfocado de P1 cambia de rol tras la reconciliación con el repo. Ya no funciona
como una exploración previa al modelado, porque el equipo ya cerró la Etapa 4 con un
clasificador entrenado. Su función ahora es más precisa: documentar si la señal que usa
el modelo es legítima, si las features seleccionadas tienen sentido de negocio y si la
Fase 1 se sostiene como una solución defendible.

La primera prueba es temporal. Las 16 features del modelo pertenecen al momento M0, es
decir, al momento de compra o aprobación de la orden. No dependen de la fecha real de
entrega, de reseñas, ni de columnas calculadas después de que el cliente recibe el
producto. Esto permite que el modelo sea conceptualmente desplegable: Olist podría
calcular esas variables antes de saber si la orden terminó llegando tarde.

La segunda prueba es de pertinencia. Las features seleccionadas no son solo "permitidas";
también describen los mecanismos reales del problema. La geografía del comprador y del
vendedor captura diferencias regionales; `mismo_estado` y `dist_haversine_km` aproximan
dificultad logística; `dias_prometidos` representa el colchón de la promesa;
`tasa_vendedor` resume desempeño histórico del seller; peso, volumen, flete, precio,
número de ítems y categoría describen la complejidad física y comercial del pedido; mes
y día de compra capturan estacionalidad.

En conjunto, las features son coherentes con Olist como marketplace. La entrega no
depende solo de "kilómetros": depende de la red de vendedores, la región del comprador,
el tipo de producto, la holgura de la promesa y el comportamiento histórico del seller.
Por eso las 16 features pueden defenderse como un subconjunto correcto y suficiente para
Fase 1. No son necesariamente el conjunto final del proyecto: si la Fase 2 avanza hacia
regresión sobre `dias_entrega_real`, la pregunta de features deberá reabrirse.

#### 7.3.2 Feature de vendedor sin leakage temporal (celda D2)

La feature más delicada del modelo es `tasa_vendedor`, porque resume desempeño histórico
del seller. Si se calculara usando la propia orden o pedidos futuros, introduciría
*data leakage*: el modelo estaría usando información que no existiría en producción.

El repo la implementa como una tasa *point-in-time*: para cada orden, solo usa órdenes
anteriores del mismo vendedor. Además, exige un mínimo de 5 órdenes previas; cuando no
hay suficiente historia, usa la tasa global del train y activa `sin_historial_vendedor`.
Esto evita que el modelo descarte vendedores nuevos y, al mismo tiempo, impide que la
orden se prediga con información de sí misma.

La auditoría de la Etapa 4 refuerza que la señal no parece contaminada. Las métricas
están en un rango realista, lejos de valores cercanos a 1.0 que sugerirían fuga. Además,
`tasa_vendedor` pesa cerca del 6% de la importancia total: aporta señal, pero no domina
artificialmente el modelo.

Desde negocio, esta feature es especialmente valiosa porque traduce el comportamiento
del seller en una señal accionable para Olist. La plataforma no controla toda la logística
como un operador único, pero sí puede monitorear vendedores, ajustar promesas según
historial y diseñar políticas de curaduría o prevención.

#### 7.3.3 Veredicto final de viabilidad de P1

**Veredicto: P1 es viable con reservas.**

P1 es viable porque los datos permiten construir un target limpio (`entrega_tarde`),
seleccionar features disponibles en el momento de la compra y entrenar un modelo que
supera el azar sin depender de información futura. La Fase 1 ya está implementada en el
repo como clasificación binaria de entrega tardía: predice si una orden romperá la
promesa actual de Olist.

La señal es honesta en dos sentidos. Primero, no hay *data leakage*: las variables
post-entrega, las reseñas y la fecha real no entran como features. Segundo, las variables
seleccionadas representan factores reales del negocio: región, vendedor, promesa,
distancia, temporalidad y características del pedido. Por eso la Fase 1 no es solo un
ejercicio técnico; es un primer sistema defendible de priorización de riesgo logístico.

Las métricas son modestas, pero útiles. En test, XGBoost alcanza ROC-AUC 0.703 y PR-AUC
0.124 frente a una tasa base de 0.066. En un problema desbalanceado, donde las entregas
tardías son minoría, PR-AUC es más informativa que la accuracy. El modelo no predice
perfectamente, pero sí ordena el riesgo mejor que el azar. En el punto de alta cobertura,
captura cerca del 63% de las entregas tardías alertando alrededor del 35% de las órdenes.
Esto sirve como herramienta de riesgo, no como automatización final sin supervisión.

La reserva principal es estratégica. `entrega_tarde` mide incumplimiento contra la promesa
actual, pero esa promesa tiene un colchón amplio: la mediana real de entrega ronda 10 días
y la prometida ronda 23. Entonces la clasificación ayuda a proteger una promesa
conservadora, pero no necesariamente optimiza la fecha que ve el cliente.

Por eso el framing final queda en dos fases. La **Fase 1**, ya entregada, es clasificación
de `entrega_tarde`: útil para anticipar riesgo de incumplimiento. La **Fase 2** recomendada
es una regresión sobre `dias_entrega_real`: estimar cuántos días tardará realmente la
entrega. Esa segunda fase porta más valor de negocio porque permitiría construir una
promesa más honesta, competitiva y ajustada por región, vendedor y características de la
orden.

Las limitaciones quedan declaradas. El dataset no mide conversión, abandono de carrito,
recompra, compensaciones ni costo real de incumplir o sobre-prometer. Las órdenes
canceladas/no entregadas quedan fuera del target principal. Además, existe un cambio de
régimen temporal entre train, val y test, por lo que la calibración y los umbrales deben
revisarse antes de producción.

En síntesis: P1 es viable con reservas. Viable porque tiene target limpio, features
honestas, señal predictiva y valor operativo. Con reservas porque las métricas son
moderadas, la promesa actual está inflada, el dataset no mide todos los costos de negocio
y la solución completa exige una Fase 2 de duración real más una política de nivel de
servicio.

---

## 8. Decisiones derivadas de este chat (Nivel 0)

*Versión narrativa con el porqué. La Bitácora §4 tiene el puntero de una línea; el futuro Decision Log (GitHub) tendrá la versión atómica indexada con contexto/opciones/razón. No duplicar: extraer de aquí cuando se cree el Log.*

1. **Universo consolidado en 5 candidatos (P1–P5).** *Razón:* de 12 dolores, varios eran la misma cadena causal; agrupar por identidad del dolor evita juzgar doble y deja un set comparable para el filtro.
2. **Descarte de "calidad del anuncio".** *Razón:* su resultado (conversión) no es medible sin datos de navegación, ausentes.
3. **item-to-item fuera del pool, dentro de la narrativa.** *Razón:* ya investigado (viable pero limitado); borrarlo perdería el gancho de consultora.
4. **Fichas en dos niveles de detalle.** *Razón:* para *filtrar* basta una mini-ficha de 4 datos (dolor · problema concreto · target candidato · palanca de acción); la ficha completa de 6 elementos se reserva a los sobrevivientes, para no gastar esfuerzo en candidatos que se cortarán.
5. **Tensión P2-vs-P1 registrada como pregunta empírica.** *Razón:* decidir si P2 es problema propio o síntoma de P1 requiere medir cuánta insatisfacción no viene de la entrega → es trabajo de Nivel 2, no del filtro.

---

*Fin del contenido redactado. Queda pendiente el backfill de §3 (DVA item-to-item,
de chat previo); §6 y §7 ya están redactadas como captura de trabajo del embudo y
cierre de viabilidad de P1.*
