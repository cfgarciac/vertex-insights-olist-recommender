# Project Charter - P1 Desempeno de entrega Olist

> **Estado:** Borrador inicial para validacion del equipo  
> **Proyecto:** Vertex Insights - Olist Marketplace  
> **Problema elegido:** P1 - Desempeno de entrega  
> **Fase actual:** Fase 1 entregada; Fase 2 recomendada en diseno  
> **Ultima actualizacion:** 2026-06-29

---

## 1. Resumen ejecutivo

Olist es un marketplace: conecta clientes, vendedores y operadores logisticos. En este
tipo de negocio, la confianza del cliente depende mucho de una pregunta simple:
**"mi pedido llegara cuando me dijeron que llegaria?"**

Durante el descubrimiento del problema, el equipo evaluo varias alternativas. La
hipotesis inicial del cliente era un recomendador item-to-item, es decir, sugerir
productos parecidos o complementarios. Ese camino fue investigado y resulto viable,
pero limitado por la baja recompra y la baja co-compra del dataset. El equipo entonces
pivoto hacia un dolor mas fuerte y mejor sostenido por los datos: **el desempeno de
entrega**.

El veredicto del DVA es: **P1 es viable con reservas**.

Esto significa:

- **Viable**, porque existe un target limpio (`entrega_tarde`), variables disponibles
  al momento de la compra, disciplina anti-leakage y un modelo inicial que supera al
  azar.
- **Con reservas**, porque las metricas son moderadas, el dataset no mide todos los
  costos de negocio y la promesa actual de entrega parece tener un colchon amplio.

Por eso el proyecto queda ordenado en dos fases:

| Fase | Estado | Objetivo |
|---|---|---|
| Fase 1 | Entregada | Clasificar si una orden tiene riesgo de llegar tarde contra la promesa actual. |
| Fase 2 | Recomendada | Estimar `dias_entrega_real` para ayudar a construir una promesa de entrega mas inteligente. |

---

## 2. Problema de negocio

Olist promete al cliente una fecha estimada de entrega. Cuando esa promesa se rompe,
el cliente percibe incumplimiento, aunque Olist no controle toda la cadena logistica.

El problema no es solamente "entregar rapido". El problema real es mas preciso:

> **Olist necesita prometer fechas de entrega que sean confiables para el cliente y,
> al mismo tiempo, suficientemente competitivas para no parecer innecesariamente lento.**

Una promesa demasiado optimista aumenta el riesgo de incumplir. Una promesa demasiado
conservadora protege contra reclamos, pero puede reducir atractivo comercial: el
cliente podria elegir otra opcion si ve una entrega demasiado lejana.

---

## 3. Usuario destino

El usuario destino principal no es un operador que corrige pedidos uno por uno.

El usuario destino es:

> **El sistema o equipo de Olist que define la fecha prometida de entrega en el
> momento de la compra.**

En terminos simples, el flujo esperado seria:

```text
Nueva orden en checkout
        |
        v
Variables conocidas en ese momento
        |
        v
Modelo estima riesgo o duracion
        |
        v
Politica de promesa decide fecha visible para cliente
        |
        v
Cliente recibe una promesa mas realista
```

La solucion tambien puede apoyar a equipos de monitoreo logistico, pero su valor
principal esta antes de la entrega: **prometer mejor desde el inicio**.

---

## 4. Valor de negocio esperado

El valor de negocio se organiza en tres niveles.

### 4.1 Proteger la confianza del cliente

Si el cliente recibe una fecha y Olist no la cumple, se rompe una expectativa. Aunque
la causa sea el vendedor, la ruta o el operador logistico, el cliente ve la promesa
como parte de la experiencia de compra.

### 4.2 Priorizar riesgo logistico

La Fase 1 permite ordenar pedidos por probabilidad de llegar tarde. Esto no resuelve
toda la operacion, pero ayuda a identificar donde esta el riesgo.

### 4.3 Mejorar la promesa de entrega

La Fase 2 apunta al valor mas fuerte: estimar cuantos dias tardara realmente una
orden y convertir esa estimacion en una promesa. Esto permitiria ajustar la promesa
por ruta, estado, vendedor, categoria y comportamiento reciente.

---

## 5. Evidencia que sostiene el Charter

### 5.1 Evidencia del DVA de P1

