# ADR-03a · Etapa VENDOR: Medición inicial por residuo operativo

* **Estatus:** 📘 **SUPERADO** por el [ADR-03b · Etapa VENDOR: Medición por señal directa STA push](ARD-03b.md)
* **Contexto Técnico:** Fase 2 / Primer modelo de atribución de retrasos
* **Referencias:** PR #59 (Desplegado el 15 de junio de 2026)

## Contexto y Problema
El modelo inicial requería una metodología para atribuir de manera precisa el retraso correspondiente al Proveedor (*Vendor*). Se buscaba un enfoque matemático que explicara el desvío total dentro del pipeline de datos.

## Opciones Consideradas

### Opción 1: Atribución de Vendor por residuo operativo (Elegida inicialmente)
Cálculo basado en la resta del tiempo total de demerito menos los tiempos imputables a los tramos de Carrier y Centro de Distribución (DC): `Delay − Carrier − DC`.
* **Pros:** Permite un cierre matemático exacto donde la suma de las partes iguala el retraso total del pedido.
* **Contras:** Asume erróneamente que todos los tramos de la cadena son perfectamente aditivos y excluyentes. Falla por completo en las 27 POs que no tienen registro de tráiler, rompiendo la integridad del pipeline.

### Opción 2: Atribución por señal directa STA push (`APPROVED_DT > STA_DT`)
Medición directa del desfase temporal utilizando los eventos de auditoría nativos del negocio: la fecha en que se aprueba el envío (`APPROVED_DT`) contra la fecha de arribo planificada original (`STA_DT`).
* **Pros:** No depende de que existan tramos aditivos y resuelve la medición para las 27 POs críticas sin tráiler.
* **Contras:** Si se aplica de forma directa y laxa sin un umbral de tolerancia, genera una sobreatribución masiva.

## Decisión Inicial
Se eligió la **Opción 1** debido a la simplicidad del cierre matemático aditivo. Fue implementada provisionalmente en el [PR #59](#).

## Consecuencias de su Caída
* **Falla de Integridad:** Se constató que la asunción de tramos aditivos rompe el análisis en los 27 POs sin tráiler. 
* **Obsolescencia:** La regla fue descartada tras la sesión de revisión con el mentor para transicionar hacia un modelo basado en señales directas.
