# -*- coding: utf-8 -*-
"""Scoring por lote desde CSV para el dashboard (HU-15, D-39).

Logica pura (sin Streamlit) para poder testearla: valida el CSV contra el
contrato de la API (docs/contrato_api.md), construye los payloads fila a fila
y los envia por el MISMO camino que el simulador (la API HTTP), de modo que el
batch nunca diverge del serving online.
"""
from __future__ import annotations

from typing import Callable

import pandas as pd

# Contrato [CLI] (docs/contrato_api.md).
COLUMNAS_OBLIGATORIAS = ["precio_total", "flete_total", "n_items", "customer_state", "timestamp"]
COLUMNAS_OPCIONALES = [
    "dias_prometidos", "seller_state", "categoria_principal", "peso_total_g",
    "volumen_total_cm3", "dist_haversine_km", "tasa_vendedor", "sin_historial_vendedor",
]
LIMITE_FILAS = 500  # proteccion del demo: el scoring va fila a fila por la API

PLANTILLA = pd.DataFrame({
    "precio_total": [134.97, 59.90, 89.00],
    "flete_total": [18.50, 8.90, 35.00],
    "n_items": [1, 1, 2],
    "customer_state": ["BA", "SP", "PA"],
    "timestamp": ["2018-07-10T14:30:00", "2018-07-15T10:00:00", "2018-07-12T09:00:00"],
    "dias_prometidos": [24.0, 12.0, 30.0],
    "seller_state": ["SP", "SP", "SP"],
    "categoria_principal": ["health_beauty", "watches_gifts", "bed_bath_table"],
})


def validar_csv(df: pd.DataFrame) -> list[str]:
    """Devuelve la lista de problemas (vacia si el CSV cumple el contrato)."""
    problemas = []
    faltantes = [c for c in COLUMNAS_OBLIGATORIAS if c not in df.columns]
    if faltantes:
        problemas.append(f"Faltan columnas obligatorias: {faltantes}. "
                         f"Descarga la plantilla para ver el formato.")
    if len(df) == 0:
        problemas.append("El CSV no tiene filas.")
    if len(df) > LIMITE_FILAS:
        problemas.append(f"El CSV tiene {len(df)} filas; el maximo del demo es "
                         f"{LIMITE_FILAS} (el scoring va fila a fila por la API).")
    desconocidas = [c for c in df.columns
                    if c not in COLUMNAS_OBLIGATORIAS + COLUMNAS_OPCIONALES]
    if desconocidas:
        problemas.append(f"Columnas ignoradas (no estan en el contrato): {desconocidas}")
    return problemas


def construir_payload(fila: pd.Series) -> dict:
    """Fila del CSV -> payload del contrato (omite opcionales vacios)."""
    payload = {
        "precio_total": float(fila["precio_total"]),
        "flete_total": float(fila["flete_total"]),
        "n_items": int(fila["n_items"]),
        "customer_state": str(fila["customer_state"]).strip().upper(),
        "timestamp": str(fila["timestamp"]),
    }
    for col in COLUMNAS_OPCIONALES:
        if col in fila.index and pd.notna(fila[col]) and str(fila[col]).strip() != "":
            if col in ("seller_state", "categoria_principal"):
                payload[col] = str(fila[col]).strip()
            elif col in ("sin_historial_vendedor", "n_items"):
                payload[col] = int(fila[col])
            else:
                payload[col] = float(fila[col])
    return payload


def puntuar_lote(
    df: pd.DataFrame,
    post: Callable[[str, dict], tuple[int, dict]],
    al_progresar: Callable[[float], None] | None = None,
) -> pd.DataFrame:
    """Puntua cada fila via la API: /promise siempre; riesgo si hay dias_prometidos.

    `post(ruta, payload) -> (status_code, json)` es inyectable (requests o
    TestClient), lo que mantiene una sola via de serving y permite testear.
    """
    resultados = []
    for i, (_, fila) in enumerate(df.iterrows()):
        payload = construir_payload(fila)
        registro: dict = {"fila": i + 1, **{c: fila.get(c) for c in COLUMNAS_OBLIGATORIAS}}

        code, promesa = post("/promise", payload)
        if code == 200:
            registro.update({
                "pred_dias": promesa["pred_dias"],
                "promesa_P90_dias": promesa["promesa_dias"],
                "imputaciones": ", ".join(promesa["flags_imputacion"]) or "ninguna",
            })
        else:
            registro["error"] = f"/promise {code}: {promesa.get('detail', promesa)}"

        if "dias_prometidos" in payload and code == 200:
            code_r, riesgo = post("/predict/delivery-risk", payload)
            if code_r == 200:
                registro.update({
                    "p_tarde_v2": riesgo["p_tarde"],
                    "alerta_riesgo": bool(riesgo["bandera_riesgo"]),
                })
            else:
                registro["error"] = f"/predict/delivery-risk {code_r}"

        resultados.append(registro)
        if al_progresar is not None:
            al_progresar((i + 1) / len(df))
    return pd.DataFrame(resultados)
