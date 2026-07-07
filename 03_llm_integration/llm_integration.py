#!/usr/bin/env python3
"""
llm_integration.py

Fase 3 — Integración con LLM para generar explicaciones de causa raíz.

Soporta CUATRO backends:
    - Qwen 2.5:7B (local, vía Ollama)     -> modo local
    - Claude (Anthropic API)               -> modo cloud
    - DeepSeek (DeepSeek API)              -> modo cloud
    - OpenAI (OpenAI API)                  -> modo cloud

Uso:
    # Modo local (Qwen con Ollama)
    python llm_integration.py --mode test --backend local

    # Modo cloud (Claude con API key)
    python llm_integration.py --mode test --backend claude --api-key sk-ant-...

    # Modo cloud (DeepSeek con API key)
    python llm_integration.py --mode test --backend deepseek --api-key sk-...

    # Modo cloud (OpenAI con API key)
    python llm_integration.py --mode test --backend openai --api-key sk-proj-...

    # Modo producción con Claude
    python llm_integration.py --mode full --backend claude

Variables de entorno (recomendado):
    ANTHROPIC_API_KEY=sk-ant-...
    DEEPSEEK_API_KEY=sk-...
    OPENAI_API_KEY=sk-proj-...
    OLLAMA_URL=http://localhost:11434/api/generate
"""

import argparse
import json
import os
import re
import sys
import time
import unicodedata
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import pandas as pd
import requests
from dotenv import load_dotenv
from tqdm import tqdm

# ============================================================
# Constantes (PEP 8: mayúsculas con guión bajo)
# ============================================================

# Cargar variables de entorno antes de derivar las constantes operativas que leen
# de .env (el orden importa: load_dotenv puebla os.environ).
load_dotenv()

# --- Inferencia (comportamiento del modelo) ---
# Reproducible y auditable: se externaliza a llm_config.json y se lee por nombre vía
# load_llm_config(). Estas constantes quedan como default de los backends
# (construcción directa) y como degradación si faltara una clave del JSON.
DEFAULT_OLLAMA_URL = "http://localhost:11434/api/generate"
DEFAULT_OLLAMA_MODEL = "qwen2.5:7b"
DEFAULT_CLAUDE_MODEL = "claude-sonnet-4-6"
DEFAULT_DEEPSEEK_MODEL = "deepseek-chat"   # alternativa: "deepseek-reasoner"
DEFAULT_OPENAI_MODEL = "gpt-4o-mini"       # alternativa: "gpt-4", "gpt-4-turbo"
DEFAULT_TEMPERATURE = 0.3
DEFAULT_MAX_TOKENS = 512
DEFAULT_TIMEOUT_SECONDS = 60
DEFAULT_MAX_RETRIES = 3
# Llamada de acción (ARD-16): el contrato híbrido no cabe en 512 tokens; degradación
# si llm_config.json no trae la clave max_tokens_action.
DEFAULT_MAX_TOKENS_ACTION = 1024
# Reintentos del pase de autocrítica (ARD-16 Decisión 7): 1 llamada + 2 regeneraciones.
DEFAULT_ACTION_QA_RETRIES = 2

# --- Operativo (despliegue) ---
# Cambia por entorno, no por lógica del producto: se lee de .env con default en
# código. Documentadas en .env.example.
DEFAULT_DELAY_SECONDS = float(os.environ.get("LLM_DELAY_SECONDS", "0.5"))
RETRY_SLEEP_SECONDS = float(os.environ.get("LLM_RETRY_SLEEP_SECONDS", "2"))
DEFAULT_SAVE_EVERY = int(os.environ.get("LLM_SAVE_EVERY", "50"))

# --- Fallbacks del parser (_parse_llm_json) ---
# Rutas de degradación cuando el modelo no devuelve JSON usable; no son config
# calibrable, solo nombran lo que antes eran literales sueltos.
FALLBACK_SEVERITY = "MEDIUM"
FALLBACK_CONFIDENCE = 0.5             # JSON válido pero sin 'confianza'
FALLBACK_RAW_CHARS = 200             # recorte del texto crudo en el dict de emergencia
FALLBACK_ACTION = "Revisar manualmente con el equipo"
FALLBACK_EMERGENCY_CONFIDENCE = 0.3  # sin JSON parseable (modo local, texto libre)


# ============================================================
# Configuración de inferencia (Twelve-Factor §III) — externalizada a JSON
# ============================================================
# Espeja load_rules_config()/_thr de Fase 2 (classifier_core): ruta resuelta desde
# __file__ (no del cwd), para que funcione igual desde la suite, un notebook o una
# ejecución directa. Temperatura, max_tokens, timeout, reintentos y modelos por
# backend viven en llm_config.json (versionado), no como literales en el código.
_DEFAULT_LLM_CONFIG_PATH = Path(__file__).resolve().parent / "llm_config.json"


def load_llm_config(path=None) -> dict:
    """Carga llm_config.json y devuelve el dict de configuración de inferencia.

    Input:  path opcional (str | Path) para sobreescribir la ubicación; None usa el
            JSON convencional junto a este módulo.
    Output: dict con las claves de inferencia (`temperature`, `max_tokens`,
            `timeout_seconds`, `max_retries`, `models`, ...).
    """
    config_path = Path(path) if path else _DEFAULT_LLM_CONFIG_PATH
    with open(config_path, encoding="utf-8") as f:
        return json.load(f)


# ============================================================
# Prompt builder
# ============================================================

# Mapeo etapa → (campo de exceso que la justifica, campo del responsable a nombrar).
# Es la curación de #99 (D2.1): el ejemplo few-shot muestra SOLO la señal de la etapa
# elegida y el nombre de su responsable, para enseñar el razonamiento sin ruido.
_STAGE_SIGNAL = {
    "Vendor":  ("excess_vendor_hrs",  "VENDOR_NAME"),
    "Carrier": ("excess_carrier_hrs", "CARRIER_PARTY_NAME"),
    "DC":      ("excess_dc_hrs",      "DC_LOC_NAME"),
}


def _format_example(ex: Dict[str, Any]) -> str:
    """Formatea un ejemplo few-shot como espejo de forma + JSON ideal (#99, D2.1).

    El ejemplo replica los BLOQUES de `build_prompt` (DATOS / MÉTRICAS / CLASIFICACIÓN /
    CONTEXTO) pero curado en contenido: solo los campos que enseñan el razonamiento de la
    acción (la señal de exceso de la etapa elegida, el delay citado, el responsable a
    nombrar, el reason que se discute, y los agravantes activos). NO incluye el timeline de
    fechas (mostrarlo reenseñaría a recalcular, contra #91) ni campos de ruido.

    NOTA DE CURACIÓN (auditar a futuro): `is_rescheduled` se incluye SOLO cuando el ejemplo
    lo trae activo, y SIEMPRE como contexto neutro — la `accion_recomendada` ideal del
    ejemplo no debe culpar al vendor por la reprogramación (sesgo que ADR-05/#67 corrigieron).
    Cada ejemplo nuevo se revisa con este criterio antes de entrar al pool.

    Args:
        ex: dict con los campos del ejemplo (stage_primary, delay_days_calc, REASON_DSC,
            el excess_* y el nombre del responsable según la etapa, agravantes opcionales)
            y la salida ideal (causa_raiz, accion_recomendada, severidad,
            coincide_con_reason_code, confianza).

    Returns:
        Bloque de texto del ejemplo: entrada curada + "ANÁLISIS CORRECTO:" + JSON ideal.
    """
    stage = ex.get("stage_primary", "Desconocido")
    exc_field, resp_field = _STAGE_SIGNAL.get(stage, (None, None))

    lineas = ["EJEMPLO RESUELTO:", "DATOS DE LA PO:"]
    if resp_field and ex.get(resp_field):
        etiqueta = {"VENDOR_NAME": "Proveedor",
                    "CARRIER_PARTY_NAME": "Transportista",
                    "DC_LOC_NAME": "Centro de distribución"}[resp_field]
        lineas.append(f"- {etiqueta}: {ex[resp_field]}")

    lineas.append("MÉTRICAS CALCULADAS:")
    lineas.append(f"- Días de retraso: {ex.get('delay_days_calc', 0):.2f} días")
    if exc_field and exc_field in ex:
        etiqueta_exc = {"excess_vendor_hrs": "Exceso del proveedor",
                        "excess_carrier_hrs": "Exceso del transportista",
                        "excess_dc_hrs": "Exceso del centro de distribución"}[exc_field]
        lineas.append(f"- {etiqueta_exc}: {ex[exc_field]:.1f} horas")

    lineas.append("CLASIFICACIÓN AUTOMÁTICA:")
    lineas.append(f"- Etapa primaria del retraso: {stage}")

    lineas.append("CONTEXTO ADICIONAL:")
    lineas.append(f"- ¿Es Hot PO (urgente)? {'Sí' if ex.get('HOT_PO_FLAG', 0) == 1 else 'No'}")
    lineas.append(f"- ¿Es short ship (envío incompleto)? {'Sí' if ex.get('_short_ship', False) else 'No'}")
    # Contexto neutro (#67): solo se muestra si el ejemplo lo trae activo (ver NOTA).
    if ex.get("is_rescheduled", False):
        lineas.append("- ¿Se reprogramó la cita de entrega? Sí")
    # Espejo del comportamiento de build_prompt (#135): substage solo cuando INDETERMINADO.
    if ex.get("stage_primary") == "Indeterminado" and ex.get("indeterminado_substage"):
        lineas.append(f"- Sub-categoría INDETERMINADO: {ex['indeterminado_substage']}")
    lineas.append(f"- Código de motivo registrado por el DC: {ex.get('REASON_DSC', 'No registrado')}")

    ideal = {
        "causa_raiz": ex.get("causa_raiz", ""),
        "accion_recomendada": ex.get("accion_recomendada", ""),
        "severidad": ex.get("severidad", "MEDIUM"),
        "coincide_con_reason_code": ex.get("coincide_con_reason_code", False),
        "confianza": ex.get("confianza", 0.8),
    }
    lineas.append("ANÁLISIS CORRECTO:")
    lineas.append(json.dumps(ideal, ensure_ascii=False, indent=2))
    return "\n".join(lineas)


def _examples_block(examples: Optional[List[Dict[str, Any]]]) -> str:
    """Arma el bloque EJEMPLOS DE RAZONAMIENTO para few-shot (#99), o "" si no hay.

    El encabezado presenta los ejemplos como ILUSTRACIONES del razonamiento, no como
    plantillas, y advierte que son una muestra parcial del espacio de situaciones (#143:
    los tres ejemplos del pool son casos de discrepancia reason↔etapa; sin esa advertencia
    el modelo infiere que siempre hay discrepancia y copia la redacción). Devuelve "" en
    zero-shot, de modo que al unir con el resto del prompt no altera el comportamiento
    histórico.
    """
    if not examples:
        return ""
    partes = [
        "EJEMPLOS DE RAZONAMIENTO:",
        "Estudia estos casos resueltos como ilustraciones del razonamiento, no como "
        "plantillas. Observa cómo la etapa se decide por la señal temporal medida (no por "
        "el REASON_DSC del DC) y cómo la acción cita datos concretos del PO en lugar de una "
        "fórmula. Los ejemplos son una muestra parcial del espacio de situaciones posibles; "
        "razona cada PO con sus propios datos.\n",
    ]
    partes.extend(_format_example(ex) + "\n" for ex in examples)
    return "\n".join(partes)


# ============================================================
# Contexto de dominio condicional por (actor × señal) (#151)
# ============================================================
# El LLM producía acciones correctas pero HOMOGÉNEAS dentro de una etapa: casi no se
# diferenciaban entre POs del mismo responsable. La diversidad no puede venir del
# conocimiento compartido-por-actor (idéntico para todas sus POs); viene de lo que
# DIFIERE entre POs. Por eso se inyecta, según las SEÑALES que ya emite Fase 2, un
# repertorio de acciones de referencia acotado al caso (no la base entera).
#
# Recuperación = lookup determinista, NO RAG: la clave de ruteo (stage_primary) ya está
# calculada en Fase 2, así que basta un diccionario indexado por (actor × señal). Sin
# embeddings: reproducible y testeable.

_DEFAULT_DOMAIN_KB_PATH = Path(__file__).resolve().parent / "domain_kb.json"

# Umbrales de Fase 2: FUENTE ÚNICA en rules_config.json (no se duplican aquí). La banda de
# magnitud normaliza el exceso por la tolerancia de cada tramo leyendo de ahí.
_RULES_CONFIG_PATH = (
    Path(__file__).resolve().parent.parent / "02_clasif_reglas_negocio" / "rules_config.json"
)
_rules_thresholds_cache: Optional[Dict[str, float]] = None

