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


# ── Ejecutar y validar ───────────────────────────────────────────────────────
df_clean = clean_po_data(df_raw)

print('✅ clean_po_data() ejecutado correctamente')
print(f'   Shape:                      {df_clean.shape}')
print(f'   Columnas agregadas:         {df_clean.shape[1] - df_raw.shape[1]}')
print(f'   POs con datos confiables:   {df_clean["_data_reliable"].sum()} / {len(df_clean)}')
print(f'   POs rescheduled:            {df_clean["_rescheduled"].sum()}')
print(f'   Short ships:                {df_clean["_short_ship"].sum()}')
print(f'   Flag yard congestion:       {df_clean["flag_yard_congestion"].sum()}')
print(f'   Flag dock backlog:          {df_clean["flag_dock_backlog"].sum()}')
print(f'   Flag carrier miss:          {df_clean["flag_carrier_miss"].sum()}')

# Nuevas columnas
new_cols = [c for c in df_clean.columns if c not in df_raw.columns]
print(f'\nColumnas nuevas: {new_cols}')