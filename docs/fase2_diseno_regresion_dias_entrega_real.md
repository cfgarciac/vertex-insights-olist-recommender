# Diseno Fase 2 - Regresion de dias_entrega_real

> **Estado:** Borrador de diseno, sin implementacion  
> **Proyecto:** Vertex Insights - Olist Marketplace  
> **Problema:** P1 - Desempeno de entrega  
> **Fase relacionada:** Fase 2 recomendada en `docs/project_charter_p1.md`  
> **Ultima actualizacion:** 2026-06-29

---

## 1. Resumen ejecutivo

Fase 1 ya responde una pregunta binaria:

> **Llegara tarde contra la promesa actual?**

Esa pregunta es util para alertar riesgo, pero tiene una limitacion: depende de la
promesa actual de Olist. Si la promesa actual tiene mucho colchon, el modelo protege
esa promesa, pero no necesariamente ayuda a mejorarla.

Fase 2 propone una pregunta mas directa:

> **Cuantos dias tardara realmente la entrega?**

La respuesta seria una prediccion numerica llamada `dias_entrega_real`. Con esa
prediccion, Olist podria construir una fecha prometida mas inteligente, usando una
politica de nivel de servicio.

En simple:

```text
Modelo de Fase 2 predice dias reales
        |
        v
Politica de negocio agrega margen o percentil
        |
        v
Olist muestra una fecha prometida al cliente
```

---

## 2. Separacion clave: modelo vs politica

Esta fase debe separar dos decisiones:

| Capa | Pregunta | Quien decide |
|---|---|---|
| Modelo | Cuantos dias tardara la entrega? | Equipo de datos |
| Politica de promesa | Que fecha mostramos al cliente? | Negocio / Product Owner |

El modelo no deberia decidir solo que tan agresiva o conservadora sera la promesa.
El modelo entrega una estimacion. La politica define el nivel de riesgo aceptable.

Ejemplo:

- Si el modelo estima 8 dias, una politica agresiva podria prometer 8 o 9 dias.
- Una politica conservadora podria prometer 11 o 12 dias.
- La diferencia depende de cuanto riesgo de incumplimiento acepta Olist.

---

## 3. Regla de aislamiento frente a Fase 1

Fase 2 debe desarrollarse como una extension controlada del proyecto, no como una
reescritura de Fase 1.

Regla explicita:

> Durante el desarrollo de Fase 2 no se debe modificar el codigo, la arquitectura,
> los artefactos ni el comportamiento validado de Fase 1. Fase 2 puede reutilizar
> componentes de Fase 1, pero cualquier cambio nuevo debe vivir en archivos,
> scripts, experimentos o modulos separados hasta que el equipo apruebe una
> integracion formal.

Esto protege el trabajo ya entregado: el clasificador `entrega_tarde`, su pipeline,
el split temporal, la disciplina anti-leakage, los tests y los artefactos existentes.

Reutilizar no significa mezclar sin control. La reutilizacion recomendada es:

| Componente de Fase 1 | Puede reutilizarse en Fase 2? | Condicion |
|---|---|---|
| Logica de carga y agregacion order-level | Si | Sin romper la salida actual de Fase 1. |
| Features M0 ya validadas | Si | Como copia, importacion estable o experimento separado. |
| Split temporal 70/15/15 | Si | Mantenerlo como criterio de evaluacion comparable. |
| Lista anti-leakage | Si | Ampliarla para Fase 2 sin relajar reglas existentes. |
| Pipeline/modelo `entrega_tarde` | No modificar | Queda como entregable cerrado de Fase 1. |
| Artefactos `modelo_p1.joblib` y metricas Fase 1 | No modificar | Solo lectura o comparacion documental. |

Si Fase 2 demuestra valor y el equipo decide integrarla al producto, esa integracion
debe tratarse como una decision nueva, con plan, pruebas y documentacion propia.

---

## 4. Target de Fase 2

### 4.1 Target elegido

El target propuesto es:

```text
dias_entrega_real = order_delivered_customer_date - order_purchase_timestamp
```

Es decir, cuantos dias pasaron entre la compra y la entrega al cliente.