# Encabezados del bloque inyectado (constantes, no literales sueltos).
_DOMAIN_HEADER = "CONTEXTO DE DOMINIO (relevante a esta PO):"
_DOMAIN_LEVERS_LEAD = (
    "Palancas y tensiones de dominio relevantes a las señales de esta PO "
    "(úsalas como insumo para razonar la causa y construir UNA recomendación "
    "anclada en las cifras; no las transcribas). Estas palancas están en horas; "
    "no dejes de citar también el retraso en días en tu causa_raiz:"
)
_DEFAULT_BAND_CUTOFFS = (1.0, 3.0)

# Etapa atribuida → campo de exceso que la banda de magnitud normaliza.
_EXCESS_FIELD = {
    "Vendor":  "excess_vendor_hrs",
    "Carrier": "excess_carrier_hrs",
    "DC":      "excess_dc_hrs",
}
# Claves de condición reconocidas por _cond_matches (una clave fuera de este set no matchea).
_COND_BOOL_KEYS = ("is_rescheduled", "is_short_ship")
_COND_STR_KEYS = ("dc_substage", "indeterminado_substage")


def load_domain_kb(path=None) -> dict:
    """Carga domain_kb.json (base de conocimiento de dominio) y devuelve su dict.

    Input:  path opcional (str | Path); None usa el JSON junto a este módulo.
    Output: dict con `band_cutoffs` y `actors` (primer + palancas por actor).
    """
    kb_path = Path(path) if path else _DEFAULT_DOMAIN_KB_PATH
    with open(kb_path, encoding="utf-8") as f:
        return json.load(f)


def _load_rules_thresholds(path=None) -> Dict[str, float]:
    """Devuelve {nombre_umbral: valor} desde rules_config.json de Fase 2 (fuente única).

    Cachea el default a nivel de módulo (se lee una vez, no por PO). Un `path` explícito
    (tests) no usa ni puebla el cache.
    """
    global _rules_thresholds_cache
    if path is not None:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return {k: v["value"] for k, v in data["thresholds"].items()}
    if _rules_thresholds_cache is None:
        data = json.loads(_RULES_CONFIG_PATH.read_text(encoding="utf-8"))
        _rules_thresholds_cache = {k: v["value"] for k, v in data["thresholds"].items()}
    return _rules_thresholds_cache


def _excess_band(row: pd.Series, actor: str, cutoffs=_DEFAULT_BAND_CUTOFFS) -> Optional[str]:
    """Banda de magnitud del exceso de la etapa ATRIBUIDA: 'bajo' / 'medio' / 'alto'.

    r = exceso_de_la_etapa / umbral_de_Fase_2 de ese tramo. cutoffs=(lo, hi):
    r ≤ lo → bajo · lo < r ≤ hi → medio · r > hi → alto. Devuelve None cuando la banda
    no aplica (Indeterminado / On-Time / actor sin campo de exceso, o exceso ≤ 0). En
    Indeterminado el exceso se retira a propósito (ADR-14), así que no hay banda.
    """
    field = _EXCESS_FIELD.get(actor)
    if not field:
        return None
    try:
        excess = float(row.get(field, 0) or 0)
    except (TypeError, ValueError):
        return None
    if excess <= 0:
        return None
    thr = _load_rules_thresholds()
    if actor == "DC":
        threshold = thr["dock_hrs"] if row.get("dc_substage") == "Dock" else thr["yard_wait_hrs"]
    elif actor == "Vendor":
        threshold = thr["vendor_gap_hrs"]
    else:  # Carrier
        threshold = thr["carrier_lag_hrs"]
    if threshold <= 0:
        return None
    r = excess / threshold
    lo, hi = cutoffs
    if r <= lo:
        return "bajo"
    if r <= hi:
        return "medio"
    return "alto"


def _one_cond_ok(key: str, want, row: pd.Series, band: Optional[str]) -> bool:
    """Evalúa UNA condición del `cond`. Clave no reconocida → False (falla cerrada)."""
    if key == "excess_band":
        return band == want
    if key == "hot":
        return (row.get("HOT_PO_FLAG", 0) == 1) == bool(want)
    if key in _COND_BOOL_KEYS:
        return bool(row.get(key, False)) == bool(want)
    if key in _COND_STR_KEYS:
        return str(row.get(key, "")) == str(want)
    return False


def _cond_matches(cond: dict, row: pd.Series, band: Optional[str]) -> bool:
    """True si la fila cumple TODAS las condiciones de `cond` (AND lógico).

    Claves reconocidas: is_rescheduled / is_short_ship (bool), hot (HOT_PO_FLAG == 1),
    excess_band ('bajo'/'medio'/'alto', ya calculada), dc_substage / indeterminado_substage
    (igualdad). Una clave no reconocida → la acción no aplica (falla cerrada; un lint del KB
    caza el typo). `cond` vacío → True (acción incondicional del actor).
    """
    return all(_one_cond_ok(key, want, row, band) for key, want in cond.items())


def select_domain_context(row: pd.Series, kb: Optional[dict]) -> str:
    """Arma el bloque CONTEXTO DE DOMINIO acotado a ESTA PO, o '' si no aplica.

    Rutea por stage_primary al bucket del actor en `kb`, calcula la banda de magnitud y
    filtra las palancas a aquellas cuyas condiciones cumple la PO (vía _cond_matches).
    Devuelve '' cuando kb es None/vacío, cuando el actor no está en el KB (On-Time,
    Desconocido) o cuando no hay ni primer ni palancas que mostrar — así, con kb=None el
    prompt no cambia (invariante zero-shot).
    """
    if not kb:
        return ""
    actor = str(row.get("stage_primary", ""))
    entry = kb.get("actors", {}).get(actor)
    if not entry:
        return ""
    cutoffs = kb.get("band_cutoffs", _DEFAULT_BAND_CUTOFFS)
    band = _excess_band(row, actor, cutoffs)
    lines = [_DOMAIN_HEADER]
    primer = str(entry.get("primer", "")).strip()
    if primer:
        lines.append(f"- {primer}")
    matched = [
        lever["lever"]
        for lever in entry.get("levers", [])
        if "lever" in lever and _cond_matches(lever.get("cond", {}), row, band)
    ]
    if matched:
        lines.append(_DOMAIN_LEVERS_LEAD)
        lines.extend(f"- {a}" for a in matched)
    if len(lines) == 1:  # solo el encabezado, sin contenido útil
        return ""
    return "\n".join(lines)


def build_prompt(
    row: pd.Series,
    examples: Optional[List[Dict[str, Any]]] = None,
    kb: Optional[dict] = None,
) -> str:
    """
    Construye el prompt para el LLM a partir de una fila del DataFrame.

    Sigue el lineamiento del mentor (kickoff §03 / README §5): inyecta toda la
    aritmética ya resuelta (timeline + MÉTRICAS CALCULADAS) e instruye al modelo a
    INTERPRETAR sin recalcular, citando textualmente las cifras dadas. La explicación
    pedida (`causa_raiz`) son 2-3 oraciones con los elementos del mentor: etapa exacta,
    delay cuantificado citado, coincidencia con REASON_DSC y agravantes. La
    reprogramación de cita (`is_rescheduled`, #67) se pasa como contexto neutro —un
    evento, no una causa de etapa—, no como agravante automático.

    Few-shot (#99): si se pasan `examples`, se antepone un bloque EJEMPLOS DE RAZONAMIENTO
    (antes de INSTRUCCIONES) que enseña a derivar la acción de la señal temporal y a no
    copiar el REASON_DSC. Sin `examples` (default), el prompt es idéntico al zero-shot
    histórico — no cambia el comportamiento existente.

    Anti-overfitting (#143): un bloque CÓMO RAZONAR (entre INSTRUCCIONES y el formato JSON)
    enseña la combinatoria de dominio que los ejemplos no muestran —las cuatro etapas y las
    tres relaciones posibles con el REASON_DSC (coincide / discrepa / vacío)—, porque los
    ejemplos del pool son todos de discrepancia y el modelo, sin esta guía, copiaba esa
    redacción como plantilla. Las descripciones de campo del JSON remiten a esta guía para
    no duplicarla.

    Args:
        row: Una fila del DataFrame con los datos de una PO. Campos leídos vía
            row.get(..., default), por lo que una fila incompleta no rompe (los
            faltantes caen a 'N/A'/0).
        examples: lista opcional de ejemplos resueltos (few-shot). Cada uno es un dict
            con los campos curados de entrada y la salida ideal (ver `_format_example`).
            None o lista vacía → zero-shot.
        kb: dict opcional de la base de conocimiento de dominio (domain_kb.json). Si se
            pasa, `select_domain_context` inyecta un bloque CONTEXTO DE DOMINIO con el
            primer del actor (stage_primary) y las acciones de referencia cuyas condiciones
            cumple la PO. None (default) → sin bloque, prompt byte-idéntico al zero-shot.

    Returns:
        Prompt formateado listo para enviar al LLM.
    """
    hot_flag = "Sí" if row.get('HOT_PO_FLAG', 0) == 1 else "No"
    short_ship = "Sí" if row.get('_short_ship', False) else "No"
    # Contexto neutro (#67): la reprogramación de cita es un evento, NO una causa de
    # etapa. Se muestra como dato para juzgar el REASON_DSC; no implica culpa del vendor.
    rescheduled = "Sí" if row.get('is_rescheduled', False) else "No"

    context_lines = [
        "CONTEXTO ADICIONAL:",
        f"- ¿Es Hot PO (urgente)? {hot_flag}",
        f"- ¿Es short ship (envío incompleto)? {short_ship}",
        f"- ¿Se reprogramó la cita de entrega? {rescheduled}",
    ]
    # Solo cuando el clasificador no pudo resolver la etapa (#135): indicar si fue
    # por falta de señal temporal (sin_datos) o por empate entre etapas (sin_causa_dominante).
    if row.get("stage_primary") == "Indeterminado":
        substage = row.get("indeterminado_substage", "")
        if substage:
            context_lines.append(f"- Sub-categoría INDETERMINADO: {substage}")
    context_lines.append(
        f"- Código de motivo registrado por el DC: {row.get('REASON_DSC', 'No registrado')}"
    )

    # El exceso por etapa (proveedor/transportista/CD) es la SEÑAL DE ATRIBUCIÓN de Fase 2:
    # solo es válida cuando el clasificador atribuyó una etapa. En Indeterminado la atribución
    # se retiró a propósito (sin_datos = faltan timestamps que aíslen la etapa; sin_causa_
    # dominante = ningún tramo destaca), así que mostrar un exceso crudo —p. ej. el push de
    # vendor que sobrevive en un sin_datos— invitaría a sobre-escribir el veredicto. Se omiten
    # esas líneas para Indeterminado; yard/dock crudos sí se muestran (observación, no atribución).
    metric_lines = [
        "MÉTRICAS CALCULADAS:",
        f"- Días de retraso: {row.get('delay_days_calc', 0):.2f} días",
        f"- Espera en patio (yard): {row.get('yard_wait_calc_hrs', 0):.1f} horas",
        f"- Tiempo de descarga (dock): {row.get('dock_calc_hrs', 0):.1f} horas",
    ]
    if row.get("stage_primary") != "Indeterminado":
        metric_lines += [
            f"- Exceso del proveedor: {row.get('excess_vendor_hrs', 0):.1f} horas",
            f"- Exceso del transportista: {row.get('excess_carrier_hrs', 0):.1f} horas",
            f"- Exceso del centro de distribución: {row.get('excess_dc_hrs', 0):.1f} horas",
        ]
    metric_lines[-1] += "\n"

    # Contexto de dominio condicional (#151): vacío salvo que se pase kb. Con kb=None el
    # bloque no se añade y el prompt es byte-idéntico al zero-shot histórico.
    domain_block = select_domain_context(row, kb)

    # Cierre de CÓMO RAZONAR sobre la acción (#151): con kb=None se preserva el cierre
    # histórico (dos líneas ilustrativas) para no tocar el prompt zero-shot que sirve de
    # baseline de no-regresión. Con kb, esas dos líneas fijas se sustituyen por un puntero
    # a las palancas por-PO de CONTEXTO DE DOMINIO, para no competir con ellas como plantilla.
    if kb:
        accion_guidance = (
            "La acción se dirige al responsable de la etapa MEDIDA —no al que sugiere el motivo "
            "si discrepa— y su firmeza depende del impacto: la magnitud del exceso/retraso y los "
            "agravantes (hot PO, short ship) marcan si toca un escalamiento urgente o una "
            "revisión operativa ligera. Las palancas y tensiones de CONTEXTO DE DOMINIO (arriba) "
            "son el insumo concreto para esa firmeza y ese destinatario en ESTE PO: úsalas para "
            "razonar la acción, no un fraseo fijo.\n"
        )
    else:
        accion_guidance = (
            "La acción se dirige al responsable de la etapa MEDIDA —no al que sugiere el motivo "
            "si discrepa— y su firmeza depende del impacto: la magnitud del exceso/retraso y los "
            "agravantes (hot PO, short ship) marcan si toca un escalamiento urgente o una "
            "revisión operativa ligera. El fraseo y el tono varían según el caso; estas dos "
            "líneas solo ilustran el rango, no son plantillas:\n"
            "- \"Abrir un reclamo con [transportista] por las 30.8 h de exceso de tránsito y "
            "exigir un plan correctivo con fecha.\"\n"
            "- \"Revisar con el equipo del [DC] el tiempo de descarga, que concentra el grueso "
            "del retraso.\"\n"
        )

    prompt_lines = [
        "Eres un analista experto en cadena de suministro. "
        "Analiza este Purchase Order retrasado.\n",
        "DATOS DE LA PO:",
        f"- Número de PO: {row.get('PO_NBR', 'N/A')}",
        f"- Proveedor: {row.get('VENDOR_NAME', 'N/A')}",
        f"- Centro de distribución: {row.get('DC_LOC_NAME', 'N/A')}",
        f"- Transportista: {row.get('CARRIER_PARTY_NAME', 'N/A')}\n",
        "TIMELINE (fechas clave):",
        f"- Fecha prometida (STA): {row.get('STA_DT', 'N/A')}",
        f"- Fecha real de recibo: {row.get('RECPT_DT', 'N/A')}",
        f"- Cita aprobada: {row.get('APPROVED_DT', 'N/A')}",
        f"- Llegada del tráiler: {row.get('TRAILER_ARRIVE_DT', 'N/A')}",
        f"- Check-in (inicio descarga): {row.get('CHECKIN_DT', 'N/A')}",
        f"- Check-out (fin descarga): {row.get('CHECKOUT_DT', 'N/A')}\n",
        *metric_lines,
        "CLASIFICACIÓN AUTOMÁTICA:",
        f"- Etapa primaria del retraso: {row.get('stage_primary', 'Desconocido')}",
        f"- Causas múltiples: {row.get('stage_multi', 'Ninguna')}\n",
        "\n".join(context_lines) + "\n",
        *([domain_block + "\n"] if domain_block else []),
        _examples_block(examples),
        "INSTRUCCIONES:",
        "Tu trabajo es INTERPRETAR los datos dados, NO calcular. Usa ÚNICAMENTE las "
        "cifras de las secciones MÉTRICAS CALCULADAS y TIMELINE. No estimes, no "
        "recalcules fechas ni horas, no inventes números. Toda cifra que menciones en "
        "tu explicación debe ser una de las dadas arriba, citada textualmente "
        "(p. ej. \"un retraso de 4.2 días\").\n",
        "CÓMO RAZONAR ESTE PO (guía, no texto a copiar):",
        "La 'Etapa primaria del retraso' de la CLASIFICACIÓN AUTOMÁTICA es la fuente de verdad, "
        "ya medida por la señal temporal: la etapa que nombres en tu explicación DEBE ser "
        "exactamente esa. El REASON_DSC es una nota humana que puede fallar; sirve para "
        "CONTRASTAR, nunca para sustituir la etapa, y no lo promuevas a etapa aunque nombre una "
        "(p. ej. 'Vendor delayed shipment'). Contrasta el motivo con la etapa medida:\n"
        "- Vendor: el retraso nace antes del tránsito (envío tardío o cita reprogramada).\n"
        "- Carrier: el exceso está en el tránsito del transportista hacia el DC.\n"
        "- DC: el exceso está en la recepción del centro (espera en patio o descarga).\n"
        "- Indeterminado: la señal no aísla una etapa. Declara la etapa como indeterminada y "
        "explica por qué (sin_datos = faltan timestamps que la aíslen; sin_causa_dominante = "
        "varias etapas pesan sin una dominante). Aunque el REASON_DSC nombre una etapa, NO la "
        "adoptes: no hay señal medible que la confirme.\n",
        "Al comparar el REASON_DSC con la etapa medida puede que coincidan (el motivo apunta "
        "a la misma etapa → la evidencia lo respalda), que discrepen (apunta a otra causa → "
        "di en qué difieren) o que el motivo sea vacío o 'Not applicable' (indícalo sin "
        "evaluarlo). Decide con los datos de ESTE PO, no por la forma de los ejemplos.\n",
        accion_guidance,
        "Genera un análisis en formato JSON. "
        "Responde ÚNICAMENTE con el JSON, sin texto adicional.\n",
        "Formato requerido:",
        "{",
        '  "causa_raiz": "2-3 oraciones: etapa exacta, retraso citado de los datos, '
        'relación con el REASON_DSC (ver CÓMO RAZONAR) y agravantes si los hay",',
        '  "accion_recomendada": "Acción concreta al responsable de la etapa medida, '
        'anclada en los datos de este PO (ver CÓMO RAZONAR). No genérica",',
        '  "severidad": "HIGH o MEDIUM o LOW",',
        '  "coincide_con_reason_code": true o false,',
        '  "confianza": 0.0 a 1.0',
        "}\n",
        "Reglas de severidad (umbral del mentor):",
        "- HIGH: Hot PO con retraso > 3 días, O short ship con retraso",
        "- MEDIUM: Retraso > 0 días sin agravantes",
        "- LOW: Borderline (casi a tiempo, retraso < 1 día)\n",
        "Regla para coincide_con_reason_code:",
        "- true si tu causa_raiz coincide con el REASON_DSC del DC",
        "- false si discrepas"
    ]

    return "\n".join(prompt_lines)


