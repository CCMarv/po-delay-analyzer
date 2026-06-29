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
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import pandas as pd
import requests
from dotenv import load_dotenv
from tqdm import tqdm

# ============================================================
# Constantes (PEP 8: mayúsculas con guión bajo)
# ============================================================

DEFAULT_OLLAMA_URL = "http://localhost:11434/api/generate"
DEFAULT_OLLAMA_MODEL = "qwen2.5:7b"
DEFAULT_CLAUDE_MODEL = "claude-sonnet-4-6"
DEFAULT_DEEPSEEK_MODEL = "deepseek-chat"   # alternativa: "deepseek-reasoner"
DEFAULT_OPENAI_MODEL = "gpt-4o-mini"       # alternativa: "gpt-4", "gpt-4-turbo"
DEFAULT_TEMPERATURE = 0.3
DEFAULT_MAX_TOKENS = 512
DEFAULT_DELAY_SECONDS = 0.5
DEFAULT_SAVE_EVERY = 50
RETRY_SLEEP_SECONDS = 2

# Cargar variables de entorno
load_dotenv()


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
    if ex.get("stage_primary") == "INDETERMINADO" and ex.get("indeterminado_substage"):
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

    El encabezado dirige la atención del modelo a lo que los ejemplos enseñan: que la
    etapa sale de la señal temporal (no del REASON_DSC) y que la acción ataca la causa
    medida sin pedir investigar lo que el reason ya explica. Devuelve "" en zero-shot, de
    modo que al unir con el resto del prompt no altera el comportamiento histórico.
    """
    if not examples:
        return ""
    partes = [
        "EJEMPLOS DE RAZONAMIENTO:",
        "Estudia estos casos resueltos. Observa cómo la etapa se decide por la señal "
        "temporal medida (no por el REASON_DSC del DC, que puede equivocarse) y cómo la "
        "acción ataca la causa real sin pedir investigar lo que el motivo ya explica.\n",
    ]
    partes.extend(_format_example(ex) + "\n" for ex in examples)
    return "\n".join(partes)


def build_prompt(row: pd.Series, examples: Optional[List[Dict[str, Any]]] = None) -> str:
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

    Args:
        row: Una fila del DataFrame con los datos de una PO. Campos leídos vía
            row.get(..., default), por lo que una fila incompleta no rompe (los
            faltantes caen a 'N/A'/0).
        examples: lista opcional de ejemplos resueltos (few-shot). Cada uno es un dict
            con los campos curados de entrada y la salida ideal (ver `_format_example`).
            None o lista vacía → zero-shot.

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
    if row.get("stage_primary") == "INDETERMINADO":
        substage = row.get("indeterminado_substage", "")
        if substage:
            context_lines.append(f"- Sub-categoría INDETERMINADO: {substage}")
    context_lines.append(
        f"- Código de motivo registrado por el DC: {row.get('REASON_DSC', 'No registrado')}"
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
        "MÉTRICAS CALCULADAS:",
        f"- Días de retraso: {row.get('delay_days_calc', 0):.2f} días",
        f"- Espera en patio (yard): {row.get('yard_wait_calc_hrs', 0):.1f} horas",
        f"- Tiempo de descarga (dock): {row.get('dock_calc_hrs', 0):.1f} horas",
        f"- Exceso del transportista: {row.get('excess_carrier_hrs', 0):.1f} horas",
        f"- Exceso del centro de distribución: {row.get('excess_dc_hrs', 0):.1f} horas\n",
        "CLASIFICACIÓN AUTOMÁTICA:",
        f"- Etapa primaria del retraso: {row.get('stage_primary', 'Desconocido')}",
        f"- Causas múltiples: {row.get('stage_multi', 'Ninguna')}\n",
        "\n".join(context_lines) + "\n",
        _examples_block(examples),
        "INSTRUCCIONES:",
        "Tu trabajo es INTERPRETAR los datos dados, NO calcular. Usa ÚNICAMENTE las "
        "cifras de las secciones MÉTRICAS CALCULADAS y TIMELINE. No estimes, no "
        "recalcules fechas ni horas, no inventes números. Toda cifra que menciones en "
        "tu explicación debe ser una de las dadas arriba, citada textualmente "
        "(p. ej. \"un retraso de 4.2 días\").\n",
        "Genera un análisis en formato JSON. "
        "Responde ÚNICAMENTE con el JSON, sin texto adicional.\n",
        "Formato requerido:",
        "{",
        '  "causa_raiz": "2-3 oraciones que: (a) nombren la etapa exacta del retraso '
        '(Vendor, Carrier o DC); (b) citen el retraso cuantificado tomado de los datos '
        'dados; (c) digan si la evidencia coincide o no con el REASON_DSC del DC; '
        '(d) mencionen agravantes si los hay (hot PO, short ship)",',
        '  "accion_recomendada": "Acción concreta y operable, nombrando al responsable '
        '(vendor, carrier o equipo del DC). Evita recomendaciones genéricas",',
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
                    or 'MEDIUM'
                ).upper(),
                "coincide_con_reason_code": bool(
                    parsed.get('coincide_con_reason_code')
                    or parsed.get('matches_reason', False)
                ),
                "confianza": float(
                    parsed.get('confianza')
                    or parsed.get('confidence', 0.5)
                )
            }
        except (json.JSONDecodeError, ValueError):
            pass

    if fallback:
        return {
            "causa_raiz": raw_response[:200],
            "accion_recomendada": "Revisar manualmente con el equipo",
            "severidad": "MEDIUM",
            "coincide_con_reason_code": False,
            "confianza": 0.3
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
        url: str = DEFAULT_OLLAMA_URL
    ) -> None:
        """
        Inicializa el backend de Qwen.

        Args:
            model: Nombre del modelo en Ollama.
            url: URL de la API de Ollama.
        """
        self.model = model
        self.url = url

    def call(self, prompt: str, max_retries: int = 3) -> Optional[Dict]:
        """
        Llama a Qwen y parsea la respuesta.

        Args:
            prompt: Texto a enviar al modelo.
            max_retries: Número máximo de reintentos.

        Returns:
            Diccionario con la respuesta parseada o None si falló.
        """
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    self.url,
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": DEFAULT_TEMPERATURE,
                            "num_predict": DEFAULT_MAX_TOKENS
                        }
                    },
                    timeout=60
                )
                response.raise_for_status()

                result = response.json()
                raw_response = result.get('response', '')
                # fallback=True: Qwen puede responder en texto libre
                return _parse_llm_json(raw_response, fallback=True)

            except requests.exceptions.HTTPError as e:
                print(f"  Error HTTP {e.response.status_code}, "
                      f"intento {attempt + 1}/{max_retries}")
                time.sleep(RETRY_SLEEP_SECONDS)
            except requests.exceptions.RequestException as e:
                print(f"  Error de red: {e}, "
                      f"intento {attempt + 1}/{max_retries}")
                time.sleep(RETRY_SLEEP_SECONDS)

        return None


# ============================================================
# Backend: Claude (Anthropic API)
# ============================================================

class ClaudeBackend:
    """Backend para Claude API de Anthropic."""

    def __init__(
        self,
        api_key: str,
        model: str = DEFAULT_CLAUDE_MODEL
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

    def call(self, prompt: str, max_retries: int = 3) -> Optional[Dict]:
        """
        Llama a Claude y parsea la respuesta.

        Args:
            prompt: Texto a enviar al modelo.
            max_retries: Número máximo de reintentos.

        Returns:
            Diccionario con la respuesta parseada o None si falló.
        """
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        body = {
            "model": self.model,
            "max_tokens": DEFAULT_MAX_TOKENS,
            "temperature": DEFAULT_TEMPERATURE,
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }

        for attempt in range(max_retries):
            try:
                response = requests.post(
                    self.url, headers=headers, json=body, timeout=60
                )
                response.raise_for_status()

                result = response.json()
                content = result.get('content', [])
                # Guardia explícita contra lista vacía
                raw_response = content[0].get('text', '') if content else ''
                # fallback=False: se espera JSON estricto de Claude
                return _parse_llm_json(raw_response, fallback=False)

            except requests.exceptions.HTTPError as e:
                print(f"  Error HTTP {e.response.status_code}: "
                      f"{e.response.text[:100]}, "
                      f"intento {attempt + 1}/{max_retries}")
                time.sleep(RETRY_SLEEP_SECONDS)
            except requests.exceptions.RequestException as e:
                print(f"  Error de red: {e}, "
                      f"intento {attempt + 1}/{max_retries}")
                time.sleep(RETRY_SLEEP_SECONDS)

        return None


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
        model: str = DEFAULT_DEEPSEEK_MODEL
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

    def call(self, prompt: str, max_retries: int = 3) -> Optional[Dict]:
        """
        Llama a DeepSeek y parsea la respuesta.

        Args:
            prompt: Texto a enviar al modelo.
            max_retries: Número máximo de reintentos.

        Returns:
            Diccionario con la respuesta parseada o None si falló.
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        body = {
            "model": self.model,
            "max_tokens": DEFAULT_MAX_TOKENS,
            "temperature": DEFAULT_TEMPERATURE,
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }

        for attempt in range(max_retries):
            try:
                response = requests.post(
                    self.url, headers=headers, json=body, timeout=60
                )
                response.raise_for_status()

                result = response.json()
                choices = result.get('choices', [])
                # Guardia explícita contra lista vacía
                raw_response = (
                    choices[0].get('message', {}).get('content', '')
                    if choices else ''
                )
                # fallback=False: se espera JSON estricto de DeepSeek
                return _parse_llm_json(raw_response, fallback=False)

            except requests.exceptions.HTTPError as e:
                print(f"  Error HTTP {e.response.status_code}: "
                      f"{e.response.text[:100]}, "
                      f"intento {attempt + 1}/{max_retries}")
                time.sleep(RETRY_SLEEP_SECONDS)
            except requests.exceptions.RequestException as e:
                print(f"  Error de red: {e}, "
                      f"intento {attempt + 1}/{max_retries}")
                time.sleep(RETRY_SLEEP_SECONDS)

        return None


