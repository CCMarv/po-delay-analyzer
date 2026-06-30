#!/usr/bin/env python3
"""
eval_diversity.py — Analizador OFFLINE de diversidad de las acciones del LLM.

No llama a ninguna API: lee los fixtures .md que ya produjo `eval_quality.py` y mide
qué tan homogéneas son las acciones recomendadas (la columna "acción LLM" de la tabla).
La homogeneidad de redacción —acciones casi calcadas entre POs de estructura similar—
se concentra en las acciones de etapa Vendor; este script la cuantifica para sostener
con un número la observación cualitativa de #94/#143 y servir de evidencia al barrido de
temperatura (ADR-13 / #137).

Métrica (una por conjunto de acciones):
    diversidad = 1 − similitud_media_por_pares
donde la similitud de dos acciones es el índice de Jaccard sobre sus CONJUNTOS de
tokens. Tokenizar = minúsculas + separar por caracteres no alfanuméricos + descartar
vacíos. Para n acciones se promedia la Jaccard de las C(n,2) parejas. Diversidad alta
(→1) = acciones distintas entre sí; baja (→0) = acciones casi idénticas.

La métrica se reporta DOS veces por fixture: sobre TODAS las acciones y sobre el
SUBCONJUNTO VENDOR (las acciones cuya etapa verdadera —columna "etapa", que es
stage_primary— es Vendor). También se cuenta cuántas acciones DISTINTAS hay tras una
normalización ligera (minúsculas + colapsar espacios + quitar puntuación de borde).

Casos borde: un conjunto con menos de 2 acciones no tiene diversidad definida (no hay
parejas) → se devuelve None y se muestra como "n/a", sin reventar.

Uso:
    # Tabla comparativa del barrido C3 (los 4 fixtures por defecto):
    python eval_diversity.py

    # Sobrescribir las rutas de los fixtures (se resuelven relativas a 03_llm_integration/):
    python eval_diversity.py fixtures/eval_quality_20pos_C3.md fixtures/otro.md
"""

import argparse
import re
import statistics
from itertools import combinations
from pathlib import Path
from typing import Optional

# ── Nombres de columnas de la tabla del fixture (por encabezado, no por índice) ──
# La tabla la arma eval_quality.to_markdown(); ahí la acción sale de r['llm_accion']
# bajo el encabezado "acción LLM", y la etapa verdadera de r['stage_primary'] bajo
# "etapa". El subconjunto Vendor se filtra por la etapa VERDADERA, no por la que el
# LLM reporte dentro del texto.
COL_ACCION = "acción LLM"
COL_ETAPA = "etapa"
VENDOR_LABEL = "vendor"

# Barrido C3 por defecto (rutas relativas a 03_llm_integration/, como eval_quality.py).
DEFAULT_FIXTURES = {
    0.3: "fixtures/eval_quality_20pos_C3.md",
    0.5: "fixtures/eval_quality_20pos_C3_t05.md",
    0.7: "fixtures/eval_quality_20pos_C3_t07.md",
    0.9: "fixtures/eval_quality_20pos_C3_t09.md",
}

# Directorio del script: las rutas de fixtures se resuelven relativas a aquí.
_HERE = Path(__file__).resolve().parent

# Separa una fila Markdown por pipes NO escapados (un '\|' dentro de una celda no parte).
_PIPE = re.compile(r"(?<!\\)\|")
# Tokenizador: corta por todo lo que no sea alfanumérico (incluye acentos/ñ del español).
_NON_ALNUM = re.compile(r"[^0-9a-záéíóúüñ]+")


# ════════════════════════════════════════════════════════════════════════════
# A. Tokenización y similitud
# ════════════════════════════════════════════════════════════════════════════
def tokenize(text: str) -> set:
    """Conjunto de tokens de un texto: minúsculas, cortado por no-alfanuméricos,
    sin vacíos. Es la base de la Jaccard."""
    return {t for t in _NON_ALNUM.split(text.lower()) if t}


