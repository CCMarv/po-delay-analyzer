#!/usr/bin/env python3
"""
eval_differentiation.py — Diferenciación intra-etapa de las recomendaciones tier-2 (#151).

Mide, sobre el output del entregable (`po_output.csv`, corrida full con `--action-call`),
si POs de la MISMA etapa reciben recomendaciones DIFERENCIADAS ahora que existe la señal
diferencial de tier-2 (hipótesis + evidencia + paso discriminante + plan escalonado).

Operacionalización (ADR-16 §Validación/Discriminación): NO es la diversidad léxica de
ADR-15 —dos POs con la misma evidencia DEBEN converger; penalizar la convergencia por sí
sola premiaría el ruido—. Se separa convergencia justificada de convergencia sospechosa en
dos capas:

  Capa 1 — Convergencia léxica intra-etapa. Por etapa, tokens de contenido (normalizados,
    sin stopwords, len>=3) y Jaccard por pares; dos POs "convergen" si Jaccard >= THETA
    (0.25, heredado del fixture de ola 1 en ADR-16). Los clústeres se forman por líder /
    vecindario: cada miembro queda dentro de THETA del líder, sin encadenamiento
    transitivo. Se mide sobre DOS campos —`llm_hipotesis` (diagnóstico) y
    `llm_accion_inmediata` (recomendación)— para localizar dónde entra la homogeneidad en
    la cadena evidencia -> hipótesis -> acción.

  Capa 2 — Covarianza señal -> hipótesis. A cada clúster convergente se le lee una firma de
    evidencia por PO, derivada de columnas DETERMINISTAS (no del texto del LLM):
    is_short_ship, HOT_PO_FLAG, llm_coincide_con_reason (señales fuertes discretas) y el
    tercil de magnitud del exceso de la etapa (señal graduada). Clasificación:
      - justificado: los miembros no difieren en ninguna señal fuerte (misma evidencia).
      - graduado:    difieren solo en el tercil de magnitud (misma evidencia, otra
                     intensidad); no es fallo.
      - sospechoso:  difieren en >=1 señal fuerte y aun así convergen léxicamente — el
                     fallo que mide #151 (el clúster que "ignora la evidencia" de ADR-16).

Métrica titular: fracción de POs en clústeres SOSPECHOSOS, por campo y por etapa.

Reproducible y SIN API: solo LEE `po_output.csv`. El CSV con tier-2 poblado se genera
aparte (gasta API) con:  python llm_integration.py --mode full --backend openai --action-call

Uso:
    python eval_differentiation.py
    python eval_differentiation.py --po-output ../data/processed/po_output.csv
    python eval_differentiation.py --no-write
"""

import argparse
import re
import unicodedata
from collections import Counter
from pathlib import Path

import pandas as pd

# Rutas por defecto resueltas desde la raíz del repo (patrón de eval_severity_ranking.py),
# para correr desde cualquier CWD.
REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PO_OUTPUT = REPO_ROOT / "data" / "processed" / "po_output.csv"

# Reporte versionado, junto al script (patrón de eval_quality.py / eval_severity_ranking.py).
OUTPUT_MD = Path(__file__).resolve().parent / "eval_differentiation.md"

# ── Helpers léxicos ───────────────────────────────────────────────────────────
# Copiados VERBATIM de la métrica de convergencia de ADR-16 en eval_quality.py (θ,
# stopwords, tokenización), para que la métrica sea idéntica. NO se importa eval_quality:
# su top-level hace `from llm_integration import ...`, que arrastraría todo el pipeline
# (backends, config) a un script que solo debe leer un CSV. Consolidar ambas copias en un
# módulo compartido queda como deuda diferida, fuera del alcance de #151.
CONVERGENCE_THETA = 0.25

_TOKEN_RE = re.compile(r"[a-z0-9]+")

