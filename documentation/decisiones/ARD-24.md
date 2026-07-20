# Regla Late Shipment del README: descartada por columna inexistente

* **Estatus:** 🟢 **Vigente**
* **Contexto Técnico:** Fase 2 / Modelado de reglas de clasificación — regla heredada del
  README/kickoff, nunca implementada
* **Referencias:** README del repo original del mentor (regla `VENDOR_SHIP_DT > STA_DT`);
  Issue #17 (prueba y descarte del proxy); [ADR-03b](ARD-03b.md) (STA Push, señal vendor
  vigente); `.claude/brief_proyecto.md`

## Contexto y Problema

El README del repo original del mentor define "Late Shipment" como causa vendor con la regla
`VENDOR_SHIP_DT > STA_DT`. La columna `VENDOR_SHIP_DT` no existe en ninguna de las 39 columnas
del CSV real — aparece en el kickoff sin definición ni en la lista de key fields, regla
huérfana desde el origen. El descarte ya ocurrió de facto (nunca se implementó, ni la regla ni
un proxy funcional), pero vivía disperso en el brief y en el issue #17, sin registro formal en
`documentation/decisiones/`: un evaluador que busque esta regla del README no encuentra su
descarte documentado.

## Opciones Consideradas

**Opción A — Dejarlo sin documentar (statu quo).** Pros: cero esfuerzo. Contras: la regla
sigue citada en el README del mentor; sin un registro explícito, parece un olvido del equipo
en vez de un descarte deliberado y justificado.

**Opción B — Proxy de lead time corto (`STA_DT − PO_DT < 3 días`) como clasificador de
causa.** Probado en #17: dispara en 0% de los casos sobre el dataset real — no discrimina
nada, mide planeación del vendor, no ejecución del envío. Descartado como clasificador de
etapa.

**Opción C — Documentar el descarte formalmente, sin implementar ninguna variante (elegida).**
Dado que la columna no existe y el único proxy probado no discrimina, no hay una versión
viable de esta regla para el dataset actual. La señal vendor real ya la cubre STA Push
(ADR-03b/06b), que no depende de `VENDOR_SHIP_DT` ni del proxy de lead time.

## Decisión

No se implementa Late Shipment como regla de clasificación de etapa. Dos razones
independientes, cada una suficiente por sí sola:

1. **La columna no existe.** `VENDOR_SHIP_DT` no está entre las 39 columnas del CSV real; no
   hay forma de calcular la regla tal como la describe el README del mentor.
2. **El proxy probado no discrimina.** `STA_DT − PO_DT < 3 días` (aproximación de lead time
   corto) se probó en #17 y disparó en 0% de los POs — no separa casos, así que no sirve como
   señal de causa aunque se aceptara como sustituto de `VENDOR_SHIP_DT`.

La responsabilidad vendor ya queda cubierta por **STA Push** (`APPROVED_DT > STA_DT`,
[ADR-03b](ARD-03b.md)/[ADR-06b](ARD-06b.md)), que no depende de ninguna de las dos columnas
en cuestión y sí tiene poder discriminante medido. `lead_time_days` (`STA_DT − PO_DT`) se
conserva únicamente como insumo potencial de **severidad**, no de etapa — no se implementa
en esa función aquí; queda como candidato futuro si el equipo decide ponderarlo.

## Consecuencias

**Positivas:** cierra la brecha de trazabilidad entre el README del mentor y las reglas
vigentes del proyecto — un evaluador que pregunte por "Late Shipment" tiene una respuesta
citable con su razón, no un silencio. No introduce código ni cambia el reparto de
`stage_primary` vigente.

**Negativas:** ninguna variante de la regla queda disponible incluso como insumo secundario
de etapa; si en el futuro aparece una columna real de fecha de embarque del vendor, este ARD
debería revisarse (no encadenarse a ciegas).

## Relación con otras decisiones

No supera ningún ARD previo — documenta un descarte que **ADR-03b** (STA Push) ya vuelve
innecesario como clasificador de etapa. No reabre la taxonomía de **ADR-07** (Indeterminado).
