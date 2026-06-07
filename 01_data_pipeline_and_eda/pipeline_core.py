# ── Imports requeridos  ─────────────────────────────────────────────────────
import numpy as np
import pandas as pd
import os


def clean_po_data(df_input: pd.DataFrame) -> pd.DataFrame:
    """
    Pipeline de limpieza y enriquecimiento del dataset de PO Root Cause.

    Input:  DataFrame crudo del CSV po_root_cause_synthetic.csv
    Output: DataFrame enriquecido con:
            - Timestamps parseados a datetime
            - Flags de calidad de datos (_ts_issue, _trailer_arrive_null)
            - Deltas calculados (yard_wait_calc_hrs, dock_calc_hrs, carrier_lag_hrs, etc.)
            - Flags de clasificación (flag_yard_congestion, flag_dock_backlog, etc.)
            - Flags operacionales (_rescheduled, _short_ship, _fill_rate)
    """
    df = df_input.copy()

    # ── 1. Parsear timestamps ────────────────────────────────────────────────
    DATE_COLS = [
        'PO_DT', 'STA_DT', 'RECPT_DT',
        'REQUESTED_DT', 'FIRST_SUBMITTED_DT',
        'DT_APPT_FIRST_APPROVED', 'APPROVED_DT', 'DT_APPT_CURRENT_APPROVED',
        'PREVIOUS_REQUEST_DT',
        'TRAILER_ARRIVE_DT', 'CHECKIN_DT', 'CHECKOUT_DT', 'TRAILER_DEPART_DT'
    ]
    for col in DATE_COLS:
        df[col] = pd.to_datetime(df[col], errors='coerce')

    # ── 2. Flags de calidad ──────────────────────────────────────────────────
    df['_trailer_arrive_null'] = df['TRAILER_ARRIVE_DT'].isna()
    df['_ts_issue'] = (
        (df['CHECKIN_DT']  < df['TRAILER_ARRIVE_DT']) |
        (df['CHECKOUT_DT'] < df['CHECKIN_DT'])         |
        (df['RECPT_DT']    < df['CHECKIN_DT'])         |
        (df['STA_DT']      < df['PO_DT'])
    ).fillna(False)
    df['_data_reliable'] = (~df['_ts_issue']) & (~df['_trailer_arrive_null'])

    # ── 3. Métricas operacionales ────────────────────────────────────────────
    df['_rescheduled'] = (
        df['DT_APPT_CURRENT_APPROVED'] != df['DT_APPT_FIRST_APPROVED']
    ).fillna(False)

    df['_fill_rate'] = (
        df['NUM_CASES_SHIPPED'] / df['NUM_CASES_ORDERED'].replace(0, np.nan)
    ).clip(0, 1)
    df['_short_ship'] = df['_fill_rate'] < 0.90

    # ── 4. Deltas de tiempo ──────────────────────────────────────────────────
    def hrs(series): return series.dt.total_seconds() / 3600
    def days(series): return series.dt.total_seconds() / 86400

    df['lead_time_days']    = days(df['STA_DT']            - df['PO_DT']).clip(lower=0)
    df['carrier_lag_hrs']   = hrs(df['TRAILER_ARRIVE_DT']  - df['APPROVED_DT'])
    df['yard_wait_calc_hrs']= hrs(df['CHECKIN_DT']         - df['TRAILER_ARRIVE_DT']).clip(lower=0)
    df['dock_calc_hrs']     = hrs(df['CHECKOUT_DT']        - df['CHECKIN_DT']).clip(lower=0)
    df['total_dc_hrs']      = hrs(df['CHECKOUT_DT']        - df['TRAILER_ARRIVE_DT']).clip(lower=0)
    df['appt_lead_days']    = days(df['STA_DT']            - df['APPROVED_DT'])
    df['delay_days_calc']   = days(df['RECPT_DT']          - df['STA_DT']).clip(lower=0)

    # ── 5. Flags de clasificación por etapa ──────────────────────────────────
    YARD_THR    = 4.0
    DOCK_THR    = 6.0
    CARRIER_THR = 4.0
    LEAD_THR    = 3.0

    df['flag_yard_congestion'] = df['YARD_WAIT_HRS'] > YARD_THR
    df['flag_dock_backlog']    = df['DOCK_HRS']      > DOCK_THR
    df['flag_carrier_miss']    = df['carrier_lag_hrs'] > CARRIER_THR
    df['flag_short_lead_time'] = df['lead_time_days']  < LEAD_THR
    df['flag_hot_late']        = (df['HOT_PO_FLAG'] == 1) & (df['IS_LATE'] == 'Y')

    return df


