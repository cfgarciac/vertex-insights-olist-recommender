"""Modelado de P1 — clasificación de entrega tardía (Etapa 4).

Reúne el baseline, los clasificadores y las utilidades de evaluación que
consumen la tabla analítica y el preprocesador construidos en la Etapa 3
(`src/features/build_dataset.py`). Mantiene la disciplina anti-leakage: solo
features [t0], split temporal de la Etapa 3 y preprocesador ajustado en train.
"""