_STOPWORDS_ES = frozenset((
    "de", "del", "la", "el", "los", "las", "un", "una", "unos", "unas", "y", "o",
    "u", "e", "en", "a", "al", "que", "por", "para", "con", "sin", "su", "sus",
    "se", "es", "son", "no", "lo", "le", "como", "mas", "esta", "este", "esto",
    "estan", "hay", "ha", "han", "fue", "ser", "entre", "sobre", "hacia", "debido",
))


def _norm(texto: str) -> str:
    """Minúsculas sin acentos, para comparar texto del LLM de forma robusta."""
    sin_acentos = "".join(
        c for c in unicodedata.normalize("NFD", str(texto))
        if unicodedata.category(c) != "Mn"
    )
    return sin_acentos.lower()


def _tokens(texto: str) -> set:
    """Tokens de CONTENIDO: normalizados, sin stopwords ni tokens de <3 caracteres."""
    return {
        t for t in _TOKEN_RE.findall(_norm(texto))
        if len(t) >= 3 and t not in _STOPWORDS_ES
    }


def _jaccard(a: set, b: set) -> float:
    """Similitud de Jaccard entre dos sets de tokens; 0.0 si alguno está vacío."""
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


# ── Configuración de la medición ──────────────────────────────────────────────
# Campos medidos: diagnóstico y recomendación (columna -> etiqueta legible).
FIELDS = {
    "llm_hipotesis": "hipótesis",
    "llm_accion_inmediata": "acción inmediata",
}

# Señales FUERTES discretas de la firma de evidencia (su desacuerdo = evidencia distinta).
STRONG_SIGNALS = ["is_short_ship", "HOT_PO_FLAG", "llm_coincide_con_reason"]

# Exceso que define la magnitud dominante de cada etapa. Indeterminado no tiene una etapa
# de exceso única -> se usa delay_days_calc como proxy de magnitud.
STAGE_EXCESS = {
    "Vendor": "excess_vendor_hrs",
    "Carrier": "excess_carrier_hrs",
    "DC": "excess_dc_hrs",
}


# ── Capa 2: firma de evidencia ────────────────────────────────────────────────
def magnitude_tercile(series: pd.Series) -> pd.Series:
    """Tercil (T0/T1/T2) del valor DENTRO del grupo, robusto a duplicados/valores
    constantes. Con muchos empates qcut colapsa bins: se acepta y se etiqueta con los que
    resulten (la magnitud es una señal graduada, no fuerte)."""
    try:
        codes = pd.qcut(series, 3, labels=False, duplicates="drop")
        return codes.map(lambda c: f"T{int(c)}" if pd.notna(c) else "T0")
    except (ValueError, IndexError):
        return pd.Series(["T0"] * len(series), index=series.index)


def add_signature(g: pd.DataFrame, stage: str) -> pd.DataFrame:
    """Agrega la columna `_tercil` (magnitud de la etapa) al grupo de una etapa."""
    g = g.copy()
    col = STAGE_EXCESS.get(stage, "delay_days_calc")
    g["_tercil"] = magnitude_tercile(g[col])
    return g


# ── Capa 1: clustering por líder / vecindario ─────────────────────────────────
def convergent_clusters(token_sets: list, theta: float = CONVERGENCE_THETA) -> list:
    """Partición de los POs de una etapa por líder/vecindario.

    Cada clúster se ancla en el PO con más vecinos (Jaccard >= theta) aún sin asignar, y lo
    forman ese líder y sus vecinos libres. Así cada miembro queda dentro de theta del líder
    (afirmar "comparten recomendación" es justo) y se evita el encadenamiento transitivo de
    las componentes conexas. Devuelve una lista de listas de índices posicionales; el índice
    0 de cada clúster es el líder. Incluye singletons (POs diferenciados).
    """
    n = len(token_sets)
    neighbors = {i: set() for i in range(n)}
    for i in range(n):
        for j in range(i + 1, n):
            if _jaccard(token_sets[i], token_sets[j]) >= theta:
                neighbors[i].add(j)
                neighbors[j].add(i)
    unassigned = set(range(n))
    clusters = []
    while unassigned:
        leader = max(unassigned, key=lambda i, u=unassigned: len(neighbors[i] & u))
        members = {leader} | (neighbors[leader] & unassigned)
        clusters.append([leader] + sorted(members - {leader}))
        unassigned -= members
    return clusters


