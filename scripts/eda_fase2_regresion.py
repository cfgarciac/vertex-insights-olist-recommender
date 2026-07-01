"""EDA reproducible de Fase 2 para regresion de dias_entrega_real.

Lee el dataset experimental generado por Chat B y crea un reporte Markdown con
tablas, metricas y figuras para decidir que hipotesis de feature engineering
deben avanzar a Chat D.

Uso:
    python scripts/eda_fase2_regresion.py
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


# --------------------------------------------------------------------------- #
# 0. Rutas y constantes
# --------------------------------------------------------------------------- #
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = PROJECT_ROOT / "data" / "processed" / "orders_fase2_regresion.csv"
DEFAULT_REPORT = PROJECT_ROOT / "reports" / "fase2_eda_regresion.md"
DEFAULT_FIGURES_DIR = PROJECT_ROOT / "reports" / "figures_fase2_eda"

TARGET = "dias_entrega_real"
SPLIT_ORDER = ["train", "val", "test"]

PROHIBITED_AS_FEATURES = {
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
}

NUMERIC_FEATURES = [
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

CATEGORICAL_ANALYSIS_COLUMNS = [
    "customer_state",
    "seller_state",
    "ruta_estado",
    "categoria_principal",
    "seller_id",
]

FEATURE_INVENTORY = [
    {
        "bloque": "Geografia destino",
        "feature": "customer_state",
        "rol": "feature base M0",
        "influencia_esperada": "El DVA/EDA previo mostro dolor regional fuerte; estados norte/nordeste tienden a entregas mas largas.",
        "evaluar": "Mediana, p90, estabilidad por split y si rolling 30d por destino supera al estado crudo.",
    },
    {
        "bloque": "Geografia origen",
        "feature": "seller_state",
        "rol": "feature base M0",
        "influencia_esperada": "El origen logistico puede afectar rutas, red de despacho y distancia efectiva.",
        "evaluar": "Senal incremental frente a customer_state y estabilidad de combinaciones origen-destino.",
    },
    {
        "bloque": "Ruta",
        "feature": "ruta_estado",
        "rol": "soporte para analisis/rolling",
        "influencia_esperada": "Resume origen + destino; deberia capturar dificultad logistica mejor que un solo estado.",
        "evaluar": "Volumen por ruta, rutas raras, cobertura en val/test y fallback por customer_state.",
    },
    {
        "bloque": "Cercania",
        "feature": "mismo_estado",
        "rol": "feature base M0",
        "influencia_esperada": "Ordenes dentro del mismo estado deberian tender a menor duracion.",
        "evaluar": "Diferencia real contra no mismo estado y aporte frente a distancia/ruta.",
    },
    {
        "bloque": "Distancia",
        "feature": "dist_haversine_km",
        "rol": "feature base M0",
        "influencia_esperada": "Aproxima separacion cliente-vendedor; en EDA actual muestra relacion monotona fuerte.",
        "evaluar": "No linealidad, bins de distancia, nulos y comparacion con ruta/estado.",
    },
    {
        "bloque": "Categoria",
        "feature": "categoria_principal",
        "rol": "feature base M0",
        "influencia_esperada": "Algunas categorias tienen productos mas grandes, sellers distintos o logistica mas lenta.",
        "evaluar": "Volumen por categoria, categorias raras, rolling por categoria e interaccion con ruta.",
    },
    {
        "bloque": "Economia",
        "feature": "precio_total",
        "rol": "feature base M0",
        "influencia_esperada": "Puede actuar como proxy de tipo de producto o complejidad, no como causa directa.",
        "evaluar": "Relacion no lineal, outliers y si solo replica categoria.",
    },
    {
        "bloque": "Envio",
        "feature": "flete_total",
        "rol": "feature base M0",
        "influencia_esperada": "Puede resumir distancia, peso, volumen y politica comercial de envio.",
        "evaluar": "Separar efecto de distancia/peso y comparar contra ratio_flete.",
    },
    {
        "bloque": "Envio",
        "feature": "ratio_flete",
        "rol": "feature base M0",
        "influencia_esperada": "Flete alto relativo al precio puede indicar dificultad logistica.",
        "evaluar": "Outliers, transformacion log/binning y estabilidad por split.",
    },
    {
        "bloque": "Complejidad orden",
        "feature": "n_items",
        "rol": "feature base M0",
        "influencia_esperada": "Mas items podria implicar preparacion o consolidacion mas compleja.",
        "evaluar": "Umbrales 1 vs multiples y si la relacion es debil/no lineal.",
    },
    {
        "bloque": "Fisica",
        "feature": "peso_total_g",
        "rol": "feature base M0",
        "influencia_esperada": "Paquetes pesados pueden limitar opciones logisticas.",
        "evaluar": "log_peso, bins, outliers e interaccion con distancia.",
    },
    {
        "bloque": "Fisica",
        "feature": "volumen_total_cm3",
        "rol": "feature base M0",
        "influencia_esperada": "Paquetes voluminosos pueden tener tratamiento logistico distinto.",
        "evaluar": "log_volumen, bins, outliers e interaccion peso-volumen.",
    },
    {
        "bloque": "Temporal",
        "feature": "mes_compra",
        "rol": "feature base M0",
        "influencia_esperada": "El DVA/EDA detecto cambio de regimen y estacionalidad.",
        "evaluar": "Distinguir estacionalidad real de drift temporal; revisar por split.",
    },
    {
        "bloque": "Temporal",
        "feature": "dia_semana_compra",
        "rol": "feature base M0",
        "influencia_esperada": "Puede afectar aprobacion/despacho indirectamente.",
        "evaluar": "Confirmar si aporta o queda como senal secundaria.",
    },
    {
        "bloque": "Seller historico",
        "feature": "tasa_vendedor",
        "rol": "feature base M0 historica",
        "influencia_esperada": "En Fase 1 fue util y auditada point-in-time para tardanza.",
        "evaluar": "Si tasa de tardanza predice duracion real o si conviene duracion rolling.",
    },
    {
        "bloque": "Seller historico",
        "feature": "sin_historial_vendedor",
        "rol": "feature base M0 historica",
        "influencia_esperada": "Marca incertidumbre para sellers nuevos o sin pasado suficiente.",
        "evaluar": "Cobertura por split y diferencia de duracion/error con vs sin historial.",
    },
    {
        "bloque": "Seller soporte",
        "feature": "seller_id",
        "rol": "soporte para analisis/rolling",
        "influencia_esperada": "Puede contener senal, pero crudo tiende a memorizar y generaliza mal.",
        "evaluar": "No usar crudo; evaluar agregados historicos con conteo y fallback.",
    },
]

TRANSFORMATION_CANDIDATES = [
    ("log_dist_haversine_km", "dist_haversine_km", "log1p"),
    ("log_precio_total", "precio_total", "log1p"),
    ("log_flete_total", "flete_total", "log1p"),
    ("log_ratio_flete", "ratio_flete", "log1p"),
    ("log_peso_total_g", "peso_total_g", "log1p"),
    ("log_volumen_total_cm3", "volumen_total_cm3", "log1p"),
]

MULTICOLLINEARITY_FEATURES = [
    "dist_haversine_km",
    "flete_total",
    "ratio_flete",
    "precio_total",
    "peso_total_g",
    "volumen_total_cm3",
    "mismo_estado",
    "n_items",
]


# --------------------------------------------------------------------------- #
# 1. Utilidades de formato
# --------------------------------------------------------------------------- #
def fmt_float(value: float, digits: int = 2) -> str:
    """Formatea numeros para tablas Markdown."""
    if pd.isna(value):
        return "NA"
    return f"{value:,.{digits}f}"


def fmt_int(value: float) -> str:
    """Formatea enteros con separador de miles."""
    if pd.isna(value):
        return "NA"
    return f"{int(round(value)):,}"


def to_markdown(df: pd.DataFrame, float_digits: int = 2) -> str:
    """Convierte un DataFrame a Markdown con formato compacto."""
    formatted = df.copy()
    for col in formatted.columns:
        if pd.api.types.is_float_dtype(formatted[col]):
            formatted[col] = formatted[col].map(lambda x: fmt_float(x, float_digits))
        elif pd.api.types.is_integer_dtype(formatted[col]):
            formatted[col] = formatted[col].map(fmt_int)
    formatted = formatted.astype(str)
    headers = list(formatted.columns)
    rows = formatted.values.tolist()

    def clean_cell(value: str) -> str:
        return value.replace("|", "\\|").replace("\n", " ")

    header_line = "| " + " | ".join(clean_cell(col) for col in headers) + " |"
    separator_line = "| " + " | ".join("---" for _ in headers) + " |"
    row_lines = [
        "| " + " | ".join(clean_cell(value) for value in row) + " |"
        for row in rows
    ]
    return "\n".join([header_line, separator_line] + row_lines)


def agg_target(df: pd.DataFrame, group_cols: str | list[str]) -> pd.DataFrame:
    """Resume duracion real por grupos."""
    grouped = (
        df.groupby(group_cols, dropna=False)[TARGET]
        .agg(
            ordenes="count",
            media="mean",
            mediana="median",
            p75=lambda x: x.quantile(0.75),
            p90=lambda x: x.quantile(0.90),
        )
        .reset_index()
    )
    grouped["share_pct"] = grouped["ordenes"] / len(df) * 100
    return grouped


def make_feature_inventory() -> pd.DataFrame:
    """Devuelve la tabla puente de features iniciales e hipotesis a evaluar."""
    return pd.DataFrame(FEATURE_INVENTORY)


def evaluate_group_median_baselines(df: pd.DataFrame) -> pd.DataFrame:
    """Evalua reglas simples basadas en medianas historicas de train.

    Estas reglas no sustituyen al modelado. Sirven para medir si una columna
    tiene senal predictiva basica en val/test sin usar informacion futura.
    """
    train = df[df["split"] == "train"].copy()
    eval_df = df[df["split"].isin(["val", "test"])].copy()
    global_median = train[TARGET].median()

    specs = [
        ("global_train", None, 0),
        ("customer_state", "customer_state", 20),
        ("seller_state", "seller_state", 20),
        ("categoria_principal", "categoria_principal", 20),
        ("ruta_estado", "ruta_estado", 20),
        ("seller_id", "seller_id", 5),
    ]
    rows = []
    for split, split_df in eval_df.groupby("split", sort=False):
        y_true = split_df[TARGET]
        rows.append(
            {
                "split": split,
                "regla": "global_train",
                "min_train_n": 0,
                "grupos_train": 1,
                "grupos_elegibles": 1,
                "cobertura_seen_pct": 100.0,
                "cobertura_elegible_pct": 100.0,
                "mae_fallback_global": (y_true - global_median).abs().mean(),
            }
        )

        for name, col, min_count in specs[1:]:
            counts = train.groupby(col)[TARGET].size()
            medians = train.groupby(col)[TARGET].median()
            eligible_groups = counts[counts >= min_count].index

            seen_mask = split_df[col].isin(medians.index)
            eligible_mask = split_df[col].isin(eligible_groups)
            eligible_medians = medians.loc[eligible_groups]

            preds = split_df[col].map(eligible_medians).fillna(global_median)
            rows.append(
                {
                    "split": split,
                    "regla": name,
                    "min_train_n": min_count,
                    "grupos_train": counts.shape[0],
                    "grupos_elegibles": len(eligible_groups),
                    "cobertura_seen_pct": seen_mask.mean() * 100,
                    "cobertura_elegible_pct": eligible_mask.mean() * 100,
                    "mae_fallback_global": (y_true - preds).abs().mean(),
                }
            )
    return pd.DataFrame(rows).sort_values(["split", "mae_fallback_global"])


def evaluate_categorical_stability(df: pd.DataFrame) -> pd.DataFrame:
    """Compara medias por categoria entre train y val/test con umbrales minimos."""
    train = df[df["split"] == "train"].copy()
    rows = []
    thresholds = {
        "customer_state": 100,
        "seller_state": 100,
        "ruta_estado": 50,
        "categoria_principal": 100,
        "seller_id": 20,
    }

    train_stats = {}
    for col in CATEGORICAL_ANALYSIS_COLUMNS:
        stats = train.groupby(col)[TARGET].agg(["count", "mean", "median"])
        train_stats[col] = stats[stats["count"] >= thresholds[col]]

    for col in CATEGORICAL_ANALYSIS_COLUMNS:
        for split in ["val", "test"]:
            current = df[df["split"] == split].groupby(col)[TARGET].agg(
                ["count", "mean", "median"]
            )
            current = current[current["count"] >= thresholds[col]]
            joined = train_stats[col].join(
                current, how="inner", lsuffix="_train", rsuffix=f"_{split}"
            )
            if len(joined) >= 2:
                corr_media = joined["mean_train"].corr(joined[f"mean_{split}"])
                shift_mediana = (
                    joined[f"median_{split}"] - joined["median_train"]
                ).abs().median()
            else:
                corr_media = np.nan
                shift_mediana = np.nan
            rows.append(
                {
                    "feature": col,
                    "split_comparado": split,
                    "min_ordenes_por_split": thresholds[col],
                    "grupos_comparables": len(joined),
                    "corr_media_train_vs_split": corr_media,
                    "shift_mediana_abs_dias": shift_mediana,
                }
            )
    return pd.DataFrame(rows)


def evaluate_numeric_transformations(df: pd.DataFrame) -> pd.DataFrame:
    """Compara correlacion de variables crudas vs transformaciones simples."""
    rows = []
    for transformed_name, source_col, transform in TRANSFORMATION_CANDIDATES:
        raw = df[source_col].replace([np.inf, -np.inf], np.nan)
        if transform == "log1p":
            transformed = np.log1p(raw.clip(lower=0))
        else:
            transformed = raw
        rows.append(
            {
                "feature_original": source_col,
                "feature_candidata": transformed_name,
                "transformacion": transform,
                "spearman_original": raw.corr(df[TARGET], method="spearman"),
                "spearman_transformada": transformed.corr(
                    df[TARGET], method="spearman"
                ),
                "missing_pct": raw.isna().mean() * 100,
            }
        )
    return pd.DataFrame(rows)


def evaluate_multicollinearity(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Revisa redundancia exploratoria entre features numericas.

    En Chat C esto es una alerta de diseno. La decision formal de eliminar o
    conservar variables queda para Chat E, cuando se mida impacto en MAE.
    """
    available = [col for col in MULTICOLLINEARITY_FEATURES if col in df.columns]
    corr_matrix = df[available].corr(method="spearman").round(3)

    pairs = []
    for i, left in enumerate(available):
        for right in available[i + 1 :]:
            value = corr_matrix.loc[left, right]
            pairs.append(
                {
                    "feature_a": left,
                    "feature_b": right,
                    "spearman_abs": abs(value),
                    "spearman": value,
                    "lectura": (
                        "alta redundancia exploratoria"
                        if abs(value) >= 0.70
                        else "redundancia moderada"
                        if abs(value) >= 0.40
                        else "baja redundancia"
                    ),
                }
            )

    pair_table = (
        pd.DataFrame(pairs)
        .sort_values(["spearman_abs", "feature_a", "feature_b"], ascending=[False, True, True])
        .reset_index(drop=True)
    )
    return corr_matrix.reset_index().rename(columns={"index": "feature"}), pair_table


