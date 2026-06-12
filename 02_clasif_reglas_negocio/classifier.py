####################################################################################
# PENDIENTE CONVERTIR A MODULO EXPORTABLE
# PENDIENTE AGREGAR DEPENDENCIAS (pandas, numpy)


# ═══════════════════════════════════════════════════════════════════════
# MAPEO MANUAL: REASON_DSC → reason_group_manual
# ═══════════════════════════════════════════════════════════════════════
REASON_DSC_MAP = {
    'Rescheduled by vendor'              : 'Vendor',
    'Vendor delayed shipment'            : 'Vendor',
    'Carrier delivery delay'             : 'Carrier',
    'Equipment/trailer issue'            : 'Carrier',
    'Weather/road conditions'            : 'Carrier',
    'Missed appointment window'          : 'Carrier',
    'Yard congestion - no available door': 'DC',
    'Dock processing backlog'            : 'DC',
    'Other'                              : 'Unknown',
    'Not applicable'                     : 'On-Time',
}


# ═══════════════════════════════════════════════════════════════════════
# LÓGICA DE CLASIFICACIÓN AUTOMÁTICA
# #
# Señales por etapa:
#   CARRIER  → carrier_lag_hrs > CARRIER_LAG_STRONG (6h)
#              (discriminador altamente efectivo, EDA Fase 1)
#   DC       → yard_wait_calc_hrs > YARD_THR (4h)
#              OR dock_calc_hrs > DOCK_THR (6h)
#   VENDOR   → _rescheduled, _short_ship, flag_short_lead_time  [explícito]
#              OR: PO tardía (delay_days_calc > 0) sin señales de Carrier ni DC
#       
# 
# !!!!! TEMPORAL:
#        [por eliminación "VENDOR" — la demora existe y no se atribuye a otro]
# ═══════════════════════════════════════════════════════════════════════

def _compute_flags(row: pd.Series) -> dict:
    """Evalúa las señales booleanas de cada etapa desde columnas calculadas."""
    carrier_lag = float(row.get('carrier_lag_hrs', 0) or 0)
    yard_calc   = float(row.get('yard_wait_calc_hrs', 0) or 0)
    dock_calc   = float(row.get('dock_calc_hrs', 0) or 0)
    delay       = float(row.get('delay_days_calc', 0) or 0)

    carrier_flag   = carrier_lag > CARRIER_LAG_STRONG
    dc_flag        = (yard_calc > YARD_THR) or (dock_calc > DOCK_THR)

    vendor_explicit = (
        bool(row.get('_rescheduled', False)) or
        bool(row.get('_short_ship', False))  or
        bool(row.get('flag_short_lead_time', False))
    )
    # Vendor por eliminación: PO confirmada tardía, sin evidencia Carrier/DC
    vendor_fallback = (delay > 0) and (not carrier_flag) and (not dc_flag)
    vendor_flag     = vendor_explicit or vendor_fallback

    return {
        'vendor_flag'     : vendor_flag,
        'vendor_explicit' : vendor_explicit,
        'vendor_fallback' : vendor_fallback,
        'carrier_flag'    : carrier_flag,
        'dc_flag'         : dc_flag,
    }


def _stage_from_flags(flags: dict) -> str:
    """Combina los 3 flags en una de las 8 etiquetas de stage_class."""
    v = flags['vendor_flag']
    c = flags['carrier_flag']
    d = flags['dc_flag']
    count = sum([v, c, d])

    if count == 0:
        return 'None'
    elif count == 3:
        return 'Vendor + Carrier + DC'
    elif v and c:
        return 'Vendor + Carrier'
    elif v and d:
        return 'Vendor + DC'
    elif c and d:
        return 'Carrier + DC'
    elif v:
        return 'Vendor'
    elif c:
        return 'Carrier'
    else:
        return 'DC'


def _add_vendor_modifiers(base_stage: str, row: pd.Series) -> str:
    """
    Agrega sufijos narrativos cuando hay señales explícitas de Vendor
    pero el causante principal identificado NO es Vendor.
    Ej: 'Carrier (+ vendor_rescheduled)'
    """
    suffix = ''
    if bool(row.get('_rescheduled', False)) and 'Vendor' not in base_stage:
        suffix += ' (+ vendor_rescheduled)'
    if bool(row.get('_short_ship', False)) and 'Vendor' not in base_stage:
        suffix += ' (+ vendor_short_ship)'
    return base_stage + suffix


def classify_po(df_input: pd.DataFrame) -> pd.DataFrame:
    """
    Clasifica cada PO con:
      reason_group_manual  — mapeo de REASON_DSC a grupo
      stage_class          — clasificación automática (8 etiquetas)
      reason_group_auto    — stage_class + modificadores vendor narrativos
      confidence           — High / Medium / Low
      _severity_score      — puntaje 0–100
      _severity            — banda Low / Medium / High / Critical / On-Time
    """
    df = df_input.copy()

    # 3.1 ── reason_group_manual ──────────────────────────────────────────
    df['reason_group_manual'] = (
        df['REASON_DSC'].map(REASON_DSC_MAP).fillna('Unknown')
    )

    # 3.2 ── Clasificación automática por fila ────────────────────────────
    stages, reasons_auto, confidences = [], [], []

    for _, row in df.iterrows():

        # On-Time: regla prioritaria — alta confianza siempre
        if row.get('IS_LATE') != 'Y':
            stages.append('On-Time')
            reasons_auto.append('On-Time')
            confidences.append('High')
            continue

        flags    = _compute_flags(row)
        stage    = _stage_from_flags(flags)
        reason_a = _add_vendor_modifiers(stage, row)

        stages.append(stage)
        reasons_auto.append(reason_a)

        # Confianza basada en calidad de datos
        if not row.get('_data_reliable', False):
            conf = 'Low'
        elif stage in ('None', 'Unknown'):
            conf = 'Medium'
        else:
            conf = 'High'
        confidences.append(conf)

    df['stage_class']       = stages
    df['reason_group_auto'] = reasons_auto
    df['confidence']        = confidences

    # 3.3 ── Severity Score ───────────────────────────────────────────────
    df['_severity_score'] = df.apply(compute_severity_score, axis=1)
    df['_severity']       = df['_severity_score'].apply(severity_band)

    return df


# ── Ejecutar ─────────────────────────────────────────────────────────────
df_classif = classify_po(df)
df_classif.to_csv('df_classif.csv',encoding="utf-8-sig", index=False)

# ── Resumen de salida ─────────────────────────────────────────────────────
late_mask = df_classif['IS_LATE'] == 'Y'
none_late = (df_classif[late_mask]['stage_class'] == 'None').sum()

print("\n✅ classify_po() ejecutado correctamente.")
print(f"   Shape: {df_classif.shape[0]:,} × {df_classif.shape[1]} columnas")
print(f"   Columnas nuevas: reason_group_manual | stage_class | reason_group_auto | confidence | _severity_score | _severity")
print(f"\n   POs tardías con stage_class == 'None': {none_late}  ← debe ser 0")

print(f"\n   Distribución stage_class (tardías):")
print(df_classif[late_mask]['stage_class'].value_counts().to_string())

print(f"\n   Distribución _severity (tardías):")
print(df_classif[late_mask]['_severity'].value_counts().to_string())

print(f"\n   Confianza del clasificador:")
print(df_classif[late_mask]['confidence'].value_counts().to_string())

print("\n   Guardado: df_classif.csv")
print()
df_classif[['PO_NBR','IS_LATE','reason_group_manual','reason_group_auto',
            'confidence','_severity_score','_severity']].head(10)