# ============================================================
# Llamada de acción (ARD-16, ola 1): contrato híbrido + checks por regla
# ============================================================
# Segunda llamada por PO detrás del flag opt-in `action_call` (patrón de ARD-15:
# default apagado, producción intacta). La llamada 1 diagnostica (etapa/causa/severidad,
# auditada por Fase 2); esta llamada PLANIFICA: hipótesis de mecanismo bajo el nivel
# etapa, plan (inmediata/correctiva/preventiva) e hipótesis alternativa con su paso
# discriminante. Perímetro de ARD-16 Decisión 2: los hechos provienen solo de los datos
# (cifras citadas textualmente — ADR-14 se conserva para las premisas factuales); las
# generalizaciones de dominio del modelo quedan permitidas y MARCADAS en la redacción.
# Sin playbook y sin few-shot de acciones (descartes registrados en el ARD).

# Llaves de nivel superior del contrato, EN ORDEN. El orden es requisito, no estilo:
# condiciona el plan al razonamiento ya generado (generación autoregresiva).
_ACTION_TOP_KEYS = (
    "razonamiento", "hipotesis_principal", "hipotesis_alternativa", "confianza",
)

# Campos planos que devuelve el parseo del contrato; todos son de texto (la confianza
# va aparte) y participan del check de esquema y del de cifras ∈ input.
_ACTION_TEXT_FIELDS = (
    "razonamiento", "hipotesis", "hipotesis_evidencia",
    "accion_inmediata", "accion_correctiva", "accion_preventiva",
    "hipotesis_alt", "paso_discriminante",
)

# Verbos meta (lista CERRADA de ARD-16 Decisión 3): no cuentan como acción principal.
# Detección por stem del primer token (cubre conjugaciones: revisar/revise/revisa...)
# más el compuesto dar/hacer seguimiento.
_META_VERB_STEMS = ("revis", "analiz", "investig", "monitor")
_META_COMPOUND_LEADS = ("dar", "da", "de", "dando", "hacer", "haz", "haga", "haciendo")

# Términos que satisfacen la decisión del faltante ante short ship (ARD-16 Decisión 3).
_SHORT_SHIP_DECISION_KEYS = ("re-emitir", "reemitir", "re emitir", "esperar", "cancelar")

# Términos con los que la HIPÓTESIS (el campo solo, no el razonamiento) reconoce la
# indeterminación en POs Indeterminado (ARD-16 ola 2). Compartida con la tasa del
# evaluador (patrón de is_meta_action: check y métrica usan la misma lista).
_INDET_HYP_KEYS = (
    "indetermin", "dato faltante", "no atribuible", "no se puede atribuir",
    "esclarecer", "por confirmar", "si se confirma",
)
# "si" condicional como token: la formulación que el prompt pide ("si <dato> muestra X,
# el mecanismo es A"). El gate de la ola 2 mostró el hueco: las 4 hipótesis Indeterminado
# salieron condicionales pero sin palabra literal de la lista, y el check las marcaba
# (mismo tipo de hueco de vocabulario que sin_decision_faltante en la ola 1). Solo se
# evalúa en POs Indeterminado, donde el falso positivo del token es mínimo ("sí" afirmativo
# también normaliza a "si"; aceptado y raro dentro de una hipótesis).
_COND_SI_RE = re.compile(r"\bsi\b")

# Grupos de reason_group_manual que apuntan a una etapa (línea de concordancia
# motivo↔etapa de la llamada 2; Unknown / On-Time no son etapas evaluables).
_REASON_STAGE_GROUPS = ("Vendor", "Carrier", "DC")

# Alias en español de cada etapa para el check `etapa_incorrecta`: el gate de la ola 2
# mostró el falso positivo — el modelo escribe "proveedor" y el check buscaba el literal
# "Vendor" (100197/100318). Comparación sobre texto normalizado (_norm_text).
_STAGE_ALIASES = {
    "Vendor": ("vendor", "proveedor"),
    "Carrier": ("carrier", "transportista"),
    "DC": ("dc", "centro de distribucion"),
}

# Cifras: el MISMO patrón se aplica al prompt y a la salida; la comparación es por
# float, de modo que 4.2 y 4.20 cuentan como la misma cifra.
_NUMBER_RE = re.compile(r"\d+(?:[.,]\d+)?")


def _norm_text(texto) -> str:
    """Minúsculas sin acentos, para comparar texto del LLM de forma robusta."""
    sin_acentos = "".join(
        c for c in unicodedata.normalize("NFD", str(texto))
        if unicodedata.category(c) != "Mn"
    )
    return sin_acentos.lower()


def reconoce_indeterminacion(texto) -> bool:
    """True si una hipótesis reconoce la indeterminación (ARD-16 ola 2).

    Dos vías: una clave literal de _INDET_HYP_KEYS ("indetermin", "dato faltante"...)
    o la formulación condicional que el prompt pide (el "si" condicional como token,
    _COND_SI_RE). Función ÚNICA para el check `indeterminado_sin_reconocer` y la tasa
    del evaluador: los dos miden lo mismo por construcción.
    """
    t = _norm_text(texto)
    return any(k in t for k in _INDET_HYP_KEYS) or bool(_COND_SI_RE.search(t))


def compute_dataset_stats(df: pd.DataFrame) -> Dict[str, Any]:
    """Estadísticos globales DETERMINISTAS para los comparativos de la llamada 2.

    Se computan una vez por corrida sobre los tardíos (delay_days_calc > 0) del
    DataFrame clasificado completo — no por PO ni sobre una muestra:
      - delay_values / delay_median: retraso total de todos los tardíos.
      - excess[etapa]: valores y mediana del exceso de esa etapa ENTRE los POs
        ATRIBUIDOS a ella (la magnitud típica cuando esa etapa es la causa).
    ARD-16 Decisión 3: estos comparativos van al prompt de TODA PO — presentarlos
    condicionalmente introduciría juicio por selección.
    """
    tardios = df[df["delay_days_calc"] > 0]
    delays = tardios["delay_days_calc"].dropna().astype(float)
    stats: Dict[str, Any] = {
        "delay_values": delays.tolist(),
        "delay_median": float(delays.median()) if len(delays) else 0.0,
        "excess": {},
    }
    for etapa, campo in _EXCESS_FIELD.items():
        if campo in tardios.columns:
            serie = tardios.loc[
                tardios["stage_primary"] == etapa, campo
            ].dropna().astype(float)
        else:
            serie = pd.Series(dtype=float)
        stats["excess"][etapa] = {
            "values": serie.tolist(),
            "median": float(serie.median()) if len(serie) else 0.0,
        }
    return stats


def _percentile_rank(values: List[float], x: float) -> Optional[int]:
    """Percentil entero (0-100) de x dentro de values: % de valores estrictamente
    menores. Determinista; None si la lista está vacía."""
    if not values:
        return None
    return round(100 * sum(1 for v in values if v < x) / len(values))


