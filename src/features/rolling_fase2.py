"""Features rolling point-in-time para Fase 2 de regresion.

Este modulo toma el dataset experimental de Fase 2 y agrega senales de historia
reciente usando solo ordenes ya entregadas antes del momento de compra M0.

Uso:
    python -m src.features.rolling_fase2 \
        --input data/processed/orders_fase2_regresion.csv \
        --input-dir "C:/ruta/OLIST DATASETS" \
        --output data/processed/orders_fase2_regresion_rolling.csv \
        --report reports/fase2_rolling_features.md
"""

from __future__ import annotations

import argparse
from bisect import bisect_left, insort
from collections import deque
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd


# --------------------------------------------------------------------------- #
# 0. Contrato de columnas y rutas
# --------------------------------------------------------------------------- #
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = PROJECT_ROOT / "data" / "processed" / "orders_fase2_regresion.csv"
DEFAULT_OUTPUT = (
    PROJECT_ROOT / "data" / "processed" / "orders_fase2_regresion_rolling.csv"
)
DEFAULT_REPORT = PROJECT_ROOT / "reports" / "fase2_rolling_features.md"
# Default portable (relativo al repo); si los crudos viven en otra ruta, usar --input-dir.
DEFAULT_INPUT_DIR = PROJECT_ROOT / "data" / "raw"

TARGET = "dias_entrega_real"
PURCHASE_COL = "order_purchase_timestamp"
DELIVERY_COL = "order_delivered_customer_date"
WINDOW_DAYS = 30
SPLIT_ORDER = ["train", "val", "test"]

RAW_ORDERS_FILE = "olist_orders_dataset.csv"

FORBIDDEN_OUTPUT_COLUMNS = {
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
}

ROLLING_SPECS = [
    {
        "group_col": "ruta_estado",
        "prefix": "ruta_estado_30d",
        "include_median": True,
    },
    {
        "group_col": "customer_state",
        "prefix": "customer_state_30d",
        "include_median": True,
    },
    {
        "group_col": "categoria_principal",
        "prefix": "categoria_principal_30d",
        "include_median": False,
    },
    {
        "group_col": "seller_id",
        "prefix": "seller_id_30d",
        "include_median": False,
    },
]

ROLLING_PURE_COLUMNS = [
    "ruta_estado_30d_days_mean",
    "ruta_estado_30d_days_median",
    "ruta_estado_30d_orders_count",
    "ruta_estado_30d_sin_historial",
    "customer_state_30d_days_mean",
    "customer_state_30d_days_median",
    "customer_state_30d_orders_count",
    "customer_state_30d_sin_historial",
    "categoria_principal_30d_days_mean",
    "categoria_principal_30d_orders_count",
    "categoria_principal_30d_sin_historial",
    "seller_id_30d_days_mean",
    "seller_id_30d_orders_count",
    "seller_id_30d_sin_historial",
]

FALLBACK_COLUMNS = [
    "customer_state_30d_days_mean_fallback",
    "ruta_estado_30d_days_mean_fallback",
    "categoria_principal_30d_days_mean_fallback",
    "seller_id_30d_days_mean_fallback",
]


# --------------------------------------------------------------------------- #
# 1. Utilidades de calculo rolling
# --------------------------------------------------------------------------- #
def _median_from_sorted(values: list[float]) -> float:
    """Calcula mediana desde una lista ya ordenada."""
    n_values = len(values)
    if n_values == 0:
        return np.nan
    middle = n_values // 2
    if n_values % 2:
        return float(values[middle])
    return float((values[middle - 1] + values[middle]) / 2)


def _remove_sorted(values: list[float], value: float) -> None:
    """Elimina una ocurrencia de value en una lista ordenada."""
    pos = bisect_left(values, value)
    if pos < len(values) and values[pos] == value:
        values.pop(pos)
        return
    raise ValueError(f"No se encontro el valor activo para remover: {value}")


