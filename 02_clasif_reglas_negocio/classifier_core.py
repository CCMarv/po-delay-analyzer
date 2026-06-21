# ── Imports requeridos ───────────────────────────────────────────────────────
# Solo lo barato a nivel de módulo: importar classifier_core no debe exigir dotenv
# ni cargar el pipeline. Los imports pesados de ejecución viven en el guard __main__.
import json
import os
from pathlib import Path

import pandas as pd


# ── Carga de configuración de umbrales ───────────────────────────────────────
# Ruta convencional del JSON de reglas: junto a este módulo. Se resuelve desde
# __file__ (no desde el cwd) para que `load_rules_config()` funcione igual desde
# la suite, el notebook o una ejecución directa.
_DEFAULT_RULES_PATH = Path(__file__).resolve().parent / "rules_config.json"


def load_rules_config(path=None) -> dict:
    """Carga rules_config.json y devuelve el dict de configuración.

    Externalizar los umbrales (en vez de constantes en código) permite que #44/#45
    los lean POR NOMBRE desde el JSON y se recalibren sin tocar el módulo.

    Input:  path opcional (str | Path) para sobreescribir la ubicación; si es None
            usa el JSON convencional junto a este módulo.
    Output: dict con la estructura del config (claves `version`, `thresholds`, ...).
    """
    rules_path = Path(path) if path else _DEFAULT_RULES_PATH
    with open(rules_path, encoding="utf-8") as f:
        return json.load(f)


# ── Helpers internos de lectura de config ────────────────────────────────────
def _thr(rules: dict, name: str) -> float:
    """Valor del umbral `name` bajo rules["thresholds"]. Falla ruidoso si falta:
    un umbral ausente es un error de config, no algo que silenciar con un default."""
    return float(rules["thresholds"][name]["value"])


# ── #44 · Flags por umbral + máscaras field-level ────────────────────────────
def _flags_por_umbral(df: pd.DataFrame, rules: dict) -> pd.DataFrame:
    """Recalcula las flags de etapa desde las columnas *_calc (no las precalc del
    CSV) y añade máscaras field-level que separan "no pasó" de "no se pudo medir".

    Por qué recalcular: el pipeline (#15) dejó flag_yard_congestion/flag_dock_backlog
    apoyadas en YARD_WAIT_HRS/DOCK_HRS (precalculadas), pero la fuente de verdad son
    los timestamps → aquí se reescriben sobre yard_wait_calc_hrs/dock_calc_hrs.

    Por qué las máscaras (#44): si TRAILER_ARRIVE_DT es null, carrier_lag_hrs y
    yard_wait_calc_hrs salen NaN y la flag quedaría silenciosamente False — se vería
    como "no hubo problema" cuando la verdad es "no se puede saber". Las máscaras
    _carrier_medible / _dc_medible lo hacen explícito; #45 las usa para Indeterminado.

    Muta y devuelve el mismo df (ya es copia dentro de classify_po_stages).
    """
    # Máscaras de medibilidad (vienen de las flags de calidad del pipeline):
    #   carrier necesita la hora de llegada del tráiler (fin del tramo carrier).
    #   DC (yard+dock) necesita además que la secuencia no esté invertida (_ts_issue).
    df["_carrier_medible"] = ~df["_trailer_arrive_null"]
    df["_dc_medible"]      = (~df["_trailer_arrive_null"]) & (~df["_ts_issue"])

    # Flags desde *_calc, umbrales leídos del JSON por nombre. Donde la métrica es
    # NaN (no medible), la comparación da False; la máscara distingue ese caso.
    df["flag_carrier_calc"] = df["carrier_lag_hrs"]    > _thr(rules, "carrier_lag_hrs")
    df["flag_yard_calc"]    = df["yard_wait_calc_hrs"] > _thr(rules, "yard_wait_hrs")
    df["flag_dock_calc"]    = df["dock_calc_hrs"]      > _thr(rules, "dock_hrs")

    return df


