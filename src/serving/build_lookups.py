# -*- coding: utf-8 -*-
"""Hornea los lookups estaticos de serving desde los datos historicos (D-39).

La API recibe ~7 campos del cliente y el servidor deriva el resto de las
features del modelo con estos lookups (ver docs/contrato_api.md).

Granularidad: AGREGADO. El repo solo versiona data/processed/orders_features.csv
(sin product_id ni seller_id), por lo que los lookups se calculan a nivel de
categoria de producto, par de estados y estado del vendedor. Es el mismo patron
de degradacion controlada de D-38: cuando el equipo disponga de los CSV crudos
de Olist podra regenerar estos archivos con granularidad por ID sin cambiar el
contrato de la API (mismo esquema de salida, mas filas).

Disciplina point-in-time: TODOS los agregados se calculan SOLO con el split
`train` (corte 2018-04-15). Nunca val/test: sin fuga (D-05/D-22) y coherente
con el regimen R-14 (el baseline de drift usa la misma ventana).

Salidas en artifacts/serving/:
- catalogo_categorias.parquet     categoria_principal -> peso/volumen unitarios
- geo_estados.parquet             (customer_state, seller_state) -> dist mediana
- stats_vendedor_estado.parquet   seller_state -> tasa_vendedor mediana
- manifest.json                   corte, nivel, fallbacks globales, conteos

Uso:
    python -m src.serving.build_lookups [--input data/processed/orders_features.csv]
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = ROOT / "data" / "processed" / "orders_features.csv"
SERVING_DIR = ROOT / "artifacts" / "serving"


def construir_lookups(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Calcula los tres lookups agregados usando SOLO el split train."""
    train = df[df["split"] == "train"].copy()
    if train.empty:
        raise ValueError("El dataset no tiene filas con split == 'train'.")

    # Catalogo por categoria: peso/volumen UNITARIOS (por item) medianos.
    train["peso_unitario_g"] = train["peso_total_g"] / train["n_items"].clip(lower=1)
    train["volumen_unitario_cm3"] = train["volumen_total_cm3"] / train["n_items"].clip(lower=1)
    catalogo = (
        train.groupby("categoria_principal", dropna=True)
        .agg(
            peso_unitario_g=("peso_unitario_g", "median"),
            volumen_unitario_cm3=("volumen_unitario_cm3", "median"),
            n_ordenes=("categoria_principal", "size"),
        )
        .reset_index()
    )

    # Geo por par de estados: distancia haversine mediana observada en train.
    geo = (
        train.groupby(["customer_state", "seller_state"], dropna=True)
        .agg(dist_haversine_km=("dist_haversine_km", "median"), n_ordenes=("dist_haversine_km", "size"))
        .reset_index()
    )

    # Stats de vendedor por estado (proxy point-in-time congelado al corte):
    # mediana de la tasa historica de tardanza de los vendedores del estado.
    stats_vendedor = (
        train.groupby("seller_state", dropna=True)
        .agg(tasa_vendedor=("tasa_vendedor", "median"), n_ordenes=("tasa_vendedor", "size"))
        .reset_index()
    )

    return {"catalogo": catalogo, "geo": geo, "stats_vendedor": stats_vendedor, "_train": train}


def construir_manifest(train: pd.DataFrame, lookups: dict[str, pd.DataFrame]) -> dict:
    """Fallbacks globales y metadatos de trazabilidad."""
    return {
        "generado": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "nivel": "agregado (categoria / par de estados / estado vendedor)",
        "fuente": "data/processed/orders_features.csv (split train)",
        "fecha_corte_train": str(train["order_purchase_timestamp"].max()),
        "n_ordenes_train": int(len(train)),
        "fallbacks_globales": {
            "peso_unitario_g": float(train["peso_unitario_g"].median()),
            "volumen_unitario_cm3": float(train["volumen_unitario_cm3"].median()),
            "dist_haversine_km": float(train["dist_haversine_km"].median()),
            "tasa_vendedor": float(train["tasa_vendedor"].median()),
            "seller_state_modal": str(train["seller_state"].mode().iloc[0]),
            "categoria_modal": str(train["categoria_principal"].mode().iloc[0]),
        },
        "filas_por_lookup": {
            "catalogo_categorias": int(len(lookups["catalogo"])),
            "geo_estados": int(len(lookups["geo"])),
            "stats_vendedor_estado": int(len(lookups["stats_vendedor"])),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Hornea los lookups estaticos de serving (D-39).")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT,
                        help="Ruta a orders_features.csv (default: data/processed/).")
    args = parser.parse_args()

    print(f"[1/3] Leyendo {args.input} ...")
    df = pd.read_csv(args.input, parse_dates=["order_purchase_timestamp"])

    print("[2/3] Calculando lookups (solo split train, point-in-time) ...")
    lookups = construir_lookups(df)
    manifest = construir_manifest(lookups.pop("_train"), lookups)

    SERVING_DIR.mkdir(parents=True, exist_ok=True)
    lookups["catalogo"].to_parquet(SERVING_DIR / "catalogo_categorias.parquet", index=False)
    lookups["geo"].to_parquet(SERVING_DIR / "geo_estados.parquet", index=False)
    lookups["stats_vendedor"].to_parquet(SERVING_DIR / "stats_vendedor_estado.parquet", index=False)
    with open(SERVING_DIR / "manifest.json", "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, ensure_ascii=False)

    print(f"[3/3] Lookups horneados en {SERVING_DIR}")
    print(f"      corte train: {manifest['fecha_corte_train']} | "
          f"categorias: {manifest['filas_por_lookup']['catalogo_categorias']} | "
          f"pares geo: {manifest['filas_por_lookup']['geo_estados']} | "
          f"estados vendedor: {manifest['filas_por_lookup']['stats_vendedor_estado']}")


if __name__ == "__main__":
    main()