def _reschedule_line(row: pd.Series) -> str:
    """Línea de la magnitud del reschedule en horas (primera cita aprobada → vigente).

    Magnitud hoy oculta al prompt (ARD-16 Decisión 3). No está precalculada en el
    pipeline: se deriva determinista de DT_APPT_CURRENT_APPROVED −
    DT_APPT_FIRST_APPROVED. Valor neutro cuando no hubo reprogramación (línea
    incondicional, sin juicio por selección).
    """
    if not bool(row.get("is_rescheduled", False)):
        return "- Reprogramación de la cita: sin reprogramación (0.0 h)"
    try:
        delta = (
            pd.Timestamp(row.get("DT_APPT_CURRENT_APPROVED"))
            - pd.Timestamp(row.get("DT_APPT_FIRST_APPROVED"))
        )
        horas = delta.total_seconds() / 3600
    except (TypeError, ValueError):
        return "- Reprogramación de la cita: magnitud no disponible (falta timestamp)"
    if pd.isna(horas):
        return "- Reprogramación de la cita: magnitud no disponible (falta timestamp)"
    return (
        f"- Reprogramación de la cita: {horas:+.1f} horas entre la primera cita "
        "aprobada y la vigente"
    )


def _reason_concordance_line(row: pd.Series) -> str:
    """Línea de concordancia motivo↔etapa medida (ARD-16 ola 2, meta-señal REASON_DSC).

    DETERMINISTA: compara reason_group_manual (mapeo REASON_DSC → etapa de Fase 2,
    classifier_core) contra stage_primary — no depende del juicio de la llamada 1, que
    hereda la varianza entre corridas. Incondicional con 3 estados (concuerda / discrepa /
    no evaluable), como la línea de reschedule: sin juicio por selección. La discrepancia
    se presenta como meta-señal del PROCESO DE ANOTACIÓN (habilita hipótesis de proceso),
    nunca como etapa alternativa: la regla vigente de no promover el REASON_DSC no cambia.
    """
    grupo = str(row.get("reason_group_manual", "Unknown"))
    etapa = str(row.get("stage_primary", "Desconocido"))
    if grupo not in _REASON_STAGE_GROUPS:
        return ("- Concordancia motivo↔etapa: no evaluable (el motivo anotado no "
                "apunta a una etapa).")
    if grupo == etapa:
        return (f"- Concordancia motivo↔etapa: el motivo anotado apunta a la misma "
                f"etapa medida ({etapa}).")
    return (
        f"- Concordancia motivo↔etapa: DISCREPA — el motivo anotado apunta a {grupo} "
        f"y la etapa medida es {etapa}. Trátala como meta-señal del PROCESO DE "
        "ANOTACIÓN (p. ej. handoff mal registrado o anotación por inercia): puede "
        "sustentar una hipótesis de proceso, nunca sustituir la etapa medida."
    )


def _order_magnitude_lines(row: pd.Series) -> List[str]:
    """Bloque MAGNITUDES DE LA ORDEN: los datos hoy ocultos al prompt (ARD-16 D3).

    Incondicionales, con valor neutro cuando no aplican: tamaño de la orden, cajas
    embarcadas + fill rate real (con el umbral de short ship al lado, para que el
    modelo dimensione el margen) y la magnitud de la reprogramación en horas.
    """
    lineas = ["MAGNITUDES DE LA ORDEN:"]
    pedidas = row.get("NUM_CASES_ORDERED")
    if pedidas is not None and not pd.isna(pedidas):
        lineas.append(f"- Tamaño de la orden: {float(pedidas):.0f} cajas pedidas")
    else:
        lineas.append("- Tamaño de la orden: no disponible")
    embarcadas = row.get("NUM_CASES_SHIPPED")
    fill = row.get("_fill_rate")
    umbral_ss = _load_rules_thresholds()["short_ship_fill_rate"] * 100
    if (embarcadas is not None and not pd.isna(embarcadas)
            and fill is not None and not pd.isna(fill)):
        lineas.append(
            f"- Cajas embarcadas: {float(embarcadas):.0f} (fill rate: "
            f"{float(fill) * 100:.1f}%; umbral de short ship: por debajo de "
            f"{umbral_ss:.0f}%)"
        )
    else:
        lineas.append("- Cajas embarcadas: no disponible")
    lineas.append(_reschedule_line(row))
    return lineas


def _comparative_lines(row: pd.Series, stats: Dict[str, Any]) -> List[str]:
    """Bloque COMPARATIVOS DEL DATASET: percentiles y medianas ya calculados.

    Incondicionales para toda PO (ARD-16 D3). La línea del exceso solo existe para
    etapas ATRIBUIDAS (Vendor/Carrier/DC): en Indeterminado el exceso se retira por
    ADR-14 — regla por etapa, no juicio por PO; medianas y percentil del delay sí van.
    """
    lineas = ["COMPARATIVOS DEL DATASET (ya calculados; no los recalcules):"]
    delay = float(row.get("delay_days_calc", 0) or 0)
    p_delay = _percentile_rank(stats.get("delay_values", []), delay)
    if p_delay is not None:
        lineas.append(
            f"- El retraso total de esta PO ({delay:.2f} días) está en el percentil "
            f"{p_delay} de los POs tardíos del dataset "
            f"(mediana: {stats['delay_median']:.2f} días)."
        )
    etapa = str(row.get("stage_primary", ""))
    campo = _EXCESS_FIELD.get(etapa)
    if campo:
        exceso = float(row.get(campo, 0) or 0)
        info = stats.get("excess", {}).get(etapa, {})
        p_exc = _percentile_rank(info.get("values", []), exceso)
        if p_exc is not None:
            lineas.append(
                f"- El exceso de {etapa} de esta PO ({exceso:.1f} h) está en el "
                f"percentil {p_exc} de los POs tardíos atribuidos a {etapa} "
                f"(mediana de esa etapa: {info['median']:.1f} h)."
            )
    medianas = stats.get("excess", {})
    if medianas:
        partes = " · ".join(
            f"{et} {medianas[et]['median']:.1f} h"
            for et in ("Vendor", "Carrier", "DC") if et in medianas
        )
        lineas.append(f"- Medianas de exceso por etapa entre tardíos: {partes}.")
    return lineas


def build_action_prompt(
    row: pd.Series,
    diagnosis: Dict[str, Any],
    stats: Dict[str, Any],
) -> str:
    """Construye el prompt de la LLAMADA DE ACCIÓN (llamada 2, ARD-16 ola 1).

    Rol: planner de abastecimiento con autoridad de decisión, no analista que asesora
    (el antídoto directo a la meta-acción: quien ejecuta no puede delegar). Recibe el
    diagnóstico de la llamada 1 como fuente de verdad — sin esa ancla el modelo
    re-diagnosticaría la etapa que Fase 2 ya validó — y pide el contrato híbrido
    razonamiento → hipotesis_principal{hipotesis, evidencia, plan{...}} →
    hipotesis_alternativa{hipotesis, paso_discriminante} → confianza, con las llaves
    EN ORDEN. Sin límite de longitud por campo (a diferencia de la llamada 1).

    Los bloques DATOS/TIMELINE/MÉTRICAS/CONTEXTO espejan build_prompt para que ambas
    llamadas vean los mismos hechos; se suman las magnitudes destapadas
    (_order_magnitude_lines) y los comparativos globales (_comparative_lines).

    Args:
        row: fila del DataFrame clasificado (una PO tardía).
        diagnosis: dict devuelto por la llamada 1 (causa_raiz, severidad, ...).
        stats: dict de compute_dataset_stats sobre el DataFrame completo.

    Returns:
        Prompt de la llamada de acción, listo para backend.call_raw().
    """
    stage = row.get("stage_primary", "Desconocido")

    hot_flag = "Sí" if row.get("HOT_PO_FLAG", 0) == 1 else "No"
    short_ship = "Sí" if row.get("_short_ship", False) else "No"
    rescheduled = "Sí" if row.get("is_rescheduled", False) else "No"
    context_lines = [
        "CONTEXTO ADICIONAL:",
        f"- ¿Es Hot PO (urgente)? {hot_flag}",
        f"- ¿Es short ship (envío incompleto)? {short_ship}",
        f"- ¿Se reprogramó la cita de entrega? {rescheduled}",
    ]
    if stage == "Indeterminado":
        substage = row.get("indeterminado_substage", "")
        if substage:
            context_lines.append(f"- Sub-categoría INDETERMINADO: {substage}")
    context_lines.append(
        f"- Código de motivo registrado por el DC: {row.get('REASON_DSC', 'No registrado')}"
    )
    context_lines.append(_reason_concordance_line(row))

    # Espejo de build_prompt: en Indeterminado los excesos se retiran (ADR-14).
    metric_lines = [
        "MÉTRICAS CALCULADAS:",
        f"- Días de retraso: {row.get('delay_days_calc', 0):.2f} días",
        f"- Espera en patio (yard): {row.get('yard_wait_calc_hrs', 0):.1f} horas",
        f"- Tiempo de descarga (dock): {row.get('dock_calc_hrs', 0):.1f} horas",
    ]
    if stage != "Indeterminado":
        metric_lines += [
            f"- Exceso del proveedor: {row.get('excess_vendor_hrs', 0):.1f} horas",
            f"- Exceso del transportista: {row.get('excess_carrier_hrs', 0):.1f} horas",
            f"- Exceso del centro de distribución: {row.get('excess_dc_hrs', 0):.1f} horas",
        ]
    metric_lines[-1] += "\n"

    magnitude_lines = _order_magnitude_lines(row)
    magnitude_lines[-1] += "\n"
    comparative_lines = _comparative_lines(row, stats)
    comparative_lines[-1] += "\n"

    # Diagnóstico diferencial (ARD-16 ola 2): la regla mecanismo-vs-etiqueta es genérica
    # para toda etapa; SOLO Vendor recibe el pointer de señales (fill rate /
    # reprogramación) porque ahí está el síntoma del baseline (5/8 hipótesis convergen a
    # "capacidad del proveedor"). Condicional por etapa determinista (patrón de #151),
    # no un menú curado de causas (descarte de ARD-16, Opción B).
    differential_lines = [
        "DIAGNÓSTICO DIFERENCIAL (obligatorio):",
        "- Tu hipótesis nombra un MECANISMO, no una etiqueta: qué falló y cómo eso "
        "produce exactamente las cifras observadas. Una etiqueta genérica (\"capacidad "
        "del proveedor\", \"congestión\") sin el dato que la sostiene no cuenta como "
        "mecanismo.",
        "- Las dos hipótesis nombran mecanismos DISTINTOS y DISTINGUIBLES: si la "
        "alternativa es compatible con exactamente la misma evidencia y ningún dato "
        "podría separarlas, elige otra alternativa.",
        "- La evidencia de cada hipótesis cita las cifras que la favorecen SOBRE la "
        "otra, no solo las que la acompañan.",
    ]
    if stage == "Vendor":
        differential_lines.append(
            "- En esta etapa (Vendor), el fill rate y la magnitud de la reprogramación "
            "separan mecanismos: un fill rate corto apunta a falta de producto "
            "(inventario/producción); una entrega completa pero reprogramada apunta a "
            "planificación/agenda, no a falta de producto."
        )
    differential_lines[-1] += "\n"

    # Reparto multi-actor (ARD-16 ola 2): solo con stage_multi activo (≥2 etapas). El
    # plan puede repartir correctiva/preventiva entre actores, pero la acción inmediata
    # es UNA: la del cuello de botella (stage_primary, la etapa dominante por medición).
    stage_multi = str(row.get("stage_multi", "Ninguno"))
    multi_actor_lines = []
    if " + " in stage_multi:
        multi_actor_lines.append(
            f"- Hay causas múltiples activas ({stage_multi}): las acciones correctiva "
            "y preventiva pueden repartirse entre esos actores, cada una citando la "
            "cifra de exceso de la etapa que atiende; la acción inmediata sigue siendo "
            f"UNA sola, dirigida al cuello de botella (la etapa primaria: {stage})."
        )

    prompt_lines = [
        "Eres el planner de abastecimiento responsable de esta Purchase Order "
        "retrasada. Tienes autoridad para decidir los siguientes pasos: el plan que "
        "emitas es el que se ejecuta, no una sugerencia para otro equipo.\n",
        "DIAGNÓSTICO VALIDADO (fuente de verdad, no lo re-litigues):",
        f"- Etapa primaria del retraso: {stage}",
        f"- Causas múltiples: {row.get('stage_multi', 'Ninguna')}",
        f"- Causa raíz identificada: {diagnosis.get('causa_raiz', '')}",
        f"- Severidad: {diagnosis.get('severidad', '')}\n",
        "DATOS DE LA PO:",
        f"- Número de PO: {row.get('PO_NBR', 'N/A')}",
        f"- Proveedor: {row.get('VENDOR_NAME', 'N/A')}",
        f"- Centro de distribución: {row.get('DC_LOC_NAME', 'N/A')}",
        f"- Transportista: {row.get('CARRIER_PARTY_NAME', 'N/A')}\n",
        "TIMELINE (fechas clave):",
        f"- Fecha prometida (STA): {row.get('STA_DT', 'N/A')}",
        f"- Fecha real de recibo: {row.get('RECPT_DT', 'N/A')}",
        f"- Cita aprobada: {row.get('APPROVED_DT', 'N/A')}",
        f"- Llegada del tráiler: {row.get('TRAILER_ARRIVE_DT', 'N/A')}",
        f"- Check-in (inicio descarga): {row.get('CHECKIN_DT', 'N/A')}",
        f"- Check-out (fin descarga): {row.get('CHECKOUT_DT', 'N/A')}\n",
        *metric_lines,
        *magnitude_lines,
        *comparative_lines,
        "\n".join(context_lines) + "\n",
        "PERÍMETRO DE RAZONAMIENTO:",
        "- Los HECHOS de esta PO y del dataset son únicamente los datos de arriba. "
        "Toda cifra que uses debe ser una de las dadas, citada textualmente. No "
        "inventes hechos ni números.",
        "- Tu conocimiento de dominio de cadena de suministro SÍ está habilitado para "
        "generalizar (causas típicas, prácticas de industria, consecuencias "
        "operativas). Cuando lo uses, márcalo en la redacción (p. ej. \"como patrón "
        "de industria…\", \"típicamente…\"), separado de lo que los datos muestran.",
        "- Si los datos no alcanzan para distinguir dos mecanismos, decláralo: esa "
        "carencia es exactamente lo que tu paso discriminante debe resolver.\n",
        "TU TAREA:",
        f"La etapa ya está decidida ({stage}); tu trabajo es el mecanismo DEBAJO de "
        "ese nivel (según la etapa: inventario o capacidad del proveedor, "
        "documentación, congestión de puertas o de patio, planificación de rutas…) y "
        "el plan que se deriva de él. Si la etapa es Indeterminado, tu hipótesis NO "
        "afirma un mecanismo como causa: reconoce explícitamente la indeterminación, "
        "identifica el dato faltante que impide atribuir la etapa y formula el "
        "mecanismo en condicional (\"si <dato> muestra X, el mecanismo es A; si "
        "muestra Y, es B\"). La acción inmediata es el paso de esclarecimiento: "
        "conseguir hoy ese dato, con la decisión que depende de él.\n",
        *differential_lines,
        "REGLAS DEL PLAN (obligatorias):",
        "- La acción inmediata es una medida ejecutable hoy, con destinatario y "
        "objeto concretos. Revisar, analizar, investigar, monitorear o dar "
        "seguimiento NO cuentan como acción principal: delegan la decisión en vez de "
        "tomarla.",
        "- Toda verificación que incluyas nombra el DATO exacto a obtener y la "
        "DECISIÓN que depende de él (\"obtener X: si X supera Y, hacer A; si no, B\").",
        "- Si hubo short ship, el plan decide qué hacer con el faltante —re-emitir, "
        "esperar o cancelar— y con qué criterio.",
        *multi_actor_lines,
        "- La etapa que nombres es exactamente la del diagnóstico.\n",
        "Responde ÚNICAMENTE con el JSON, sin texto adicional, con las llaves EN "
        "ESTE ORDEN:",
        "{",
        '  "razonamiento": "tu análisis del mecanismo: qué observas en los datos, '
        'qué mecanismos son compatibles y cuál pesa más y por qué",',
        '  "hipotesis_principal": {',
        '    "hipotesis": "el mecanismo concreto bajo la etapa diagnosticada",',
        '    "evidencia": "los datos citados que la sostienen",',
        '    "plan": {',
        '      "accion_inmediata": "qué se hace hoy, dirigida a quién y sobre qué",',
        '      "accion_correctiva": "qué corrige la causa en esta PO o este flujo",',
        '      "accion_preventiva": "qué evita que se repita"',
        "    }",
        "  },",
        '  "hipotesis_alternativa": {',
        '    "hipotesis": "el segundo mecanismo compatible con los datos",',
        '    "paso_discriminante": "el dato exacto que separa ambas hipótesis y la '
        'decisión que depende de él"',
        "  },",
        '  "confianza": 0.0 a 1.0 (tu confianza en la hipótesis principal)',
        "}",
    ]
    return "\n".join(prompt_lines)


