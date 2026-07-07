#!/usr/bin/env python3
"""
eval_quality.py — Benchmark de calidad de explicación del LLM (#94).

Construye el benchmark *LLM Explanation Quality* del mentor (README §6): selecciona
20 POs tardíos **estratificados por etapa**, corre el prompt alineado (#91/#67) sobre
ellos y arma una tabla con los tres checks del mentor por PO:

    (a) etapa correcta   — la explicación nombra la etapa = stage_primary; para los
                           'Indeterminado', acierta si LO DECLARA indeterminado, no si
                           copia la etapa del reason code (hallazgo de #95).
    (b) cuantifica delay — cita una cifra y esa cifra coincide con delay_days_calc.
    (c) acción viable    — nombra un responsable (vendor/carrier/DC) y es operable
                           (NO se autoevalúa: lo valida el humano).

Meta del mentor: 4/5 (80%).

Los checks (a) y (b) se PRE-evalúan de forma heurística para acelerar el etiquetado;
(c) y el veredicto final los confirma una persona a mano. La selección es reproducible
(semilla fija): #99 reusa el MISMO conjunto para comparar combinaciones de few-shot.

Uso:
    # Solo seleccionar y mostrar los 20 POs (SIN llamar a la API):
    python eval_quality.py --dry-run

    # Correr el benchmark contra OpenAI (20 llamadas reales) y escribir la tabla:
    python eval_quality.py --backend openai
"""

import argparse
import re
import sys
import unicodedata
from pathlib import Path
from typing import List, Optional

import pandas as pd

# Reusar la infraestructura de F3 (mismo dir): no se reimplementa la corrida del LLM.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from llm_integration import (  # noqa: E402
    DEFAULT_MAX_TOKENS_ACTION, build_action_prompt, build_prompt,
    call_action_with_qa, compute_dataset_stats, create_backend, is_meta_action,
    load_domain_kb, load_llm_config, prepare_classified_df, reconoce_indeterminacion,
)
from fewshot import select_examples  # noqa: E402

# Combinaciones few-shot del benchmark (#99): C0=zero-shot (ya medido), C1/C2/C3 añaden
# 1/2/3 ejemplos del pool auditado, en progresión anidada por fuerza de etapa
# (Vendor ⊂ Vendor+Carrier ⊂ Vendor+Carrier+DC). Así C1⊂C2⊂C3 y se ve el efecto marginal
# de cada ejemplo añadido. Cada combinación corre los MISMOS 20 POs (semilla 42).
COMBOS = {
    "C0": lambda: None,
    "C1": lambda: select_examples(1, stages=["Vendor"]),
    "C2": lambda: select_examples(2, stages=["Vendor", "Carrier"]),
    "C3": lambda: select_examples(3, stages=["Vendor", "Carrier", "DC"]),
}

# Composición estratificada de la muestra (#94, OK del usuario): sobrerrepresenta los
# minoritarios para probar los 4 tipos de explicación con muestra suficiente cada uno.
# El universo de tardíos es ~ Vendor 131 / Carrier 40 / Indeterminado 39 / DC 37.
STRATA = {"Vendor": 8, "Carrier": 4, "Indeterminado": 4, "DC": 4}
RANDOM_STATE = 42  # semilla fija → muestra reproducible (la reusa #99)

# Versionado (junto al script): es el entregable del benchmark, evidencia que reusa #99.
OUTPUT_MD = Path(__file__).resolve().parent / "eval_quality_20pos.md"

# Temperatura ancla del benchmark: 0.3, el punto de referencia histórico del barrido de
# #137 (ADR-13). El benchmark fija su PROPIA ancla de nombrado, independiente de la
# temperatura de producción de llm_config.json (0.9 desde ADR-13 ronda 2): solo el fixture
# generado a 0.3 va sin sufijo, así el baseline reproducible nunca se pisa con otra temp.
ANCHOR_TEMP = 0.3


def resolve_temperature(arg: Optional[float]) -> float:
    """Temperatura efectiva de la corrida: el override de CLI si se dio, si no la de
    llm_config.json. Es la MISMA fuente que usa create_backend, de modo que el nombre del
    fixture y la temperatura con que se corrió no puedan discrepar (causa de #147)."""
    return arg if arg is not None else load_llm_config()["temperature"]


