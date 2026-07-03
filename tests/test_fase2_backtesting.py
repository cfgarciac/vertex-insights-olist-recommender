"""Tests del backtesting offline de promesas Fase 2.

Validan el contrato de Chat F con datos sinteticos: margenes solo con `val`,
promesas enteras nunca menores a 1, calculo de cumplimiento/colchon y candados
anti-leakage sin tocar Fase 1.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.models import backtest_promesas_fase2 as backtest
from src.models import evaluate_fase2_regresion as ev


def _toy_predictions() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "order_id": [f"o{i}" for i in range(8)],
            "split": ["train", "train", "val", "val", "val", "test", "test", "test"],
            "dias_entrega_real": [3.0, 4.0, 8.0, 10.0, 14.0, 5.0, 11.0, 18.0],
            "prediccion_dias": [3.0, 4.0, 7.0, 8.0, 10.0, 6.0, 10.0, 14.0],
            "customer_state": ["SP", "RJ", "SP", "RJ", "BA", "SP", "RJ", "BA"],
            "ruta_estado": ["SP_SP", "SP_RJ", "SP_SP", "SP_RJ", "SP_BA", "SP_SP", "SP_RJ", "SP_BA"],
            "dias_prometidos_actual": [6, 7, 10, 12, 18, 8, 16, 22],
        }
    )


def test_cumplimiento_y_colchon_se_calculan_correctamente():
    df = pd.DataFrame(
        {
            "dias_entrega_real": [5.0, 8.0, 10.0],
            "promesa": [6, 8, 9],
            "dias_prometidos_actual": [7, 9, 11],
        }
    )

    metrics = backtest.promise_metrics(df, "promesa")

    assert metrics["cumplimiento"] == pytest.approx(2 / 3)
    assert metrics["incumplimiento"] == pytest.approx(1 / 3)
    assert metrics["colchon_promedio"] == pytest.approx((1 + 0 - 1) / 3)
    assert metrics["colchon_mediano"] == pytest.approx(0.0)
    assert metrics["promesa_promedio"] == pytest.approx((6 + 8 + 9) / 3)


def test_promesa_simulada_nunca_menor_a_un_dia():
    promises = backtest.simulate_promise_days([0.2, -3.0, 2.1], margin=-2.0)

    assert promises.tolist() == [1, 1, 1]
    assert (promises >= 1).all()


def test_margenes_se_calculan_solo_con_val():
    df = _toy_predictions()
    margins = backtest.calculate_residual_margins(df[df["split"] == "val"])

    residual_val = np.array([1.0, 2.0, 4.0])
    assert margins["P80"] == pytest.approx(np.quantile(residual_val, 0.80))
    assert margins["P90"] == pytest.approx(np.quantile(residual_val, 0.90))
    assert margins["P95"] == pytest.approx(np.quantile(residual_val, 0.95))


def test_test_no_usado_para_definir_politica():
    df = _toy_predictions()
    margins_before = backtest.calculate_residual_margins(df[df["split"] == "val"])

    changed = df.copy()
    changed.loc[changed["split"] == "test", "dias_entrega_real"] = 999.0
    margins_after = backtest.calculate_residual_margins(changed[changed["split"] == "val"])

    assert margins_before == margins_after


def test_columnas_post_compra_y_seller_id_crudo_fuera_de_features():
    features = backtest.selected_features()

    ev.assert_no_forbidden_features(features)
    assert "seller_id" not in features
    assert "dias_entrega_real" not in features
    assert "dias_prometidos_actual" not in features
    assert "order_delivered_customer_date" not in features
    assert "order_delivered_carrier_date" not in features


def test_evaluate_policies_incluye_actual_y_simuladas():
    df = _toy_predictions()
    margins = {"P80": 1.0, "P90": 2.0, "P95": 3.0}
    df = backtest.add_simulated_promises(df, margins)

    rows = backtest.evaluate_policies(df, split="test")
    policies = {row["politica"] for row in rows}

    assert policies == {"actual_olist", "P80", "P90", "P95"}
    assert all(row["split"] == "test" for row in rows)
    assert all(row["ordenes"] == 3 for row in rows)


def test_fase1_intacta_durante_backtesting_sintetico():
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

    df = _toy_predictions()
    margins = backtest.calculate_residual_margins(df[df["split"] == "val"])
    df = backtest.add_simulated_promises(df, margins)
    _ = backtest.evaluate_policies(df, split="test")

    after = {path: path.stat().st_mtime_ns for path in protected_files if path.exists()}
    assert before == after