### 4.2 Por que este target

| Razon | Explicacion |
|---|---|
| Es fisico | Mide la duracion real de la entrega, no una politica de promesa. |
| Es interpretable | Si el modelo se equivoca, el error se entiende en dias. |
| Sirve para prometer | Desde dias estimados se puede construir una fecha visible para el cliente. |
| Contiene mas informacion que `entrega_tarde` | De una duracion se puede derivar tarde/no tarde; de un si/no no se recupera la duracion. |

### 4.3 Targets descartados

| Target | Decision | Razon |
|---|---|---|
| `entrega_tarde` | Se conserva como Fase 1 | Sirve para riesgo contra promesa actual, pero no para mejorar directamente la promesa. |
| `dias_vs_promesa` | Descartado | Mezcla duracion real con la politica de promesa actual; puede arrastrar sesgo del colchon. |
| Fecha exacta de entrega | No inicial | Es mas complejo; primero se predicen dias y luego se convierte a fecha. |

---

## 5. Unidad de analisis y universo

### 5.1 Unidad de analisis

La unidad de analisis debe ser la **orden**, no el item.

Olist puede tener una orden con varios productos. Si se trabaja a nivel item, una
orden con tres productos podria aparecer tres veces y sesgar los resultados. Por eso
Fase 2 debe mantener la misma disciplina de P1: una fila por orden.

### 5.2 Universo principal

El universo principal son:

```text
ordenes delivered con fecha de compra y fecha real de entrega
```

El DVA temporal trabajo con 96,470 ordenes entregadas etiquetables.

### 5.3 Ordenes canceladas o no entregadas

Las ordenes canceladas o no entregadas son un dolor real, pero no tienen
`dias_entrega_real` completo. Por eso no deben entrar al target principal de Fase 2.

Tratamiento recomendado:

- Excluirlas del entrenamiento de regresion.
- Reportarlas aparte como limitacion y dolor complementario.
- No mezclarlas artificialmente con entregas tardias, porque no tienen duracion real.

---

## 6. Momento de prediccion

La prediccion debe hacerse en **M0**, el momento de compra o aprobacion de la orden.

En M0 se conoce:

- Cliente y estado del cliente.
- Vendedor y estado del vendedor.
- Producto/categoria.
- Precio, flete y cantidad de items.
- Fecha de compra.
- Promesa actual si Olist ya la genera.
- Historial agregado disponible antes de la compra.

En M0 no se conoce:

- Fecha real de entrega.
- Fecha real de despacho.
- Resena del cliente.
- Si finalmente llego tarde.
- Comentarios o satisfaccion post-compra.

Esta regla evita **leakage**, que significa fuga de datos: usar informacion del futuro
como si estuviera disponible al momento de predecir.

---

## 7. Features candidatas

**Feature** significa variable de entrada del modelo: una pista que ayuda a predecir.

### 7.1 Bloque A - Features base reutilizadas de Fase 1

| Feature | Uso esperado |
|---|---|
| `customer_state` | Captura dificultad por destino. |
| `seller_state` | Captura origen logistico. |
| `mismo_estado` | Indica si vendedor y cliente estan en el mismo estado. |
| `dist_haversine_km` | Aproxima distancia geografica. |
| `precio_total` | Contexto economico de la orden. |
| `flete_total` | Puede reflejar distancia, peso o complejidad. |
| `ratio_flete` | Mide peso relativo del flete sobre el precio. |
| `n_items` | Ordenes mas complejas pueden tardar distinto. |
| `peso_total_g` | Paquetes mas pesados pueden afectar logistica. |
| `volumen_total_cm3` | Paquetes voluminosos pueden afectar logistica. |
| `categoria_principal` | Algunas categorias pueden ser mas complejas de entregar. |
| `mes_compra` | Captura estacionalidad general. |
| `dia_semana_compra` | Captura patrones de compra/despacho por dia. |

### 7.2 Bloque B - Features temporales rolling recomendadas

**Rolling** significa ventana movil de pasado. En este caso, para una orden nueva se
mira el comportamiento de los 30 dias anteriores, sin incluir la orden actual.