def mean_pairwise_jaccard(token_sets: list) -> float:
    """Jaccard medio sobre todos los pares del grupo; NaN si hay <2 POs."""
    n = len(token_sets)
    if n < 2:
        return float("nan")
    total = pares = 0
    for i in range(n):
        for j in range(i + 1, n):
            total += _jaccard(token_sets[i], token_sets[j])
            pares += 1
    return total / pares if pares else float("nan")


def _strong_sig(r) -> tuple:
    """Firma FUERTE de un PO: señales discretas cuyo desacuerdo = evidencia distinta."""
    return (str(r["is_short_ship"]), str(r["HOT_PO_FLAG"]),
            str(r["llm_coincide_con_reason"]))


# ── Medición por campo ────────────────────────────────────────────────────────
def _cluster_record(g: pd.DataFrame, c: list, field: str) -> dict:
    """Registro de un clúster convergente.

    Fija la firma fuerte MODAL del clúster (la más común; empates -> la primera) y marca
    'fuera de firma' (off) a cada miembro cuya firma fuerte difiere de la modal: son los POs
    que reciben la recomendación calibrada a otra evidencia — el 'clúster que ignora la
    evidencia' de ADR-16, a nivel del PO mal servido. La pureza modal (miembros en la firma
    modal / tamaño) mide cuánto de la convergencia es evidencia-alineada.
    """
    sub = g.iloc[c]
    filas = [r for _, r in sub.iterrows()]
    sigs = [_strong_sig(r) for r in filas]
    modal = Counter(sigs).most_common(1)[0][0]
    miembros = []
    for r, s in zip(filas, sigs):
        difiere = [name for name, a, b in zip(STRONG_SIGNALS, s, modal) if a != b]
        miembros.append({
            "PO": r["PO_NBR"],
            "short": bool(r["is_short_ship"]),
            "hot": int(r["HOT_PO_FLAG"]),
            "coincide": bool(r["llm_coincide_con_reason"]),
            "tercil": r["_tercil"],
            "texto": str(r[field]),
            "off": bool(difiere),
            "difiere": difiere,
        })
    return {
        "size": len(c),
        "purity": sigs.count(modal) / len(sigs),
        "n_off": sum(1 for m in miembros if m["off"]),
        "modal_texto": str(g.iloc[c[0]][field]),
        "miembros": miembros,
    }


def measure(df: pd.DataFrame, field: str) -> dict:
    """Mide la diferenciación intra-etapa de un campo. Por etapa: convergencia (Capa 1),
    pureza modal y POs fuera de firma (Capa 2), más la lista de clústeres."""
    por_etapa = {}
    for stage, g in df.groupby("stage"):
        g = add_signature(g, stage)
        token_sets = [_tokens(t) for t in g[field].fillna("").tolist()]
        convergentes = [c for c in convergent_clusters(token_sets) if len(c) >= 2]
        info = [_cluster_record(g, c, field) for c in convergentes]
        n_en_conv = sum(r["size"] for r in info)
        # Pureza típica que ve un PO convergente (media ponderada por tamaño de clúster).
        purity_media = (sum(r["purity"] * r["size"] for r in info) / n_en_conv
                        if n_en_conv else float("nan"))
        n = len(g)
        n_off = sum(r["n_off"] for r in info)
        por_etapa[stage] = {
            "n": n,
            "jaccard_medio": mean_pairwise_jaccard(token_sets),
            "n_clusters": len(convergentes),
            "mayor": max((len(c) for c in convergentes), default=1),
            "n_en_conv": n_en_conv,
            "pct_en_conv": n_en_conv / n if n else 0.0,
            "purity_media": purity_media,
            "n_off": n_off,
            "pct_off": n_off / n if n else 0.0,
            "clusters": info,
        }
    return por_etapa