def _temp_suffix(temperature: Optional[float]) -> str:
    """Sufijo '_tXX' cuando la temperatura difiere del ancla; vacío si coincide o es None."""
    if temperature is None or abs(temperature - ANCHOR_TEMP) < 1e-9:
        return ""
    return f"_t{int(round(temperature * 10)):02d}"


def select_sample(df: pd.DataFrame) -> pd.DataFrame:
    """Selecciona la muestra estratificada de 20 POs tardíos (semilla fija).

    Args:
        df: DataFrame clasificado (salida de classify_po_stages).

    Returns:
        Sub-DataFrame con los POs seleccionados, ordenados por etapa.
    """
    tardios = df[df["delay_days_calc"] > 0]
    partes = []
    for etapa, n in STRATA.items():
        grupo = tardios[tardios["stage_primary"] == etapa]
        if len(grupo) < n:
            raise ValueError(
                f"Etapa '{etapa}' tiene {len(grupo)} POs tardíos, se pidieron {n}."
            )
        partes.append(grupo.sample(n=n, random_state=RANDOM_STATE))
    return pd.concat(partes).sort_values("stage_primary")


def _norm(texto: str) -> str:
    """Minúsculas sin acentos, para comparar texto del LLM de forma robusta."""
    sin_acentos = "".join(
        c for c in unicodedata.normalize("NFD", str(texto))
        if unicodedata.category(c) != "Mn"
    )
    return sin_acentos.lower()


# ── Convergencia léxica intra-etapa (gate de ARD-16 ola 2) ────────────────────
# Mide el síntoma del baseline (5/8 hipótesis Vendor convergen a "capacidad del
# proveedor") sin lista de etiquetas prohibidas: dos hipótesis "convergen" si sus tokens
# de contenido se solapan por encima de CONVERGENCE_THETA (Jaccard); el reporte es el
# clúster máximo por etapa. θ se calibró contra el fixture de la ola 1
# (eval_quality_20pos_C0_t09_accion.md): en el barrido 0.20–0.60, θ=0.25 es el punto más
# alto que reproduce el conteo humano de Vendor (5/8 "capacidad del proveedor"); desde
# 0.30 la métrica subestima la convergencia que un lector sí ve. Sesgo conocido: en
# hipótesis largas el Jaccard se diluye (Carrier del baseline da 1/4 aunque 3 mencionen
# "capacidad del transportista"), así que la métrica es conservadora, no laxa.

CONVERGENCE_THETA = 0.25

_TOKEN_RE = re.compile(r"[a-z0-9]+")

# Palabras función del español (lista cerrada): no aportan contenido a la hipótesis y
# inflarían la similitud ("la falta de la capacidad de..." vs "la gestión de la...").
_STOPWORDS_ES = frozenset((
    "de", "del", "la", "el", "los", "las", "un", "una", "unos", "unas", "y", "o",
    "u", "e", "en", "a", "al", "que", "por", "para", "con", "sin", "su", "sus",
    "se", "es", "son", "no", "lo", "le", "como", "mas", "esta", "este", "esto",
    "estan", "hay", "ha", "han", "fue", "ser", "entre", "sobre", "hacia", "debido",
))


def _hyp_tokens(texto: str) -> set:
    """Tokens de CONTENIDO de una hipótesis: normalizados (_norm), sin stopwords ni
    tokens de <3 caracteres. Base de la similitud de Jaccard de la convergencia."""
    return {
        t for t in _TOKEN_RE.findall(_norm(texto))
        if len(t) >= 3 and t not in _STOPWORDS_ES
    }


def _jaccard(a: set, b: set) -> float:
    """Similitud de Jaccard entre dos sets de tokens; 0.0 si alguno está vacío."""
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def hypothesis_convergence(hipotesis: List[str],
                           theta: float = CONVERGENCE_THETA) -> int:
    """Clúster máximo de hipótesis 'iguales' dentro de un grupo (una etapa).

    Para cada hipótesis cuenta cuántas del grupo (incluida ella misma) tienen
    Jaccard ≥ theta sobre tokens de contenido y devuelve el máximo: n hipótesis
    idénticas → n; todas distintas → 1; lista vacía → 0.
    """
    sets_ = [_hyp_tokens(h) for h in hipotesis]
    if not sets_:
        return 0
    return max(
        sum(1 for otro in sets_ if _jaccard(propio, otro) >= theta)
        for propio in sets_
    )


