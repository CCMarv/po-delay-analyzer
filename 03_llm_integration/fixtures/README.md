# Fixtures — Fase 3

Registros de validación humana de los benchmarks de calidad de F3. No son fixtures de test
automatizado: los tests de F3 usan sus propios stubs, no estos archivos.

## Qué hay aquí

- `eval_quality_20pos_C1.md` / `_C2.md` / `_C3.md` — benchmark de calidad (#94) por
  configuración de few-shot (1/2/3 ejemplos), a la temperatura ancla (0.3). C3 ganó (ver
  [`../README.md`](../README.md#estado-del-few-shot)).
- `eval_quality_20pos_C3_t05.md` / `_t07.md` / `_t09.md` — re-validación de C3 a otras
  temperaturas (ADR-13); `_t09.md` es la re-validación a la temperatura real de producción
  (20/20, cifra titular del entregable).
- `eval_quality_20pos_C0_t09.md` — baseline zero-shot a temp 0.9 (comparación, no es la cifra
  de producción).
- `eval_quality_20pos_C0_t09_accion_*.md` — control de calidad del diagnóstico diferencial
  tier-2 (ARD-16), por oleada de iteración del prompt de acción; `_kb.md` es la variante con
  contexto de dominio condicional (ADR-15, superado).
- `archive/` — oleadas intermedias del control de calidad tier-2, superadas por la versión
  citada en README/ARD-16; se conservan por trazabilidad, no son la fuente vigente.
- `mismatches_llm_zeroshot.csv` — mismatches crudos del baseline zero-shot, insumo de
  [`../mismatches_ai_vs_humano.md`](../mismatches_ai_vs_humano.md).

Cada benchmark citado como fuente de una cifra vigente está enlazado desde
[`03_llm_integration/README.md`](../README.md), `documentation/metricas-proyecto.md` o el ARD
correspondiente (12/13/15/16); este índice solo orienta qué archivo es cuál, no reemplaza esas
referencias.