# ── #45 · Etapa primaria: STA push (vendor) + exceso sobre umbral + indeterminado ──
def _etapa_primaria(df: pd.DataFrame, rules: dict) -> pd.DataFrame:
    """Asigna la etapa primaria por el tramo de MAYOR EXCESO sobre el UMBRAL del mentor
    (no por duración cruda: cruda siempre gana el tramo inherentemente más lento).

    Método (decidido por el mentor 06-16 / consulta 06-17; verificado contra los 400 POs):
      1. Exceso de cada tramo MEDIBLE = max(0, actual − UMBRAL del mentor), en HORAS.
         Umbrales: carrier 8h, yard 4h, dock 6h (rules_config). No-medible (máscara
         False) → exceso 0 en el argmax, pero la máscara queda para Indeterminado.
      2. VENDOR por SEÑAL DIRECTA "STA push" (no por residual): si la cita se aprobó
         DESPUÉS de la fecha esperada de llegada (APPROVED_DT > STA_DT), hay evidencia
         de que el vendor arrancó tarde. appt_lead_days = STA − APPROVED (días); es
         NEGATIVO cuando APPROVED > STA, así que el push en horas es −appt_lead_days*24.
         Vendor lleva UMBRAL propio (vendor_gap_hrs, consulta mentor 06-17), igual que
         carrier/DC — el push solo cuenta como exceso por encima del umbral:
            exc_vendor = max(0, −appt_lead_days * 24 − vendor_gap_hrs)
         Por qué el umbral (06-17): sin él, vendor disparaba con CUALQUIER push positivo
         mientras carrier/DC exigían 8/4/6h → asimetría de construcción (vendor absorbía
         por default, 62.8%). Con umbral simétrico, un push pequeño ya no basta para
         culpar al vendor. Valor 24h: el push se mide en días porque STA_DT está anclado
         a medianoche (sin resolución sub-día), así que 24h = un día completo es el GRANO
         NATURAL del dato; además cae en un hueco vacío de la distribución (0 POs entre 6
         y 18h) → robusto. Análisis de sensibilidad: data/_local_notes/analisis-umbral-vendor.md.
         La señal directa sigue siendo mejor que el residual: no asume tramos aditivos ni
         excluyentes, y funciona en los 27 POs SIN hora de tráiler (reemplaza #57).
      3. Etapa primaria = argmax de {VENDOR, CARRIER, DC}. Si todos 0 y no es tardío
         → 'On-Time'.
      4. INDETERMINADO = SOLO casos sin evidencia, con SUBCLASE (indeterminado_substage,
         espejo de dc_substage; consulta mentor 06-17):
           'sin_datos'           = tardío no medible (sin TRAILER_ARRIVE_DT → no se puede
                                   juzgar carrier/DC).
           'sin_causa_dominante' = tardío medible pero sin NINGUNA señal sobre umbral
                                   (push ≤ 24h y exc carrier/dc 0): datos completos pero
                                   ningún tramo destaca. Antes caía en vendor por default;
                                   ahora se separa (no inventar causalidad).
         Ambos colapsan en stage_primary='Indeterminado' (etiqueta limpia arriba); la
         razón específica vive en la subclase. El (b) cae por la intercepción argmax-de-
         ceros: si excesos.max == 0, no hay a quién atribuir con evidencia.

    Universo: tardíos = delay_days_calc > 0 (fuente de verdad #18); el resto 'On-Time'.
    Expone stage_primary, dc_substage (Yard/Dock cuando primary==DC), indeterminado_substage
    (sin_datos/sin_causa_dominante cuando primary==Indeterminado) y las magnitudes
    excess_*_hrs (para severidad #48 y para validación contra el gap dominante #46).
    """
    thr_carrier = _thr(rules, "carrier_lag_hrs")
    thr_yard    = _thr(rules, "yard_wait_hrs")
    thr_dock    = _thr(rules, "dock_hrs")
    thr_vendor  = _thr(rules, "vendor_gap_hrs")

    # Paso 1 — exceso por tramo medible sobre el UMBRAL (horas, clip 0). fillna(0): un
    # tramo no medible (NaN) o sin exceso aporta 0 al argmax; la máscara guarda el "no sé".
    exc_carrier = (df["carrier_lag_hrs"]    - thr_carrier).clip(lower=0).fillna(0)
    exc_yard    = (df["yard_wait_calc_hrs"] - thr_yard).clip(lower=0).fillna(0)
    exc_dock    = (df["dock_calc_hrs"]      - thr_dock).clip(lower=0).fillna(0)
    # Solo cuenta el exceso de un tramo si ese tramo es medible.
    exc_carrier = exc_carrier.where(df["_carrier_medible"], 0.0)
    exc_yard    = exc_yard.where(df["_dc_medible"], 0.0)
    exc_dock    = exc_dock.where(df["_dc_medible"], 0.0)
    exc_dc      = exc_yard + exc_dock

    # Paso 2 — VENDOR por STA push (horas) SOBRE su umbral. appt_lead_days = STA − APPROVED
    # (días): negativo cuando APPROVED > STA, así que −appt_lead_days*24 es el push en horas.
    # Igual que carrier/DC, solo cuenta el exceso por encima del umbral (vendor_gap_hrs).
    exc_vendor = (-df["appt_lead_days"] * 24 - thr_vendor).clip(lower=0).fillna(0)

    df["excess_carrier_hrs"] = exc_carrier
    df["excess_yard_hrs"]    = exc_yard
    df["excess_dock_hrs"]    = exc_dock
    df["excess_dc_hrs"]      = exc_dc
    df["excess_vendor_hrs"]  = exc_vendor

    # Paso 3+4 — etapa primaria con intercepción de Indeterminado.
    es_tardio = df["delay_days_calc"] > 0
    # ¿Puedo decidir? Necesito al menos un tramo medible para atribuir con honestidad.
    decidible = df["_carrier_medible"] | df["_dc_medible"]

    excesos = pd.DataFrame(
        {"Vendor": exc_vendor, "Carrier": exc_carrier, "DC": exc_dc}
    )
    ganador = excesos.idxmax(axis=1)          # nombre del tramo con mayor exceso
    algun_exceso = excesos.max(axis=1) > 0

    # Las dos ramas de Indeterminado (se reutilizan para la subclase más abajo):
    #   sin_datos          = tardío no decidible (ningún tramo medible).
    #   sin_causa_dominante = tardío decidible pero sin ningún exceso sobre umbral.
    rama_sin_datos = es_tardio & ~decidible
    rama_sin_causa = es_tardio & decidible & ~algun_exceso

    stage = pd.Series("On-Time", index=df.index, dtype="object")
    # Tardío y decidible → el ganador del argmax (si hay algún exceso medible/vendor).
    stage = stage.mask(es_tardio & decidible & algun_exceso, ganador)
    # Tardío sin evidencia (cualquiera de las dos ramas) → Indeterminado (etiqueta limpia
    # arriba; la razón específica va en indeterminado_substage). No vendor por descarte.
    stage = stage.mask(rama_sin_datos | rama_sin_causa, "Indeterminado")

    df["stage_primary"] = stage

    # Subclase del DC: solo informativa cuando el primario es DC; separa Yard de Dock
    # por el mayor exceso de los dos. Empate (o ambos 0 dentro de un DC) → 'Dock': es la
    # operación TERMINAL del CD (procesamiento en muelle), la más informativa para el LLM.
    es_dc = df["stage_primary"] == "DC"
    dc_substage = pd.Series(pd.NA, index=df.index, dtype="object")
    dc_substage = dc_substage.mask(es_dc & (exc_yard > exc_dock), "Yard")
    dc_substage = dc_substage.mask(es_dc & (exc_yard <= exc_dock), "Dock")
    df["dc_substage"] = dc_substage

    # Subclase de Indeterminado (espejo de dc_substage; consulta mentor 06-17): distingue
    # "no hay datos para medir" de "datos completos pero ningún tramo destaca". Solo poblada
    # cuando stage_primary == 'Indeterminado'; NA en el resto.
    indeterminado_substage = pd.Series(pd.NA, index=df.index, dtype="object")
    indeterminado_substage = indeterminado_substage.mask(rama_sin_datos, "sin_datos")
    indeterminado_substage = indeterminado_substage.mask(rama_sin_causa, "sin_causa_dominante")
    df["indeterminado_substage"] = indeterminado_substage

    return df


