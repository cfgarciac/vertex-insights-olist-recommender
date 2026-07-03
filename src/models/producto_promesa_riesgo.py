"""Producto conjunto de P1 — "Promesa inteligente + escudo de riesgo" (unión Fase 1 + Fase 2).

Une los dos modelos del equipo en un solo producto, según la propuesta acordada
con el PO (`propuesta_solucion_conjunta_P1.md`) y las decisiones D-31 (escudo,
Fase 1) y D-33 a D-36 (motor de promesa, Fase 2 de Harrison):

  MOTOR  (Fase 2) — regresión de `dias_entrega_real` (Random Forest, Chat E) +
                    márgenes P80/P90/P95 calculados SOLO en `val` (backtesting
                    Chat F). Propone una promesa honesta y competitiva.
  ESCUDO (Fase 1) — `artifacts/modelo_riesgo_p1.joblib`: P(entrega tarde) calibrada
                    (regresión de `dias_vs_promesa` + isotónica). Marca las órdenes
                    en riesgo para intervención operativa.
  UNIÓN            — además de las políticas puras, una **política mixta por
                    riesgo**: margen P80 (competitivo) para órdenes sin bandera y
                    P95 (conservador) para órdenes en riesgo. El escudo también se
                    audita como "red de seguridad": ¿qué fracción de los fallos
                    residuales de la promesa nueva estaba marcada?

Los dos modelos quedan ligados por la identidad
`dias_vs_promesa = dias_entrega_real − dias_prometidos`.

Datos (con degradación controlada, sin romper la selección de Chat E):
  - Si existe `data/processed/orders_fase2_regresion_rolling.csv` → bloque
    `M0_mas_seller_rolling` (candidato ganador, D-35).
  - Si no (el CSV rolling no se versiona) → bloque `M0_base_sin_rolling`
    (2º de Chat E; MAE val 4.593 vs 4.553) sobre `orders_features.csv`,
    reconstruyendo `ruta_estado = seller_state_customer_state`.
  - La promesa actual y las features del escudo salen SIEMPRE de
    `orders_features.csv` (`dias_prometidos_actual = ceil(dias_prometidos) ≥ 1`,
    misma definición que el backtesting de Fase 2).

Salidas:
  - reports/producto_promesa_riesgo.md (+ producto_promesa_riesgo_metrics.json)
  - reports/figures_producto_promesa_riesgo/*.png
  - reports/predicciones_promesa_riesgo.csv (tabla por orden; regenerable)
  - artifacts/producto_promesa_riesgo.joblib (motor + márgenes + escudo + metadatos)

Ejecución:
    python -m src.models.producto_promesa_riesgo
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import joblib
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.models import backtest_promesas_fase2 as bt  # noqa: E402
from src.models import evaluate as ev_f1  # noqa: E402
from src.models import evaluate_fase2_regresion as ev_f2  # noqa: E402
from src.models import train_fase2_regresion as train_f2  # noqa: E402

# --------------------------------------------------------------------------- #
# 0. Contrato del producto
# --------------------------------------------------------------------------- #
TARGET = ev_f2.TARGET  # dias_entrega_real
CURRENT_PROMISE_COL = bt.CURRENT_PROMISE_COL  # dias_prometidos_actual
POLITICA_RECOMENDADA = "P90"  # D-36 (candidata preliminar de Fase 2)
ESCUDO_PUNTO = "recall_obj_70"  # punto de operación del escudo (D-31)
MEZCLA = {"sin_riesgo": "P80", "con_riesgo": "P95"}  # política mixta por riesgo

DATA_ROLLING = ROOT / "data" / "processed" / "orders_fase2_regresion_rolling.csv"
DATA_BASE = ROOT / "data" / "processed" / "orders_features.csv"
ESCUDO_ARTIFACT = ROOT / "artifacts" / "modelo_riesgo_p1.joblib"

ARTIFACT = ROOT / "artifacts" / "producto_promesa_riesgo.joblib"
REPORTS = ROOT / "reports"
FIG_DIR = REPORTS / "figures_producto_promesa_riesgo"
REPORT_MD = REPORTS / "producto_promesa_riesgo.md"
METRICS_JSON = REPORTS / "producto_promesa_riesgo_metrics.json"
PREDICCIONES_CSV = REPORTS / "predicciones_promesa_riesgo.csv"

# Paleta validada (dataviz): familia P80/P90/P95 = rampa azul (secuencial),
# promesa actual = gris neutro (referencia), política mixta = naranja (identidad).
AZUL_RAMPA = {"P80": "#6baed6", "P90": "#3182bd", "P95": "#08519c"}
GRIS_REF = "#6b7280"
NARANJA_MIXTA = "#E69F00"
TINTA = "#333333"


# --------------------------------------------------------------------------- #
# 1. Carga de datos (motor con fallback controlado + insumos del escudo)
# --------------------------------------------------------------------------- #
def cargar_datos() -> tuple[pd.DataFrame, str]:
    """Devuelve (df del producto, nombre del bloque de features del motor).

    El df incluye: soporte (order_id, split, ts, ruta_estado, customer_state),
    target del motor, promesa actual y las features de motor y escudo.
    """
    base = pd.read_csv(DATA_BASE, parse_dates=["order_purchase_timestamp"])
    faltan = {TARGET, "dias_prometidos", "split", "order_id"} - set(base.columns)
    if faltan:
        raise ValueError(f"Faltan columnas en {DATA_BASE}: {sorted(faltan)}")
    # Promesa actual de Olist: misma definición que el backtesting de Fase 2.
    base[CURRENT_PROMISE_COL] = (
        np.maximum(np.ceil(base["dias_prometidos"]), 1).astype("int64")
    )
    base["ruta_estado"] = (
        base["seller_state"].fillna("NA") + "_" + base["customer_state"].fillna("NA")
    )

    if DATA_ROLLING.exists():
        rolling = train_f2.load_dataset(DATA_ROLLING)
        feature_set = "M0_mas_seller_rolling"  # candidato ganador (D-35)
        extras = [c for c in rolling.columns if c not in base.columns] + ["order_id"]
        df = base.merge(rolling[extras], on="order_id", how="inner")
    else:
        feature_set = "M0_base_sin_rolling"  # 2º de Chat E (Δ MAE val 0.04)
        df = base

    features = list(train_f2.FEATURE_SETS[feature_set])
    ev_f2.assert_no_forbidden_features(features)  # candado Fase 2 (sin fuga)
    faltan = set(features) - set(df.columns)
    if faltan:
        raise ValueError(f"Faltan features del bloque {feature_set}: {sorted(faltan)}")
    return df, feature_set


# --------------------------------------------------------------------------- #
# 2. Motor de promesa (Fase 2, reutilizado)
# --------------------------------------------------------------------------- #
def entrenar_motor(df: pd.DataFrame, feature_set: str):
    """Entrena el candidato de Chat E (Random Forest) SOLO con train."""
    features = list(train_f2.FEATURE_SETS[feature_set])
    modelo = train_f2.build_model_candidates(features)[bt.SELECTED_MODEL]
    train = df[df["split"] == "train"]
    modelo.fit(train[features], train[TARGET])
    return modelo, features


def predecir_y_prometer(df: pd.DataFrame, modelo, features: list[str]) -> tuple[pd.DataFrame, dict]:
    """Predice días, calcula márgenes P80/P90/P95 en `val` y simula promesas."""
    out = df.copy()
    out["prediccion_dias"] = train_f2.clipped_predict(modelo, out[features])
    margenes = bt.calculate_residual_margins(out[out["split"] == "val"])
    out = bt.add_simulated_promises(out, margenes)
    return out, margenes


# --------------------------------------------------------------------------- #
# 3. Escudo de riesgo (Fase 1, reutilizado)
# --------------------------------------------------------------------------- #
def aplicar_escudo(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Añade P(tarde) calibrada y bandera de riesgo del escudo (D-31)."""
    bundle = joblib.load(ESCUDO_ARTIFACT)
    x_cols = bundle["numeric_features"] + bundle["categorical_features"]
    ev_f1.assert_sin_features_post(x_cols)  # candado Fase 1 (R-12)
    proba = bundle["calibrador_isotonic"].predict(
        bundle["modelo_regresion"].predict(df[x_cols])
    )
    umbral = float(bundle["puntos_operacion"][ESCUDO_PUNTO]["umbral"])
    out = df.copy()
    out["prob_riesgo_tarde"] = np.round(proba, 4)
    out["bandera_riesgo"] = (proba >= umbral).astype(int)
    return out, {"bundle": bundle, "umbral": umbral, "punto": ESCUDO_PUNTO}


