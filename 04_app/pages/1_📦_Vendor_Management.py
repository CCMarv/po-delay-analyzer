#AÑADIDO CSS
# En app.py (y en las 3 páginas de /pages)
import streamlit as st
import pandas as pd
from utils.helpers import load_css
from services.metrics_service import vendor_scorecard, culpas_injustas_vendor
from components.navbar import render_navbar


# 1. Configurar página
st.set_page_config(page_title="PO Root Cause Analyzer", layout="wide")
# 2. Inyectar CSS
load_css()

render_navbar(active_page="vendor")

"""Dashboard de Vendor Management."""

from config import (
    COL_APPT_LEAD_DAYS, COL_DELAY_DAYS, COL_EXCESS_VENDOR, COL_IS_RESCHEDULED,
    COL_IS_SHORT_SHIP, COL_SEVERITY, COL_STAGE_PRIMARY, COL_VENDOR,
)
from services.data_service import load_classified_data, get_tardios
from services.metrics_service import vendor_scorecard
from components.sidebar import render_sidebar, apply_filters
from components.metrics_cards import metric_card
from components.charts import bar_chart, scatter_chart
from components.data_tables import po_table, po_detail_expander

st.set_page_config(page_title="Vendor Management", page_icon="📦", layout="wide")

df = load_classified_data()
filters = render_sidebar(df)
df = apply_filters(df, filters)

st.title("📦 Vendor Management")
st.markdown("**STA push · short shipments · score de vendors para renegociación de SLAs**")

# ── KPIs ───────────────────────────────────────────────────────────────────
tardios = get_tardios(df)
vendor_culpa = tardios[tardios[COL_STAGE_PRIMARY] == "Vendor"]

col1, col2, col3, col4 = st.columns(4)
with col1:
    metric_card("POs totales", len(df), icon="📋")
with col2:
    metric_card("Culpa Vendor", len(vendor_culpa), icon="⚠️")
with col3:
    short = int(vendor_culpa[COL_IS_SHORT_SHIP].sum())
    metric_card("Short shipments", short, icon="📦")
with col4:
    resch = int(vendor_culpa[COL_IS_RESCHEDULED].sum())
    metric_card("Rescheduled", resch, icon="🔄")

# ── Vendor Scorecard ───────────────────────────────────────────────────────
st.subheader("🏆 Vendor Scorecard")
scorecard = vendor_scorecard(df)

if len(scorecard) > 0:
    scorecard_display = scorecard[[
        COL_VENDOR, "POs", "pct_tardios", "excess_sum_hrs",
        "short_ship", "rescheduled", "high_severity"
    ]].copy()
    scorecard_display.columns = [
        "Vendor", "POs", "% tardíos", "Excess sum (h)",
        "Short", "Resch.", "HIGH"
    ]
    st.dataframe(scorecard_display, use_container_width=True, hide_index=True)
else:
    st.info("No hay POs con culpa Vendor para los filtros seleccionados.")

# ── Gráficos ────────────────────────────────────────────────────────────────
col_g1, col_g2 = st.columns(2)

with col_g1:
    if len(scorecard) > 0:
        bar_chart(
            scorecard.sort_values("pct_tardios", ascending=False).head(10),
            x=COL_VENDOR, y="pct_tardios",
            title="% tardíos por vendor",
        )

with col_g2:
    vendor_plot = vendor_culpa[[COL_EXCESS_VENDOR, COL_APPT_LEAD_DAYS, COL_VENDOR]].dropna()
    if len(vendor_plot) > 0:
        scatter_chart(
            vendor_plot,
            x=COL_APPT_LEAD_DAYS, y=COL_EXCESS_VENDOR,
            title="Lead time vs delay real (cada punto = PO)",
            color=COL_VENDOR,
        )

# ── POs de alta severidad ───────────────────────────────────────────────────
st.subheader("🔥 POs con culpa Vendor + severidad alta")
high_vendor = vendor_culpa[vendor_culpa[COL_SEVERITY] == "HIGH"].head(10)

if len(high_vendor) > 0:
    cols_tabla = [
        "PO_NBR", COL_VENDOR, "DC_LOC_NAME", COL_SEVERITY,
        COL_EXCESS_VENDOR, COL_APPT_LEAD_DAYS, COL_IS_SHORT_SHIP,
        COL_IS_RESCHEDULED, COL_DELAY_DAYS,
    ]
    po_table(high_vendor, cols_tabla, key="vendor_high_table")

    # Drill-down
    st.markdown("---")
    st.subheader("🔍 Detalle de PO")
    selected_po = st.selectbox(
        "Selecciona un PO para ver detalle",
        options=high_vendor["PO_NBR"].tolist(),
        key="vendor_po_select",
    )
    if selected_po:
        row = high_vendor[high_vendor["PO_NBR"] == selected_po].iloc[0]
        po_detail_expander(row, title="Detalle")
else:
    st.info("No hay POs Vendor con severidad HIGH.")


# ── Defensa: culpas injustas ────────────────────────────────────────────────
st.subheader("⚖️ Defensa: culpas injustas")
culpas_vendor = culpas_injustas_vendor(df)
st.markdown(
    f"**{len(culpas_vendor)} POs** no deberían impactar el KPI del Vendor. "
    "El reason humano dice 'Vendor' pero el cómputo atribuye la culpa a Carrier o DC."
)

if len(culpas_vendor) > 0:
    cols_culpa = [
        "PO_NBR", "VENDOR_NAME", "reason_group_manual", "stage_primary",
        "excess_carrier_hrs", "excess_dc_hrs", "delay_days_calc",
    ]
    po_table(culpas_vendor, cols_culpa, key="vendor_culpas_table")
else:
    st.success("✅ No hay culpas injustas detectadas.")

