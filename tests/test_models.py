"""Tests de la Etapa 4 — modelado de P1 (entrega tardía).

Verifican lo esencial sin reentrenar el pipeline completo:
  - que ninguna feature [POST] entre al modelo (candado anti-fuga, R-12),
  - que el pipeline (preprocesador + estimador) entrena y predice probabilidades
    válidas,
  - que la serialización con joblib es idempotente (round-trip),
  - que un clasificador real supera al baseline de clase mayoritaria en PR-AUC.

Se subsamplea train/val para que la suite sea rápida y determinista.
"""

from __future__ import annotations

import joblib
import numpy as np
import pytest
from sklearn.metrics import average_precision_score

from src.models import baseline as bl
from src.models import evaluate as ev
from src.models.train import (
    DEFAULT_DATA,
    TARGET,
    X_COLS,
    cargar_splits,
    construir_modelos,
    proba_positiva,
)

pytestmark = pytest.mark.skipif(
    not DEFAULT_DATA.exists(), reason="dataset orders_p1_features.csv no disponible"
)


@pytest.fixture(scope="module")
def datos():
    _, train, val, _ = cargar_splits(DEFAULT_DATA)
    tr = train.sample(n=min(15000, len(train)), random_state=42).reset_index(drop=True)
    va = val.sample(n=min(5000, len(val)), random_state=42).reset_index(drop=True)
    return tr, va


def test_sin_features_post():
    # No debe haber columnas [POST] entre las features (R-12 / D-21).
    ev.assert_sin_features_post(X_COLS)
    assert "dias_vs_promesa" not in X_COLS


def test_target_binario_y_desbalanceado(datos):
    tr, _ = datos
    assert set(np.unique(tr[TARGET])) <= {0, 1}
    assert 0.0 < tr[TARGET].mean() < 0.5  # clase positiva minoritaria


def test_pipeline_entrena_y_predice(datos):
    tr, va = datos
    modelo = construir_modelos(tr[TARGET].values)["logistic_regression"]
    modelo.fit(tr[X_COLS], tr[TARGET].values)
    proba = proba_positiva(modelo, va[X_COLS])
    assert proba.shape == (len(va),)
    assert np.all((proba >= 0) & (proba <= 1))


def test_serializacion_roundtrip(tmp_path, datos):
    tr, va = datos
    modelo = construir_modelos(tr[TARGET].values)["logistic_regression"]
    modelo.fit(tr[X_COLS], tr[TARGET].values)
    proba_antes = proba_positiva(modelo, va[X_COLS])

    ruta = tmp_path / "modelo.joblib"
    joblib.dump(modelo, ruta)
    proba_despues = proba_positiva(joblib.load(ruta), va[X_COLS])
    assert np.allclose(proba_antes, proba_despues)


def test_modelo_supera_baseline(datos):
    tr, va = datos
    base = bl.BaselineClaseMayoritaria().fit(tr[X_COLS], tr[TARGET].values)
    ap_base = average_precision_score(va[TARGET].values, proba_positiva(base, va[X_COLS]))

    modelo = construir_modelos(tr[TARGET].values)["logistic_regression"]
    modelo.fit(tr[X_COLS], tr[TARGET].values)
    ap_modelo = average_precision_score(va[TARGET].values, proba_positiva(modelo, va[X_COLS]))

    assert ap_modelo > ap_base
