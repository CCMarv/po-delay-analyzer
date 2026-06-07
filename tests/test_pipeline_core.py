"""
Suite de tests de pipeline_core (issue #13).

Prueba las dos funciones puras del módulo:
  - clean_po_data(df)        — parseo, flags de calidad, deltas, flags de clasif.
  - cross_validate_deltas(df) — discrepancias calc vs precalc.

Las funciones, fixtures y el helper row_for vienen de tests/conftest.py (pytest lo
carga solo). Cada test sigue el patrón AAA (Arrange-Act-Assert); el "arrange" ya
está hecho en el fixture, así que aquí casi todo es Act + Assert.

Dos reglas de oro que se repiten abajo (explicadas en la guía local):
  · Floats → pytest.approx, nunca ==. Los deltas salen de dividir segundos, así
    que cargan ruido de coma flotante (~1e-15). approx tolera ese ruido.
  · NaN → pd.isna(x), nunca x == NaN (porque NaN != NaN siempre da False).
"""
import numpy as np
import pandas as pd
import pytest

from conftest import row_for, clean_po_data, cross_validate_deltas

# Columnas que clean_po_data debe convertir a datetime.
DATE_COLS = [
    "PO_DT", "STA_DT", "RECPT_DT",
    "REQUESTED_DT", "FIRST_SUBMITTED_DT",
    "DT_APPT_FIRST_APPROVED", "APPROVED_DT", "DT_APPT_CURRENT_APPROVED",
    "PREVIOUS_REQUEST_DT",
    "TRAILER_ARRIVE_DT", "CHECKIN_DT", "CHECKOUT_DT", "TRAILER_DEPART_DT",
]


# ════════════════════════════════════════════════════════════════════════════
# A. Smoke / import — ¿corre y devuelve lo básico?
# ════════════════════════════════════════════════════════════════════════════
def test_clean_runs_and_preserves_rows(df_raw, df_clean):
    # No pierde ni inventa filas: limpieza enriquece, no filtra.
    assert len(df_clean) == len(df_raw)
    assert isinstance(df_clean, pd.DataFrame)


def test_clean_adds_expected_columns(df_clean):
    # Columnas nuevas que el resto de la suite va a interrogar. Si una falta,
    # el módulo cambió de contrato y conviene saberlo aquí, no en cada test.
    nuevas = {
        "_trailer_arrive_null", "_ts_issue", "_data_reliable",
        "_rescheduled", "_fill_rate", "_short_ship",
        "lead_time_days", "carrier_lag_hrs", "yard_wait_calc_hrs",
        "dock_calc_hrs", "total_dc_hrs", "appt_lead_days", "delay_days_calc",
        "flag_yard_congestion", "flag_dock_backlog", "flag_carrier_miss",
        "flag_short_lead_time", "flag_hot_late",
    }
    assert nuevas.issubset(df_clean.columns)


# ════════════════════════════════════════════════════════════════════════════
# B. Parseo de fechas
# ════════════════════════════════════════════════════════════════════════════
@pytest.mark.parametrize("col", DATE_COLS)
def test_date_cols_are_datetime(df_clean, col):
    # Cada columna de fecha queda como datetime64 tras el parseo.
    assert pd.api.types.is_datetime64_any_dtype(df_clean[col])


@pytest.mark.filterwarnings("ignore::UserWarning")  # pandas avisa que infiere formato; aquí es lo esperado
def test_unparseable_date_becomes_nat(df_raw):
    # errors='coerce': una fecha basura no revienta; se vuelve NaT.
    df_raw.loc[df_raw["PO_NBR"] == "PO-CLEAN", "PO_DT"] = "no-es-fecha"
    out = clean_po_data(df_raw)
    assert pd.isna(row_for(out, "PO-CLEAN")["PO_DT"])


# ════════════════════════════════════════════════════════════════════════════
# C. Flags de calidad
# ════════════════════════════════════════════════════════════════════════════
def test_trailer_arrive_null_flag(df_clean):
    assert row_for(df_clean, "PO-NULLTRAILER")["_trailer_arrive_null"] == True   # noqa: E712
    assert row_for(df_clean, "PO-CLEAN")["_trailer_arrive_null"] == False        # noqa: E712


# Las 4 filas que violan el orden temporal, una por cada condición de _ts_issue.
TS_ISSUE_ROWS = ["PO-TS-CHECKIN", "PO-TS-CHECKOUT", "PO-TS-RECPT", "PO-TS-STA"]


