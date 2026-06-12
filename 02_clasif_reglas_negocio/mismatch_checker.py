####################################################################################
# PENDIENTE CONVERTIR A MODULO EXPORTABLE
# PENDIENTE AGREGAR DEPENDENCIAS (pandas, numpy)


# modulo aplicable a la salida del classifier.py, para comparar reason_group_manual vs reason_group_auto
# y generar métricas de desacuerdo (mismatch) para auditoría y mejora continua del modelo.


def _mismatch_type(manual: str, auto_base: str) -> str:
    """Genera etiqueta descriptiva del tipo de desacuerdo."""
    m = str(manual).strip()
    a = str(auto_base).strip()
    if m == a or m == 'On-Time' or a == 'On-Time':
        return 'Match'
    combos = {
        ('Vendor',  'Carrier')  : 'Vendor culpado — TS indica Carrier',
        ('Vendor',  'DC')       : 'Vendor culpado — TS indica DC',
        ('Vendor',  'Vendor + DC'): 'Vendor culpado — TS indica Vendor+DC',
        ('Carrier', 'Vendor')   : 'Carrier culpado — TS indica Vendor',
        ('Carrier', 'DC')       : 'Carrier culpado — TS indica DC',
        ('Carrier', 'Vendor + DC'): 'Carrier culpado — TS indica Vendor+DC',
        ('DC',      'Vendor')   : 'DC culpado — TS indica Vendor',
        ('DC',      'Carrier')  : 'DC culpado — TS indica Carrier',
        ('DC',      'Vendor + Carrier'): 'DC culpado — TS indica Vendor+Carrier',
        ('Unknown', 'Vendor')   : 'Sin causa manual — TS indica Vendor',
        ('Unknown', 'Carrier')  : 'Sin causa manual — TS indica Carrier',
        ('Unknown', 'DC')       : 'Sin causa manual — TS indica DC',
    }
    if (m, a) in combos:
        return combos[(m, a)]
    if '+' in a:
        if m in a:
            return f'{m} culpado — TS indica co-responsabilidad ({a})'
        return f'{m} culpado — TS indica múltiples ({a})'
    return f'{m} → {a}'


def _mismatch_severity_label(mismatch_type: str) -> str:
    """
    Alta: inversión total de culpa (Vendor↔Carrier, Vendor↔DC)
    Media: mismatch parcial (subconjunto o co-responsabilidad)
    Baja: desacuerdo menor (Unknown vs algo)
    None: Match
    """
    if mismatch_type == 'Match':
        return 'None'
    altas = [
        'Vendor culpado — TS indica Carrier',
        'Carrier culpado — TS indica Vendor',
        'Vendor culpado — TS indica DC',
        'DC culpado — TS indica Carrier',
        'DC culpado — TS indica Vendor',
        'Carrier culpado — TS indica DC',
    ]
    if mismatch_type in altas:
        return 'Alta'
    if 'co-responsabilidad' in mismatch_type or 'múltiples' in mismatch_type:
        return 'Media'
    return 'Baja'


def _mismatch_detail(row: pd.Series) -> str:
    """Texto narrativo con valores reales de timestamps y umbrales."""
    parts = [
        f"Manual='{row.get('reason_group_manual','?')}'"
        f" | Auto='{row.get('stage_class','?')}'"
    ]
    cl = row.get('carrier_lag_hrs', np.nan)
    yc = row.get('yard_wait_calc_hrs', np.nan)
    dc = row.get('dock_calc_hrs', np.nan)
    dl = row.get('delay_days_calc', np.nan)

    if pd.notna(cl): parts.append(f"carrier_lag={cl:.1f}h (umbral {CARRIER_LAG_STRONG}h)")
    if pd.notna(yc): parts.append(f"yard_wait={yc:.1f}h (umbral {YARD_THR}h)")
    if pd.notna(dc): parts.append(f"dock={dc:.1f}h (umbral {DOCK_THR}h)")
    if pd.notna(dl): parts.append(f"delay={dl:.1f}d")
    return ' | '.join(parts)


# ── Función principal ─────────────────────────────────────────────────────

