# -*- coding: utf-8 -*-
"""Esquemas Pydantic del contrato de la API (HU-13, docs/contrato_api.md).

La validacion estricta convierte cualquier payload invalido en un 422
automatico, sin tocar el modelo.
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class OrdenBase(BaseModel):
    """Campos [CLI] del contrato + overrides opcionales [SRV]."""

    # Obligatorios [CLI]
    precio_total: float = Field(gt=0, description="Total de productos del pedido (BRL).",
                                examples=[134.97])
    flete_total: float = Field(ge=0, description="Flete cotizado (BRL).", examples=[18.5])
    n_items: int = Field(ge=1, description="Items del carrito.", examples=[1])
    customer_state: str = Field(min_length=2, max_length=2,
                                description="UF del cliente (ej. BA, SP).", examples=["BA"])
    timestamp: datetime = Field(description="Momento de la compra (ISO 8601).",
                                examples=["2018-07-10T14:30:00"])

    # Opcionales: si Olist los conoce mejoran la precision; si faltan se derivan.
    seller_state: str | None = Field(default=None, min_length=2, max_length=2)
    categoria_principal: str | None = None
    peso_total_g: float | None = Field(default=None, gt=0)
    volumen_total_cm3: float | None = Field(default=None, gt=0)
    dist_haversine_km: float | None = Field(default=None, ge=0)
    tasa_vendedor: float | None = Field(default=None, ge=0, le=1)
    sin_historial_vendedor: int | None = Field(default=None, ge=0, le=1)

    @field_validator("customer_state", "seller_state")
    @classmethod
    def _mayusculas(cls, v: str | None) -> str | None:
        return v.upper() if isinstance(v, str) else v


class PromesaRequest(OrdenBase):
    """Request de /promise: el motor NO usa dias_prometidos (decision Fase 2)."""


class RiesgoRequest(OrdenBase):
    """Request de /predict/delivery-risk: el escudo exige la promesa vigente."""

    dias_prometidos: float | None = Field(
        default=None, gt=0,
        description="Promesa VIGENTE de Olist en dias (feature [t0] del escudo). Obligatoria.",
        examples=[24],
    )
    incluir_v1: bool = Field(
        default=False,
        description="Si true, incluye tambien el escudo v1 (riesgo vs promesa vigente).",
    )


class PromesaResponse(BaseModel):
    pred_dias: float = Field(description="Dias de entrega predichos por el motor.")
    promesa_dias: int = Field(description="Promesa recomendada: max(ceil(pred + margen), 1).")
    politica: str
    margenes_val: dict[str, float]
    flags_imputacion: list[str]
    model_version: str


class EscudoV1(BaseModel):
    p_tarde: float
    bandera_riesgo: bool
    umbral: float


class RiesgoResponse(BaseModel):
    p_tarde: float = Field(description="P(entrega tarde vs promesa P90), escudo v2 calibrado.")
    bandera_riesgo: bool
    umbral: float
    escudo: str = "v2"
    escudo_v1: EscudoV1 | None = None
    flags_imputacion: list[str]
    model_version: str


class HealthResponse(BaseModel):
    status: str
    model_version: str
    motor_feature_set: str
    politica: str
    escudo_umbral_v1: float
    escudo_umbral_v2: float
    lookups_nivel: str
    nota: str