| Feature candidata | Decision preliminar | Razon |
|---|---|---|
| `ruta_estado_30d_days_mean` | Prioritaria | Fuerte senal para duracion real; cobertura 95.4%. |
| `customer_state_30d_days_mean` | Prioritaria | Muy estable; cobertura 99.7%. |
| `categoria_principal_30d_days_mean` | Prioritaria secundaria | Aporta contexto de producto; cobertura alta. |
| `seller_id_30d_days_mean` | Prioritaria con respaldo | Tiene senal, pero muchos vendedores tienen poco historial. |
| `ruta_estado_30d_late_rate` | Complementaria | Resume riesgo reciente de tardanza por ruta. |
| `customer_state_30d_late_rate` | Complementaria | Resume riesgo reciente por destino. |

### 7.3 Bloque C - Feature delicada: `dias_prometidos`

`dias_prometidos` puede tener senal porque Olist ya uso algun criterio para definir la
promesa. Pero tambien puede hacer que el modelo copie la politica actual.

Recomendacion:

| Uso de `dias_prometidos` | Decision |
|---|---|
| Modelo principal para mejorar promesa | No usar inicialmente. |
| Benchmark de comparacion | Si usar. |
| Analisis de cuanto aprende el modelo vs politica actual | Si usar como experimento controlado. |

**Benchmark** significa punto de comparacion. Sirve para responder: "mi modelo nuevo
mejora o solo repite lo que ya hacia Olist?"

---

## 8. ETL y feature engineering de Fase 2

Fase 2 necesita un diseno propio de ETL y feature engineering. Esto no significa
reescribir Fase 1. Significa construir una extension controlada que produzca una tabla
experimental para regresion, manteniendo intacto el clasificador `entrega_tarde`.

**ETL** significa extraer, transformar y cargar datos. En simple: tomar los datos crudos,
limpiarlos, unirlos y dejarlos listos para modelar.

**Feature engineering** significa crear variables utiles para el modelo a partir de los
datos disponibles. Por ejemplo: convertir fechas en dias, agrupar rutas, calcular
historial reciente o resumir comportamiento de sellers.

### 8.1 Salida esperada del ETL

La salida de Fase 2 debe ser una tabla a nivel orden, separada de la tabla validada de
Fase 1.

| Elemento | Pauta |
|---|---|
| Unidad | Una fila por orden. |
| Universo | Ordenes `delivered` con fecha de compra y fecha real de entrega. |
| Target | `dias_entrega_real`. |
| Features | Solo variables conocidas en M0 o historicos calculados con pasado. |
| Split | Temporal 70/15/15 como punto de partida. |
| Salida recomendada | Tabla experimental Fase 2, sin sobrescribir salidas de Fase 1. |

### 8.2 Regla de aislamiento del ETL

El ETL de Fase 2 puede reutilizar logica de Fase 1, pero no debe modificar la salida ni
el comportamiento del pipeline existente.

Pauta recomendada:

```text
src/features/build_dataset.py          -> queda como Fase 1
nuevo script o experimento Fase 2      -> construye dataset de regresion
```

Si se decide integrar codigo compartido mas adelante, debe hacerse con una decision
formal, pruebas y validacion del equipo.

### 8.3 Hipotesis de feature engineering

Antes de crear features complejas, Fase 2 debe formular y validar hipotesis. Una
hipotesis es una suposicion que se puede contrastar con datos.

| Hipotesis | Como evaluarla | Decision posible |
|---|---|---|
| Algunas rutas estado-estado tardan mas que otras. | Comparar medianas de `dias_entrega_real` por `ruta_estado` con volumen minimo. | Crear features por ruta o rolling por ruta. |
| Algunos estados destino son logisticamente mas lentos. | Comparar `customer_state` por mediana, P90 y estabilidad temporal. | Mantener `customer_state` y rolling por destino. |
| El pasado reciente predice mejor que el promedio historico total. | Comparar rolling 30d vs promedio historico acumulado. | Priorizar rolling 30d si mejora MAE/backtesting. |
| Algunos sellers tienen comportamiento parecido. | Comparar sellers por volumen, categorias, tiempos y destinos atendidos. | Explorar clustering de sellers como experimento. |
| Algunas categorias tienen dificultad logistica similar. | Medir duracion y tardanza por categoria con volumen suficiente. | Crear grupos de categorias o rolling por categoria. |
| Zonas geoespaciales cercanas comparten comportamiento logistico. | Agrupar coordenadas o estados y comparar duracion por grupo. | Explorar clusters geoespaciales si son estables. |

