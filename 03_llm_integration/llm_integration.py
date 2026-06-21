#!/usr/bin/env python3
"""
llm_integration.py

Fase 3 — Integración con LLM para generar explicaciones de causa raíz.

Soporta tres backends:
    - Qwen 2.5:7B (local, vía Ollama)     -> modo local
    - Claude (Anthropic API)               -> modo cloud
    - DeepSeek (DeepSeek API)              -> modo cloud

Uso:
    # Modo local (Qwen con Ollama)
    python llm_integration.py --mode test --backend local

    # Modo cloud (Claude con API key)
    python llm_integration.py --mode test --backend claude --api-key sk-ant-...

    # Modo cloud (DeepSeek con API key)
    python llm_integration.py --mode test --backend deepseek --api-key sk-...

    # Modo producción con Claude
    python llm_integration.py --mode full --backend claude

Variables de entorno (recomendado):
    ANTHROPIC_API_KEY=sk-ant-...
    DEEPSEEK_API_KEY=sk-...
    OLLAMA_URL=http://localhost:11434/api/generate
"""

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Union

import pandas as pd
import requests
from dotenv import load_dotenv
from tqdm import tqdm

# ============================================================
# Constantes (PEP 8: mayúsculas con guión bajo)
# ============================================================

DEFAULT_OLLAMA_URL = "http://localhost:11434/api/generate"
DEFAULT_OLLAMA_MODEL = "qwen2.5:7b"
DEFAULT_CLAUDE_MODEL = "claude-3-sonnet-20241022"
DEFAULT_DEEPSEEK_MODEL = "deepseek-chat"   # alternativa: "deepseek-reasoner"
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

def build_prompt(row: pd.Series) -> str:
    """
    Construye el prompt para el LLM a partir de una fila del DataFrame.

    Args:
        row: Una fila del DataFrame con los datos de una PO.

    Returns:
        Prompt formateado listo para enviar al LLM.
    """
    hot_flag = "Sí" if row.get('HOT_PO_FLAG', 0) == 1 else "No"
    short_ship = "Sí" if row.get('_short_ship', False) else "No"

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
        "CONTEXTO ADICIONAL:",
        f"- ¿Es Hot PO (urgente)? {hot_flag}",
        f"- ¿Es short ship (envío incompleto)? {short_ship}",
        f"- Código de motivo registrado por el DC: {row.get('REASON_DSC', 'No registrado')}\n",
        "INSTRUCCIONES:",
        "Genera un análisis en formato JSON. "
        "Responde ÚNICAMENTE con el JSON, sin texto adicional.\n",
        "Formato requerido:",
        "{",
        '  "causa_raiz": "Explicación de 1-2 líneas",',
        '  "accion_recomendada": "Acción concreta. Menciona al responsable",',
        '  "severidad": "HIGH o MEDIUM o LOW",',
        '  "coincide_con_reason_code": true o false,',
        '  "confianza": 0.0 a 1.0',
        "}\n",
        "Reglas de severidad:",
        "- HIGH: Hot PO con retraso, O retraso > 7 días, O short ship + retraso",
        "- MEDIUM: Retraso > 0 días sin agravantes",
        "- LOW: Sin retraso\n",
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
# Factory
# ============================================================

