# ── Imports requeridos  ─────────────────────────────────────────────────────
import os
from pathlib import Path

import numpy as np
import pandas as pd


# ── Contrato de entrada (T2 · A-D2-1) ────────────────────────────────────────
# Columnas CRUDAS que clean_po_data() necesita del CSV (extremo productor del
# handoff 1→2). Si falta cualquiera, el pipeline fallaba aguas adentro con un
# KeyError opaco (en el loop de fechas o al calcular un delta); declararlas y
# validarlas aquí convierte ese fallo en un error que NOMBRA la columna ausente.
#
# _DATE_INPUT_COLUMNS — las columnas que se parsean a datetime (bloque 1). Es la
#   FUENTE DE VERDAD de "qué columna es fecha"; un lector que reconstruya el handoff
#   desde el CSV (donde las fechas son texto) reparsea exactamente estas (no por un
#   heurístico de sufijo: DT_APPT_FIRST_APPROVED es fecha y no termina en _DT).
_DATE_INPUT_COLUMNS = [
    "PO_DT", "STA_DT", "RECPT_DT",
    "REQUESTED_DT", "FIRST_SUBMITTED_DT",
    "DT_APPT_FIRST_APPROVED", "APPROVED_DT", "DT_APPT_CURRENT_APPROVED",
    "PREVIOUS_REQUEST_DT",
    "TRAILER_ARRIVE_DT", "CHECKIN_DT", "CHECKOUT_DT", "TRAILER_DEPART_DT",
]
# El resto de columnas crudas requeridas (no fechas): cantidades para el fill rate,
# flags precalc (YARD/DOCK_HRS) y contexto (HOT_PO_FLAG, IS_LATE).
_REQUIRED_INPUT_COLUMNS = _DATE_INPUT_COLUMNS + [
    "NUM_CASES_ORDERED", "NUM_CASES_SHIPPED",
    "YARD_WAIT_HRS", "DOCK_HRS",
    "HOT_PO_FLAG", "IS_LATE",
]


# ── Umbrales PRELIMINARES del EDA de Fase 1 (T14) ────────────────────────────
# Externalizados a constantes de módulo (antes eran literales duplicados entre esta
# función y el notebook → riesgo de divergencia). El notebook las IMPORTA, no las
# redeclara, para que haya una sola fuente. Son EXPLORATORIOS: las flags de F1 que
# dependen de ellos sirvieron al EDA, pero NO son los umbrales de clasificación.
# Los VIGENTES (para asignar la etapa) viven en 02_.../rules_config.json y los lee
# Fase 2 por nombre. El de carrier de F1 (4h) está SUPERADO por el del mentor (8h,
# validación 06-16); se conserva el 4h aquí solo para no alterar el EDA histórico.
_YARD_THR_EDA    = 4.0
_DOCK_THR_EDA    = 6.0
_CARRIER_THR_EDA = 4.0   # preliminar / superado por 8h en Fase 2 (no es el carrier definitivo)
_LEAD_THR_EDA    = 3.0