# --------------------------------------------------------------------------- #
# 4. La UNIÓN: política mixta por riesgo + sinergia del escudo
# --------------------------------------------------------------------------- #
def agregar_politica_mixta(df: pd.DataFrame, margenes: dict) -> pd.DataFrame:
    """Promesa mixta: margen P80 sin bandera, P95 con bandera (por orden)."""
    out = df.copy()
    m_bajo = margenes[MEZCLA["sin_riesgo"]]
    m_alto = margenes[MEZCLA["con_riesgo"]]
    margen = np.where(out["bandera_riesgo"] == 1, m_alto, m_bajo)
    out["promesa_mixta_riesgo"] = np.maximum(
        np.ceil(out["prediccion_dias"].to_numpy(dtype="float64") + margen), 1
    ).astype("int64")
    return out

def entrenar_escudo_v2(df: pd.DataFrame, escudo_bundle: dict, recall_objetivo: float = 0.70) -> tuple[pd.DataFrame, dict]:
    """Escudo v2: reentrena el clasificador de riesgo CONTRA LA PROMESA NUEVA.

    El escudo v1 fue calibrado contra la promesa vigente de Olist y no transfiere
    a la promesa simulada (sus fallos residuales son órdenes distintas). Gracias a
    la identidad `dias_vs_promesa = dias_entrega_real − dias_prometidos`, basta
    redefinir el target: `tarde_v2 = dias_entrega_real > promesa_P90` y reusar las
    mismas 16 features [t0] y la misma familia (XGBoost, spec de la Etapa 4).
    Umbral por recall objetivo en `val`; `test` una sola vez.
    """
    from xgboost import XGBClassifier  # import local: opcional para el resto del módulo

    x_cols = escudo_bundle["numeric_features"] + escudo_bundle["categorical_features"]
    ev_f1.assert_sin_features_post(x_cols)
    out = df.copy()
    out["tarde_vs_promesa_nueva"] = (
        out[TARGET] > out[f"promesa_{POLITICA_RECOMENDADA}"]
    ).astype(int)

    train = out[out["split"] == "train"]
    val = out[out["split"] == "val"]
    y_tr, y_va = train["tarde_vs_promesa_nueva"].values, val["tarde_vs_promesa_nueva"].values
    spw = float((y_tr == 0).sum()) / max(int((y_tr == 1).sum()), 1)

    from src.features.build_dataset import build_preprocessor
    from sklearn.pipeline import Pipeline as SkPipeline

    clf = SkPipeline([
        ("prep", build_preprocessor()),
        ("clf", XGBClassifier(
            n_estimators=400, max_depth=4, learning_rate=0.05, subsample=0.9,
            colsample_bytree=0.9, reg_lambda=2.0, min_child_weight=5,
            scale_pos_weight=spw, eval_metric="aucpr", tree_method="hist",
            n_jobs=-1, random_state=42,
        )),
    ])
    clf.fit(train[x_cols], y_tr)
    proba_va = clf.predict_proba(val[x_cols])[:, 1]
    umbral = ev_f1.umbral_para_recall(y_va, proba_va, recall_objetivo)
    out["prob_riesgo_v2"] = np.round(clf.predict_proba(out[x_cols])[:, 1], 4)
    out["bandera_riesgo_v2"] = (out["prob_riesgo_v2"] >= umbral).astype(int)
    return out, {"modelo": clf, "umbral": float(umbral), "recall_objetivo": recall_objetivo}


