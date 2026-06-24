# ADR-06a · Umbral propio de vendor: Modelo inicial sin umbral

* **Estatus:** 📘 **SUPERADO** por el [ADR-06b · Umbral propio de vendor: Configuración de 24h](ADR-06b.md)
* **Contexto Técnico:** Fase 2 / Clasificación por Reglas de Negocio
* **Referencias:** Implementación inicial de la señal directa (`APPROVED_DT > STA_DT`)

## Contexto y Problema
Al implementar el clasificador determinístico basado en la señal directa de la Fase 2, se asumió un modelo donde el Proveedor (*Vendor*) no requería una tolerancia inicial. El problema radicaba en medir de forma pura cualquier desvío numérico positivo en el pipeline de datos.

## Opciones Consideradas

### Opción 1: Mantener Vendor sin umbral de tolerancia (Elegida inicialmente)
* **Pros:** Refleja de manera cruda cualquier minuto de retraso en la aprobación del pedido.
* **Contras:** Genera una sobreatribución artificial severa (absorbiendo inicialmente el 62.8% de los casos). Introduce un sesgo sistémico que penaliza injustamente a Vendor por retrasos insignificantes, mientras que Carrier y DC operaban protegidos por umbrales estrictos (8h y 4/6h).

## Decisión Inicial
Se adoptó la **Opción 1** para la primera iteración funcional del clasificador, bajo la premisa de que la aprobación tardía era mandatoria por definición en el brief.

## Consecuencias de su Caída
* **Asimetría de Construcción:** Durante la Ronda 2 de consultas (respondida el 2026-06-18), el mentor señaló que el modelo estaba desbalanceado por la falta de un umbral en Vendor que equiparara las reglas de Carrier y DC.
* **Obsolescencia:** Se descartó de inmediato para migrar hacia un estudio analítico que determinara una tolerancia matemáticamente justificada.

