"""
conftest.py — configuración y fixtures compartidas de la suite de tests.

pytest carga este archivo AUTOMÁTICAMENTE (no hay que importarlo). Todo lo que
definimos aquí con @pytest.fixture queda disponible en cualquier test_*.py del
directorio, solo con nombrar el fixture como argumento de la función de test.

Qué vive aquí:
  1. El fixture sintético (`df_raw`): un DataFrame pequeño de FILAS DE VALORES
     CONOCIDOS, una fila por escenario, identificadas por PO_NBR. Construido a mano
     con datetimes redondos para que los deltas esperados se puedan verificar de
     cabeza (ver la tabla más abajo).
  2. `df_clean`: el resultado de pasar df_raw por clean_po_data() UNA vez.
  3. `df_xval`: df_clean pasado además por cross_validate_deltas().
  4. `row_for(df, po_nbr)`: helper para leer la única fila de un escenario.

Por qué un fixture sintético y NO el CSV real: el CSV de 400 filas vive en
data/raw/ pero está gitignored (no se sube), así que CI no lo tendría. Además,
"valores conocidos" significa que NOSOTROS calculamos la respuesta esperada — con
400 filas reales no sabríamos cuánto debe dar cada delta. Un test necesita una
respuesta conocida contra la cual comparar.
"""
import sys
from pathlib import Path

import pandas as pd
import pytest

# ── Import del módulo bajo prueba ────────────────────────────────────────────
# pyproject.toml ya añade 01_/02_/03_ al pythonpath, así que estos imports funcionan
# pese a que las carpetas empiecen con dígito. Mantenemos también estos inserts como
# red de seguridad por si alguien corre pytest sin la config (p. ej. apuntando a un
# solo archivo desde otra carpeta).
_REPO_ROOT = Path(__file__).resolve().parent.parent
for _sub in ("01_data_pipeline_and_eda", "02_clasif_reglas_negocio", "03_llm_integration"):
    _dir = _REPO_ROOT / _sub
    if str(_dir) not in sys.path:
        sys.path.insert(0, str(_dir))

from pipeline_core import clean_po_data, cross_validate_deltas  # noqa: E402


# ── Helper de lectura de filas ───────────────────────────────────────────────
def row_for(df: pd.DataFrame, po_nbr: str) -> pd.Series:
    """Devuelve la única fila cuyo PO_NBR == po_nbr (como pd.Series).

    Falla ruidosamente si hay 0 o >1 coincidencias: si el fixture cambia y un
    PO_NBR se duplica o desaparece, queremos enterarnos en el test, no obtener
    una fila silenciosamente equivocada.
    """
    hits = df[df["PO_NBR"] == po_nbr]
    assert len(hits) == 1, f"Se esperaba 1 fila para {po_nbr!r}, hay {len(hits)}"
    return hits.iloc[0]