# ── Capa complementaria · etiquetas multi-causa + modificadores (de María) ───
# Mapeo manual REASON_DSC → grupo de responsable. Se conserva para el análisis de
# mismatch (#47, diferido): permite contrastar la anotación humana vs el cómputo.
_REASON_DSC_MAP = {
    "Rescheduled by vendor":               "Vendor",
    "Vendor delayed shipment":             "Vendor",
    "Carrier delivery delay":              "Carrier",
    "Equipment/trailer issue":             "Carrier",
    "Weather/road conditions":             "Carrier",
    "Missed appointment window":           "Carrier",
    "Yard congestion - no available door": "DC",
    "Dock processing backlog":             "DC",
    "Other":                               "Unknown",
    "Not applicable":                      "On-Time",
}


def _capa_complementaria(df: pd.DataFrame, rules: dict) -> pd.DataFrame:
    """Columnas SECUNDARIAS (no son el driver de la clasificación; stage_primary lo es).
    Capa auxiliar de validación / revisión + las flags de contexto para Fase 3.

      reason_group_manual — REASON_DSC mapeado a {Vendor, Carrier, DC, Unknown, On-Time}.
      stage_multi         — etiquetas multi-causa desde las CAUSAS reales de cada etapa
                            (p.ej. 'Vendor + Carrier'). Las tres señales (V/C/DC) miden
                            EXCESO sobre su umbral del mentor, igual que stage_primary:
                            'Vendor' = STA push por encima de vendor_gap_hrs (24h), NO
                            cualquier push ni rescheduled/short-ship (el mentor 06-16 los
                            descartó como señal de vendor: describen un evento, no la causa).

    Flags de CONTEXTO (decisión del mentor: rescheduled/short-ship son contexto/agravante,
    no etapa). Se exponen SIEMPRE como columnas propias para que la severidad (#48) y el
    LLM (Fase 3) las consuman sin reinterpretar las flags internas del pipeline:
      is_rescheduled — la cita se reprogramó (DT_APPT_CURRENT != DT_APPT_FIRST).
      is_short_ship  — fill rate por debajo del umbral (envío incompleto).
      is_short_lead  — lead time PO→STA por debajo del mínimo (ventana de aviso corta).
    """
    # REASON_DSC es columna de entrada (anotación humana, 2.2% nulls en el CSV real).
    # Si faltara por completo, degradar a "Unknown" en vez de romper: la capa
    # complementaria no debe ser un requisito duro del clasificador primario.
    if "REASON_DSC" in df.columns:
        df["reason_group_manual"] = df["REASON_DSC"].map(_REASON_DSC_MAP).fillna("Unknown")
    else:
        df["reason_group_manual"] = "Unknown"

    # Flags de contexto propias (siempre presentes, alias estables de las del pipeline).
    df["is_rescheduled"] = df["_rescheduled"].fillna(False)
    df["is_short_ship"]  = df["_short_ship"].fillna(False)
    df["is_short_lead"]  = df["flag_short_lead_time"].fillna(False)

    # Señales multi-causa: SOLO causas de etapa (el mentor sacó reschedule/short-ship
    # de la señal de vendor). Las tres señales miden EXCESO sobre el umbral del mentor,
    # igual que stage_primary: Vendor por excess_vendor_hrs (push sobre vendor_gap_hrs=24h),
    # carrier/DC por sus flags de umbral. Antes vendor usaba appt_lead_days<0 (cualquier
    # push), divergiendo de stage_primary y reintroduciendo el sesgo pro-vendor que el
    # umbral 24h (mentor 06-17) corrige; excess_vendor_hrs ya lo calculó _etapa_primaria.
    v = (df["excess_vendor_hrs"] > 0).fillna(False)     # STA push SOBRE el umbral de 24h
    c = df["flag_carrier_calc"].fillna(False)
    d = (df["flag_yard_calc"].fillna(False)) | (df["flag_dock_calc"].fillna(False))

    def _etiqueta(vv: bool, cc: bool, dd: bool) -> str:
        activos = [n for n, on in (("Vendor", vv), ("Carrier", cc), ("DC", dd)) if on]
        return " + ".join(activos) if activos else "None"

    df["stage_multi"] = [
        _etiqueta(vv, cc, dd) for vv, cc, dd in zip(v, c, d)
    ]

    return df


