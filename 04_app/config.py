"""Configuración global de la aplicación Streamlit — Fase 4."""
import os
from pathlib import Path

from dotenv import load_dotenv

# ─ Rutas del proyecto ──────────────────────────────────────────────────────
APP_DIR = Path(__file__).resolve().parent
REPO_ROOT = APP_DIR.parent

# shared/ es un paquete top-level dentro de 04_app/, que ya está en
# pythonpath (pyproject.toml) y es el directorio de trabajo cuando Streamlit
# corre `04_app/app.py` — no hace falta tocar sys.path aquí (evita la
# contaminación cruzada de sys.modules que sufre `config`/`services` entre
# 04_app/ y telegram_bot/, ver tests/test_telegram_auth.py).
from shared.data_contract import (
    COL_PO, COL_STAGE, COL_SEVERITY, COL_EXPLANATION, COL_ACTION,
    COL_PO_DT, COL_STA_DT, COL_APPROVED_DT, COL_TRAILER_ARRIVE_DT,
    COL_CHECKIN_DT, COL_CHECKOUT_DT, COL_RECPT_DT,
    COL_HOT_PO_FLAG, COL_IS_SHORT_SHIP, COL_REASON_DSC, COL_LLM_COINCIDE,
    COL_LLM_CONFIANZA, COL_VENDOR_NAME, COL_CARRIER_NAME, COL_DC_NAME,
    COL_DELAY_DAYS, COL_EXCESS_VENDOR_HRS, COL_EXCESS_CARRIER_HRS, COL_EXCESS_DC_HRS,
    COL_LLM_RAZONAMIENTO, COL_LLM_HIPOTESIS, COL_LLM_HIPOTESIS_EVIDENCIA,
    COL_LLM_ACCION_INMEDIATA, COL_LLM_ACCION_CORRECTIVA, COL_LLM_ACCION_PREVENTIVA,
    COL_LLM_HIPOTESIS_ALT, COL_LLM_PASO_DISCRIMINANTE, COL_LLM_CONFIANZA_HIPOTESIS,
    STAGE_SEGMENT_COLUMNS, STAGE_EXCESS_COLUMN, STAGE_COLORS, SEVERITY_COLORS,
    data_processed_dir, po_output_csv, po_output_sample_csv, scorecards_dir,
    dataset_cutoff_date,
)

DATA_PROCESSED_DIR = data_processed_dir(REPO_ROOT)

# Cargar .env de la raíz del repo (mismo archivo que telegram_bot/config.py).
_DOTENV_PATH = REPO_ROOT / ".env"
if _DOTENV_PATH.exists():
    load_dotenv(_DOTENV_PATH)

# ── Artefacto de handoff F3→F4 (único input de la app) ─────────────────────
PO_OUTPUT_CSV = po_output_csv(REPO_ROOT)

# ── Muestra versionada (fallback cuando no se corrió Fase 3 localmente) ────
PO_OUTPUT_SAMPLE_CSV = po_output_sample_csv(REPO_ROOT)

# ── Canal adicional: bot de Telegram (ARD-20, landing, ARD-23) ─────────────
# Handle público del bot para el enlace "Consultar por Telegram" de la
# landing. ARD-20 no expone un handle público (solo el token en .env, que es
# secreto); esta var es operativa y distinta del token — no se inventa un
# valor si falta: la landing oculta el botón y muestra solo la descripción.
TELEGRAM_BOT_USERNAME = os.getenv("TELEGRAM_BOT_USERNAME", "")

# ── Scorecards por entidad (JSON del motor offline scorecard_core.py) ──────
# Regenerables y gitignored; la app los lee, no recomputa la capa estadística.
SCORECARDS_DIR = scorecards_dir(REPO_ROOT)

# Etapa → etiqueta legible (Title case) para texto compuesto en UI ("Exceso
# Vendor: …", pill de tramo del timeline, chips de leyenda). Las claves de
# stage_key son minúsculas (normalizadas desde el CSV vía .lower()). Distinta
# de STAGE_LABELS del bot (nombres largos en español + emoji): cada canal
# mantiene su propia forma de mostrar la etapa sobre la misma clave.
STAGE_DISPLAY = {
    "vendor": "Vendor",
    "carrier": "Carrier",
    "dc": "DC",
    "indeterminado": "Indeterminado",
}

# ── Sistema de diseño — paleta (ARD-17) ─────────────────────────────────────
# Etapa: hue categórico Okabe-Ito (CUD), idéntico en toda la app. Indeterminado
# usa gris neutro (no un hue) porque señala "sin causa atribuible", no una
# categoría más de la taxonomía. STAGE_COLORS (tema claro) viene de
# shared/data_contract.py — base compartida con el bot de Telegram.

# Severidad: ordinal, NO compite por hue con la etapa — rampa de luminancia
# acromática (gris-carbón) + ícono/forma + etiqueta de texto. La codificación
# por color es redundante, no la única señal.
SEVERITY = {
    "HIGH":   {"color": SEVERITY_COLORS["alta"], "icon": "■", "label": "Alta"},
    "MEDIUM": {"color": SEVERITY_COLORS["media"], "icon": "◆", "label": "Media"},
    "LOW":    {"color": SEVERITY_COLORS["baja"], "icon": "●", "label": "Baja"},
}