def _hipotesis_reconoce_indet(texto: str) -> bool:
    """True si la hipótesis reconoce la indeterminación (frente iv de la ola 2).

    Delegado a reconoce_indeterminacion de llm_integration — la MISMA función del
    check `indeterminado_sin_reconocer` (claves literales + formulación condicional),
    para que métrica y check no discrepen (patrón de is_meta_action)."""
    return reconoce_indeterminacion(texto)


def _check_etapa(explicacion: str, stage: str) -> bool:
    """(a) ¿La explicación nombra la etapa correcta?

    Para 'Indeterminado' acierta si DECLARA indeterminación (no atribuible a una sola
    etapa), no si nombra una etapa concreta tomada del reason code.
    """
    e = _norm(explicacion)
    if stage == "Indeterminado":
        return any(k in e for k in ("indetermin", "no atribuible", "no se puede atribuir",
                                    "multiples etapas", "multiple", "no concluyente"))
    return _norm(stage) in e


def _check_cuantifica(explicacion: str, delay_days: float) -> bool:
    """(b) ¿Cita el delay y la cifra coincide con la dada (±0.1 día)?"""
    e = _norm(explicacion)
    # Busca el número de días dado (con 1-2 decimales) textualmente en la explicación.
    objetivo = f"{delay_days:.2f}"
    objetivo_1 = f"{delay_days:.1f}"
    return objetivo in e or objetivo_1 in e


def evaluate(df_sample: pd.DataFrame, backend, examples=None, kb=None,
             action_call: bool = False, action_backend=None,
             stats: Optional[dict] = None) -> pd.DataFrame:
    """Corre el LLM sobre la muestra y pre-evalúa los checks objetivos (a) y (b).

    Args:
        df_sample: muestra estratificada (20 POs).
        backend: backend de LLM (de create_backend).
        examples: ejemplos few-shot a anteponer (#99). None → zero-shot (C0). Se pasan tal
            cual a build_prompt; las MISMAS condiciones (semilla 42, muestra) en todas las
            combinaciones, solo cambia el número de ejemplos.
        kb: dict opcional de la base de conocimiento de dominio (#151), de load_domain_kb.
            None (default) → sin bloque de contexto de dominio. Se pasa tal cual a
            build_prompt; validar su efecto en diversidad es independiente de `examples`
            (el cruce kb×few-shot queda fuera de esta ronda).
        action_call: activa la llamada de acción (ARD-16 ola 1) sobre el diagnóstico de
            la llamada 1: añade a la tabla el plan (hipótesis / acciones / paso
            discriminante) y los qa_flags, y el check de verbo meta se evalúa sobre la
            accion_inmediata (la acción de la llamada 1 deja de consumirse).
        action_backend: backend de la llamada 2 (max_tokens_action). None → `backend`.
        stats: dict de compute_dataset_stats sobre el df clasificado COMPLETO (no la
            muestra); requerido si action_call.

    Returns:
        DataFrame con una fila por PO: datos dados, explicación del LLM, los
        pre-veredictos de (a)/(b) y el de verbo meta. (c) y el veredicto final quedan
        vacíos para el humano.
    """
    filas = []
    for _, row in df_sample.iterrows():
        prompt = build_prompt(row, examples=examples, kb=kb)
        resp = backend.call(prompt) or {}
        causa = resp.get("causa_raiz", "")
        delay = float(row["delay_days_calc"])
        fila = {
            "PO_NBR": row["PO_NBR"],
            "stage_primary": row["stage_primary"],
            "delay_days_calc": round(delay, 2),
            "REASON_DSC": row.get("REASON_DSC", ""),
            "llm_causa_raiz": causa,
            "llm_accion": resp.get("accion_recomendada", ""),
        }
        # La acción principal sobre la que se mide el verbo meta: en modo acción es la
        # accion_inmediata del plan; en modo clásico, la accion_recomendada histórica
        # (así la métrica es comparable contra los fixtures previos).
        accion_principal = fila["llm_accion"]
        if action_call:
            if resp:
                action_prompt = build_action_prompt(row, resp, stats)
                parsed, qa_flags = call_action_with_qa(
                    action_backend or backend, action_prompt, row
                )
            else:
                # Política ola 1: sin diagnóstico de la llamada 1 no hay llamada 2.
                parsed, qa_flags = {}, ["sin_diagnostico_llamada1"]
            fila.update({
                "llm_hipotesis": parsed.get("hipotesis", ""),
                "llm_hipotesis_alt": parsed.get("hipotesis_alt", ""),
                "llm_accion_inmediata": parsed.get("accion_inmediata", ""),
                "llm_accion_correctiva": parsed.get("accion_correctiva", ""),
                "llm_accion_preventiva": parsed.get("accion_preventiva", ""),
                "llm_paso_discriminante": parsed.get("paso_discriminante", ""),
                "qa_flags": ";".join(qa_flags),
            })
            accion_principal = fila["llm_accion_inmediata"]
        fila.update({
            "chk_a_etapa": _check_etapa(causa, row["stage_primary"]),
            "chk_b_cuantifica": _check_cuantifica(causa, delay),
            "chk_meta": is_meta_action(accion_principal),
            "chk_c_accion_viable": "",   # ← lo valida el humano
            "veredicto": "",             # ← lo confirma el humano (PASA si a&b&c)
        })
        filas.append(fila)
    return pd.DataFrame(filas)


