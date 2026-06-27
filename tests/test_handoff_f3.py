"""
test_handoff_f3.py — contrato de handoff F3→F4 (#100).

Tercera frontera del contrato de handoff del proyecto, espejo de
`test_handoff_contract.py` (que cubre F1→F2 y F2→F3). Aquí el artefacto NO es el df
completo, sino el CSV-entregable `po_output.csv` que produce `export_deliverable_csv`:
el ÚNICO input de Fase 4. La app lo relee y reconstruye lo que mostraría, sin recomputar
el pipeline ni llamar al LLM.

Qué blinda este contrato:
  - Las 5 columnas del mentor (PO_NBR, stage, severity, explanation, action) van
    primero y en orden — el contrato canónico que evalúa el mentor.
  - El bloque de soporte de la app (timeline + agravantes + concordancia) está presente,
    para que Fase 4 dibuje el timeline y marque agravantes SIN recomputar.
  - Alcance de filas: solo POs tardíos.
  - Identidad funcional: el CSV releído reconstruye el DataFrame que se exportó (mismas
    columnas y valores; el tipado de fecha es texto en CSV, igual que el contrato F1/F2).

Un cambio en lo que produce F3 (columnas del export), en lo que F1/F2 entregan, o en lo
que la app espera, rompe aquí — que es justo lo que el contrato debe detectar.
"""
import pandas as pd
import pandas.testing as pdt

from llm_integration import (
    export_deliverable_csv,
    _DELIVERABLE_COLUMNS,
    _MENTOR_COLUMNS,
)

_SEVERITY_DOMAIN = {"HIGH", "MEDIUM", "LOW"}


def _df_clasificado_con_llm() -> pd.DataFrame:
    """DataFrame de F2+F3 con dos tardíos y un on-time, con todas las columnas que el
    artefacto consume (las del mapeo del mentor + el soporte de la app)."""
    base = {
        "PO_NBR": ["PO-1", "PO-2", "PO-ONTIME"],
        "stage_primary": ["Vendor", "Carrier", "On-Time"],
        "delay_days_calc": [4.0, 1.5, 0.0],
        "llm_severidad": ["HIGH", "MEDIUM", ""],
        "llm_causa_raiz": ["cita aprobada tarde", "tránsito lento", ""],
        "llm_accion_recomendada": ["contactar vendor", "escalar carrier", ""],
        "HOT_PO_FLAG": [1, 0, 0],
        "is_short_ship": [False, True, False],
        "REASON_DSC": ["Vendor late appt", "Carrier delay", ""],
        "llm_coincide_con_reason": [True, False, False],
    }
    for col in ("PO_DT", "STA_DT", "APPROVED_DT", "TRAILER_ARRIVE_DT",
                "CHECKIN_DT", "CHECKOUT_DT", "RECPT_DT"):
        base[col] = ["2024-01-05 00:00", "2024-01-06 00:00", "2024-01-04 00:00"]
    return pd.DataFrame(base)


def test_contrato_f3_columnas_y_orden(tmp_path):
    # El artefacto declara columnas exactas; las 5 del mentor primero y en orden.
    out_path = tmp_path / "po_output.csv"
    export_deliverable_csv(_df_clasificado_con_llm(), out_path)
    releido = pd.read_csv(out_path)
    assert list(releido.columns) == _DELIVERABLE_COLUMNS
    assert list(releido.columns[:5]) == _MENTOR_COLUMNS


def test_contrato_f3_solo_tardios(tmp_path):
    # Alcance de filas del contrato: solo POs tardíos (el on-time no entra).
    out_path = tmp_path / "po_output.csv"
    export_deliverable_csv(_df_clasificado_con_llm(), out_path)
    releido = pd.read_csv(out_path)
    assert len(releido) == 2
    assert "PO-ONTIME" not in set(releido["PO_NBR"])


def test_contrato_f3_severity_en_dominio(tmp_path):
    # severity (la oficial, del LLM — ADR-10) solo toma valores HIGH/MEDIUM/LOW.
    out_path = tmp_path / "po_output.csv"
    export_deliverable_csv(_df_clasificado_con_llm(), out_path)
    releido = pd.read_csv(out_path)
    assert set(releido["severity"]).issubset(_SEVERITY_DOMAIN)


def test_contrato_f3_soporte_para_timeline_presente(tmp_path):
    # El soporte de la app está en el artefacto → Fase 4 dibuja el timeline y marca
    # agravantes/concordancia SIN recomputar el pipeline ni llamar al LLM.
    out_path = tmp_path / "po_output.csv"
    export_deliverable_csv(_df_clasificado_con_llm(), out_path)
    releido = pd.read_csv(out_path)
    for col in ("PO_DT", "STA_DT", "APPROVED_DT", "TRAILER_ARRIVE_DT",
                "CHECKIN_DT", "CHECKOUT_DT", "RECPT_DT",
                "HOT_PO_FLAG", "is_short_ship",
                "REASON_DSC", "llm_coincide_con_reason"):
        assert col in releido.columns


def test_contrato_f3_releido_reconstruye_lo_exportado(tmp_path):
    # Identidad funcional: el CSV releído == el DataFrame que export_deliverable_csv
    # devolvió (lo que la app cargaría). Comparación por valor; las fechas viajan como
    # texto en el CSV, igual que en el contrato F1/F2.
    out_path = tmp_path / "po_output.csv"
    exportado = export_deliverable_csv(_df_clasificado_con_llm(), out_path)
    releido = pd.read_csv(out_path)

    fechas = ["PO_DT", "STA_DT", "APPROVED_DT", "TRAILER_ARRIVE_DT",
              "CHECKIN_DT", "CHECKOUT_DT", "RECPT_DT"]
    izq, der = exportado.reset_index(drop=True), releido.reset_index(drop=True)
    for col in fechas:
        izq[col] = pd.to_datetime(izq[col], errors="coerce")
        der[col] = pd.to_datetime(der[col], errors="coerce")
    pdt.assert_frame_equal(izq, der, check_dtype=False)