def cross_validate_deltas(df: pd.DataFrame) -> pd.DataFrame:
    """
    Cross-validation: deltas calculados desde timestamps vs columnas precalculadas.

    Los timestamps son la fuente de verdad; las discrepancias son hallazgos
    (no errores). Compara yard_wait_calc_hrs / dock_calc_hrs / delay_days_calc
    contra YARD_WAIT_HRS / DOCK_HRS / DELAY_DAYS, imprime el reporte y marca las
    discrepancias significativas (> 1.0).

    Input:  DataFrame ya enriquecido por clean_po_data() (necesita las columnas
            *_calc y las precalculadas del CSV).
    Output: el mismo DataFrame con _yard_discrepancy y _dock_discrepancy añadidas.
    """
    print('-- Cross-validation: calculados vs pre-calculados -----------------------')

    delta_yard = (df['yard_wait_calc_hrs'] - df['YARD_WAIT_HRS']).abs()
    delta_dock = (df['dock_calc_hrs'] - df['DOCK_HRS']).abs()
    delta_delay = (df['delay_days_calc'] - df['DELAY_DAYS']).abs()

    print(f'  YARD_WAIT_HRS  - diferencia media: {delta_yard.mean():.3f}h, max: {delta_yard.max():.3f}h')
    print(f'  DOCK_HRS       - diferencia media: {delta_dock.mean():.3f}h, max: {delta_dock.max():.3f}h')
    print(f'  DELAY_DAYS     - diferencia media: {delta_delay.mean():.3f}d, max: {delta_delay.max():.3f}d')

    # Marcar discrepancias significativas
    df['_yard_discrepancy'] = delta_yard > 1.0
    df['_dock_discrepancy'] = delta_dock > 1.0

    print(f'\n  POs con discrepancia de yard > 1h: {df["_yard_discrepancy"].sum()}')
    print(f'  POs con discrepancia de dock > 1h: {df["_dock_discrepancy"].sum()}')

    return df


# ── AGREGADO: Envolver el bloque de ejecución para proteger el módulo ────────
if __name__ == "__main__":
    # Imports solo necesarios para la ejecución como script (no para importar el
    # módulo): se mantienen dentro del guard para que `import pipeline_core` siga
    # siendo barato y no exija python-dotenv solo para usar la función.
    from pathlib import Path
    from dotenv import load_dotenv

    # 1. Resolver la raíz del repo desde la ubicación del módulo (no desde el cwd).
    #    Mismo patrón acordado en #11 (celda 4 del notebook), pero usando __file__
    #    porque para un módulo lo correcto es ubicarse por su archivo, no por
    #    desde dónde se ejecute.
    REPO_ROOT = Path(__file__).resolve().parent
    if REPO_ROOT.name == "01_data_pipeline_and_eda":
        REPO_ROOT = REPO_ROOT.parent

    load_dotenv(REPO_ROOT / ".env", override=True)

    # 2. Resolver la ruta al CSV: respeta PO_CSV_PATH si está definida; si no, el
    #    default convencional bajo la raíz del repo (data/raw/).
    _env_path = os.environ.get("PO_CSV_PATH")
    csv_path = Path(_env_path) if _env_path else REPO_ROOT / "data" / "raw" / "po_root_cause_synthetic.csv"

    try:
        # 3. Intentar cargar únicamente el archivo local
        df_raw = pd.read_csv(csv_path, low_memory=False)
        print(f"[OK] Archivo local cargado exitosamente desde: {csv_path}")

    except FileNotFoundError:
        # 4. Mensaje de error detallado para el equipo de desarrollo
        error_msg = (
            f"\nERROR: Archivo no encontrado.\n"
            f"Debido a que la carpeta 'data/' está en .gitignore, debes colocar manualmente el archivo en:\n"
            f"  {csv_path}\n"
            f"Asegúrate de crear las carpetas 'data/' y 'raw/' en la raíz de tu repositorio local,\n"
            f"o define PO_CSV_PATH=/ruta/completa.csv en el archivo .env de la raíz."
        )
        raise FileNotFoundError(error_msg)


# ── Ejecutar y validar ───────────────────────────────────────────────────────
    df_clean = clean_po_data(df_raw)

    print('[OK] clean_po_data() ejecutado correctamente')
    print(f'   Shape:                      {df_clean.shape}')
    print(f'   Columnas agregadas:         {df_clean.shape[1] - df_raw.shape[1]}')
    print(f'   POs con datos confiables:   {df_clean["_data_reliable"].sum()} / {len(df_clean)}')
    print(f'   POs rescheduled:            {df_clean["_rescheduled"].sum()}')
    print(f'   Short ships:                {df_clean["_short_ship"].sum()}')
    print(f'   Flag yard congestion:       {df_clean["flag_yard_congestion"].sum()}')
    print(f'   Flag dock backlog:          {df_clean["flag_dock_backlog"].sum()}')
    print(f'   Flag carrier miss:          {df_clean["flag_carrier_miss"].sum()}')

    # Cross-validation: deltas calculados vs columnas precalculadas
    print()
    df_clean = cross_validate_deltas(df_clean)

    # Nuevas columnas
    new_cols = [c for c in df_clean.columns if c not in df_raw.columns]
    print(f'\nColumnas nuevas: {new_cols}')