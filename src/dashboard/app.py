# -*- coding: utf-8 -*-
"""Dashboard del producto P1: promesa inteligente + escudo de riesgo (HU-15, D-39).

Modo HIBRIDO (decision abierta #1 de la arquitectura):
- Pestanas de PREDICCION -> consumen la API por HTTP (valida el contrato E2E).
- Pestanas ANALITICAS -> leen reports/ y monitoring/ con cache (datos batch).

Ejecucion local (la API debe estar viva para la pestana de alertas):
    venv/Scripts/uvicorn src.api.main:app             # terminal 1
    venv/Scripts/streamlit run src/dashboard/app.py   # terminal 2
La URL de la API se configura con la variable de entorno API_URL
(default http://localhost:8000).
"""
from __future__ import annotations

import json
import os
from datetime import date, datetime, time as dtime
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st

import sys

ROOT = Path(__file__).resolve().parents[2]
# streamlit run ejecuta el script con src/dashboard/ en sys.path (no la raiz):
# se agrega la raiz para poder importar el paquete src.
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.dashboard import scoring  # noqa: E402
# 127.0.0.1 y no localhost: en Windows, localhost intenta IPv6 primero (~2 s de
# penalidad por conexion); con IP directa + sesion keep-alive el p50 es ~30 ms.
API_URL = os.environ.get("API_URL", "http://127.0.0.1:8000")
METRICS_JSON = ROOT / "reports" / "producto_promesa_riesgo_metrics.json"
DRIFT_JSON = ROOT / "monitoring" / "drift_report.json"
PERFORMANCE_JSON = ROOT / "monitoring" / "performance_report.json"

ESTADOS_UF = ["AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA", "MG", "MS",
              "MT", "PA", "PB", "PE", "PI", "PR", "RJ", "RN", "RO", "RR", "RS", "SC",
              "SE", "SP", "TO"]
NORTE_NORDESTE = {"AC", "AM", "AP", "PA", "RO", "RR", "TO",
                  "AL", "BA", "CE", "MA", "PB", "PE", "PI", "RN", "SE"}

st.set_page_config(page_title="Vertex Olist P1 — Promesa + Riesgo", page_icon="📦",
                   layout="wide")


# --------------------------------------------------------------------------- #
# Utilidades cacheadas
# --------------------------------------------------------------------------- #
@st.cache_data(ttl=60)
def cargar_json(ruta: Path) -> dict | None:
    if not ruta.exists():
        return None
    with open(ruta, encoding="utf-8") as fh:
        return json.load(fh)


@st.cache_resource
def sesion_http() -> requests.Session:
    """Sesion con keep-alive: reutiliza la conexion TCP entre requests."""
    return requests.Session()


@st.cache_data(ttl=30)
def api_health() -> dict | None:
    try:
        r = sesion_http().get(f"{API_URL}/health", timeout=3)
        return r.json() if r.status_code == 200 else None
    except requests.RequestException:
        return None


def post_api(ruta: str, payload: dict) -> tuple[int, dict]:
    r = sesion_http().post(f"{API_URL}{ruta}", json=payload, timeout=10)
    return r.status_code, r.json()


# --------------------------------------------------------------------------- #
# Encabezado
# --------------------------------------------------------------------------- #
st.title("📦 Vertex Insights — Olist P1")
st.caption("Promesa inteligente (motor Fase 2) + escudo de riesgo (Fase 1) · D-38/D-39 · "
           "política y umbrales provisionales, pendientes del PO (Fase 0)")

salud = api_health()
if salud:
    st.success(f"API conectada en `{API_URL}` · modelo `{salud['model_version']}` · "
               f"política **{salud['politica']}** · umbral v2 {salud['escudo_umbral_v2']}", icon="✅")
else:
    st.warning(f"API no disponible en `{API_URL}`. Levántala con "
               "`venv/Scripts/uvicorn src.api.main:app` (la pestaña de alertas la necesita; "
               "las analíticas funcionan igual).", icon="⚠️")