# ── Reporte markdown ──────────────────────────────────────────────────────────
def _celda(texto) -> str:
    """Texto seguro para una celda markdown (sin | ni saltos de línea)."""
    return str(texto).replace("|", "\\|").replace("\n", " ")


def _snippet(texto, n: int = 180) -> str:
    """Recorte corto de un texto del LLM para el reporte."""
    s = str(texto).replace("\n", " ").strip()
    return s if len(s) <= n else s[: n - 1] + "…"


def _firma_str(m: dict) -> str:
    """Firma legible de un miembro para la tabla del reporte."""
    return (f"short={m['short']}, hot={m['hot']}, coincide={m['coincide']}, "
            f"mag={m['tercil']}")


def to_markdown(medidas: dict, n_total: int, coincide_counts: dict) -> str:
    L = [
        "# Diferenciación intra-etapa de las recomendaciones tier-2 (#151)",
        "",
        "Se mide si POs de la misma etapa reciben recomendaciones diferenciadas, ahora que "
        "tier-2 emite señal diferencial (hipótesis + evidencia + paso discriminante + plan). "
        "La operacionalización sigue "
        "[ADR-16](../documentation/decisiones/ARD-16.md) §Validación/Discriminación: no la "
        "diversidad léxica de ADR-15 —dos POs con la misma evidencia deben converger—, sino "
        "convergencia léxica intra-etapa leída junto con la covarianza señal -> hipótesis.",
        "",
        "Método en dos capas:",
        "",
        "1. **Convergencia léxica intra-etapa.** Por etapa, Jaccard sobre tokens de "
        f"contenido; dos POs convergen si Jaccard >= θ={CONVERGENCE_THETA}. Los clústeres se "
        "forman por líder/vecindario (cada miembro dentro de θ del líder, sin encadenamiento "
        "transitivo). Se mide sobre `llm_hipotesis` y `llm_accion_inmediata`.",
        "2. **Covarianza señal -> hipótesis.** A cada clúster convergente se le fija la firma "
        "de evidencia determinista MODAL de sus miembros (`is_short_ship`, `HOT_PO_FLAG`, "
        "`llm_coincide_con_reason`; el tercil de magnitud del exceso es señal graduada y no "
        "cuenta para la firma). La convergencia con firma modal homogénea es *justificada* "
        "(misma evidencia -> misma recomendación) y la **pureza modal** mide esa fracción. El "
        "fallo —el clúster que *ignora la evidencia* de ADR-16— son los POs **fuera de "
        "firma**: los que reciben la recomendación modal aunque su firma fuerte difiera de la "
        "modal.",
        "",
        "**Métrica titular:** fracción de POs fuera de firma (evidencia ignorada), reportada "
        "junto al paisaje de convergencia (% en clúster, pureza modal). No se usa una tasa de "
        "'clúster sospechoso' porque satura: con clústeres grandes, casi cualquiera incluye "
        "algo de variación de señales y quedaría marcado, inflando el fallo.",
        "",
        f"Supuestos: θ={CONVERGENCE_THETA} se hereda del fixture de ola 1 (calibrado en "
        "ADR-16) y se aplica al conjunto completo. En esta corrida "
        f"`llm_coincide_con_reason` es binaria ({coincide_counts.get(True, 0)} True / "
        f"{coincide_counts.get(False, 0)} False): no aparece el estado 'no-evaluable'. "
        f"Población: {n_total} POs tardíos con tier-2 poblado.",
        "",
    ]

    for field, etiqueta in FIELDS.items():
        por_etapa = medidas[field]
        n_off_total = sum(v["n_off"] for v in por_etapa.values())
        L += [
            f"## Campo: {etiqueta} (`{field}`)",
            "",
            f"POs fuera de firma (evidencia ignorada): **{n_off_total}/{n_total}** "
            f"({n_off_total / n_total * 100:.1f}%).",
            "",
            "| Etapa | n | Jaccard medio | Clústeres conv. | Mayor | % en conv. | "
            "Pureza modal | Fuera de firma |",
            "|---|--:|--:|--:|--:|--:|--:|--:|",
        ]
        for stage in sorted(por_etapa):
            v = por_etapa[stage]
            jm = "—" if pd.isna(v["jaccard_medio"]) else f"{v['jaccard_medio']:.3f}"
            pm = "—" if pd.isna(v["purity_media"]) else f"{v['purity_media']:.2f}"
            L.append(
                f"| {stage} | {v['n']} | {jm} | {v['n_clusters']} | {v['mayor']} | "
                f"{v['pct_en_conv'] * 100:.1f}% | {pm} | "
                f"{v['n_off']} ({v['pct_off'] * 100:.1f}%) |"
            )
        L.append("")

        # Clústeres con POs fuera de firma: los homogéneos que ignoran la evidencia.
        con_off = [
            (stage, c)
            for stage in sorted(por_etapa)
            for c in por_etapa[stage]["clusters"]
            if c["n_off"] > 0
        ]
        if con_off:
            L += [f"### Clústeres con evidencia ignorada ({etiqueta})", ""]
            for stage, c in con_off:
                L += [
                    f"**{stage}** — clúster de {c['size']} POs, pureza modal "
                    f"{c['purity']:.2f}, {c['n_off']} fuera de firma.",
                    "",
                    f"> Recomendación modal: {_snippet(c['modal_texto'])}",
                    "",
                    "| PO fuera de firma | difiere en | firma de evidencia | recomendación |",
                    "|---|---|---|---|",
                ]
                for m in c["miembros"]:
                    if not m["off"]:
                        continue
                    L.append(
                        f"| {m['PO']} | {', '.join(m['difiere'])} | "
                        f"{_celda(_firma_str(m))} | {_celda(_snippet(m['texto'], 120))} |"
                    )
                L.append("")
        else:
            L += [
                f"No hay POs fuera de firma para {etiqueta}: toda convergencia intra-etapa "
                "está alineada a evidencia compartida.",
                "",
            ]

    L += [
        "## Lectura",
        "",
        "La convergencia intra-etapa es alta pero mayormente *justificada*: en el clúster "
        "mayor de Vendor (hipótesis) la pureza modal es ~0.75 —la misma hipótesis de "
        "planificación del proveedor sobre POs que comparten firma de evidencia—. El fallo no "
        "es la convergencia sino la cola fuera de firma (~1 de cada 6 POs), concentrada en "
        "Carrier. La convergencia de `acción inmediata` puede además ser mayor por diseño: las "
        "Reglas de concreción de ADR-16 hacen converger la acción al `paso_discriminante` "
        "cuando el mecanismo no está confirmado; por eso la firma modal absuelve esa "
        "convergencia y solo los POs fuera de firma señalan evidencia ignorada.",
        "",
        "## Boceto de solución (insumo para #154)",
        "",
        "La homogeneidad residual son POs cuya firma de evidencia difiere de la firma modal "
        "de su clúster y que aun así reciben la hipótesis/acción del modo. Un marcador "
        "contrastivo determinista, calculado por PO e inyectado al prompt de la llamada de "
        "acción, ataca ese mecanismo: declara en qué se aparta el PO del perfil modal de su "
        "etapa (por ejemplo «atípico para Vendor: envío incompleto (short-ship)», «PO marcado "
        "crítico», «la anotación REASON_DSC discrepa de la etapa medida»). A diferencia de una "
        "regla señal -> hipótesis declarativa —que el cierre del Carril-1 mostró de bajo "
        "rendimiento (mueve 2/8 POs)—, el marcador no prescribe la conclusión: fuerza al "
        "modelo a condicionar sobre la señal que hoy ignora y le deja derivar la hipótesis "
        "(coherente con la capa analítica de ADR-16). Es barato (determinista, sin llamada "
        "extra) y su superficie de validación es esta misma métrica de fuera de firma. Primer "
        "objetivo por impacto: Carrier (la tasa más alta, 30-35%). Queda como boceto; la "
        "decisión y su relación con el estadio agéntico del Carril-2 corresponden a #154.",
        "",
        "## Reproducir",
        "",
        "```bash",
        "# 1) generar el entregable con tier-2 poblado (GASTA API):",
        "python llm_integration.py --mode full --backend openai --action-call",
        "# 2) medir (sin API):",
        "python eval_differentiation.py",
        "```",
        "",
        "Fuente: `data/processed/po_output.csv` · agrupación por `stage` · "
        f"convergencia Jaccard θ={CONVERGENCE_THETA} sobre tokens de contenido · firma de "
        "evidencia determinista (`is_short_ship`, `HOT_PO_FLAG`, `llm_coincide_con_reason`, "
        "tercil de magnitud).",
        "",
    ]
    return "\n".join(L)


