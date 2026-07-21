# ADR-06b · Umbral propio de vendor: Configuración definitiva de 24h

* **Estatus:** 🟢 **VIGENTE** (Reemplaza al [ADR-06a · Umbral propio de vendor: Modelo inicial sin umbral](ARD-06a.md))
* **Contexto Técnico:** Cierre de Fase 2 / Análisis de Sensibilidad y Calibración
* **Referencias:** Consulta de Ronda 2 del mentor (2026-06-18), Discussion #57, Stack de PRs #62, #66 y #64

## Contexto y Problema
Tras detectar la asimetría de construcción del modelo inicial (detallada en el [ADR-06a](ARD-06a.md)), necesitábamos balancear el clasificador con un umbral simétrico para Vendor que eliminara los micro-retrasos insignificantes, pero sin alterar artificialmente la distribución real del negocio.

## Opciones Consideradas

### Opción 1: Implementar un umbral adaptativo mediante análisis de sensibilidad (Elegida)
Correr una malla de pruebas evaluando umbrales de 6, 12, 18, 24, 48 y 72 horas para identificar el comportamiento real de los datos crudos y su impacto en las asignaciones.
* **Pros:** Científicamente sustentado. Permite descubrir patrones de negocio ocultos y desacoplar la tolerancia en archivos de configuración centralizados.
* **Contras:** Exige un esfuerzo de desarrollo secundario para evaluar la sensibilidad del volumen de pedidos afectados.

## Decisión Definitiva
Elegimos la **Opción 1**. Tras ejecutar el análisis de sensibilidad sobre los 247 pedidos tardíos, se descubrió que la distribución del retraso de Vendor es **bimodal**: 12 POs se concentran en micro-retrasos (≤ 6h), 141 POs presentan demoras críticas (≥ 18h) y existe un **hueco vacío absoluto entre las 6h y las 18h**.

Se fijó de forma definitiva **`vendor_gap_hrs = 24h`** en el archivo **`rules_config.json` (v3)** debido a:
1. **Nivel de agregación natural del dato:** La variable planificada `STA_DT` se registra a medianoche sin desglose de horas. 24 horas representa un día calendario completo (la unidad real del problema).
2. **Robustez matemática:** Al caer exactamente dentro del hueco vacío de la distribución (6-18h), cualquier ajuste menor en el umbral no desestabiliza ni altera el reparto final.
3. **Respeto al dato:** El modelo reduce la atribución de Vendor al 53.0% (131 POs) de forma orgánica, cumpliendo la orden del mentor de no forzar un "20% de kickoff artificial".

El cálculo de la variable `_etapa_primaria` se normalizó a `max(0, push − 24)`, haciéndolo simétrico con los demás actores y liberando los cambios mediante el stack de PRs [#62](https://github.com/CCMarv/po-delay-analyzer/pull/62), [#66](https://github.com/CCMarv/po-delay-analyzer/pull/66) y [#64](https://github.com/CCMarv/po-delay-analyzer/pull/64).

## Consecuencias
* **Positivas:** Eliminación definitiva de la asimetría de construcción y alta estabilidad del pipeline. Se comprobó que endurecer el umbral incrementó el acuerdo con la anotación humana (*Reason agreement*) del 88.7% al 89.7%.
* **Negativas:** Los pedidos excluidos por el umbral de 24h ya no se asignan a Vendor; al demostrarse mediante el análisis de migración que no pertenecían a Carrier ni a DC, requirieron una nueva estructura de clasificación neutra (detallada en el [ADR-07](ARD-07.md)).

