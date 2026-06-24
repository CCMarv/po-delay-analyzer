# ADR-04a · Umbral de carrier provisional (4h)

* **Estatus:** 📘 **SUPERADO** por el [ADR-04b · Umbral de carrier definitivo (8h)](ADR-04b.md)
* **Contexto Técnico:** Fase 1 / Análisis Exploratorio de Datos (EDA)
* **Referencias:** Configuración inicial de código duro

## Contexto y Problema
El transportista (*Carrier*) requiere un umbral de tolerancia para activar su flag de retraso. Durante la Fase 1 y el Análisis Exploratorio de Datos (EDA), se adoptó un límite provisional estricto de 4 horas con la intención de alertar de manera temprana cualquier desviación logística en los envíos.

## Opciones Consideradas

### Opción 1: Establecer un umbral provisional de 4 horas (Elegida inicialmente)
* **Pros:** Criterio estricto que no deja pasar ninguna micro-demora en el transporte.
* **Contras:** Al aplicarlo a la masa de datos real del proyecto, resultó ser demasiado sensible para un dataset compuesto principalmente por trayectos cortos, lo que generaba falsos positivos y ruido operativo en el negocio.

## Decisión Inicial
Se eligió la **Opción 1** de forma provisional para la primera iteración del pipeline durante el EDA de la Fase 1.

## Consecuencias de su Caída
* **Sobreatribución masiva:** El umbral disparaba la flag de retraso en el 25.8% de los casos (103 POs), sobrepenalizando al Carrier por retrasos menores insignificantes.
* **Obsolescencia:** Se descartó el 2026-06-16 tras la sugerencia del mentor en la discusión #53 para dar paso a un análisis de sensibilidad formal.