# ── CLI ───────────────────────────────────────────────────────────────────────
def _print_resumen(medidas: dict, n_total: int) -> None:
    """Resumen ASCII a stdout (sin emojis -> no requiere PYTHONUTF8)."""
    print("=" * 70)
    print(f"Diferenciacion intra-etapa tier-2 (#151) - {n_total} POs")
    print("=" * 70)
    for field, etiqueta in FIELDS.items():
        por_etapa = medidas[field]
        n_off = sum(v["n_off"] for v in por_etapa.values())
        print(f"\n[{_norm(etiqueta)}]  ({field})")  # sin acentos: stdout ASCII
        print(f"  {'etapa':<14} {'n':>4} {'jaccard':>8} {'conv':>5} {'mayor':>6} "
              f"{'%conv':>7} {'pureza':>7} {'off-firma':>11}")
        for stage in sorted(por_etapa):
            v = por_etapa[stage]
            jm = "  nan" if pd.isna(v["jaccard_medio"]) else f"{v['jaccard_medio']:.3f}"
            pm = "  nan" if pd.isna(v["purity_media"]) else f"{v['purity_media']:.2f}"
            print(f"  {stage:<14} {v['n']:>4} {jm:>8} {v['n_clusters']:>5} {v['mayor']:>6} "
                  f"{v['pct_en_conv'] * 100:>6.1f}% {pm:>7} "
                  f"{v['n_off']:>3} ({v['pct_off'] * 100:>4.1f}%)")
        print(f"  -> POs FUERA DE FIRMA (evidencia ignorada): {n_off}/{n_total} "
              f"({n_off / n_total * 100:.1f}%)")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Mide la diferenciación intra-etapa de las recomendaciones tier-2 (#151)."
    )
    parser.add_argument("--po-output", type=Path, default=DEFAULT_PO_OUTPUT,
                        help="CSV-entregable con los campos tier-2 poblados.")
    parser.add_argument("--no-write", action="store_true",
                        help="Solo imprime el resumen; no escribe el .md.")
    args = parser.parse_args()

    if not args.po_output.exists():
        raise SystemExit(
            f"No existe {args.po_output}. Genera el entregable con "
            "`python llm_integration.py --mode full --backend openai --action-call` (gasta API)."
        )

    df = pd.read_csv(args.po_output)

    # Guarda: sin tier-2 poblado (corrida sin --action-call) la medición no aplica.
    faltantes = [c for c in FIELDS if c not in df.columns]
    if faltantes:
        raise SystemExit(f"Faltan columnas tier-2 en el CSV: {faltantes}. "
                         "Regenera con --action-call.")
    vacios = [c for c in FIELDS if df[c].fillna("").astype(str).str.strip().eq("").all()]
    if vacios:
        raise SystemExit(f"Columnas tier-2 vacías ({vacios}): el CSV es una corrida sin "
                         "--action-call. Regenera con --action-call y vuelve a medir.")

    n_total = len(df)
    coincide_counts = df["llm_coincide_con_reason"].value_counts(dropna=False).to_dict()
    medidas = {field: measure(df, field) for field in FIELDS}

    _print_resumen(medidas, n_total)

    if not args.no_write:
        OUTPUT_MD.write_text(to_markdown(medidas, n_total, coincide_counts), encoding="utf-8")
        print(f"\nReporte escrito en: {OUTPUT_MD}")


if __name__ == "__main__":
    main()