# ============================================================
# Backend: OpenAI (Chat Completions API)
# ============================================================

class OpenAIBackend:
    """Backend para OpenAI API (ChatGPT, GPT-4, etc)."""

    def __init__(
        self,
        api_key: str,
        model: str = DEFAULT_OPENAI_MODEL
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

    def call(self, prompt: str, max_retries: int = 3) -> Optional[Dict]:
        """
        Llama a OpenAI y parsea la respuesta.

        Args:
            prompt: Texto a enviar al modelo.
            max_retries: Número máximo de reintentos.

        Returns:
            Diccionario con la respuesta parseada o None si falló.
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        body = {
            "model": self.model,
            "max_tokens": DEFAULT_MAX_TOKENS,
            "temperature": DEFAULT_TEMPERATURE,
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }

        for attempt in range(max_retries):
            try:
                response = requests.post(
                    self.url, headers=headers, json=body, timeout=60
                )
                response.raise_for_status()

                result = response.json()
                choices = result.get('choices', [])
                # Guardia explícita contra lista vacía
                raw_response = (
                    choices[0].get('message', {}).get('content', '')
                    if choices else ''
                )
                # fallback=False: se espera JSON estricto de OpenAI
                return _parse_llm_json(raw_response, fallback=False)

            except requests.exceptions.HTTPError as e:
                print(f"  Error HTTP {e.response.status_code}: "
                      f"{e.response.text[:100]}, "
                      f"intento {attempt + 1}/{max_retries}")
                time.sleep(RETRY_SLEEP_SECONDS)
            except requests.exceptions.RequestException as e:
                print(f"  Error de red: {e}, "
                      f"intento {attempt + 1}/{max_retries}")
                time.sleep(RETRY_SLEEP_SECONDS)

        return None


# ============================================================
# Factory
# ============================================================

def create_backend(
    backend_type: str,
    ollama_model: str = DEFAULT_OLLAMA_MODEL,
    ollama_url: str = DEFAULT_OLLAMA_URL,
    claude_model: str = DEFAULT_CLAUDE_MODEL,
    claude_api_key: Optional[str] = None,
    deepseek_model: str = DEFAULT_DEEPSEEK_MODEL,
    deepseek_api_key: Optional[str] = None,
    openai_model: str = DEFAULT_OPENAI_MODEL,
    openai_api_key: Optional[str] = None
) -> Union[QwenBackend, ClaudeBackend, DeepSeekBackend, OpenAIBackend]:
    """
    Crea el backend apropiado según la configuración.

    La API key se resuelve en este orden de prioridad:
        1. Argumento explícito (--api-key en CLI)
        2. Variable de entorno (ANTHROPIC_API_KEY / DEEPSEEK_API_KEY / OPENAI_API_KEY)

    Args:
        backend_type: 'local', 'claude', 'deepseek' u 'openai'.
        ollama_model: Modelo de Ollama.
        ollama_url: URL de Ollama.
        claude_model: Modelo de Claude.
        claude_api_key: API key de Anthropic (opcional si está en .env).
        deepseek_model: Modelo de DeepSeek.
        deepseek_api_key: API key de DeepSeek (opcional si está en .env).
        openai_model: Modelo de OpenAI.
        openai_api_key: API key de OpenAI (opcional si está en .env).

    Returns:
        Instancia del backend configurado.

    Raises:
        ValueError: Si el backend requiere API key y no se encuentra.
    """
    if backend_type == "claude":
        api_key = claude_api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError(
                "❌ Se requiere API key de Claude. "
                "Pásala con --api-key o define ANTHROPIC_API_KEY en .env"
            )
        print(f"🔑 Usando Claude API (modelo: {claude_model})")
        return ClaudeBackend(api_key, claude_model)

    if backend_type == "deepseek":
        api_key = deepseek_api_key or os.environ.get("DEEPSEEK_API_KEY")
        if not api_key:
            raise ValueError(
                "❌ Se requiere API key de DeepSeek. "
                "Pásala con --api-key o define DEEPSEEK_API_KEY en .env"
            )
        print(f"🔑 Usando DeepSeek API (modelo: {deepseek_model})")
        return DeepSeekBackend(api_key, deepseek_model)

    if backend_type == "openai":
        api_key = openai_api_key or os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "❌ Se requiere API key de OpenAI. "
                "Pásala con --api-key o define OPENAI_API_KEY en .env"
            )
        print(f"🔑 Usando OpenAI API (modelo: {openai_model})")
        return OpenAIBackend(api_key, openai_model)

    # Default: backend local con Qwen/Ollama
    print(f"🖥️ Usando Qwen local (modelo: {ollama_model})")
    return QwenBackend(ollama_model, ollama_url)


# ============================================================
# Función principal de procesamiento
# ============================================================

def add_llm_explanations(
    df: pd.DataFrame,
    backend: Union[QwenBackend, ClaudeBackend, DeepSeekBackend, OpenAIBackend],
    delay_between_calls: float = DEFAULT_DELAY_SECONDS,
    test_mode: bool = False,
    test_limit: int = 10,
    save_every: int = DEFAULT_SAVE_EVERY,
    output_path: Optional[str] = None
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

        prompt = build_prompt(row)
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
        "--ollama-model", type=str, default=DEFAULT_OLLAMA_MODEL,
        help="Modelo de Ollama (solo aplica con --backend local)"
    )
    parser.add_argument(
        "--ollama-url", type=str, default=DEFAULT_OLLAMA_URL,
        help="URL de la API de Ollama"
    )
    parser.add_argument(
        "--claude-model", type=str, default=DEFAULT_CLAUDE_MODEL,
        help="Modelo de Claude (solo aplica con --backend claude)"
    )
    parser.add_argument(
        "--deepseek-model", type=str, default=DEFAULT_DEEPSEEK_MODEL,
        help="Modelo de DeepSeek (solo aplica con --backend deepseek)"
    )
    parser.add_argument(
        "--openai-model", type=str, default=DEFAULT_OPENAI_MODEL,
        help="Modelo de OpenAI (solo aplica con --backend openai)"
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
        output_path=str(output_path)
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