def _rolling_stats_for_group(
    group: pd.DataFrame,
    original_index: pd.Index,
    window: pd.Timedelta,
    include_median: bool,
) -> tuple[pd.Series, pd.Series, pd.Series | None]:
    """Calcula conteo, media y mediana para un grupo sin mirar futuro."""
    events = group[[DELIVERY_COL, TARGET]].sort_values([DELIVERY_COL, TARGET])
    queries = group[[PURCHASE_COL]].sort_values(PURCHASE_COL)

    counts = pd.Series(0, index=original_index, dtype="int64")
    means = pd.Series(np.nan, index=original_index, dtype="float64")
    medians = (
        pd.Series(np.nan, index=original_index, dtype="float64")
        if include_median
        else None
    )

    active: deque[tuple[pd.Timestamp, float]] = deque()
    active_sorted_values: list[float] = []
    active_sum = 0.0
    event_pos = 0
    event_times = events[DELIVERY_COL].to_numpy()
    event_values = events[TARGET].to_numpy(dtype="float64")

    for idx, row in queries.iterrows():
        purchase_time = row[PURCHASE_COL]
        window_start = purchase_time - window

        while event_pos < len(events) and event_times[event_pos] < purchase_time:
            event_time = pd.Timestamp(event_times[event_pos])
            value = float(event_values[event_pos])
            active.append((event_time, value))
            active_sum += value
            insort(active_sorted_values, value)
            event_pos += 1

        while active and active[0][0] < window_start:
            _, old_value = active.popleft()
            active_sum -= old_value
            _remove_sorted(active_sorted_values, old_value)

        count = len(active)
        counts.at[idx] = count
        if count:
            means.at[idx] = active_sum / count
            if medians is not None:
                medians.at[idx] = _median_from_sorted(active_sorted_values)

    return counts, means, medians


def add_group_rolling_features(
    df: pd.DataFrame,
    group_col: str,
    prefix: str,
    window_days: int = WINDOW_DAYS,
    include_median: bool = True,
) -> pd.DataFrame:
    """Agrega rolling 30d por grupo usando entregas cerradas antes de M0."""
    required = {group_col, PURCHASE_COL, DELIVERY_COL, TARGET}
    missing = required - set(df.columns)
    if missing:
        raise KeyError(f"Faltan columnas para rolling {prefix}: {sorted(missing)}")

    output = df.copy()
    window = pd.Timedelta(days=window_days)
    counts = pd.Series(0, index=output.index, dtype="int64")
    means = pd.Series(np.nan, index=output.index, dtype="float64")
    medians = (
        pd.Series(np.nan, index=output.index, dtype="float64")
        if include_median
        else None
    )

    for _, group in output.groupby(group_col, dropna=False, sort=False):
        group_counts, group_means, group_medians = _rolling_stats_for_group(
            group=group,
            original_index=group.index,
            window=window,
            include_median=include_median,
        )
        counts.loc[group.index] = group_counts
        means.loc[group.index] = group_means
        if include_median and medians is not None and group_medians is not None:
            medians.loc[group.index] = group_medians

    output[f"{prefix}_orders_count"] = counts.astype("int64")
    output[f"{prefix}_days_mean"] = means.astype("float64")
    output[f"{prefix}_sin_historial"] = (counts == 0).astype("int64")
    if include_median and medians is not None:
        output[f"{prefix}_days_median"] = medians.astype("float64")
    return output


def add_all_rolling_features(
    df: pd.DataFrame, window_days: int = WINDOW_DAYS
) -> pd.DataFrame:
    """Calcula todas las familias rolling candidatas para Chat D."""
    output = df.copy()
    for spec in ROLLING_SPECS:
        output = add_group_rolling_features(
            output,
            group_col=spec["group_col"],
            prefix=spec["prefix"],
            window_days=window_days,
            include_median=spec["include_median"],
        )
    return output


# --------------------------------------------------------------------------- #
# 2. Fallbacks y validacion anti-leakage
# --------------------------------------------------------------------------- #
def add_fallback_features(df: pd.DataFrame) -> pd.DataFrame:
    """Agrega columnas con respaldo jerarquico usando la mediana global de train."""
    output = df.copy()
    train_mask = output["split"] == "train"
    if not train_mask.any():
        raise AssertionError("Se requiere split train para calcular fallback global")
    global_train = float(output.loc[train_mask, TARGET].median())

    output["customer_state_30d_days_mean_fallback"] = output[
        "customer_state_30d_days_mean"
    ].fillna(global_train)
    output["ruta_estado_30d_days_mean_fallback"] = (
        output["ruta_estado_30d_days_mean"]
        .fillna(output["customer_state_30d_days_mean"])
        .fillna(global_train)
    )
    output["categoria_principal_30d_days_mean_fallback"] = output[
        "categoria_principal_30d_days_mean"
    ].fillna(global_train)
    output["seller_id_30d_days_mean_fallback"] = (
        output["seller_id_30d_days_mean"]
        .fillna(output["ruta_estado_30d_days_mean"])
        .fillna(output["customer_state_30d_days_mean"])
        .fillna(global_train)
    )
    return output


