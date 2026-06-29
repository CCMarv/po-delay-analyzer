#!/usr/bin/env python3
"""
eval_mismatches.py — Pasada zero-shot de los 8 mismatches de F2 (#99 → insumo de #95).

Corre el prompt zero-shot (alineado a #91) sobre los 8 mismatches más fuertes que F2
identificó con `metrics_core.select_mismatches` (donde la clasificación por timestamps
discrepa del REASON_DSC humano). Persiste la explicación del LLM por PO como artefacto que
#95 reusa SIN volver a llamar a la API: es la evidencia de que el cómputo supera a la
anotación humana, narrada en el documento de mismatches.

Estos 8 POs son el pool de ejemplos few-shot de #99, pero esta pasada NO los usa como
ejemplos: los pasa como ENTRADA (zero-shot) para capturar qué explica el LLM sobre ellos.

Uso:
    # Mostrar los 8 mismatches sin llamar a la API:
    python eval_mismatches.py --dry-run

    # Correr los 8 por el LLM (8 llamadas reales) y escribir el artefacto:
    python eval_mismatches.py --backend openai
"""

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "02_clasif_reglas_negocio"))
from llm_integration import build_prompt, create_backend, prepare_classified_df  # noqa: E402
from metrics_core import select_mismatches  # noqa: E402

N_MISMATCHES = 8
# Fixture de evidencia (corrida congelada, insumo de #95): versionado, no output efímero.
OUTPUT_CSV = Path(__file__).resolve().parent / "fixtures" / "mismatches_llm_zeroshot.csv"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Pasada zero-shot de los 8 mismatches (#99 → #95)")
    parser.add_argument("--backend", default="openai",
                        choices=["local", "claude", "deepseek", "openai"])
    parser.add_argument("--dry-run", action="store_true",
                        help="Mostrar los 8 mismatches sin llamar a la API.")
    args = parser.parse_args()

    df = prepare_classified_df(from_csv=False)
    # Estratificado: que la narración de #95 cubra las tres etapas, no solo Vendor (que
    # domina el ranking por señal). El más fuerte de cada etapa, hasta N_MISMATCHES.
    mis = select_mismatches(df, n=N_MISMATCHES, stratify=True)

    print(f"Mismatches estratificados (n={N_MISMATCHES}, de select_mismatches):")
    cols_show = ["PO_NBR", "stage_primary", "reason_group_manual", "REASON_DSC",
                 "senal_computo_hrs", "delay_days_calc"]
    cols_show = [c for c in cols_show if c in mis.columns]
    print(mis[cols_show].to_string(index=False))

    if args.dry_run:
        print("\n(dry-run: no se llamó a la API.)")
        return

    # Para armar el prompt completo se necesita la fila ORIGINAL del df (todas las columnas
    # que build_prompt lee), no solo las que select_mismatches devuelve.
    backend = create_backend(backend_type=args.backend)
    print(f"\nCorriendo {len(mis)} mismatches por el LLM zero-shot ({args.backend})...")

    filas = []
    for po in mis["PO_NBR"]:
        row = df[df["PO_NBR"] == po].iloc[0]
        resp = backend.call(build_prompt(row)) or {}   # zero-shot: sin examples
        filas.append({
            "PO_NBR": po,
            "stage_primary": row["stage_primary"],
            "reason_group_manual": row.get("reason_group_manual", ""),
            "REASON_DSC": row.get("REASON_DSC", ""),
            "senal_computo_hrs": round(float(
                mis.loc[mis["PO_NBR"] == po, "senal_computo_hrs"].iloc[0]), 1),
            "delay_days_calc": round(float(row["delay_days_calc"]), 2),
            "llm_causa_raiz": resp.get("causa_raiz", ""),
            "llm_accion_recomendada": resp.get("accion_recomendada", ""),
            "llm_coincide_con_reason": resp.get("coincide_con_reason_code", False),
        })

    out = pd.DataFrame(filas)
    out.to_csv(OUTPUT_CSV, index=False, encoding="utf-8")
    print(f"\nArtefacto escrito en: {OUTPUT_CSV} ({len(out)} mismatches)")
    print("Insumo de #95 (narración de mismatches AI vs humano), sin re-gastar API.")


if __name__ == "__main__":
    main()