def sinergia_escudo(df: pd.DataFrame, promesa_col: str, split: str = "test",
                    bandera_col: str = "bandera_riesgo", proba_col: str = "prob_riesgo_tarde") -> dict:
    """Audita el escudo como red de seguridad de una promesa simulada."""
    d = df[df["split"] == split]
    incumplida = d[TARGET] > d[promesa_col]
    if int(incumplida.sum()) == 0:
        return {"promesa": promesa_col, "escudo": bandera_col, "incumplidas": 0}
    marcadas = d.loc[incumplida, bandera_col].mean()
    return {
        "promesa": promesa_col,
        "escudo": bandera_col,
        "incumplidas": int(incumplida.sum()),
        "pct_incumplidas_marcadas_por_escudo": float(marcadas),
        "prob_media_incumplidas": float(d.loc[incumplida, proba_col].mean()),
        "prob_media_cumplidas": float(d.loc[~incumplida, proba_col].mean()),
        "pct_alertas_split": float(d[bandera_col].mean()),
    }


def evaluar_politicas(df: pd.DataFrame, split: str = "test") -> list[dict]:
    """Promesa actual + P80/P90/P95 + mixta, con las métricas de Fase 2."""
    d = df[df["split"] == split]
    cols = {"actual_olist": CURRENT_PROMISE_COL}
    cols.update({p: f"promesa_{p}" for p in bt.POLICY_QUANTILES})
    cols["mixta_riesgo"] = "promesa_mixta_riesgo"
    return [
        {"split": split, "politica": p, **bt.promise_metrics(d, c)}
        for p, c in cols.items()
    ]


