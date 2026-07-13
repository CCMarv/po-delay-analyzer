#!/usr/bin/env python3
"""
eval_severity_ranking.py — Métrica *Severity Ranking* del mentor (#98, README §6).

Mide, sobre el output OFICIAL del entregable, qué porcentaje de los POs con
`HOT_PO_FLAG == 1` y `delay_days_calc > 3` tienen `severity == HIGH`, y lo contrasta
con el umbral del mentor (**>95%**).

Qué columna se mide y por qué (reconciliación de #98):
    La `severity` oficial del CSV-entregable es la que EMITE el LLM
    (`severity` ← `llm_severidad`), no la determinística de Fase 2 — decisión registrada
    en ADR-10 (Opción C, VIGENTE) y en el contrato del README (§ "Salida"). El cuerpo de
    #98/#92 asumía la determinística ("Opción A", cumplimiento "por construcción"); ese
    encuadre quedó obsoleto tras ADR-10. Por eso esta medición es EMPÍRICA: valida si el
    LLM RESPETÓ la regla `hot & delay>3 ⇒ HIGH`, no la da por sentada. Puede dar <100%.

Como referencia se reporta al lado el baseline DETERMINÍSTICO (columna de auditoría de F2,
`data/processed/df_classified.csv`): el mismo filtro da HIGH por construcción, y el contraste
LLM-vs-regla materializa el "dónde el LLM discrepa de la regla" de ADR-10.

Reproducible y SIN API: solo LEE CSVs ya generados. El `po_output.csv` con la severidad del
LLM poblada se genera aparte (gasta API), con el backend oficial:

    python llm_integration.py --mode full --backend openai

Uso:
    python eval_severity_ranking.py
    python eval_severity_ranking.py --po-output ../data/processed/po_output.csv
"""

import argparse
from pathlib import Path

import pandas as pd

# Rutas por defecto, resueltas desde la raíz del repo igual que llm_integration.py, para
# que el script corra desde cualquier CWD.
REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PO_OUTPUT = REPO_ROOT / "data" / "processed" / "po_output.csv"
DEFAULT_CLASSIFIED = REPO_ROOT / "data" / "processed" / "df_classified.csv"

# Reporte versionado, junto al script (patrón de eval_quality.py). El número vive aquí, NO
# en un CSV de datos (que va gitignored).
OUTPUT_MD = Path(__file__).resolve().parent / "eval_severity_ranking.md"

# Definición de la métrica (README §6). Filtro EXPLÍCITO del mentor/#98 — no la bandera
# derivada `flag_hot_late` de F2, que cubre un conjunto distinto (ver nota de validación
# en el reporte). El umbral es estricto (">95%").
DELAY_DAYS_MIN = 3.0
THRESHOLD = 0.95


def hot_late(df: pd.DataFrame) -> pd.DataFrame:
    """Subconjunto de la métrica: POs con HOT_PO_FLAG==1 y delay_days_calc > 3 (el
    denominador). Es el filtro literal del README §6 y de #98."""
    return df[(df["HOT_PO_FLAG"] == 1) & (df["delay_days_calc"] > DELAY_DAYS_MIN)].copy()


def _is_high(serie: pd.Series) -> pd.Series:
    """True donde la severidad es HIGH, robusto a espacios/caso. NaN → no-HIGH."""
    return serie.astype(str).str.strip().str.upper().eq("HIGH")


def measure(df_hot: pd.DataFrame, sev_col: str = "severity") -> dict:
    """Mide el Severity Ranking sobre un subconjunto hot+late ya filtrado.

    Returns un dict con el conteo, el %, el veredicto vs el umbral, cuántos POs quedaron
    sin severidad poblada (señal de corrida incompleta) y los POs que NO son HIGH.
    """
    n_total = len(df_hot)
    n_missing = int(df_hot[sev_col].isna().sum())
    is_high = _is_high(df_hot[sev_col])
    n_high = int(is_high.sum())
    pct = (n_high / n_total) if n_total else 0.0
    return {
        "n_total": n_total,
        "n_high": n_high,
        "n_missing": n_missing,
        "pct": pct,
        "pass": pct > THRESHOLD,
        "no_high": df_hot[~is_high],  # incumplidores (incl. NaN si los hubiera)
    }


