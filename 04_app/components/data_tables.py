"""Tablas de datos estilizadas."""
import pandas as pd
import streamlit as st


def po_table(df: pd.DataFrame, columns: list, key: str = "po_table"):
    """Muestra una tabla de POs con formato."""
    st.dataframe(
        df[columns],
        use_container_width=True,
        hide_index=True,
        key=key,
    )


def po_detail_expander(row: pd.Series, title: str = "🔍 Detalle"):
    """Expander con el JSON de detalle de un PO."""
    from utils.helpers import po_detail_json

    with st.expander(f"{title}: {row.get('PO_NBR', '')}"):
        st.json(po_detail_json(row))