@pytest.mark.parametrize("po_nbr", TS_ISSUE_ROWS)
def test_ts_issue_true_on_inverted_row(df_clean, po_nbr):
    # Requisito del issue: _ts_issue debe marcarse True en cada inversión.
    assert row_for(df_clean, po_nbr)["_ts_issue"] == True   # noqa: E712


def test_ts_issue_false_on_clean_row(df_clean):
    assert row_for(df_clean, "PO-CLEAN")["_ts_issue"] == False   # noqa: E712


def test_ts_issue_false_on_null_trailer(df_clean):
    # Matiz importante: el trailer nulo NO dispara _ts_issue (comparar contra NaT
    # da False), lo caza el OTRO flag, _trailer_arrive_null. Por eso _data_reliable
    # combina ambos.
    assert row_for(df_clean, "PO-NULLTRAILER")["_ts_issue"] == False   # noqa: E712


def test_data_reliable_logic(df_clean):
    # reliable = sin inversión temporal Y con trailer no nulo.
    assert row_for(df_clean, "PO-CLEAN")["_data_reliable"] == True            # noqa: E712
    assert row_for(df_clean, "PO-TS-CHECKOUT")["_data_reliable"] == False     # noqa: E712
    assert row_for(df_clean, "PO-NULLTRAILER")["_data_reliable"] == False     # noqa: E712


# ════════════════════════════════════════════════════════════════════════════
# D. Deltas de tiempo (el núcleo de pytest.approx)
# ════════════════════════════════════════════════════════════════════════════
# (PO_NBR, columna, valor_esperado) para los deltas de la fila PO-CLEAN, todos
# verificables a mano desde los datetimes del fixture.
CLEAN_DELTAS = [
    ("lead_time_days", 4.0),     # STA(01-05) - PO(01-01)
    ("carrier_lag_hrs", 2.0),    # ARRIVE(04 02:00) - APPROVED(04 00:00)
    ("yard_wait_calc_hrs", 3.0), # CHECKIN(05:00) - ARRIVE(02:00)
    ("dock_calc_hrs", 4.0),      # CHECKOUT(09:00) - CHECKIN(05:00)
    ("total_dc_hrs", 7.0),       # CHECKOUT(09:00) - ARRIVE(02:00)
    ("appt_lead_days", 1.0),     # STA(01-05) - APPROVED(01-04)
    ("delay_days_calc", 0.0),    # RECPT(01-05) - STA(01-05) = on-time
]


@pytest.mark.parametrize("col,expected", CLEAN_DELTAS)
def test_clean_deltas_known_values(df_clean, col, expected):
    got = row_for(df_clean, "PO-CLEAN")[col]
    assert got == pytest.approx(expected, abs=1e-9)


def test_lead_time_clipped_at_zero(df_clean):
    # PO-TS-STA tiene STA antes que PO → días negativos → clip a 0.
    assert row_for(df_clean, "PO-TS-STA")["lead_time_days"] == pytest.approx(0.0, abs=1e-9)


def test_carrier_lag_not_clipped(df_raw):
    # carrier_lag_hrs NO se clipa a 0 (a diferencia de yard/dock/total/lead): un
    # arribo ANTES del approved produce un valor negativo, y se conserva. Mutamos
    # PO-CLEAN para que el trailer arribe 3h antes del approved → -3.0.
    mask = df_raw["PO_NBR"] == "PO-CLEAN"
    df_raw.loc[mask, "APPROVED_DT"] = "2024-01-04 05:00"
    df_raw.loc[mask, "TRAILER_ARRIVE_DT"] = "2024-01-04 02:00"  # 3h antes
    out = clean_po_data(df_raw)
    assert row_for(out, "PO-CLEAN")["carrier_lag_hrs"] == pytest.approx(-3.0, abs=1e-9)


def test_carrier_lag_nan_on_null_trailer(df_clean):
    # Trailer nulo → ARRIVE es NaT → la resta es NaT → el delta es NaN.
    # Se afirma con pd.isna, NUNCA con == (NaN == NaN es False).
    assert pd.isna(row_for(df_clean, "PO-NULLTRAILER")["carrier_lag_hrs"])