tab_alertas, tab_csv, tab_region, tab_metricas, tab_drift = st.tabs(
    ["🚨 Alertas de riesgo", "📁 Scoring por CSV", "🗺️ Promesa por región",
     "📊 Métricas del modelo", "📈 Drift"]
)

# --------------------------------------------------------------------------- #
# 1. Alertas de riesgo (consume la API)
# --------------------------------------------------------------------------- #
with tab_alertas:
    st.subheader("Simulador de órdenes: promesa recomendada + riesgo")
    with st.form("form_orden"):
        c1, c2, c3, c4 = st.columns(4)
        precio = c1.number_input("Precio total (BRL)", min_value=0.01, value=134.97)
        flete = c2.number_input("Flete total (BRL)", min_value=0.0, value=18.50)
        n_items = c3.number_input("N.º de ítems", min_value=1, value=1, step=1)
        customer_state = c4.selectbox("Estado del cliente", ESTADOS_UF, index=ESTADOS_UF.index("BA"))
        c5, c6, c7 = st.columns(3)
        fecha = c5.date_input("Fecha de compra", value=date(2018, 7, 10))
        hora = c6.time_input("Hora", value=dtime(14, 30))
        dias_prometidos = c7.number_input("Promesa vigente de Olist (días)", min_value=1.0, value=24.0,
                                          help="Feature [t0] del escudo; requerida para el riesgo.")
        with st.expander("Datos opcionales (si Olist los conoce, mejoran la precisión)"):
            o1, o2, o3 = st.columns(3)
            seller_state = o1.selectbox("Estado del vendedor", ["(derivar)"] + ESTADOS_UF)
            categoria = o2.text_input("Categoría principal", value="")
            peso = o3.number_input("Peso total (g)", min_value=0.0, value=0.0)
        enviado = st.form_submit_button("Consultar promesa y riesgo", type="primary")

    if enviado:
        if not salud:
            st.error("La API no está disponible: no se puede simular.")
        else:
            payload = {
                "precio_total": precio, "flete_total": flete, "n_items": int(n_items),
                "customer_state": customer_state,
                "timestamp": datetime.combine(fecha, hora).isoformat(),
            }
            if seller_state != "(derivar)":
                payload["seller_state"] = seller_state
            if categoria.strip():
                payload["categoria_principal"] = categoria.strip()
            if peso > 0:
                payload["peso_total_g"] = peso

            code_p, promesa = post_api("/promise", payload)
            code_r, riesgo = post_api("/predict/delivery-risk",
                                      {**payload, "dias_prometidos": dias_prometidos,
                                       "incluir_v1": True})
            if code_p != 200 or code_r != 200:
                st.error(f"API respondió {code_p}/{code_r}: {promesa if code_p != 200 else riesgo}")
            else:
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Predicción del motor", f"{promesa['pred_dias']:.1f} días")
                m2.metric(f"Promesa recomendada ({promesa['politica']})",
                          f"{promesa['promesa_dias']} días",
                          delta=f"{promesa['promesa_dias'] - dias_prometidos:+.0f} vs vigente",
                          delta_color="inverse")
                m3.metric("P(tarde) — escudo v2", f"{riesgo['p_tarde']:.1%}",
                          delta="🚩 ALERTA" if riesgo["bandera_riesgo"] else "sin alerta",
                          delta_color="inverse" if riesgo["bandera_riesgo"] else "off")
                v1 = riesgo.get("escudo_v1")
                if v1:
                    m4.metric("P(tarde) — escudo v1 (vs vigente)", f"{v1['p_tarde']:.1%}",
                              delta="🚩" if v1["bandera_riesgo"] else "ok",
                              delta_color="inverse" if v1["bandera_riesgo"] else "off")
                if riesgo["bandera_riesgo"]:
                    st.error("El escudo marca esta orden como riesgosa incluso con la promesa nueva: "
                             "priorizar en operación (despacho/carrier) o comunicar proactivamente.",
                             icon="🚨")
                else:
                    st.success("Orden dentro del riesgo tolerado para la promesa recomendada.", icon="👍")
                flags = promesa["flags_imputacion"]
                if flags:
                    st.caption("Features derivadas por el servidor: " + ", ".join(f"`{f}`" for f in flags))