### 8.4 Pruebas antes de aceptar una feature

Ninguna feature nueva deberia entrar al modelo solo porque parece interesante. Debe
pasar pruebas minimas.

| Prueba | Pregunta que responde |
|---|---|
| Disponibilidad M0 | La feature existe al momento de la compra? |
| Anti-leakage | Usa solo pasado y excluye la orden actual? |
| Cobertura | Se puede calcular para suficientes ordenes? |
| Estabilidad temporal | Funciona en train, val y test, o solo en un periodo? |
| Mejora incremental | Mejora MAE o backtesting frente al modelo sin esa feature? |
| Interpretabilidad | Se puede explicar a negocio sin forzar la historia? |
| Costo productivo | Se puede calcular en produccion sin arquitectura excesiva? |

**Mejora incremental** significa comparar el modelo sin la feature contra el modelo con
la feature. Si no mejora, no se justifica agregar complejidad.

### 8.5 Uso experimental de aprendizaje no supervisado

El aprendizaje no supervisado puede explorarse, pero no debe ser requisito inicial de
Fase 2.

**Aprendizaje no supervisado** significa que el algoritmo agrupa o resume datos sin usar
una respuesta correcta como target. Un ejemplo es clustering.

**Clustering** significa agrupar observaciones parecidas. Puede servir para crear nuevas
features, por ejemplo:

- clusters geoespaciales de zonas similares;
- clusters de rutas logisticas;
- clusters de sellers con comportamiento historico parecido;
- clusters de categorias con patrones de entrega similares.

La regla de diseno es:

> Clustering es una linea experimental de feature engineering, no una dependencia del
> MVP de Fase 2.

### 8.6 Clustering geoespacial

El clustering geoespacial puede ayudar a limpiar senales regionales. En vez de usar
coordenadas crudas o miles de rutas raras, se podrian formar grupos de zonas con
comportamiento similar.

Pautas:

| Pauta | Razon |
|---|---|
| Usar solo informacion disponible antes de la compra. | Evita leakage. |
| Comparar contra `customer_state` y `ruta_estado`. | El cluster solo vale si mejora lo simple. |
| Exigir estabilidad temporal. | Un cluster util no debe funcionar solo en un mes. |
| Mantener interpretabilidad. | El equipo debe poder explicar que representa cada grupo. |

Riesgo principal: un cluster geoespacial puede ser tecnicamente atractivo pero dificil
de explicar si no mejora metricas ni backtesting.

### 8.7 Clustering de sellers

Agrupar sellers puede ser util porque muchos vendedores tienen pocas ordenes. En vez de
tratar cada seller como unico, se podria asignar un seller a un grupo de comportamiento
parecido.

Variables historicas candidatas, siempre calculadas solo con pasado:

- volumen historico de ordenes;
- categorias vendidas previamente;
- estados destino atendidos previamente;
- mediana historica de dias reales;
- tasa historica de tardanza;
- dispersion de tiempos de entrega;
- proporcion de ordenes con historial suficiente.

Riesgos:

| Riesgo | Mitigacion |
|---|---|
| Seller nuevo sin historial. | Asignar cluster de respaldo o usar categoria/ruta/estado. |
| Leakage por usar todo el historial del seller. | Calcular features point-in-time, excluyendo orden actual y futuras. |
| Complejidad productiva. | Versionar el modelo de clustering y documentar fallback. |
| Baja interpretabilidad. | Describir clusters con perfiles simples: alto volumen, lento, regional, mixto, etc. |

### 8.8 Acople entre modelos supervisados y no supervisados

