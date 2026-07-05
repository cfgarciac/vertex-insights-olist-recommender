# Contrato de la API — Producto P1 (promesa inteligente + escudo de riesgo)

> Define QUÉ envía el cliente y QUÉ deriva el servidor (D-39, §1.2.2 de
> [arquitectura_despliegue.md](arquitectura_despliegue.md)). El modelo está
> entrenado con features fijas (motor: 15, escudo: 16 [t0]); este contrato las
> reconstruye desde ~7 campos sin tocar el modelo.

## Endpoints

| Método | Ruta | Qué devuelve | Modelo |
|---|---|---|---|
| GET | `/health` | estado, versión del artefacto, política y umbrales (provisionales) | — |
| POST | `/promise` | `pred_dias` + `promesa_dias` (P90) + márgenes | motor (15 features) |
| POST | `/predict/delivery-risk` | `p_tarde` + `bandera_riesgo` (escudo v2; v1 opcional) | escudo (16 features) |

## Campos del request

### Obligatorios [CLI] (ambos endpoints)

| Campo | Tipo | Ejemplo | Nota |
|---|---|---|---|
| `precio_total` | float > 0 | `134.97` | total de productos del pedido (BRL) |
| `flete_total` | float ≥ 0 | `18.50` | flete cotizado |
| `n_items` | int ≥ 1 | `2` | ítems del carrito |
| `customer_state` | str (UF) | `"BA"` | estado del cliente |
| `timestamp` | ISO datetime | `"2018-07-10T14:30:00"` | momento de la compra |

### Obligatorio solo en `/predict/delivery-risk`

| Campo | Tipo | Nota |
|---|---|---|
| `dias_prometidos` | float > 0 | la promesa VIGENTE de Olist (estimated_delivery − purchase). El escudo la usa como feature [t0]; sin ella el endpoint responde 422. `/promise` NO la necesita (el motor no la usa, decisión de Fase 2). |

### Opcionales (si Olist los conoce, mejoran la precisión; si faltan, se derivan y se flaggea)

`seller_state`, `categoria_principal`, `peso_total_g`, `volumen_total_cm3`,
`dist_haversine_km`, `tasa_vendedor`, `sin_historial_vendedor`.

## Derivación en el servidor [SRV]

| Feature | Cómo se deriva | Flag si se imputa |
|---|---|---|
| `ratio_flete` | `flete_total / precio_total` (0 si precio=0) | `ratio_flete:precio_cero` |
| `mismo_estado` | `customer_state == seller_state` | — |
| `mes_compra`, `dia_semana_compra` | del `timestamp` (lunes=0) | — |
| `seller_state` | modal del train (`SP`) si no viene | `seller_state:modal_train` |
| `categoria_principal` | modal del train si no viene | `categoria_principal:modal_train` |
| `peso_total_g`, `volumen_total_cm3` | mediana unitaria de la categoría × `n_items` (lookup `catalogo_categorias`) → global | `peso_total_g:catalogo_categoria` / `:global_train` |
| `dist_haversine_km` | mediana del par (cliente, vendedor) → mediana del estado del cliente → global (lookup `geo_estados`) | `dist_haversine_km:par_estados` / `:estado_cliente` / `:global_train` |
| `tasa_vendedor` | mediana del estado del vendedor (lookup `stats_vendedor_estado`) → prior global (+ `sin_historial_vendedor=1`) | `tasa_vendedor:estado_vendedor` / `:prior_global` |

Los lookups se hornean con `python -m src.serving.build_lookups` **solo con el
split train** (corte 2018-04-15, point-in-time, sin fuga). Granularidad actual:
**agregado** (el repo no versiona product_id/seller_id); con los CSV crudos de
Olist se regeneran a nivel de ID con el mismo esquema (degradación controlada,
patrón D-38). Los `flags_imputacion` viajan en la respuesta y en
`logs/predictions.jsonl` — insumo del monitoreo de calidad de datos (HU-16).

## Ejemplos

```bash
# Promesa (request mínimo)
curl -s -X POST http://localhost:8000/promise -H "Content-Type: application/json" -d '{
  "precio_total": 134.97, "flete_total": 18.5, "n_items": 1,
  "customer_state": "BA", "timestamp": "2018-07-10T14:30:00"}'
# -> {"pred_dias": 19.52, "promesa_dias": 26, "politica": "P90", ...}

# Riesgo (requiere la promesa vigente)
curl -s -X POST http://localhost:8000/predict/delivery-risk -H "Content-Type: application/json" -d '{
  "precio_total": 134.97, "flete_total": 18.5, "n_items": 1,
  "customer_state": "BA", "timestamp": "2018-07-10T14:30:00", "dias_prometidos": 24}'
# -> {"p_tarde": 0.49, "bandera_riesgo": true, "escudo": "v2", ...}
```

## Errores

| Código | Cuándo |
|---|---|
| 422 | payload inválido (Pydantic) o `dias_prometidos` ausente en `/predict/delivery-risk` |
| 503 | artefacto o lookups no cargados al arrancar |
| 500 | error interno controlado |

> **Valores provisionales:** política P90 y umbrales (v1 = 0.0721 @ recall_obj_70,
> v2 = 0.3658) tomados del artefacto D-38, **pendientes de confirmación del PO**
> (Fase 0 del roadmap). `/health` los expone para trazabilidad.