# --------------------------------------------------------------------------- #
# 2. Scoring por CSV (batch, via la API — misma via que el simulador)
# --------------------------------------------------------------------------- #
with tab_csv:
    st.subheader("Puntuar un lote de órdenes desde CSV")
    st.markdown(
        "Sube un CSV con las columnas del **contrato** "
        "([docs/contrato_api.md](https://github.com/cfgarciac/vertex-insights-olist-recommender/blob/developer/docs/contrato_api.md)): "
        f"obligatorias `{'`, `'.join(scoring.COLUMNAS_OBLIGATORIAS)}`; "
        "opcionales p. ej. `dias_prometidos` (necesaria para el riesgo), `seller_state`, "
        "`categoria_principal`. Lo que falte lo deriva el servidor y queda flaggeado."
    )
    st.download_button(
        "⬇️ Descargar plantilla de ejemplo (3 órdenes)",
        data=scoring.PLANTILLA.to_csv(index=False).encode("utf-8"),
        file_name="plantilla_scoring_p1.csv", mime="text/csv",
    )
    archivo = st.file_uploader("CSV de órdenes", type=["csv"],
                               help=f"Máximo {scoring.LIMITE_FILAS} filas (el demo puntúa fila a fila por la API).")
    if archivo is not None:
        try:
            lote = pd.read_csv(archivo)
        except Exception as exc:
            st.error(f"No se pudo leer el CSV: {exc}")
            lote = None
        if lote is not None:
            problemas = scoring.validar_csv(lote)
            errores_bloqueantes = [p for p in problemas if not p.startswith("Columnas ignoradas")]
            for p in problemas:
                (st.error if p in errores_bloqueantes else st.warning)(p)
            st.dataframe(lote.head(10), use_container_width=True, hide_index=True)
            if not errores_bloqueantes:
                if not salud:
                    st.error("La API no está disponible: no se puede puntuar el lote.")
                elif st.button(f"Puntuar {len(lote)} órdenes", type="primary"):
                    barra = st.progress(0.0, text="Puntuando vía la API…")
                    resultados = scoring.puntuar_lote(
                        lote, post_api,
                        al_progresar=lambda f: barra.progress(f, text=f"Puntuando… {f:.0%}"),
                    )
                    barra.empty()
                    n_err = resultados["error"].notna().sum() if "error" in resultados else 0
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Órdenes puntuadas", len(resultados) - n_err)
                    c2.metric("Promesa P90 promedio",
                              f"{resultados['promesa_P90_dias'].mean():.1f} d")
                    if "alerta_riesgo" in resultados:
                        c3.metric("Alertas del escudo", f"{resultados['alerta_riesgo'].mean():.1%}")
                    if n_err:
                        c4.metric("Filas con error", int(n_err))
                    st.dataframe(resultados, use_container_width=True, hide_index=True)
                    st.download_button(
                        "⬇️ Descargar resultados (CSV)",
                        data=resultados.to_csv(index=False).encode("utf-8"),
                        file_name="resultados_scoring_p1.csv", mime="text/csv",
                    )