Usar clustering junto con regresion crea un sistema de dos pasos:

```text
Datos M0
   |
   v
Modelo no supervisado asigna cluster
   |
   v
Modelo supervisado predice dias_entrega_real
```

Esto puede mejorar el modelo, pero tambien complica produccion. Habria que versionar,
monitorear y probar dos componentes, no uno.

Por eso, la pauta productiva es:

1. Primero construir Fase 2 sin clustering.
2. Luego probar clustering como experimento aislado.
3. Aceptarlo solo si mejora MAE y backtesting de forma clara.
4. Mantenerlo solo si tiene fallback para datos nuevos o incompletos.
5. Documentar como se recalcula y versiona el cluster.

### 8.9 Criterios para aceptar clustering en Fase 2

Un cluster solo debe pasar a candidato productivo si cumple:

- mejora MAE en validacion frente al modelo sin cluster;
- mejora o mantiene el cumplimiento de promesa en backtesting;
- no reduce cobertura de forma grave;
- se calcula solo con informacion M0 o historica pasada;
- tiene significado de negocio interpretable;
- tiene estrategia para sellers, rutas o zonas nuevas;
- puede versionarse sin modificar Fase 1.

Si no cumple esos criterios, debe quedar como hallazgo exploratorio, no como parte de la
solucion principal.
## 9. Features prohibidas

Estas columnas no deben entrar como features porque se conocen despues de la compra o
derivan del resultado:

```text
order_delivered_carrier_date
order_delivered_customer_date
delivery_days
delivery_delay_days
is_late_delivery
review_count
avg_review_score
min_review_score
max_review_score
has_review_comment
review_comment_titles
review_comment_messages
last_review_creation_date
last_review_answer_timestamp
is_dissatisfied
entrega_tarde
dias_vs_promesa
dias_entrega_real
```

Nota importante:

- `dias_entrega_real` es valido como target.
- `dias_entrega_real` esta prohibido como feature.

---

## 10. Diseno de datasets experimentales

Para no mezclar decisiones, se proponen tres datasets de experimento.

| Dataset | Features | Objetivo |
|---|---|---|
| Baseline simple | Mediana global o mediana por `customer_state`. | Medir el piso minimo. |
| Fase 2 sin promesa | Features M0 + rolling, sin `dias_prometidos`. | Modelo principal para mejorar promesa. |
| Fase 2 con promesa | Features M0 + rolling + `dias_prometidos`. | Benchmark para medir cuanto aporta la promesa actual. |

La version recomendada para storytelling es **Fase 2 sin promesa**. Asi se evita que el
modelo simplemente copie la promesa vieja.

---

## 11. Evaluacion temporal

Fase 2 debe usar evaluacion temporal, no split aleatorio.

**Split aleatorio** significa mezclar pasado y futuro al azar. En este proyecto no es
recomendable porque puede hacer que el modelo aprenda patrones del futuro.

Evaluacion recomendada:

```text
train: pasado
val: periodo intermedio para seleccionar modelo/politica
test: futuro reciente para evaluacion final
```

Mantener la proporcion usada por Fase 1 como punto de partida:

| Split | Proporcion | Uso |
|---|---|---|
| Train | 70% | Entrenar modelos. |
| Val | 15% | Elegir modelo, features y politica. |
| Test | 15% | Evaluacion final honesta. |

Ademas, por el riesgo R-14 de cambio de regimen temporal, se recomienda reportar:

- MAE en train, val y test.
- Error por mes.
- Error por `customer_state`.
- Error por `ruta_estado` con suficiente volumen.
- Cumplimiento simulado de promesa por split.

---

## 12. Metricas tecnicas

### 12.1 Metrica principal

| Metrica | Lectura |
|---|---|
| MAE | Error absoluto medio en dias. Si MAE = 3, el modelo se equivoca unos 3 dias en promedio. |

MAE es la metrica principal porque es facil de explicar a negocio.

### 12.2 Metricas secundarias