def is_meta_action(text) -> bool:
    """True si la acción ARRANCA con un verbo meta (lista cerrada de ARD-16).

    Es la MISMA lógica del check `verbo_meta` y de la métrica de la eval (#94):
    prompt, check y métrica comparten la lista para no discrepar. Detecta por stem
    del primer token normalizado (revise/revisa/revisar → revis-) y el compuesto
    dar/hacer seguimiento en los primeros tokens. Texto vacío NO es meta (lo caza
    el check de esquema, no este).
    """
    tokens = _norm_text(text).split()
    if not tokens:
        return False
    if tokens[0].startswith(_META_VERB_STEMS):
        return True
    return tokens[0] in _META_COMPOUND_LEADS and "seguimiento" in tokens[:4]


def _extract_numbers(text) -> set:
    """Cifras del texto como set de floats (coma decimal normalizada a punto)."""
    return {float(m.replace(",", ".")) for m in _NUMBER_RE.findall(str(text))}


def _action_keys_in_order(raw_response: str) -> bool:
    """True si las llaves de nivel superior aparecen en el crudo en el orden del
    contrato. json.loads no falla por orden, así que se verifica sobre el TEXTO."""
    posiciones = [raw_response.find(f'"{k}"') for k in _ACTION_TOP_KEYS]
    return all(p >= 0 for p in posiciones) and posiciones == sorted(posiciones)


def _parse_action_json(raw_response: str) -> Optional[Dict[str, Any]]:
    """Extrae el contrato híbrido de la llamada de acción y lo APLANA a campos planos.

    Estricto a propósito (sin dict de emergencia, a diferencia de _parse_llm_json):
    los fallos los maneja el ciclo de QA (regeneración citando el defecto → qa_flags).
    Las llaves faltantes devuelven "" — las caza el check de esquema, que además
    reporta CUÁLES faltan.

    Returns:
        dict con _ACTION_TEXT_FIELDS + confianza_hipotesis, o None si la respuesta
        no contiene un JSON parseable.
    """
    json_match = re.search(r'\{[\s\S]*\}', raw_response or "")
    if not json_match:
        return None
    try:
        parsed = json.loads(json_match.group())
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, dict):
        return None

    hp = parsed.get("hipotesis_principal")
    hp = hp if isinstance(hp, dict) else {}
    plan = hp.get("plan")
    plan = plan if isinstance(plan, dict) else {}
    ha = parsed.get("hipotesis_alternativa")
    ha = ha if isinstance(ha, dict) else {}
    try:
        confianza = float(parsed.get("confianza", FALLBACK_CONFIDENCE))
    except (TypeError, ValueError):
        confianza = FALLBACK_CONFIDENCE

    def _texto(valor) -> str:
        return str(valor).strip() if valor is not None else ""

    return {
        "razonamiento": _texto(parsed.get("razonamiento")),
        "hipotesis": _texto(hp.get("hipotesis")),
        "hipotesis_evidencia": _texto(hp.get("evidencia")),
        "accion_inmediata": _texto(plan.get("accion_inmediata")),
        "accion_correctiva": _texto(plan.get("accion_correctiva")),
        "accion_preventiva": _texto(plan.get("accion_preventiva")),
        "hipotesis_alt": _texto(ha.get("hipotesis")),
        "paso_discriminante": _texto(ha.get("paso_discriminante")),
        "confianza_hipotesis": confianza,
    }


def run_action_checks(
    parsed: Dict[str, Any],
    raw_response: str,
    row: pd.Series,
    prompt: str,
) -> List[tuple]:
    """Checks por regla post-llamada (ARD-16 Decisión 7 — solo la parte por regla;
    el juez LLM es de otra ola). En código y sin costo.

    Returns:
        Lista de (código, detalle); vacía = pasa. El detalle se cita en la
        regeneración; el código alimenta qa_flags.
    """
    defectos: List[tuple] = []

    # 1. Esquema completo: todos los campos del contrato con contenido.
    faltantes = [c for c in _ACTION_TEXT_FIELDS if not parsed.get(c)]
    if faltantes:
        defectos.append((
            "esquema_incompleto",
            "el JSON no trae (o trae vacíos) estos campos del contrato: "
            + ", ".join(faltantes),
        ))

    # 2. Orden de llaves (verificado sobre el crudo).
    if not _action_keys_in_order(raw_response):
        defectos.append((
            "orden_de_llaves",
            "las llaves de nivel superior no están en el orden requerido: "
            + " → ".join(_ACTION_TOP_KEYS),
        ))

    # 3. Verbo meta como acción principal.
    if parsed.get("accion_inmediata") and is_meta_action(parsed["accion_inmediata"]):
        defectos.append((
            "verbo_meta",
            "la accion_inmediata arranca con un verbo meta (revisar/analizar/"
            f"investigar/monitorear/dar seguimiento): \"{parsed['accion_inmediata']}\". "
            "Sustitúyela por una medida ejecutable con destinatario y objeto concretos.",
        ))

    # 4. Cifras ∈ input (ADR-14 para premisas factuales). confianza_hipotesis se
    #    excluye: es estimación propia del modelo, no una cifra de los datos.
    dadas = _extract_numbers(prompt)
    citadas: set = set()
    for campo in _ACTION_TEXT_FIELDS:
        citadas |= _extract_numbers(parsed.get(campo, ""))
    fuera = sorted(c for c in citadas if c not in dadas)
    if fuera:
        defectos.append((
            "cifra_fuera_de_input",
            "estas cifras de tu salida NO están entre los datos dados (cítalas "
            f"textualmente de los datos o quítalas): {fuera}",
        ))

    # 4b. Evidencia de la hipótesis sin cifra (ARD-16 ola 2): el diferencial exige
    #     anclar cada hipótesis en las cifras que la favorecen sobre la alternativa.
    #     El caso vacío lo caza el check de esquema, no este.
    if parsed.get("hipotesis_evidencia") and not _extract_numbers(
        parsed["hipotesis_evidencia"]
    ):
        defectos.append((
            "evidencia_sin_cifra",
            "la evidencia de la hipótesis no cita ninguna cifra de los datos: "
            "ánclala en las cifras dadas (fill rate, excesos, reprogramación, "
            "percentiles).",
        ))

    # 5. Decisión del faltante si hubo short ship.
    if bool(row.get("is_short_ship", row.get("_short_ship", False))):
        plan_texto = _norm_text(" ".join(
            str(parsed.get(c, "")) for c in
            ("accion_inmediata", "accion_correctiva", "accion_preventiva")
        ))
        if not any(k in plan_texto for k in _SHORT_SHIP_DECISION_KEYS):
            defectos.append((
                "sin_decision_faltante",
                "hubo short ship y el plan no decide el destino del faltante: "
                "incluye re-emitir, esperar o cancelar, con su criterio.",
            ))

    # 6. Etapa nombrada = stage_primary (Indeterminado: declararlo, no adoptar una).
    etapa = str(row.get("stage_primary", ""))
    texto_diag = _norm_text(" ".join(
        (str(parsed.get("razonamiento", "")), str(parsed.get("hipotesis", "")))
    ))
    if etapa == "Indeterminado":
        ok_etapa = any(k in texto_diag for k in (
            "indetermin", "no atribuible", "no se puede atribuir",
            "sin datos", "sin causa dominante", "dato faltante",
        ))
    else:
        ok_etapa = any(
            alias in texto_diag
            for alias in _STAGE_ALIASES.get(etapa, (_norm_text(etapa),))
        )
    if etapa and not ok_etapa:
        defectos.append((
            "etapa_incorrecta",
            f"tu razonamiento/hipótesis no nombra la etapa del diagnóstico ({etapa}); "
            "la etapa ya está decidida y tu mecanismo debe vivir dentro de ella.",
        ))

    # 7. Indeterminado: la HIPÓTESIS misma reconoce la indeterminación (ARD-16 ola 2).
    #    El check 6 acepta la declaración en razonamiento+hipótesis concatenados; el
    #    hueco del baseline es que la hipótesis afirmaba un mecanismo ("congestión de
    #    patio") aunque el razonamiento declarara indeterminado. Aquí se inspecciona
    #    SOLO el campo hipotesis, con la lista compartida _INDET_HYP_KEYS (la misma
    #    que usa la tasa del evaluador, para no discrepar).
    if etapa == "Indeterminado" and parsed.get("hipotesis"):
        if not reconoce_indeterminacion(parsed["hipotesis"]):
            defectos.append((
                "indeterminado_sin_reconocer",
                "la etapa es Indeterminado pero tu hipótesis afirma un mecanismo sin "
                "reconocer la indeterminación: nómbrala, identifica el dato faltante "
                "y formula el mecanismo en condicional.",
            ))

    return defectos