def jaccard(a: set, b: set) -> float:
    """Índice de Jaccard |A∩B| / |A∪B| sobre dos conjuntos de tokens.

    Dos textos sin tokens (ambos vacíos) se consideran idénticos (similitud 1.0):
    la unión vacía no define el cociente, pero dos acciones vacías no aportan
    diversidad, así que tratarlas como iguales es lo conservador.
    """
    union = a | b
    if not union:
        return 1.0
    return len(a & b) / len(union)


def mean_pairwise_similarity(actions: list) -> Optional[float]:
    """Promedio de la Jaccard sobre las C(n,2) parejas de acciones.

    Devuelve None si hay menos de 2 acciones (no hay parejas → similitud, y por
    tanto diversidad, indefinida).
    """
    if len(actions) < 2:
        return None
    token_sets = [tokenize(a) for a in actions]
    sims = [jaccard(x, y) for x, y in combinations(token_sets, 2)]
    return statistics.mean(sims)


def diversity(actions: list) -> Optional[float]:
    """Diversidad = 1 − similitud_media_por_pares. None si <2 acciones."""
    sim = mean_pairwise_similarity(actions)
    if sim is None:
        return None
    return 1.0 - sim


# ════════════════════════════════════════════════════════════════════════════
# B. Conteo de acciones distintas (normalización ligera)
# ════════════════════════════════════════════════════════════════════════════
def normalize_light(text: str) -> str:
    """Normalización ligera para contar distintas: minúsculas, colapsa espacios
    internos y quita puntuación/espacios de los bordes. NO toca la puntuación
    interna (dos acciones que solo difieren en una coma siguen contando como dos)."""
    t = re.sub(r"\s+", " ", text.lower()).strip()
    return t.strip(".,;:!¡¿?\"'()[]- ")


def count_distinct(actions: list) -> int:
    """Cuántas acciones distintas hay tras normalize_light."""
    return len({normalize_light(a) for a in actions})


# ════════════════════════════════════════════════════════════════════════════
# C. Parser del fixture (localiza columnas por NOMBRE de encabezado)
# ════════════════════════════════════════════════════════════════════════════
def _split_row(line: str) -> list:
    """Parte una fila Markdown en celdas: corta por pipes no escapados, recorta
    los bordes vacíos que dejan los pipes externos, des-escapa '\\|' → '|' y trim."""
    parts = _PIPE.split(line.strip())
    # Una fila '| a | b |' deja '' en los extremos tras el split: se descartan.
    if parts and parts[0].strip() == "":
        parts = parts[1:]
    if parts and parts[-1].strip() == "":
        parts = parts[:-1]
    return [p.replace("\\|", "|").strip() for p in parts]


def _is_separator(cells: list) -> bool:
    """¿Es la fila separadora del header? (solo guiones, dos puntos y espacios)."""
    return bool(cells) and all(set(c) <= set("-: ") and c for c in cells)


def parse_fixture_text(text: str) -> list:
    """Extrae las filas de la tabla como dicts {etapa, accion} localizando las
    columnas POR NOMBRE de encabezado (robusto al orden de columnas).

    Estrategia: recorre las líneas; la primera fila que empieza por '|' y contiene
    los encabezados buscados es el header → fija el mapa nombre→índice. Las filas
    siguientes que empiezan por '|' (saltando la separadora '---') son datos.
    """
    rows = []
    header_map = None
    for raw in text.splitlines():
        line = raw.strip()
        if not line.startswith("|"):
            # Una línea sin pipe inicial corta la tabla en curso (p. ej. el header
            # ya pasó y empieza la sección de Resultado). Solo importa si ya teníamos
            # header; mientras no, seguimos buscando.
            if header_map is not None:
                break
            continue
        cells = _split_row(line)
        if header_map is None:
            # ¿Este header tiene las columnas que necesitamos?
            idx = {name: i for i, name in enumerate(cells)}
            if COL_ACCION in idx and COL_ETAPA in idx:
                header_map = idx
            continue
        if _is_separator(cells):
            continue
        i_accion = header_map[COL_ACCION]
        i_etapa = header_map[COL_ETAPA]
        if max(i_accion, i_etapa) >= len(cells):
            continue  # fila malformada / corta: se ignora, no revienta
        rows.append({
            "etapa": cells[i_etapa],
            "accion": cells[i_accion],
        })
    if header_map is None:
        raise ValueError(
            f"No se encontró una tabla con las columnas {COL_ETAPA!r} y {COL_ACCION!r}."
        )
    return rows