| Hallazgo | Lectura |
|---|---|
| Universo P1: 96,470 ordenes entregadas etiquetables. | Hay volumen suficiente para analisis y modelado. |
| Tasa global `entrega_tarde`: 8.1%. | La clase tardia es minoria; se necesita evaluar con metricas adecuadas. |
| Mediana real cercana a 10 dias vs promesa cercana a 23 dias. | La promesa actual tiene colchon; hay espacio para discutir ajuste. |
| Variables honestas disponibles en M0. | El modelo puede operar al momento de compra sin usar informacion futura. |
| XGBoost logra ROC-AUC 0.703 y PR-AUC 0.124 en test. | El modelo no es perfecto, pero ordena riesgo mejor que el azar. |

**M0** significa "momento cero": el momento de compra o aprobacion de la orden. En este
proyecto, una feature solo es valida si se conoce en M0.

### 5.2 Evidencia temporal reciente

El EDA temporal robusto local refuerza la idea de Fase 2:

| Patron | Evidencia | Lectura |
|---|---|---|
| La tardanza cambia por mes. | Marzo 2018 llega a 21.4% de tardanza; junio 2018 baja a 1.4%. | La promesa no deberia depender solo de promedios historicos. |
| La operacion reciente parece mas rapida. | En test, la mediana real baja a 7.2 dias. | Olist puede necesitar promesas adaptadas al regimen reciente. |
| La ruta importa. | `ruta_estado_30d` tiene correlacion 0.530 con dias reales y cobertura 95.4%. | La historia reciente por ruta es una senal fuerte para duracion. |
| El destino importa. | `customer_state_30d` tiene correlacion 0.504 y cobertura 99.7%. | El estado del cliente captura dificultad logistica regional. |
| El vendedor aporta, pero con reservas. | `seller_id_30d` tiene senal, pero menor cobertura. | Usar vendedor cuando haya historial; respaldar con ruta/estado/categoria cuando no. |

**Rolling 30 dias** significa mirar una ventana movil de los ultimos 30 dias antes de
la compra. Es una forma de aprender del pasado reciente sin mirar el futuro.

---

## 6. Alcance

### Dentro del alcance

- Mantener la Fase 1 como clasificador de `entrega_tarde`.
- Documentar el problema P1 como dolor de negocio principal.
- Usar solo features disponibles al momento de compra.
- Evaluar con split temporal, es decir, entrenar con pasado y medir con futuro.
- Disenar Fase 2 como regresion sobre `dias_entrega_real`.
- Definir una politica de nivel de servicio para convertir dias estimados en promesa.

**Regresion** significa predecir un numero. En Fase 2, el numero seria la duracion
real de entrega en dias.

**Nivel de servicio** significa que porcentaje de pedidos queremos cumplir dentro de
la fecha prometida. Por ejemplo, una politica P90 busca que aproximadamente 90% de
los pedidos lleguen dentro de la fecha prometida.

### Fuera del alcance

- No optimizar rutas logisticas reales.
- No prometer reduccion directa de costos logisticos.
- No medir conversion, abandono de carrito o recompra, porque el dataset no tiene
  esos datos.
- No usar resenas, fecha real de entrega ni variables post-entrega como features.
- No tratar ordenes canceladas/no entregadas como parte del target principal.
- No vender Fase 2 como modelo de series temporales puro.

---

## 7. KPIs y metricas

### 7.1 KPIs de negocio

| KPI | Que mide | Uso |
|---|---|---|
| Tasa de entregas tardias | Porcentaje de ordenes que rompen la promesa. | Mide dolor visible para cliente. |
| GMV expuesto a tardanza | Valor monetario de ordenes afectadas por tardanza. | Da magnitud economica del problema. |
| Cumplimiento de promesa | Porcentaje de pedidos entregados dentro de la fecha prometida. | Mide confiabilidad de la promesa. |
| Colchon de promesa | Diferencia entre dias prometidos y dias reales. | Mide cuan conservadora es la promesa. |

**GMV** significa Gross Merchandise Value: valor bruto de mercancia vendida. En simple,
es el valor de las ventas asociadas a las ordenes.

### 7.2 Metricas tecnicas de Fase 1

| Metrica | Lectura simple |
|---|---|
| ROC-AUC | Que tan bien separa el modelo ordenes tardias vs puntuales. |
| PR-AUC | Que tan bien encuentra la clase minoritaria: las tardias. |
| Recall | De todas las tardias reales, cuantas logra detectar. |
| Precision | De las que marca como riesgo, cuantas realmente llegan tarde. |
| Calibracion | Si una probabilidad de 30% se comporta como 30% en la realidad. |

### 7.3 Metricas tecnicas de Fase 2

| Metrica | Lectura simple |
|---|---|
| MAE | Error promedio en dias. Si MAE = 3, el modelo se equivoca unos 3 dias en promedio. |
| Error por region/ruta | Ver si el modelo falla mas en algunas zonas. |
| Cobertura de features rolling | Porcentaje de ordenes con suficiente historial reciente. |
| Cumplimiento simulado de promesa | Si prometieramos con la regla propuesta, que porcentaje se cumpliria. |

