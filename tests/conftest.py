"""Configuración de pytest: hace importable el paquete `src` desde la raíz.

Incluye además los fixtures SINTÉTICOS de serving (D-39): un artefacto con el
mismo esquema de dict que producto_promesa_riesgo.joblib y lookups mínimos,
para que los tests de la API/feature_builder corran sin datos ni artefactos
reales (los .joblib y .csv no se versionan — el CI depende de esto).
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import joblib  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import pytest  # noqa: E402
from sklearn.compose import ColumnTransformer  # noqa: E402
from sklearn.isotonic import IsotonicRegression  # noqa: E402
from sklearn.linear_model import LinearRegression, LogisticRegression  # noqa: E402
from sklearn.pipeline import Pipeline  # noqa: E402
from sklearn.preprocessing import OneHotEncoder  # noqa: E402

# Mismas listas de features que el artefacto real (contrato del producto D-38).
NUMERICAS_ESCUDO = [
    "dias_prometidos", "dist_haversine_km", "ratio_flete", "precio_total",
    "flete_total", "n_items", "peso_total_g", "volumen_total_cm3",
    "tasa_vendedor", "mes_compra", "dia_semana_compra",
]
CATEGORICAS_ESCUDO = [
    "customer_state", "seller_state", "categoria_principal",
    "mismo_estado", "sin_historial_vendedor",
]
FEATURES_MOTOR = [c for c in NUMERICAS_ESCUDO if c != "dias_prometidos"] + CATEGORICAS_ESCUDO


def _datos_sinteticos(n: int = 60) -> pd.DataFrame:
    rng = np.random.default_rng(7)
    df = pd.DataFrame({
        "dias_prometidos": rng.uniform(5, 30, n),
        "dist_haversine_km": rng.uniform(10, 2000, n),
        "ratio_flete": rng.uniform(0.05, 0.6, n),
        "precio_total": rng.uniform(20, 500, n),
        "flete_total": rng.uniform(5, 60, n),
        "n_items": rng.integers(1, 4, n),
        "peso_total_g": rng.uniform(100, 5000, n),
        "volumen_total_cm3": rng.uniform(500, 30000, n),
        "tasa_vendedor": rng.uniform(0.0, 0.3, n),
        "mes_compra": rng.integers(1, 13, n),
        "dia_semana_compra": rng.integers(0, 7, n),
        "customer_state": rng.choice(["SP", "BA", "RJ"], n),
        "seller_state": rng.choice(["SP", "MG"], n),
        "categoria_principal": rng.choice(["cat_a", "cat_b"], n),
        "mismo_estado": rng.integers(0, 2, n),
        "sin_historial_vendedor": rng.integers(0, 2, n),
    })
    df["dias_entrega_real"] = 5 + 0.01 * df["dist_haversine_km"] + rng.normal(0, 2, n)
    df["tarde"] = (df["dias_entrega_real"] > df["dias_prometidos"]).astype(int)
    return df


def _pipeline(numericas: list[str], categoricas: list[str], estimador) -> Pipeline:
    pre = ColumnTransformer([
        ("num", "passthrough", numericas),
        ("cat", OneHotEncoder(handle_unknown="ignore"), categoricas),
    ])
    return Pipeline([("pre", pre), ("clf", estimador)])


@pytest.fixture(scope="session")
def bundle_sintetico() -> dict:
    """Dict con el MISMO esquema que producto_promesa_riesgo.joblib (D-38)."""
    df = _datos_sinteticos()

    motor = _pipeline([c for c in NUMERICAS_ESCUDO if c != "dias_prometidos"],
                      CATEGORICAS_ESCUDO, LinearRegression())
    motor.fit(df[FEATURES_MOTOR], df["dias_entrega_real"])

    escudo_reg = _pipeline(NUMERICAS_ESCUDO, CATEGORICAS_ESCUDO, LinearRegression())
    x_escudo = df[NUMERICAS_ESCUDO + CATEGORICAS_ESCUDO]
    escudo_reg.fit(x_escudo, df["dias_entrega_real"] - df["dias_prometidos"])
    calibrador = IsotonicRegression(out_of_bounds="clip")
    calibrador.fit(escudo_reg.predict(x_escudo), df["tarde"])

    escudo_v2 = _pipeline(NUMERICAS_ESCUDO, CATEGORICAS_ESCUDO, LogisticRegression(max_iter=500))
    escudo_v2.fit(x_escudo, df["tarde"])

    return {
        "tarea": "producto_promesa_riesgo (sintetico de tests)",
        "motor": motor,
        "motor_features": FEATURES_MOTOR,
        "motor_feature_set": "M0_base_sin_rolling",
        "margenes_val": {"P80": 2.0, "P90": 5.8, "P95": 9.7},
        "politica_recomendada": "P90",
        "escudo": {
            "modelo_regresion": escudo_reg,
            "calibrador_isotonic": calibrador,
            "numeric_features": NUMERICAS_ESCUDO,
            "categorical_features": CATEGORICAS_ESCUDO,
        },
        "escudo_umbral": 0.3,
        "escudo_v2_modelo": escudo_v2,
        "escudo_v2_umbral": 0.5,
        "generado": "sintetico-tests",
    }


@pytest.fixture(scope="session")
def lookups_sinteticos(tmp_path_factory) -> Path:
    """Directorio con los 3 parquet + manifest que espera FeatureBuilder."""
    carpeta = tmp_path_factory.mktemp("serving")
    pd.DataFrame({
        "categoria_principal": ["cat_a", "cat_b"],
        "peso_unitario_g": [500.0, 1200.0],
        "volumen_unitario_cm3": [4000.0, 9000.0],
        "n_ordenes": [30, 30],
    }).to_parquet(carpeta / "catalogo_categorias.parquet", index=False)
    pd.DataFrame({
        "customer_state": ["SP", "BA"],
        "seller_state": ["SP", "SP"],
        "dist_haversine_km": [100.0, 1200.0],
        "n_ordenes": [40, 20],
    }).to_parquet(carpeta / "geo_estados.parquet", index=False)
    pd.DataFrame({
        "seller_state": ["SP", "MG"],
        "tasa_vendedor": [0.08, 0.12],
        "n_ordenes": [50, 10],
    }).to_parquet(carpeta / "stats_vendedor_estado.parquet", index=False)
    manifest = {
        "generado": "sintetico-tests",
        "nivel": "agregado (sintetico)",
        "fuente": "tests",
        "fecha_corte_train": "2018-04-15 20:12:35",
        "n_ordenes_train": 60,
        "fallbacks_globales": {
            "peso_unitario_g": 700.0,
            "volumen_unitario_cm3": 6859.0,
            "dist_haversine_km": 450.0,
            "tasa_vendedor": 0.056,
            "seller_state_modal": "SP",
            "categoria_modal": "cat_a",
        },
        "filas_por_lookup": {"catalogo_categorias": 2, "geo_estados": 2,
                             "stats_vendedor_estado": 2},
    }
    with open(carpeta / "manifest.json", "w", encoding="utf-8") as fh:
        json.dump(manifest, fh)
    return carpeta


@pytest.fixture(scope="session")
def artefacto_sintetico(tmp_path_factory, bundle_sintetico) -> Path:
    """El bundle sintetico serializado como joblib (para el lifespan de la API)."""
    ruta = tmp_path_factory.mktemp("artifacts") / "producto_promesa_riesgo.joblib"
    joblib.dump(bundle_sintetico, ruta)
    return ruta