| Metrica | Para que sirve |
|---|---|
| MedAE | Mediana del error absoluto; menos sensible a casos extremos. |
| P90 del error absoluto | Mide que tan malos son los errores grandes. |
| Bias promedio | Indica si el modelo tiende a subestimar o sobreestimar dias. |
| MAE por estado/ruta | Detecta zonas donde el modelo falla mas. |
| Cobertura rolling | Mide cuantas ordenes tienen historial reciente suficiente. |

**Bias** significa sesgo promedio del error. Si el modelo predice menos dias de los
reales, puede sobreprometer y aumentar incumplimientos.

---

## 13. Politica de nivel de servicio

El modelo predice una duracion esperada, pero la promesa final debe incluir una
politica de riesgo.

### 13.1 Politicas candidatas

| Politica | Lectura | Ventaja | Riesgo |
|---|---|---|---|
| P50 | Promesa cercana a la mediana. | Muy competitiva. | Alto riesgo de incumplir. |
| P80 | Busca cumplir alrededor de 80% de pedidos. | Balance entre velocidad y confianza. | Puede incumplir 1 de cada 5. |
| P90 | Busca cumplir alrededor de 90% de pedidos. | Mas confiable para cliente. | Promesa mas larga. |
| P95 | Muy conservadora. | Menor incumplimiento. | Puede parecer lenta. |

**P80, P90 o P95** son percentiles. P90 significa que la promesa apunta a cubrir el
90% de los casos, dejando alrededor de 10% con riesgo de llegar despues.

### 13.2 Recomendacion inicial

Para el primer diseno se recomienda evaluar:

- P80 como opcion competitiva.
- P90 como opcion balanceada.
- P95 como opcion conservadora.

No se recomienda elegir una politica sin backtesting.

---

## 14. Backtesting offline de promesas

**Backtesting** significa simular con datos historicos que habria pasado si Olist
hubiera usado una politica de promesa propuesta.

### 14.1 Pregunta del backtesting

> Si en el pasado hubieramos prometido usando Fase 2, que porcentaje de pedidos se
> habria cumplido y cuantos dias de colchon habriamos mostrado?

### 14.2 Metricas del backtesting

| Metrica | Lectura |
|---|---|
| Cumplimiento de promesa simulado | Porcentaje de ordenes que llegarian antes o en la fecha prometida. |
| Tasa de incumplimiento simulado | Porcentaje de ordenes que romperian la nueva promesa. |
| Colchon promedio simulado | Diferencia entre promesa y entrega real. |
| Colchon mediano simulado | Version robusta del colchon. |
| Promesa promedio vs promesa actual | Si la nueva promesa es mas corta, igual o mas larga. |
| Incumplimiento por estado/ruta | Donde la politica falla mas. |

### 14.3 Comparacion contra politica actual

La evaluacion debe comparar:

| Politica | Que representa |
|---|---|
| Promesa actual de Olist | Lo que ya estaba en el dataset. |
| Modelo Fase 2 P80 | Promesa mas competitiva. |
| Modelo Fase 2 P90 | Promesa balanceada. |
| Modelo Fase 2 P95 | Promesa conservadora. |

El objetivo no es necesariamente minimizar dias prometidos. El objetivo es encontrar
un balance entre:

```text
promesa atractiva para cliente
        +
cumplimiento confiable
```

---

## 15. Modelos candidatos

Este documento no implementa modelos, pero propone candidatos.

| Modelo | Por que considerarlo |
|---|---|
| Mediana global | Baseline minimo. |
| Mediana por `customer_state` | Baseline interpretable por destino. |
| Regresion Lineal / Ridge | Modelo simple e interpretable. |
| Random Forest Regressor | Captura relaciones no lineales. |
| XGBoost Regressor | Continuidad con Fase 1; suele funcionar bien con datos tabulares. |

**Modelo tabular** significa modelo que aprende desde filas y columnas, como una hoja
de calculo enriquecida.

Recomendacion inicial:

1. Empezar con baselines simples.
2. Probar un modelo interpretable.
3. Probar XGBoost Regressor como candidato fuerte.
4. Elegir por MAE en validacion y comportamiento de promesa en backtesting.

---

## 16. Experimentos minimos recomendados

