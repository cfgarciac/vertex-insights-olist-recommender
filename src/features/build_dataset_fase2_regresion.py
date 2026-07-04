"""ETL experimental de Fase 2 para regresion de dias_entrega_real.

Construye una tabla analitica a nivel orden desde las tablas crudas de Olist,
sin modificar ni depender del pipeline validado de Fase 1. El dataset resultante
esta pensado para experimentos posteriores de regresion, no para entrenar aqui.

Reglas principales:
  - Universo: ordenes `delivered` con fecha de compra y entrega real.
  - Target: `dias_entrega_real`, dias entre compra y entrega al cliente.
  - Features: solo variables conocidas en M0 o historicos cerrados antes de M0.
  - Split: temporal 70/15/15 por `order_purchase_timestamp`.
  - Sin `dias_prometidos` en el dataset principal inicial.

Uso:
    python -m src.features.build_dataset_fase2_regresion \
        --input-dir "C:/ruta/OLIST DATASETS" \
        --output data/processed/orders_fase2_regresion.csv
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Mapping

import numpy as np
import pandas as pd


# --------------------------------------------------------------------------- #
# 0. Contrato de columnas y rutas
# --------------------------------------------------------------------------- #
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT_DIR = Path(
    r"C:\Users\LENOVO\Documents\Cursos\Soy Henry\PF\proyecto"
    r"\MLops_Pipeline_VERTEX\OLIST DATASETS"
)
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "processed" / "orders_fase2_regresion.csv"

TARGET = "dias_entrega_real"
ROLLING_WINDOW_DAYS = 30
MIN_ORDENES_VENDEDOR = 5

RAW_FILES = {
    "customers": "olist_customers_dataset.csv",
    "geolocation": "olist_geolocation_dataset.csv",
    "orders": "olist_orders_dataset.csv",
    "items": "olist_order_items_dataset.csv",
    "products": "olist_products_dataset.csv",
    "sellers": "olist_sellers_dataset.csv",
    "translations": "product_category_name_translation.csv",
}

DATE_COLUMNS = {
    "orders": [
        "order_purchase_timestamp",
        "order_approved_at",
        "order_delivered_carrier_date",
        "order_delivered_customer_date",
        "order_estimated_delivery_date",
    ],
}

PROHIBITED_FEATURE_COLUMNS = [
    "order_delivered_carrier_date",
    "order_delivered_customer_date",
    "delivery_days",
    "delivery_delay_days",
    "is_late_delivery",
    "review_count",
    "avg_review_score",
    "min_review_score",
    "max_review_score",
    "has_review_comment",
    "review_comment_titles",
    "review_comment_messages",
    "last_review_creation_date",
    "last_review_answer_timestamp",
    "is_dissatisfied",
    "entrega_tarde",
    "dias_vs_promesa",
    TARGET,
]

# Dataset principal Fase 2: sin dias_prometidos. Puede existir luego como
# benchmark controlado, pero no entra al primer ETL experimental.
EXCLUDED_MAIN_FEATURE_COLUMNS = ["dias_prometidos"]

BASE_FEATURE_COLUMNS = [
    "customer_state",
    "seller_state",
    "categoria_principal",
    "mismo_estado",
    "dist_haversine_km",
    "precio_total",
    "flete_total",
    "ratio_flete",
    "n_items",
    "peso_total_g",
    "volumen_total_cm3",
    "mes_compra",
    "dia_semana_compra",
    "tasa_vendedor",
    "sin_historial_vendedor",
]

# Columnas de soporte para features rolling futuras; no son features directas del
# dataset principal mientras no exista validacion incremental.
ROLLING_SUPPORT_COLUMNS = [
    "seller_id",
    "ruta_estado",
]

OUTPUT_COLUMNS = (
    ["order_id", "order_purchase_timestamp", "split", TARGET]
    + BASE_FEATURE_COLUMNS
    + ROLLING_SUPPORT_COLUMNS
)


# --------------------------------------------------------------------------- #
# 1. Carga de tablas crudas
# --------------------------------------------------------------------------- #
def load_raw_tables(input_dir: str | Path) -> dict[str, pd.DataFrame]:
    """Carga las tablas crudas requeridas desde el directorio local de Olist."""
    input_path = Path(input_dir)
    tables: dict[str, pd.DataFrame] = {}

    for name, filename in RAW_FILES.items():
        path = input_path / filename
        if not path.exists():
            raise FileNotFoundError(f"No se encontro la tabla requerida: {path}")
        tables[name] = pd.read_csv(path)

    for table_name, columns in DATE_COLUMNS.items():
        for col in columns:
            tables[table_name][col] = pd.to_datetime(
                tables[table_name][col], errors="coerce"
            )

    return tables


def summarize_raw_columns(input_dir: str | Path) -> dict[str, list[str]]:
    """Devuelve el esquema de columnas de cada CSV disponible en input_dir."""
    input_path = Path(input_dir)
    schemas: dict[str, list[str]] = {}
    for path in sorted(input_path.glob("*.csv")):
        schemas[path.name] = list(pd.read_csv(path, nrows=0).columns)
    return schemas


# --------------------------------------------------------------------------- #
# 2. Consolidacion a nivel orden
# --------------------------------------------------------------------------- #
def build_order_table(tables: Mapping[str, pd.DataFrame]) -> pd.DataFrame:
    """Reconstruye una fila por orden desde las tablas crudas de Olist."""
    orders = tables["orders"].copy()
    customers = tables["customers"].copy()
    items = tables["items"].copy()
    products = tables["products"].copy()
    sellers = tables["sellers"].copy()
    translations = tables["translations"].copy()
    geolocation = tables["geolocation"].copy()

    orders = orders[
        (orders["order_status"] == "delivered")
        & orders["order_purchase_timestamp"].notna()
        & orders["order_delivered_customer_date"].notna()
    ].copy()

    geolocation_zip = (
        geolocation.groupby("geolocation_zip_code_prefix", as_index=False)
        .agg(
            geolocation_lat=("geolocation_lat", "median"),
            geolocation_lng=("geolocation_lng", "median"),
        )
        .rename(columns={"geolocation_zip_code_prefix": "zip_code_prefix"})
    )

    customers = customers.merge(
        geolocation_zip.add_prefix("customer_"),
        left_on="customer_zip_code_prefix",
        right_on="customer_zip_code_prefix",
        how="left",
    )
    sellers = sellers.merge(
        geolocation_zip.add_prefix("seller_"),
        left_on="seller_zip_code_prefix",
        right_on="seller_zip_code_prefix",
        how="left",
    )

    item_level = (
        items.merge(products, on="product_id", how="left")
        .merge(translations, on="product_category_name", how="left")
        .merge(sellers, on="seller_id", how="left")
    )
    item_level["item_volume_cm3"] = (
        item_level["product_length_cm"]
        * item_level["product_height_cm"]
        * item_level["product_width_cm"]
    )
    item_level["categoria_principal"] = item_level[
        "product_category_name_english"
    ].fillna(item_level["product_category_name"])
    item_level["categoria_principal"] = item_level["categoria_principal"].fillna(
        "desconocido"
    )

    item_level = item_level.sort_values(["order_id", "order_item_id"])
    principal = (
        item_level.groupby("order_id", as_index=False)
        .first()[
            [
                "order_id",
                "seller_id",
                "seller_state",
                "seller_geolocation_lat",
                "seller_geolocation_lng",
                "categoria_principal",
            ]
        ]
        .rename(
            columns={
                "seller_geolocation_lat": "seller_lat",
                "seller_geolocation_lng": "seller_lng",
            }
        )
    )

    agg = (
        item_level.groupby("order_id", as_index=False)
        .agg(
            n_items=("order_item_id", "count"),
            precio_total=("price", "sum"),
            flete_total=("freight_value", "sum"),
            peso_total_g=("product_weight_g", "sum"),
            volumen_total_cm3=("item_volume_cm3", "sum"),
        )
    )

    order_level = (
        orders.merge(customers, on="customer_id", how="left")
        .merge(principal, on="order_id", how="left")
        .merge(agg, on="order_id", how="left")
    )
    order_level = order_level.rename(
        columns={
            "customer_geolocation_lat": "customer_lat",
            "customer_geolocation_lng": "customer_lng",
        }
    )
    return order_level


# --------------------------------------------------------------------------- #
# 3. Target y features M0 directas
# --------------------------------------------------------------------------- #
def haversine_km(lat1, lon1, lat2, lon2):
    """Calcula distancia haversine en km entre dos puntos geograficos."""
    radius_km = 6371.0
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    return 2 * radius_km * np.arcsin(np.sqrt(a))


def add_target_and_base_features(orders: pd.DataFrame) -> pd.DataFrame:
    """Agrega el target de regresion y las features base conocidas en M0."""
    orders = orders.copy()
    orders[TARGET] = (
        orders["order_delivered_customer_date"] - orders["order_purchase_timestamp"]
    ).dt.total_seconds() / 86400.0
    orders = orders[orders[TARGET] > 0].copy()

    orders["entrega_tarde_hist"] = (
        orders["order_delivered_customer_date"]
        > orders["order_estimated_delivery_date"]
    ).astype(int)

    orders["ratio_flete"] = orders["flete_total"] / orders["precio_total"].replace(
        0, np.nan
    )
    orders["mes_compra"] = orders["order_purchase_timestamp"].dt.month.astype("int64")
    orders["dia_semana_compra"] = orders[
        "order_purchase_timestamp"
    ].dt.dayofweek.astype("int64")
    orders["mismo_estado"] = (
        orders["customer_state"] == orders["seller_state"]
    ).astype("int64")
    orders["ruta_estado"] = (
        orders["seller_state"].fillna("NA") + "_" + orders["customer_state"].fillna("NA")
    )
    orders["dist_haversine_km"] = haversine_km(
        orders["customer_lat"],
        orders["customer_lng"],
        orders["seller_lat"],
        orders["seller_lng"],
    )

    for col in ["peso_total_g", "volumen_total_cm3", "ratio_flete"]:
        orders[col] = orders[col].replace([np.inf, -np.inf], np.nan)
        orders[col] = orders[col].fillna(orders[col].median())

    return orders


# --------------------------------------------------------------------------- #
# 4. Split temporal y feature historica de vendedor
# --------------------------------------------------------------------------- #
def temporal_split(
    orders: pd.DataFrame, frac_train: float = 0.70, frac_val: float = 0.15
) -> pd.DataFrame:
    """Asigna train/val/test ordenando por fecha de compra, sin aleatoriedad."""
    orders = orders.sort_values(["order_purchase_timestamp", "order_id"]).reset_index(
        drop=True
    )
    n_rows = len(orders)
    idx_train = int(n_rows * frac_train)
    idx_val = int(n_rows * (frac_train + frac_val))

    split = np.array(["train"] * n_rows, dtype=object)
    split[idx_train:idx_val] = "val"
    split[idx_val:] = "test"
    orders["split"] = split
    return orders


def add_seller_rate(
    orders: pd.DataFrame,
    global_rate_train: float,
    min_orders: int = MIN_ORDENES_VENDEDOR,
) -> pd.DataFrame:
    """Calcula tasa historica de tardanza del vendedor disponible antes de M0.

    Para ser estrictos con M0, una orden previa solo aporta si su entrega real ya
    habia ocurrido antes de la compra de la orden actual. Si no hay suficiente
    historial cerrado, se usa la tasa global del split train y se marca el flag.
    """
    orders = orders.sort_values(["order_purchase_timestamp", "order_id"]).copy()
    rates = pd.Series(index=orders.index, dtype="float64")
    no_history = pd.Series(index=orders.index, dtype="int64")

    for _, seller_orders in orders.groupby("seller_id", sort=False):
        previous: list[int] = []
        for idx, row in seller_orders.iterrows():
            purchase_time = row["order_purchase_timestamp"]
            known_previous = [
                prev_idx
                for prev_idx in previous
                if orders.at[prev_idx, "order_delivered_customer_date"] < purchase_time
            ]
            if len(known_previous) >= min_orders:
                rates.at[idx] = orders.loc[known_previous, "entrega_tarde_hist"].mean()
                no_history.at[idx] = 0
            else:
                rates.at[idx] = global_rate_train
                no_history.at[idx] = 1
            previous.append(idx)

    orders["tasa_vendedor"] = rates.astype("float64")
    orders["sin_historial_vendedor"] = no_history.astype("int64")
    return orders.sort_values(["order_purchase_timestamp", "order_id"]).reset_index(
        drop=True
    )


# --------------------------------------------------------------------------- #
# 5. Validaciones anti-leakage y salida
# --------------------------------------------------------------------------- #
def assert_dataset_contract(dataset: pd.DataFrame) -> None:
    """Valida el contrato minimo del dataset experimental de Fase 2."""
    duplicated = dataset["order_id"].duplicated().sum()
    if duplicated:
        raise AssertionError(f"Dataset con ordenes duplicadas: {duplicated}")

    if not pd.api.types.is_numeric_dtype(dataset[TARGET]):
        raise AssertionError(f"{TARGET} debe ser numerico")
    if not (dataset[TARGET] > 0).all():
        raise AssertionError(f"{TARGET} debe ser positivo")
    if not (dataset[TARGET] <= 365).all():
        raise AssertionError(f"{TARGET} contiene valores no razonables (>365 dias)")

    forbidden_features = set(BASE_FEATURE_COLUMNS) & set(PROHIBITED_FEATURE_COLUMNS)
    if forbidden_features:
        raise AssertionError(f"Features prohibidas detectadas: {forbidden_features}")

    excluded_features = set(BASE_FEATURE_COLUMNS) & set(EXCLUDED_MAIN_FEATURE_COLUMNS)
    if excluded_features:
        raise AssertionError(
            f"Features excluidas del dataset principal: {excluded_features}"
        )

    observed_splits = set(dataset["split"].unique())
    if observed_splits != {"train", "val", "test"}:
        raise AssertionError(f"Splits inesperados: {observed_splits}")

    max_train = dataset.loc[dataset["split"] == "train", "order_purchase_timestamp"].max()
    min_val = dataset.loc[dataset["split"] == "val", "order_purchase_timestamp"].min()
    max_val = dataset.loc[dataset["split"] == "val", "order_purchase_timestamp"].max()
    min_test = dataset.loc[dataset["split"] == "test", "order_purchase_timestamp"].min()
    if not (max_train <= min_val <= max_val <= min_test):
        raise AssertionError("El split temporal no respeta el orden cronologico")


def build_dataset(tables: Mapping[str, pd.DataFrame]) -> pd.DataFrame:
    """Construye el dataset final de Fase 2 desde tablas ya cargadas."""
    orders = build_order_table(tables)
    orders = add_target_and_base_features(orders)
    orders = temporal_split(orders)

    global_rate_train = orders.loc[
        orders["split"] == "train", "entrega_tarde_hist"
    ].mean()
    orders = add_seller_rate(orders, global_rate_train=float(global_rate_train))

    dataset = orders[OUTPUT_COLUMNS].copy()
    assert_dataset_contract(dataset)
    return dataset


def run(input_dir: str | Path = DEFAULT_INPUT_DIR, output: str | Path = DEFAULT_OUTPUT):
    """Ejecuta el ETL completo y guarda el CSV experimental no versionado."""
    print(f"[1/5] Leyendo tablas crudas desde: {input_dir}")
    tables = load_raw_tables(input_dir)

    print("[2/5] Consolidando a nivel orden y creando target/features M0")
    dataset = build_dataset(tables)

    print("[3/5] Validando contrato anti-leakage y split temporal")
    assert_dataset_contract(dataset)

    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    dataset.to_csv(output_path, index=False)

    print("[4/5] Dataset guardado")
    print(f"      ruta: {output_path}")
    print(f"      shape: {dataset.shape[0]:,} x {dataset.shape[1]:,}")
    print("[5/5] Conteo por split")
    print(dataset["split"].value_counts().reindex(["train", "val", "test"]).to_string())
    return dataset


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="ETL experimental Fase 2 para regresion de dias_entrega_real"
    )
    parser.add_argument("--input-dir", default=str(DEFAULT_INPUT_DIR))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument(
        "--schema-only",
        action="store_true",
        help="Imprime columnas de los CSV disponibles y no genera dataset.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    if args.schema_only:
        for filename, columns in summarize_raw_columns(args.input_dir).items():
            print(f"{filename}: {', '.join(columns)}")
    else:
        run(args.input_dir, args.output)
