"""Genera un PDF con el resumen de la Etapa 3 (ETL + Feature Engineering) de P1.

Fuente del contenido: docs/etapas/cierre-etapa-3.md
Figuras embebidas: reports/figures_eda_etapa3/*.png (PNG a 150 dpi).
Salida: reports/etapa3_resumen.pdf
"""

from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# --- Rutas -------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[1]
FIG_DIR = ROOT / "reports" / "figures_eda_etapa3"
OUT_PDF = ROOT / "reports" / "etapa3_resumen.pdf"

# Paleta
AZUL = colors.HexColor("#1f3a5f")
AZUL_CLARO = colors.HexColor("#dde6f0")
GRIS = colors.HexColor("#555555")

# --- Estilos -----------------------------------------------------------------
styles = getSampleStyleSheet()
styles.add(
    ParagraphStyle(
        name="Portada",
        fontName="Helvetica-Bold",
        fontSize=26,
        leading=32,
        textColor=AZUL,
        alignment=TA_CENTER,
    )
)
styles.add(
    ParagraphStyle(
        name="SubPortada",
        fontName="Helvetica",
        fontSize=13,
        leading=18,
        textColor=GRIS,
        alignment=TA_CENTER,
    )
)
styles.add(
    ParagraphStyle(
        name="H1",
        fontName="Helvetica-Bold",
        fontSize=15,
        leading=19,
        textColor=AZUL,
        spaceBefore=14,
        spaceAfter=8,
    )
)
styles.add(
    ParagraphStyle(
        name="Cuerpo",
        fontName="Helvetica",
        fontSize=10.5,
        leading=15,
        alignment=TA_JUSTIFY,
        spaceAfter=6,
    )
)
styles.add(
    ParagraphStyle(
        name="Caption",
        fontName="Helvetica-Oblique",
        fontSize=9,
        leading=12,
        textColor=GRIS,
        alignment=TA_CENTER,
        spaceBefore=4,
        spaceAfter=10,
    )
)
styles.add(
    ParagraphStyle(
        name="Vinieta",
        fontName="Helvetica",
        fontSize=10.5,
        leading=15,
        leftIndent=12,
        bulletIndent=2,
        spaceAfter=4,
    )
)


def header_footer(canvas, doc):
    """Pie de página con numeración y banda de marca."""
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(GRIS)
    canvas.drawString(2 * cm, 1.1 * cm, "Vertex Insights — Proyecto Final · Etapa 3")
    canvas.drawRightString(
        A4[0] - 2 * cm, 1.1 * cm, f"Página {doc.page}"
    )
    canvas.setStrokeColor(AZUL_CLARO)
    canvas.setLineWidth(0.8)
    canvas.line(2 * cm, 1.4 * cm, A4[0] - 2 * cm, 1.4 * cm)
    canvas.restoreState()


def tabla(data, col_widths, header=True):
    """Construye una tabla con estilo de marca."""
    t = Table(data, colWidths=col_widths, hAlign="LEFT")
    estilo = [
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 9.5),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, colors.HexColor("#cfd8e3")),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, colors.HexColor("#f4f7fb")]),
    ]
    if header:
        estilo += [
            ("BACKGROUND", (0, 0), (-1, 0), AZUL),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ]
    t.setStyle(TableStyle(estilo))
    return t


def imagen_ajustada(path: Path, max_w: float, max_h: float) -> Image:
    """Escala una imagen para que quepa en el ancho/alto dado manteniendo proporción."""
    ir = ImageReader(str(path))
    iw, ih = ir.getSize()
    ratio = min(max_w / iw, max_h / ih)
    return Image(str(path), width=iw * ratio, height=ih * ratio)


# Figuras con su descripción (orden del EDA de cambios de la Etapa 3)
FIGURAS = [
    (
        "01_granularidad_universo.png",
        "Figura 1 — Granularidad y universo: del CSV consolidado a la tabla "
        "analítica a nivel orden sobre 'delivered' (96,470 órdenes etiquetables).",
    ),
    (
        "02_target_entrega_tarde.png",
        "Figura 2 — Distribución del target 'entrega_tarde': tasa base de 8.11% "
        "(problema desbalanceado).",
    ),
    (
        "03_gradiente_regional.png",
        "Figura 3 — Gradiente regional de entrega tardía: SP 5.9% vs AL 23.9% "
        "(≈4×), señal de negocio preservada tras el FE.",
    ),
    (
        "04_features_distribuciones.png",
        "Figura 4 — Distribuciones de las features [t0] construidas "
        "(importes, peso/volumen, distancia haversine, colchón de promesa).",
    ),
    (
        "05_separacion_tasa_vendedor.png",
        "Figura 5 — Tasa histórica del vendedor point-in-time (expanding, mín. 5 "
        "órdenes) con respaldo a la tasa global del train; prueba anti-fuga OK.",
    ),
    (
        "06_nulos_antes_despues.png",
        "Figura 6 — Nulos antes/después del ETL+FE: imputación con sentido de "
        "negocio; distancia haversine nula en 0.49% (unión de huecos geo).",
    ),
    (
        "07_split_temporal_regimen2018.png",
        "Figura 7 — Split temporal 70/15/15 por fecha de compra "
        "(67,529 / 14,470 / 14,471) y vigilancia del régimen 2018 (R-14).",
    ),
]