# ── #48 · Severidad determinística ───────────────────────────────────────────
# Orden de niveles para subir/bajar por índice (LOW < MEDIUM < HIGH).
_SEVERITY_LEVELS = ["LOW", "MEDIUM", "HIGH"]


def _severidad(df: pd.DataFrame, rules: dict) -> pd.DataFrame:
    """Asigna severidad determinística a cada PO tardío (#48). Auditable y reproducible
    (no la decide el LLM; esa es una capa narrativa aparte de Fase 3).

    Nivel BASE (regla del brief/mentor):
      HIGH   = HOT PO en retraso fuerte: flag_hot_late & delay_days_calc > severity_delay_days (3.0).
      LOW    = borderline: delay_days_calc < severity_low_days (1.0), casi a tiempo (<~24h).
      MEDIUM = el resto de los tardíos (retraso normal).
      On-Time (no tardío)        → severity = '' (no entra al ranking de #48).

    AGRAVANTES (decisión del mentor #40/#42: lead corto y short-ship NO son etapa, son
    contexto que agrava la severidad). Si is_short_lead OR is_short_ship: subir 1 nivel
    (LOW→MEDIUM, MEDIUM→HIGH); HIGH se queda HIGH (tope). No acumulan más allá de HIGH:
    el gate HIGH "real" sigue siendo HOT_PO + retraso fuerte; un agravante puede empujar
    un caso a HIGH, pero la base se mantiene monótona y fácil de explicar.

    Por qué determinística y no del LLM: la rúbrica pide un Severity Ranking auditable
    (>95%); el cómputo desde columnas confiables es defendible, el del LLM es narrativa.
    """
    thr_high = _thr(rules, "severity_delay_days")   # 3.0
    thr_low  = _thr(rules, "severity_low_days")     # 1.0

    es_tardio = df["delay_days_calc"] > 0
    hot_late  = df["flag_hot_late"].fillna(False)
    delay     = df["delay_days_calc"].fillna(0)

    # Nivel base: empieza vacío; solo los tardíos reciben nivel.
    base = pd.Series("", index=df.index, dtype="object")
    base = base.mask(es_tardio, "MEDIUM")                       # tardío normal
    base = base.mask(es_tardio & (delay < thr_low), "LOW")      # borderline
    base = base.mask(es_tardio & hot_late & (delay > thr_high), "HIGH")  # hot + fuerte

    # Agravante: lead corto o short-ship sube un escalón (sin pasar de HIGH).
    agrava = df["is_short_lead"].fillna(False) | df["is_short_ship"].fillna(False)

    def _subir(nivel: str, sube: bool) -> str:
        if nivel == "" or not sube:
            return nivel
        i = _SEVERITY_LEVELS.index(nivel)
        return _SEVERITY_LEVELS[min(i + 1, len(_SEVERITY_LEVELS) - 1)]

    df["severity"] = [_subir(n, s) for n, s in zip(base, agrava)]
    return df