def _regeneration_prompt(
    prompt: str, defectos: List[tuple], intento: int, total: int
) -> str:
    """Prompt de reintento: el original + bloque de REGENERACIÓN citando los defectos
    (ARD-16 Decisión 7: regenerar citando el defecto, no repetir a ciegas)."""
    lineas = [
        prompt,
        "",
        f"REGENERACIÓN (intento {intento} de {total}): tu respuesta anterior falló "
        "estas verificaciones:",
    ]
    lineas += [f"- {detalle}" for _, detalle in defectos]
    lineas.append(
        "Corrige exactamente esos defectos y vuelve a emitir el JSON COMPLETO, con "
        "las llaves en el orden requerido."
    )
    return "\n".join(lineas)


def call_action_with_qa(
    backend,
    prompt: str,
    row: pd.Series,
    max_qa_retries: int = DEFAULT_ACTION_QA_RETRIES,
) -> tuple:
    """Llamada de acción + pase de autocrítica por regla (ARD-16 Decisión 7).

    Ciclo: call_raw → _parse_action_json → run_action_checks. Con defectos, re-llama
    con el prompt original + bloque de regeneración que los cita; máximo
    `max_qa_retries` reintentos (default 2 → 3 llamadas). Si persisten, NO bloquea:
    devuelve la última salida utilizable con sus qa_flags visibles.

    Args:
        backend: backend con call_raw() (los cuatro de este módulo lo exponen).
        prompt: prompt de build_action_prompt.
        row: fila de la PO (los checks leen is_short_ship / stage_primary).
        max_qa_retries: reintentos de regeneración tras la primera llamada.

    Returns:
        (parsed, qa_flags): parsed es el dict aplanado del contrato ({} si nunca
        hubo JSON utilizable); qa_flags la lista de códigos de defecto de la última
        iteración (vacía si pasó limpio).
    """
    total = max_qa_retries + 1
    parsed_final: Dict[str, Any] = {}
    defectos: List[tuple] = []
    prompt_actual = prompt
    for intento in range(1, total + 1):
        raw = backend.call_raw(prompt_actual)
        if raw is None:
            # Red/backend agotado: call_raw ya reintenta HTTP; repetir el ciclo QA
            # no ayuda.
            defectos = [("sin_respuesta", "el backend no devolvió respuesta")]
            break
        parsed = _parse_action_json(raw)
        if parsed is None:
            defectos = [(
                "json_invalido",
                "no se encontró un JSON parseable con el contrato pedido; responde "
                "únicamente con el JSON.",
            )]
        else:
            parsed_final = parsed
            defectos = run_action_checks(parsed, raw, row, prompt)
        if not defectos:
            return parsed_final, []
        if intento < total:
            prompt_actual = _regeneration_prompt(prompt, defectos, intento + 1, total)
    return parsed_final, [codigo for codigo, _ in defectos]


# ============================================================
# Utilidad compartida: parseo de JSON
# ============================================================

def _parse_llm_json(
    raw_response: str,
    fallback: bool = True
) -> Optional[Dict]:
    """
    Extrae y normaliza el JSON de la respuesta de cualquier LLM.

    Centraliza el parseo para evitar duplicación entre backends (DRY).

    Args:
        raw_response: Texto crudo devuelto por el modelo.
        fallback: Si True, devuelve un dict de emergencia cuando no
                  se encuentra JSON válido. Útil para modelos locales
                  que pueden responder en texto libre.

    Returns:
        Diccionario con los campos normalizados, o None si falló y
        fallback=False.
    """
    json_match = re.search(r'\{[\s\S]*\}', raw_response)
    if json_match:
        try:
            parsed = json.loads(json_match.group())
            return {
                "causa_raiz": (
                    parsed.get('causa_raiz')
                    or parsed.get('root_cause')
                    or parsed.get('causa', '')
                ),
                "accion_recomendada": (
                    parsed.get('accion_recomendada')
                    or parsed.get('recommended_action')
                    or parsed.get('accion', '')
                ),
                "severidad": (
                    parsed.get('severidad')
                    or parsed.get('severity')
                    or FALLBACK_SEVERITY
                ).upper(),
                "coincide_con_reason_code": bool(
                    parsed.get('coincide_con_reason_code')
                    or parsed.get('matches_reason', False)
                ),
                "confianza": float(
                    parsed.get('confianza')
                    or parsed.get('confidence', FALLBACK_CONFIDENCE)
                )
            }
        except (json.JSONDecodeError, ValueError):
            pass

    if fallback:
        return {
            "causa_raiz": raw_response[:FALLBACK_RAW_CHARS],
            "accion_recomendada": FALLBACK_ACTION,
            "severidad": FALLBACK_SEVERITY,
            "coincide_con_reason_code": False,
            "confianza": FALLBACK_EMERGENCY_CONFIDENCE
        }

    return None


# ============================================================
# Backend: Qwen (Ollama local)
# ============================================================

class QwenBackend:
    """Backend para Qwen 2.5:7B vía Ollama local."""

    def __init__(
        self,
        model: str = DEFAULT_OLLAMA_MODEL,
        url: str = DEFAULT_OLLAMA_URL,
        temperature: float = DEFAULT_TEMPERATURE,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
        max_retries: int = DEFAULT_MAX_RETRIES,
    ) -> None:
        """
        Inicializa el backend de Qwen.

        Args:
            model: Nombre del modelo en Ollama.
            url: URL de la API de Ollama.
        """
        self.model = model
        self.url = url
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries

    def call_raw(self, prompt: str) -> Optional[str]:
        """
        Llama a Qwen y devuelve el TEXTO crudo de la respuesta (o None si falló).

        La llamada de acción (ARD-16) necesita el crudo para verificar el orden de
        llaves del contrato híbrido; call() lo envuelve con el parseo de la llamada 1.

        Args:
            prompt: Texto a enviar al modelo.

        Returns:
            Texto crudo devuelto por el modelo, o None si agotó los reintentos.
        """
        for attempt in range(self.max_retries):
            try:
                response = requests.post(
                    self.url,
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": self.temperature,
                            "num_predict": self.max_tokens
                        }
                    },
                    timeout=self.timeout_seconds
                )
                response.raise_for_status()

                result = response.json()
                return result.get('response', '')

            except requests.exceptions.HTTPError as e:
                print(f"  Error HTTP {e.response.status_code}, "
                      f"intento {attempt + 1}/{self.max_retries}")
                time.sleep(RETRY_SLEEP_SECONDS)
            except requests.exceptions.RequestException as e:
                print(f"  Error de red: {e}, "
                      f"intento {attempt + 1}/{self.max_retries}")
                time.sleep(RETRY_SLEEP_SECONDS)

        return None

    def call(self, prompt: str) -> Optional[Dict]:
        """
        Llama a Qwen y parsea la respuesta (contrato de la llamada 1).

        Args:
            prompt: Texto a enviar al modelo.

        Returns:
            Diccionario con la respuesta parseada o None si falló.
        """
        raw_response = self.call_raw(prompt)
        if raw_response is None:
            return None
        # fallback=True: Qwen puede responder en texto libre
        return _parse_llm_json(raw_response, fallback=True)


# ============================================================
# Backend: Claude (Anthropic API)
# ============================================================

class ClaudeBackend:
    """Backend para Claude API de Anthropic."""

    def __init__(
        self,
        api_key: str,
        model: str = DEFAULT_CLAUDE_MODEL,
        temperature: float = DEFAULT_TEMPERATURE,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
        max_retries: int = DEFAULT_MAX_RETRIES,
    ) -> None:
        """
        Inicializa el backend de Claude.

        Args:
            api_key: API key de Anthropic.
            model: Modelo de Claude a utilizar.
        """
        self.api_key = api_key
        self.model = model
        self.url = "https://api.anthropic.com/v1/messages"
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries

    def call_raw(self, prompt: str) -> Optional[str]:
        """
        Llama a Claude y devuelve el TEXTO crudo de la respuesta (o None si falló).

        Args:
            prompt: Texto a enviar al modelo.

        Returns:
            Texto crudo devuelto por el modelo, o None si agotó los reintentos.
        """
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        body = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }

        for attempt in range(self.max_retries):
            try:
                response = requests.post(
                    self.url, headers=headers, json=body, timeout=self.timeout_seconds
                )
                response.raise_for_status()

                result = response.json()
                content = result.get('content', [])
                # Guardia explícita contra lista vacía
                return content[0].get('text', '') if content else ''

            except requests.exceptions.HTTPError as e:
                print(f"  Error HTTP {e.response.status_code}: "
                      f"{e.response.text[:100]}, "
                      f"intento {attempt + 1}/{self.max_retries}")
                time.sleep(RETRY_SLEEP_SECONDS)
            except requests.exceptions.RequestException as e:
                print(f"  Error de red: {e}, "
                      f"intento {attempt + 1}/{self.max_retries}")
                time.sleep(RETRY_SLEEP_SECONDS)

        return None

    def call(self, prompt: str) -> Optional[Dict]:
        """
        Llama a Claude y parsea la respuesta (contrato de la llamada 1).

        Args:
            prompt: Texto a enviar al modelo.

        Returns:
            Diccionario con la respuesta parseada o None si falló.
        """
        raw_response = self.call_raw(prompt)
        if raw_response is None:
            return None
        # fallback=False: se espera JSON estricto de Claude
        return _parse_llm_json(raw_response, fallback=False)


# ============================================================
# Backend: DeepSeek (API compatible con OpenAI)
# ============================================================

class DeepSeekBackend:
    """
    Backend para DeepSeek API.

    Usa el formato de mensajes compatible con OpenAI
    (chat/completions), por lo que es fácil de mantener
    junto a otros backends de la misma familia.
    """

    def __init__(
        self,
        api_key: str,
        model: str = DEFAULT_DEEPSEEK_MODEL,
        temperature: float = DEFAULT_TEMPERATURE,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
        max_retries: int = DEFAULT_MAX_RETRIES,
    ) -> None:
        """
        Inicializa el backend de DeepSeek.

        Args:
            api_key: API key de DeepSeek.
            model: Modelo a utilizar ('deepseek-chat' o 'deepseek-reasoner').
        """
        self.api_key = api_key
        self.model = model
        self.url = "https://api.deepseek.com/v1/chat/completions"
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries

    def call_raw(self, prompt: str) -> Optional[str]:
        """
        Llama a DeepSeek y devuelve el TEXTO crudo de la respuesta (o None si falló).

        Args:
            prompt: Texto a enviar al modelo.

        Returns:
            Texto crudo devuelto por el modelo, o None si agotó los reintentos.
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        body = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }

        for attempt in range(self.max_retries):
            try:
                response = requests.post(
                    self.url, headers=headers, json=body, timeout=self.timeout_seconds
                )
                response.raise_for_status()

                result = response.json()
                choices = result.get('choices', [])
                # Guardia explícita contra lista vacía
                return (
                    choices[0].get('message', {}).get('content', '')
                    if choices else ''
                )

            except requests.exceptions.HTTPError as e:
                print(f"  Error HTTP {e.response.status_code}: "
                      f"{e.response.text[:100]}, "
                      f"intento {attempt + 1}/{self.max_retries}")
                time.sleep(RETRY_SLEEP_SECONDS)
            except requests.exceptions.RequestException as e:
                print(f"  Error de red: {e}, "
                      f"intento {attempt + 1}/{self.max_retries}")
                time.sleep(RETRY_SLEEP_SECONDS)

        return None

    def call(self, prompt: str) -> Optional[Dict]:
        """
        Llama a DeepSeek y parsea la respuesta (contrato de la llamada 1).

        Args:
            prompt: Texto a enviar al modelo.

        Returns:
            Diccionario con la respuesta parseada o None si falló.
        """
        raw_response = self.call_raw(prompt)
        if raw_response is None:
            return None
        # fallback=False: se espera JSON estricto de DeepSeek
        return _parse_llm_json(raw_response, fallback=False)


# ============================================================
# Backend: OpenAI (Chat Completions API)
# ============================================================

class OpenAIBackend:
    """Backend para OpenAI API (ChatGPT, GPT-4, etc)."""

    def __init__(
        self,
        api_key: str,
        model: str = DEFAULT_OPENAI_MODEL,
        temperature: float = DEFAULT_TEMPERATURE,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
        max_retries: int = DEFAULT_MAX_RETRIES,
    ) -> None:
        """
        Inicializa el backend de OpenAI.

        Args:
            api_key: API key de OpenAI.
            model: Modelo a utilizar ('gpt-4o-mini', 'gpt-4', 'gpt-4-turbo', etc).
        """
        self.api_key = api_key
        self.model = model
        self.url = "https://api.openai.com/v1/chat/completions"
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries

    def call_raw(self, prompt: str) -> Optional[str]:
        """
        Llama a OpenAI y devuelve el TEXTO crudo de la respuesta (o None si falló).

        Args:
            prompt: Texto a enviar al modelo.

        Returns:
            Texto crudo devuelto por el modelo, o None si agotó los reintentos.
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        body = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }

        for attempt in range(self.max_retries):
            try:
                response = requests.post(
                    self.url, headers=headers, json=body, timeout=self.timeout_seconds
                )
                response.raise_for_status()

                result = response.json()
                choices = result.get('choices', [])
                # Guardia explícita contra lista vacía
                return (
                    choices[0].get('message', {}).get('content', '')
                    if choices else ''
                )

            except requests.exceptions.HTTPError as e:
                print(f"  Error HTTP {e.response.status_code}: "
                      f"{e.response.text[:100]}, "
                      f"intento {attempt + 1}/{self.max_retries}")
                time.sleep(RETRY_SLEEP_SECONDS)
            except requests.exceptions.RequestException as e:
                print(f"  Error de red: {e}, "
                      f"intento {attempt + 1}/{self.max_retries}")
                time.sleep(RETRY_SLEEP_SECONDS)

        return None

    def call(self, prompt: str) -> Optional[Dict]:
        """
        Llama a OpenAI y parsea la respuesta (contrato de la llamada 1).

        Args:
            prompt: Texto a enviar al modelo.

        Returns:
            Diccionario con la respuesta parseada o None si falló.
        """
        raw_response = self.call_raw(prompt)
        if raw_response is None:
            return None
        # fallback=False: se espera JSON estricto de OpenAI
        return _parse_llm_json(raw_response, fallback=False)