# Confianza (llm_confianza, escalar 0–1): mismo mecanismo ordinal que
# severidad (rampa acromática), sin ícono — solo bucket + texto.
CONFIDENCE_BUCKETS = [
    {"key": "alta", "min": 0.80, "max": 1.00, "color": SEVERITY_COLORS["alta"], "label": "Alta",
     "description": "Evidencia suficiente"},
    {"key": "media", "min": 0.50, "max": 0.79, "color": SEVERITY_COLORS["media"], "label": "Media",
     "description": "Requiere verificación humana"},
    {"key": "baja", "min": 0.00, "max": 0.49, "color": SEVERITY_COLORS["baja"], "label": "Baja",
     "description": "Datos insuficientes"},
]


def confidence_bucket(score: float, theme: str | None = None) -> dict:
    """Mapea un score de confianza escalar (0-1) a su bucket ordinal (tema activo)."""
    buckets = CONFIDENCE_BUCKETS_DARK if (theme or current_theme()) == "dark" else CONFIDENCE_BUCKETS
    for bucket in buckets:
        if bucket["min"] <= score <= bucket["max"]:
            return bucket
    return buckets[-1]


# Vista plana (retrocompat): las páginas actuales resuelven color por etapa o
# severidad con `COLORS.get(clave.lower(), ...)`. Se consolida aquí para que
# no haya una segunda fuente de verdad de hex.
COLORS = {
    **STAGE_COLORS,
    "high": SEVERITY["HIGH"]["color"],
    "medium": SEVERITY["MEDIUM"]["color"],
    "low": SEVERITY["LOW"]["color"],
}

# ── Sistema de diseño — variantes de tema oscuro (ARD-17) ───────────────────
# Mismos hues (etapa) / misma rampa (severidad-confianza) que las variantes
# claras de arriba, con la luminancia ajustada que fija la tabla de ARD-17
# para mantener contraste ≥3:1 sobre fondo oscuro. `STAGE_COLORS`/`SEVERITY`/
# `CONFIDENCE_BUCKETS`/`COLORS` no cambian de significado: siguen siendo la
# variante clara, consumida sin cambios por `badges.py`/`timeline.py` (que
# solo usan la key para elegir clase CSS, nunca el hex).
STAGE_COLORS_DARK = {
    "vendor": "#4DA8DB",
    "carrier": "#F0B840",
    "dc": "#3FC79A",
    "indeterminado": "#9B9B9B",
}

_SEVERITY_DARK_COLOR = {"HIGH": "#E8E8E8", "MEDIUM": "#A8A8A8", "LOW": "#6B6B6B"}
SEVERITY_DARK = {
    key: {**entry, "color": _SEVERITY_DARK_COLOR[key]}
    for key, entry in SEVERITY.items()
}

_CONFIDENCE_DARK_COLOR = {"alta": "#E8E8E8", "media": "#A8A8A8", "baja": "#6B6B6B"}
CONFIDENCE_BUCKETS_DARK = [
    {**bucket, "color": _CONFIDENCE_DARK_COLOR[bucket["key"]]}
    for bucket in CONFIDENCE_BUCKETS
]

COLORS_DARK = {
    **STAGE_COLORS_DARK,
    "high": SEVERITY_DARK["HIGH"]["color"],
    "medium": SEVERITY_DARK["MEDIUM"]["color"],
    "low": SEVERITY_DARK["LOW"]["color"],
}

# Mirror de --text-primary / --border-subtle / --accent (styles.css): Plotly
# no puede leer variables CSS, así que el tema activo necesita el hex resuelto
# en Python. line_color reusa --accent (no un hue nuevo) para la tendencia
# temporal, que no tiene serie categórica y por tanto no está en la tabla de
# ARD-17.
PLOT_THEME = {
    "light": {"font_color": "#1a202c", "gridcolor": "#e2e8f0", "line_color": "#4299e1"},
    "dark": {"font_color": "#e8eaed", "gridcolor": "#333c48", "line_color": "#5aa9e6"},
}


def current_theme() -> str:
    """Tema activo — la app está bloqueada a CLARO en Fase 1.

    Streamlit queda fijado a un solo modo vía un único `[theme]` en config.toml, así
    que el tema siempre es claro. El modo oscuro (y sus variantes `*_DARK`, que quedan
    dormidas) se difieren a la export estática (Fase 2), donde el toggle manual es
    instantáneo vía CSS. Las funciones `stage_colors()`/`severity_colors()`/etc. siguen
    aceptando un `theme` explícito, útil para la Fase 2 y para tests.
    """
    return "light"


def stage_colors(theme: str | None = None) -> dict:
    """STAGE_COLORS resuelto al tema activo (o al `theme` dado)."""
    return STAGE_COLORS_DARK if (theme or current_theme()) == "dark" else STAGE_COLORS


def severity_colors(theme: str | None = None) -> dict:
    """SEVERITY resuelto al tema activo (o al `theme` dado)."""
    return SEVERITY_DARK if (theme or current_theme()) == "dark" else SEVERITY


def colors_flat(theme: str | None = None) -> dict:
    """COLORS (vista plana) resuelto al tema activo (o al `theme` dado)."""
    return COLORS_DARK if (theme or current_theme()) == "dark" else COLORS


def plot_theme(theme: str | None = None) -> dict:
    """Tokens de texto/grid/línea para gráficas Plotly, resueltos al tema activo."""
    return PLOT_THEME["dark" if (theme or current_theme()) == "dark" else "light"]