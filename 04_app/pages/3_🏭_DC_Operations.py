#AÑADIDO CSS
# En app.py (y en las 3 páginas de /pages)
import streamlit as st
from utils.helpers import load_css
from components.navbar import render_navbar

# 1. Configurar página
st.set_page_config(page_title="PO Root Cause Analyzer", layout="wide")
# 2. Inyectar CSS
load_css()

render_navbar(active_page="dc")

"""Dashboard de DC Operations."""

from config import (
    COL_DC, COL_DELAY_DAYS, COL_EXCESS_DC, COL_EXCESS_DOCK, COL_EXCESS_YARD,
    COL_SEVERITY, COL_STAGE_PRIMARY, COL_EXCESS_CARRIER, COL_EXCESS_VENDOR,
)

from services.data_service import load_classified_data, get_tardios
from services.metrics_service import dc_substage_stats, culpas_injustas
from components.sidebar import render_sidebar, apply_filters
from components.metrics_cards import metric_card
from components.charts import bar_chart
from components.data_tables import po_table, po_detail_expander

st.set_page_config(page_title="DC Operations", page_icon="🏭", layout="wide")

df = load_classified_data()
filters = render_sidebar(df)
df = apply_filters(df, filters)

st.title("🏭 DC Operations")
st.markdown("**Throughput de muelle · defensa contra culpas injustas · priorización de capacidad**")

# ── KPIs ────────────────────────────────────────────────────────────────────
tardios = get_tardios(df)
dc_pos = tardios[tardios[COL_STAGE_PRIMARY] == "DC"]
yard_congestion = dc_pos[dc_pos["excess_yard_hrs"] > 4]
dock_backlog = dc_pos[dc_pos["excess_dock_hrs"] > 6]
culpas = culpas_injustas(df)

col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    metric_card("POs tardíos DC", len(dc_pos), icon="🏭")
with col2:
    metric_card("Yard congestion", len(yard_congestion), icon="🚧")
with col3:
    metric_card("Dock backlog", len(dock_backlog), icon="📦")
with col4:
    metric_card("⚖️ Culpas injustas", len(culpas), icon="⚖️")
with col5:
    high_dc = dc_pos[dc_pos[COL_SEVERITY] == "HIGH"]
    metric_card("HIGH severity", len(high_dc), icon="🔥")

# ── Sub-etapa DC ────────────────────────────────────────────────────────────
st.subheader("Sub-etapa DC")
substats = dc_substage_stats(df)

if len(substats) > 0:
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        bar_chart(
            substats, x="dc_substage", y="avg_excess_hrs",
            title="Exceso promedio (h)",
        )
    with col_s2:
        st.dataframe(substats, use_container_width=True, hide_index=True)

# ── POs DC de alta severidad ────────────────────────────────────────────────
st.subheader("🔥 POs DC de alta severidad")
high_dc = dc_pos[dc_pos[COL_SEVERITY] == "HIGH"].head(10)

if len(high_dc) > 0:
    cols_tabla = [
        "PO_NBR", COL_DC, "VENDOR_NAME", "dc_substage", COL_SEVERITY,
        COL_EXCESS_YARD, COL_EXCESS_DOCK, COL_DELAY_DAYS,
    ]
    po_table(high_dc, cols_tabla, key="dc_high_table")

    st.markdown("---")
    st.subheader("🔍 Drill-down")
    selected_po = st.selectbox(
        "Selecciona un PO",
        options=high_dc["PO_NBR"].tolist(),
        key="dc_po_select",
    )
    if selected_po:
        row = high_dc[high_dc["PO_NBR"] == selected_po].iloc[0]
        po_detail_expander(row, title="Detalle")
else:
    st.info("No hay POs DC con severidad HIGH.")

# ── Defensa: culpas injustas ────────────────────────────────────────────────
st.subheader("⚖️ Defensa: culpas injustas")
st.markdown(
    f"**{len(culpas)} POs** no deberían impactar el KPI del DC. "
    "El reason humano dice 'DC' pero el cómputo atribuye la culpa a Vendor o Carrier."
)

if len(culpas) > 0:
    cols_culpa = [
        "PO_NBR", COL_DC, "reason_group_manual", COL_STAGE_PRIMARY,
        COL_EXCESS_CARRIER, COL_EXCESS_VENDOR, COL_DELAY_DAYS,
    ]
    po_table(culpas, cols_culpa, key="culpas_table")
else:
    st.success("✅ No hay culpas injustas detectadas.")