# ============================================================
# Factory
# ============================================================

def create_backend(
    backend_type: str,
    ollama_model: Optional[str] = None,
    ollama_url: str = DEFAULT_OLLAMA_URL,
    claude_model: Optional[str] = None,
    claude_api_key: Optional[str] = None,
    deepseek_model: Optional[str] = None,
    deepseek_api_key: Optional[str] = None,
    openai_model: Optional[str] = None,
    openai_api_key: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
) -> Union[QwenBackend, ClaudeBackend, DeepSeekBackend, OpenAIBackend]:
    """
    Crea el backend apropiado según la configuración.

    Inferencia (temperatura, max_tokens, timeout, reintentos, modelo por backend)
    se lee de llm_config.json vía load_llm_config(): es config reproducible, no
    literales en el código. El modelo se resuelve con prioridad: argumento explícito
    (p. ej. --claude-model) por encima del de llm_config.json.

    La API key se resuelve en este orden de prioridad:
        1. Argumento explícito (--api-key en CLI)
        2. Variable de entorno (ANTHROPIC_API_KEY / DEEPSEEK_API_KEY / OPENAI_API_KEY)

    Args:
        backend_type: 'local', 'claude', 'deepseek' u 'openai'.
        ollama_model/claude_model/deepseek_model/openai_model: override del modelo;
            None usa el de llm_config.json["models"].
        ollama_url: URL de Ollama (endpoint operativo, no en el JSON de inferencia).
        claude_api_key/deepseek_api_key/openai_api_key: API key (opcional si está en .env).
        temperature: override de temperatura para esta corrida; None usa llm_config.json.
        max_tokens: override de tokens de salida; None usa llm_config.json. Lo usa la
            llamada de acción (ARD-16): su contrato híbrido no cabe en los 512 default.

    Returns:
        Instancia del backend configurado.

    Raises:
        ValueError: Si el backend requiere API key y no se encuentra.
    """
    cfg = load_llm_config()
    inference = {
        "temperature": temperature if temperature is not None else cfg["temperature"],
        "max_tokens": max_tokens if max_tokens is not None else cfg["max_tokens"],
        "timeout_seconds": cfg["timeout_seconds"],
        "max_retries": cfg["max_retries"],
    }
    models = cfg["models"]

    if backend_type == "claude":
        api_key = claude_api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError(
                "❌ Se requiere API key de Claude. "
                "Pásala con --api-key o define ANTHROPIC_API_KEY en .env"
            )
        model = claude_model or models["claude"]
        print(f"🔑 Usando Claude API (modelo: {model})")
        return ClaudeBackend(api_key, model, **inference)

    if backend_type == "deepseek":
        api_key = deepseek_api_key or os.environ.get("DEEPSEEK_API_KEY")
        if not api_key:
            raise ValueError(
                "❌ Se requiere API key de DeepSeek. "
                "Pásala con --api-key o define DEEPSEEK_API_KEY en .env"
            )
        model = deepseek_model or models["deepseek"]
        print(f"🔑 Usando DeepSeek API (modelo: {model})")
        return DeepSeekBackend(api_key, model, **inference)

    if backend_type == "openai":
        api_key = openai_api_key or os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "❌ Se requiere API key de OpenAI. "
                "Pásala con --api-key o define OPENAI_API_KEY en .env"
            )
        model = openai_model or models["openai"]
        print(f"🔑 Usando OpenAI API (modelo: {model})")
        return OpenAIBackend(api_key, model, **inference)

    # Default: backend local con Qwen/Ollama
    model = ollama_model or models["local"]
    print(f"🖥️ Usando Qwen local (modelo: {model})")
    return QwenBackend(model, ollama_url, **inference)


# ============================================================
# Función principal de procesamiento
# ============================================================

# Columna del DataFrame → campo aplanado del contrato de la llamada de acción.
_ACTION_COLUMN_MAP = {
    "llm_razonamiento": "razonamiento",
    "llm_hipotesis": "hipotesis",
    "llm_hipotesis_evidencia": "hipotesis_evidencia",
    "llm_accion_inmediata": "accion_inmediata",
    "llm_accion_correctiva": "accion_correctiva",
    "llm_accion_preventiva": "accion_preventiva",
    "llm_hipotesis_alt": "hipotesis_alt",
    "llm_paso_discriminante": "paso_discriminante",
}


def add_llm_explanations(
    df: pd.DataFrame,
    backend: Union[QwenBackend, ClaudeBackend, DeepSeekBackend, OpenAIBackend],
    delay_between_calls: float = DEFAULT_DELAY_SECONDS,
    test_mode: bool = False,
    test_limit: int = 10,
    save_every: int = DEFAULT_SAVE_EVERY,
    output_path: Optional[str] = None,
    kb: Optional[dict] = None,
    action_call: bool = False,
    action_backend=None,
) -> pd.DataFrame:
    """
    Añade columnas con explicaciones del LLM al DataFrame clasificado.

    Args:
        df: DataFrame con los POs ya clasificados.
        backend: Backend de LLM a utilizar.
        delay_between_calls: Segundos entre llamadas a la API.
        test_mode: Si es True, procesa solo test_limit POs.
        test_limit: Número de POs a procesar en modo test.
        save_every: Guardar resultados cada N POs.
        output_path: Ruta para guardar resultados parciales.
        kb: dict opcional de la base de conocimiento de dominio (#151), tal cual lo
            devuelve `load_domain_kb`. Se pasa sin modificar a `build_prompt`. None
            (default) → sin bloque de contexto de dominio, comportamiento sin cambios.
        action_call: activa la llamada de acción (ARD-16 ola 1): segunda llamada por
            PO con el contrato híbrido + checks por regla. False (default) → una sola
            llamada, columnas y comportamiento históricos sin cambios. OJO: duplica
            las llamadas al backend (2 por PO, más reintentos de QA).
        action_backend: backend para la llamada de acción (típicamente el mismo
            proveedor con max_tokens_action). None → se reusa `backend`.

    Returns:
        DataFrame con columnas adicionales de análisis LLM.
    """
    df_result = df.copy()

    # Inicializar columnas
    for col in ('llm_causa_raiz', 'llm_accion_recomendada', 'llm_severidad'):
        if col not in df_result.columns:
            df_result[col] = ''

    if 'llm_coincide_con_reason' not in df_result.columns:
        df_result['llm_coincide_con_reason'] = False

    if 'llm_confianza' not in df_result.columns:
        df_result['llm_confianza'] = 0.0

    # Llamada de acción (ARD-16): columnas propias + estadísticos globales, SOLO en
    # modo opt-in — con action_call=False el DataFrame de salida no cambia.
    if action_call:
        for col in _ACTION_COLUMN_MAP:
            if col not in df_result.columns:
                df_result[col] = ''
        if 'llm_confianza_hipotesis' not in df_result.columns:
            df_result['llm_confianza_hipotesis'] = 0.0
        if 'llm_qa_flags' not in df_result.columns:
            df_result['llm_qa_flags'] = ''
        action_stats = compute_dataset_stats(df_result)
        action_be = action_backend or backend

    # Filtrar POs con retraso
    delayed_mask = df_result['delay_days_calc'] > 0
    delayed_indices = df_result[delayed_mask].index.tolist()
    total_delayed = len(delayed_indices)

    if test_mode:
        delayed_indices = delayed_indices[:test_limit]
        print(f"🔧 Modo test: procesando {len(delayed_indices)} POs "
              f"(de {total_delayed} totales)")
    else:
        print(f"🚀 Modo producción: procesando {len(delayed_indices)} POs")

    pbar = tqdm(delayed_indices, desc="Procesando POs", unit="po")

    for i, idx in enumerate(pbar):
        row = df_result.loc[idx]
        po_nbr = row.get('PO_NBR', 'N/A')
        pbar.set_description(f"PO {po_nbr}")

        prompt = build_prompt(row, kb=kb)
        response = backend.call(prompt)

        if response:
            df_result.at[idx, 'llm_causa_raiz'] = response.get('causa_raiz', '')
            df_result.at[idx, 'llm_accion_recomendada'] = response.get(
                'accion_recomendada', ''
            )
            df_result.at[idx, 'llm_severidad'] = response.get('severidad', 'MEDIUM')
            df_result.at[idx, 'llm_coincide_con_reason'] = response.get(
                'coincide_con_reason_code', False
            )
            df_result.at[idx, 'llm_confianza'] = response.get('confianza', 0.5)
            pbar.set_postfix({"status": "OK"})
        else:
            pbar.set_postfix({"status": "FALLÓ"})

        # Llamada de acción (ARD-16 ola 1): planifica SOBRE el diagnóstico de la
        # llamada 1. Política ante fallback de la primera (pendiente del ARD que la
        # ola 1 resuelve operativamente): sin diagnóstico no hay insumo para el plan
        # → no se llama y se marca el qa_flag.
        if action_call:
            if response:
                action_prompt = build_action_prompt(row, response, action_stats)
                parsed_action, qa_flags = call_action_with_qa(
                    action_be, action_prompt, row
                )
                for col, campo in _ACTION_COLUMN_MAP.items():
                    df_result.at[idx, col] = parsed_action.get(campo, '')
                df_result.at[idx, 'llm_confianza_hipotesis'] = parsed_action.get(
                    'confianza_hipotesis', 0.0
                )
                df_result.at[idx, 'llm_qa_flags'] = ";".join(qa_flags)
            else:
                df_result.at[idx, 'llm_qa_flags'] = 'sin_diagnostico_llamada1'

        # Guardado automático cada N POs
        if output_path and (i + 1) % save_every == 0:
            df_result.to_csv(output_path, index=False)
            print(f"\n  💾 Guardado parcial en: {output_path}")

        # Pausa entre llamadas (excepto en la última iteración)
        if i < len(delayed_indices) - 1:
            time.sleep(delay_between_calls)

    pbar.close()

    completados = df_result['llm_causa_raiz'].str.len().gt(0).sum()
    print(f"\n✅ Procesamiento completado. {completados} POs con explicación")
    return df_result


# ============================================================
# Orquestación del pipeline (handoff F2 → F3)
# ============================================================

def _ensure_pipeline_on_path() -> None:
    """
    Inserta los directorios de Fase 1 y 2 en sys.path para importar sus *_core.

    Se hace en runtime (no al top-level) porque las rutas dependen de __file__,
    que solo existe en tiempo de ejecución.
    """
    repo_root = Path(__file__).resolve().parent.parent
    for sub in ("01_data_pipeline_and_eda", "02_clasif_reglas_negocio"):
        sub_path = str(repo_root / sub)
        if sub_path not in sys.path:
            sys.path.insert(0, sub_path)


