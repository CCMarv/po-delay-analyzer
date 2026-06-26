"""Helpers de formateo y utilidades varias."""
import json
import math

import pandas as pd


def po_detail_json(row: pd.Series) -> str:
    """Construye el JSON de detalle para el drill-down de un PO."""
    import json
    import math
    
    def convert_value(val):
        """Convierte valores pandas a tipos JSON-serializables."""
        if pd.isna(val):
            return None
        if isinstance(val, (int, float)):
            if math.isnan(val) or math.isinf(val):
                return None
            return round(float(val), 1)  # ← Redondea a 1 decimal
        return val

    detail = {
        "Vendor": convert_value(row.get("VENDOR_NAME", "")),
        "Carrier": convert_value(row.get("CARRIER_PARTY_NAME", "")),
        "DC": convert_value(row.get("DC_LOC_NAME", "")),
        "stage_primary": convert_value(row.get("stage_primary", "")),
        "dc_substage": convert_value(row.get("dc_substage", None)),
        "severity": convert_value(row.get("severity", "")),
        "excess_vendor_hrs": convert_value(row.get("excess_vendor_hrs", 0)),
        "excess_carrier_hrs": convert_value(row.get("excess_carrier_hrs", 0)),
        "excess_yard_hrs": convert_value(row.get("excess_yard_hrs", 0)),
        "excess_dock_hrs": convert_value(row.get("excess_dock_hrs", 0)),
        "delay_days": convert_value(row.get("delay_days_calc", 0)),
        "is_rescheduled": bool(convert_value(row.get("is_rescheduled", False))),
        "is_short_ship": bool(convert_value(row.get("is_short_ship", False))),
        "is_short_lead": bool(convert_value(row.get("is_short_lead", False))),
        "appt_lead_days": convert_value(row.get("appt_lead_days", 0)),
    }
    return json.dumps(detail, indent=3, ensure_ascii=False, default=str)


###AÑADIDO CSS
import streamlit as st
from pathlib import Path

def load_css():
    """Inyecta el CSS personalizado en la app."""
    css_path = Path(__file__).parent.parent / "assets" / "styles.css"
    if css_path.exists():
        with open(css_path, encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

            