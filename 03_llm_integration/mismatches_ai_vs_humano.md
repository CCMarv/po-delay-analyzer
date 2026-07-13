# Mismatches AI vs humano — narración de evidencia (#95)

Documenta los ocho casos donde la clasificación por timestamps (`stage_primary`) discrepa del
`REASON_DSC` anotado por el staff del DC y el cómputo resulta más defendible. Son la evidencia
central de la tesis del proyecto: la anotación humana es ~20% incorrecta (dato del mentor); los
timestamps del lifecycle no lo son.

Fuente primaria: `fixtures/mismatches_llm_zeroshot.csv`, la corrida zero-shot ya congelada de
los 8 mismatches que `metrics_core.select_mismatches(df, n=8, stratify=True)` seleccionó en
Fase 2 (3 Vendor / 3 Carrier / 2 DC). Este documento no vuelve a llamar al LLM: reusa esa
corrida como artefacto versionado. El detalle de excesos por tramo remite a
`02_clasif_reglas_negocio/README.md` §5.4/§6 y a `metrics_core.select_mismatches`.

## Los ocho casos

| PO | Etapa (cómputo) | REASON_DSC (humano) | Evidencia temporal | Explicación LLM | Por qué el cómputo es más preciso |
|---|---|---|---|---|---|
| 100280 | Vendor | Carrier — "Missed appointment window" | STA push 124.6 h (exceso 100.6 h sobre umbral 24h); exceso carrier = 0 | Vendor, 5.54 d; el LLM marca coincidencia con el REASON_DSC | La aprobación se retrasó 124.6 h antes de que el PO llegara al carrier; el tramo carrier no tiene exceso medido — "ventana de cita perdida" es un síntoma corriente abajo, no la causa |
| 100236 | Vendor | Carrier — "Equipment/trailer issue" | STA push 118.5 h (exceso 94.5 h); exceso carrier = 0 | Vendor, 5.26 d; el LLM marca NO-coincidencia y nota hot PO | Mismo patrón: el push de aprobación antecede a cualquier tramo del carrier; "problema de equipo/tráiler" no tiene respaldo temporal |
| 100382 | Vendor | DC — "Yard congestion - no available door" | STA push 111.0 h (exceso 87.0 h); exceso yard/dock = 0 | Vendor, 5.01 d; el LLM marca coincidencia y nota hot PO | La aprobación llegó tarde antes de que el PO llegara al patio; sin exceso medido en yard/dock |
| 100024 | Carrier | DC — "Dock processing backlog" | Exceso carrier 25.7 h; exceso dock = 0 | Carrier, 1.07 d; el LLM marca NO-coincidencia | El exceso vive en tránsito, no en el procesamiento del dock, que no muestra backlog medido |
| 100244 | Carrier | DC — "Yard congestion - no available door" | Exceso carrier 30.8 h; exceso yard/dock = 0 | Carrier, 1.63 d; el LLM marca NO-coincidencia | Igual que 100024: la señal está en tránsito, no en patio/puerta del DC |
| 100138 | Carrier | DC — "Dock processing backlog" | Exceso carrier 1.9 h (señal más débil del lote, apenas sobre el umbral de 8h); exceso dock = 0 | Carrier, 0.43 d; el LLM marca NO-coincidencia | Aun con retraso menor, el exceso identificable sigue en carrier, no en dock |
| 100058 | DC | Carrier — "Equipment/trailer issue" | Exceso DC 19.3 h; exceso carrier = 0 | DC, 0.82 d; el LLM marca coincidencia | El exceso se mide en el tramo DC, no en tránsito del carrier; "problema de equipo/tráiler" no tiene respaldo temporal en carrier |
| 100230 | DC (subclase yard/dock no confirmada — el fixture no trae `dc_substage`) | Carrier — "Equipment/trailer issue" | Exceso DC 19.0 h; exceso carrier = 0 | DC, 0.75 d; el LLM marca coincidencia | Mismo patrón que 100058 (mismo REASON_DSC y reason_group_manual); el exceso vive en DC, no en carrier |

## Patrón transversal

Los ocho mismatches exhiben dos variantes del mismo fenómeno. En los tres casos Vendor (100280,
100236, 100382) el humano culpa al eslabón donde el PO se atoró físicamente —carrier o patio del
DC— mientras la aprobación ya había llegado tarde desde antes (STA push de 87–125 h) y el tramo
acusado no registra exceso alguno: es el patrón "eslabón visible" ya documentado en el README de
Fase 2. En los cinco casos restantes (Carrier↔DC) el humano confunde dos etapas downstream
contiguas —tránsito vs. procesamiento en el DC— mientras el cómputo aísla el exceso en una sola
de las dos.

Un matiz honesto: en 4 de los 8 casos (100280, 100382, 100058, 100230) el propio LLM marcó
coincidencia con el REASON_DSC pese al mismatch categórico entre `stage_primary` y
`reason_group_manual`. Esto no debilita la tesis: ocurre porque el texto del REASON_DSC es
temáticamente compatible con la etapa que el cómputo señala, no con la etapa a la que quedó
archivado — es decir, incluso la redacción humana del motivo es ambigua frente a la taxonomía de
tres etapas que usa el clasificador.

## Uso posterior

Este documento es insumo del documento de hallazgos del reporte final (#105) y de la validación
de cierre (#85). No abre trabajo de ninguno de los dos issues.
