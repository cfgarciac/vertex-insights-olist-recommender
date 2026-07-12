"""Tests de rolling point-in-time para Fase 2.

Validan con datos sinteticos que las features de historia reciente solo usen
ordenes ya entregadas antes de M0 y que el dataset final no exponga columnas
posteriores a la compra.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.features import rolling_fase2 as rolling


def _synthetic_rolling_dataset() -> pd.DataFrame:
    rows = [
        {
            "order_id": "hist_fuera_ventana",
            "order_purchase_timestamp": "2017-12-20",
            "order_delivered_customer_date": "2017-12-22",
            "split": "train",
            "dias_entrega_real": 2.0,
            "ruta_estado": "SP_RJ",
            "customer_state": "RJ",
            "categoria_principal": "books",
            "seller_id": "seller_a",
        },
        {
            "order_id": "hist_valida_1",
            "order_purchase_timestamp": "2018-01-20",
            "order_delivered_customer_date": "2018-01-25",
            "split": "train",
            "dias_entrega_real": 5.0,
            "ruta_estado": "SP_RJ",
            "customer_state": "RJ",
            "categoria_principal": "books",
            "seller_id": "seller_a",
        },
        {
            "order_id": "hist_valida_2",
            "order_purchase_timestamp": "2018-01-24",
            "order_delivered_customer_date": "2018-01-28",
            "split": "train",
            "dias_entrega_real": 4.0,
            "ruta_estado": "SP_RJ",
            "customer_state": "RJ",
            "categoria_principal": "books",
            "seller_id": "seller_b",
        },
        {
            "order_id": "comprada_antes_no_cerrada",
            "order_purchase_timestamp": "2018-01-26",
            "order_delivered_customer_date": "2018-02-20",
            "split": "train",
            "dias_entrega_real": 25.0,
            "ruta_estado": "SP_RJ",
            "customer_state": "RJ",
            "categoria_principal": "books",
            "seller_id": "seller_a",
        },
        {
            "order_id": "actual",
            "order_purchase_timestamp": "2018-02-01",
            "order_delivered_customer_date": "2018-02-10",
            "split": "val",
            "dias_entrega_real": 9.0,
            "ruta_estado": "SP_RJ",
            "customer_state": "RJ",
            "categoria_principal": "books",
            "seller_id": "seller_a",
        },
        {
            "order_id": "futura",
            "order_purchase_timestamp": "2018-02-05",
            "order_delivered_customer_date": "2018-02-07",
            "split": "test",
            "dias_entrega_real": 2.0,
            "ruta_estado": "SP_RJ",
            "customer_state": "RJ",
            "categoria_principal": "books",
            "seller_id": "seller_a",
        },
        {
            "order_id": "sin_historial_grupo",
            "order_purchase_timestamp": "2018-02-01",
            "order_delivered_customer_date": "2018-02-04",
            "split": "val",
            "dias_entrega_real": 3.0,
            "ruta_estado": "MG_BA",
            "customer_state": "BA",
            "categoria_principal": "toys",
            "seller_id": "seller_nuevo",
        },
    ]
    df = pd.DataFrame(rows)
    df["order_purchase_timestamp"] = pd.to_datetime(df["order_purchase_timestamp"])
    df["order_delivered_customer_date"] = pd.to_datetime(
        df["order_delivered_customer_date"]
    )
    return df


def _row(df: pd.DataFrame, order_id: str) -> pd.Series:
    return df.loc[df["order_id"] == order_id].iloc[0]


def test_excluye_orden_actual_y_ordenes_futuras():
    result = rolling.add_rolling_features(_synthetic_rolling_dataset())
    actual = _row(result, "actual")

    assert actual["ruta_estado_30d_orders_count"] == 2
    assert actual["ruta_estado_30d_days_mean"] == 4.5

    # Si la orden actual o la futura entraran por error, el conteo seria mayor.
    assert actual["seller_id_30d_orders_count"] == 1
    assert actual["seller_id_30d_days_mean"] == 5.0


def test_excluye_orden_comprada_antes_pero_entregada_despues_de_m0():
    result = rolling.add_rolling_features(_synthetic_rolling_dataset())
    actual = _row(result, "actual")

    assert actual["ruta_estado_30d_orders_count"] == 2
    assert actual["ruta_estado_30d_days_mean"] == 4.5
    assert actual["ruta_estado_30d_days_median"] == 4.5


def test_respeta_conteo_por_ventana_de_30_dias():
    result = rolling.add_rolling_features(_synthetic_rolling_dataset())
    actual = _row(result, "actual")

    assert actual["customer_state_30d_orders_count"] == 2
    assert actual["categoria_principal_30d_orders_count"] == 2
    assert actual["ruta_estado_30d_sin_historial"] == 0


def test_fallback_jerarquico_correcto():
    result = rolling.add_rolling_features(_synthetic_rolling_dataset())
    sin_historial = _row(result, "sin_historial_grupo")

    global_train_median = _synthetic_rolling_dataset()
    global_train_median = global_train_median.loc[
        global_train_median["split"] == "train", "dias_entrega_real"
    ].median()

    assert sin_historial["ruta_estado_30d_sin_historial"] == 1
    assert sin_historial["seller_id_30d_sin_historial"] == 1
    assert sin_historial["ruta_estado_30d_days_mean_fallback"] == global_train_median
    assert sin_historial["seller_id_30d_days_mean_fallback"] == global_train_median
    assert sin_historial["categoria_principal_30d_days_mean_fallback"] == global_train_median


def test_columnas_prohibidas_no_salen_como_features():
    result = rolling.add_rolling_features(_synthetic_rolling_dataset())
    output = rolling.clean_output_columns(result)

    forbidden = rolling.FORBIDDEN_OUTPUT_COLUMNS & set(output.columns)
    assert not forbidden
    assert "order_delivered_customer_date" not in output.columns
    assert "dias_entrega_real" in output.columns


def test_run_no_toca_archivos_fase1(tmp_path):
    dataset = _synthetic_rolling_dataset()
    input_path = tmp_path / "orders_fase2_regresion.csv"
    output_path = tmp_path / "orders_fase2_regresion_rolling.csv"
    report_path = tmp_path / "fase2_rolling_features.md"
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()

    dataset.drop(columns=["order_delivered_customer_date"]).to_csv(input_path, index=False)
    dataset[["order_id", "order_delivered_customer_date"]].to_csv(
        raw_dir / rolling.RAW_ORDERS_FILE, index=False
    )

    protected_files = [
        Path("src/features/build_dataset.py"),
        Path("src/models/train.py"),
        Path("src/models/evaluate.py"),
        Path("src/models/predict.py"),
        Path("src/models/baseline.py"),
        Path("tests/test_models.py"),
        Path("reports/etapa4_metrics.json"),
    ]
    before = {path: path.stat().st_mtime_ns for path in protected_files if path.exists()}

    output = rolling.build_rolling_dataset(
        input_path=input_path,
        input_dir=raw_dir,
        output_path=output_path,
        report_path=report_path,
    )

    after = {path: path.stat().st_mtime_ns for path in protected_files if path.exists()}
    assert before == after
    assert output_path.exists()
    assert report_path.exists()
    assert output.shape[0] == dataset.shape[0]
