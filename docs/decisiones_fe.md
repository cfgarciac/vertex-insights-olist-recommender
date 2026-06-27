# Feature Engineering — Decisiones (P1 · desempeño de entrega)

> Documento técnico de la Etapa 3. Registra cómo se construyó la tabla
> analítica y el pipeline de features para modelar el **desempeño de entrega**,
> con énfasis en la disciplina anti-leakage (D-21, R-12). Es el insumo directo
> de la Etapa 4 (modelado).
>
> **Actualización (2026-06-27, re-ejecución de la Etapa 3, D-30).** El FE se
> amplió para habilitar **varias familias de modelos** (clasificación binaria,
> clasificación multiclase y regresión) sin rehacer features ni split: se
> promueven varios *targets* [POST] sobre el **mismo** conjunto de features [t0].
> El CSV de salida pasó a llamarse `orders_features.csv` (antes
> `orders_p1_features.csv`) y de 21 a 23 columnas.

**Fecha:** 2026-06-20 (ampliado 2026-06-27)
**Responsable:** Data Scientist (Aguilar Lomas, Oscar Amaury)
**Artefactos asociados:**
- Script reproducible: `src/features/build_dataset.py`
- Tabla analítica: `vertex_files/orders_features.csv` (96,470 × 23)
- Pipeline serializado: `artifacts/pipeline_p1.joblib`
- EDA de cambios: `notebooks/03_EDA_VERTEX.ipynb`

---

## Resumen

Se transformó el CSV consolidado de Olist a nivel ítem
(`orders_consolidated.csv`, 112,650 filas) en una **tabla analítica a nivel
orden** sobre el universo `delivered` (96,470 órdenes), con **varios targets**
(clasificación y regresión) y un conjunto de features **estrictamente [t0]**
(conocidas en el momento de la compra). Las transformaciones que aprenden
parámetros de los datos (escalado, encoding, imputación estadística) se
encapsulan en un `Pipeline`/`ColumnTransformer` ajustado **solo sobre el split
de entrenamiento** y serializado con `joblib`. El **mismo** `X` (features [t0])
alimenta a todas las familias de modelos; solo cambia la columna `y`.

---

## Tabla analítica: universo, granularidad, conteos

- **Fuente.** Se partió del CSV ya consolidado (`orders_consolidated.csv`) en
  lugar de las nueve tablas crudas, por indicación operativa de la etapa
  (decisión D-22). El CSV ya integra ítems, pagos, reseñas, producto y
  geolocalización.
- **Universo = `delivered`** (D-20). Se descartan los demás estados (shipped,
  canceled, invoiced, processing, unavailable, approved ≈ 2,453 filas) porque no
  son etiquetables; se tratan aparte como "ausencia informativa".
- **Etiquetabilidad.** Se eliminan 8 órdenes `delivered` sin fecha de entrega
  real (no se pueden etiquetar).
- **Granularidad = orden** (D-23). El CSV viene a nivel ítem; se colapsa a una
  fila por `order_id`:
  - **Vendedor/producto principal = primer ítem** (`order_item_id == 1`): de él
    se toman `seller_id`, `seller_state`, geo del vendedor, `categoria_principal`.
  - **Agregados sobre todos los ítems** de la orden: `precio_total`,
    `flete_total`, `peso_total_g`, `volumen_total_cm3`, `n_items`.
- **Conteo final:** 96,470 órdenes (cuadra con el EDA, ≈96.5k).

---

## Targets disponibles (clasificación y regresión)

La tabla expone **cuatro targets** [POST] sobre el mismo `X` (D-30). Todos son
*labels* (se calculan con fechas posteriores a la compra) y **ninguno es
feature**. La Etapa 4 elige `y` según la familia de modelo:

| Target | Tipo | Definición | Uso |
|---|---|---|---|
| `entrega_tarde` | clasificación binaria | `entregada > estimada` (1=tarde) | Clasificadores (target principal del MVP) |
| `clase_entrega` | clasificación multiclase | `tarde` (>0) · `a_tiempo` (−3..0) · `muy_temprano` (<−3 d) | Clasificación multiclase / análisis de severidad |
| `dias_vs_promesa` | regresión | `entregada − estimada` en días (>0 = tarde) | Regresión del adelanto/retraso vs promesa |
| `dias_entrega_real` | regresión | `entregada − compra` en días | Regresión del tiempo total de entrega |