def prepare_classified_df(
    from_csv: bool = False,
    repo_root: Optional[Path] = None,
) -> pd.DataFrame:
    """
    Prepara el DataFrame clasificado que consume la integración LLM (handoff F2→F3).

    Por DEFAULT recomputa la cadena completa (clean -> classify) — nunca se sirven
    datos rancios por defecto. La lectura del handoff de F2 (df_classified.csv) es
    OPT-IN: si `from_csv` es True y el CSV existe, se lee reparseando las fechas
    para que sea funcionalmente idéntico a lo que la cadena dejaría en memoria.

    Args:
        from_csv: Si True, intenta leer data/processed/df_classified.csv en vez de
                  recomputar. Si el CSV no existe, recae en recomputar.
        repo_root: Raíz del repo (para resolver rutas de data/). Por defecto se
                   deduce de __file__; se inyecta en tests para no tocar data/ real.

    Returns:
        DataFrame con los POs ya clasificados (salida de classify_po_stages).

    Raises:
        FileNotFoundError: Si hay que recomputar y el CSV crudo no existe.
    """
    _ensure_pipeline_on_path()
    from pipeline_core import clean_po_data, _DATE_INPUT_COLUMNS  # noqa: E402
    from classifier_core import classify_po_stages  # noqa: E402

    if repo_root is None:
        repo_root = Path(__file__).resolve().parent.parent
    classified_csv = repo_root / "data" / "processed" / "df_classified.csv"

    if from_csv and classified_csv.exists():
        df_classified = pd.read_csv(
            classified_csv, low_memory=False, parse_dates=list(_DATE_INPUT_COLUMNS)
        )
        print(f"📂 Handoff F2 leído desde CSV (opt-in): {classified_csv}")
        return df_classified

    if from_csv:
        print(f"⚠️ --from-csv pedido pero no existe {classified_csv}; se recomputa.")

    csv_path = repo_root / "data" / "raw" / "po_root_cause_synthetic.csv"
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV crudo no encontrado en {csv_path}")

    print(f"📂 Cargando CSV: {csv_path}")
    df_raw = pd.read_csv(csv_path, low_memory=False)

    print("🔧 Ejecutando pipeline de limpieza...")
    df_clean = clean_po_data(df_raw)

    print("🔧 Ejecutando clasificador por etapa...")
    return classify_po_stages(df_clean)


def save_llm_output(df: pd.DataFrame, output_path: Union[str, Path]) -> None:
    """
    Persiste el DataFrame con las columnas LLM a CSV (artefacto interno de F3).

    Es el guardado del DataFrame completo `df_with_llm_*.csv`. El CSV-entregable
    de las cinco columnas del mentor (PO_NBR, stage, severity, explanation, action)
    lo produce `export_deliverable_csv` (#97).

    Args:
        df: DataFrame con las columnas llm_* ya añadidas.
        output_path: Ruta destino del CSV.
    """
    df.to_csv(output_path, index=False)
    print(f"\n💾 Resultado guardado en: {output_path}")


# Las cinco columnas canónicas del mentor (kickoff §09 / README §9), en orden.
# Son el contrato exacto del entregable y van SIEMPRE primero en el artefacto.
_MENTOR_COLUMNS = ["PO_NBR", "stage", "severity", "explanation", "action"]

# Columnas de soporte para la app de Fase 4 (contrato F3→F4, #100): el timeline del
# PO, los agravantes y la concordancia con la anotación humana. Permiten que la app
# LEA el artefacto sin recomputar el pipeline ni llamar al LLM. Mapeo (origen → nombre
# en el artefacto): se conserva el nombre de origen salvo donde el contrato canoniza.
_TIMELINE_COLUMNS = [
    "PO_DT", "STA_DT", "APPROVED_DT", "TRAILER_ARRIVE_DT",
    "CHECKIN_DT", "CHECKOUT_DT", "RECPT_DT",
]
_AGGRAVANT_COLUMNS = ["HOT_PO_FLAG", "is_short_ship"]
_AGREEMENT_COLUMNS = ["REASON_DSC", "llm_coincide_con_reason"]

# Orden final del artefacto: las 5 del mentor primero, luego el bloque de soporte.
_DELIVERABLE_COLUMNS = (
    _MENTOR_COLUMNS + _TIMELINE_COLUMNS + _AGGRAVANT_COLUMNS + _AGREEMENT_COLUMNS
)


def export_deliverable_csv(
    df: pd.DataFrame,
    output_path: Union[str, Path],
) -> pd.DataFrame:
    """
    Escribe el CSV-entregable (`po_output.csv`), artefacto del contrato F3→F4 (#100).

    Estructura (las 5 del mentor primero, en orden; luego soporte de la app):
      1. Contrato del mentor (kickoff §09 / README §9): PO_NBR, stage, severity,
         explanation, action.
      2. Soporte de Fase 4 para que la app NO recompute: el timeline del PO, los
         agravantes (hot PO, short ship) y la concordancia con REASON_DSC.

    Alcance de filas: solo los POs tardíos (`delay_days_calc > 0`) — los que el LLM
    explica y los que la app ofrece en el selector (#102).

    Mapeo de las 5 del mentor (materializa ADR-10, severidad híbrida):
        stage       <- stage_primary
        severity    <- llm_severidad   (la OFICIAL es la del LLM; la determinística
                                        de F2 queda como auditoría, fuera de este CSV)
        explanation <- llm_causa_raiz
        action      <- llm_accion_recomendada
    Las columnas de soporte conservan su nombre de origen.

    Args:
        df: DataFrame con la clasificación de F2 y las columnas llm_* de F3.
        output_path: Ruta destino del CSV-entregable (p. ej. po_output.csv).

    Returns:
        El DataFrame entregable (solo tardíos) que se persistió, con las columnas
        en el orden de `_DELIVERABLE_COLUMNS`.
    """
    tardios = df[df["delay_days_calc"] > 0]

    datos = {
        # 1. Contrato del mentor.
        "PO_NBR":      tardios["PO_NBR"].values,
        "stage":       tardios["stage_primary"].values,
        "severity":    tardios["llm_severidad"].values,
        "explanation": tardios["llm_causa_raiz"].values,
        "action":      tardios["llm_accion_recomendada"].values,
    }
    # 2. Soporte de la app: timeline + agravantes + concordancia (nombre de origen).
    for col in _TIMELINE_COLUMNS + _AGGRAVANT_COLUMNS + _AGREEMENT_COLUMNS:
        datos[col] = tardios[col].values

    out = pd.DataFrame(datos, columns=_DELIVERABLE_COLUMNS)
    out.to_csv(output_path, index=False)
    print(f"📦 CSV-entregable guardado en: {output_path} ({len(out)} POs tardíos)")
    return out


# ============================================================
# Script principal
# ============================================================

def main() -> None:
    """Punto de entrada principal."""
    parser = argparse.ArgumentParser(
        description="Genera explicaciones con LLM para POs retrasados"
    )
    parser.add_argument(
        "--mode", type=str, default="test",
        choices=["test", "full", "custom"],
        help="Modo: test (10 POs), full (todos), custom"
    )
    parser.add_argument(
        "--limit", type=int, default=50,
        help="Límite de POs en modo custom"
    )
    parser.add_argument(
        "--backend", type=str, default="local",
        choices=["local", "claude", "deepseek", "openai"],
        help="Backend: local (Qwen/Ollama), claude, deepseek u openai"
    )
    parser.add_argument(
        "--ollama-model", type=str, default=None,
        help="Modelo de Ollama (override; default desde llm_config.json)"
    )
    parser.add_argument(
        "--ollama-url", type=str, default=DEFAULT_OLLAMA_URL,
        help="URL de la API de Ollama"
    )
    parser.add_argument(
        "--claude-model", type=str, default=None,
        help="Modelo de Claude (override; default desde llm_config.json)"
    )
    parser.add_argument(
        "--deepseek-model", type=str, default=None,
        help="Modelo de DeepSeek (override; default desde llm_config.json)"
    )
    parser.add_argument(
        "--openai-model", type=str, default=None,
        help="Modelo de OpenAI (override; default desde llm_config.json)"
    )
    parser.add_argument(
        "--api-key", type=str, default=None,
        help=(
            "API key del backend seleccionado. "
            "Alternativa: ANTHROPIC_API_KEY, DEEPSEEK_API_KEY u OPENAI_API_KEY en .env"
        )
    )
    parser.add_argument(
        "--from-csv", action="store_true",
        help=(
            "Leer el handoff de Fase 2 desde data/processed/df_classified.csv en vez de "
            "recomputar la cadena clean->classify. Opt-in (contrato dual); por default se "
            "recomputa. Tambien activable con la env var PO_USE_PREV_CSV."
        )
    )
    parser.add_argument(
        "--action-call", action="store_true",
        help=(
            "Activa la llamada de acción (ARD-16 ola 1): segunda llamada por PO con "
            "contrato híbrido (hipótesis + plan) y checks por regla. Default: apagado "
            "(solo la llamada 1, comportamiento histórico). DUPLICA las llamadas al "
            "backend (2 por PO, más reintentos de QA)."
        )
    )
    args = parser.parse_args()

    print("=" * 60)
    print("Fase 3 — Integración con LLM (Producción)")
    print("=" * 60)

    # Origen de los datos clasificados: por DEFAULT se recomputa la cadena completa
    # (clean -> classify) — nunca se sirven datos rancios por defecto (H3). La lectura
    # del handoff de F2 es OPT-IN: --from-csv o env PO_USE_PREV_CSV.
    from_csv = args.from_csv or bool(os.environ.get("PO_USE_PREV_CSV"))
    try:
        df_classified = prepare_classified_df(from_csv=from_csv)
    except FileNotFoundError as e:
        print(f"❌ {e}")
        sys.exit(1)

    repo_root = Path(__file__).resolve().parent.parent

    # Resolver API key según el backend elegido
    claude_api_key = args.api_key if args.backend == "claude" else None
    deepseek_api_key = args.api_key if args.backend == "deepseek" else None
    openai_api_key = args.api_key if args.backend == "openai" else None

    try:
        backend = create_backend(
            backend_type=args.backend,
            ollama_model=args.ollama_model,
            ollama_url=args.ollama_url,
            claude_model=args.claude_model,
            claude_api_key=claude_api_key,
            deepseek_model=args.deepseek_model,
            deepseek_api_key=deepseek_api_key,
            openai_model=args.openai_model,
            openai_api_key=openai_api_key
        )
    except ValueError as e:
        print(e)
        sys.exit(1)

    # Backend de la llamada de acción (ARD-16): mismo proveedor, max_tokens_action
    # (el contrato híbrido no cabe en los 512 default de la llamada 1).
    action_backend = None
    if args.action_call:
        cfg = load_llm_config()
        action_backend = create_backend(
            backend_type=args.backend,
            ollama_model=args.ollama_model,
            ollama_url=args.ollama_url,
            claude_model=args.claude_model,
            claude_api_key=claude_api_key,
            deepseek_model=args.deepseek_model,
            deepseek_api_key=deepseek_api_key,
            openai_model=args.openai_model,
            openai_api_key=openai_api_key,
            max_tokens=cfg.get("max_tokens_action", DEFAULT_MAX_TOKENS_ACTION),
        )

    # Configurar modo
    if args.mode == "test":
        test_mode = True
        test_limit = 10
        output_filename = f"df_with_llm_test_{args.backend}.csv"
    elif args.mode == "full":
        test_mode = False
        test_limit = 0
        output_filename = f"df_with_llm_full_{args.backend}.csv"
    else:  # custom
        test_mode = True
        test_limit = args.limit
        output_filename = f"df_with_llm_{args.limit}_{args.backend}.csv"

    output_path = repo_root / "data" / "processed" / output_filename

    print("🤖 Ejecutando análisis con LLM...")
    df_with_llm = add_llm_explanations(
        df_classified,
        backend=backend,
        test_mode=test_mode,
        test_limit=test_limit,
        output_path=str(output_path),
        action_call=args.action_call,
        action_backend=action_backend,
    )

    # Guardar resultado final (artefacto interno df_with_llm_*.csv)
    save_llm_output(df_with_llm, output_path)

    # Guardar el CSV-entregable del mentor (5 columnas, solo tardíos) — el artefacto
    # que consume Fase 4 (contrato F3→F4, #100).
    deliverable_path = repo_root / "data" / "processed" / "po_output.csv"
    export_deliverable_csv(df_with_llm, deliverable_path)

    # Estadísticas finales
    total_delayed = (df_with_llm['delay_days_calc'] > 0).sum()
    with_llm = df_with_llm['llm_causa_raiz'].str.len().gt(0).sum()

    print("\n📊 Estadísticas finales:")
    print(f"   Total POs:             {len(df_with_llm)}")
    print(f"   POs retrasados:        {total_delayed}")
    print(f"   POs con análisis LLM:  {with_llm}")


if __name__ == "__main__":
    main()