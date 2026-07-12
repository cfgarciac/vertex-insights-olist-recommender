"""Tests del producto conjunto — promesa inteligente + escudo de riesgo (D-38).

Verifican lo esencial sin correr el pipeline completo:
  - el bloque de features del motor no contiene columnas prohibidas (anti-fuga),
  - los márgenes P80/P90/P95 son monótonos y las promesas son enteras y >= 1,
  - la política mixta queda acotada entre las promesas P80 y P95 por orden,
  - el escudo (v1) del artefacto de Fase 1 produce probabilidades válidas,
  - la sinergia se calcula con el contrato esperado.

Se subsamplea para que la suite sea rápida y determinista.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.models import backtest_promesas_fase2 as bt
from src.models import producto_promesa_riesgo as ppr
from src.models import train_fase2_regresion as train_f2

pytestmark = pytest.mark.skipif(
    not ppr.DATA_BASE.exists() or not ppr.ESCUDO_ARTIFACT.exists(),
    reason="datos base o escudo de Fase 1 no disponibles",
)


@pytest.fixture(scope="module")
def producto():
    """Motor entrenado en subsample + promesas + escudo, una sola vez por sesión."""
    df, feature_set = ppr.cargar_datos()
    # Subsample estratificado por split (determinista) para velocidad.
    df = pd.concat(
        [g.sample(min(6000, len(g)), random_state=42) for _, g in df.groupby("split")],
        ignore_index=True,
    )
    modelo, features = ppr.entrenar_motor(df, feature_set)
    df, margenes = ppr.predecir_y_prometer(df, modelo, features)
    df, escudo = ppr.aplicar_escudo(df)
    df = ppr.agregar_politica_mixta(df, margenes)
    return df, margenes, escudo


def test_features_motor_sin_fuga():
    df, feature_set = ppr.cargar_datos()
    features = train_f2.FEATURE_SETS[feature_set]
    # El candado de Fase 2 no permite target, fechas post-compra ni la promesa.
    assert ppr.TARGET not in features
    assert "dias_prometidos" not in features
    assert "seller_id" not in features


def test_margenes_monotonos_y_promesas_validas(producto):
    df, margenes, _ = producto
    assert margenes["P80"] <= margenes["P90"] <= margenes["P95"]
    for pol in bt.POLICY_QUANTILES:
        col = df[f"promesa_{pol}"]
        assert col.dtype.kind == "i" and (col >= 1).all()


def test_mixta_acotada_por_p80_y_p95(producto):
    df, _, _ = producto
    assert (df["promesa_mixta_riesgo"] >= df["promesa_P80"]).all()
    assert (df["promesa_mixta_riesgo"] <= df["promesa_P95"]).all()


def test_escudo_probabilidades_validas(producto):
    df, _, escudo = producto
    assert df["prob_riesgo_tarde"].between(0, 1).all()
    assert set(df["bandera_riesgo"].unique()) <= {0, 1}
    assert 0.0 < escudo["umbral"] < 1.0


def test_cumplimiento_val_cercano_al_cuantil(producto):
    """Los márgenes se calculan en val: ahí el cumplimiento ≈ el cuantil por construcción."""
    df, _, _ = producto
    val = df[df["split"] == "val"]
    cumplimiento_p90 = (val[ppr.TARGET] <= val["promesa_P90"]).mean()
    assert cumplimiento_p90 >= 0.88  # 0.90 nominal, con holgura por subsample + ceil


def test_sinergia_contrato(producto):
    df, _, _ = producto
    s = ppr.sinergia_escudo(df, "promesa_P90")
    assert {"promesa", "incumplidas"} <= set(s)
    if s["incumplidas"]:
        assert 0.0 <= s["pct_incumplidas_marcadas_por_escudo"] <= 1.0