def create_backend(
    backend_type: str,
    ollama_model: str = DEFAULT_OLLAMA_MODEL,
    ollama_url: str = DEFAULT_OLLAMA_URL,
    claude_model: str = DEFAULT_CLAUDE_MODEL,
    claude_api_key: Optional[str] = None,
    deepseek_model: str = DEFAULT_DEEPSEEK_MODEL,
    deepseek_api_key: Optional[str] = None
) -> Union[QwenBackend, ClaudeBackend, DeepSeekBackend]:
    """
    Crea el backend apropiado según la configuración.

    La API key se resuelve en este orden de prioridad:
        1. Argumento explícito (--api-key en CLI)
        2. Variable de entorno (ANTHROPIC_API_KEY / DEEPSEEK_API_KEY)

    Args:
        backend_type: 'local', 'claude' o 'deepseek'.
        ollama_model: Modelo de Ollama.
        ollama_url: URL de Ollama.
        claude_model: Modelo de Claude.
        claude_api_key: API key de Anthropic (opcional si está en .env).
        deepseek_model: Modelo de DeepSeek.
        deepseek_api_key: API key de DeepSeek (opcional si está en .env).

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

    # Default: backend local con Qwen/Ollama
    print(f"🖥️ Usando Qwen local (modelo: {ollama_model})")
    return QwenBackend(ollama_model, ollama_url)


# ============================================================
# Función principal de procesamiento
# ============================================================

def add_llm_explanations(
    df: pd.DataFrame,
    backend: Union[QwenBackend, ClaudeBackend, DeepSeekBackend],
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
        choices=["local", "claude", "deepseek"],
        help="Backend: local (Qwen/Ollama), claude o deepseek"
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
        "--api-key", type=str, default=None,
        help=(
            "API key del backend seleccionado. "
            "Alternativa: ANTHROPIC_API_KEY o DEEPSEEK_API_KEY en .env"
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

    # --------------------------------------------------------
    # Configurar sys.path para imports locales del proyecto.
    # Se hace aquí (y no al top-level) porque las rutas dependen
    # de __file__, que solo está disponible en tiempo de ejecución.
    # --------------------------------------------------------
    repo_root = Path(__file__).resolve().parent.parent
    for sub in ("01_data_pipeline_and_eda", "02_clasif_reglas_negocio"):
        sub_path = str(repo_root / sub)
        if sub_path not in sys.path:
            sys.path.insert(0, sub_path)

    from pipeline_core import clean_po_data, _DATE_INPUT_COLUMNS  # noqa: E402
    from classifier_core import classify_po_stages  # noqa: E402

    print("=" * 60)
    print("Fase 3 — Integración con LLM (Producción)")
    print("=" * 60)

    # Origen de los datos clasificados: por DEFAULT se recomputa la cadena completa
    # (clean -> classify) — nunca se sirven datos rancios por defecto (H3). La lectura
    # del handoff de F2 (df_classified.csv) es OPT-IN: --from-csv o env PO_USE_PREV_CSV.
    # Si se pide y el CSV existe, se carga reparseando las fechas (texto en el CSV) para
    # que sea funcionalmente idéntico a lo que la cadena dejaría en memoria.
    from_csv = args.from_csv or bool(os.environ.get("PO_USE_PREV_CSV"))
    classified_csv = repo_root / "data" / "processed" / "df_classified.csv"

    if from_csv and classified_csv.exists():
        df_classified = pd.read_csv(
            classified_csv, low_memory=False, parse_dates=list(_DATE_INPUT_COLUMNS)
        )
        print(f"📂 Handoff F2 leído desde CSV (opt-in): {classified_csv}")
    else:
        if from_csv:
            print(f"⚠️ --from-csv pedido pero no existe {classified_csv}; se recomputa.")
        csv_path = repo_root / "data" / "raw" / "po_root_cause_synthetic.csv"
        if not csv_path.exists():
            print(f"❌ CSV no encontrado en {csv_path}")
            sys.exit(1)

        print(f"📂 Cargando CSV: {csv_path}")
        df_raw = pd.read_csv(csv_path, low_memory=False)

        print("🔧 Ejecutando pipeline de limpieza...")
        df_clean = clean_po_data(df_raw)

        print("🔧 Ejecutando clasificador por etapa...")
        df_classified = classify_po_stages(df_clean)

    # Resolver API key según el backend elegido
    claude_api_key = args.api_key if args.backend == "claude" else None
    deepseek_api_key = args.api_key if args.backend == "deepseek" else None

    try:
        backend = create_backend(
            backend_type=args.backend,
            ollama_model=args.ollama_model,
            ollama_url=args.ollama_url,
            claude_model=args.claude_model,
            claude_api_key=claude_api_key,
            deepseek_model=args.deepseek_model,
            deepseek_api_key=deepseek_api_key
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

    # Guardar resultado final
    df_with_llm.to_csv(output_path, index=False)
    print(f"\n💾 Resultado guardado en: {output_path}")

    # Estadísticas finales
    total_delayed = (df_with_llm['delay_days_calc'] > 0).sum()
    with_llm = df_with_llm['llm_causa_raiz'].str.len().gt(0).sum()

    print("\n📊 Estadísticas finales:")
    print(f"   Total POs:             {len(df_with_llm)}")
    print(f"   POs retrasados:        {total_delayed}")
    print(f"   POs con análisis LLM:  {with_llm}")


if __name__ == "__main__":
    main()