**MAE** significa Mean Absolute Error, o error absoluto medio. Es una metrica natural
para Fase 2 porque se entiende en dias.

---

## 8. Fases del proyecto

### Fase 1 - Clasificacion de entrega tardia

**Estado:** entregada.

Objetivo:

> Predecir si una orden llegara tarde contra la promesa actual de Olist.

Resultado:

- Target: `entrega_tarde`.
- Modelo candidato: XGBoost.
- Metrica en test: ROC-AUC 0.703; PR-AUC 0.124.
- Uso recomendado: priorizacion de riesgo logistico.

Limitacion:

> Protege la promesa actual, pero no necesariamente mejora la promesa que ve el
> cliente.

### Fase 2 - Regresion de dias reales de entrega

**Estado:** recomendada; pendiente de diseno tecnico formal.

Objetivo:

> Estimar `dias_entrega_real` para construir una promesa de entrega mas honesta,
> competitiva y adaptada al contexto logistico.

Features candidatas:

- Features actuales de Fase 1 disponibles en M0.
- Rolling 30 dias por `ruta_estado`.
- Rolling 30 dias por `customer_state`.
- Rolling 30 dias por `categoria_principal`.
- Rolling 30 dias por `seller_id`, con respaldo cuando no haya historial suficiente.

Salida esperada:

```text
Prediccion de dias reales
        |
        v
Politica de nivel de servicio
        |
        v
Fecha prometida al cliente
```

---

## 9. Riesgos y mitigaciones

| Riesgo | Nivel | Mitigacion |
|---|---|---|
| Data leakage: usar informacion futura como feature. | Alto | Mantener regla M0 y lista de columnas prohibidas. |
| Cambio de regimen temporal. | Medio | Evaluar siempre con split temporal y revisar calibracion. |
| Muchos vendedores con poco historial. | Medio | Usar `seller_id` con respaldo por ruta, estado o categoria. |
| Valor de negocio no completamente medible. | Medio | Declarar que no hay conversion, abandono ni costo logistico real. |
| Sobreprometer fechas demasiado agresivas. | Alto | Definir politica de nivel de servicio antes de usar Fase 2. |
| Alcance excesivo para el tiempo disponible. | Alto | Separar Fase 1 entregada, Fase 2 diseno y posible implementacion posterior. |

---

## 10. Supuestos

- La fecha de compra representa el momento en que se necesita predecir.
- Olist puede usar informacion historica agregada por ruta, estado, vendedor o
  categoria al momento de compra.
- La promesa de entrega puede ser ajustada por una politica de negocio.
- El dataset publico de Olist es suficiente para una prueba offline, pero no para
  medir todos los efectos de negocio.
- Las ordenes canceladas/no entregadas son un dolor real, pero requieren tratamiento
  aparte porque no tienen fecha real de entrega.

---

## 11. Criterios de exito del Charter

Este Charter se considera valido si el equipo puede responder con claridad:

- Que dolor de negocio se eligio.
- Por que se eligio P1 y no el recomendador como solucion final.
- Que entrega Fase 1 y que no entrega.
- Por que Fase 2 es la evolucion natural.
- Quien usaria la solucion.
- Que metricas mediran el exito.
- Que riesgos y limites quedan declarados.

---

## 12. Proximo paso

El siguiente entregable recomendado es:

> **Diseno de Fase 2: regresion sobre `dias_entrega_real`.**

Ese documento debe definir:

- Target final.
- Features candidatas.
- Politica anti-leakage.
- Metricas tecnicas.
- Evaluacion temporal.
- Politica de nivel de servicio.
- Backtesting offline de promesas.

**Backtesting** significa simular en datos historicos que habria pasado si la politica
propuesta se hubiera usado en ese momento.

---

## 13. Glosario corto

| Termino | Explicacion simple |
|---|---|
| Target | La variable que queremos predecir. |
| Feature | Una pista que usa el modelo para predecir. |
| Leakage | Fuga de datos: usar informacion del futuro por error. |
| Split temporal | Separar datos por tiempo: pasado para aprender, futuro para probar. |
| Rolling | Ventana movil de historia reciente. |
| Regresion | Modelo que predice un numero. |
| Clasificacion | Modelo que predice una categoria, como tarde/no tarde. |
| Nivel de servicio | Porcentaje de pedidos que se busca cumplir dentro de la promesa. |
| Calibracion | Que la probabilidad estimada se parezca a la frecuencia real. |
