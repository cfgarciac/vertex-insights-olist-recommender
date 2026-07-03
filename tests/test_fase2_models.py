"""Tests de modelos Fase 2 para regresion.

Usan datos sinteticos pequenos para validar el contrato de Chat E sin tocar
datasets, modelos ni artefactos de Fase 1.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.models import evaluate_fase2_regresion as ev
from src.models import train_fase2_regresion as train_fase2


def _synthetic_model_dataset(n_rows: int = 36) -> pd.DataFrame:
    base_date = pd.Timestamp("2018-01-01")
    rows = []
    for i in range(n_rows):
        if i < int(n_rows * 0.70):
            split = "train"
        elif i < int(n_rows * 0.85):
            split = "val"
        else:
            split = "test"
        customer_state = "SP" if i % 3 == 0 else "RJ" if i % 3 == 1 else "BA"
        seller_state = "SP" if i % 2 == 0 else "MG"
        ruta_estado = f"{seller_state}_{customer_state}"
        distance = 100.0 + 30.0 * i
        target = 3.0 + (customer_state == "BA") * 4.0 + distance / 400.0
        rows.append(
            {
                "order_id": f"order_{i:03d}",
                "order_purchase_timestamp": base_date + pd.Timedelta(days=i),
                "split": split,
                "dias_entrega_real": target,
                "customer_state": customer_state,
                "seller_state": seller_state,
                "categoria_principal": "books" if i % 2 == 0 else "toys",
                "mismo_estado": int(customer_state == seller_state),
                "dist_haversine_km": distance,
                "precio_total": 80.0 + i,
                "flete_total": 10.0 + i / 5,
                "ratio_flete": 0.1 + i / 1000,
                "n_items": 1 + (i % 3),
                "peso_total_g": 500.0 + i * 10,
                "volumen_total_cm3": 1000.0 + i * 20,
                "mes_compra": 1 + (i % 6),
                "dia_semana_compra": i % 7,
                "tasa_vendedor": 0.05 + (i % 4) / 100,
                "sin_historial_vendedor": int(i % 5 == 0),
                "seller_id": f"seller_{i % 4}",
                "ruta_estado": ruta_estado,
                "ruta_estado_30d_days_mean_fallback": target - 0.2,
                "ruta_estado_30d_days_median": target - 0.1,
                "ruta_estado_30d_orders_count": 5 + i,
                "ruta_estado_30d_sin_historial": 0,
                "customer_state_30d_days_mean_fallback": target - 0.3,
                "customer_state_30d_days_median": target - 0.2,
                "customer_state_30d_orders_count": 8 + i,
                "customer_state_30d_sin_historial": 0,
                "categoria_principal_30d_days_mean_fallback": target,
                "categoria_principal_30d_orders_count": 6 + i,
                "categoria_principal_30d_sin_historial": 0,
                "seller_id_30d_days_mean_fallback": target + 0.1,
                "seller_id_30d_orders_count": 3 + i,
                "seller_id_30d_sin_historial": int(i % 4 == 0),
            }
        )
    return pd.DataFrame(rows)


def test_columnas_prohibidas_fuera_de_x_cols():
    for feature_set in train_fase2.FEATURE_SETS.values():
        ev.assert_no_forbidden_features(feature_set)
        assert "dias_entrega_real" not in feature_set
        assert "order_purchase_timestamp" not in feature_set
        assert "split" not in feature_set


def test_seller_id_crudo_fuera_de_features():
    assert "seller_id" not in train_fase2.all_feature_columns()
    assert "seller_id_30d_days_mean_fallback" in train_fase2.all_feature_columns()


def test_split_temporal_respetado():
    df = _synthetic_model_dataset()
    ev.assert_temporal_split(df)

    broken = df.copy()
    broken.loc[broken["split"] == "test", "order_purchase_timestamp"] = pd.Timestamp(
        "2017-01-01"
    )
    with pytest.raises(AssertionError):
        ev.assert_temporal_split(broken)


def test_baselines_entrenan_y_predicen():
    df = _synthetic_model_dataset()
    train_df = df[df["split"] == "train"]
    val_df = df[df["split"] == "val"]

    for baseline in ev.build_baselines().values():
        baseline.fit(train_df, train_df[ev.TARGET])
        preds = baseline.predict(val_df)
        assert preds.shape == (len(val_df),)
        assert np.isfinite(preds).all()


def test_modelo_pequeno_entrena_y_predice_numeros():
    df = _synthetic_model_dataset()
    splits = train_fase2.split_data(df)
    feature_cols = train_fase2.FEATURE_SETS["M0_base_sin_rolling"]
    model = train_fase2.build_model_candidates(feature_cols)["ridge"]

    model.fit(splits["train"][feature_cols], splits["train"][ev.TARGET])
    preds = train_fase2.clipped_predict(model, splits["val"][feature_cols])

    assert preds.shape == (len(splits["val"]),)
    assert np.isfinite(preds).all()
    assert (preds >= 0).all()


def test_metricas_calculan_correctamente():
    y_true = np.array([1.0, 2.0, 4.0])
    y_pred = np.array([1.5, 1.0, 5.0])

    metrics = ev.regression_metrics(y_true, y_pred)

    assert metrics["mae"] == pytest.approx((0.5 + 1.0 + 1.0) / 3)
    assert metrics["medae"] == pytest.approx(1.0)
    assert metrics["rmse"] == pytest.approx(np.sqrt((0.25 + 1.0 + 1.0) / 3))
    assert metrics["p90_abs_error"] == pytest.approx(1.0)
    assert metrics["bias_mean"] == pytest.approx((0.5 - 1.0 + 1.0) / 3)