@pytest.mark.parametrize("col", ["yard_wait_calc_hrs", "dock_calc_hrs", "total_dc_hrs"])
def test_dc_deltas_never_negative(df_clean, col):
    # Estos tres sí clipan a 0: ninguna fila debe dar negativo.
    serie = df_clean[col].dropna()
    assert (serie >= 0).all()


def test_delay_days_clipped_on_inverted_recpt(df_clean):
    # PO-TS-RECPT: RECPT antes que CHECKIN, pero delay_days mide RECPT - STA.
    # Su RECPT (04 03:00) < STA (01-05) → negativo → clip a 0.
    assert row_for(df_clean, "PO-TS-RECPT")["delay_days_calc"] == pytest.approx(0.0, abs=1e-9)


# ════════════════════════════════════════════════════════════════════════════
# E. Flags de clasificación
# ════════════════════════════════════════════════════════════════════════════
def test_flag_yard_congestion_uses_precalc(df_clean):
    # El flag lee la columna PRECALC YARD_WAIT_HRS, no el yard_wait_calc_hrs.
    # PO-XVAL-DISC: calc=3.0 (no congestión) pero precalc=10.0 (>4) → flag True.
    # Eso prueba que el flag mira la precalc.
    fila = row_for(df_clean, "PO-XVAL-DISC")
    assert fila["yard_wait_calc_hrs"] == pytest.approx(3.0, abs=1e-9)  # calc bajo
    assert fila["flag_yard_congestion"] == True   # noqa: E712  ← pero el flag dispara


def test_flag_dock_backlog_uses_precalc(df_clean):
    # Igual que arriba pero con DOCK_HRS precalc=20.0 (>6) vs dock_calc=4.0.
    fila = row_for(df_clean, "PO-XVAL-DISC")
    assert fila["dock_calc_hrs"] == pytest.approx(4.0, abs=1e-9)
    assert fila["flag_dock_backlog"] == True   # noqa: E712


def test_flag_carrier_miss_uses_calc(df_clean):
    # carrier_miss SÍ usa el calc (carrier_lag_hrs > 4). Construimos un miss claro.
    fila = row_for(df_clean, "PO-CLEAN")  # baseline: lag 2.0 → no miss
    assert fila["flag_carrier_miss"] == False   # noqa: E712


def test_flag_carrier_miss_silent_false_on_null_trailer(df_clean):
    # ── TEST ESTRELLA — documenta el hallazgo #16 / B4 ──────────────────────
    # PO-NULLTRAILER simula un carrier miss REAL (el trailer nunca registró
    # arribo). Pero como TRAILER_ARRIVE es NaT, carrier_lag_hrs = NaN, y la
    # comparación NaN > 4.0 da False. Resultado: el flag de carrier miss queda
    # SILENCIOSAMENTE en False — el delay del carrier se vuelve invisible.
    # Esto NO es lo que el test "avala": lo DOCUMENTA como hallazgo pendiente de
    # decisión en #16 ("¿no aplica" o "indeterminado"?).
    fila = row_for(df_clean, "PO-NULLTRAILER")
    assert pd.isna(fila["carrier_lag_hrs"])              # la causa
    assert fila["flag_carrier_miss"] == False   # noqa: E712  ← el efecto silencioso


def test_flag_short_lead_time(df_clean):
    # lead_time_days < 3 → True. PO-CLEAN tiene 4.0 → False; PO-TS-STA clipa a 0 → True.
    assert row_for(df_clean, "PO-CLEAN")["flag_short_lead_time"] == False   # noqa: E712
    assert row_for(df_clean, "PO-TS-STA")["flag_short_lead_time"] == True   # noqa: E712


@pytest.mark.parametrize(
    "hot,is_late,expected",
    [(1, "Y", True), (1, "N", False), (0, "Y", False), (0, "N", False)],
)
def test_flag_hot_late(df_raw, hot, is_late, expected):
    # flag_hot_late = (HOT_PO_FLAG == 1) & (IS_LATE == 'Y'). Mutamos PO-CLEAN.
    mask = df_raw["PO_NBR"] == "PO-CLEAN"
    df_raw.loc[mask, "HOT_PO_FLAG"] = hot
    df_raw.loc[mask, "IS_LATE"] = is_late
    out = clean_po_data(df_raw)
    assert bool(row_for(out, "PO-CLEAN")["flag_hot_late"]) is expected


