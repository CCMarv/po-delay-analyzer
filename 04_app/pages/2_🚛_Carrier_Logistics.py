#AÑADIDO CSS
# En app.py (y en las 3 páginas de /pages)
import streamlit as st
from utils.helpers import load_css
from services.metrics_service import culpas_injustas_carrier
from components.navbar import render_navbar

# 1. Configurar página
st.set_page_config(page_title="PO Root Cause Analyzer", layout="wide")
# 2. Inyectar CSS
load_css()

render_navbar(active_page="carrier")


"""Dashboard de Carrier Logistics."""

from config import (
    COL_CARRIER, COL_CARRIER_MEDIBLE, COL_DELAY_DAYS, COL_EXCESS_CARRIER,
    COL_IS_RESCHEDULED, COL_SEVERITY, COL_STAGE_PRIMARY,
)
from services.data_service import load_classified_data, get_tardios
from services.metrics_service import carrier_scorecard, carrier_miss_por_dc
from components.sidebar import render_sidebar, apply_filters
from components.metrics_cards import metric_card
from components.charts import bar_chart, heatmap
from components.data_tables import po_table, po_detail_expander

st.set_page_config(page_title="Carrier Logistics", page_icon="🚛", layout="wide")

df = load_classified_data()
filters = render_sidebar(df)
df = apply_filters(df, filters)

st.title("🚛 Carrier Logistics")
st.markdown("**Carrier miss · appointment adherence · visibilidad de trailers**")

# ── KPIs ────────────────────────────────────────────────────────────────────
tardios = get_tardios(df)
carrier_culpa = tardios[tardios[COL_STAGE_PRIMARY] == "Carrier"]
sin_datos = tardios[tardios[COL_CARRIER_MEDIBLE] == False]

col1, col2, col3, col4 = st.columns(4)
with col1:
    metric_card("POs totales", len(df), icon="📋")
with col2:
    metric_card("Carrier miss", len(carrier_culpa), icon="🚛")
with col3:
    metric_card("Etapa primaria", len(carrier_culpa), icon="")
with col4:
    metric_card("⚠️ Sin datos", len(sin_datos), icon="❓")

# ── Carrier Scorecard ───────────────────────────────────────────────────────
st.subheader("🏆 Carrier Scorecard")
scorecard = carrier_scorecard(df)

if len(scorecard) > 0:
    scorecard_display = scorecard[[
        COL_CARRIER, "POs", "pct_miss", "excess_sum_hrs", "rescheduled"
    ]].copy()
    scorecard_display.columns = [
        "Carrier", "POs", "% miss", "Excess sum (h)", "Resch."
    ]
    st.dataframe(scorecard_display, use_container_width=True, hide_index=True)
else:
    st.info("No hay POs con culpa Carrier para los filtros seleccionados.")

# ── Gráficos ────────────────────────────────────────────────────────────────
col_g1, col_g2 = st.columns(2)

with col_g1:
    if len(scorecard) > 0:
        bar_chart(
            scorecard.sort_values("excess_sum_hrs", ascending=False).head(10),
            x=COL_CARRIER, y="excess_sum_hrs",
            title="Excess carrier (h)",
        )

with col_g2:
    heatmap_df = carrier_miss_por_dc(df)
    if len(heatmap_df) > 0:
        heatmap(heatmap_df, title="Carrier miss por DC (%)", x_title="DC", y_title="Carrier")

# ── Visibilidad ────────────────────────────────────────────────────────────
st.subheader("📡 Visibilidad: trailers sin hora de llegada")
st.markdown(f"**⚠️ {len(sin_datos)} POs** sin `TRAILER_ARRIVE_DT` → no se puede juzgar al carrier.")

if len(sin_datos) > 0:
    visibilidad = (
        sin_datos
        .groupby(COL_CARRIER)
        .size()
        .reset_index(name="POs sin llegada")
        .sort_values("POs sin llegada", ascending=False)
    )
    st.dataframe(visibilidad, use_container_width=True, hide_index=True)


# ── Defensa: culpas injustas ────────────────────────────────────────────────
st.subheader("⚖️ Defensa: culpas injustas")
culpas_carrier = culpas_injustas_carrier(df)
st.markdown(
    f"**{len(culpas_carrier)} POs** no deberían impactar el KPI del Carrier. "
    "El reason humano dice 'Carrier' pero el cómputo atribuye la culpa a Vendor o DC."
)

if len(culpas_carrier) > 0:
    cols_culpa = [
        "PO_NBR", "CARRIER_PARTY_NAME", "reason_group_manual", "stage_primary",
        "excess_vendor_hrs", "excess_dc_hrs", "delay_days_calc",
    ]
    po_table(culpas_carrier, cols_culpa, key="carrier_culpas_table")
else:
    st.success("✅ No hay culpas injustas detectadas.")


# ── POs de alta severidad ───────────────────────────────────────────────────
st.subheader("🔥 POs con carrier miss + severidad alta")
high_carrier = carrier_culpa[carrier_culpa[COL_SEVERITY] == "HIGH"].head(10)

if len(high_carrier) > 0:
    cols_tabla = [
        "PO_NBR", COL_CARRIER, "DC_LOC_NAME", COL_SEVERITY,
        COL_EXCESS_CARRIER, COL_DELAY_DAYS, COL_IS_RESCHEDULED,
    ]
    po_table(high_carrier, cols_tabla, key="carrier_high_table")

    st.markdown("---")
    st.subheader(" Detalle de PO")
    selected_po = st.selectbox(
        "Selecciona un PO",
        options=high_carrier["PO_NBR"].tolist(),
        key="carrier_po_select",
    )
    if selected_po:
        row = high_carrier[high_carrier["PO_NBR"] == selected_po].iloc[0]
        po_detail_expander(row, title="Detalle")
else:
    st.info("No hay POs Carrier con severidad HIGH.")