"""Sidebar con filtros globales."""
import pandas as pd
import streamlit as st

from config import COL_CARRIER, COL_DC, COL_VENDOR


def render_sidebar(df):
    """Renderiza el sidebar con filtros de DC, Vendor, Carrier y Severidad.

    Returns:
        dict con los filtros seleccionados.
    """
    st.sidebar.header("🔍 Filtros")

    # DC
    dcs = sorted(df[COL_DC].dropna().unique().tolist())
    selected_dcs = st.sidebar.multiselect("Distribution Centers", dcs, default=dcs)

    # Vendor
    vendors = sorted(df[COL_VENDOR].dropna().unique().tolist())
    selected_vendors = st.sidebar.multiselect("Vendors", vendors, default=vendors)

    # Carrier
    carriers = sorted(df[COL_CARRIER].dropna().unique().tolist())
    selected_carriers = st.sidebar.multiselect("Carriers", carriers, default=carriers)

    # Severidad
    severidades = ["HIGH", "MEDIUM", "LOW"]
    selected_sev = st.sidebar.multiselect("Severidad mínima", severidades, default=severidades)

    return {
        "dcs": selected_dcs,
        "vendors": selected_vendors,
        "carriers": selected_carriers,
        "severidades": selected_sev,
    }


def apply_filters(df, filters: dict):
    """Aplica los filtros del sidebar al DataFrame."""
    mask = pd.Series(True, index=df.index)

    if filters["dcs"]:
        mask &= df[COL_DC].isin(filters["dcs"])
    if filters["vendors"]:
        mask &= df[COL_VENDOR].isin(filters["vendors"])
    if filters["carriers"]:
        mask &= df[COL_CARRIER].isin(filters["carriers"])
    if filters["severidades"]:
        # Solo aplica a tardíos (los On-Time no tienen severidad)
        mask &= (df["severity"].isin(filters["severidades"])) | (df["delay_days_calc"] <= 0)

    return df[mask].copy()