def clean_po_data(df_input: pd.DataFrame) -> pd.DataFrame:
    """
    Pipeline de limpieza y enriquecimiento del dataset de PO Root Cause.

    Contrato de entrada (T2): el DataFrame crudo debe traer las columnas de
    _REQUIRED_INPUT_COLUMNS (las que esta función referencia). Se validan al inicio:
    si falta alguna, se lanza KeyError NOMBRÁNDOLA, en vez de fallar aguas adentro
    con un mensaje opaco. No se valida el TIPO ni la NULIDAD: las fechas se parsean
    con errors='coerce' (un valor inválido → NaT, tratado por las flags de calidad
    _ts_issue/_trailer_arrive_null), y las cantidades con divisor 0 → fill rate NaN
    (manejado en el bloque 3). Es decir, el contrato exige PRESENCIA de columna;
    los valores presentes-pero-inválidos los absorbe el pipeline como dato sucio.

    Input:  DataFrame crudo del CSV po_root_cause_synthetic.csv, con al menos las
            columnas de _REQUIRED_INPUT_COLUMNS.
    Output: DataFrame enriquecido con:
            - Timestamps parseados a datetime
            - Flags de calidad de datos (_ts_issue, _trailer_arrive_null)
            - Deltas calculados (yard_wait_calc_hrs, dock_calc_hrs, carrier_lag_hrs, etc.)
            - Flags de clasificación (flag_yard_congestion, flag_dock_backlog, etc.)
            - Flags operacionales (_rescheduled, _short_ship, _fill_rate)

    Raises: KeyError si falta alguna columna de _REQUIRED_INPUT_COLUMNS.
    """
    # Validación del contrato de entrada: nombra TODAS las columnas ausentes de una
    # vez (no solo la primera), para no obligar a iterar arreglando una por corrida.
    faltantes = [c for c in _REQUIRED_INPUT_COLUMNS if c not in df_input.columns]
    if faltantes:
        raise KeyError(
            "clean_po_data: faltan columnas requeridas en la entrada: "
            f"{faltantes}. El contrato de entrada de Fase 1 exige las columnas de "
            "_REQUIRED_INPUT_COLUMNS (ver docstring)."
        )

    df = df_input.copy()

    # ── 1. Parsear timestamps ────────────────────────────────────────────────
    # Se leen de la constante de módulo (fuente de verdad de "qué columna es fecha").
    for col in _DATE_INPUT_COLUMNS:
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
    # Umbrales leídos de las constantes de módulo (_*_THR_EDA), no de literales aquí:
    # son los umbrales PRELIMINARES del EDA de Fase 1. Los VIGENTES para clasificar viven
    # en 02_clasif_reglas_negocio/rules_config.json (leídos por nombre). En particular el
    # de carrier de F1 (4h) está SUPERADO por el del mentor (8h, validación 06-16) que usa
    # Fase 2: flag_carrier_miss es un indicador exploratorio de F1, NO el carrier definitivo
    # aguas abajo (T9). F2 recomputa carrier desde carrier_lag_hrs con su propio umbral 8h.
    df['flag_yard_congestion'] = df['YARD_WAIT_HRS']   > _YARD_THR_EDA
    df['flag_dock_backlog']    = df['DOCK_HRS']        > _DOCK_THR_EDA
    df['flag_carrier_miss']    = df['carrier_lag_hrs'] > _CARRIER_THR_EDA   # 4h preliminar; F2 usa 8h
    # flag_short_lead_time: ventana de aviso corta. DESTINO (T13): Fase 2 la consume como
    # is_short_lead, un MODIFICADOR de severidad (#48), no una etapa de retraso.
    df['flag_short_lead_time'] = df['lead_time_days']  < _LEAD_THR_EDA
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


# ── T3 · Persistencia de la salida limpia (contrato dual del handoff 1→2) ─────
def save_clean_output(df: pd.DataFrame, path=None) -> Path:
    """Persiste el DataFrame limpio COMPLETO a un CSV en data/processed/ (T3).

    Espejo de save_classified_output() de Fase 2: bajo el contrato dual (§3-A), el CSV
    de salida de F1 es IDÉNTICO al DataFrame que clean_po_data() deja en memoria — TODAS
    las columnas (crudas + las que añade F1), no un subconjunto. Releerlo reconstruye lo
    que F2 cargaría si corriera la cadena monolítica. F2 decide qué consume de ese conjunto.
    Limitación de CSV: las fechas se escriben como texto; un lector que necesite datetime
    las reparsea (el guard __main__ ofrece esa lectura opcional).

    Resolución de ruta (mismo patrón que PO_CSV_PATH del guard __main__):
      - `path` explícito tiene prioridad;
      - si no, respeta la env var PO_CLEAN_OUTPUT_PATH;
      - si no, default convencional: <repo>/data/processed/df_clean.csv.
    data/processed/ está en .gitignore: el CSV NO se versiona, se regenera ejecutando.

    Input:  df — DataFrame ya pasado por clean_po_data().
            path — ruta destino opcional (str | Path).
    Output: el Path donde se escribió.
    """
    if path is not None:
        out_path = Path(path)
    elif os.environ.get("PO_CLEAN_OUTPUT_PATH"):
        out_path = Path(os.environ["PO_CLEAN_OUTPUT_PATH"])
    else:
        repo_root = Path(__file__).resolve().parent
        if repo_root.name == "01_data_pipeline_and_eda":
            repo_root = repo_root.parent
        out_path = repo_root / "data" / "processed" / "df_clean.csv"

    # Contrato dual: escribir el DataFrame ENTERO (todas las columnas, mismo orden).
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False)
    return out_path


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

    # Contrato dual del handoff 1→2 (T3): persistir el df limpio ANTES de la
    # cross-validation. F2 consume la salida de clean_po_data(), no las columnas de
    # diagnóstico (_yard_discrepancy/_dock_discrepancy) que añade cross_validate_deltas;
    # así el CSV es idéntico a lo que F2 cargaría en memoria.
    out_path = save_clean_output(df_clean)
    print(f'\n[OK] Salida limpia escrita en: {out_path}')

    # Cross-validation: deltas calculados vs columnas precalculadas (solo reporte; sus
    # columnas de diagnóstico NO entran al CSV de handoff de arriba).
    print()
    df_clean = cross_validate_deltas(df_clean)

    # Nuevas columnas
    new_cols = [c for c in df_clean.columns if c not in df_raw.columns]
    print(f'\nColumnas nuevas: {new_cols}')