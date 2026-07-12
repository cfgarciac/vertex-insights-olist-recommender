# Manual de usuario — Producto P1: Promesa inteligente + Escudo de riesgo

> **Para quién:** operaciones, atención al cliente y dirección de Olist (usuarios no
> técnicos) y evaluadores del proyecto. **Qué aprenderás:** qué te dice cada pieza del
> producto y cómo usarla. La instalación técnica está en el [README](../README.md).

## 1. Qué hace el producto (en una frase)

Cuando entra un pedido, el sistema **recomienda cuántos días prometer** (promesa
honesta, más corta y más confiable que la actual) y **marca si ese pedido está en
riesgo** de llegar tarde incluso con esa promesa — para priorizarlo en bodega o
avisar proactivamente al cliente.

## 2. Las cuatro puertas de entrada

| Herramienta | Para quién | Para qué |
|---|---|---|
| **API REST** (`:8000`) | sistemas de Olist (checkout, WMS) | pedir promesa y riesgo orden por orden, en ~30 ms |
| **Dashboard operativo** (`:8501`) | operaciones, día a día | simular órdenes, puntuar lotes CSV, ver drift |
| **Tablero Power BI** | dirección / junta | KPIs del negocio: dónde duele y cuánto vale |
| **Monitoreo** (scripts) | equipo de datos | vigilar que el modelo siga sano |

---

## 3. La API (para integraciones)

Con la API corriendo (README §Despliegue), abre **http://localhost:8000/docs**: es
una página interactiva (Swagger) donde puedes probar cada endpoint con "Try it out".

### 3.1 Pedir una promesa — `POST /promise`

Envías lo que el checkout ya sabe (5 campos mínimos):

```json
{
  "precio_total": 134.97, "flete_total": 18.5, "n_items": 1,
  "customer_state": "BA", "timestamp": "2018-07-10T14:30:00"
}
```

Respuesta: `pred_dias` (lo que el motor cree que tardará), **`promesa_dias`** (lo
que conviene prometer, política P90) y `flags_imputacion` (qué datos derivó el
servidor por ti — si envías más campos opcionales, deriva menos).

### 3.2 Pedir el riesgo — `POST /predict/delivery-risk`

Igual que el anterior **+ `dias_prometidos`** (la promesa vigente). Respuesta:
**`p_tarde`** (probabilidad calibrada de que llegue tarde) y **`bandera_riesgo`**
(true = priorizar esa orden). Con `"incluir_v1": true` devuelve también el escudo
v1 (riesgo contra la promesa vigente, útil en la transición).

### 3.3 ¿Está viva? — `GET /health`

Devuelve la versión del modelo, la política y los umbrales que está sirviendo
(trazabilidad total de qué versión respondió cada predicción).

**Errores que puedes ver:** `422` = el pedido está mal formado (falta un campo o
tiene un valor inválido; el detalle te dice cuál) · `503` = el modelo no está
cargado (revisa los prerrequisitos del README).

---

## 4. El dashboard operativo (Streamlit)

Abre **http://localhost:8501**. Cinco pestañas:

1. **🚨 Alertas de riesgo** — formulario de una orden: te devuelve la promesa
   recomendada, la probabilidad de tardanza y la bandera. Úsalo para explorar
   casos ("¿y si el pedido va a Pará?").
2. **📁 Scoring por CSV** — sube un archivo con muchas órdenes (hay una plantilla
   descargable; máx. 500 filas) y descarga los resultados con promesa + riesgo por
   orden. Ideal para puntuar el backlog de pedidos de la mañana.
3. **🗺️ Promesa por región** — compara la política P90 contra la promesa actual por
   estado, con foco Norte/Nordeste (donde la promesa actual falla más).
4. **📊 Métricas del modelo** — las cifras del cierre: 96.70% vs 94.32%, frontera
   cumplimiento-vs-longitud, sinergia del escudo.
5. **📈 Drift** — la salud del modelo (ver §6). Incluye una guía de lectura para no
   malinterpretar las barras rojas.

> La pestaña 1 y 2 necesitan la API viva; las demás funcionan solas.

---

## 5. El tablero Power BI (para la dirección)

Archivo `Vertex Power BI.pbix` (documentado en
`Documentacion_Dashboard_PowerBI_Vertex.md`, carpeta compartida del equipo).
Cinco páginas y la decisión que habilita cada una:

| Página | Qué muestra | Decisión que habilita |
|---|---|---|
| Portada | navegación | — |
| **Resumen Ejecutivo** | tardanza 8.1% · insatisfacción 5.8× · GMV expuesto · brecha regional 2.3× | ¿dónde duele y cuánto? |
| **Drivers** | tardanza por distancia, deciles de vendedor, AOV puntual vs tarde | ¿qué palancas mover? |
| **Logística** | buffer de promesa ~12 d · despacho 2.7 d · tránsito 9.3 d | ¿dónde está el tiempo? |
| **Financiero – GMV** | GMV total R$13.59M · **en riesgo R$3.80M (28%)** · por problema P1/P2/P3 | ¿qué priorizar y cuánto vale? |

> **Nota de universos:** el tablero mide TODA la operación (incluye canceladas y
> órdenes sin review); el modelo se evalúa sobre entregas con etiqueta. Por eso
> algunas cifras difieren levemente — la documentación del tablero lo detalla.

---

## 6. ¿El modelo sigue sano? (monitoreo, en 3 comandos)

```bash
python -m src.monitoring.simulate_production   # 1) genera tráfico (o llega de la API real)
python -m src.monitoring.drift                 # 2) ¿cambiaron los datos de entrada?
python -m src.monitoring.performance           # 3) ¿se siguen cumpliendo las promesas?
```

Lectura rápida (pestaña Drift del dashboard):
- **Verde/ok**: nada que hacer.
- **Ámbar/moderado**: investigar la feature.
- **Rojo/severo**: si además el cumplimiento realizado baja de 95%, aplicar el
  runbook (1º recalibrar márgenes, 2º reentrenar) — detalle en
  [estrategia_monitoreo.md](estrategia_monitoreo.md).
- **Gris/derivada**: ignorar (es un artefacto de los datos derivados, no drift real).

## 7. Preguntas frecuentes

- **¿Por qué la promesa recomendada a veces es MÁS larga que la actual?** Porque esa
  ruta/orden realmente tarda más: la promesa actual ahí está incumpliendo. El valor
  del producto es prometer lo cumplible (en el agregado, la promesa media BAJA 1.25 d).
- **¿Qué hago con una orden con bandera de riesgo?** Priorizarla en despacho o
  comunicar proactivamente al cliente; capturamos ~48% de los incumplimientos
  alertando ~35% de las órdenes.
- **¿Puedo confiar en la probabilidad?** Sí: está calibrada (Brier 0.063) — "30%"
  significa que ~3 de cada 10 órdenes así llegan tarde.
- **¿Cada cuánto se reentrena?** Cuando el monitoreo lo pida (disparadores en
  [plan_validacion.md](plan_validacion.md)); primero se recalibran márgenes (barato).