# ── Clasificación por etapa ──────────────────────────────────────────────────
def classify_po_stages(df_input: pd.DataFrame, rules: dict | None = None) -> pd.DataFrame:
    """Clasifica cada PO por etapa a partir del DataFrame ya enriquecido.

    Contrato (#43, esqueleto): recibe el DataFrame que devuelve clean_po_data() de
    pipeline_core y devuelve ESE MISMO DataFrame con columnas de clasificación
    añadidas (no un objeto aparte). Trabaja sobre una copia para no mutar la entrada.

    `rules` es inyectable: si es None se carga del JSON convencional; pasarlo permite
    a los tests usar un dict controlado. #44/#45 implementan aquí las flags/etapas
    leyendo los umbrales desde `rules["thresholds"][<nombre>]`.

    Input:  df_input — DataFrame enriquecido por clean_po_data() (ya trae las columnas
            *_calc: yard_wait_calc_hrs, dock_calc_hrs, carrier_lag_hrs, delay_days_calc,
            _fill_rate, etc.).
            rules    — dict de configuración; default: load_rules_config().
    Output: el mismo DataFrame con las columnas de clasificación de Fase 2 añadidas.
    """
    df = df_input.copy()

    if rules is None:
        rules = load_rules_config()

    # Orquestación de la fase (Opción 2: un core, funciones-hueco por issue).
    #   #44 → flags desde *_calc + máscaras field-level (prerequisito de #45).
    #   #45 → etapa primaria por STA push (vendor) + exceso sobre umbral + indeterminado.
    #   complementaria → flags de contexto + vector multi-causa + modificadores.
    #   #48 → severidad determinística (usa las flags de contexto de la complementaria).
    df = _flags_por_umbral(df, rules)      # #44
    df = _etapa_primaria(df, rules)        # #45
    df = _capa_complementaria(df, rules)   # complementaria (is_*, stage_multi, modifiers)
    df = _severidad(df, rules)             # #48 (tras la complementaria: necesita is_*)

    return df