def _celda(texto) -> str:
    """Texto seguro para una celda de la tabla markdown (sin | ni saltos de línea)."""
    return str(texto).replace("|", "\\|").replace("\n", " ")


def _ola2_metric_lines(df_eval: pd.DataFrame) -> List[str]:
    """Líneas del resumen con las métricas de la ola 2 (solo modo acción, ARD-16):
    convergencia léxica intra-etapa (gate) y tasa de hipótesis Indeterminado que
    reconocen la indeterminación."""
    conv_partes = []
    for etapa in STRATA:
        grupo = df_eval[df_eval["stage_primary"] == etapa]
        if len(grupo):
            cluster = hypothesis_convergence(list(grupo["llm_hipotesis"]))
            conv_partes.append(f"{etapa} {cluster}/{len(grupo)}")
    indet = df_eval[df_eval["stage_primary"] == "Indeterminado"]
    k_indet = int(indet["llm_hipotesis"].map(_hipotesis_reconoce_indet).sum())
    return [
        f"Convergencia intra-etapa (θ={CONVERGENCE_THETA}): " + " · ".join(conv_partes)
        + " (meta ola 2: sin clúster de plantilla; un clúster alineado a evidencia "
        "compartida no cuenta como fallo — criterio de Discriminación de ARD-16, "
        "validar la covarianza señal→hipótesis a mano).",
        f"Indeterminado reconoce indeterminación: {k_indet}/{len(indet)} "
        "(meta ola 2: todas).",
    ]