def mismatch_po(df_input: pd.DataFrame) -> pd.DataFrame:
    """
    Agrega columnas de auditoría de mismatch al df_classif:

    appt_pushed_hrs        — desplazamiento del appointment (primera vez calculado)
    feat_appt_push_severity— categoría del push (no_push/minor_push/day_push/major_push)
    mismatch_flag          — booleano: ¿manual ≠ auto?
    mismatch_partial       — booleano: coincidencia parcial (subconjunto)
    mismatch_type          — etiqueta descriptiva del desacuerdo
    mismatch_detail        — texto narrativo con valores reales
    mismatch_severity      — Alta / Media / Baja / None
    _severity              — banda de severidad (Low/Medium/High/Critical/On-Time)
    """
    df = df_input.copy()

    # ── appt_pushed_hrs ───────────────────────────────────────────────────
    # Primera vez que se calcula; no viene en df_clean.csv
    df['appt_pushed_hrs'] = (
        (df['DT_APPT_CURRENT_APPROVED'] - df['DT_APPT_FIRST_APPROVED'])
        .dt.total_seconds() / 3600
    )

    # ── feat_appt_push_severity ───────────────────────────────────────────
    def _push_cat(hrs):
        if pd.isna(hrs) or hrs == 0:   return 'no_push'
        if 0  < hrs <= 12:              return 'minor_push'
        if 12 < hrs <= 24:              return 'day_push'
        return                                 'major_push'

    df['feat_appt_push_severity'] = df['appt_pushed_hrs'].apply(_push_cat)

    # ── auto_base (sin modificadores entre paréntesis) ────────────────────
    df['_auto_base'] = df['reason_group_auto'].apply(_get_auto_base)

    # ── mismatch_flag ─────────────────────────────────────────────────────
    df['mismatch_flag'] = (
        (df['IS_LATE'] == 'Y') &
        (df['reason_group_manual'] != df['_auto_base'])
    )

    # ── mismatch_partial ──────────────────────────────────────────────────
    def _is_partial(row):
        if not row['mismatch_flag']:
            return False
        manual = str(row['reason_group_manual'])
        auto   = str(row['_auto_base'])
        # manual está contenido dentro de un auto multi-causante
        if '+' in auto and manual in auto:
            return True
        # auto está contenido dentro de un manual multi-causante
        if '+' in manual and auto in manual:
            return True
        return False

    df['mismatch_partial']  = df.apply(_is_partial, axis=1)

    # ── mismatch_type & detail ────────────────────────────────────────────
    df['mismatch_type']   = df.apply(
        lambda r: _mismatch_type(r['reason_group_manual'], r['_auto_base']), axis=1
    )
    df['mismatch_detail'] = df.apply(_mismatch_detail, axis=1)

    # ── mismatch_severity ─────────────────────────────────────────────────
    df['mismatch_severity'] = df['mismatch_type'].apply(_mismatch_severity_label)

    # Limpieza de columna auxiliar
    df = df.drop(columns=['_auto_base'])

    # Guardar
    df.to_csv('df_mismatch.csv',encoding="utf-8-sig", index=False)

    # ── Resumen ───────────────────────────────────────────────────────────
    late_m = df['IS_LATE'] == 'Y'
    n_mm   = df['mismatch_flag'].sum()
    n_part = df['mismatch_partial'].sum()

    print("\n✅ mismatch_po() ejecutado correctamente.")
    print(f"   Shape: {df.shape[0]:,} × {df.shape[1]} columnas")
    print(f"   Columnas nuevas: appt_pushed_hrs | feat_appt_push_severity |")
    print(f"                    mismatch_flag | mismatch_partial | mismatch_type |")
    print(f"                    mismatch_detail | mismatch_severity")
    print(f"\n   mismatch_flag = True : {n_mm} POs  ({n_mm/late_m.sum():.1%} de tardías)")
    print(f"   mismatch_partial     : {n_part} POs")
    print(f"\n   Severidad del mismatch:")
    print(df[df['mismatch_flag']]['mismatch_severity'].value_counts().to_string())
    print(f"\n   Appointment push (tardías):")
    print(df[late_m]['feat_appt_push_severity'].value_counts().to_string())
    print("\n   Guardado: df_mismatch.csv")
    return df


# ── Ejecutar ─────────────────────────────────────────────────────────────
df_mismatch = mismatch_po(df_classif)

df_mismatch[[
    'PO_NBR','IS_LATE','reason_group_manual','reason_group_auto',
    'mismatch_flag','mismatch_partial','mismatch_type',
    'mismatch_severity','appt_pushed_hrs','feat_appt_push_severity','_severity'
]].head(10)