def evaluate_binary_segments(df: pd.DataFrame) -> pd.DataFrame:
    """Resume diferencias para features binarias clave."""
    rows = []
    for col in ["mismo_estado", "sin_historial_vendedor"]:
        for value, segment in df.groupby(col):
            rows.append(
                {
                    "feature": col,
                    "valor": int(value),
                    "ordenes": len(segment),
                    "share_pct": len(segment) / len(df) * 100,
                    "media": segment[TARGET].mean(),
                    "mediana": segment[TARGET].median(),
                    "p90": segment[TARGET].quantile(0.90),
                }
            )
    return pd.DataFrame(rows)


def make_feature_decision_matrix(
    corr_table: pd.DataFrame,
    baseline_table: pd.DataFrame,
    stability_table: pd.DataFrame,
) -> pd.DataFrame:
    """Sintetiza la decision sugerida por feature inicial."""
    corr_lookup = corr_table.set_index("feature")["spearman"].to_dict()
    val_baselines = baseline_table[baseline_table["split"] == "val"].set_index("regla")
    stability_val = stability_table[stability_table["split_comparado"] == "val"]
    stability_lookup = stability_val.set_index("feature")[
        "corr_media_train_vs_split"
    ].to_dict()

    rows = [
        {
            "feature": "customer_state",
            "senal": "alta",
            "evidencia": f"baseline mediana estado MAE val {val_baselines.at['customer_state', 'mae_fallback_global']:.2f}; estabilidad corr {stability_lookup.get('customer_state', np.nan):.2f}",
            "riesgo": "bajo",
            "decision": "avanza y rolling 30d prioritario",
        },
        {
            "feature": "seller_state",
            "senal": "media",
            "evidencia": f"baseline MAE val {val_baselines.at['seller_state', 'mae_fallback_global']:.2f}",
            "riesgo": "bajo/medio",
            "decision": "mantener base; evaluar interaccion con destino",
        },
        {
            "feature": "ruta_estado",
            "senal": "alta",
            "evidencia": f"baseline ruta MAE val {val_baselines.at['ruta_estado', 'mae_fallback_global']:.2f}; cobertura elegible val {val_baselines.at['ruta_estado', 'cobertura_elegible_pct']:.1f}%",
            "riesgo": "medio por cardinalidad",
            "decision": "avanza como rolling con fallback",
        },
        {
            "feature": "dist_haversine_km",
            "senal": "alta descriptiva",
            "evidencia": f"Spearman {corr_lookup.get('dist_haversine_km', np.nan):.2f}",
            "riesgo": "nulos bajos y no linealidad",
            "decision": "mantener; evaluar bins/log",
        },
        {
            "feature": "categoria_principal",
            "senal": "media",
            "evidencia": f"baseline categoria MAE val {val_baselines.at['categoria_principal', 'mae_fallback_global']:.2f}; estabilidad corr {stability_lookup.get('categoria_principal', np.nan):.2f}",
            "riesgo": "categorias raras",
            "decision": "avanza con conteos y fallback",
        },
        {
            "feature": "flete_total / ratio_flete",
            "senal": "media",
            "evidencia": f"Spearman flete {corr_lookup.get('flete_total', np.nan):.2f}; ratio {corr_lookup.get('ratio_flete', np.nan):.2f}",
            "riesgo": "proxy de otras variables",
            "decision": "mantener; transformar/log y controlar outliers",
        },
        {
            "feature": "peso_total_g / volumen_total_cm3",
            "senal": "baja/media",
            "evidencia": f"Spearman peso {corr_lookup.get('peso_total_g', np.nan):.2f}; volumen {corr_lookup.get('volumen_total_cm3', np.nan):.2f}",
            "riesgo": "colas largas",
            "decision": "mantener con log/bins; validar incremental",
        },
        {
            "feature": "mes_compra / dia_semana_compra",
            "senal": "baja directa",
            "evidencia": f"Spearman mes {corr_lookup.get('mes_compra', np.nan):.2f}; dia {corr_lookup.get('dia_semana_compra', np.nan):.2f}",
            "riesgo": "capturar drift temporal",
            "decision": "mantener como control; no sobreinterpretar",
        },
        {
            "feature": "tasa_vendedor",
            "senal": "incierta para duracion",
            "evidencia": f"Spearman {corr_lookup.get('tasa_vendedor', np.nan):.2f}",
            "riesgo": "debe seguir point-in-time",
            "decision": "reemplazar/complementar con duracion rolling seller",
        },
        {
            "feature": "seller_id",
            "senal": "potencial pero riesgosa",
            "evidencia": f"baseline seller MAE val {val_baselines.at['seller_id', 'mae_fallback_global']:.2f}; cobertura elegible val {val_baselines.at['seller_id', 'cobertura_elegible_pct']:.1f}%",
            "riesgo": "memoriza y no generaliza a sellers nuevos",
            "decision": "no usar crudo; solo agregados historicos",
        },
    ]
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- #
# 2. Figuras
# --------------------------------------------------------------------------- #
def save_target_distribution(df: pd.DataFrame, figures_dir: Path) -> str:
    """Guarda histogramas del target por split."""
    path = figures_dir / "target_distribution_by_split.png"
    p99 = df[TARGET].quantile(0.99)
    fig, axes = plt.subplots(1, 3, figsize=(14, 4), sharey=True)

    for ax, split in zip(axes, SPLIT_ORDER):
        data = df.loc[df["split"] == split, TARGET].clip(upper=p99)
        ax.hist(data, bins=35, color="#4C78A8", alpha=0.85)
        ax.axvline(data.median(), color="#F58518", linewidth=2, label="mediana")
        ax.set_title(split)
        ax.set_xlabel("dias reales")
        ax.grid(axis="y", alpha=0.25)
    axes[0].set_ylabel("ordenes")
    axes[0].legend()
    fig.suptitle("Distribucion de dias_entrega_real por split (recorte p99 visual)")
    fig.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path.relative_to(PROJECT_ROOT).as_posix()