# ── Constructor del DataFrame sintético ──────────────────────────────────────
# Cada fila es UN escenario. Los datetimes usan offsets de horas/días enteros
# desde una base, para que los deltas esperados sean exactos:
#
# Línea base de PO-CLEAN (el resto deriva de esta para ser comparables):
#   PO_DT           = 2024-01-01 00:00
#   STA_DT          = 2024-01-05 00:00   → lead_time_days  = 4.0
#   APPROVED_DT     = 2024-01-04 00:00   → appt_lead_days  = 1.0
#   TRAILER_ARRIVE  = 2024-01-04 02:00   → carrier_lag_hrs = 2.0  (< 4 → no miss)
#   CHECKIN_DT      = 2024-01-04 05:00   → yard_wait_calc  = 3.0
#   CHECKOUT_DT     = 2024-01-04 09:00   → dock_calc       = 4.0 ; total_dc = 7.0
#   RECPT_DT        = 2024-01-05 00:00   → delay_days_calc = 0.0  (on-time)
# Precalc de PO-CLEAN se fija IGUAL al calc (YARD=3, DOCK=4, DELAY=0) → sin
# discrepancia en cross_validate.
def _build_raw() -> pd.DataFrame:
    NaT = None  # pd.to_datetime(None) → NaT; en el dict crudo usamos None

    # Construimos como lista de dicts (una fila por escenario) y luego DataFrame:
    # leer "fila = escenario" es más claro que columnas paralelas gigantes.
    rows = [
        # ── PO-CLEAN: happy path, todo en orden, on-time, precalc == calc ────
        dict(
            PO_NBR="PO-CLEAN",
            PO_DT="2024-01-01 00:00", STA_DT="2024-01-05 00:00",
            APPROVED_DT="2024-01-04 00:00",
            DT_APPT_FIRST_APPROVED="2024-01-04 00:00",
            DT_APPT_CURRENT_APPROVED="2024-01-04 00:00",
            TRAILER_ARRIVE_DT="2024-01-04 02:00",
            CHECKIN_DT="2024-01-04 05:00", CHECKOUT_DT="2024-01-04 09:00",
            RECPT_DT="2024-01-05 00:00",
            REQUESTED_DT="2024-01-01 00:00", FIRST_SUBMITTED_DT="2024-01-01 00:00",
            PREVIOUS_REQUEST_DT=NaT, TRAILER_DEPART_DT="2024-01-04 10:00",
            NUM_CASES_ORDERED=100, NUM_CASES_SHIPPED=100,
            YARD_WAIT_HRS=3.0, DOCK_HRS=4.0, DELAY_DAYS=0.0,
            HOT_PO_FLAG=0, IS_LATE="N",
        ),
        # ── PO-TS-CHECKIN: CHECKIN < TRAILER_ARRIVE (cond 1 de _ts_issue) ────
        dict(
            PO_NBR="PO-TS-CHECKIN",
            PO_DT="2024-01-01 00:00", STA_DT="2024-01-05 00:00",
            APPROVED_DT="2024-01-04 00:00",
            DT_APPT_FIRST_APPROVED="2024-01-04 00:00",
            DT_APPT_CURRENT_APPROVED="2024-01-04 00:00",
            TRAILER_ARRIVE_DT="2024-01-04 05:00",
            CHECKIN_DT="2024-01-04 02:00",   # antes que el arribo → inversión
            CHECKOUT_DT="2024-01-04 09:00",
            RECPT_DT="2024-01-05 00:00",
            REQUESTED_DT="2024-01-01 00:00", FIRST_SUBMITTED_DT="2024-01-01 00:00",
            PREVIOUS_REQUEST_DT=NaT, TRAILER_DEPART_DT="2024-01-04 10:00",
            NUM_CASES_ORDERED=100, NUM_CASES_SHIPPED=100,
            YARD_WAIT_HRS=0.0, DOCK_HRS=7.0, DELAY_DAYS=0.0,
            HOT_PO_FLAG=0, IS_LATE="N",
        ),
        # ── PO-TS-CHECKOUT: CHECKOUT < CHECKIN (cond 2; única inversión real)─
        dict(
            PO_NBR="PO-TS-CHECKOUT",
            PO_DT="2024-01-01 00:00", STA_DT="2024-01-05 00:00",
            APPROVED_DT="2024-01-04 00:00",
            DT_APPT_FIRST_APPROVED="2024-01-04 00:00",
            DT_APPT_CURRENT_APPROVED="2024-01-04 00:00",
            TRAILER_ARRIVE_DT="2024-01-04 02:00",
            CHECKIN_DT="2024-01-04 09:00",
            CHECKOUT_DT="2024-01-04 05:00",  # antes que el check-in → inversión
            RECPT_DT="2024-01-05 00:00",
            REQUESTED_DT="2024-01-01 00:00", FIRST_SUBMITTED_DT="2024-01-01 00:00",
            PREVIOUS_REQUEST_DT=NaT, TRAILER_DEPART_DT="2024-01-04 10:00",
            NUM_CASES_ORDERED=100, NUM_CASES_SHIPPED=100,
            YARD_WAIT_HRS=7.0, DOCK_HRS=0.0, DELAY_DAYS=0.0,
            HOT_PO_FLAG=0, IS_LATE="N",
        ),
        # ── PO-TS-RECPT: RECPT < CHECKIN (cond 3 de _ts_issue) ──────────────
        dict(
            PO_NBR="PO-TS-RECPT",
            PO_DT="2024-01-01 00:00", STA_DT="2024-01-05 00:00",
            APPROVED_DT="2024-01-04 00:00",
            DT_APPT_FIRST_APPROVED="2024-01-04 00:00",
            DT_APPT_CURRENT_APPROVED="2024-01-04 00:00",
            TRAILER_ARRIVE_DT="2024-01-04 02:00",
            CHECKIN_DT="2024-01-04 05:00", CHECKOUT_DT="2024-01-04 09:00",
            RECPT_DT="2024-01-04 03:00",     # antes que el check-in → inversión
            REQUESTED_DT="2024-01-01 00:00", FIRST_SUBMITTED_DT="2024-01-01 00:00",
            PREVIOUS_REQUEST_DT=NaT, TRAILER_DEPART_DT="2024-01-04 10:00",
            NUM_CASES_ORDERED=100, NUM_CASES_SHIPPED=100,
            YARD_WAIT_HRS=3.0, DOCK_HRS=4.0, DELAY_DAYS=0.0,
            HOT_PO_FLAG=0, IS_LATE="N",
        ),
        # ── PO-TS-STA: STA < PO (cond 4) + lead_time se clipa a 0 ───────────
        dict(
            PO_NBR="PO-TS-STA",
            PO_DT="2024-01-05 00:00", STA_DT="2024-01-01 00:00",  # STA antes que PO
            APPROVED_DT="2024-01-04 00:00",
            DT_APPT_FIRST_APPROVED="2024-01-04 00:00",
            DT_APPT_CURRENT_APPROVED="2024-01-04 00:00",
            TRAILER_ARRIVE_DT="2024-01-04 02:00",
            CHECKIN_DT="2024-01-04 05:00", CHECKOUT_DT="2024-01-04 09:00",
            RECPT_DT="2024-01-06 00:00",
            REQUESTED_DT="2024-01-01 00:00", FIRST_SUBMITTED_DT="2024-01-01 00:00",
            PREVIOUS_REQUEST_DT=NaT, TRAILER_DEPART_DT="2024-01-04 10:00",
            NUM_CASES_ORDERED=100, NUM_CASES_SHIPPED=100,
            YARD_WAIT_HRS=3.0, DOCK_HRS=4.0, DELAY_DAYS=5.0,
            HOT_PO_FLAG=0, IS_LATE="Y",
        ),
        # ── PO-NULLTRAILER: TRAILER_ARRIVE vacío → carrier_lag NaN → el flag
        #    de carrier miss queda silenciosamente False (hallazgo #16/B4) ────
        dict(
            PO_NBR="PO-NULLTRAILER",
            PO_DT="2024-01-01 00:00", STA_DT="2024-01-05 00:00",
            APPROVED_DT="2024-01-01 00:00",  # arribo "real" sería días después
            DT_APPT_FIRST_APPROVED="2024-01-01 00:00",
            DT_APPT_CURRENT_APPROVED="2024-01-01 00:00",
            TRAILER_ARRIVE_DT=NaT,           # ← el nulo
            CHECKIN_DT="2024-01-04 05:00", CHECKOUT_DT="2024-01-04 09:00",
            RECPT_DT="2024-01-06 00:00",
            REQUESTED_DT="2024-01-01 00:00", FIRST_SUBMITTED_DT="2024-01-01 00:00",
            PREVIOUS_REQUEST_DT=NaT, TRAILER_DEPART_DT="2024-01-04 10:00",
            NUM_CASES_ORDERED=100, NUM_CASES_SHIPPED=100,
            YARD_WAIT_HRS=0.0, DOCK_HRS=4.0, DELAY_DAYS=1.0,
            HOT_PO_FLAG=0, IS_LATE="Y",
        ),
        # ── PO-ZEROORD: NUM_CASES_ORDERED=0 → _fill_rate NaN, sin crash ─────
        dict(
            PO_NBR="PO-ZEROORD",
            PO_DT="2024-01-01 00:00", STA_DT="2024-01-05 00:00",
            APPROVED_DT="2024-01-04 00:00",
            DT_APPT_FIRST_APPROVED="2024-01-04 00:00",
            DT_APPT_CURRENT_APPROVED="2024-01-04 00:00",
            TRAILER_ARRIVE_DT="2024-01-04 02:00",
            CHECKIN_DT="2024-01-04 05:00", CHECKOUT_DT="2024-01-04 09:00",
            RECPT_DT="2024-01-05 00:00",
            REQUESTED_DT="2024-01-01 00:00", FIRST_SUBMITTED_DT="2024-01-01 00:00",
            PREVIOUS_REQUEST_DT=NaT, TRAILER_DEPART_DT="2024-01-04 10:00",
            NUM_CASES_ORDERED=0, NUM_CASES_SHIPPED=10,   # divisor 0
            YARD_WAIT_HRS=3.0, DOCK_HRS=4.0, DELAY_DAYS=0.0,
            HOT_PO_FLAG=0, IS_LATE="N",
        ),
        # ── PO-SHORTSHIP: shipped/ordered = 0.5 → _short_ship True ──────────
        dict(
            PO_NBR="PO-SHORTSHIP",
            PO_DT="2024-01-01 00:00", STA_DT="2024-01-05 00:00",
            APPROVED_DT="2024-01-04 00:00",
            DT_APPT_FIRST_APPROVED="2024-01-04 00:00",
            DT_APPT_CURRENT_APPROVED="2024-01-04 00:00",
            TRAILER_ARRIVE_DT="2024-01-04 02:00",
            CHECKIN_DT="2024-01-04 05:00", CHECKOUT_DT="2024-01-04 09:00",
            RECPT_DT="2024-01-05 00:00",
            REQUESTED_DT="2024-01-01 00:00", FIRST_SUBMITTED_DT="2024-01-01 00:00",
            PREVIOUS_REQUEST_DT=NaT, TRAILER_DEPART_DT="2024-01-04 10:00",
            NUM_CASES_ORDERED=100, NUM_CASES_SHIPPED=50,  # fill = 0.5
            YARD_WAIT_HRS=3.0, DOCK_HRS=4.0, DELAY_DAYS=0.0,
            HOT_PO_FLAG=0, IS_LATE="N",
        ),
        # ── PO-RESCHED: current != first approved → _rescheduled True ───────
        dict(
            PO_NBR="PO-RESCHED",
            PO_DT="2024-01-01 00:00", STA_DT="2024-01-05 00:00",
            APPROVED_DT="2024-01-04 00:00",
            DT_APPT_FIRST_APPROVED="2024-01-03 00:00",     # primera cita
            DT_APPT_CURRENT_APPROVED="2024-01-04 00:00",   # ≠ → reprogramado
            TRAILER_ARRIVE_DT="2024-01-04 02:00",
            CHECKIN_DT="2024-01-04 05:00", CHECKOUT_DT="2024-01-04 09:00",
            RECPT_DT="2024-01-05 00:00",
            REQUESTED_DT="2024-01-01 00:00", FIRST_SUBMITTED_DT="2024-01-01 00:00",
            PREVIOUS_REQUEST_DT=NaT, TRAILER_DEPART_DT="2024-01-04 10:00",
            NUM_CASES_ORDERED=100, NUM_CASES_SHIPPED=100,
            YARD_WAIT_HRS=3.0, DOCK_HRS=4.0, DELAY_DAYS=0.0,
            HOT_PO_FLAG=0, IS_LATE="N",
        ),
        # ── PO-HOTLATE: HOT_PO_FLAG=1 + IS_LATE='Y' → flag_hot_late True ────
        dict(
            PO_NBR="PO-HOTLATE",
            PO_DT="2024-01-01 00:00", STA_DT="2024-01-05 00:00",
            APPROVED_DT="2024-01-04 00:00",
            DT_APPT_FIRST_APPROVED="2024-01-04 00:00",
            DT_APPT_CURRENT_APPROVED="2024-01-04 00:00",
            TRAILER_ARRIVE_DT="2024-01-04 02:00",
            CHECKIN_DT="2024-01-04 05:00", CHECKOUT_DT="2024-01-04 09:00",
            RECPT_DT="2024-01-07 00:00",
            REQUESTED_DT="2024-01-01 00:00", FIRST_SUBMITTED_DT="2024-01-01 00:00",
            PREVIOUS_REQUEST_DT=NaT, TRAILER_DEPART_DT="2024-01-04 10:00",
            NUM_CASES_ORDERED=100, NUM_CASES_SHIPPED=100,
            YARD_WAIT_HRS=3.0, DOCK_HRS=4.0, DELAY_DAYS=2.0,
            HOT_PO_FLAG=1, IS_LATE="Y",
        ),
        # ── PO-XVAL-DISC: yard/dock calc difieren >1.0 del precalc ──────────
        #    calc: yard=3.0 (05:00-02:00), dock=4.0 (09:00-05:00).
        #    precalc YARD_WAIT_HRS=10.0, DOCK_HRS=20.0 → |3-10|=7>1, |4-20|=16>1.
        dict(
            PO_NBR="PO-XVAL-DISC",
            PO_DT="2024-01-01 00:00", STA_DT="2024-01-05 00:00",
            APPROVED_DT="2024-01-04 00:00",
            DT_APPT_FIRST_APPROVED="2024-01-04 00:00",
            DT_APPT_CURRENT_APPROVED="2024-01-04 00:00",
            TRAILER_ARRIVE_DT="2024-01-04 02:00",
            CHECKIN_DT="2024-01-04 05:00", CHECKOUT_DT="2024-01-04 09:00",
            RECPT_DT="2024-01-05 00:00",
            REQUESTED_DT="2024-01-01 00:00", FIRST_SUBMITTED_DT="2024-01-01 00:00",
            PREVIOUS_REQUEST_DT=NaT, TRAILER_DEPART_DT="2024-01-04 10:00",
            NUM_CASES_ORDERED=100, NUM_CASES_SHIPPED=100,
            YARD_WAIT_HRS=10.0, DOCK_HRS=20.0, DELAY_DAYS=0.0,
            HOT_PO_FLAG=0, IS_LATE="N",
        ),
        # ── PO-CARRIER-LATE: carrier domina el exceso → stage_primary='Carrier' ──
        #    Umbrales del mentor: carrier 8.0 / yard 4.0 / dock 6.0 h.
        #    carrier_lag=14h (exc 14-8=6) · yard=1h (exc 0) · dock=2h (exc 0) → exc_dc=0
        #    APPROVED(01-04) < STA(01-05) → appt_lead +1d → STA push 0 → gana Carrier.
        dict(
            PO_NBR="PO-CARRIER-LATE",
            PO_DT="2024-01-01 00:00", STA_DT="2024-01-05 00:00",
            APPROVED_DT="2024-01-04 00:00",
            DT_APPT_FIRST_APPROVED="2024-01-04 00:00",
            DT_APPT_CURRENT_APPROVED="2024-01-04 00:00",
            TRAILER_ARRIVE_DT="2024-01-04 14:00",   # lag 14h desde APPROVED
            CHECKIN_DT="2024-01-04 15:00",           # yard 1h
            CHECKOUT_DT="2024-01-04 17:00",          # dock 2h
            RECPT_DT="2024-01-05 12:00",             # delay 0.5 día
            REQUESTED_DT="2024-01-01 00:00", FIRST_SUBMITTED_DT="2024-01-01 00:00",
            PREVIOUS_REQUEST_DT=NaT, TRAILER_DEPART_DT="2024-01-04 18:00",
            NUM_CASES_ORDERED=100, NUM_CASES_SHIPPED=100,
            YARD_WAIT_HRS=1.0, DOCK_HRS=2.0, DELAY_DAYS=0.5,
            HOT_PO_FLAG=0, IS_LATE="Y",
            REASON_DSC="Carrier delivery delay",
        ),
        # ── PO-DOCK-LATE: dock domina DC → stage_primary='DC' (subclase Dock) ───
        #    carrier_lag=2h (exc 0) · yard=1h (exc 0) · dock=10h (exc 10-6=4) → exc_dc=4
        #    APPROVED(01-04) < STA(01-05) → STA push 0 → gana DC; exc_dock>exc_yard → Dock.
        dict(
            PO_NBR="PO-DOCK-LATE",
            PO_DT="2024-01-01 00:00", STA_DT="2024-01-05 00:00",
            APPROVED_DT="2024-01-04 00:00",
            DT_APPT_FIRST_APPROVED="2024-01-04 00:00",
            DT_APPT_CURRENT_APPROVED="2024-01-04 00:00",
            TRAILER_ARRIVE_DT="2024-01-04 02:00",    # lag 2h
            CHECKIN_DT="2024-01-04 03:00",           # yard 1h
            CHECKOUT_DT="2024-01-04 13:00",          # dock 10h
            RECPT_DT="2024-01-05 12:00",             # delay 0.5 día
            REQUESTED_DT="2024-01-01 00:00", FIRST_SUBMITTED_DT="2024-01-01 00:00",
            PREVIOUS_REQUEST_DT=NaT, TRAILER_DEPART_DT="2024-01-04 14:00",
            NUM_CASES_ORDERED=100, NUM_CASES_SHIPPED=100,
            YARD_WAIT_HRS=1.0, DOCK_HRS=10.0, DELAY_DAYS=0.5,
            HOT_PO_FLAG=0, IS_LATE="Y",
            REASON_DSC="Dock processing backlog",
        ),
        # ── PO-VENDOR-LATE: APPROVED > STA → STA push domina → stage_primary='Vendor' ──
        #    STA(01-04) → APPROVED(01-06): appt_lead_days = -2d → STA push = 48h.
        #    carrier_lag=2h (exc 0) · yard=1h (exc 0) · dock=2h (exc 0) → solo vendor.
        #    RECPT(01-07) > CHECKIN(01-06 03:00) y STA>PO → sin _ts_issue (DC medible).
        #    delay_days_calc = RECPT - STA = 3.0d. → gana Vendor con excess_vendor_hrs≈48.
        dict(
            PO_NBR="PO-VENDOR-LATE",
            PO_DT="2024-01-01 00:00", STA_DT="2024-01-04 00:00",
            APPROVED_DT="2024-01-06 00:00",                 # APPROVED > STA → push
            DT_APPT_FIRST_APPROVED="2024-01-06 00:00",
            DT_APPT_CURRENT_APPROVED="2024-01-06 00:00",
            TRAILER_ARRIVE_DT="2024-01-06 02:00",            # carrier 2h
            CHECKIN_DT="2024-01-06 03:00",                   # yard 1h
            CHECKOUT_DT="2024-01-06 05:00",                  # dock 2h
            RECPT_DT="2024-01-07 00:00",                     # > CHECKIN → sin inversión
            REQUESTED_DT="2024-01-01 00:00", FIRST_SUBMITTED_DT="2024-01-01 00:00",
            PREVIOUS_REQUEST_DT=NaT, TRAILER_DEPART_DT="2024-01-08 00:00",
            NUM_CASES_ORDERED=100, NUM_CASES_SHIPPED=100,
            YARD_WAIT_HRS=1.0, DOCK_HRS=2.0, DELAY_DAYS=3.0,
            HOT_PO_FLAG=0, IS_LATE="Y",
            REASON_DSC="Vendor delayed shipment",
        ),
        # ── PO-HOT-HIGH: HOT_PO_FLAG=1 + delay>3 → severity='HIGH' (gate del mentor) ──
        #    Sin exceso en ningún tramo (carrier/yard/dock bajo umbral) y APPROVED<STA
        #    (push 0) → stage_primary='Indeterminado'; pero la severidad NO depende de la
        #    etapa: HOT + delay 4.0 (>3) → HIGH determinístico. delay=RECPT-STA=4d.
        dict(
            PO_NBR="PO-HOT-HIGH",
            PO_DT="2024-01-01 00:00", STA_DT="2024-01-05 00:00",
            APPROVED_DT="2024-01-04 00:00",
            DT_APPT_FIRST_APPROVED="2024-01-04 00:00",
            DT_APPT_CURRENT_APPROVED="2024-01-04 00:00",
            TRAILER_ARRIVE_DT="2024-01-04 02:00",            # carrier 2h
            CHECKIN_DT="2024-01-04 05:00", CHECKOUT_DT="2024-01-04 09:00",  # yard 3h, dock 4h
            RECPT_DT="2024-01-09 00:00",                     # delay = 4 días
            REQUESTED_DT="2024-01-01 00:00", FIRST_SUBMITTED_DT="2024-01-01 00:00",
            PREVIOUS_REQUEST_DT=NaT, TRAILER_DEPART_DT="2024-01-04 10:00",
            NUM_CASES_ORDERED=100, NUM_CASES_SHIPPED=100,
            YARD_WAIT_HRS=3.0, DOCK_HRS=4.0, DELAY_DAYS=4.0,
            HOT_PO_FLAG=1, IS_LATE="Y",
        ),
        # ── PO-VENDOR-SUBUMBRAL: STA push POSITIVO pero BAJO el umbral de 24h ────
        #    APPROVED(01-04 12:00) > STA(01-04 00:00): appt_lead_days = -0.5d → push 12h.
        #    12h < vendor_gap_hrs(24) → excess_vendor_hrs = max(0, 12 - 24) = 0.
        #    carrier 2h / yard 1h / dock 2h, todos bajo umbral (exc 0). RECPT>STA → tardío.
        #    Caso límite de T7: con la señal vieja (appt_lead_days<0) stage_multi pondría
        #    'Vendor'; con la alineada (excess_vendor_hrs>0) NO debe ponerlo (push sub-umbral).
        dict(
            PO_NBR="PO-VENDOR-SUBUMBRAL",
            PO_DT="2024-01-01 00:00", STA_DT="2024-01-04 00:00",
            APPROVED_DT="2024-01-04 12:00",                  # push 12h (< 24h umbral)
            DT_APPT_FIRST_APPROVED="2024-01-04 12:00",
            DT_APPT_CURRENT_APPROVED="2024-01-04 12:00",
            TRAILER_ARRIVE_DT="2024-01-04 14:00",            # carrier 2h
            CHECKIN_DT="2024-01-04 15:00",                   # yard 1h
            CHECKOUT_DT="2024-01-04 17:00",                  # dock 2h
            RECPT_DT="2024-01-05 00:00",                     # > CHECKIN → sin inversión; delay 1d
            REQUESTED_DT="2024-01-01 00:00", FIRST_SUBMITTED_DT="2024-01-01 00:00",
            PREVIOUS_REQUEST_DT=NaT, TRAILER_DEPART_DT="2024-01-05 02:00",
            NUM_CASES_ORDERED=100, NUM_CASES_SHIPPED=100,
            YARD_WAIT_HRS=1.0, DOCK_HRS=2.0, DELAY_DAYS=1.0,
            HOT_PO_FLAG=0, IS_LATE="Y",
        ),
    ]
    return pd.DataFrame(rows)


# ── Fixtures ─────────────────────────────────────────────────────────────────
@pytest.fixture
def df_raw() -> pd.DataFrame:
    """DataFrame sintético CRUDO (fechas como strings), tal cual lo recibiría
    clean_po_data desde un read_csv."""
    return _build_raw()


@pytest.fixture
def df_clean(df_raw) -> pd.DataFrame:
    """df_raw pasado por clean_po_data() una sola vez. La mayoría de los tests
    consumen este."""
    return clean_po_data(df_raw)


@pytest.fixture
def df_xval(df_clean) -> pd.DataFrame:
    """df_clean pasado además por cross_validate_deltas() (añade las columnas de
    discrepancia). Para los tests de cross-validation."""
    return cross_validate_deltas(df_clean)
