"""Baselines de P1 (entrega tardía) — piso de comparación de la Etapa 4.

La guía exige un baseline trivial que fije el piso: todo modelo debe superarlo
en PR-AUC/recall para justificar su complejidad (etapa_4_guia §2.3). Se proveen
dos, complementarios:

  1. `BaselineClaseMayoritaria` — predice siempre la clase mayoritaria (a tiempo)
     con probabilidad constante = tasa base. Da el piso de discriminación
     (ROC-AUC ≈ 0.5, PR-AUC ≈ tasa base).
  2. `BaselineReglaDistanciaEstado` — la regla de negocio "larga distancia +
     distinto estado = tarde". Usa la distancia (mediana de train como corte) y
     `mismo_estado` como score de riesgo interpretable.

Ambos son compatibles con la API de scikit-learn (`fit`/`predict`/
`predict_proba`) y operan sobre las columnas crudas de la tabla analítica, sin
preprocesador (son referencias triviales, no modelos productivos).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, ClassifierMixin


class BaselineClaseMayoritaria(BaseEstimator, ClassifierMixin):
    """Predice la clase mayoritaria; `predict_proba` devuelve la tasa base."""

    def fit(self, X, y):
        y = np.asarray(y)
        self.tasa_base_ = float(np.mean(y))
        self.clase_mayoritaria_ = int(self.tasa_base_ >= 0.5)
        self.classes_ = np.array([0, 1])
        return self

    def predict_proba(self, X) -> np.ndarray:
        n = len(X)
        p1 = np.full(n, self.tasa_base_)
        return np.column_stack([1 - p1, p1])

    def predict(self, X) -> np.ndarray:
        return np.full(len(X), self.clase_mayoritaria_, dtype=int)


class BaselineReglaDistanciaEstado(BaseEstimator, ClassifierMixin):
    """Regla de negocio: riesgo alto si la distancia es grande y el vendedor
    está en otro estado.

    El score de riesgo combina la distancia (normalizada por su mediana de
    train) y el flag `mismo_estado`, de forma que sea ordenable para PR/ROC-AUC
    y, a la vez, produzca una decisión 0/1 interpretable.
    """

    def __init__(self, col_dist: str = "dist_haversine_km", col_mismo: str = "mismo_estado"):
        self.col_dist = col_dist
        self.col_mismo = col_mismo

    def fit(self, X: pd.DataFrame, y=None):
        self.mediana_dist_ = float(np.nanmedian(X[self.col_dist]))
        self.classes_ = np.array([0, 1])
        return self

    def _score(self, X: pd.DataFrame) -> np.ndarray:
        dist = X[self.col_dist].fillna(self.mediana_dist_).to_numpy(dtype=float)
        # Riesgo creciente con la distancia (acotado en [0,1) y monótono).
        score_dist = dist / (dist + self.mediana_dist_ + 1e-9)
        otro_estado = (X[self.col_mismo].to_numpy() == 0).astype(float)
        # Mezcla interpretable: la distancia manda, el cruce de estado suma.
        return np.clip(0.7 * score_dist + 0.3 * otro_estado, 0.0, 1.0)

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        p1 = self._score(X)
        return np.column_stack([1 - p1, p1])

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        # Regla dura: distancia por encima de la mediana Y vendedor en otro estado.
        dist = X[self.col_dist].fillna(self.mediana_dist_).to_numpy(dtype=float)
        otro_estado = X[self.col_mismo].to_numpy() == 0
        return ((dist > self.mediana_dist_) & otro_estado).astype(int)
