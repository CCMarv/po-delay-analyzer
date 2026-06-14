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

    # #44/#45: aquí se construyen las flags por umbral y la etapa primaria
    # (gap dominante + residual para VENDOR), leyendo de `rules`. El esqueleto
    # de #43 no añade columnas todavía.

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
    print(f"   Columnas añadidas por #43:  {df_classified.shape[1] - df_clean.shape[1]} (esqueleto: 0)")
    print(f"   Umbrales cargados:          {list(rules.get('thresholds', {}).keys())}")