def save_bar_plot(
    table: pd.DataFrame,
    label_col: str,
    value_col: str,
    title: str,
    filename: str,
    figures_dir: Path,
) -> str:
    """Guarda barras horizontales para grupos con mayor duracion."""
    path = figures_dir / filename
    plot_df = table.sort_values(value_col, ascending=True)
    fig, ax = plt.subplots(figsize=(10, max(4, len(plot_df) * 0.35)))
    ax.barh(plot_df[label_col].astype(str), plot_df[value_col], color="#59A14F")
    ax.set_xlabel("dias reales promedio")
    ax.set_title(title)
    ax.grid(axis="x", alpha=0.25)
    for idx, (_, row) in enumerate(plot_df.iterrows()):
        ax.text(row[value_col] + 0.1, idx, f"n={int(row['ordenes']):,}", va="center")
    fig.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path.relative_to(PROJECT_ROOT).as_posix()


def save_seller_distribution(df: pd.DataFrame, figures_dir: Path) -> str:
    """Guarda distribucion de volumen por seller."""
    path = figures_dir / "seller_orders_distribution.png"
    seller_counts = df.groupby("seller_id")["order_id"].count()
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.hist(seller_counts, bins=50, color="#E15759", alpha=0.85)
    ax.set_yscale("log")
    ax.set_xlabel("ordenes por seller")
    ax.set_ylabel("cantidad de sellers (escala log)")
    ax.set_title("Distribucion de ordenes por seller")
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path.relative_to(PROJECT_ROOT).as_posix()