def add_rolling_features(df: pd.DataFrame, window_days: int = WINDOW_DAYS) -> pd.DataFrame:
    """Agrega rolling puras y fallbacks jerarquicos al dataset enriquecido."""
    output = df.copy()
    output[PURCHASE_COL] = pd.to_datetime(output[PURCHASE_COL], errors="coerce")
    output[DELIVERY_COL] = pd.to_datetime(output[DELIVERY_COL], errors="coerce")
    output = add_all_rolling_features(output, window_days=window_days)
    output = add_fallback_features(output)
    return output


def assert_rolling_contract(df: pd.DataFrame) -> None:
    """Valida columnas esperadas y ausencia de campos prohibidos en la salida."""
    missing = (set(ROLLING_PURE_COLUMNS) | set(FALLBACK_COLUMNS)) - set(df.columns)
    if missing:
        raise AssertionError(f"Faltan columnas rolling: {sorted(missing)}")

    forbidden = FORBIDDEN_OUTPUT_COLUMNS & set(df.columns)
    if forbidden:
        raise AssertionError(f"Columnas prohibidas en salida rolling: {forbidden}")

    for col in [c for c in ROLLING_PURE_COLUMNS if c.endswith("_orders_count")]:
        if (df[col] < 0).any():
            raise AssertionError(f"Conteo negativo detectado en {col}")

    for col in FALLBACK_COLUMNS:
        if df[col].isna().any():
            raise AssertionError(f"Fallback con nulos detectado en {col}")


