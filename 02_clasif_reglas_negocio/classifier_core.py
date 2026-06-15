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


def _expected(rules: dict, name: str) -> float:
    """Tiempo esperado (presupuesto) del tramo `name` bajo expected_leg_times (#45)."""
    return float(rules["expected_leg_times"][name]["value"])


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


# ── #45 · Etapa primaria: gap dominante + vendor residual + indeterminado ────
def _etapa_primaria(df: pd.DataFrame, rules: dict) -> pd.DataFrame:
    """Asigna la etapa primaria por el tramo de MAYOR EXCESO sobre su tiempo esperado
    (no por duración cruda: cruda siempre gana el tramo inherentemente más lento).

    Método (decidido y verificado contra los 400 POs; ver respuestas-maria-fase2):
      1. Exceso de cada tramo MEDIBLE = max(0, actual − esperado), en HORAS.
         No-medible (máscara False) → exceso 0 en el argmax, pero la máscara queda.
      2. VENDOR = residual de pre-llegada (no hay VENDOR_SHIP_DT): el delay total que
         los tramos medibles NO explican con su exceso. Todo en horas:
            exceso_vendor = max(0, delay_days_calc*24 − (exceso_carrier + exceso_dc))
         El clip(0) absorbe los casos donde lo medible "sobra" (residual negativo).
         APROXIMACIÓN (provisional, #57): el exceso de tramos internos del viaje se
         resta de la tardanza vs la promesa (RECPT−STA) — ejes distintos, pero es la
         única vía sin dato de embarque. El lunes el mentor confirma.
      3. Etapa primaria = argmax de {VENDOR, CARRIER, DC}. Si todos 0 y no es tardío
         → 'On-Time'.
      4. INDETERMINADO intercepta ANTES de premiar a vendor por descarte: si el PO es
         tardío pero los tramos clave no son medibles y nada medible tiene exceso, no
         se le endosa a vendor — se marca 'Indeterminado' (separa "no medible" de "fue
         vendor", como pedía la nota: "primero sacamos los indeterminados").

    Universo: tardíos = delay_days_calc > 0 (fuente de verdad #18); el resto 'On-Time'.
    Expone stage_primary + las magnitudes excess_*_hrs (para severidad futura #48 y
    para validación contra stage_multi).
    """
    esperado_carrier = _expected(rules, "carrier_hrs")
    esperado_yard    = _expected(rules, "yard_hrs")
    esperado_dock    = _expected(rules, "dock_hrs")

    # Paso 1 — exceso por tramo medible (horas, clip 0). fillna(0): un tramo no
    # medible (NaN) o sin exceso aporta 0 al argmax; la máscara guarda el "no sé".
    exc_carrier = (df["carrier_lag_hrs"]    - esperado_carrier).clip(lower=0).fillna(0)
    exc_yard    = (df["yard_wait_calc_hrs"] - esperado_yard).clip(lower=0).fillna(0)
    exc_dock    = (df["dock_calc_hrs"]      - esperado_dock).clip(lower=0).fillna(0)
    # Solo cuenta el exceso de un tramo si ese tramo es medible.
    exc_carrier = exc_carrier.where(df["_carrier_medible"], 0.0)
    exc_yard    = exc_yard.where(df["_dc_medible"], 0.0)
    exc_dock    = exc_dock.where(df["_dc_medible"], 0.0)
    exc_dc      = exc_yard + exc_dock

    # Paso 2 — residual vendor (horas). delay en días → horas para operar en 1 unidad.
    delay_hrs     = (df["delay_days_calc"] * 24).fillna(0)
    exc_vendor    = (delay_hrs - (exc_carrier + exc_dc)).clip(lower=0)

    df["excess_carrier_hrs"] = exc_carrier
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

    stage = pd.Series("On-Time", index=df.index, dtype="object")
    # Tardío y decidible → el ganador del argmax (si hay algún exceso medible/vendor).
    stage = stage.mask(es_tardio & decidible & algun_exceso, ganador)
    # Tardío pero NO decidible (no medible) → Indeterminado, no vendor por descarte.
    stage = stage.mask(es_tardio & ~decidible, "Indeterminado")
    # Tardío, decidible, pero sin exceso en ningún tramo medible y residual vendor 0
    # → tampoco hay a quién atribuir con evidencia: Indeterminado.
    stage = stage.mask(es_tardio & decidible & ~algun_exceso, "Indeterminado")

    df["stage_primary"] = stage
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
    Sirven como capa auxiliar de validación / revisión histórica: el vector multi-causa
    de María y los modificadores narrativos.

      reason_group_manual — REASON_DSC mapeado a {Vendor, Carrier, DC, Unknown, On-Time}.
      stage_multi         — las 8 etiquetas multi-causa desde las flags *_calc de #44
                            (p.ej. 'Vendor + Carrier + DC'). 'Vendor' aquí = señal
                            explícita de vendor (rescheduled/short-ship/lead corto), NO
                            la atribución por residual — es la capa de banderas, a propósito.
      stage_modifiers     — sufijos cuando hay señal de vendor pero el primario no es
                            Vendor (#54): '(+ vendor_rescheduled)', '(+ vendor_short_ship)'.

    Short-ship: en esta tanda solo se apoya en _short_ship (ya viene del pipeline); su
    rol de agravante de severidad llega con #48 (diferido), aquí no se puntúa.
    """
    # REASON_DSC es columna de entrada (anotación humana, 2.2% nulls en el CSV real).
    # Si faltara por completo, degradar a "Unknown" en vez de romper: la capa
    # complementaria no debe ser un requisito duro del clasificador primario.
    if "REASON_DSC" in df.columns:
        df["reason_group_manual"] = df["REASON_DSC"].map(_REASON_DSC_MAP).fillna("Unknown")
    else:
        df["reason_group_manual"] = "Unknown"

    # Señales de banderas (capa complementaria, independiente del residual de #45).
    v = (
        df["_rescheduled"].fillna(False)
        | df["_short_ship"].fillna(False)
        | df["flag_short_lead_time"].fillna(False)
    )
    c = df["flag_carrier_calc"].fillna(False)
    d = (df["flag_yard_calc"].fillna(False)) | (df["flag_dock_calc"].fillna(False))

    def _etiqueta(vv: bool, cc: bool, dd: bool) -> str:
        activos = [n for n, on in (("Vendor", vv), ("Carrier", cc), ("DC", dd)) if on]
        return " + ".join(activos) if activos else "None"

    df["stage_multi"] = [
        _etiqueta(vv, cc, dd) for vv, cc, dd in zip(v, c, d)
    ]

    # Modificadores narrativos: señal de vendor cuando el primario NO es Vendor.
    def _mods(row) -> str:
        suf = []
        no_vendor_primary = row["stage_primary"] != "Vendor"
        if bool(row.get("_rescheduled", False)) and no_vendor_primary:
            suf.append("(+ vendor_rescheduled)")
        if bool(row.get("_short_ship", False)) and no_vendor_primary:
            suf.append("(+ vendor_short_ship)")
        return " ".join(suf)

    df["stage_modifiers"] = df.apply(_mods, axis=1)
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
    #   #45 → etapa primaria por gap dominante + vendor residual + indeterminado.
    #   complementaria → vector multi-causa + modificadores (capa auxiliar).
    # #48 (severidad) y #47 (mismatch) quedan diferidos: no se añaden aquí.
    df = _flags_por_umbral(df, rules)      # #44
    df = _etapa_primaria(df, rules)        # #45
    df = _capa_complementaria(df, rules)   # complementaria

    return df


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
    print(f"   Columnas añadidas (#44/#45): {df_classified.shape[1] - df_clean.shape[1]}")
    print(f"   Umbrales cargados:          {list(rules.get('thresholds', {}).keys())}")
    print(f"   Tiempos esperados (#45):    {list(rules.get('expected_leg_times', {}).keys())}")

    # Reparto de la etapa primaria sobre el universo de tardíos (delay_days_calc > 0).
    tardios = df_classified[df_classified["delay_days_calc"] > 0]
    print(f"\n   Tardíos (delay_days_calc > 0): {len(tardios)}")
    print("   Reparto stage_primary (tardíos):")
    print(tardios["stage_primary"].value_counts().to_string().replace("\n", "\n     "))
    sin_clase = (tardios["stage_primary"] == "On-Time").sum()
    print(f"\n   Tardíos sin clase primaria (debe ser 0): {sin_clase}")