def to_markdown(df_eval: pd.DataFrame) -> str:
    """Arma el documento .md del benchmark: criterio + tabla + resumen pre-evaluado.

    Modo clásico: la tabla histórica + la columna (meta) — tasa de verbos meta como
    acción principal (ARD-16; medible también sobre corridas de una sola llamada, para
    comparar contra los fixtures previos). Modo acción (detectado por la presencia de
    `llm_accion_inmediata`): la acción de la llamada 1 deja de consumirse y la tabla
    muestra el plan del contrato híbrido + qa_flags.
    """
    action_mode = "llm_accion_inmediata" in df_eval.columns
    n = len(df_eval)
    pre_ok = (df_eval["chk_a_etapa"] & df_eval["chk_b_cuantifica"]).sum()
    n_meta = int(df_eval["chk_meta"].sum())
    lineas = [
        "# Benchmark de calidad de explicación del LLM — 20 POs (#94)",
        "",
        "Métrica del mentor *LLM Explanation Quality* (README §6). Muestra estratificada "
        f"8/4/4/4 (Vendor/Carrier/Indeterminado/DC), semilla `{RANDOM_STATE}` (reproducible; "
        "la reusa #99). Backend: el oficial del entregable.",
        "",
        "## Criterio (binario por PO; PASA si cumple los 3)",
        "- **(a) etapa correcta:** nombra la etapa = `stage_primary`. Para `Indeterminado`, "
        "acierta si lo declara indeterminado (no si copia la etapa del reason code).",
        "- **(b) cuantifica el delay:** cita una cifra y coincide con `delay_days_calc`.",
        "- **(c) acción viable:** nombra responsable y es operable (NO genérica). *Validación humana.*",
        "- **(meta) sin verbo meta:** la acción principal no arranca con revisar/analizar/"
        "investigar/monitorear/dar seguimiento (ARD-16; no cuenta para PASA, se reporta "
        "como tasa).",
        "",
        f"## Pre-evaluación automática (a & b): {pre_ok}/{n}",
        f"Tasa de verbos meta como acción principal: {n_meta}/{n} (meta ola 1 de ARD-16: 0).",
    ]
    if action_mode:
        lineas += _ola2_metric_lines(df_eval)
    lineas += [
        "",
        "_(c) y el veredicto final los confirma una persona; rellenar las columnas vacías._",
        "",
    ]
    if action_mode:
        lineas += [
            "| PO | etapa | delay (d) | REASON_DSC | explicación LLM | hipótesis | "
            "hipótesis alternativa | acción inmediata | acción correctiva | "
            "acción preventiva | paso discriminante "
            "| qa_flags | (a) | (b) | (meta) | (c)? | veredicto |",
            "|---|---|--:|---|---|---|---|---|---|---|---|---|:--:|:--:|:--:|:--:|:--:|",
        ]
    else:
        lineas += [
            "| PO | etapa | delay (d) | REASON_DSC | explicación LLM | acción LLM | (a) "
            "| (b) | (meta) | (c)? | veredicto |",
            "|---|---|--:|---|---|---|:--:|:--:|:--:|:--:|:--:|",
        ]
    for _, r in df_eval.iterrows():
        a = "✅" if r["chk_a_etapa"] else "❌"
        b = "✅" if r["chk_b_cuantifica"] else "❌"
        meta = "❌" if r["chk_meta"] else "✅"   # ❌ = arranca con verbo meta
        base = (
            f"| {r['PO_NBR']} | {r['stage_primary']} | {r['delay_days_calc']:.2f} | "
            f"{_celda(r['REASON_DSC'])} | {_celda(r['llm_causa_raiz'])} | "
        )
        if action_mode:
            lineas.append(
                base
                + f"{_celda(r['llm_hipotesis'])} | {_celda(r['llm_hipotesis_alt'])} | "
                f"{_celda(r['llm_accion_inmediata'])} | "
                f"{_celda(r['llm_accion_correctiva'])} | {_celda(r['llm_accion_preventiva'])} | "
                f"{_celda(r['llm_paso_discriminante'])} | {_celda(r['qa_flags'])} | "
                f"{a} | {b} | {meta} |  |  |"
            )
        else:
            lineas.append(
                base + f"{_celda(r['llm_accion'])} | {a} | {b} | {meta} |  |  |"
            )
    lineas += [
        "",
        "## Resultado (a completar tras validación humana)",
        f"- POs que PASAN: __/{n}  →  equivalente sobre 5: __/5  (meta del mentor: 4/5).",
        "- Fallos y por qué: _(documentar aquí)_.",
        "",
    ]
    return "\n".join(lineas)


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark de calidad LLM (20 POs, #94)")
    parser.add_argument("--backend", default="openai",
                        choices=["local", "claude", "deepseek", "openai"])
    parser.add_argument("--dry-run", action="store_true",
                        help="Solo seleccionar y mostrar los 20 POs, sin llamar a la API.")
    parser.add_argument("--combo", default="C0", choices=list(COMBOS),
                        help="Combinación few-shot (#99): C0=zero-shot, C1/C2/C3=1/2/3 "
                             "ejemplos del pool. Cada una corre los mismos 20 POs.")
    parser.add_argument("--temperature", type=float, default=None,
                        help="Override de temperatura (default: la de llm_config.json, "
                             "actualmente 0.9). La temperatura EFECTIVA (override o config) "
                             "se codifica en el nombre del fixture cuando difiere del ancla "
                             f"({ANCHOR_TEMP}).")
    parser.add_argument("--kb", action="store_true",
                        help="Activa el contexto de dominio condicional (#151, "
                             "domain_kb.json). Default: sin kb (comportamiento histórico). "
                             "Esta ronda valida kb sobre C0; el cruce con --combo es "
                             "exploratorio, no el gate de esta ronda.")
    parser.add_argument("--action-call", action="store_true",
                        help="Activa la llamada de acción (ARD-16 ola 1): 2 llamadas por "
                             "PO (diagnóstico + plan con contrato híbrido y checks por "
                             "regla, con hasta 2 regeneraciones de QA). El fixture lleva "
                             "sufijo _accion. Default: solo la llamada 1.")
    parser.add_argument("--tag", default="",
                        help="Sufijo opcional del nombre del fixture (p. ej. 'ola2'): "
                             "permite correr las mismas banderas sin pisar el fixture "
                             "previo, que queda como baseline de comparación. Con --tag "
                             "la salida siempre va a fixtures/.")
    args = parser.parse_args()

    examples = COMBOS[args.combo]()
    kb = load_domain_kb() if args.kb else None

    df = prepare_classified_df(from_csv=False)
    sample = select_sample(df)

    print(f"Muestra estratificada (20 POs, semilla {RANDOM_STATE}):")
    print(sample["stage_primary"].value_counts().to_string())
    n_ej = 0 if examples is None else len(examples)
    print(f"Combinación: {args.combo} ({n_ej} ejemplo(s) few-shot)")
    print(f"Contexto de dominio (#151): {'activo' if kb else 'inactivo'}")

    # Temperatura efectiva = la de la corrida (override o config); de ELLA sale el sufijo,
    # no del argumento crudo. Sin --temperature, con la config en 0.9, el fixture lleva
    # _t09 y no pisa el baseline 0.3 sin sufijo (#147).
    temperatura = resolve_temperature(args.temperature)
    temp_suffix = _temp_suffix(temperatura)
    kb_suffix = "_kb" if args.kb else ""
    accion_suffix = "_accion" if args.action_call else ""
    tag_suffix = f"_{args.tag}" if args.tag else ""
    # Nombre de salida: C0 a la temperatura ancla, sin kb, sin llamada de acción y sin
    # tag → benchmark principal (junto al script); cualquier otra variante → fixtures/.
    if (args.combo == "C0" and not temp_suffix and not kb_suffix
            and not accion_suffix and not tag_suffix):
        out_md = OUTPUT_MD
    else:
        out_md = (OUTPUT_MD.parent / "fixtures" /
                  f"eval_quality_20pos_{args.combo}{temp_suffix}{kb_suffix}"
                  f"{accion_suffix}{tag_suffix}.md")

    if args.dry_run:
        cols = ["PO_NBR", "stage_primary", "delay_days_calc", "REASON_DSC"]
        print("\n" + sample[cols].to_string(index=False))
        if examples:
            origen = [e.get("_meta", {}).get("po_origen") for e in examples]
            print(f"\nEjemplos few-shot de la combinación {args.combo}: POs {origen}")
        origen_temp = "override" if args.temperature is not None else "llm_config.json"
        print(f"\nTemperatura efectiva: {temperatura} ({origen_temp})")
        print(f"Fixture de salida: {out_md}")
        print("\n(dry-run: no se llamó a la API.)")
        return

    backend = create_backend(backend_type=args.backend, temperature=temperatura)

    # Llamada de acción (ARD-16 ola 1): backend propio con max_tokens_action y
    # estadísticos globales del df COMPLETO (no de la muestra), una vez por corrida.
    action_backend = None
    stats = None
    if args.action_call:
        stats = compute_dataset_stats(df)
        action_backend = create_backend(
            backend_type=args.backend, temperature=temperatura,
            max_tokens=load_llm_config().get(
                "max_tokens_action", DEFAULT_MAX_TOKENS_ACTION
            ),
        )
        print(f"\nModo acción: 2 llamadas por PO → {2 * len(sample)} llamadas base "
              f"(hasta {4 * len(sample)} con reintentos de QA), backend {args.backend}.")

    print(f"\nCorriendo {len(sample)} POs por el LLM ({args.backend})...")
    df_eval = evaluate(sample, backend, examples=examples, kb=kb,
                       action_call=args.action_call, action_backend=action_backend,
                       stats=stats)
    out_md.write_text(to_markdown(df_eval), encoding="utf-8")
    pre_ok = int((df_eval["chk_a_etapa"] & df_eval["chk_b_cuantifica"]).sum())
    n_meta = int(df_eval["chk_meta"].sum())
    print(f"Pre-evaluación (a & b): {pre_ok}/{len(df_eval)}")
    print(f"Verbos meta como acción principal: {n_meta}/{len(df_eval)} "
          "(meta ola 1 de ARD-16: 0)")
    print(f"Tabla escrita en: {out_md}")
    print("Falta validar a mano (c) y el veredicto final.")


if __name__ == "__main__":
    main()