# --------------------------------------------------------------------------- #
# 5. Figuras (paleta validada; etiquetas directas; un solo eje)
# --------------------------------------------------------------------------- #
def _guardar(fig, nombre: str) -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG_DIR / nombre, dpi=150, bbox_inches="tight")
    plt.close(fig)


def fig_tradeoff(politicas: list[dict]) -> None:
    """Trade-off: promesa promedio (x) vs cumplimiento (y), por política."""
    colores = {**AZUL_RAMPA, "actual_olist": GRIS_REF, "mixta_riesgo": NARANJA_MIXTA}
    etiquetas = {"actual_olist": "Olist actual", "mixta_riesgo": "Mixta por riesgo (unión)"}
    fig, ax = plt.subplots(figsize=(8, 5.5))
    for fila in politicas:
        p = fila["politica"]
        x, y = fila["promesa_promedio"], fila["cumplimiento"] * 100
        ax.scatter(x, y, s=110, color=colores[p], zorder=3,
                   edgecolor="white", linewidth=1.5)
        ax.annotate(f"{etiquetas.get(p, p)}\n{x:.1f} d · {y:.1f}%",
                    (x, y), textcoords="offset points", xytext=(10, -4),
                    fontsize=8.5, color=TINTA)
    ax.set(xlabel="Promesa promedio (días) — menor es más competitiva",
           ylabel="Cumplimiento (%) — mayor es más confiable",
           title="Trade-off por política de promesa (test)")
    ax.grid(alpha=0.25)
    _guardar(fig, "01_tradeoff_politicas.png")


def fig_region(df: pd.DataFrame) -> None:
    """Cumplimiento por región: actual vs P90 vs mixta (test)."""
    d = df[df["split"] == "test"].copy()
    d["region"] = d["customer_state"].map(ev_f1.ESTADO_A_REGION).fillna("Otro")
    filas = []
    for region, g in d.groupby("region"):
        if region == "Otro" or len(g) < 100:
            continue
        filas.append({
            "region": region,
            "Olist actual": (g[TARGET] <= g[CURRENT_PROMISE_COL]).mean() * 100,
            f"{POLITICA_RECOMENDADA}": (g[TARGET] <= g[f"promesa_{POLITICA_RECOMENDADA}"]).mean() * 100,
            "Mixta por riesgo": (g[TARGET] <= g["promesa_mixta_riesgo"]).mean() * 100,
        })
    t = pd.DataFrame(filas).sort_values("Olist actual")
    x = np.arange(len(t)); w = 0.27
    fig, ax = plt.subplots(figsize=(9.5, 5.2))
    series = [("Olist actual", GRIS_REF), (POLITICA_RECOMENDADA, AZUL_RAMPA["P90"]),
              ("Mixta por riesgo", NARANJA_MIXTA)]
    for i, (nombre, color) in enumerate(series):
        vals = t[nombre].to_numpy()
        ax.bar(x + (i - 1) * w, vals, w * 0.92, label=nombre, color=color)
        for xi, v in zip(x + (i - 1) * w, vals):
            ax.text(xi, v + 0.4, f"{v:.0f}", ha="center", fontsize=7.5, color=TINTA)
    ax.set_xticks(x, t["region"], fontsize=9)
    ax.set(ylabel="Cumplimiento (%)", ylim=(0, 104),
           title=f"Cumplimiento por región (test): promesa actual vs {POLITICA_RECOMENDADA} vs mixta")
    ax.legend(fontsize=8, loc="lower right")
    ax.grid(axis="y", alpha=0.25)
    _guardar(fig, "02_cumplimiento_por_region.png")


