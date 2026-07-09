# ADR-03b · Etapa VENDOR: Medición por señal directa STA push

* **Estatus:** 🟢 **VIGENTE** (Reemplaza al [ADR-03a · Etapa VENDOR: Medición inicial por residuo operativo](ARD-03a.md))
* **Contexto Técnico:** Cierre de Fase 2 / Modelado de Atribución Dominante
* **Referencias:** Issue #40, Discussion #57, PR #62, PR #64, PR #66 (Validado por el mentor el 2026-06-16)

## Contexto y Problema
Tras la obsolescencia del modelo residual (detallada en el [ADR-03a](ARD-03a.md)), el reto principal radicaba en medir el tramo de forma justa sin asumir comportamientos aditivos inexistentes en la cadena, asegurando la cobertura del 100% del dataset, incluidas las 27 Órdenes de Compra (POs) que carecen de registro de tráiler.

## Opciones Consideradas

### Opción 1: Atribución por señal directa STA push (`APPROVED_DT > STA_DT`) (Elegida)
Medición directa del desfase temporal utilizando los eventos de auditoría nativos del negocio: la fecha en que se aprueba el envío (`APPROVED_DT`) contra la fecha de arribo planificada original (`STA_DT`).
* **Pros:** Es la regla estipulada orgánicamente desde el kickoff del proyecto. No depende de que existan tramos aditivos y resuelve la medición para las 27 POs críticas sin tráiler.
* **Contras:** Si se aplica de forma directa y laxa sin un umbral de tolerancia, genera una sobreatribución masiva (absorbiendo inicialmente el 62.8% de los casos) debido a la asimetría con Carrier y DC.

*(Nota: El modelo residual ya no fue considerado como opción viable en esta etapa por sus fallas estructurales).*

## Decisión Definitiva
Elegimos la **Opción 1**. Tras la validación con el mentor el 2026-06-16, se adopta de forma definitiva la **señal directa STA push** como el estándar para medir a Vendor. 

Para corregir la asimetría de construcción detectada en la discusión [#57](#), esta decisión evolucionó posteriormente e integró un umbral restrictivo de tolerancia (`vendor_gap_hrs = 24h`), el cual se detalla por separado en el [ADR-06b](ARD-06b.md). El código final fue desplegado mediante un stack de Pull Requests ([PR #62](#), [PR #66](#), [PR #64](#)).

## Consecuencias
* **Positivas:** El clasificador es robusto, seguro y capaz de evaluar el 100% de las POs del dataset (incluyendo las 27 sin tráiler). Cumple con las directrices de diseño limpio validadas por la mentoría.
* **Negativas:** La introducción de la señal directa obligó a replantear el tratamiento de los casos limítrofes y de empates matemáticos, forzando la creación de una nueva taxonomía de soporte para pedidos indeterminados (detallada en el [ADR-07](ARD-07.md)).