def save_numeric_correlations(corr_table: pd.DataFrame, figures_dir: Path) -> str:
    """Guarda correlaciones numericas con el target."""
    path = figures_dir / "numeric_spearman_correlations.png"
    plot_df = corr_table.sort_values("spearman", ascending=True)
    colors = np.where(plot_df["spearman"] >= 0, "#4C78A8", "#F58518")
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.barh(plot_df["feature"], plot_df["spearman"], color=colors)
    ax.axvline(0, color="#333333", linewidth=1)
    ax.set_xlabel("correlacion Spearman con dias_entrega_real")
    ax.set_title("Relacion monotona entre features numericas y target")
    ax.grid(axis="x", alpha=0.25)
    fig.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path.relative_to(PROJECT_ROOT).as_posix()


# --------------------------------------------------------------------------- #
# 3. Analisis principal
# --------------------------------------------------------------------------- #
def build_analysis(df: pd.DataFrame, figures_dir: Path) -> dict[str, object]:
    """Calcula todas las tablas y figuras requeridas por el reporte."""
    figures_dir.mkdir(parents=True, exist_ok=True)

    split_counts = (
        df["split"]
        .value_counts()
        .reindex(SPLIT_ORDER)
        .rename_axis("split")
        .reset_index(name="ordenes")
    )
    split_counts["share_pct"] = split_counts["ordenes"] / len(df) * 100

    target_summary = (
        df[TARGET]
        .describe(percentiles=[0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95, 0.99])
        .reset_index()
        .rename(columns={"index": "metrica", TARGET: "valor"})
    )

    split_target = (
        df.groupby("split")[TARGET]
        .agg(
            ordenes="count",
            media="mean",
            mediana="median",
            p75=lambda x: x.quantile(0.75),
            p90=lambda x: x.quantile(0.90),
            p95=lambda x: x.quantile(0.95),
        )
        .reindex(SPLIT_ORDER)
        .reset_index()
    )

    split_dates = (
        df.groupby("split")["order_purchase_timestamp"]
        .agg(inicio="min", fin="max")
        .reindex(SPLIT_ORDER)
        .reset_index()
    )
    split_dates["inicio"] = split_dates["inicio"].dt.strftime("%Y-%m-%d")
    split_dates["fin"] = split_dates["fin"].dt.strftime("%Y-%m-%d")

    missing = (
        (df.isna().mean() * 100)
        .round(3)
        .sort_values(ascending=False)
        .reset_index()
        .rename(columns={"index": "columna", 0: "missing_pct"})
    )

    customer_state = agg_target(df, "customer_state").sort_values(
        ["media", "ordenes"], ascending=[False, False]
    )
    seller_state = agg_target(df, "seller_state").sort_values(
        ["media", "ordenes"], ascending=[False, False]
    )
    ruta_estado = agg_target(df, "ruta_estado").sort_values(
        ["media", "ordenes"], ascending=[False, False]
    )
    categoria = agg_target(df, "categoria_principal").sort_values(
        ["media", "ordenes"], ascending=[False, False]
    )

    customer_top = customer_state[customer_state["ordenes"] >= 500].head(12)
    seller_top = seller_state[seller_state["ordenes"] >= 500].head(12)
    ruta_top = ruta_estado[ruta_estado["ordenes"] >= 200].head(15)
    categoria_top = categoria[categoria["ordenes"] >= 500].head(15)

    seller_counts = df.groupby("seller_id")["order_id"].count()
    seller_stats = pd.DataFrame(
        {
            "metrica": [
                "sellers_unicos",
                "ordenes_por_seller_mediana",
                "ordenes_por_seller_p75",
                "ordenes_por_seller_p90",
                "ordenes_por_seller_max",
                "sellers_con_1_orden_pct",
                "sellers_con_menos_5_ordenes_pct",
                "ordenes_en_sellers_menos_5_ordenes_pct",
                "ordenes_sin_historial_vendedor_pct",
            ],
            "valor": [
                seller_counts.shape[0],
                seller_counts.median(),
                seller_counts.quantile(0.75),
                seller_counts.quantile(0.90),
                seller_counts.max(),
                (seller_counts.eq(1).mean() * 100),
                (seller_counts.lt(5).mean() * 100),
                (
                    df["seller_id"].isin(seller_counts[seller_counts < 5].index).mean()
                    * 100
                ),
                (df["sin_historial_vendedor"].mean() * 100),
            ],
        }
    )

    seller_history_by_split = (
        df.groupby("split")
        .agg(
            ordenes=("order_id", "count"),
            sin_historial_pct=("sin_historial_vendedor", lambda x: x.mean() * 100),
            tasa_vendedor_media=("tasa_vendedor", "mean"),
            tasa_vendedor_mediana=("tasa_vendedor", "median"),
        )
        .reindex(SPLIT_ORDER)
        .reset_index()
    )

    numeric_cols = [col for col in NUMERIC_FEATURES if col in df.columns]
    corr_rows = []
    for col in numeric_cols:
        corr_rows.append(
            {
                "feature": col,
                "pearson": df[[col, TARGET]].corr(method="pearson").iloc[0, 1],
                "spearman": df[[col, TARGET]].corr(method="spearman").iloc[0, 1],
                "missing_pct": df[col].isna().mean() * 100,
            }
        )
    corr_table = pd.DataFrame(corr_rows).sort_values(
        "spearman", ascending=False, key=lambda s: s.abs()
    )
    transformation_table = evaluate_numeric_transformations(df)
    multicollinearity_matrix, multicollinearity_pairs = evaluate_multicollinearity(df)
    binary_segments = evaluate_binary_segments(df)
    baseline_table = evaluate_group_median_baselines(df)
    stability_table = evaluate_categorical_stability(df)

    categorical_cardinality = pd.DataFrame(
        {
            "columna": [
                "customer_state",
                "seller_state",
                "ruta_estado",
                "categoria_principal",
                "seller_id",
            ],
            "valores_unicos": [
                df["customer_state"].nunique(),
                df["seller_state"].nunique(),
                df["ruta_estado"].nunique(),
                df["categoria_principal"].nunique(),
                df["seller_id"].nunique(),
            ],
        }
    )

    forbidden_present = sorted(PROHIBITED_AS_FEATURES.intersection(df.columns))
    forbidden_unexpected = [col for col in forbidden_present if col != TARGET]
    expected_columns = [
        "order_id",
        "order_purchase_timestamp",
        "split",
        TARGET,
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
        "seller_id",
        "ruta_estado",
    ]
    column_check = pd.DataFrame(
        {
            "revision": [
                "filas",
                "columnas",
                "order_id_unico",
                "target_positivo",
                "target_max_menor_365",
                "columnas_prohibidas_presentes_sin_target",
                "dias_prometidos_ausente",
                "columnas_esperadas_presentes",
            ],
            "resultado": [
                f"{len(df):,}",
                f"{df.shape[1]:,}",
                str(df["order_id"].is_unique),
                str((df[TARGET] > 0).all()),
                str((df[TARGET] <= 365).all()),
                ", ".join(forbidden_unexpected) if forbidden_unexpected else "ninguna",
                str("dias_prometidos" not in df.columns),
                str(set(expected_columns).issubset(df.columns)),
            ],
        }
    )

    figures = {
        "target_distribution": save_target_distribution(df, figures_dir),
        "customer_state": save_bar_plot(
            customer_top,
            "customer_state",
            "media",
            "Estados destino con mayor duracion media (n >= 500)",
            "customer_state_top_duration.png",
            figures_dir,
        ),
        "ruta_estado": save_bar_plot(
            ruta_top,
            "ruta_estado",
            "media",
            "Rutas estado-estado con mayor duracion media (n >= 200)",
            "ruta_estado_top_duration.png",
            figures_dir,
        ),
        "seller_distribution": save_seller_distribution(df, figures_dir),
        "numeric_correlations": save_numeric_correlations(corr_table, figures_dir),
    }
    decision_matrix = make_feature_decision_matrix(
        corr_table, baseline_table, stability_table
    )

    return {
        "feature_inventory": make_feature_inventory(),
        "split_counts": split_counts,
        "target_summary": target_summary,
        "split_target": split_target,
        "split_dates": split_dates,
        "missing": missing,
        "customer_state": customer_state,
        "seller_state": seller_state,
        "ruta_estado": ruta_estado,
        "categoria": categoria,
        "customer_top": customer_top,
        "seller_top": seller_top,
        "ruta_top": ruta_top,
        "categoria_top": categoria_top,
        "seller_stats": seller_stats,
        "seller_history_by_split": seller_history_by_split,
        "corr_table": corr_table,
        "transformation_table": transformation_table,
        "multicollinearity_matrix": multicollinearity_matrix,
        "multicollinearity_pairs": multicollinearity_pairs,
        "binary_segments": binary_segments,
        "baseline_table": baseline_table,
        "stability_table": stability_table,
        "decision_matrix": decision_matrix,
        "categorical_cardinality": categorical_cardinality,
        "column_check": column_check,
        "figures": figures,
    }