# ── #49 · Persistencia del output clasificado ────────────────────────────────
# Columnas que se exportan: el veredicto por PO (stage_primary, severity, dc_substage),
# las flags de etapa y las máscaras de evaluabilidad (para auditar QUÉ se pudo medir), y
# las flags de contexto que Fase 3 consume. Se mantienen solo las relevantes para los
# consumidores (Fase 3/4 + revisión), no todo el DataFrame intermedio.
_OUTPUT_COLUMNS = [
    "PO_NBR",
    "stage_primary", "severity", "dc_substage", "indeterminado_substage",
    "excess_vendor_hrs", "excess_carrier_hrs", "excess_dc_hrs",
    "flag_carrier_calc", "flag_yard_calc", "flag_dock_calc",
    "_carrier_medible", "_dc_medible",
    "is_rescheduled", "is_short_ship", "is_short_lead",
    "reason_group_manual",
]


def save_classified_output(df: pd.DataFrame, path=None) -> Path:
    """Persiste el DataFrame clasificado a un CSV en data/processed/ (#49).

    Función REUSABLE (Fase 3/4 la importan en vez de re-implementar el to_csv): escribe
    solo las columnas del veredicto + auditabilidad (_OUTPUT_COLUMNS), no el DataFrame
    intermedio entero. Crea el directorio destino si no existe.

    Resolución de ruta (mismo patrón que la entrada PO_CSV_PATH del guard __main__):
      - `path` explícito tiene prioridad;
      - si no, respeta la env var PO_OUTPUT_PATH;
      - si no, default convencional: <repo>/data/processed/df_classified.csv.
    data/processed/ está en .gitignore: el CSV NO se versiona, se regenera ejecutando.

    Input:  df — DataFrame ya pasado por classify_po_stages().
            path — ruta destino opcional (str | Path).
    Output: el Path donde se escribió (para que el caller lo reporte/loguee).
    """
    if path is not None:
        out_path = Path(path)
    elif os.environ.get("PO_OUTPUT_PATH"):
        out_path = Path(os.environ["PO_OUTPUT_PATH"])
    else:
        repo_root = Path(__file__).resolve().parent
        if repo_root.name == "02_clasif_reglas_negocio":
            repo_root = repo_root.parent
        out_path = repo_root / "data" / "processed" / "df_classified.csv"

    # Exportar solo las columnas presentes (robustez: si el contrato cambia, no rompe).
    cols = [c for c in _OUTPUT_COLUMNS if c in df.columns]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df[cols].to_csv(out_path, index=False)
    return out_path


