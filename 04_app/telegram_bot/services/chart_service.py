"""Generación de gráficos PNG para enviar por Telegram.

Usa Plotly para crear figuras y las exporta a PNG (requiere kaleido instalado).
Si kaleido no está disponible, falla suavemente con un mensaje de error.
"""
import io
import logging
from pathlib import Path

import pandas as pd
import plotly.express as px

from config import (
    COL_STAGE, COL_SEVERITY, COL_PO_DT, COL_LLM_COINCIDE,
    STAGE_COLORS, SEVERITY_COLORS,
)

logger = logging.getLogger(__name__)

# ── Intentar importar kaleido ──────────────────────────────────────────────
_KALEIDO_AVAILABLE = False
try:
    import plotly.io as pio
    pio.kaleido.scope.mathjax = None  # Deshabilitar MathJax (más rápido)
    _KALEIDO_AVAILABLE = True
except (ImportError, AttributeError):
    logger.warning("kaleido no disponible. Los gráficos PNG no funcionarán.")


def _fig_to_png(fig) -> bytes:
    """Convierte una figura Plotly a bytes PNG."""
    if not _KALEIDO_AVAILABLE:
        raise RuntimeError(
            "kaleido no está instalado. "
            "Ejecuta: pip install kaleido"
        )
    buf = io.BytesIO()
    fig.write_image(buf, format="png", width=800, height=400, scale=1.5)
    buf.seek(0)
    return buf.getvalue()


# ── Paleta de colores para severidad (rampa de luminancia acromática) ──────
# Fuente única: SEVERITY_COLORS (shared/data_contract.py, ARD-17). Solo se
# remapea a las claves HIGH/MEDIUM/LOW que usa el df de severidad.
SEV_COLORS = {
    "HIGH": SEVERITY_COLORS["alta"],
    "MEDIUM": SEVERITY_COLORS["media"],
    "LOW": SEVERITY_COLORS["baja"],
}


def distribucion_etapa(df: pd.DataFrame) -> bytes:
    """Gráfico de barras horizontal: distribución por etapa."""
    counts = df[COL_STAGE].value_counts().reset_index()
    counts.columns = [COL_STAGE, "count"]
    counts["label"] = counts["count"].astype(str)

    color_map = {s: STAGE_COLORS.get(str(s).lower(), "#767676")
                 for s in counts[COL_STAGE].unique()}

    fig = px.bar(
        counts, x="count", y=COL_STAGE, orientation="h",
        color=COL_STAGE, color_discrete_map=color_map,
        text="label", title="Distribución por Etapa",
    )
    fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_layout(
        showlegend=False,
        height=300,
        margin=dict(l=10, r=50, t=40, b=10),
        xaxis_title=None, yaxis_title=None,
        paper_bgcolor="white", plot_bgcolor="white",
        font=dict(size=12),
    )
    fig.update_xaxes(showgrid=False, showticklabels=False)
    fig.update_yaxes(categoryorder="total ascending")
    return _fig_to_png(fig)


def distribucion_severidad(df: pd.DataFrame) -> bytes:
    """Gráfico de barras horizontal: distribución por severidad."""
    counts = df[COL_SEVERITY].value_counts().reset_index()
    counts.columns = [COL_SEVERITY, "count"]
    counts["label"] = counts["count"].astype(str)

    fig = px.bar(
        counts, x="count", y=COL_SEVERITY, orientation="h",
        color=COL_SEVERITY, color_discrete_map=SEV_COLORS,
        text="label", title="Distribución por Severidad",
        category_orders={COL_SEVERITY: ["HIGH", "MEDIUM", "LOW"]},
    )
    fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_layout(
        showlegend=False,
        height=250,
        margin=dict(l=10, r=50, t=40, b=10),
        xaxis_title=None, yaxis_title=None,
        paper_bgcolor="white", plot_bgcolor="white",
        font=dict(size=12),
    )
    fig.update_xaxes(showgrid=False, showticklabels=False)
    fig.update_yaxes(categoryorder="array", categoryarray=["LOW", "MEDIUM", "HIGH"])
    return _fig_to_png(fig)


def tendencia_temporal(df: pd.DataFrame) -> bytes:
    """Gráfico de línea: POs tardíos por semana."""
    trend = df.dropna(subset=[COL_PO_DT]).copy()
    if trend.empty:
        raise ValueError("Sin fechas de PO válidas para tendencia.")

    trend["week"] = trend[COL_PO_DT].dt.to_period("W").dt.start_time
    weekly = trend.groupby("week").size().reset_index(name="count").sort_values("week")

    fig = px.line(
        weekly, x="week", y="count", markers=True,
        title="Tendencia Semanal — POs Tardíos",
    )
    fig.update_traces(line_color="#0072B2", marker=dict(size=8))
    fig.update_layout(
        height=320,
        margin=dict(l=10, r=40, t=40, b=30),
        xaxis_title=None, yaxis_title="POs tardíos",
        paper_bgcolor="white", plot_bgcolor="white",
        font=dict(size=12),
    )
    # Anotar el último valor
    last = weekly.iloc[-1]
    fig.add_annotation(
        x=last["week"], y=last["count"],
        text=str(int(last["count"])),
        showarrow=False, yshift=14,
        font=dict(size=13, weight="bold"),
    )
    return _fig_to_png(fig)


def desacuerdo_por_etapa(df: pd.DataFrame) -> bytes:
    """Gráfico de barras: % de desacuerdo AI vs humano por etapa."""
    dis_df = (
        df.assign(_disagree=(df[COL_LLM_COINCIDE] == False))
        .groupby(COL_STAGE)["_disagree"].mean().mul(100).reset_index()
    )
    dis_df.columns = [COL_STAGE, "rate"]
    dis_df["label"] = dis_df["rate"].map(lambda v: f"{v:.0f}%")

    color_map = {s: STAGE_COLORS.get(str(s).lower(), "#767676")
                 for s in dis_df[COL_STAGE].unique()}

    fig = px.bar(
        dis_df, x="rate", y=COL_STAGE, orientation="h",
        color=COL_STAGE, color_discrete_map=color_map,
        text="label", title="% de Desacuerdo AI vs Humano por Etapa",
    )
    fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_layout(
        showlegend=False,
        height=300,
        margin=dict(l=10, r=50, t=40, b=10),
        xaxis_title=None, yaxis_title=None,
        paper_bgcolor="white", plot_bgcolor="white",
        font=dict(size=12),
    )
    fig.update_xaxes(showgrid=False, showticklabels=False, range=[0, 100])
    fig.update_yaxes(categoryorder="total ascending")
    return _fig_to_png(fig)
