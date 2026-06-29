"""ETL y feature engineering de P1 — desempeño de entrega (multi-modelo).

Etapa 3 del Proyecto Final (Vertex Insights). Toma el CSV consolidado de Olist a
nivel ítem y produce:

  1. Una tabla analítica a NIVEL ORDEN (universo `delivered`) con un conjunto de
     features estrictamente [t0] (conocidas en el momento de la compra) y
     **varios targets** que habilitan distintas familias de modelos sin rehacer
     el feature engineering (disciplina anti-leakage D-21 / R-12):
       - `entrega_tarde`     — clasificación binaria (llegó tarde sí/no).
       - `clase_entrega`     — clasificación multiclase (muy_temprano / a_tiempo / tarde).
       - `dias_vs_promesa`   — regresión (días de holgura vs la promesa; >0 = tarde).
       - `dias_entrega_real` — regresión (días totales compra → entrega).
     Todos los targets son [POST] (solo etiquetan); el **mismo set de features**
     [t0] alimenta a clasificadores y regresores: solo cambia la `y`.
  2. Un pipeline de preprocesamiento de scikit-learn (ColumnTransformer dentro de
     un Pipeline), ajustado SOLO sobre el split de entrenamiento, serializado con
     joblib para que la Etapa 4 lo consuma sin recalcular parámetros.

Decisiones de diseño relevantes (ver docs/decisiones_fe.md):
  - Universo = `delivered` (D-20). Las no entregadas se excluyen del núcleo.
  - Granularidad = orden. El "vendedor/producto principal" es el del primer ítem
    (order_item_id == 1); los importes/peso/volumen se agregan sobre todos los ítems.
  - Tasa histórica de entrega tardía del vendedor: expanding y point-in-time
    (solo órdenes ANTERIORES del vendedor), con mínimo de 5 órdenes previas y
    respaldo a la tasa global del TRAIN + flag `sin_historial_vendedor`.
  - Split temporal por fecha de compra (sin aleatoriedad), 70/15/15.
  - Alcance multi-modelo de los targets (re-ejecución de la Etapa 3): D-30.

Uso:
    python -m src.features.build_dataset \
        --input  /Users/amaury/henry/Proyecto_Final/vertex_files/orders_consolidated.csv \
        --output /Users/amaury/henry/Proyecto_Final/vertex_files/orders_features.csv
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

# --------------------------------------------------------------------------- #
# Rutas por defecto
# --------------------------------------------------------------------------- #
DEFAULT_INPUT = "/Users/amaury/henry/Proyecto_Final/vertex_files/orders_consolidated.csv"
DEFAULT_OUTPUT = "/Users/amaury/henry/Proyecto_Final/vertex_files/orders_features.csv"
DEFAULT_PIPELINE = (
    Path(__file__).resolve().parents[2] / "artifacts" / "pipeline_p1.joblib"
)

# Parámetros de la tasa del vendedor
MIN_ORDENES_VENDEDOR = 5

# Umbral (días antes de la promesa) para separar "a_tiempo" de "muy_temprano"
# en el target multiclase `clase_entrega` (D-30).
UMBRAL_MUY_TEMPRANO_DIAS = 3

# Columnas [POST]: conocidas solo DESPUÉS de la compra. Prohibidas como feature;
# solo sirven para construir el target. (Disciplina anti-leakage D-21 / R-12.)
COLS_POST = [
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
]

DATE_COLS = [
    "order_purchase_timestamp",
    "order_approved_at",
    "order_delivered_customer_date",
    "order_estimated_delivery_date",
]

# Features finales que entran al modelo
NUMERIC_FEATURES = [
    "dias_prometidos",
    "dist_haversine_km",
    "ratio_flete",
    "precio_total",
    "flete_total",
    "n_items",
    "peso_total_g",
    "volumen_total_cm3",
    "tasa_vendedor",
    "mes_compra",
    "dia_semana_compra",
]
CATEGORICAL_FEATURES = [
    "customer_state",
    "seller_state",
    "categoria_principal",
    "mismo_estado",
    "sin_historial_vendedor",
]

# Targets [POST]: solo etiquetan, NUNCA son features. El mismo X (NUMERIC +
# CATEGORICAL) alimenta a todas las familias; solo cambia la columna `y` (D-30).
CLASSIFICATION_TARGET = "entrega_tarde"      # binaria 0/1
MULTICLASS_TARGET = "clase_entrega"          # muy_temprano / a_tiempo / tarde
REGRESSION_TARGETS = ["dias_vs_promesa", "dias_entrega_real"]
TARGETS = [CLASSIFICATION_TARGET, MULTICLASS_TARGET] + REGRESSION_TARGETS


# --------------------------------------------------------------------------- #
# 1. Carga y limpieza inicial
# --------------------------------------------------------------------------- #
def load_raw(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    for col in DATE_COLS:
        df[col] = pd.to_datetime(df[col], errors="coerce")
    # Universo P1: solo órdenes entregadas (D-20).
    df = df[df["order_status"] == "delivered"].copy()
    # No se puede etiquetar sin fecha de entrega real.
    df = df[df["order_delivered_customer_date"].notna()].copy()
    return df


def haversine_km(lat1, lon1, lat2, lon2):
    """Distancia haversine en km entre dos puntos (arrays o escalares)."""
    r = 6371.0
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    return 2 * r * np.arcsin(np.sqrt(a))


# --------------------------------------------------------------------------- #
# 2. Consolidación a nivel orden
# --------------------------------------------------------------------------- #
def build_order_table(df: pd.DataFrame) -> pd.DataFrame:
    """Colapsa la tabla item-level a una fila por orden."""
    df = df.sort_values(["order_id", "order_item_id"])

    # Volumen por ítem (cm3) para luego agregar por orden.
    df["item_volume_cm3"] = (
        df["product_length_cm"] * df["product_height_cm"] * df["product_width_cm"]
    )

    # --- Atributos del "ítem principal" (primer ítem de la orden) --------- #
    principal = df.groupby("order_id").first().reset_index()
    principal = principal[
        [
            "order_id",
            "customer_id",
            "customer_unique_id",
            "seller_id",
            "order_purchase_timestamp",
            "order_estimated_delivery_date",
            "order_delivered_customer_date",
            "product_category_name_english",
            "customer_state",
            "customer_lat",
            "customer_lng",
            "seller_state",
            "seller_lat",
            "seller_lng",
            "product_weight_g",
            "item_volume_cm3",
        ]
    ].rename(
        columns={
            "product_category_name_english": "categoria_principal",
            "product_weight_g": "peso_principal_g",
            "item_volume_cm3": "volumen_principal_cm3",
        }
    )

    # --- Agregados sobre todos los ítems de la orden --------------------- #
    agg = (
        df.groupby("order_id")
        .agg(
            n_items=("order_item_id", "count"),
            precio_total=("price", "sum"),
            flete_total=("freight_value", "sum"),
            peso_total_g=("product_weight_g", "sum"),
            volumen_total_cm3=("item_volume_cm3", "sum"),
        )
        .reset_index()
    )

    orders = principal.merge(agg, on="order_id", how="left")
    return orders


# --------------------------------------------------------------------------- #
# 3. Target y features [t0] directas
# --------------------------------------------------------------------------- #
def add_target_and_direct_features(orders: pd.DataFrame) -> pd.DataFrame:
    # --- Targets [POST para etiquetar, NO son features] (D-30) ----------- #
    # Clasificación binaria: llegó después de la fecha prometida.
    orders["entrega_tarde"] = (
        orders["order_delivered_customer_date"]
        > orders["order_estimated_delivery_date"]
    ).astype(int)
    # Regresión 1: días de holgura frente a la promesa (>0 = tarde, <0 = adelantado).
    orders["dias_vs_promesa"] = (
        orders["order_delivered_customer_date"]
        - orders["order_estimated_delivery_date"]
    ).dt.total_seconds() / 86400.0
    # Regresión 2: días totales de entrega (compra → entrega real).
    orders["dias_entrega_real"] = (
        orders["order_delivered_customer_date"]
        - orders["order_purchase_timestamp"]
    ).dt.total_seconds() / 86400.0
    # Clasificación multiclase: separa el adelanto grande del ajustado.
    orders["clase_entrega"] = np.select(
        [
            orders["dias_vs_promesa"] > 0,
            orders["dias_vs_promesa"] < -UMBRAL_MUY_TEMPRANO_DIAS,
        ],
        ["tarde", "muy_temprano"],
        default="a_tiempo",
    )

    # --- Features [t0] --------------------------------------------------- #
    orders["dias_prometidos"] = (
        orders["order_estimated_delivery_date"]
        - orders["order_purchase_timestamp"]
    ).dt.total_seconds() / 86400.0

    orders["ratio_flete"] = orders["flete_total"] / orders["precio_total"].replace(
        0, np.nan
    )

    orders["mes_compra"] = orders["order_purchase_timestamp"].dt.month
    orders["dia_semana_compra"] = orders["order_purchase_timestamp"].dt.dayofweek

    orders["mismo_estado"] = (
        orders["customer_state"] == orders["seller_state"]
    ).astype(int)

    orders["dist_haversine_km"] = haversine_km(
        orders["customer_lat"],
        orders["customer_lng"],
        orders["seller_lat"],
        orders["seller_lng"],
    )

    # Peso/volumen de la orden: priorizar el agregado; respaldo al principal.
    orders["peso_total_g"] = orders["peso_total_g"].fillna(orders["peso_principal_g"])
    orders["volumen_total_cm3"] = orders["volumen_total_cm3"].fillna(
        orders["volumen_principal_cm3"]
    )
    return orders


# --------------------------------------------------------------------------- #
# 4. Tasa histórica del vendedor SIN FUGA (point-in-time, expanding)
# --------------------------------------------------------------------------- #
def add_seller_rate(orders: pd.DataFrame, global_rate: float) -> pd.DataFrame:
    """Tasa de tardanza del vendedor usando SOLO sus órdenes anteriores.

    Para la orden i del vendedor s: media de `entrega_tarde` sobre las órdenes de s
    estrictamente ANTERIORES (por fecha de compra). Si hay < MIN_ORDENES_VENDEDOR
    órdenes previas, se respalda con `global_rate` (tasa del TRAIN) y se marca
    `sin_historial_vendedor = 1`.
    """
    orders = orders.sort_values(
        ["order_purchase_timestamp", "order_id"]
    ).reset_index(drop=True)

    g = orders.groupby("seller_id")["entrega_tarde"]
    # Suma y conteo acumulados EXCLUYENDO la fila actual (shift de 1).
    cum_sum = g.cumsum() - orders["entrega_tarde"]
    cum_cnt = g.cumcount()  # nº de órdenes anteriores del vendedor

    with np.errstate(invalid="ignore", divide="ignore"):
        tasa_hist = cum_sum / cum_cnt

    suficiente = cum_cnt >= MIN_ORDENES_VENDEDOR
    orders["sin_historial_vendedor"] = (~suficiente).astype(int)
    orders["tasa_vendedor"] = np.where(suficiente, tasa_hist, global_rate)
    return orders


# --------------------------------------------------------------------------- #
# 5. Split temporal sin leakage
# --------------------------------------------------------------------------- #
def temporal_split(orders: pd.DataFrame, frac_train=0.70, frac_val=0.15):
    """Asigna split por fecha de compra: pasado=train, futuro=val/test."""
    orders = orders.sort_values(
        ["order_purchase_timestamp", "order_id"]
    ).reset_index(drop=True)
    n = len(orders)
    i_train = int(n * frac_train)
    i_val = int(n * (frac_train + frac_val))
    split = np.array(["train"] * n, dtype=object)
    split[i_train:i_val] = "val"
    split[i_val:] = "test"
    orders["split"] = split
    return orders


# --------------------------------------------------------------------------- #
# 6. Imputación con sentido de negocio (geo y dimensiones)
# --------------------------------------------------------------------------- #
def impute_business(orders: pd.DataFrame) -> pd.DataFrame:
    """Imputaciones que no se aprenden de la distribución global del modelo:
    distancia faltante por geo ausente, peso/volumen faltantes por la mediana de
    su categoría. (Las imputaciones estadísticas numéricas/categóricas finales las
    hace el ColumnTransformer, ajustado solo en train.)
    """
    # Dimensiones faltantes -> mediana de la categoría (sobre el dataset, ya que
    # es un atributo estable del producto; no es una estadística del target).
    for col in ["peso_total_g", "volumen_total_cm3"]:
        med_cat = orders.groupby("categoria_principal")[col].transform("median")
        orders[col] = orders[col].fillna(med_cat)
        orders[col] = orders[col].fillna(orders[col].median())

    # ratio_flete faltante (precio 0) -> mediana.
    orders["ratio_flete"] = orders["ratio_flete"].fillna(orders["ratio_flete"].median())

    # Distancia faltante por geo ausente: la deja el ColumnTransformer (mediana en
    # train). Se conserva el NaN aquí para que la imputación viva en el pipeline.
    return orders


# --------------------------------------------------------------------------- #
# 7. Pipeline de preprocesamiento (ajustado solo en train)
# --------------------------------------------------------------------------- #
def build_preprocessor() -> ColumnTransformer:
    numeric = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )
    categorical = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("encoder", OneHotEncoder(handle_unknown="ignore", min_frequency=0.01)),
        ]
    )
    return ColumnTransformer(
        [
            ("num", numeric, NUMERIC_FEATURES),
            ("cat", categorical, CATEGORICAL_FEATURES),
        ]
    )


# --------------------------------------------------------------------------- #
# Orquestación
# --------------------------------------------------------------------------- #
def run(input_path: str, output_path: str, pipeline_path: Path) -> pd.DataFrame:
    print(f"[1/7] Cargando y filtrando delivered: {input_path}")
    df = load_raw(input_path)
    print(f"      filas item-level (delivered, etiquetables): {len(df):,}")

    print("[2/7] Consolidando a nivel orden ...")
    orders = build_order_table(df)
    print(f"      órdenes: {len(orders):,}")

    print("[3/7] Targets y features [t0] directas ...")
    orders = add_target_and_direct_features(orders)
    base_rate = orders["entrega_tarde"].mean()
    print(f"      tasa base entrega_tarde: {base_rate*100:.2f}%")
    dist_clase = orders["clase_entrega"].value_counts(normalize=True).mul(100).round(2)
    print(f"      clase_entrega (%): {dist_clase.to_dict()}")
    print(
        "      dias_vs_promesa  -> "
        f"media {orders['dias_vs_promesa'].mean():.1f}, mediana {orders['dias_vs_promesa'].median():.1f}"
    )
    print(
        "      dias_entrega_real-> "
        f"media {orders['dias_entrega_real'].mean():.1f}, mediana {orders['dias_entrega_real'].median():.1f}"
    )

    print("[4/7] Split temporal por fecha de compra ...")
    orders = temporal_split(orders)
    global_rate_train = orders.loc[orders["split"] == "train", "entrega_tarde"].mean()
    print(f"      tasa global (TRAIN) para respaldo del vendedor: {global_rate_train*100:.2f}%")

    print("[5/7] Tasa histórica del vendedor sin fuga (point-in-time) ...")
    orders = add_seller_rate(orders, global_rate=global_rate_train)
    sin_hist = orders["sin_historial_vendedor"].mean()
    print(f"      órdenes sin historial suficiente del vendedor: {sin_hist*100:.2f}%")

    print("[6/7] Imputación de negocio (dimensiones, ratio) ...")
    orders = impute_business(orders)

    # --- Test anti-fuga obligatorio de la tasa del vendedor -------------- #
    assert_no_leakage_seller_rate(orders)

    print("[7/7] Ajustando ColumnTransformer SOLO en train y serializando ...")
    preprocessor = build_preprocessor()
    train = orders[orders["split"] == "train"]
    preprocessor.fit(train[NUMERIC_FEATURES + CATEGORICAL_FEATURES])

    pipeline_path.parent.mkdir(parents=True, exist_ok=True)
    import joblib

    joblib.dump(
        {
            "preprocessor": preprocessor,
            "numeric_features": NUMERIC_FEATURES,
            "categorical_features": CATEGORICAL_FEATURES,
            "classification_target": CLASSIFICATION_TARGET,
            "multiclass_target": MULTICLASS_TARGET,
            "regression_targets": REGRESSION_TARGETS,
            "min_ordenes_vendedor": MIN_ORDENES_VENDEDOR,
            "global_rate_train": float(global_rate_train),
        },
        pipeline_path,
    )
    print(f"      pipeline serializado en: {pipeline_path}")

    # --- Tabla analítica de salida --------------------------------------- #
    keep = (
        ["order_id", "order_purchase_timestamp", "split"]
        + TARGETS
        + NUMERIC_FEATURES
        + CATEGORICAL_FEATURES
    )
    out = orders[keep].copy()
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(output_path, index=False)
    print(f"      tabla analítica guardada en: {output_path}  ({out.shape[0]:,} x {out.shape[1]})")
    return out


def assert_no_leakage_seller_rate(orders: pd.DataFrame) -> None:
    """Verifica que la tasa del vendedor de una orden NO depende de sí misma.

    Recalcula, para una muestra de vendedores con historial, la tasa usando solo
    órdenes estrictamente anteriores y compara con la columna producida.
    """
    df = orders.sort_values(["order_purchase_timestamp", "order_id"]).reset_index(drop=True)
    con_hist = df[df["sin_historial_vendedor"] == 0]
    if con_hist.empty:
        return
    sample = con_hist.sample(min(200, len(con_hist)), random_state=42)
    ok = True
    for _, row in sample.iterrows():
        s = row["seller_id"]
        t = row["order_purchase_timestamp"]
        prev = df[(df["seller_id"] == s) & (df["order_purchase_timestamp"] < t)]
        if len(prev) >= MIN_ORDENES_VENDEDOR:
            esperado = prev["entrega_tarde"].mean()
            if not np.isclose(esperado, row["tasa_vendedor"], atol=1e-6):
                ok = False
                break
    assert ok, "FUGA DETECTADA: la tasa del vendedor depende de la orden actual/futuras."
    print("      ✔ test anti-fuga de la tasa del vendedor: OK")


def parse_args():
    p = argparse.ArgumentParser(description="ETL + feature engineering P1 (entrega_tarde)")
    p.add_argument("--input", default=DEFAULT_INPUT)
    p.add_argument("--output", default=DEFAULT_OUTPUT)
    p.add_argument("--pipeline", default=str(DEFAULT_PIPELINE))
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run(args.input, args.output, Path(args.pipeline))
