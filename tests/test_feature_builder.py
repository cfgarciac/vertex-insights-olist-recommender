# -*- coding: utf-8 -*-
"""Tests del contrato de serving (D-39): feature_builder + candado anti-divergencia.

El test de contrato es la salvaguarda central de la arquitectura: si alguien
cambia las features del modelo o del builder, esto rompe ANTES de llegar a
produccion.
"""
import pytest

from src.serving.feature_builder import FeatureBuilder

REQUEST_MINIMO = {
    "precio_total": 100.0,
    "flete_total": 15.0,
    "n_items": 2,
    "customer_state": "BA",
    "timestamp": "2018-07-10T14:30:00",
    "dias_prometidos": 20.0,
}


@pytest.fixture()
def builder(lookups_sinteticos) -> FeatureBuilder:
    return FeatureBuilder(lookups_sinteticos)


def test_contrato_cubre_features_del_modelo(builder, bundle_sintetico):
    """Candado: las columnas construidas cubren motor_features y las del escudo."""
    fila, _ = builder.construir(REQUEST_MINIMO)
    FeatureBuilder.validar_contrato(fila, bundle_sintetico)  # no lanza


def test_contrato_detecta_divergencia(builder, bundle_sintetico):
    fila, _ = builder.construir(REQUEST_MINIMO)
    bundle_roto = dict(bundle_sintetico)
    bundle_roto["motor_features"] = bundle_sintetico["motor_features"] + ["feature_inexistente"]
    with pytest.raises(ValueError, match="feature_inexistente"):
        FeatureBuilder.validar_contrato(fila, bundle_roto)


def test_request_minimo_imputa_y_flaggea(builder):
    fila, flags = builder.construir(REQUEST_MINIMO)
    # seller_state y categoria no vinieron -> modal del manifest, flaggeados.
    assert fila.loc[0, "seller_state"] == "SP"
    assert "seller_state:modal_train" in flags
    assert "categoria_principal:modal_train" in flags
    # peso/volumen desde el catalogo por categoria (cat_a: 500 g/item x 2 items).
    assert fila.loc[0, "peso_total_g"] == pytest.approx(1000.0)
    assert "peso_total_g:catalogo_categoria" in flags
    # distancia por par (BA, SP) del lookup sintetico.
    assert fila.loc[0, "dist_haversine_km"] == pytest.approx(1200.0)
    assert "dist_haversine_km:par_estados" in flags


def test_overrides_del_cliente_no_se_flaggean(builder):
    completo = {
        **REQUEST_MINIMO,
        "seller_state": "MG",
        "categoria_principal": "cat_b",
        "peso_total_g": 750.0,
        "volumen_total_cm3": 5000.0,
        "dist_haversine_km": 320.0,
        "tasa_vendedor": 0.11,
        "sin_historial_vendedor": 0,
    }
    fila, flags = builder.construir(completo)
    assert flags == []
    assert fila.loc[0, "peso_total_g"] == pytest.approx(750.0)
    assert fila.loc[0, "dist_haversine_km"] == pytest.approx(320.0)


def test_derivaciones_aritmeticas_y_calendario(builder):
    fila, _ = builder.construir(REQUEST_MINIMO)
    assert fila.loc[0, "ratio_flete"] == pytest.approx(15.0 / 100.0)
    # 2018-07-10 fue martes -> dayofweek 1 (convencion lunes=0 del dataset).
    assert fila.loc[0, "mes_compra"] == 7
    assert fila.loc[0, "dia_semana_compra"] == 1
    # seller imputado SP != customer BA -> mismo_estado 0.
    assert fila.loc[0, "mismo_estado"] == 0


def test_mismo_estado_cuando_coinciden(builder):
    fila, _ = builder.construir({**REQUEST_MINIMO, "customer_state": "SP", "seller_state": "SP"})
    assert fila.loc[0, "mismo_estado"] == 1


def test_faltan_obligatorios_lanza_error(builder):
    incompleto = {k: v for k, v in REQUEST_MINIMO.items() if k != "precio_total"}
    with pytest.raises(ValueError, match="precio_total"):
        builder.construir(incompleto)


def test_estado_desconocido_cae_a_fallbacks(builder):
    fila, flags = builder.construir({**REQUEST_MINIMO, "customer_state": "TO",
                                     "seller_state": "AM"})
    # (TO, AM) no esta en el lookup ni TO como estado -> fallback global.
    assert fila.loc[0, "dist_haversine_km"] == pytest.approx(450.0)
    assert "dist_haversine_km:global_train" in flags
    # AM tampoco tiene stats -> prior global + sin_historial=1.
    assert fila.loc[0, "tasa_vendedor"] == pytest.approx(0.056)
    assert "tasa_vendedor:prior_global" in flags
    assert fila.loc[0, "sin_historial_vendedor"] == 1