# --------------------------------------------------------------------------- #
# 3. Promesa por región (analítica: metrics JSON)
# --------------------------------------------------------------------------- #
with tab_region:
    st.subheader("Política P90 vs promesa actual por estado (split test)")
    metrics = cargar_json(METRICS_JSON)
    if not metrics:
        st.info("No hay métricas en reports/. Ejecuta `python -m src.models.producto_promesa_riesgo`.")
    else:
        reg = pd.DataFrame(metrics["politicas_por_region"])
        reg = reg[reg["politica"].isin(["actual_olist", "P90"])]
        reg["region"] = reg["customer_state"].map(
            lambda s: "Norte/Nordeste" if s in NORTE_NORDESTE else "Resto")
        foco = st.toggle("Foco Norte/Nordeste (donde la promesa actual falla más)", value=True)
        vista = reg[reg["region"] == "Norte/Nordeste"] if foco else reg

        fig = px.bar(vista, x="customer_state", y="cumplimiento", color="politica",
                     barmode="group", text_auto=".1%",
                     labels={"cumplimiento": "Cumplimiento", "customer_state": "Estado",
                             "politica": "Política"},
                     color_discrete_map={"actual_olist": "#9aa8b3", "P90": "#0a6f7a"})
        fig.update_layout(yaxis_tickformat=".0%", legend_title=None, height=420)
        st.plotly_chart(fig, use_container_width=True)

        fig2 = px.bar(vista, x="customer_state", y="promesa_promedio", color="politica",
                      barmode="group", text_auto=".1f",
                      labels={"promesa_promedio": "Promesa promedio (días)",
                              "customer_state": "Estado", "politica": "Política"},
                      color_discrete_map={"actual_olist": "#9aa8b3", "P90": "#0a6f7a"})
        fig2.update_layout(legend_title=None, height=420)
        st.plotly_chart(fig2, use_container_width=True)
        st.caption("Lectura: en la mayoría de estados P90 sube el cumplimiento con promesas iguales "
                   "o más cortas que las vigentes; el detalle completo está en "
                   "reports/producto_promesa_riesgo.md.")

# --------------------------------------------------------------------------- #
# 3. Métricas del modelo (analítica: metrics JSON)
# --------------------------------------------------------------------------- #
with tab_metricas:
    st.subheader("Resultados en test (una sola evaluación, D-38)")
    metrics = cargar_json(METRICS_JSON)
    if not metrics:
        st.info("No hay métricas en reports/.")
    else:
        pol = pd.DataFrame(metrics["politicas_test"])
        actual = pol[pol["politica"] == "actual_olist"].iloc[0]
        p90 = pol[pol["politica"] == "P90"].iloc[0]
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Cumplimiento P90", f"{p90['cumplimiento']:.2%}",
                  delta=f"{p90['cumplimiento'] - actual['cumplimiento']:+.2%} vs actual")
        c2.metric("Promesa promedio P90", f"{p90['promesa_promedio']:.2f} d",
                  delta=f"{p90['promesa_promedio'] - actual['promesa_promedio']:+.2f} d vs actual",
                  delta_color="inverse")
        mae_test = metrics["motor_mae"]["test"]
        c3.metric("MAE del motor (test)", f"{mae_test['mae']:.2f} d",
                  help=f"Bias medio test: {mae_test['bias_mean']:+.2f} d (R-14)")
        sin_v2 = next(s for s in metrics["sinergia"]
                      if s["escudo"] == "bandera_riesgo_v2" and s["promesa"] == "promesa_P90")
        c4.metric("Escudo v2: fallos capturados", f"{sin_v2['pct_incumplidas_marcadas_por_escudo']:.1%}",
                  help=f"Alertando {sin_v2['pct_alertas_split']:.1%} del split "
                       f"(lift ≈ {sin_v2['pct_incumplidas_marcadas_por_escudo']/sin_v2['pct_alertas_split']:.2f}x)")

        st.divider()
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=pol["promesa_promedio"], y=pol["cumplimiento"], mode="markers+text",
            text=pol["politica"], textposition="top center",
            marker=dict(size=14, color=["#9aa8b3", "#86949d", "#0a6f7a", "#2bb8c6", "#c9542f"]),
        ))
        fig.update_layout(
            title="Frontera cumplimiento vs longitud de promesa (test)",
            xaxis_title="Promesa promedio (días)", yaxis_title="Cumplimiento",
            yaxis_tickformat=".1%", height=460,
        )
        st.plotly_chart(fig, use_container_width=True)
        st.caption("P90 domina a la promesa actual: más cumplimiento (96.70% vs 94.32%) con promesa "
                   "más corta (17.87 vs 19.12 días). El escudo v2 defiende esa promesa capturando "
                   "47.6% de los incumplimientos residuales alertando 34.7% de las órdenes.")