def construir_documento():
    story = []

    # ---------- Portada ----------
    story.append(Spacer(1, 5 * cm))
    story.append(Paragraph("Resumen de la Etapa 3", styles["Portada"]))
    story.append(Spacer(1, 0.3 * cm))
    story.append(
        Paragraph("Preparación de datos y Feature Engineering (P1)", styles["Portada"])
    )
    story.append(Spacer(1, 1 * cm))
    story.append(
        Paragraph(
            "Vertex Insights — Proyecto Final<br/>"
            "Fase CRISP-DM: Data Preparation · Tag V1.2.0<br/>"
            "Problema P1: predicción de entrega tardía (entrega_tarde)<br/>"
            "Fecha de cierre: 2026-06-20 · Sprint 1",
            styles["SubPortada"],
        )
    )
    story.append(Spacer(1, 2 * cm))
    story.append(
        Paragraph(
            "Líder de etapa: Data Scientist — Aguilar Lomas, Oscar Amaury",
            styles["SubPortada"],
        )
    )
    story.append(PageBreak())

    # ---------- 1. Contexto y objetivo ----------
    story.append(Paragraph("1. Contexto y objetivo", styles["H1"]))
    story.append(
        Paragraph(
            "La Etapa 3 es el corazón de la fase <b>Data Preparation</b> de CRISP-DM. "
            "Su objetivo fue convertir los hallazgos del EDA (Etapa 2) en una "
            "<b>tabla analítica modelable</b> y un <b>pipeline reproducible</b> para el "
            "problema vigente <b>P1 — predicción de entrega tardía</b> "
            "(<font face='Courier'>entrega_tarde</font>), sin reabrir el pivote ya "
            "decidido en la Etapa 2. Se entregó la tabla analítica a nivel orden con el "
            "target y las features [t0], el pipeline de preprocesamiento serializado, el "
            "split temporal sin leakage y un EDA breve que evidencia los cambios del "
            "ETL+FE. La disciplina anti-leakage (R-12) fue el eje rector de la etapa.",
            styles["Cuerpo"],
        )
    )

    # ---------- 2. Productos entregados ----------
    story.append(Paragraph("2. Productos entregados", styles["H1"]))
    productos = [
        "<b>Script reproducible de ETL + FE</b> (src/features/build_dataset.py): "
        "colapsa a nivel orden sobre 'delivered', construye target y features [t0], "
        "calcula la tasa del vendedor sin fuga y serializa el pipeline.",
        "<b>Tabla analítica de P1</b> (orders_features.csv): "
        "96,470 órdenes × 23 columnas (identificadores, split, 4 targets, features [t0]).",
        "<b>Pipeline de preprocesamiento serializado</b> (artifacts/pipeline_p1.joblib): "
        "ColumnTransformer ajustado solo en train + metadatos.",
        "<b>EDA breve de cambios</b> (notebooks/03_EDA_VERTEX.ipynb): 7 figuras "
        "antes/después exportadas a reports/figures_eda_etapa3/.",
        "<b>Documento técnico de FE</b> (docs/decisiones_fe.md): catálogo de features, "
        "ventana del vendedor, imputación, encodings, split y multicolinealidad.",
    ]
    for p in productos:
        story.append(Paragraph(f"• {p}", styles["Vinieta"]))

    # ---------- 3. Decisiones clave ----------
    story.append(Paragraph("3. Decisiones clave (bitácora)", styles["H1"]))
    dec = [
        ["ID", "Decisión"],
        ["D-22", "Fuente del FE: CSV consolidado en vez de las 9 tablas crudas."],
        ["D-23", "Granularidad a nivel orden; vendedor/producto = primer ítem; importes/peso/volumen agregados."],
        ["D-24", "Tasa del vendedor: expanding point-in-time, mín. 5 órdenes, respaldo a tasa global + flag."],
        ["D-25", "Split temporal 70/15/15 por fecha de compra."],
        ["D-26", "Imputación con sentido de negocio + pipeline serializado (ColumnTransformer)."],
    ]
    story.append(tabla(dec, col_widths=[1.6 * cm, 14.4 * cm]))

    # ---------- 4. Resultados y verificaciones ----------
    story.append(Paragraph("4. Resultados y verificaciones clave", styles["H1"]))
    res = [
        ["Métrica de la etapa", "Valor"],
        ["Órdenes en la tabla analítica (delivered, etiquetables)", "96,470"],
        ["Tasa base entrega_tarde", "8.11%"],
        ["Split temporal (train / val / test)", "67,529 / 14,470 / 14,471"],
        ["Tasa global del vendedor (respaldo, train)", "9.03%"],
        ["Órdenes sin historial suficiente del vendedor", "11.57%"],
        ["Distancia haversine nula (geo faltante, imputada)", "476 (0.49%)"],
        ["Prueba anti-fuga de la tasa del vendedor", "OK"],
        ["Sanity check regional (SP vs AL)", "5.9% vs 23.9% (≈4×)"],
    ]
    story.append(tabla(res, col_widths=[11 * cm, 5 * cm]))
    story.append(Spacer(1, 0.3 * cm))
    story.append(
        Paragraph(
            "El gradiente regional y el colchón de la promesa del EDA de la Etapa 2 se "
            "reproducen sobre las features construidas, lo que confirma que el FE "
            "preserva la señal de negocio.",
            styles["Cuerpo"],
        )
    )

    # ---------- 5. Galería de gráficas ----------
    story.append(PageBreak())
    story.append(Paragraph("5. Galería de gráficas (EDA de cambios)", styles["H1"]))
    story.append(
        Paragraph(
            "Las siguientes figuras documentan el antes/después del ETL+FE. "
            "Se exportaron en PNG a 150 dpi desde notebooks/03_EDA_VERTEX.ipynb.",
            styles["Cuerpo"],
        )
    )
    story.append(Spacer(1, 0.2 * cm))

    max_w = 16 * cm
    max_h = 10.5 * cm
    for i, (nombre, desc) in enumerate(FIGURAS):
        path = FIG_DIR / nombre
        if not path.exists():
            story.append(Paragraph(f"[Figura no encontrada: {nombre}]", styles["Caption"]))
            continue
        story.append(imagen_ajustada(path, max_w, max_h))
        story.append(Paragraph(desc, styles["Caption"]))
        # Dos figuras por página para legibilidad
        if i % 2 == 1:
            story.append(PageBreak())

    # ---------- 6. Lecciones aprendidas ----------
    story.append(PageBreak())
    story.append(Paragraph("6. Lecciones aprendidas", styles["H1"]))
    lecciones = [
        "El leakage se previene por construcción, no por revisión: la tasa del "
        "vendedor point-in-time con prueba anti-fuga automática es más fiable que "
        "auditar a posteriori.",
        "Imputar con la causa del hueco en mente: geo, vendedor nuevo y dimensiones "
        "faltantes piden estrategias distintas; un fillna(0) global habría borrado señal.",
        "Una feature derivada hereda la unión de los huecos de sus fuentes: los nulos "
        "de la distancia (0.49%) son la suma de geo cliente + vendedor.",
        "El split temporal es parte del feature engineering: la tasa global de respaldo "
        "y el preprocesador se ajustan solo en train.",
        "Reusar trabajo validado acelera sin perder rigor: partir del consolidado fue "
        "una decisión de tiempo razonable y trazable.",
    ]
    for l in lecciones:
        story.append(Paragraph(f"• {l}", styles["Vinieta"]))

    # ---------- 7. Próximos pasos ----------
    story.append(Paragraph("7. Próximos pasos — Etapa 4 (Modelado)", styles["H1"]))
    story.append(
        Paragraph(
            "La Etapa 4 arranca con la tabla analítica y el pipeline de preprocesamiento "
            "ya listos. Toma como insumo el split temporal y la disciplina anti-leakage de "
            "esta etapa. Foco: añadir el estimador al Pipeline, entrenar un baseline y "
            "modelos (regresión logística, árboles/boosting), evaluar con ROC-AUC/PR-AUC/F1 "
            "sobre el split temporal y vigilar la tasa_vendedor y el régimen 2018. "
            "Tag esperado al cierre: V1.3.0.",
            styles["Cuerpo"],
        )
    )

    return story


def main():
    OUT_PDF.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(OUT_PDF),
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        title="Resumen Etapa 3 — ETL y Feature Engineering",
        author="Vertex Insights",
    )
    doc.build(construir_documento(), onFirstPage=header_footer, onLaterPages=header_footer)
    print(f"PDF generado en: {OUT_PDF}")


if __name__ == "__main__":
    main()