def _celda(texto) -> str:
    """Texto seguro para una celda de tabla markdown (sin | ni saltos de línea)."""
    return str(texto).replace("|", "\\|").replace("\n", " ")


def _snippet(texto, n: int = 140) -> str:
    """Recorte corto de una explicación para la tabla de incumplidores."""
    s = str(texto).replace("\n", " ").strip()
    return s if len(s) <= n else s[: n - 1] + "…"


def to_markdown(oficial: dict, df_hot: pd.DataFrame, audit: dict,
                n_pop_missing: int) -> str:
    """Arma el reporte .md: definición, resultado oficial (LLM), baseline determinístico,
    discrepancia LLM-vs-regla y cómo reproducir."""
    pct_txt = f"{oficial['pct'] * 100:.1f}%"
    veredicto = "✅ CUMPLE" if oficial["pass"] else "❌ NO CUMPLE"
    lineas = [
        "# Severity Ranking sobre el output del entregable (#98)",
        "",
        "Métrica del mentor (README §6): los POs con `HOT_PO_FLAG=1` y `delay_days_calc > 3` "
        "deben tener `severity=HIGH` en **>95%** de los casos.",
        "",
        "Columna medida: `severity` del entregable (`po_output.csv`), que **es la del LLM** "
        "(`severity ← llm_severidad`, [ADR-10](../documentation/decisiones/ARD-10.md), Opción C). "
        "La medición es **empírica**: valida si el LLM respetó `hot & delay>3 ⇒ HIGH`.",
        "",
        "## Resultado oficial (severidad del LLM)",
        "",
        f"- POs hot + delay>3 (denominador): **{oficial['n_total']}**",
        f"- De ellos con `severity=HIGH`: **{oficial['n_high']}**",
        f"- **Severity Ranking = {pct_txt}**  (umbral del mentor >95%) → **{veredicto}**",
    ]
    if oficial["n_missing"]:
        lineas.append(
            f"- ⚠️ **{oficial['n_missing']} PO(s) sin `severity` poblada**: el `po_output.csv` "
            "NO es una corrida completa. Regenera con `--mode full --backend openai` y vuelve a "
            "medir; el número de arriba no es válido hasta que esto sea 0."
        )
    lineas += [
        "",
        f"> Granularidad: con {oficial['n_total']} POs en el denominador, un solo PO no-HIGH "
        f"baja la métrica a {(oficial['n_total'] - 1) / oficial['n_total'] * 100:.1f}%, ya por "
        "debajo del 95%. El umbral es, en la práctica, todos-HIGH.",
        "",
    ]
    # Incumplidores (si los hay): PO, severidad emitida, delay y explicación.
    no_high = oficial["no_high"]
    if len(no_high):
        lineas += [
            "### POs que no cumplen (`severity != HIGH`)",
            "",
            "| PO | severity (LLM) | delay (d) | explicación (LLM) |",
            "|---|---|--:|---|",
        ]
        for _, r in no_high.iterrows():
            sev = r["severity"] if pd.notna(r["severity"]) else "_(sin poblar)_"
            lineas.append(
                f"| {r['PO_NBR']} | {_celda(sev)} | {float(r['delay_days_calc']):.2f} | "
                f"{_celda(_snippet(r.get('explanation', '')))} |"
            )
        lineas.append("")
    else:
        lineas += ["Todos los POs del denominador son HIGH: no hay incumplidores.", ""]

    # Baseline determinístico (columna de auditoría de F2) y discrepancia.
    lineas += [
        "## Referencia: baseline determinístico (columna de auditoría F2)",
        "",
        "La regla determinística de F2 (`flag_hot_late & delay>3 ⇒ HIGH`) asigna HIGH **por "
        "construcción**; se conserva como auditoría (ADR-10) y es la referencia contra la que "
        "se mide al LLM.",
        "",
        f"- POs hot + delay>3 en `df_classified.csv`: **{audit['n_total']}**",
        f"- Con `severity=HIGH` (determinística): **{audit['n_high']}** "
        f"({audit['pct'] * 100:.1f}%, por construcción)",
    ]
    if audit["n_total"] != oficial["n_total"]:
        lineas.append(
            f"- ⚠️ El conteo del denominador difiere entre CSVs "
            f"({oficial['n_total']} en po_output vs {audit['n_total']} en df_classified): "
            "revisar el alcance de filas antes de interpretar."
        )
    lineas += [
        "",
        "> Nota de validación: `flag_hot_late` (bandera de F2) cubre un conjunto más amplio "
        "que el filtro explícito `HOT_PO_FLAG==1 & delay_days_calc>3` de esta métrica. Aquí se "
        "usa el filtro explícito del README §6, no la bandera.",
        "",
        "## Reproducir",
        "",
        "```bash",
        "# 1) generar el entregable con la severidad del LLM (GASTA API, ~247 llamadas):",
        "python llm_integration.py --mode full --backend openai",
        "# 2) medir (sin API):",
        "python eval_severity_ranking.py",
        "```",
        "",
        "Fuente: `data/processed/po_output.csv` (severidad oficial = LLM) · filtro "
        "`HOT_PO_FLAG==1 & delay_days_calc>3` · numerador `severity=='HIGH'`. Baseline de "
        "auditoría: `data/processed/df_classified.csv` (severidad determinística de F2).",
        "",
    ]
    return "\n".join(lineas)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Mide el Severity Ranking del mentor sobre el entregable (#98)."
    )
    parser.add_argument("--po-output", type=Path, default=DEFAULT_PO_OUTPUT,
                        help="CSV-entregable con la severidad oficial (del LLM).")
    parser.add_argument("--classified", type=Path, default=DEFAULT_CLASSIFIED,
                        help="CSV clasificado de F2 (severidad determinística de auditoría).")
    parser.add_argument("--no-write", action="store_true",
                        help="Solo imprime el resumen; no escribe el .md.")
    args = parser.parse_args()

    if not args.po_output.exists():
        raise SystemExit(
            f"❌ No existe {args.po_output}. Genera el entregable con "
            "`python llm_integration.py --mode full --backend openai` (gasta API)."
        )

    df_out = pd.read_csv(args.po_output)
    df_hot = hot_late(df_out)
    oficial = measure(df_hot, sev_col="severity")

    # Baseline determinístico (auditoría). Si el CSV no está, se sigue sin baseline.
    if args.classified.exists():
        df_cls = pd.read_csv(args.classified)
        audit = measure(hot_late(df_cls), sev_col="severity")
    else:
        audit = {"n_total": 0, "n_high": 0, "n_missing": 0, "pct": 0.0,
                 "pass": False, "no_high": df_hot.iloc[0:0]}

    # Resumen a stdout.
    print("=" * 60)
    print("Severity Ranking del entregable (#98) — columna oficial: LLM")
    print("=" * 60)
    print(f"Denominador (hot + delay>3): {oficial['n_total']} POs")
    print(f"HIGH (severidad del LLM)   : {oficial['n_high']}")
    print(f"Severity Ranking           : {oficial['pct'] * 100:.1f}%  "
          f"(umbral >95% → {'CUMPLE' if oficial['pass'] else 'NO CUMPLE'})")
    if oficial["n_missing"]:
        print(f"⚠️  {oficial['n_missing']} PO(s) SIN severidad poblada: "
              "el output es una corrida incompleta (test). Regenera con --mode full.")
    print(f"Baseline determinístico    : {audit['n_high']}/{audit['n_total']} HIGH "
          "(por construcción)")

    if not args.no_write:
        OUTPUT_MD.write_text(to_markdown(oficial, df_hot, audit, oficial["n_missing"]),
                             encoding="utf-8")
        print(f"\nReporte escrito en: {OUTPUT_MD}")


if __name__ == "__main__":
    main()