# --------------------------------------------------------------------------- #
# 4. Reporte Markdown
# --------------------------------------------------------------------------- #
def render_report(df: pd.DataFrame, analysis: dict[str, object]) -> str:
    """Renderiza el reporte final en Markdown."""
    split_target = analysis["split_target"]
    corr_table = analysis["corr_table"]
    transformation_table = analysis["transformation_table"]
    multicollinearity_matrix = analysis["multicollinearity_matrix"]
    multicollinearity_pairs = analysis["multicollinearity_pairs"]
    binary_segments = analysis["binary_segments"]
    baseline_table = analysis["baseline_table"]
    stability_table = analysis["stability_table"]
    decision_matrix = analysis["decision_matrix"]
    customer_top = analysis["customer_top"]
    ruta_top = analysis["ruta_top"]
    seller_stats = analysis["seller_stats"]
    figures = analysis["figures"]
    figure_links = {
        name: path.removeprefix("reports/") for name, path in figures.items()
    }

    train_median = split_target.loc[split_target["split"] == "train", "mediana"].iloc[0]
    test_median = split_target.loc[split_target["split"] == "test", "mediana"].iloc[0]
    target_median = df[TARGET].median()
    target_p90 = df[TARGET].quantile(0.90)

    top_corr = corr_table.head(5)[["feature", "spearman"]].copy()
    top_states = customer_top.head(5)[
        ["customer_state", "ordenes", "media", "mediana", "p90"]
    ]
    top_routes = ruta_top.head(5)[["ruta_estado", "ordenes", "media", "mediana", "p90"]]

    seller_unique = int(seller_stats.loc[seller_stats["metrica"] == "sellers_unicos", "valor"].iloc[0])
    no_hist_pct = float(
        seller_stats.loc[
            seller_stats["metrica"] == "ordenes_sin_historial_vendedor_pct", "valor"
        ].iloc[0]
    )

    lines: list[str] = []
    lines.append("# Fase 2 - EDA de regresion sobre dias_entrega_real")
    lines.append("")
    lines.append(
        "> EDA significa analisis exploratorio de datos: revisar patrones antes de modelar. "
        "Este reporte interpreta el dataset experimental de Chat B para decidir que "
        "features deben avanzar a Chat D."
    )
    lines.append("")
    lines.append("## 1. Resumen ejecutivo")
    lines.append("")
    lines.append(
        f"El dataset contiene {len(df):,} ordenes y {df.shape[1]} columnas, con una "
        f"mediana global de {target_median:.2f} dias reales de entrega y un p90 de "
        f"{target_p90:.2f} dias. La distribucion es asimetrica: la mayoria de ordenes "
        "se entrega relativamente rapido, pero hay una cola larga de casos lentos."
    )
    lines.append("")
    lines.append(
        "Las senales mas prometedoras son geograficas y operativas: estado destino "
        "(`customer_state`), ruta estado-estado (`ruta_estado` como soporte para rolling), "
        "estado vendedor, categoria, flete/precio/peso/volumen y la historia del seller "
        "cuando existe. La palabra rolling significa ventana movil de pasado: por ejemplo, "
        "mirar los ultimos 30 dias antes de la compra, sin incluir la orden actual."
    )
    lines.append("")
    lines.append(
        "Los riesgos principales son: cambio de regimen temporal R-14, cola larga de "
        "duraciones extremas, sellers con historial desigual y posible sobreinterpretacion "
        "de correlaciones. Correlacion significa que dos variables se mueven juntas; no "
        "demuestra que una cause la otra."
    )
    lines.append("")
    lines.append("Features que parecen avanzar:")
    lines.append("")
    lines.append("- `customer_state` y `seller_state`, por senal geografica interpretable.")
    lines.append("- `ruta_estado` solo como soporte para rolling, no necesariamente como categoria cruda sin control.")
    lines.append("- `categoria_principal`, con umbrales de volumen para evitar categorias raras.")
    lines.append("- Variables fisicas y economicas: `flete_total`, `ratio_flete`, `peso_total_g`, `volumen_total_cm3`, `precio_total`, `n_items`.")
    lines.append("- `tasa_vendedor` y `sin_historial_vendedor`, manteniendo calculo point-in-time.")
    lines.append("")
    lines.append("## 2. Validacion del dataset de Chat B")
    lines.append("")
    lines.append("### Shape y columnas")
    lines.append("")
    lines.append(to_markdown(analysis["column_check"]))
    lines.append("")
    lines.append("Columnas observadas:")
    lines.append("")
    lines.append("```text")
    lines.append(", ".join(df.columns))
    lines.append("```")
    lines.append("")
    lines.append("Cardinalidad de columnas categoricas y de soporte:")
    lines.append("")
    lines.append(to_markdown(analysis["categorical_cardinality"]))
    lines.append("")
    lines.append("### Conteo por split")
    lines.append("")
    lines.append(to_markdown(analysis["split_counts"]))
    lines.append("")
    lines.append("Rangos temporales por split:")
    lines.append("")
    lines.append(to_markdown(analysis["split_dates"]))
    lines.append("")
    lines.append("### Distribucion de dias_entrega_real")
    lines.append("")
    lines.append(to_markdown(analysis["target_summary"]))
    lines.append("")
    lines.append(f"![Distribucion por split]({figure_links['target_distribution']})")
    lines.append("")
    lines.append("### Revision anti-leakage rapida")
    lines.append("")
    lines.append(
        "Leakage significa fuga de informacion: usar datos del futuro como si fueran "
        "conocidos al momento de compra. En la salida revisada no aparecen "
        "`order_delivered_customer_date`, `order_delivered_carrier_date`, reviews, "
        "`entrega_tarde`, `dias_vs_promesa` ni `dias_prometidos`. `dias_entrega_real` "
        "esta presente solo como target, no como feature."
    )
    lines.append("")
    lines.append("Porcentaje de nulos principales:")
    lines.append("")
    lines.append(to_markdown(analysis["missing"].head(10), float_digits=3))
    lines.append("")
    lines.append("## 3. Analisis temporal")
    lines.append("")
    lines.append(to_markdown(split_target))
    lines.append("")
    lines.append(
        f"La mediana baja de {train_median:.2f} dias en train a {test_median:.2f} dias "
        "en test. Esto es consistente con R-14: el regimen temporal de 2018 parece mas "
        "rapido que el pasado de entrenamiento. Si Chat D construye rolling features, "
        "debe reportar cobertura y efecto por split, porque una senal que funciona en "
        "train puede degradarse o cambiar de sentido en periodos recientes."
    )
    lines.append("")
    lines.append(
        "Lectura practica: el split temporal es correcto y necesario. No conviene usar "
        "split aleatorio, porque mezclaria meses viejos y nuevos y podria esconder el "
        "cambio de regimen."
    )
    lines.append("")
    lines.append("## 4. Analisis por geografia")
    lines.append("")
    lines.append("### Customer state")
    lines.append("")
    lines.append(to_markdown(top_states))
    lines.append("")
    lines.append(f"![Estados destino]({figure_links['customer_state']})")
    lines.append("")
    lines.append("### Seller state")
    lines.append("")
    lines.append(
        to_markdown(
            analysis["seller_top"].head(10)[
                ["seller_state", "ordenes", "media", "mediana", "p90"]
            ]
        )
    )
    lines.append("")
    lines.append("### Ruta estado-estado")
    lines.append("")
    lines.append(to_markdown(top_routes))
    lines.append("")
    lines.append(f"![Rutas estado]({figure_links['ruta_estado']})")
    lines.append("")
    lines.append(
        "`ruta_estado` es especialmente util como base de features rolling: resume "
        "origen y destino sin usar datos futuros. Sin embargo, como categoria cruda puede "
        "generar alta cardinalidad y rutas con poco volumen. La recomendacion es usarla "
        "con umbral de cobertura y fallback por `customer_state`."
    )
    lines.append("")
    lines.append("## 5. Analisis por seller")
    lines.append("")
    lines.append(to_markdown(seller_stats, float_digits=2))
    lines.append("")
    lines.append(to_markdown(analysis["seller_history_by_split"]))
    lines.append("")
    lines.append(f"![Distribucion sellers]({figure_links['seller_distribution']})")
    lines.append("")
    lines.append(
        f"Hay {seller_unique:,} sellers. La cobertura historica no es uniforme: "
        f"{no_hist_pct:.2f}% de las ordenes queda marcada con `sin_historial_vendedor=1`. "
        "`tasa_vendedor` es valida solo porque fue calculada point-in-time, es decir, "
        "mirando pedidos previos ya cerrados antes de la compra actual."
    )
    lines.append("")
    lines.append(
        "`seller_id` crudo no debe ser feature inicial: puede memorizar vendedores del "
        "pasado, no generaliza bien a sellers nuevos o con pocas ordenes y complica la "
        "interpretacion. Si se usa seller, conviene convertirlo en agregados historicos "
        "con fallback: tasa/duracion rolling, conteo de historial y flag de insuficiencia."
    )
    lines.append("")
    lines.append("## 6. Categoria y caracteristicas fisicas")
    lines.append("")
    lines.append("Categorias con mayor duracion media y volumen suficiente:")
    lines.append("")
    lines.append(
        to_markdown(
            analysis["categoria_top"].head(12)[
                ["categoria_principal", "ordenes", "media", "mediana", "p90"]
            ]
        )
    )
    lines.append("")
    lines.append("Relacion de features numericas con el target:")
    lines.append("")
    lines.append(to_markdown(corr_table[["feature", "pearson", "spearman", "missing_pct"]]))
    lines.append("")
    lines.append(f"![Correlaciones numericas]({figure_links['numeric_correlations']})")
    lines.append("")
    lines.append(
        "Spearman mide relacion monotona por ranking: si una variable sube y el target "
        "tiende a subir tambien, Spearman sera positivo aunque la relacion no sea lineal. "
        "Las correlaciones son moderadas o bajas; eso no descarta utilidad en modelos "
        "tabulares, pero obliga a validar mejora incremental con MAE en Chat E."
    )
    lines.append("")
    lines.append("## 7. Analisis profundo de feature engineering")
    lines.append("")
    lines.append(
        "Feature engineering significa disenar variables utiles para el modelo a "
        "partir de datos disponibles. En esta fase no buscamos agregar columnas por "
        "intuicion: buscamos decidir que senales tienen evidencia, cobertura, "
        "estabilidad temporal y bajo riesgo de leakage."
    )
    lines.append("")
    lines.append("### 7.1 Punto de partida: features iniciales y preguntas a evaluar")
    lines.append("")
    lines.append(
        "La siguiente tabla separa las features base M0 de las columnas de soporte. "
        "M0 significa momento de compra: solo se aceptan variables conocidas en ese "
        "momento o historicos cerrados antes de ese momento."
    )
    lines.append("")
    lines.append(
        to_markdown(
            analysis["feature_inventory"][
                ["bloque", "feature", "rol", "influencia_esperada", "evaluar"]
            ]
        )
    )
    lines.append("")
    lines.append("### 7.2 Marco de decision")
    lines.append("")
    lines.append(
        "Una feature candidata debe pasar cinco filtros antes de avanzar a Chat D:"
    )
    lines.append("")
    lines.append("- Disponibilidad M0: se conoce en la compra o se calcula con pasado cerrado.")
    lines.append("- Cobertura: aplica a suficientes ordenes en train, val y test.")
    lines.append("- Estabilidad: mantiene sentido entre periodos, especialmente por R-14.")
    lines.append("- Interpretabilidad: se puede explicar al negocio sin forzar causalidad.")
    lines.append("- Mejora incremental: en Chat E debe mejorar MAE o error regional frente a baselines.")
    lines.append("")
    lines.append(
        "MAE significa error absoluto medio: cuantos dias se equivoca una regla o "
        "modelo en promedio. En esta seccion todavia no entrenamos modelos; usamos "
        "baselines simples para medir senal inicial."
    )
    lines.append("")
    lines.append("### 7.3 Baselines por agregacion historica")
    lines.append("")
    lines.append(
        "Estas reglas usan solo el split train para calcular medianas historicas y "
        "las aplican en val/test con fallback a la mediana global de train. Si una "
        "agregacion simple reduce MAE, la columna tiene senal candidata para feature "
        "engineering. Fallback significa valor de respaldo cuando una ruta, categoria "
        "o seller no tiene historial suficiente."
    )
    lines.append("")
    lines.append(
        to_markdown(
            baseline_table[
                [
                    "split",
                    "regla",
                    "min_train_n",
                    "grupos_train",
                    "grupos_elegibles",
                    "cobertura_seen_pct",
                    "cobertura_elegible_pct",
                    "mae_fallback_global",
                ]
            ],
            float_digits=2,
        )
    )
    lines.append("")
    lines.append(
        "Lectura: `customer_state` y `ruta_estado` tienen una prueba inicial fuerte "
        "porque reglas muy simples por destino/ruta compiten contra la mediana global. "
        "`seller_id` puede mejorar en algunos casos, pero su cobertura elegible y su "
        "riesgo de memorizar vendedores obligan a no usarlo crudo."
    )
    lines.append("")
    lines.append("### 7.4 Estabilidad temporal de agregaciones")
    lines.append("")
    lines.append(
        "La siguiente tabla compara medias de grupos entre train y val/test usando "
        "umbrales minimos de volumen. Una correlacion alta indica que el ranking de "
        "grupos se parece entre periodos; un shift alto indica que el nivel de dias "
        "cambio, aunque el orden relativo pueda mantenerse."
    )
    lines.append("")
    lines.append(to_markdown(stability_table, float_digits=2))
    lines.append("")
    lines.append(
        "Por R-14, no basta con encontrar diferencias entre grupos: hay que verificar "
        "si esas diferencias sobreviven al cambio temporal de 2018. Si una feature es "
        "estable en ranking pero baja de nivel, Chat D debe usar rolling reciente para "
        "capturar el nuevo regimen."
    )
    lines.append("")
    lines.append("### 7.5 Features binarias: lectura operacional")
    lines.append("")
    lines.append(to_markdown(binary_segments, float_digits=2))
    lines.append("")
    lines.append(
        "`mismo_estado` ayuda a resumir cercania logistica, pero probablemente queda "
        "por debajo de `ruta_estado` y `dist_haversine_km`. `sin_historial_vendedor` "
        "no busca explicar duracion por si sola; su valor es avisar que la historia "
        "del seller tiene baja confianza."
    )
    lines.append("")
    lines.append("### 7.6 Transformaciones numericas candidatas")
    lines.append("")
    lines.append(
        "Muchas variables fisicas y economicas tienen cola larga: pocos pedidos muy "
        "pesados, muy caros o muy voluminosos. Una transformacion log1p comprime esos "
        "extremos. log1p significa aplicar log(1 + valor), util cuando hay ceros."
    )
    lines.append("")
    lines.append(to_markdown(transformation_table, float_digits=3))
    lines.append("")
    lines.append(
        "La correlacion Spearman no cambia mucho con log1p porque Spearman usa ranking, "
        "pero la transformacion puede ayudar a modelos lineales y a controlar outliers. "
        "Para arboles como XGBoost puede ser menos necesaria, aunque sigue siendo util "
        "para interpretacion y baselines lineales."
    )
    lines.append("")
    lines.append("### 7.6.1 Multicolinealidad exploratoria")
    lines.append("")
    lines.append(
        "Multicolinealidad significa que dos o mas features cuentan informacion muy "
        "parecida. En Chat C se revisa como alerta de diseno: no elimina variables de "
        "forma definitiva, pero advierte que Chat E debe medir si una variable aporta "
        "algo nuevo o solo repite informacion de otra."
    )
    lines.append("")
    lines.append(
        "Matriz Spearman entre features numericas y binarias relacionadas con distancia, "
        "costo y fisica del envio:"
    )
    lines.append("")
    lines.append(to_markdown(multicollinearity_matrix, float_digits=3))
    lines.append("")
    lines.append("Pares con mayor redundancia exploratoria:")
    lines.append("")
    lines.append(
        to_markdown(
            multicollinearity_pairs.head(12)[
                ["feature_a", "feature_b", "spearman", "spearman_abs", "lectura"]
            ],
            float_digits=3,
        )
    )
    lines.append("")
    lines.append(
        "Implicacion: `dist_haversine_km`, `flete_total`, `ratio_flete`, peso y volumen "
        "pueden solaparse parcialmente porque todos describen dificultad logistica. "
        "Para modelos lineales, Chat E debe revisar VIF o regularizacion. Para modelos "
        "de arboles, el riesgo principal es interpretar mal las importancias, porque "
        "dos features redundantes pueden repartirse el mismo merito predictivo."
    )
    lines.append("")
    lines.append("### 7.7 Hipotesis por bloque")
    lines.append("")
    lines.append("Geografia y ruta:")
    lines.append("")
    lines.append("- Hipotesis: la dificultad de entrega depende mas del destino y la ruta que de una distancia lineal pura.")
    lines.append("- Evidencia actual: `dist_haversine_km` tiene Spearman alto y los estados/rutas lentas se concentran en destinos especificos.")
    lines.append("- Evaluacion Chat D: rolling 30d por `ruta_estado` y `customer_state`, con conteo y fallback.")
    lines.append("")
    lines.append("Seller:")
    lines.append("")
    lines.append("- Hipotesis: sellers con historial reciente lento tienden a generar entregas mas largas, pero solo cuando hay historial suficiente.")
    lines.append("- Evidencia actual: muchos sellers tienen bajo volumen; `tasa_vendedor` tiene baja correlacion directa con duracion real.")
    lines.append("- Evaluacion Chat D: reemplazar o complementar con `seller_id_30d_days_mean`, conteo previo y flag de insuficiencia.")
    lines.append("")
    lines.append("Categoria y fisica:")
    lines.append("")
    lines.append("- Hipotesis: categorias, peso, volumen y flete capturan complejidad logistica, aunque no necesariamente causalidad.")
    lines.append("- Evidencia actual: categorias como `office_furniture` muestran mayor duracion; flete y distancia tienen relacion monotona.")
    lines.append("- Evaluacion Chat D/E: rolling por categoria y transformaciones log/bins para fisicas.")
    lines.append("")
    lines.append("Temporalidad:")
    lines.append("")
    lines.append("- Hipotesis: el regimen logistico cambia en 2018; las medias historicas largas pueden quedar desactualizadas.")
    lines.append("- Evidencia actual: la mediana baja de train a test de forma marcada.")
    lines.append("- Evaluacion Chat D: rolling 30d primero; comparar 60/90d si 30d tiene poca cobertura.")
    lines.append("")
    lines.append("### 7.8 Transformaciones e interacciones candidatas")
    lines.append("")
    lines.append("Transformaciones que deben evaluarse:")
    lines.append("")
    lines.append("- `log_dist_haversine_km`, `log_flete_total`, `log_peso_total_g`, `log_volumen_total_cm3`.")
    lines.append("- Bins de distancia: corta, media, larga, muy larga, definidos por cuantiles de train.")
    lines.append("- Flags de paquete pesado/voluminoso usando p90 de train.")
    lines.append("- Conteos historicos por grupo para que el modelo sepa que tan confiable es cada agregado.")
    lines.append("")
    lines.append("Interacciones candidatas con cautela:")
    lines.append("")
    lines.append("- `ruta_estado` x `categoria_principal`, solo si hay volumen suficiente.")
    lines.append("- `dist_haversine_km` x `peso_total_g` o bins de distancia x peso alto.")
    lines.append("- `customer_state` x `mes_compra`, para capturar estacionalidad regional.")
    lines.append("- Seller historico x categoria, solo como experimento posterior si hay cobertura.")
    lines.append("")
    lines.append("### 7.9 Matriz de decision")
    lines.append("")
    lines.append(to_markdown(decision_matrix, float_digits=2))
    lines.append("")
    lines.append("### 7.9.1 Como se traduce esta matriz hacia Chat D")
    lines.append("")
    lines.append(
        "La matriz no es una seleccion final de features del modelo. Es una decision "
        "de diseno para el siguiente paso: que familias vale la pena construir como "
        "features candidatas, cuales necesitan controles y cuales no deben usarse como "
        "feature directa."
    )
    lines.append("")
    lines.append("Lectura operativa:")
    lines.append("")
    lines.append("- `avanza`: Chat D debe construir una version point-in-time, medir cobertura y documentar fallback.")
    lines.append("- `mantener base`: la feature puede seguir en el dataset base, pero no requiere rolling inmediata.")
    lines.append("- `cautela`: la feature puede ser util, pero necesita controles de volumen, multicolinealidad o leakage.")
    lines.append("- `no usar crudo`: la columna puede servir como soporte para agregados, pero no como entrada directa del modelo.")
    lines.append("")
    lines.append(
        "La seleccion real queda para Chat E: comparar modelos con y sin cada bloque "
        "mediante MAE, MedAE, p90 del error y revision regional. Por eso Chat D debe "
        "entregar features candidatas bien calculadas, no una lista cerrada de features "
        "finales."
    )
    lines.append("")
    lines.append("### 7.10 Deben avanzar")
    lines.append("")
    lines.append("- Rolling 30 dias de `ruta_estado` para media/mediana de `dias_entrega_real`, con conteo de observaciones.")
    lines.append("- Rolling 30 dias de `customer_state`, por alta cobertura esperada y lectura simple de destino.")
    lines.append("- Rolling 30 dias de `categoria_principal`, con categorias raras respaldadas por promedio global o grupo `desconocido`.")
    lines.append("- Rolling de seller solo si incluye conteo previo, flag de historial insuficiente y fallback por ruta/estado.")
    lines.append("- Mantener features base M0 fisicas, economicas y temporales para comparar contra el baseline sin rolling.")
    lines.append("")
    lines.append("### 7.11 Requieren cautela")
    lines.append("")
    lines.append("- `tasa_vendedor`: util, pero debe seguir siendo point-in-time y auditable.")
    lines.append("- `ruta_estado` cruda: prometedora, pero con riesgo de alta cardinalidad y rutas raras.")
    lines.append("- `dist_haversine_km`: interpretable, aunque tiene algunos nulos y puede capturar peor que estado/ruta la realidad logistica.")
    lines.append("- `dias_prometidos`: no debe entrar al modelo principal; solo benchmark controlado para medir si el modelo copia la politica actual.")
    lines.append("")
    lines.append("### 7.12 No deben avanzar")
    lines.append("")
    lines.append("- `dias_entrega_real` como feature: es el target.")
    lines.append("- Fechas posteriores a la compra: `order_delivered_customer_date` y `order_delivered_carrier_date`.")
    lines.append("- `dias_vs_promesa`, `entrega_tarde` y variables de reviews.")
    lines.append("- `seller_id` crudo en el primer modelo.")
    lines.append("- Clustering como requisito MVP; clustering puede quedar como experimento futuro si los baselines dejan una pregunta clara.")
    lines.append("")
    lines.append("## 8. Recomendacion para Chat D")
    lines.append("")
    lines.append(
        "A partir de las conclusiones 7.9 a 7.12, Chat D debe construir features "
        "candidatas, no seleccionar el modelo final. La prioridad es convertir las "
        "senales prometedoras en variables point-in-time auditables, con conteo de "
        "historial y fallback."
    )
    lines.append("")
    lines.append("Construir primero estas rolling features point-in-time:")
    lines.append("")
    lines.append("- `ruta_estado_30d_days_mean`, `ruta_estado_30d_days_median`, `ruta_estado_30d_orders_count`.")
    lines.append("- `customer_state_30d_days_mean`, `customer_state_30d_days_median`, `customer_state_30d_orders_count`.")
    lines.append("- `categoria_principal_30d_days_mean`, `categoria_principal_30d_orders_count`.")
    lines.append("- `seller_id_30d_days_mean`, `seller_id_30d_orders_count`, `seller_id_30d_sin_historial`.")
    lines.append("")
    lines.append(
        "Ventanas sugeridas: empezar con 30 dias por ser el diseno aprobado; comparar "
        "contra 60 y 90 dias solo si 30 dias muestra baja cobertura o alta volatilidad. "
        "Para seller, evaluar tambien ventana acumulada historica con desplazamiento, "
        "porque muchos sellers pueden no tener suficiente volumen en 30 dias."
    )
    lines.append("")
    lines.append("Criterios minimos de validacion:")
    lines.append("")
    lines.append("- Excluir la orden actual y cualquier orden futura.")
    lines.append("- Exigir conteo previo por grupo y reportar cobertura por split.")
    lines.append("- Usar fallback jerarquico: ruta -> customer_state -> global train, y seller -> ruta/customer_state -> global train.")
    lines.append("- Comparar cobertura y estabilidad en train, val y test.")
    lines.append("- En Chat E, aceptar features solo si mejoran MAE o reducen errores regionales frente a baselines.")
    lines.append("- Llevar a Chat E las alertas de multicolinealidad para evaluar redundancia con ablacion y, si aplica, VIF.")
    lines.append("")
    lines.append("## 9. Limitaciones y dudas")
    lines.append("")
    lines.append("- Este EDA no prueba causalidad; solo identifica senales predictivas candidatas.")
    lines.append("- El dataset no mide conversion, abandono de carrito ni costo logistico real.")
    lines.append("- La cola larga del target puede afectar MAE; conviene reportar tambien MedAE y p90 del error en modelado.")
    lines.append("- R-14 sigue abierto: el futuro reciente es mas rapido que el pasado de train.")
    lines.append("- Las figuras usan agregados descriptivos; no reemplazan validacion con modelo y backtesting.")
    lines.append("")
    lines.append("## 10. Figuras generadas")
    lines.append("")
    for name, path in figures.items():
        lines.append(f"- `{name}`: `{path}`")
    lines.append("")
    lines.append("## 11. Comando reproducible")
    lines.append("")
    lines.append("```powershell")
    lines.append("venv\\Scripts\\python.exe scripts\\eda_fase2_regresion.py")
    lines.append("```")
    lines.append("")
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# 5. CLI
# --------------------------------------------------------------------------- #
def run(
    input_path: str | Path = DEFAULT_INPUT,
    report_path: str | Path = DEFAULT_REPORT,
    figures_dir: str | Path = DEFAULT_FIGURES_DIR,
) -> None:
    """Ejecuta el EDA y escribe reporte/figuras."""
    input_path = Path(input_path)
    report_path = Path(report_path)
    figures_dir = Path(figures_dir)

    if not input_path.exists():
        raise FileNotFoundError(f"No se encontro el dataset: {input_path}")

    df = pd.read_csv(input_path, parse_dates=["order_purchase_timestamp"])
    analysis = build_analysis(df, figures_dir)
    report = render_report(df, analysis)

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report, encoding="utf-8")

    print(f"Reporte creado: {report_path}")
    print(f"Figuras creadas en: {figures_dir}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Genera EDA Fase 2 para regresion sobre dias_entrega_real"
    )
    parser.add_argument("--input", default=str(DEFAULT_INPUT))
    parser.add_argument("--report", default=str(DEFAULT_REPORT))
    parser.add_argument("--figures-dir", default=str(DEFAULT_FIGURES_DIR))
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run(args.input, args.report, args.figures_dir)
