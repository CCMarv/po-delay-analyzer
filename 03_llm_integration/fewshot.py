#!/usr/bin/env python3
"""
fewshot.py — Pool auditado de ejemplos few-shot y su selección (#99 / ADR-12).

Los ejemplos que enseñan el razonamiento al LLM son material calificable: cada uno se
audita (coherencia reason↔acción de la acción ideal, manejo neutral de is_rescheduled,
cifras citadas correctas). Por eso viven como DATO versionado en `fewshot_pool.json`
—revisable en PRs sin leer Python— y este módulo solo los carga y selecciona.

Selección ESTÁTICA (alcance de #99): `select_examples(n)` devuelve N ejemplos fijos en
orden determinista (por `po_origen`), de modo que C1/C2/C3 del benchmark son reproducibles:
los ejemplos que gana el benchmark son exactamente los que usa producción, sin una regla
dinámica que pudiera derivar entre una corrida y otra. (La *cifra* de calidad sí se
re-validó después a otra temperatura —ADR-13— pero la selección de ejemplos no cambió; ver
`../documentation/metricas-proyecto.md` para la progresión completa.) Mantener la selección
estática evita mezclar dos variables en la métrica (¿mejoró por los ejemplos o por una regla
de selección?).

FUTURO (fuera de #99, ver ADR-12): una `select_examples_for_po(row, pool, n)` DINÁMICA que
excluya `row.PO_NBR` del pool y elija por etapa/similitud al PO que se explica. Cambiaría
qué mide el benchmark (habría que validar la regla de selección, no un set fijo), por lo que
se difiere a un issue propio. Los metadatos `_meta.stage` / `_meta.tipo_mismatch` del pool
ya están para habilitarla sin re-trabajo.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

_POOL_PATH = Path(__file__).resolve().parent / "fewshot_pool.json"


def load_pool(path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Carga el pool auditado de ejemplos few-shot desde JSON.

    Args:
        path: Ruta al JSON del pool. Por defecto `fewshot_pool.json` junto a este módulo.

    Returns:
        Lista de ejemplos (dicts). Cada uno conserva su clave `_meta` (auditoría/selección
        futura); `build_prompt`/`_format_example` ignoran las claves que no consumen, así
        que `_meta` no estorba al armar el prompt.
    """
    pool_path = path or _POOL_PATH
    return json.loads(pool_path.read_text(encoding="utf-8"))


def select_examples(
    n: int,
    stages: Optional[List[str]] = None,
    pool: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """Selección estática y reproducible de N ejemplos para el benchmark de #99.

    El orden es determinista (por `_meta.po_origen`), de modo que `select_examples(k)`
    devuelve siempre el mismo conjunto: C1=select_examples(1), C2=select_examples(2),
    C3=select_examples(3, stages=["DC","Vendor","Carrier"]).

    Args:
        n: Número de ejemplos a devolver.
        stages: Si se da, fuerza diversidad de etapa — toma como mucho un ejemplo por etapa
            listada, en ese orden (p.ej. C3 = una de cada etapa para no sesgar). Si es None,
            toma los primeros `n` del orden determinista.
        pool: Pool ya cargado (para tests); por defecto se carga de `fewshot_pool.json`.

    Returns:
        Lista de hasta `n` ejemplos.

    Raises:
        ValueError: si se piden más ejemplos de los que el pool puede satisfacer.
    """
    ejemplos = pool if pool is not None else load_pool()
    ordenado = sorted(ejemplos, key=lambda e: e.get("_meta", {}).get("po_origen", 0))

    if stages is None:
        elegidos = ordenado[:n]
    else:
        # Un ejemplo por etapa, en el orden de `stages`, hasta completar n.
        elegidos = []
        for etapa in stages:
            if len(elegidos) >= n:
                break
            match = next((e for e in ordenado
                          if e.get("stage_primary") == etapa and e not in elegidos), None)
            if match is not None:
                elegidos.append(match)

    if len(elegidos) < n:
        raise ValueError(
            f"Se pidieron {n} ejemplos pero el pool/criterio solo aporta {len(elegidos)}."
        )
    return elegidos
