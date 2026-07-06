# -*- coding: utf-8 -*-
"""Tests del monitoreo (HU-16, D-39): PSI, severidades y vigilante R-14.

Valida con distribuciones sinteticas que el detector se comporta como exige el
criterio de aceptacion: PSI ~ 0 en distribuciones identicas, PSI > 0.25 en
desplazadas, y las alertas de performance disparan en el escenario correcto.
"""
import numpy as np
import pandas as pd
import pytest

from src.monitoring.drift import (calcular_psi, drift_categorica, drift_numerica,
                                  severidad_psi)
from src.monitoring.performance import generar_reporte


# --------------------------------------------------------------------------- #
# PSI y severidades
# --------------------------------------------------------------------------- #
def test_psi_distribuciones_identicas_es_cero():
    frec = np.array([0.1, 0.2, 0.3, 0.2, 0.2])
    assert calcular_psi(frec, frec) == pytest.approx(0.0, abs=1e-9)


def test_psi_desplazada_supera_umbral_severo():
    base = np.array([0.4, 0.3, 0.2, 0.05, 0.05])
    desplazada = np.array([0.05, 0.05, 0.2, 0.3, 0.4])
    assert calcular_psi(base, desplazada) > 0.25


def test_severidades_en_umbrales():
    assert severidad_psi(0.05) == "ok"
    assert severidad_psi(0.10) == "moderado"
    assert severidad_psi(0.25) == "moderado"
    assert severidad_psi(0.26) == "severo"


def _ref_numerica(valores: np.ndarray) -> dict:
    bordes = np.unique(np.quantile(valores, np.linspace(0, 1, 11))).astype(float)
    bordes[0], bordes[-1] = -np.inf, np.inf
    conteos, _ = np.histogram(valores, bins=bordes)
    return {"bordes": bordes.tolist(),
            "frecuencias": (conteos / conteos.sum()).tolist(),
            "muestra_ks": valores[:500].tolist(),
            "media": float(valores.mean())}


def test_drift_numerica_sin_drift_es_ok():
    rng = np.random.default_rng(1)
    train = rng.normal(10, 2, 3000)
    prod = pd.Series(rng.normal(10, 2, 1000))
    resultado = drift_numerica("x", prod, _ref_numerica(train))
    assert resultado["severidad"] == "ok"


def test_drift_numerica_detecta_desplazamiento():
    rng = np.random.default_rng(2)
    train = rng.normal(10, 2, 3000)
    prod = pd.Series(rng.normal(16, 2, 1000))  # media desplazada 3 sigmas
    resultado = drift_numerica("x", prod, _ref_numerica(train))
    assert resultado["severidad"] == "severo"
    assert resultado["psi"] > 0.25
    assert resultado["ks_pvalor"] < 0.01


def test_drift_categorica_detecta_redistribucion():
    ref = {"SP": 0.7, "BA": 0.2, "RJ": 0.1}
    prod = pd.Series(["BA"] * 70 + ["SP"] * 20 + ["RJ"] * 10)  # invertida
    resultado = drift_categorica("customer_state", prod, ref)
    assert resultado["severidad"] == "severo"


# --------------------------------------------------------------------------- #
# Performance con etiquetas diferidas (vigilante R-14)
# --------------------------------------------------------------------------- #
def _replay(pred: float, real: float, promesa: int, n: int = 100) -> pd.DataFrame:
    return pd.DataFrame({
        "pred_dias": [pred] * n,
        "dias_entrega_real": [real] * n,
        "promesa_dias": [promesa] * n,
        "bandera_riesgo": [False] * n,
        "drift_inducido": ["none"] * n,
    })


def test_performance_regimen_como_test_sin_alertas():
    # Sobre-prediccion ~ +3d (como la referencia de test) y cumplimiento alto.
    reporte = generar_reporte(_replay(pred=15.0, real=12.0, promesa=21))
    assert reporte["cumplimiento_realizado"] == 1.0
    assert reporte["sobre_prediccion_media"] == pytest.approx(3.0)
    assert reporte["alertas"] == ["sin alertas: dentro de lo esperado"]


def test_performance_subprediccion_dispara_alerta_r14():
    # El motor sub-predice (pred < real): promesas cortas -> cae cumplimiento.
    reporte = generar_reporte(_replay(pred=10.0, real=16.0, promesa=14))
    assert reporte["cumplimiento_realizado"] == 0.0
    assert reporte["sobre_prediccion_media"] == pytest.approx(-6.0)
    textos = " | ".join(reporte["alertas"])
    assert "SUB-predice" in textos
    assert "runbook R-14" in textos


def test_performance_sobreprediccion_excesiva_alerta():
    reporte = generar_reporte(_replay(pred=20.0, real=10.0, promesa=26))
    textos = " | ".join(reporte["alertas"])
    assert "duplica la referencia" in textos
