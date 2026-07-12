# -*- coding: utf-8 -*-
"""Monitoreo de performance con etiquetas diferidas — el vigilante de R-14 (HU-16, D-39).

En produccion real, `dias_entrega_real` se conoce ~30 dias despues de cada
compra: este modulo simula ese join diferido leyendo
monitoring/replay_resultados.csv (generado por simulate_production.py, que une
la prediccion servida por la API con el ground truth de cada orden).

Vigila las tres senales que el PSI de las features NO ve:
1. Cumplimiento realizado vs esperado (96.70% de P90 en test, D-38).
2. MAE del motor en produccion.
3. SOBRE-PREDICCION media (pred − real, convencion `bias_mean` del repo,
   evaluate_fase2_regresion.py): en test el motor sobre-predice +3.17d (regimen
   R-14: el presente es mas rapido que el train) y los margenes lo absorben.
   Si la sobre-prediccion CAE hacia 0 o se invierte, las promesas quedan cortas
   y el cumplimiento se derrumba ANTES de que el PSI de features lo delate.

Salida: monitoring/performance_report.json (pestana Drift del dashboard).

Uso:
    python -m src.monitoring.performance
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REPLAY = ROOT / "monitoring" / "replay_resultados.csv"
REPORT_PATH = ROOT / "monitoring" / "performance_report.json"

# Esperados del cierre D-38 (test, politica P90) y disparadores D-39.
CUMPLIMIENTO_ESPERADO = 0.9670
UMBRAL_CUMPLIMIENTO = 0.95           # disparador: cumplimiento < 95% en la ventana
SOBRE_PREDICCION_REFERENCIA = 3.17   # bias_mean test (pred - real), regimen R-14


def generar_reporte(replay: pd.DataFrame) -> dict:
    cumplidas = (replay["dias_entrega_real"] <= replay["promesa_dias"])
    # Convencion del repo (evaluate_fase2_regresion.bias_mean): pred - real.
    sobre_pred = replay["pred_dias"] - replay["dias_entrega_real"]
    incumplidas = ~cumplidas

    # Sinergia del escudo en produccion: de las ordenes que INCUMPLIERON la
    # promesa, cuantas habia marcado la bandera (y cuanto alerta en total).
    captura_escudo = (
        float(replay.loc[incumplidas, "bandera_riesgo"].mean()) if incumplidas.any() else None
    )

    cumplimiento = float(cumplidas.mean())
    mae = float(sobre_pred.abs().mean())
    sobre_prediccion = float(sobre_pred.mean())

    alertas = []
    if cumplimiento < UMBRAL_CUMPLIMIENTO:
        alertas.append(f"cumplimiento {cumplimiento:.2%} < {UMBRAL_CUMPLIMIENTO:.0%}: "
                       "runbook R-14 (1. recalibrar margenes, 2. reentrenar)")
    if sobre_prediccion < 0:
        alertas.append("el motor SUB-predice (pred < real): las promesas quedan cortas; "
                       "recalibrar margenes YA y evaluar reentrenamiento (R-14 invertido)")
    elif sobre_prediccion < SOBRE_PREDICCION_REFERENCIA / 2:
        alertas.append("la sobre-prediccion cayo a menos de la mitad de la referencia de "
                       "test (+3.17d): el colchon implicito se esta agotando; vigilar de cerca")
    elif sobre_prediccion > 2 * SOBRE_PREDICCION_REFERENCIA:
        alertas.append("la sobre-prediccion duplica la referencia de test: promesas "
                       "infladas innecesariamente; recalibrar margenes con datos recientes")

    return {
        "generado": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "n_ordenes_con_etiqueta": int(len(replay)),
        "drift_inducido": str(replay["drift_inducido"].iloc[0]) if len(replay) else "none",
        "cumplimiento_realizado": round(cumplimiento, 4),
        "cumplimiento_esperado": CUMPLIMIENTO_ESPERADO,
        "mae_produccion": round(mae, 2),
        "sobre_prediccion_media": round(sobre_prediccion, 2),
        "sobre_prediccion_test_referencia": SOBRE_PREDICCION_REFERENCIA,
        "tasa_alertas_escudo": round(float(replay["bandera_riesgo"].mean()), 4),
        "captura_incumplidas_por_escudo": (round(captura_escudo, 4)
                                           if captura_escudo is not None else None),
        "alertas": alertas or ["sin alertas: dentro de lo esperado"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Performance con etiquetas diferidas (R-14).")
    parser.add_argument("--replay", type=Path, default=DEFAULT_REPLAY)
    args = parser.parse_args()

    if not args.replay.exists():
        raise SystemExit(f"No existe {args.replay}. "
                         "Ejecuta antes: python -m src.monitoring.simulate_production")
    replay = pd.read_csv(args.replay)
    print(f"[1/2] {len(replay)} ordenes con etiqueta en {args.replay}")

    reporte = generar_reporte(replay)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(REPORT_PATH, "w", encoding="utf-8") as fh:
        json.dump(reporte, fh, indent=2, ensure_ascii=False)

    print(f"[2/2] {REPORT_PATH}")
    print(f"      cumplimiento={reporte['cumplimiento_realizado']:.2%} "
          f"(esperado {reporte['cumplimiento_esperado']:.2%}) | "
          f"MAE={reporte['mae_produccion']:.2f}d | "
          f"sobre-prediccion={reporte['sobre_prediccion_media']:+.2f}d "
          f"(ref test {reporte['sobre_prediccion_test_referencia']:+.2f}d)")
    for alerta in reporte["alertas"]:
        print(f"      -> {alerta}")


if __name__ == "__main__":
    main()