# ════════════════════════════════════════════════════════════════════════════
# F. Métricas operacionales
# ════════════════════════════════════════════════════════════════════════════
def test_rescheduled(df_clean):
    assert row_for(df_clean, "PO-RESCHED")["_rescheduled"] == True    # noqa: E712
    assert row_for(df_clean, "PO-CLEAN")["_rescheduled"] == False     # noqa: E712


def test_fill_rate_and_short_ship(df_clean):
    short = row_for(df_clean, "PO-SHORTSHIP")
    assert short["_fill_rate"] == pytest.approx(0.5, abs=1e-9)
    assert short["_short_ship"] == True   # noqa: E712
    clean = row_for(df_clean, "PO-CLEAN")
    assert clean["_fill_rate"] == pytest.approx(1.0, abs=1e-9)
    assert clean["_short_ship"] == False  # noqa: E712


def test_fill_rate_clipped_to_one(df_raw):
    # shipped > ordered → ratio > 1 → clip a 1.0.
    mask = df_raw["PO_NBR"] == "PO-CLEAN"
    df_raw.loc[mask, "NUM_CASES_SHIPPED"] = 150  # 150/100 = 1.5 → clip 1.0
    out = clean_po_data(df_raw)
    assert row_for(out, "PO-CLEAN")["_fill_rate"] == pytest.approx(1.0, abs=1e-9)


# ════════════════════════════════════════════════════════════════════════════
# G. cross_validate_deltas
# ════════════════════════════════════════════════════════════════════════════
def test_xval_returns_df_with_discrepancy_cols(df_xval):
    assert isinstance(df_xval, pd.DataFrame)
    assert "_yard_discrepancy" in df_xval.columns
    assert "_dock_discrepancy" in df_xval.columns


def test_discrepancy_true_above_threshold(df_xval):
    # PO-XVAL-DISC: |3-10|=7 y |4-20|=16, ambos > 1.0 → discrepancia True.
    fila = row_for(df_xval, "PO-XVAL-DISC")
    assert fila["_yard_discrepancy"] == True   # noqa: E712
    assert fila["_dock_discrepancy"] == True   # noqa: E712


def test_no_discrepancy_below_threshold(df_xval):
    # PO-CLEAN: precalc == calc → diferencia 0 → sin discrepancia.
    fila = row_for(df_xval, "PO-CLEAN")
    assert fila["_yard_discrepancy"] == False   # noqa: E712
    assert fila["_dock_discrepancy"] == False   # noqa: E712


def test_xval_prints_report(df_clean, capsys):
    # cross_validate imprime un reporte; el fixture capsys de pytest captura
    # stdout para poder afirmar sobre lo impreso.
    cross_validate_deltas(df_clean)
    salida = capsys.readouterr().out
    assert "Cross-validation" in salida


# ════════════════════════════════════════════════════════════════════════════
# H. Robustez — no crashea con nulls (requisito explícito del issue)
# ════════════════════════════════════════════════════════════════════════════
def test_zero_ordered_no_crash(df_clean):
    # NUM_CASES_ORDERED = 0 → _fill_rate NaN (no ZeroDivisionError), short_ship False.
    fila = row_for(df_clean, "PO-ZEROORD")
    assert pd.isna(fila["_fill_rate"])
    assert fila["_short_ship"] == False   # noqa: E712


def test_null_quantities_no_crash(df_raw):
    # Cantidades nulas no deben reventar la función.
    mask = df_raw["PO_NBR"] == "PO-CLEAN"
    df_raw.loc[mask, "NUM_CASES_ORDERED"] = np.nan
    df_raw.loc[mask, "NUM_CASES_SHIPPED"] = np.nan
    out = clean_po_data(df_raw)  # no debe lanzar excepción
    assert pd.isna(row_for(out, "PO-CLEAN")["_fill_rate"])


def test_all_nat_row_no_crash(df_raw):
    # Una fila con TODAS las fechas nulas: la función corre, los deltas son NaN
    # y los flags de calidad quedan sanos (sin excepción).
    mask = df_raw["PO_NBR"] == "PO-CLEAN"
    for col in DATE_COLS:
        df_raw.loc[mask, col] = None
    out = clean_po_data(df_raw)
    fila = row_for(out, "PO-CLEAN")
    assert pd.isna(fila["lead_time_days"])
    assert fila["_ts_issue"] == False           # noqa: E712  (NaT no dispara)
    assert fila["_trailer_arrive_null"] == True # noqa: E712