- **Tasa base `entrega_tarde` = 8.11%** (desbalance sano; cuadra con el EDA).
- **Distribución de `clase_entrega`:** `muy_temprano` 86.97% · `tarde` 8.11% ·
  `a_tiempo` 4.92%. El fuerte sesgo a `muy_temprano` refleja que **Olist promete
  con mucho colchón** (mediana de `dias_vs_promesa` ≈ **−11.9 días**, es decir,
  se entrega casi 12 días antes de lo prometido en la mediana). El umbral de 3
  días (`UMBRAL_MUY_TEMPRANO_DIAS`) es un **parámetro de negocio ajustable**: si
  la Etapa 4 necesita una clase media más poblada, puede subirse.
- **Anti-leakage:** la `tasa_vendedor` (feature [t0]) sigue calculándose sobre
  `entrega_tarde` con ventana point-in-time; los targets de regresión **no**
  realimentan ninguna feature.

---

## Catálogo de features [t0]

| Feature | Fuente | Tipo | Justificación | Imputación |
|---|---|---|---|---|
| `dias_prometidos` | estimada − compra | num | Colchón prometido; el dolor vive en su cola corta | mediana (pipeline) |
| `dist_haversine_km` | lat/lng cliente↔vendedor | num | La distancia sube la tardanza (suave) | mediana en train (pipeline) |
| `ratio_flete` | flete_total / precio_total | num | Driver débil pero legítimo [t0] | mediana (negocio + pipeline) |
| `precio_total` | suma de ítems | num | Tamaño/valor de la orden | mediana (pipeline) |
| `flete_total` | suma de ítems | num | Costo logístico | mediana (pipeline) |
| `n_items` | conteo de ítems | num | Complejidad de la orden | — |
| `peso_total_g` | suma de ítems | num | Peso ↔ logística | mediana de categoría |
| `volumen_total_cm3` | L×H×W sumado | num | Volumen ↔ logística | mediana de categoría |
| `tasa_vendedor` | histórico del vendedor | num | El vendedor mueve la tardanza | global train + flag |
| `mes_compra` | fecha de compra | num | Estacionalidad (ojo régimen 2018) | — |
| `dia_semana_compra` | fecha de compra | num | Estacionalidad semanal | — |
| `customer_state` | cliente | cat | Gradiente regional (Norte/Nordeste) | más frecuente (pipeline) |
| `seller_state` | vendedor principal | cat | Origen logístico | más frecuente (pipeline) |
| `categoria_principal` | producto principal | cat | Tipo de producto | más frecuente (pipeline) |
| `mismo_estado` | cliente == vendedor | cat(0/1) | Proxy de cercanía logística | — |
| `sin_historial_vendedor` | flag | cat(0/1) | Marca el respaldo de `tasa_vendedor` | — |

**Excluidas explícitamente como features ([POST], solo etiquetan o son fuga):**
fechas de entrega real y de carrier, `delivery_days`, `delivery_delay_days`,
`is_late_delivery`, los cuatro *targets* (`entrega_tarde`, `clase_entrega`,
`dias_vs_promesa`, `dias_entrega_real`), y **todo el bloque de reseñas**
(`avg_review_score`, `is_dissatisfied`, comentarios, etc.), que ocurren después
de la entrega.

---

## Tasa del vendedor: ventana elegida y prueba anti-fuga

- **Ventana elegida:** *expanding* y **point-in-time** — para cada orden, la
  tasa del vendedor se calcula con **solo sus órdenes anteriores** (por fecha de
  compra), excluyendo la actual. (Decisión D-24.)
- **Mínimo de historial:** 5 órdenes previas. Por debajo de ese umbral se usa el
  **respaldo a la tasa global del TRAIN** (9.03%) y se marca
  `sin_historial_vendedor = 1`. Afecta al **11.57%** de las órdenes.
- **Implementación sin fuga:** se ordena por fecha de compra y se usa la suma y
  el conteo acumulados del vendedor **desplazados** (`cumsum − valor_actual`,
  `cumcount`), de modo que la orden nunca se incluye a sí misma ni a futuras.
- **Prueba anti-fuga (en el script, `assert_no_leakage_seller_rate`):** para una
  muestra de órdenes con historial se recomputa la tasa desde cero usando solo
  órdenes estrictamente anteriores y se compara con la columna producida.
  Resultado: **OK** (sin discrepancias).

---

## Estrategia de imputación (geo, vendedor, dimensiones)