# --------------------------------------------------------------------------- #
# 4. Drift (analítica: monitoring/)
# --------------------------------------------------------------------------- #
with tab_drift:
    st.subheader("Monitoreo de drift (HU-16)")
    drift = cargar_json(DRIFT_JSON)
    if not drift:
        st.info("Aún no hay reporte de drift. Genera tráfico y córrelo:\n\n"
                "`python -m src.monitoring.simulate_production` (replay del test contra la API)\n\n"
                "`python -m src.monitoring.drift` (PSI/KS/Chi² contra el baseline del train)")
    else:
        st.caption(f"Reporte generado: {drift['generado']} · ventana analizada: "
                   f"{drift['n_predicciones']} predicciones · baseline: train "
                   f"({drift['baseline_ventana']['desde']} → {drift['baseline_ventana']['hasta']})")
        tabla = pd.DataFrame(drift["features"])
        orden_sev = {"severo": 0, "moderado": 1, "derivada": 2, "ok": 3}
        tabla = tabla.sort_values(by="severidad", key=lambda s: s.map(orden_sev))
        sev_color = {"ok": "#2f8f66", "moderado": "#b57518", "severo": "#c24329",
                     "derivada": "#86949d"}

        n_sev = (tabla["severidad"] == "severo").sum()
        n_mod = (tabla["severidad"] == "moderado").sum()
        c1, c2, c3 = st.columns(3)
        c1.metric("Features vigiladas", len(tabla))
        c2.metric("Drift moderado", int(n_mod))
        c3.metric("Drift severo", int(n_sev))
        if n_sev:
            st.error(f"{n_sev} feature(s) con PSI > 0.25 → aplicar runbook R-14 "
                     "(1º recalibrar márgenes, 2º reentrenar). Ver docs/estrategia_monitoreo.md.", icon="🚨")
        st.info(
            "**Cómo leer este drift (producción simulada):** el baseline es el train completo "
            "(sep 2016 → abr 2018, 12 meses) y la producción simulada es el período de test "
            "(jun–ago 2018, 3 meses). Por eso `mes_compra` sale severo (estacionalidad de la "
            "ventana, no fallo del modelo) y `dias_prometidos`/`flete_total` reflejan el **drift "
            "real de régimen R-14** documentado (Olist acortó promesas). Las barras grises "
            "(`derivada`) son features imputadas por lookup y se excluyen del veredicto. "
            "**La decisión de actuar no la da este PSI solo**: se cruza con el cumplimiento "
            "realizado de abajo — si sigue ≥95%, los márgenes P90 están absorbiendo el drift.",
            icon="📖",
        )

        fig = px.bar(tabla, x="psi", y="feature", orientation="h", color="severidad",
                     color_discrete_map=sev_color,
                     labels={"psi": "PSI", "feature": ""}, height=520)
        fig.add_vline(x=0.10, line_dash="dash", line_color="#b57518")
        fig.add_vline(x=0.25, line_dash="dash", line_color="#c24329")
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(tabla, use_container_width=True, hide_index=True)

        perf = cargar_json(PERFORMANCE_JSON)
        if perf:
            st.divider()
            st.subheader("Cumplimiento realizado (etiquetas diferidas ~30 d)")
            c1, c2, c3 = st.columns(3)
            c1.metric("Cumplimiento realizado", f"{perf['cumplimiento_realizado']:.2%}",
                      delta=f"{perf['cumplimiento_realizado'] - perf['cumplimiento_esperado']:+.2%} vs esperado")
            c2.metric("MAE del motor en producción", f"{perf['mae_produccion']:.2f} d")
            c3.metric("Sobre-predicción media (pred − real)", f"{perf['sobre_prediccion_media']:+.2f} d",
                      delta=f"ref. test {perf['sobre_prediccion_test_referencia']:+.2f} d",
                      delta_color="off",
                      help="Vigilante R-14: si cae hacia 0 o se invierte, las promesas "
                           "quedan cortas — recalibrar márgenes antes de que caiga el cumplimiento.")
            for alerta in perf.get("alertas", []):
                if not alerta.startswith("sin alertas"):
                    st.warning(alerta, icon="⚠️")