| Experimento | Pregunta |
|---|---|
| E0 - Mediana global | Cuanto error tiene una regla muy simple? |
| E1 - Mediana por estado destino | Cuanto aporta segmentar por destino? |
| E2 - Features Fase 1 sin `dias_prometidos` | Cuanto predicen las features base? |
| E3 - Features Fase 1 + rolling 30d | Cuanto mejora el aprendizaje reciente? |
| E4 - E3 + `dias_prometidos` | La promesa actual aporta informacion adicional o solo copia politica vieja? |
| E5 - Backtesting P80/P90/P95 | Que politica de promesa balancea mejor cumplimiento y competitividad? |
| E6 - Clustering geoespacial experimental | Agrupar zonas/rutas mejora MAE o backtesting frente a `customer_state` y `ruta_estado`? |
| E7 - Clustering de sellers experimental | Agrupar sellers con poco historial aporta senal estable sin complicar produccion? |

---

## 17. Criterios de exito de Fase 2

Fase 2 se considera prometedora si cumple:

- Supera claramente a la mediana global en MAE.
- Mejora o iguala a la mediana por estado destino.
- Las rolling de 30 dias aportan mejora real frente a features base.
- El error no se concentra de forma grave en una region o ruta.
- El backtesting muestra una politica de promesa defendible.
- La solucion mantiene disciplina anti-leakage.

Fase 2 no debe avanzar a implementacion productiva si:

- Solo mejora usando `dias_prometidos`.
- Tiene errores muy altos en regiones especificas sin explicacion.
- La politica de promesa incumple demasiado.
- Las features rolling no tienen cobertura suficiente.
- Hay sospecha de leakage.

---

## 18. Riesgos especificos de Fase 2

| Riesgo | Impacto | Mitigacion |
|---|---|---|
| Copiar la promesa actual | El modelo no mejora nada, solo reproduce politica vieja. | Comparar modelos con y sin `dias_prometidos`. |
| Sobreprometer | Se muestran fechas demasiado cortas y sube el incumplimiento. | Evaluar P80/P90/P95 antes de elegir. |
| Poca historia por seller | Feature inestable para vendedores con pocas ordenes. | Usar respaldo por ruta, estado o categoria. |
| Cambio temporal | El modelo aprende un periodo que no representa el futuro. | Evaluar por split temporal y por mes. |
| Interpretacion causal incorrecta | Confundir correlacion con causa. | Presentar como senal predictiva, no como causalidad. |
| Feature engineering sin hipotesis previa | Crear features complejas que no aportan valor real. | Exigir hipotesis, EDA, ablation y validacion temporal. |
| Acople prematuro con clustering | Dos modelos en produccion antes de probar valor. | Mantener clustering como experimento aislado hasta demostrar mejora. |
| Dataset sin conversion/costos | No se puede probar todo el valor de negocio. | Declarar limite y medir solo promesa/cumplimiento offline. |

---

## 19. Decision recomendada antes de programar

Antes de escribir codigo de modelo, el equipo debe aprobar:

1. Target: `dias_entrega_real`.
2. Dataset principal: sin `dias_prometidos`.
3. Dataset benchmark: con `dias_prometidos`.
4. Ventana rolling inicial: 30 dias.
5. Politicas a evaluar: P80, P90 y P95.
6. Metrica principal: MAE.
7. Backtesting obligatorio antes de vender valor de promesa.
8. El clustering queda como linea experimental, no como requisito inicial del MVP.
9. Toda feature nueva debe pasar pruebas de cobertura, estabilidad, anti-leakage, mejora incremental e interpretabilidad.

---

## 20. Proximo entregable

El proximo entregable puede ser uno de estos dos:

| Opcion | Cuando elegirla |
|---|---|
| Documento de plan de implementacion Fase 2 | Si el equipo quiere revisar tareas antes de programar. |
| Script experimental de Fase 2 | Si el equipo ya aprueba este diseno y quiere medir modelos/backtesting. |

Recomendacion:

> Primero aprobar este diseno. Luego crear un script experimental local o de repo
> segun lo que el equipo quiera versionar.