def clean_output_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Retira columnas internas posteriores a M0 antes de guardar."""
    output = df.drop(columns=[DELIVERY_COL], errors="ignore").copy()
    assert_rolling_contract(output)
    return output


# --------------------------------------------------------------------------- #
# 3. Entrada/salida y reporte
# --------------------------------------------------------------------------- #
def load_delivery_dates(input_dir: str | Path) -> pd.DataFrame:
    """Carga fechas reales de entrega para calculo interno point-in-time."""
    orders_path = Path(input_dir) / RAW_ORDERS_FILE
    if not orders_path.exists():
        raise FileNotFoundError(f"No se encontro la tabla de ordenes: {orders_path}")
    orders = pd.read_csv(
        orders_path,
        usecols=["order_id", DELIVERY_COL],
        parse_dates=[DELIVERY_COL],
    )
    return orders


def enrich_with_delivery_dates(
    dataset: pd.DataFrame, delivery_dates: pd.DataFrame
) -> pd.DataFrame:
    """Une fecha real de entrega solo como soporte interno de rolling."""
    if DELIVERY_COL in dataset.columns:
        return dataset.copy()

    enriched = dataset.merge(delivery_dates, on="order_id", how="left")
    missing = enriched[DELIVERY_COL].isna().sum()
    if missing:
        raise AssertionError(f"Ordenes sin fecha real de entrega interna: {missing}")
    return enriched


def _format_markdown_table(df: pd.DataFrame, digits: int = 2) -> str:
    """Convierte un DataFrame pequeno a tabla Markdown sin dependencias extras."""
    formatted = df.copy()
    for col in formatted.columns:
        if pd.api.types.is_float_dtype(formatted[col]):
            formatted[col] = formatted[col].map(lambda x: f"{x:,.{digits}f}")
        elif pd.api.types.is_integer_dtype(formatted[col]):
            formatted[col] = formatted[col].map(lambda x: f"{int(x):,}")
    formatted = formatted.astype(str)
    headers = list(formatted.columns)
    rows = formatted.values.tolist()
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    lines.extend("| " + " | ".join(row) + " |" for row in rows)
    return "\n".join(lines)


def coverage_by_split(df: pd.DataFrame) -> pd.DataFrame:
    """Resume cobertura de rolling puras por split."""
    rows = []
    specs = [
        ("ruta_estado", "ruta_estado_30d_orders_count"),
        ("customer_state", "customer_state_30d_orders_count"),
        ("categoria_principal", "categoria_principal_30d_orders_count"),
        ("seller_id", "seller_id_30d_orders_count"),
    ]
    for split in SPLIT_ORDER:
        split_df = df[df["split"] == split]
        for group_name, count_col in specs:
            rows.append(
                {
                    "split": split,
                    "grupo": group_name,
                    "ordenes": len(split_df),
                    "cobertura_pct": (split_df[count_col] > 0).mean() * 100,
                    "conteo_mediano": split_df[count_col].median(),
                    "conteo_p90": split_df[count_col].quantile(0.90),
                }
            )
    return pd.DataFrame(rows)


def fallback_by_split(df: pd.DataFrame) -> pd.DataFrame:
    """Calcula porcentaje de filas que necesitaron fallback por familia."""
    rows = []
    specs = [
        ("customer_state", "customer_state_30d_sin_historial"),
        ("ruta_estado", "ruta_estado_30d_sin_historial"),
        ("categoria_principal", "categoria_principal_30d_sin_historial"),
        ("seller_id", "seller_id_30d_sin_historial"),
    ]
    for split in SPLIT_ORDER:
        split_df = df[df["split"] == split]
        for group_name, flag_col in specs:
            rows.append(
                {
                    "split": split,
                    "grupo": group_name,
                    "fallback_pct": split_df[flag_col].mean() * 100,
                }
            )
    return pd.DataFrame(rows)


def rolling_mae_comparison(df: pd.DataFrame) -> pd.DataFrame:
    """Compara reglas 30d con fallback contra el target por split."""
    rows = []
    specs = [
        ("customer_state_30d", "customer_state_30d_days_mean_fallback"),
        ("ruta_estado_30d", "ruta_estado_30d_days_mean_fallback"),
        ("categoria_principal_30d", "categoria_principal_30d_days_mean_fallback"),
        ("seller_id_30d", "seller_id_30d_days_mean_fallback"),
    ]
    for split in SPLIT_ORDER:
        split_df = df[df["split"] == split]
        for regla, pred_col in specs:
            rows.append(
                {
                    "split": split,
                    "regla": regla,
                    "mae_dias": (split_df[TARGET] - split_df[pred_col]).abs().mean(),
                    "pred_mediana": split_df[pred_col].median(),
                }
            )
    return pd.DataFrame(rows).sort_values(["split", "mae_dias"])


def render_report(df: pd.DataFrame) -> str:
    """Genera reporte Markdown de features rolling candidatas."""
    coverage = coverage_by_split(df)
    fallback = fallback_by_split(df)
    comparison = rolling_mae_comparison(df)
    shape_text = f"{df.shape[0]:,} filas x {df.shape[1]:,} columnas"

    lines: list[str] = []
    lines.append("# Fase 2 - Rolling features point-in-time")
    lines.append("")
    lines.append("## 1. Resumen ejecutivo")
    lines.append("")
    lines.append(
        "Se construyeron features rolling de 30 dias para regresion sobre "
        "`dias_entrega_real`, sin entrenar modelos. Rolling significa ventana "
        "movil de historia reciente: para cada orden se miran ordenes del mismo "
        "grupo cuya entrega real ya ocurrio antes de la compra actual."
    )
    lines.append("")
    lines.append(
        f"La salida local `data/processed/orders_fase2_regresion_rolling.csv` "
        f"quedo con {shape_text}. Las fechas reales de entrega se usaron solo "
        "internamente para validar que el historial estuviera cerrado; no salen "
        "en el dataset final."
    )
    lines.append("")
    lines.append("## 2. Features creadas")
    lines.append("")
    lines.append("Columnas rolling puras:")
    lines.append("")
    for col in ROLLING_PURE_COLUMNS:
        lines.append(f"- `{col}`")
    lines.append("")
    lines.append("Columnas con fallback jerarquico:")
    lines.append("")
    for col in FALLBACK_COLUMNS:
        lines.append(f"- `{col}`")
    lines.append("")
    lines.append("## 3. Definicion de cada familia")
    lines.append("")
    definitions = pd.DataFrame(
        [
            {
                "familia": "ruta_estado",
                "definicion": "Ordenes con mismo origen-destino estado en los 30 dias previos ya entregadas antes de M0.",
                "fallback": "ruta_estado -> customer_state -> mediana global train",
            },
            {
                "familia": "customer_state",
                "definicion": "Ordenes al mismo estado destino en los 30 dias previos ya entregadas antes de M0.",
                "fallback": "customer_state -> mediana global train",
            },
            {
                "familia": "categoria_principal",
                "definicion": "Ordenes de la misma categoria principal en los 30 dias previos ya entregadas antes de M0.",
                "fallback": "categoria_principal -> mediana global train",
            },
            {
                "familia": "seller_id",
                "definicion": "Ordenes del mismo seller en los 30 dias previos ya entregadas antes de M0.",
                "fallback": "seller_id -> ruta_estado -> customer_state -> mediana global train",
            },
        ]
    )
    lines.append(_format_markdown_table(definitions))
    lines.append("")
    lines.append("## 4. Cobertura por split")
    lines.append("")
    lines.append(_format_markdown_table(coverage))
    lines.append("")
    lines.append("## 5. Porcentaje de fallback por split")
    lines.append("")
    lines.append(_format_markdown_table(fallback))
    lines.append("")
    lines.append("## 6. Comparacion basica 30d por grupo")
    lines.append("")
    lines.append(
        "La siguiente tabla usa cada columna `_fallback` como regla simple de "
        "prediccion y calcula MAE. MAE significa error absoluto medio: cuantos "
        "dias se equivoca la regla en promedio. Esto no selecciona features "
        "finales; solo mide senal candidata para Chat E."
    )
    lines.append("")
    lines.append(_format_markdown_table(comparison))
    lines.append("")
    lines.append("## 7. Validaciones anti-leakage")
    lines.append("")
    lines.append("- La orden actual queda excluida porque su entrega ocurre despues de su compra.")
    lines.append("- Ordenes futuras quedan excluidas al exigir entrega real anterior a M0.")
    lines.append("- Ordenes compradas antes pero entregadas despues de M0 no aportan historial.")
    lines.append("- La ventana usa entregas cerradas dentro de los 30 dias previos a la compra.")
    lines.append("- `order_delivered_customer_date` no sale en el dataset final.")
    lines.append("- `order_delivered_carrier_date`, `dias_vs_promesa`, reviews y `entrega_tarde` no salen como features.")
    lines.append("- `seller_id` crudo se conserva solo como soporte heredado del ETL base; la feature de seller es agregada historica.")
    lines.append("")
    lines.append("## 8. Riesgos y limitaciones")
    lines.append("")
    lines.append("- El cambio de regimen R-14 sigue abierto: test es mas rapido que train.")
    lines.append("- Seller tiene menor cobertura reciente; por eso requiere conteo, flag y fallback.")
    lines.append("- Las columnas `_fallback` usan la mediana global de train como respaldo final.")
    lines.append("- La multicolinealidad entre distancia, flete, peso, volumen y `mismo_estado` debe evaluarse en Chat E.")
    lines.append("- Estas features son candidatas; todavia no hay seleccion final ni entrenamiento.")
    lines.append("")
    lines.append("## 9. Recomendacion para Chat E")
    lines.append("")
    lines.append(
        "Entrenar baselines y modelos de regresion comparando bloques: base M0, "
        "base + ruta/customer rolling, base + categoria rolling y base + seller "
        "rolling. La seleccion debe hacerse con validacion temporal y MAE en val, "
        "manteniendo las alertas de cobertura y multicolinealidad."
    )
    lines.append("")
    return "\n".join(lines)


def build_rolling_dataset(
    input_path: str | Path = DEFAULT_INPUT,
    input_dir: str | Path = DEFAULT_INPUT_DIR,
    output_path: str | Path | None = None,
    report_path: str | Path | None = None,
) -> pd.DataFrame:
    """Construye y opcionalmente guarda el dataset con rolling features."""
    input_path = Path(input_path)
    if not input_path.exists():
        raise FileNotFoundError(f"No se encontro el dataset base: {input_path}")

    dataset = pd.read_csv(input_path, parse_dates=[PURCHASE_COL])
    delivery_dates = load_delivery_dates(input_dir)
    enriched = enrich_with_delivery_dates(dataset, delivery_dates)
    rolling = add_rolling_features(enriched)
    output = clean_output_columns(rolling)

    if output_path is not None:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output.to_csv(output_path, index=False)

    if report_path is not None:
        report_path = Path(report_path)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(render_report(output), encoding="utf-8")

    return output


def run(
    input_path: str | Path = DEFAULT_INPUT,
    input_dir: str | Path = DEFAULT_INPUT_DIR,
    output_path: str | Path = DEFAULT_OUTPUT,
    report_path: str | Path = DEFAULT_REPORT,
) -> pd.DataFrame:
    """Ejecuta la construccion completa de features rolling y reporte."""
    print(f"[1/4] Leyendo dataset base: {input_path}")
    print(f"[2/4] Calculando rolling point-in-time desde: {input_dir}")
    output = build_rolling_dataset(input_path, input_dir, output_path, report_path)
    print(f"[3/4] Dataset rolling guardado: {output_path}")
    print(f"      shape: {output.shape[0]:,} x {output.shape[1]:,}")
    print(f"[4/4] Reporte guardado: {report_path}")
    print(output["split"].value_counts().reindex(SPLIT_ORDER).to_string())
    return output


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Construye rolling features point-in-time para Fase 2"
    )
    parser.add_argument("--input", default=str(DEFAULT_INPUT))
    parser.add_argument("--input-dir", default=str(DEFAULT_INPUT_DIR))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--report", default=str(DEFAULT_REPORT))
    return parser.parse_args(argv)


if __name__ == "__main__":
    args = parse_args()
    run(args.input, args.input_dir, args.output, args.report)
