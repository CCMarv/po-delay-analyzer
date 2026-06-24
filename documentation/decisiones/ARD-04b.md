# ADR-04b · Umbral de carrier definitivo (8h)

* **Estatus:** 🟢 **VIGENTE** (Reemplaza al [ADR-04a · Umbral de carrier provisional (4h)](ADR-04a.md))
* **Contexto Técnico:** Fase 2 / Configuración de Reglas de Negocio
* **Referencias:** Issue #41, Discussion #53, sugerido por el mentor el 2026-06-16

## Contexto y Problema
Tras la caída del umbral de 4 horas por exceso de ruido en los datos (detallado en el [ADR-04a](ADR-04a.md)), el modelo requería una calibración justa y justificada que se acoplara a la naturaleza del dataset (trayectos cortos) sin perder la capacidad de capturar impactos severos en el transporte.

## Opciones Consideradas

### Opción 1: Incrementar el umbral a 8 horas respaldado por una tabla de sensibilidad (4/6/8/12h) (Elegida)
* **Pros:** Mitiga el ruido en los datos, bajando la activación de la flag a un 12.8% (51 POs), consistente con la operación real. Cuenta con el respaldo analítico de una matriz de sensibilidad para futuras calibraciones.
* **Contras:** Requiere modificar los archivos de configuración centralizados y documentar el estudio para justificar el cambio ante los stakeholders.

*(Nota: Mantener las 4 horas fue descartado por los problemas de falsos positivos descritos).*

## Decisión Definitiva
Elegimos la **Opción 1**. Tras la sugerencia del mentor el 2026-06-16 en la discusión [#53](#), se establece de forma definitiva un **umbral de 8 horas** para el Carrier. 

Este parámetro quedó desacoplado del código duro y se persistió formalmente en el archivo de configuración centralizado **`rules_config.json`**. El cambio analítico demostró la estabilización de la atribución logística.

## Consecuencias
* **Positivas:** Reducción drástica de falsos positivos en el tramo de transporte y mayor confianza del negocio en las alertas generadas por el clasificador.
* **Negativas:** Los pedidos que presenten retrasos de entre 4 y 7.9 horas ya no activarán la flag de Carrier, requiriendo monitoreo secundario si el negocio experimenta micro-demoras sistémicas.