def parse_fixture_file(path: Path) -> list:
    """Lee un .md y devuelve las filas {etapa, accion}."""
    return parse_fixture_text(path.read_text(encoding="utf-8"))


# ════════════════════════════════════════════════════════════════════════════
# D. Métricas por fixture
# ════════════════════════════════════════════════════════════════════════════
def analyze_rows(rows: list) -> dict:
    """Calcula diversidad y distintas sobre el set completo y sobre el subconjunto
    Vendor (etapa verdadera == 'Vendor', insensible a may/min)."""
    all_actions = [r["accion"] for r in rows]
    vendor_actions = [
        r["accion"] for r in rows if r["etapa"].strip().lower() == VENDOR_LABEL
    ]
    return {
        "n_all": len(all_actions),
        "n_vendor": len(vendor_actions),
        "div_all": diversity(all_actions),
        "div_vendor": diversity(vendor_actions),
        "distinct_all": count_distinct(all_actions),
        "distinct_vendor": count_distinct(vendor_actions),
    }


# ════════════════════════════════════════════════════════════════════════════
# E. Salida — tabla comparativa
# ════════════════════════════════════════════════════════════════════════════
def _fmt_div(value: Optional[float]) -> str:
    """Formatea una diversidad: 3 decimales o 'n/a' si es None (<2 acciones)."""
    return "n/a" if value is None else f"{value:.3f}"


def build_comparison_table(results: list) -> str:
    """Arma la tabla comparativa (una fila por temperatura) como texto plano.

    `results` es una lista de tuplas (temperatura, metrics_dict).
    """
    header = (
        f"{'temp':>5} | {'div(set)':>8} | {'div(Vendor)':>11} | "
        f"{'dist(set)':>9} | {'dist(Vendor)':>12} | {'n':>3} | {'n_vendor':>8}"
    )
    sep = "-" * len(header)
    lines = [header, sep]
    for temp, m in results:
        lines.append(
            f"{temp:>5} | {_fmt_div(m['div_all']):>8} | {_fmt_div(m['div_vendor']):>11} | "
            f"{m['distinct_all']:>9} | {m['distinct_vendor']:>12} | "
            f"{m['n_all']:>3} | {m['n_vendor']:>8}"
        )
    return "\n".join(lines)


# ════════════════════════════════════════════════════════════════════════════
# F. CLI
# ════════════════════════════════════════════════════════════════════════════
def _resolve(path_str: str) -> Path:
    """Resuelve una ruta relativa a 03_llm_integration/ (donde vive el script)."""
    p = Path(path_str)
    return p if p.is_absolute() else (_HERE / p)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analizador OFFLINE de diversidad de acciones del LLM (barrido C3)."
    )
    parser.add_argument(
        "fixtures", nargs="*",
        help="Rutas de fixtures .md a analizar (relativas a 03_llm_integration/). "
             "Si se omite, usa el barrido C3 por defecto (t=0.3/0.5/0.7/0.9).",
    )
    args = parser.parse_args()

    # (temperatura, ruta): si el usuario pasa rutas, la 'temperatura' es solo un
    # ordinal de etiqueta (no se infiere del nombre); con el default sí es la temp real.
    if args.fixtures:
        targets = [(i + 1, fx) for i, fx in enumerate(args.fixtures)]
    else:
        targets = list(DEFAULT_FIXTURES.items())

    results = []
    for label, fx in targets:
        path = _resolve(fx)
        if not path.exists():
            print(f"[saltado] no existe: {path}")
            continue
        rows = parse_fixture_file(path)
        results.append((label, analyze_rows(rows)))

    if not results:
        print("No se analizó ningún fixture (ninguna ruta existe).")
        return

    print(build_comparison_table(results))


if __name__ == "__main__":
    main()