def fig_sinergia(df: pd.DataFrame, sin_v1: dict, sin_v2: dict) -> None:
    """Dos paneles: el escudo v1 no transfiere a la promesa nueva; el v2 sí.

    Cada panel compara la P(riesgo) de las órdenes que CUMPLEN vs INCUMPLEN la
    promesa P90 en test. Si las distribuciones se separan, el escudo detecta los
    fallos residuales de la promesa nueva.
    """
    d = df[df["split"] == "test"]
    incumplida = d[TARGET] > d[f"promesa_{POLITICA_RECOMENDADA}"]
    paneles = [
        ("prob_riesgo_tarde", sin_v1, "Escudo v1 — calibrado a la promesa VIGENTE (no transfiere)"),
        ("prob_riesgo_v2", sin_v2, "Escudo v2 — reentrenado contra la promesa P90 (sí separa)"),
    ]
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.6))
    for ax, (col, s, titulo) in zip(axes, paneles):
        bins = np.linspace(0, max(0.4, float(d[col].max())), 32)
        ax.hist(d.loc[~incumplida, col], bins=bins, density=True,
                color=AZUL_RAMPA["P90"], alpha=0.35, label="Cumplidas bajo P90")
        ax.hist(d.loc[incumplida, col], bins=bins, density=True,
                histtype="step", linewidth=2.2, color=NARANJA_MIXTA,
                label="Incumplidas bajo P90 (fallos residuales)")
        pct = s.get("pct_incumplidas_marcadas_por_escudo", float("nan")) * 100
        alertas = s.get("pct_alertas_split", float("nan")) * 100
        ax.set_title(f"{titulo}\ncaptura {pct:.0f}% de fallos alertando {alertas:.0f}%",
                     fontsize=9.5)
        ax.set(xlabel="P(riesgo)", ylabel="Densidad")
        ax.legend(fontsize=8)
        ax.grid(alpha=0.25)
    fig.suptitle("La unión en acción: el escudo debe defender LA MISMA promesa que fija el motor (test)",
                 fontsize=11.5, y=1.0)
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    _guardar(fig, "03_escudo_sinergia.png")


