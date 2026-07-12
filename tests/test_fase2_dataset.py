"""Tests del ETL experimental de Fase 2 para regresion.

Usan datos sinteticos pequenos para validar el contrato del dataset sin tocar
archivos ni artefactos de Fase 1.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from src.features import build_dataset_fase2_regresion as fase2


def _synthetic_tables(n_orders: int = 20) -> dict[str, pd.DataFrame]:
    base_date = pd.Timestamp("2018-01-01 10:00:00")
    order_ids = [f"order_{i:03d}" for i in range(n_orders)]
    customer_ids = [f"customer_{i:03d}" for i in range(n_orders)]
    product_ids = [f"product_{i % 4}" for i in range(n_orders)]
    seller_ids = [f"seller_{i % 3}" for i in range(n_orders)]

    orders = pd.DataFrame(
        {
            "order_id": order_ids,
            "customer_id": customer_ids,
            "order_status": ["delivered"] * n_orders,
            "order_purchase_timestamp": [
                base_date + pd.Timedelta(days=i) for i in range(n_orders)
            ],
            "order_approved_at": [
                base_date + pd.Timedelta(days=i, hours=1) for i in range(n_orders)
            ],
            "order_delivered_carrier_date": [
                base_date + pd.Timedelta(days=i + 1) for i in range(n_orders)
            ],
            "order_delivered_customer_date": [
                base_date + pd.Timedelta(days=i + 2 + (i % 5))
                for i in range(n_orders)
            ],
            "order_estimated_delivery_date": [
                base_date + pd.Timedelta(days=i + 6) for i in range(n_orders)
            ],
        }
    )

    customers = pd.DataFrame(
        {
            "customer_id": customer_ids,
            "customer_unique_id": [f"unique_{i:03d}" for i in range(n_orders)],
            "customer_zip_code_prefix": [10000 + i for i in range(n_orders)],
            "customer_city": ["sao paulo"] * n_orders,
            "customer_state": ["SP" if i % 2 == 0 else "RJ" for i in range(n_orders)],
        }
    )

    items_rows = []
    for i, order_id in enumerate(order_ids):
        items_rows.append(
            {
                "order_id": order_id,
                "order_item_id": 1,
                "product_id": product_ids[i],
                "seller_id": seller_ids[i],
                "shipping_limit_date": base_date + pd.Timedelta(days=i + 1),
                "price": 100.0 + i,
                "freight_value": 10.0 + (i % 4),
            }
        )
    items_rows.append(
        {
            "order_id": order_ids[0],
            "order_item_id": 2,
            "product_id": product_ids[1],
            "seller_id": seller_ids[1],
            "shipping_limit_date": base_date + pd.Timedelta(days=1),
            "price": 50.0,
            "freight_value": 5.0,
        }
    )
    items = pd.DataFrame(items_rows)

    products = pd.DataFrame(
        {
            "product_id": [f"product_{i}" for i in range(4)],
            "product_category_name": ["cama_mesa_banho", "beleza_saude"] * 2,
            "product_name_lenght": [20, 21, 22, 23],
            "product_description_lenght": [100, 110, 120, 130],
            "product_photos_qty": [1, 2, 1, 3],
            "product_weight_g": [500, 700, 900, 1100],
            "product_length_cm": [20, 30, 40, 50],
            "product_height_cm": [10, 11, 12, 13],
            "product_width_cm": [15, 16, 17, 18],
        }
    )

    sellers = pd.DataFrame(
        {
            "seller_id": [f"seller_{i}" for i in range(3)],
            "seller_zip_code_prefix": [20000 + i for i in range(3)],
            "seller_city": ["sao paulo", "rio", "campinas"],
            "seller_state": ["SP", "RJ", "MG"],
        }
    )

    geolocation = pd.DataFrame(
        {
            "geolocation_zip_code_prefix": list(customers["customer_zip_code_prefix"])
            + list(sellers["seller_zip_code_prefix"]),
            "geolocation_lat": np.linspace(-23.0, -20.0, n_orders + 3),
            "geolocation_lng": np.linspace(-46.0, -43.0, n_orders + 3),
            "geolocation_city": ["city"] * (n_orders + 3),
            "geolocation_state": ["SP"] * (n_orders + 3),
        }
    )

    translations = pd.DataFrame(
        {
            "product_category_name": ["cama_mesa_banho", "beleza_saude"],
            "product_category_name_english": ["bed_bath_table", "health_beauty"],
        }
    )

    return {
        "orders": orders,
        "customers": customers,
        "items": items,
        "products": products,
        "sellers": sellers,
        "geolocation": geolocation,
        "translations": translations,
    }


def _write_raw_tables(input_dir: Path, tables: dict[str, pd.DataFrame]) -> None:
    input_dir.mkdir(parents=True, exist_ok=True)
    for table_name, filename in fase2.RAW_FILES.items():
        tables[table_name].to_csv(input_dir / filename, index=False)


def test_una_fila_por_orden_y_target_valido():
    dataset = fase2.build_dataset(_synthetic_tables())

    assert dataset["order_id"].is_unique
    assert dataset.shape[0] == 20
    assert pd.api.types.is_numeric_dtype(dataset[fase2.TARGET])
    assert (dataset[fase2.TARGET] > 0).all()
    assert (dataset[fase2.TARGET] <= 365).all()


def test_split_temporal_70_15_15():
    dataset = fase2.build_dataset(_synthetic_tables())

    counts = dataset["split"].value_counts().to_dict()
    assert counts == {"train": 14, "val": 3, "test": 3}

    train_max = dataset.loc[
        dataset["split"] == "train", "order_purchase_timestamp"
    ].max()
    val_min = dataset.loc[dataset["split"] == "val", "order_purchase_timestamp"].min()
    val_max = dataset.loc[dataset["split"] == "val", "order_purchase_timestamp"].max()
    test_min = dataset.loc[
        dataset["split"] == "test", "order_purchase_timestamp"
    ].min()
    assert train_max <= val_min <= val_max <= test_min


def test_columnas_prohibidas_no_entran_como_features_ni_salida():
    dataset = fase2.build_dataset(_synthetic_tables())

    assert set(fase2.BASE_FEATURE_COLUMNS).isdisjoint(fase2.PROHIBITED_FEATURE_COLUMNS)
    assert "dias_prometidos" not in fase2.BASE_FEATURE_COLUMNS
    assert "dias_prometidos" not in dataset.columns

    forbidden_output = set(fase2.PROHIBITED_FEATURE_COLUMNS) - {fase2.TARGET}
    assert set(dataset.columns).isdisjoint(forbidden_output)


def test_salida_esperada_sin_usar_archivos_fase1(tmp_path):
    tables = _synthetic_tables()
    input_dir = tmp_path / "olist_raw"
    output_path = tmp_path / "orders_fase2_regresion.csv"
    _write_raw_tables(input_dir, tables)

    dataset = fase2.run(input_dir=input_dir, output=output_path)

    assert output_path.exists()
    assert output_path.name == "orders_fase2_regresion.csv"
    assert fase2.DEFAULT_OUTPUT.name == "orders_fase2_regresion.csv"
    assert "orders_p1_features.csv" not in str(fase2.DEFAULT_OUTPUT)
    assert dataset.shape[0] == 20
