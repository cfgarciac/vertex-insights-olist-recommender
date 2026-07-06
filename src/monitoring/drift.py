# -*- coding: utf-8 -*-
"""Deteccion de data drift sobre las predicciones logueadas (HU-16, D-39).

Compara la produccion (logs/predictions.jsonl, escrito por la API) contra el
baseline del train (monitoring/drift_baseline.json, generado por baseline.py):

- PSI por feature (numericas y categoricas) con umbrales 0.10 / 0.25.
- Kolmogorov-Smirnov para numericas continuas (muestra del train persistida).
- Chi-cuadrado para categoricas.
- Score drift: PSI de la prediccion del motor contra la distribucion del
  target en train, y tasa de alertas del escudo vs tasa base de tardanza.

Salida: monitoring/drift_report.json (lo consume la pestana Drift del dashboard).

Uso:
    python -m src.monitoring.drift [--logs logs/predictions.jsonl]
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LOGS = ROOT / "logs" / "predictions.jsonl"
BASELINE_PATH = ROOT / "monitoring" / "drift_baseline.json"
REPORT_PATH = ROOT / "monitoring" / "drift_report.json"

EPS = 1e-4  # suavizado para bins vacios (PSI no definido con frecuencia 0)


def calcular_psi(frec_base: np.ndarray, frec_prod: np.ndarray) -> float:
    """Population Stability Index entre dos vectores de frecuencias relativas."""
    base = np.clip(np.asarray(frec_base, dtype="float64"), EPS, None)
    prod = np.clip(np.asarray(frec_prod, dtype="float64"), EPS, None)
    base, prod = base / base.sum(), prod / prod.sum()
    return float(np.sum((prod - base) * np.log(prod / base)))


def severidad_psi(psi: float) -> str:
    if psi > 0.25:
        return "severo"
    if psi >= 0.10:
        return "moderado"
    return "ok"


ACCIONES = {
    "ok": "nada",
    "moderado": "investigar causa y aumentar frecuencia de monitoreo",
    "severo": "runbook R-14: 1) recalibrar margenes con datos recientes, 2) reentrenar con re-ventaneo",
}


def drift_numerica(nombre: str, valores: pd.Series, ref: dict) -> dict:
    bordes = np.asarray(ref["bordes"], dtype="float64")
    conteos, _ = np.histogram(valores.dropna(), bins=bordes)
    frec_prod = conteos / max(conteos.sum(), 1)
    psi = calcular_psi(ref["frecuencias"], frec_prod)
    ks = stats.ks_2samp(np.asarray(ref["muestra_ks"]), valores.dropna())
    sev = severidad_psi(psi)
    return {"feature": nombre, "tipo": "numerica", "psi": round(psi, 4),
            "ks_estadistico": round(float(ks.statistic), 4),
            "ks_pvalor": float(f"{ks.pvalue:.3e}"),
            "media_produccion": round(float(valores.mean()), 4),
            "media_train": round(float(ref["media"]), 4),
            "severidad": sev, "accion": ACCIONES[sev]}


def drift_categorica(nombre: str, valores: pd.Series, ref: dict[str, float]) -> dict:
    """PSI + Chi-cuadrado sobre las categorias del baseline (resto -> __otros__)."""
    cats = [c for c in ref if c != "__otros__"]
    vc = valores.astype(str).value_counts(normalize=True)
    frec_prod = np.array([vc.get(c, 0.0) for c in cats] + [vc[~vc.index.isin(cats)].sum()])
    frec_base = np.array([ref[c] for c in cats] + [ref.get("__otros__", 0.0)])
    psi = calcular_psi(frec_base, frec_prod)

    n = int(len(valores))
    observados = np.round(frec_prod * n).astype(int)
    esperados = np.clip(frec_base * n, 1e-6, None)
    esperados = esperados * observados.sum() / esperados.sum()  # normaliza totales
    chi2 = stats.chisquare(observados, esperados)
    sev = severidad_psi(psi)
    return {"feature": nombre, "tipo": "categorica", "psi": round(psi, 4),
            "chi2_estadistico": round(float(chi2.statistic), 2),
            "chi2_pvalor": float(f"{chi2.pvalue:.3e}"),
            "severidad": sev, "accion": ACCIONES[sev]}


def pct_imputada_por_feature(logs: pd.DataFrame) -> dict[str, float]:
    """Fraccion de requests donde cada feature vino de un lookup (flag `feat:origen`).

    Una feature mayoritariamente derivada colapsa a los valores agregados del
    lookup y su PSI contra el baseline por-orden se infla ARTIFICIALMENTE: no es
    drift de la poblacion sino de la derivacion. Se reporta aparte para no
    contaminar el veredicto (matiz documentado en estrategia_monitoreo.md).
    """
    conteo: dict[str, int] = {}
    for flags in logs["flags_imputacion"]:
        for flag in flags or []:
            feat = flag.split(":", 1)[0]
            conteo[feat] = conteo.get(feat, 0) + 1
    n = max(len(logs), 1)
    return {feat: c / n for feat, c in conteo.items()}


def generar_reporte(logs: pd.DataFrame, baseline: dict) -> dict:
    features = pd.DataFrame(list(logs["features_derivadas"]))
    pct_imputada = pct_imputada_por_feature(logs)
    resultados = []
    for nombre, ref in baseline["features_numericas"].items():
        if nombre == "dias_prometidos" and features[nombre].isna().all():
            continue  # /promise no exige la promesa vigente
        resultados.append(drift_numerica(nombre, features[nombre].astype(float), ref))
    for nombre, ref in baseline["features_categoricas"].items():
        resultados.append(drift_categorica(nombre, features[nombre], ref))

    # Features mayoritariamente derivadas: PSI inflado por el lookup, no drift real.
    for r in resultados:
        pct = pct_imputada.get(r["feature"], 0.0)
        r["pct_derivada_por_lookup"] = round(pct, 3)
        if pct > 0.5 and r["severidad"] != "ok":
            r["severidad"] = "derivada"
            r["accion"] = ("PSI inflado por derivacion de lookup (valores agregados); "
                           "no cuenta para el veredicto. Exigir el campo en el contrato "
                           "o regenerar lookups con mayor granularidad.")

    # Score drift del motor: la prediccion vive en el espacio del target de train.
    scores = {}
    pred = logs["pred_dias"].dropna() if "pred_dias" in logs else pd.Series(dtype=float)
    if len(pred):
        ref_target = baseline["scores"]["dias_entrega_real_train"]
        conteos, _ = np.histogram(pred, bins=np.asarray(ref_target["bordes"]))
        psi_score = calcular_psi(ref_target["frecuencias"], conteos / max(conteos.sum(), 1))
        scores["psi_pred_dias_vs_target_train"] = round(psi_score, 4)
        scores["severidad_score"] = severidad_psi(psi_score)
        scores["media_pred_dias"] = round(float(pred.mean()), 2)
        scores["media_target_train"] = round(float(ref_target["media"]), 2)
    if "bandera_riesgo" in logs:
        banderas = logs["bandera_riesgo"].dropna()
        if len(banderas):
            scores["tasa_alertas_escudo"] = round(float(banderas.mean()), 4)
            scores["tasa_entrega_tarde_train"] = round(
                float(baseline["scores"]["tasa_entrega_tarde_train"]), 4)

    n_sev = sum(1 for r in resultados if r["severidad"] == "severo")
    return {
        "generado": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "n_predicciones": int(len(logs)),
        "baseline_ventana": baseline["ventana_train"] | {
            "desde": baseline["ventana_train"]["desde"],
            "hasta": baseline["ventana_train"]["hasta"]},
        "resumen": {
            "features_ok": sum(1 for r in resultados if r["severidad"] == "ok"),
            "features_moderado": sum(1 for r in resultados if r["severidad"] == "moderado"),
            "features_severo": n_sev,
            "features_derivadas": sum(1 for r in resultados if r["severidad"] == "derivada"),
            "veredicto": ("DRIFT SEVERO: aplicar runbook R-14" if n_sev
                          else "sin drift accionable"),
        },
        "features": resultados,
        "scores": scores,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Reporte de drift PSI/KS/Chi2 (HU-16).")
    parser.add_argument("--logs", type=Path, default=DEFAULT_LOGS)
    args = parser.parse_args()

    if not BASELINE_PATH.exists():
        raise SystemExit("Falta el baseline: python -m src.monitoring.baseline")
    if not args.logs.exists():
        raise SystemExit(f"No hay logs en {args.logs}. Genera trafico "
                         "(API real o python -m src.monitoring.simulate_production).")

    with open(BASELINE_PATH, encoding="utf-8") as fh:
        baseline = json.load(fh)
    logs = pd.read_json(args.logs, lines=True)
    print(f"[1/2] {len(logs)} predicciones en {args.logs}")

    reporte = generar_reporte(logs, baseline)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(REPORT_PATH, "w", encoding="utf-8") as fh:
        json.dump(reporte, fh, indent=2, ensure_ascii=False)

    r = reporte["resumen"]
    print(f"[2/2] {REPORT_PATH} | ok={r['features_ok']} moderado={r['features_moderado']} "
          f"severo={r['features_severo']} derivadas={r['features_derivadas']} -> {r['veredicto']}")
    if reporte["scores"]:
        print(f"      scores: {reporte['scores']}")


if __name__ == "__main__":
    main()