# --------------------------------------------------------------------------- #
# 6. Reporte
# --------------------------------------------------------------------------- #
def escribir_reporte(salida: dict) -> None:
    L = []
    L.append("# Producto conjunto P1 — Promesa inteligente + escudo de riesgo\n")
    L.append("## Vertex Insights — unión Fase 1 (escudo) + Fase 2 (motor)\n")
    L.append(f"**Generado:** {salida['generado']}  ")
    L.append(f"**Motor:** {bt.SELECTED_MODEL} · bloque `{salida['feature_set']}`"
             f"{' (fallback sin rolling: CSV de Fase 2 no disponible; Δ MAE val ≈ 0.04 vs bloque ganador)' if salida['fallback_sin_rolling'] else ''}  ")
    L.append(f"**Escudo:** `artifacts/modelo_riesgo_p1.joblib` @ `{ESCUDO_PUNTO}`  ")
    L.append(f"**Política recomendada:** {POLITICA_RECOMENDADA} (D-36) · **Unión:** política mixta "
             f"({MEZCLA['sin_riesgo']} sin bandera / {MEZCLA['con_riesgo']} con bandera)\n")
    L.append("Los dos modelos quedan ligados por `dias_vs_promesa = dias_entrega_real − dias_prometidos`. "
             "Márgenes calculados SOLO en `val`; `test` se evalúa una sola vez (D-25).\n")

    L.append("## 1. MAE del motor por split (trazabilidad)\n")
    L.append(bt.to_markdown(pd.DataFrame(salida["motor_mae"]).T.reset_index()
                            .rename(columns={"index": "split"})))
    L.append("")
    L.append("## 2. Políticas de promesa en test\n")
    L.append(bt.to_markdown(salida["politicas_test"]))
    L.append("")
    L.append(f"Ver `figures_producto_promesa_riesgo/01_tradeoff_politicas.png` "
             f"y `02_cumplimiento_por_region.png`.")
    L.append("")
    L.append("## 3. Sinergia del escudo (la unión en acción)\n")
    for s in salida["sinergia"]:
        if s.get("incumplidas", 0):
            L.append(f"- Bajo `{s['promesa']}` con `{s.get('escudo','bandera_riesgo')}`: "
                     f"**{s['incumplidas']:,}** fallos residuales; el escudo marcaba el "
                     f"**{s['pct_incumplidas_marcadas_por_escudo']*100:.1f}%** "
                     f"(prob media incumplidas {s['prob_media_incumplidas']:.3f} vs "
                     f"cumplidas {s['prob_media_cumplidas']:.3f}; alertas {s['pct_alertas_split']*100:.1f}%).")
    L.append("")
    L.append("**Hallazgo clave de la unión:** el escudo v1 (calibrado contra la promesa VIGENTE) "
             "**no transfiere** a la promesa nueva — sus fallos residuales son órdenes distintas. "
             "Gracias a la identidad `dias_vs_promesa = dias_entrega_real − dias_prometidos`, el "
             "**escudo v2** se reentrena contra `promesa_P90` con las mismas 16 features [t0] y la "
             "misma familia (XGBoost) y **sí separa y captura los fallos residuales**. El producto "
             "final = promesa P90 del motor + escudo v2 defendiéndola + escudo v1 vigilando la "
             "promesa actual durante la transición. Ver `03_escudo_sinergia.png`.\n")
    L.append("## 4. Artefactos\n")
    L.append("- `artifacts/producto_promesa_riesgo.joblib` — motor + márgenes + escudo + metadatos.")
    L.append("- `reports/predicciones_promesa_riesgo.csv` — tabla por orden "
             "(`eta_dias`, promesas simuladas, `prob_riesgo_tarde`, `bandera_riesgo`); regenerable.")
    L.append("- Métricas: `reports/producto_promesa_riesgo_metrics.json`.\n")
    L.append("## 5. Límites honestos\n")
    L.append("- El motor sobreestima días por el cambio de régimen (R-14); los márgenes en `val` "
             "(régimen reciente) absorben parte del sesgo, y el redondeo `ceil` conserva promesas enteras.")
    L.append("- El escudo v1 defiende la promesa VIGENTE; el v2 (incluido aquí) defiende la P90. La "
             "calibración fina del v2 y la elección de su punto de operación con el PO son de la Etapa 6.")
    L.append("- El target del escudo v2 usa predicciones in-sample del motor en `train` (levemente "
             "optimistas); la evaluación en `test` sigue siendo end-to-end honesta. Refinar con "
             "predicciones out-of-fold es mejora futura.")
    L.append("- La elección final de política (P80/P90/P95/mixta) es del negocio (PO), con costos reales.\n")
    L.append("*Reproducible con `python -m src.models.producto_promesa_riesgo` (D-38).*")

    REPORT_MD.write_text("\n".join(L), encoding="utf-8")


