# -*- coding: utf-8 -*-
"""Deriva las features del modelo desde el contrato minimo del request (D-39).

El cliente envia ~7 campos ([CLI], ver docs/contrato_api.md) y esta capa
reconstruye la fila EXACTA que esperan el motor (15 features) y el escudo
(16 features [t0]), leyendo las listas desde el propio artefacto serializado
(nunca hardcodeadas) y usando los lookups horneados por build_lookups.py.

Toda imputacion queda registrada en `flags_imputacion` (se devuelve en la
respuesta de la API y se persiste en logs/predictions.jsonl): es el insumo del
monitoreo de calidad de datos (HU-16).
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SERVING_DIR = ROOT / "artifacts" / "serving"

# Campos obligatorios del contrato [CLI].
CAMPOS_OBLIGATORIOS = ("precio_total", "flete_total", "n_items", "customer_state", "timestamp")


class FeatureBuilder:
    """Carga los lookups UNA vez y construye filas de features por request."""

    def __init__(self, serving_dir: Path | str = SERVING_DIR) -> None:
        serving_dir = Path(serving_dir)
        manifest_path = serving_dir / "manifest.json"
        if not manifest_path.exists():
            raise FileNotFoundError(
                f"No hay lookups en {serving_dir}. Ejecuta: python -m src.serving.build_lookups"
            )
        with open(manifest_path, encoding="utf-8") as fh:
            self.manifest = json.load(fh)
        self.fallbacks = self.manifest["fallbacks_globales"]

        catalogo = pd.read_parquet(serving_dir / "catalogo_categorias.parquet")
        self._catalogo = catalogo.set_index("categoria_principal")[
            ["peso_unitario_g", "volumen_unitario_cm3"]
        ]
        geo = pd.read_parquet(serving_dir / "geo_estados.parquet")
        self._geo_par = geo.set_index(["customer_state", "seller_state"])["dist_haversine_km"]
        self._geo_estado = geo.groupby("customer_state")["dist_haversine_km"].median()
        stats = pd.read_parquet(serving_dir / "stats_vendedor_estado.parquet")
        self._tasa_estado = stats.set_index("seller_state")["tasa_vendedor"]

    # ------------------------------------------------------------------ #
    def construir(self, datos: dict) -> tuple[pd.DataFrame, list[str]]:
        """request [CLI] validado -> (fila con las 16 columnas, flags de imputacion).

        `datos` admite ademas overrides opcionales: seller_state,
        categoria_principal, peso_total_g, volumen_total_cm3,
        dist_haversine_km, tasa_vendedor, sin_historial_vendedor,
        dias_prometidos (requerido solo por el escudo).
        """
        faltan = [c for c in CAMPOS_OBLIGATORIOS if datos.get(c) is None]
        if faltan:
            raise ValueError(f"Faltan campos obligatorios del contrato: {faltan}")

        flags: list[str] = []
        ts = pd.Timestamp(datos["timestamp"])
        precio = float(datos["precio_total"])
        flete = float(datos["flete_total"])
        n_items = int(datos["n_items"])
        customer_state = str(datos["customer_state"]).upper()

        # --- seller_state: lo envia Olist o se imputa al modal del train ---
        seller_state = datos.get("seller_state")
        if seller_state is None:
            seller_state = self.fallbacks["seller_state_modal"]
            flags.append("seller_state:modal_train")
        seller_state = str(seller_state).upper()

        # --- categoria: la envia el cliente o se imputa a la modal ---
        categoria = datos.get("categoria_principal")
        if categoria is None:
            categoria = self.fallbacks["categoria_modal"]
            flags.append("categoria_principal:modal_train")

        # --- peso / volumen: override del cliente o catalogo por categoria ---
        peso = datos.get("peso_total_g")
        volumen = datos.get("volumen_total_cm3")
        if peso is None or volumen is None:
            if categoria in self._catalogo.index:
                fila_cat = self._catalogo.loc[categoria]
                origen = "catalogo_categoria"
            else:
                fila_cat = pd.Series(
                    {
                        "peso_unitario_g": self.fallbacks["peso_unitario_g"],
                        "volumen_unitario_cm3": self.fallbacks["volumen_unitario_cm3"],
                    }
                )
                origen = "global_train"
            if peso is None:
                peso = float(fila_cat["peso_unitario_g"]) * n_items
                flags.append(f"peso_total_g:{origen}")
            if volumen is None:
                volumen = float(fila_cat["volumen_unitario_cm3"]) * n_items
                flags.append(f"volumen_total_cm3:{origen}")

        # --- distancia: override, par de estados, estado del cliente o global ---
        dist = datos.get("dist_haversine_km")
        if dist is None:
            par = (customer_state, seller_state)
            if par in self._geo_par.index:
                dist = float(self._geo_par.loc[par])
                flags.append("dist_haversine_km:par_estados")
            elif customer_state in self._geo_estado.index:
                dist = float(self._geo_estado.loc[customer_state])
                flags.append("dist_haversine_km:estado_cliente")
            else:
                dist = float(self.fallbacks["dist_haversine_km"])
                flags.append("dist_haversine_km:global_train")

        # --- tasa de vendedor: override, estado del vendedor o prior global ---
        tasa = datos.get("tasa_vendedor")
        sin_historial = datos.get("sin_historial_vendedor")
        if tasa is None:
            if seller_state in self._tasa_estado.index:
                tasa = float(self._tasa_estado.loc[seller_state])
                flags.append("tasa_vendedor:estado_vendedor")
            else:
                tasa = float(self.fallbacks["tasa_vendedor"])
                flags.append("tasa_vendedor:prior_global")
                if sin_historial is None:
                    sin_historial = 1
        if sin_historial is None:
            sin_historial = 0
            flags.append("sin_historial_vendedor:default_0")

        # --- ratio de flete (guardia division por cero) ---
        if precio > 0:
            ratio_flete = flete / precio
        else:
            ratio_flete = 0.0
            flags.append("ratio_flete:precio_cero")

        fila = pd.DataFrame(
            [
                {
                    "dias_prometidos": (
                        float(datos["dias_prometidos"]) if datos.get("dias_prometidos") is not None else None
                    ),
                    "dist_haversine_km": float(dist),
                    "ratio_flete": float(ratio_flete),
                    "precio_total": precio,
                    "flete_total": flete,
                    "n_items": n_items,
                    "peso_total_g": float(peso),
                    "volumen_total_cm3": float(volumen),
                    "tasa_vendedor": float(tasa),
                    "mes_compra": int(ts.month),
                    "dia_semana_compra": int(ts.dayofweek),
                    "customer_state": customer_state,
                    "seller_state": seller_state,
                    "categoria_principal": str(categoria),
                    "mismo_estado": int(customer_state == seller_state),
                    "sin_historial_vendedor": int(sin_historial),
                }
            ]
        )
        return fila, flags

    # ------------------------------------------------------------------ #
    @staticmethod
    def validar_contrato(fila: pd.DataFrame, bundle: dict) -> None:
        """Candado anti-divergencia: las columnas construidas deben cubrir las
        listas guardadas EN el artefacto (motor y escudo). Lanza ValueError."""
        esperadas_motor = set(bundle["motor_features"])
        escudo = bundle["escudo"]
        esperadas_escudo = set(escudo["numeric_features"]) | set(escudo["categorical_features"])
        producidas = set(fila.columns)
        faltan = (esperadas_motor | esperadas_escudo) - producidas
        if faltan:
            raise ValueError(f"feature_builder no produce columnas requeridas por el modelo: {sorted(faltan)}")