# ── Ejecución como script ────────────────────────────────────────────────────
# Replica el patrón de pipeline_core.py: resolución de raíz por __file__, carga del
# CSV local (respetando PO_CSV_PATH), y encadena clean_po_data → classify_po_stages.
if __name__ == "__main__":
    # Imports solo necesarios para la ejecución como script (no para importar el
    # módulo): se mantienen dentro del guard para que `import classifier_core` siga
    # siendo barato.
    import sys

    from dotenv import load_dotenv

    # 1. Resolver la raíz del repo desde la ubicación del módulo (no desde el cwd).
    #    Mismo patrón que pipeline_core.py: ubicarse por __file__, no por el cwd.
    REPO_ROOT = Path(__file__).resolve().parent
    if REPO_ROOT.name == "02_clasif_reglas_negocio":
        REPO_ROOT = REPO_ROOT.parent

    # clean_po_data() vive en pipeline_core (Fase 1, congelado) y entra como INPUT.
    # La carpeta empieza con dígito, así que no es importable por su nombre: la
    # añadimos a sys.path aquí (código de ejecución, no de import del módulo).
    _PIPELINE_DIR = REPO_ROOT / "01_data_pipeline_and_eda"
    if str(_PIPELINE_DIR) not in sys.path:
        sys.path.insert(0, str(_PIPELINE_DIR))
    from pipeline_core import clean_po_data

    load_dotenv(REPO_ROOT / ".env", override=True)

    # 2. Resolver la ruta al CSV: respeta PO_CSV_PATH si está definida; si no, el
    #    default convencional bajo la raíz del repo (data/raw/).
    _env_path = os.environ.get("PO_CSV_PATH")
    csv_path = Path(_env_path) if _env_path else REPO_ROOT / "data" / "raw" / "po_root_cause_synthetic.csv"

    try:
        df_raw = pd.read_csv(csv_path, low_memory=False)
        print(f"[OK] Archivo local cargado exitosamente desde: {csv_path}")

    except FileNotFoundError:
        error_msg = (
            f"\nERROR: Archivo no encontrado.\n"
            f"Debido a que la carpeta 'data/' está en .gitignore, debes colocar manualmente el archivo en:\n"
            f"  {csv_path}\n"
            f"Asegúrate de crear las carpetas 'data/' y 'raw/' en la raíz de tu repositorio local,\n"
            f"o define PO_CSV_PATH=/ruta/completa.csv en el archivo .env de la raíz."
        )
        raise FileNotFoundError(error_msg)

    # 3. Encadenar el pipeline de Fase 1 con el clasificador de Fase 2.
    df_clean = clean_po_data(df_raw)
    rules = load_rules_config()
    df_classified = classify_po_stages(df_clean, rules)

    print("[OK] classify_po_stages() ejecutado correctamente")
    print(f"   Shape entrada (clean):      {df_clean.shape}")
    print(f"   Shape salida (classified):  {df_classified.shape}")
    print(f"   Columnas añadidas:          {df_classified.shape[1] - df_clean.shape[1]}")
    print(f"   Umbrales cargados:          {list(rules.get('thresholds', {}).keys())}")

    # Reparto de la etapa primaria sobre el universo de tardíos (delay_days_calc > 0).
    tardios = df_classified[df_classified["delay_days_calc"] > 0]
    print(f"\n   Tardíos (delay_days_calc > 0): {len(tardios)}")
    print("   Reparto stage_primary (tardíos):")
    print(tardios["stage_primary"].value_counts().to_string().replace("\n", "\n     "))
    sin_clase = (tardios["stage_primary"] == "On-Time").sum()
    print(f"\n   Tardíos sin clase primaria (debe ser 0): {sin_clase}")

    # Severidad (#48) y subclase DC sobre los tardíos.
    print("\n   Reparto severity (tardíos):")
    print(tardios["severity"].value_counts().to_string().replace("\n", "\n     "))
    es_dc = df_classified["stage_primary"] == "DC"
    print("\n   dc_substage (solo DC):")
    print(df_classified.loc[es_dc, "dc_substage"].value_counts().to_string().replace("\n", "\n     "))
    es_indet = df_classified["stage_primary"] == "Indeterminado"
    print("\n   indeterminado_substage (solo Indeterminado):")
    print(df_classified.loc[es_indet, "indeterminado_substage"].value_counts().to_string().replace("\n", "\n     "))

    # Persistir el output clasificado a data/processed/ (#49). Gitignored: NO se commitea.
    out_path = save_classified_output(df_classified)
    print(f"\n[OK] Output clasificado escrito en: {out_path}")