- **Geolocalización faltante** (lat/lng ausente → `dist_haversine_km` nula, 476
  órdenes ≈ 0.49%): la imputación vive **dentro del pipeline** (mediana ajustada
  en train), para no filtrar información del futuro al imputar. El `NaN` se
  **conserva a propósito en el CSV** (no se rellena en el ETL) para que la
  imputación estadística viva en el objeto serializado y se aplique idéntica en
  val/test/producción.
  - **Por qué la distancia tiene "más" nulos que cada extremo:** la distancia es
    nula si falta la coordenada del **cliente _o_ del vendedor**, por lo que su
    hueco es la **unión** de ambos: geo cliente 0.27% (302) ∪ geo vendedor 0.22%
    (253) ≈ **0.49%** (476). No es un deterioro de la geo del vendedor (que se
    mantiene en ~0.22%); es un artefacto esperado de derivar una feature a partir
    de dos fuentes con huecos. Comparar el "antes" a nivel orden confirma que el
    porcentaje **no aumenta** (0.49% antes = 0.49% después).
- **Vendedor sin historial:** respaldo a la **tasa global del train** + flag
  `sin_historial_vendedor` (no se descarta la orden).
- **Dimensiones de producto faltantes** (peso/volumen): **mediana de la
  categoría** del producto principal (atributo estable del producto, no del
  target); respaldo a la mediana global si la categoría no tiene dato.
- **`ratio_flete`** con precio 0: mediana.

(Decisión de imputación: D-26. Riesgo asociado: R-07.)

---

## Encodings

- **Numéricas:** `SimpleImputer(median)` + `StandardScaler`.
- **Categóricas:** `SimpleImputer(most_frequent)` +
  `OneHotEncoder(handle_unknown="ignore", min_frequency=0.01)`. El
  `min_frequency` agrupa categorías raras (estados/categorías de baja frecuencia)
  para controlar la dimensionalidad y el ruido. `handle_unknown="ignore"` evita
  que una categoría no vista en train rompa la inferencia.
- Todo se ensambla en un `ColumnTransformer` dentro de un `Pipeline`, **ajustado
  solo en train** y serializado en `artifacts/pipeline_p1.joblib` (D-26).

---

## Split temporal: punto de corte y tratamiento del régimen 2018

- **Corte por fecha de compra** (no aleatorio): train = pasado, val/test =
  futuro. Proporción **70/15/15** (train 67,529 · val 14,470 · test 14,471).
  (Decisión D-25; se apoya en D-09.)
- **Régimen 2018 (R-14):** el notebook `03_EDA_VERTEX.ipynb` inspecciona la tasa
  y el volumen mensuales. Se **deja el periodo completo** en esta etapa (sin
  recortar) y se documenta la cola final como punto de vigilancia para la Etapa 4
  (si el modelo muestra degradación en el tramo final, se reevaluará recortar o
  modelar aparte). No se deja que un evento puntual redefina el comportamiento
  normal.

---

## Multicolinealidad conocida y cómo se maneja

- Esperada: `dist_haversine_km` ↔ `mismo_estado`; `peso_total_g` ↔
  `volumen_total_cm3`. No es fatal para modelos de árboles; importa para modelos
  lineales. Se documenta y la decisión de poda se difiere a la Etapa 4 con el
  modelo elegido a la vista.

---

## Pendientes / supuestos para la Etapa 4

- El pipeline serializado solo contiene el **preprocesador**; la Etapa 4 añade el
  estimador al final del `Pipeline` (el mismo `prep` sirve para clasificadores y
  regresores; en regresión, omitir el `StandardScaler` no es obligatorio).
- **Entrenar varias familias y elegir la mejor** (D-30): para clasificación,
  comparar al menos baseline + lineal + árbol/boosting sobre `entrega_tarde`;
  opcionalmente `clase_entrega` (multiclase) y regresión sobre `dias_vs_promesa`
  o `dias_entrega_real`. Selección por la métrica de D-19 en el split `val`
  temporal (nunca en `test`).
- En el notebook de la Etapa 4 graficar, como mínimo: **mejora del recall** entre
  modelos, **matriz de confusión por modelo**, y las **gráficas del modelo
  elegido** (curvas PR/ROC, calibración, importancias). Ver el handoff en
  `docs/etapas/cierre-etapa-3.md`.
- `tasa_vendedor` es la feature más potente y más sensible a fuga: si el modelo
  da métricas sospechosamente altas, revisar primero su cálculo (R-12).
- `clase_entrega` está muy desbalanceado (87% `muy_temprano`): usar métricas y
  pesos adecuados (macro-F1, `class_weight`) si se modela multiclase.
- Vigilar el tramo final de 2018 (R-14) al medir desempeño en el split de test.