# --------------------------------------------------------------------------- #
# 7. Orquestación
# --------------------------------------------------------------------------- #
def run() -> dict:
    print("[1/6] Cargando datos del producto (motor + escudo) ...")
    df, feature_set = cargar_datos()
    fallback = feature_set == "M0_base_sin_rolling"
    print(f"      filas={len(df):,}  bloque motor={feature_set}"
          f"{'  (fallback sin rolling)' if fallback else ''}")

    print("[2/6] Entrenando MOTOR de promesa (Fase 2, solo train) ...")
    modelo, features = entrenar_motor(df, feature_set)
    df, margenes = predecir_y_prometer(df, modelo, features)
    print(f"      margenes val: " + ", ".join(f"{k}={v:.2f}d" for k, v in margenes.items()))
    motor_mae = ev_f2.evaluate_predictions_by_split(df, "prediccion_dias", target=TARGET)

    print("[3/6] Aplicando ESCUDO de riesgo (Fase 1) ...")
    df, escudo = aplicar_escudo(df)
    print(f"      punto={ESCUDO_PUNTO} umbral={escudo['umbral']:.4f} "
          f"alertas(test)={df.loc[df.split=='test','bandera_riesgo'].mean()*100:.1f}%")

    print("[4/6] UNIÓN: política mixta, escudo v2 (contra la promesa nueva) y sinergia ...")
    df = agregar_politica_mixta(df, margenes)
    politicas_test = evaluar_politicas(df, "test")
    df, escudo_v2 = entrenar_escudo_v2(df, escudo["bundle"])
    sin_v1 = sinergia_escudo(df, f"promesa_{POLITICA_RECOMENDADA}")
    sin_v2 = sinergia_escudo(df, f"promesa_{POLITICA_RECOMENDADA}",
                             bandera_col="bandera_riesgo_v2", proba_col="prob_riesgo_v2")
    sinergia = [sin_v1, sin_v2, sinergia_escudo(df, "promesa_mixta_riesgo")]
    for fila in politicas_test:
        print(f"      {fila['politica']:14s} cumplimiento={fila['cumplimiento']*100:5.2f}%  "
              f"promesa_prom={fila['promesa_promedio']:5.2f}d")
    print(f"      escudo v1 -> captura {sin_v1['pct_incumplidas_marcadas_por_escudo']*100:.1f}% "
          f"de fallos P90 (alertando {sin_v1['pct_alertas_split']*100:.1f}%)")
    print(f"      escudo v2 -> captura {sin_v2['pct_incumplidas_marcadas_por_escudo']*100:.1f}% "
          f"de fallos P90 (alertando {sin_v2['pct_alertas_split']*100:.1f}%)")

    print("[5/6] Figuras y reporte ...")
    fig_tradeoff(politicas_test)
    fig_region(df)
    fig_sinergia(df, sin_v1, sin_v2)

    salida = {
        "generado": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "feature_set": feature_set,
        "fallback_sin_rolling": fallback,
        "politica_recomendada": POLITICA_RECOMENDADA,
        "escudo_punto": ESCUDO_PUNTO,
        "margenes_val": margenes,
        "motor_mae": motor_mae,
        "politicas_test": politicas_test,
        "politicas_por_region": bt.evaluate_by_group(df, "customer_state", "test", min_n=100),
        "sinergia": sinergia,
    }
    escribir_reporte(salida)
    METRICS_JSON.write_text(json.dumps(salida, ensure_ascii=False, indent=2, default=float),
                            encoding="utf-8")

    print("[6/6] Serializando producto y tabla por orden ...")
    ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {
            "tarea": "producto_promesa_riesgo (motor Fase 2 + escudo Fase 1)",
            "motor": modelo, "motor_features": features, "motor_feature_set": feature_set,
            "margenes_val": margenes, "politica_recomendada": POLITICA_RECOMENDADA,
            "mezcla_riesgo": MEZCLA,
            "escudo": escudo["bundle"], "escudo_punto": ESCUDO_PUNTO,
            "escudo_umbral": escudo["umbral"],
            "escudo_v2_modelo": escudo_v2["modelo"], "escudo_v2_umbral": escudo_v2["umbral"],
            "escudo_v2_target": f"{TARGET} > promesa_{POLITICA_RECOMENDADA}",
            "target_motor": TARGET, "promesa_actual_col": CURRENT_PROMISE_COL,
            "generado": salida["generado"],
        },
        ARTIFACT,
    )
    cols_out = ["order_id", "split", "prediccion_dias", CURRENT_PROMISE_COL,
                *(f"promesa_{p}" for p in bt.POLICY_QUANTILES),
                "promesa_mixta_riesgo", "prob_riesgo_tarde", "bandera_riesgo",
                "prob_riesgo_v2", "bandera_riesgo_v2"]
    df[cols_out].to_csv(PREDICCIONES_CSV, index=False, encoding="utf-8")
    print(f"      artefacto -> {ARTIFACT}")
    print(f"      reporte   -> {REPORT_MD}")
    print(f"      tabla     -> {PREDICCIONES_CSV}")
    return salida


def parse_args():
    return argparse.ArgumentParser(
        description="Producto conjunto P1: promesa inteligente + escudo de riesgo"
    ).parse_args()


if __name__ == "__main__":
    parse_args()
    run()
